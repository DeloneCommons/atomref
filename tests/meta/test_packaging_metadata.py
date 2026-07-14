from __future__ import annotations

from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - exercised on Python 3.10
    import tomli as tomllib


REPO_ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = REPO_ROOT / "pyproject.toml"
EXPECTED_NOTEBOOK_DEPENDENCIES = [
    "ipykernel>=6.29",
    "matplotlib>=3.8",
    "mkdocs-jupyter>=0.26,<0.27",
    "nbclient>=0.10,<0.12",
    "nbformat>=5.10,<6",
]


def _project_metadata() -> dict[str, object]:
    return tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]


def test_runtime_dependencies_remain_empty() -> None:
    project = _project_metadata()

    assert project["dependencies"] == []


def test_notebook_and_all_extras_are_identical_and_complete() -> None:
    project = _project_metadata()
    extras = project["optional-dependencies"]

    assert extras["notebook"] == EXPECTED_NOTEBOOK_DEPENDENCIES
    assert extras["all"] == EXPECTED_NOTEBOOK_DEPENDENCIES


def test_all_extra_excludes_contributor_tooling() -> None:
    project = _project_metadata()
    all_requirements = "\n".join(project["optional-dependencies"]["all"]).lower()

    for contributor_package in ("build", "flake8", "pytest", "twine"):
        assert contributor_package not in all_requirements


def test_docs_extra_contains_only_used_documentation_tooling() -> None:
    project = _project_metadata()
    docs_requirements = "\n".join(project["optional-dependencies"]["docs"])

    assert "mkdocs-include-markdown-plugin" not in docs_requirements
    assert "tomli" not in docs_requirements
