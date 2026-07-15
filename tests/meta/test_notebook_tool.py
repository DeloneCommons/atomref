from __future__ import annotations

import importlib.util
from pathlib import Path
import signal
import subprocess
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
CHECK_NOTEBOOKS_PATH = REPO_ROOT / "tools" / "check_notebooks.py"
CI_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "ci.yml"

spec = importlib.util.spec_from_file_location(
    "check_notebooks_tool", CHECK_NOTEBOOKS_PATH
)
assert spec is not None and spec.loader is not None
check_notebooks = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = check_notebooks
spec.loader.exec_module(check_notebooks)


class FakeProcess:
    def __init__(self, returncode: int = 0) -> None:
        self.pid = 4312
        self.returncode = returncode
        self.wait_timeouts: list[float] = []
        self.killed = False

    def poll(self) -> int | None:
        return None

    def wait(self, timeout: float) -> int:
        self.wait_timeouts.append(timeout)
        return self.returncode

    def kill(self) -> None:
        self.killed = True


def test_worker_process_group_options_are_platform_specific(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(check_notebooks, "IS_WINDOWS", False)
    assert check_notebooks._worker_group_options() == {"start_new_session": True}

    monkeypatch.setattr(check_notebooks, "IS_WINDOWS", True)
    monkeypatch.setattr(
        check_notebooks.subprocess,
        "CREATE_NEW_PROCESS_GROUP",
        0x00000200,
        raising=False,
    )
    assert check_notebooks._worker_group_options() == {"creationflags": 0x00000200}


def test_worker_uses_one_bounded_standard_jupyter_process(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    notebook = tmp_path / "example.ipynb"
    notebook.touch()
    working_dir = tmp_path / "working"
    working_dir.mkdir()
    runtime_root = tmp_path / "runtime" / "example"
    process = FakeProcess()
    captured: dict[str, object] = {}

    def popen(command: list[str], **kwargs: object) -> FakeProcess:
        captured["command"] = command
        captured.update(kwargs)
        return process

    monkeypatch.setattr(check_notebooks.subprocess, "Popen", popen)
    monkeypatch.setattr(
        check_notebooks,
        "_worker_group_options",
        lambda: {"start_new_session": True},
    )

    check_notebooks._run_worker(
        notebook,
        working_dir=working_dir,
        runtime_root=runtime_root,
    )

    assert captured["command"] == [
        sys.executable,
        "-m",
        "jupyter",
        "execute",
        f"--timeout={check_notebooks.CELL_TIMEOUT_SECONDS}",
        f"--startup_timeout={check_notebooks.KERNEL_STARTUP_TIMEOUT_SECONDS}",
        "--Application.log_level=INFO",
        "--inplace",
        str(notebook),
    ]
    assert captured["cwd"] == working_dir
    assert captured["start_new_session"] is True
    environment = captured["env"]
    assert isinstance(environment, dict)
    assert environment["JUPYTER_RUNTIME_DIR"] == str(runtime_root / "jupyter-runtime")
    assert environment["MPLBACKEND"] == "Agg"
    assert process.wait_timeouts == [check_notebooks.WORKER_TIMEOUT_SECONDS]


def test_worker_timeout_terminates_group_and_names_phase(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    notebook = tmp_path / "cleanup-hang.ipynb"
    notebook.touch()
    process = FakeProcess()
    terminated: list[FakeProcess] = []

    def timeout(*, timeout: float) -> int:
        raise subprocess.TimeoutExpired(["jupyter", "execute"], timeout)

    process.wait = timeout  # type: ignore[method-assign]
    monkeypatch.setattr(
        check_notebooks.subprocess,
        "Popen",
        lambda *_args, **_kwargs: process,
    )
    monkeypatch.setattr(check_notebooks, "_terminate_worker", terminated.append)

    with pytest.raises(
        check_notebooks.NotebookCheckError,
        match=(
            r"cleanup-hang\.ipynb.*420-second.*kernel startup, cell execution, "
            r"kernel cleanup, or process exit.*worker containment completed"
        ),
    ):
        check_notebooks._run_worker(
            notebook,
            working_dir=tmp_path,
            runtime_root=tmp_path / "runtime",
        )

    assert terminated == [process]


def test_worker_nonzero_exit_names_notebook_phase_and_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    notebook = tmp_path / "cell-error.ipynb"
    notebook.touch()
    process = FakeProcess(returncode=17)
    monkeypatch.setattr(
        check_notebooks.subprocess,
        "Popen",
        lambda *_args, **_kwargs: process,
    )

    with pytest.raises(
        check_notebooks.NotebookCheckError,
        match=r"cell-error\.ipynb.*startup, execution, or cleanup.*status 17",
    ):
        check_notebooks._run_worker(
            notebook,
            working_dir=tmp_path,
            runtime_root=tmp_path / "runtime",
        )


def test_posix_worker_group_is_force_killed_and_reaped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = FakeProcess()
    signals: list[tuple[int, signal.Signals]] = []
    monkeypatch.setattr(check_notebooks, "IS_WINDOWS", False)
    monkeypatch.setattr(
        check_notebooks.os,
        "killpg",
        lambda pid, sent_signal: signals.append((pid, sent_signal)),
    )

    check_notebooks._terminate_worker(process)

    assert signals == [(process.pid, signal.SIGKILL)]
    assert process.wait_timeouts == [
        check_notebooks.WORKER_TERMINATION_TIMEOUT_SECONDS
    ]
    assert not process.killed


def test_windows_worker_tree_is_force_killed_and_reaped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = FakeProcess()
    calls: list[tuple[list[str], dict[str, object]]] = []
    monkeypatch.setattr(check_notebooks, "IS_WINDOWS", True)

    def run(
        command: list[str], **kwargs: object
    ) -> subprocess.CompletedProcess[bytes]:
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(check_notebooks.subprocess, "run", run)

    check_notebooks._terminate_worker(process)

    assert calls[0][0] == [
        "taskkill",
        "/PID",
        str(process.pid),
        "/T",
        "/F",
    ]
    assert calls[0][1]["timeout"] == (
        check_notebooks.WORKER_TERMINATION_TIMEOUT_SECONDS
    )
    assert process.wait_timeouts == [
        check_notebooks.WORKER_TERMINATION_TIMEOUT_SECONDS
    ]


def test_posix_already_exited_group_is_still_reaped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = FakeProcess()
    monkeypatch.setattr(check_notebooks, "IS_WINDOWS", False)

    def missing_group(_pid: int, _sent_signal: signal.Signals) -> None:
        raise ProcessLookupError

    monkeypatch.setattr(check_notebooks.os, "killpg", missing_group)

    check_notebooks._terminate_worker(process)

    assert process.wait_timeouts == [
        check_notebooks.WORKER_TERMINATION_TIMEOUT_SECONDS
    ]


@pytest.mark.parametrize(
    "taskkill_error",
    [OSError("taskkill unavailable"), subprocess.TimeoutExpired("taskkill", 10)],
)
def test_windows_taskkill_failure_is_reported_after_direct_kill(
    taskkill_error: BaseException,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = FakeProcess()
    monkeypatch.setattr(check_notebooks, "IS_WINDOWS", True)

    def fail(*_args: object, **_kwargs: object) -> None:
        raise taskkill_error

    monkeypatch.setattr(check_notebooks.subprocess, "run", fail)

    with pytest.raises(
        check_notebooks.NotebookCheckError,
        match=r"could not confirm termination of Windows worker tree 4312",
    ):
        check_notebooks._terminate_worker(process)

    assert process.killed


def test_unreapable_worker_has_bounded_diagnostic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = FakeProcess()
    wait_calls = 0
    monkeypatch.setattr(check_notebooks, "IS_WINDOWS", False)
    monkeypatch.setattr(check_notebooks.os, "killpg", lambda *_args: None)

    def timeout(*, timeout: float) -> int:
        nonlocal wait_calls
        wait_calls += 1
        raise subprocess.TimeoutExpired("worker", timeout)

    process.wait = timeout  # type: ignore[method-assign]

    with pytest.raises(
        check_notebooks.NotebookCheckError,
        match=r"worker process 4312 could not be reaped",
    ):
        check_notebooks._terminate_worker(process)

    assert wait_calls == 2
    assert process.killed


def test_aggregate_success_waits_for_every_worker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_root = tmp_path / "source"
    source_root.mkdir()
    notebooks = []
    for name in ("one.ipynb", "two.ipynb"):
        notebook = tmp_path / name
        notebook.touch()
        notebooks.append(notebook)
    completed: list[str] = []

    monkeypatch.setattr(check_notebooks, "SRC", source_root)
    monkeypatch.setattr(
        check_notebooks,
        "_run_worker",
        lambda path, **_kwargs: completed.append(path.name),
    )

    assert check_notebooks.smoke_execute(notebooks) == 0

    assert completed == ["one.ipynb", "two.ipynb"]
    output = capsys.readouterr().out
    assert "phase=Jupyter startup/execution/cleanup" in output
    assert output.rstrip().endswith(
        "Smoke-executed 2 notebook(s) in temporary kernels."
    )


def test_cleanup_hang_cannot_print_aggregate_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_root = tmp_path / "source"
    source_root.mkdir()
    notebook = tmp_path / "cleanup-hang.ipynb"
    notebook.touch()
    monkeypatch.setattr(check_notebooks, "SRC", source_root)

    def fail(*_args: object, **_kwargs: object) -> None:
        raise check_notebooks.NotebookCheckError("cleanup did not exit")

    monkeypatch.setattr(check_notebooks, "_run_worker", fail)

    with pytest.raises(check_notebooks.NotebookCheckError):
        check_notebooks.smoke_execute([notebook])

    output = capsys.readouterr().out
    assert "cleanup-hang.ipynb" in output
    assert "Smoke-executed" not in output


def test_complete_check_deadline_stops_before_another_worker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_root = tmp_path / "source"
    source_root.mkdir()
    notebook = tmp_path / "not-started.ipynb"
    notebook.touch()
    monotonic_values = iter([10.0, 10.0 + check_notebooks.CHECK_TIMEOUT_SECONDS])
    monkeypatch.setattr(check_notebooks, "SRC", source_root)
    monkeypatch.setattr(
        check_notebooks.time,
        "monotonic",
        lambda: next(monotonic_values),
    )
    monkeypatch.setattr(
        check_notebooks,
        "_run_worker",
        lambda *_args, **_kwargs: pytest.fail("expired worker must not start"),
    )

    with pytest.raises(
        check_notebooks.NotebookCheckError,
        match=r"not-started\.ipynb.*complete notebook smoke check exceeded.*900",
    ):
        check_notebooks.smoke_execute([notebook])


def test_ci_notebook_job_has_outer_timeout() -> None:
    workflow = CI_WORKFLOW_PATH.read_text(encoding="utf-8")
    notebook_job = workflow.split("  notebooks-smoke:", 1)[1].split(
        "\n  docs-check:", 1
    )[0]
    smoke_step = notebook_job.split(
        "      - name: Smoke-execute notebooks with Jupyter", 1
    )[1]

    assert "timeout-minutes: 20" in smoke_step
    assert "run: python tools/check_notebooks.py" in smoke_step
