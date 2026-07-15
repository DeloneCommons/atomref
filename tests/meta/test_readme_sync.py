from __future__ import annotations

from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
README = REPO_ROOT / 'README.md'
SCRIPT = REPO_ROOT / 'tools' / 'gen_readme.py'


def test_readme_is_in_sync(tmp_path: Path) -> None:
    generated = tmp_path / 'README.generated.md'
    subprocess.run(
        [sys.executable, str(SCRIPT), '--output', str(generated)],
        cwd=REPO_ROOT,
        check=True,
    )
    assert generated.read_bytes() == README.read_bytes()
    assert b'\r' not in generated.read_bytes()


def test_readme_check_rejects_crlf_output(tmp_path: Path) -> None:
    generated = tmp_path / 'README.generated.md'
    subprocess.run(
        [sys.executable, str(SCRIPT), '--output', str(generated)],
        cwd=REPO_ROOT,
        check=True,
    )
    generated.write_bytes(generated.read_bytes().replace(b'\n', b'\r\n'))

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            '--output',
            str(generated),
            '--check',
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert 'out of sync' in result.stderr
