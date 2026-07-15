from __future__ import annotations

from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - exercised on Python 3.10
    import tomli as tomllib


REPO_ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = REPO_ROOT / "pyproject.toml"
EXPECTED_NOTEBOOKS_DEPENDENCIES = [
    "ipykernel>=6.29",
    "matplotlib>=3.8",
    "mkdocs>=1.6,<2",
    "mkdocs-jupyter>=0.26,<0.27",
    "nbclient>=0.10,<0.12",
    "nbformat>=5.10,<6",
]
COMPONENT_EXTRAS = {"test", "notebooks", "docs", "dev"}


def _project_metadata() -> dict[str, object]:
    return tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]


def test_runtime_dependencies_remain_empty() -> None:
    project = _project_metadata()

    assert project["dependencies"] == []


def test_notebooks_extra_is_complete_and_singular_name_is_removed() -> None:
    project = _project_metadata()
    extras = project["optional-dependencies"]

    assert extras["notebooks"] == EXPECTED_NOTEBOOKS_DEPENDENCIES
    assert "notebook" not in extras


def test_all_extra_is_the_exact_union_of_component_extras() -> None:
    project = _project_metadata()
    extras = project["optional-dependencies"]

    expected_all = set().union(
        *(set(extras[extra]) for extra in COMPONENT_EXTRAS)
    )
    assert set(extras["all"]) == expected_all
    assert len(extras["all"]) == len(set(extras["all"]))


def test_all_extra_includes_contributor_tooling() -> None:
    project = _project_metadata()
    all_requirements = "\n".join(project["optional-dependencies"]["all"]).lower()

    for contributor_package in (
        "build",
        "cffconvert",
        "flake8",
        "mypy",
        "pytest",
        "twine",
    ):
        assert contributor_package in all_requirements


def test_dev_extra_contains_release_validation_tools() -> None:
    project = _project_metadata()
    dev_requirements = "\n".join(project["optional-dependencies"]["dev"]).lower()

    assert "mypy" in dev_requirements
    assert "cffconvert" in dev_requirements


def test_mypy_uses_strict_minimum_python_configuration() -> None:
    config = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["tool"]["mypy"]

    assert config == {"python_version": "3.10", "strict": True}


def test_docs_extra_contains_only_used_documentation_tooling() -> None:
    project = _project_metadata()
    docs_requirements = "\n".join(project["optional-dependencies"]["docs"])

    assert "mkdocs-include-markdown-plugin" not in docs_requirements
    assert "tomli" not in docs_requirements


def test_mkdocs_stays_on_the_supported_1_x_line() -> None:
    project = _project_metadata()
    extras = project["optional-dependencies"]

    for extra in ("docs", "notebooks", "all"):
        assert extras[extra].count("mkdocs>=1.6,<2") == 1


def test_python_314_is_classified() -> None:
    project = _project_metadata()

    assert "Programming Language :: Python :: 3.14" in project["classifiers"]
