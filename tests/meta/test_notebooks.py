from __future__ import annotations

import base64
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
NOTEBOOKS = REPO_ROOT / "docs" / "notebooks"
EXPECTED_NOTEBOOKS = {
    "01-quickstart.ipynb",
    "02-policies-and-assessment.ipynb",
    "03-custom-sets-and-discovery.ipynb",
    "04-ias-method-selection-study.ipynb",
    "05-proatomic-density-and-ias.ipynb",
}
EXPECTED_SAVED_PNG_OUTPUTS = {
    "01-quickstart.ipynb": 0,
    "02-policies-and-assessment.ipynb": 0,
    "03-custom-sets-and-discovery.ipynb": 0,
    "04-ias-method-selection-study.ipynb": 3,
    "05-proatomic-density-and-ias.ipynb": 2,
}
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _load_notebook(path: Path) -> dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    assert data.get("nbformat") == 4
    return data


def _source(cell: dict[str, object]) -> str:
    source = cell.get("source", [])
    if isinstance(source, str):
        return source
    assert isinstance(source, list)
    assert all(isinstance(line, str) for line in source)
    return "".join(source)


def _text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    assert isinstance(value, list)
    assert all(isinstance(line, str) for line in value)
    return "".join(value)


def _cells(data: dict[str, object]) -> list[dict[str, object]]:
    cells = data.get("cells")
    assert isinstance(cells, list)
    assert all(isinstance(cell, dict) for cell in cells)
    return cells


def test_notebooks_have_one_direct_documentation_source() -> None:
    assert {path.name for path in NOTEBOOKS.glob("*.ipynb")} == EXPECTED_NOTEBOOKS
    assert not list((REPO_ROOT / "notebooks").glob("*.ipynb"))
    assert not list(NOTEBOOKS.glob("*.md"))
    assert not (REPO_ROOT / "tools" / "export_notebooks.py").exists()


def test_notebooks_have_narrative_structure_and_saved_success() -> None:
    for name in sorted(EXPECTED_NOTEBOOKS):
        cells = _cells(_load_notebook(NOTEBOOKS / name))
        markdown_cells = [cell for cell in cells if cell.get("cell_type") == "markdown"]
        code_cells = [cell for cell in cells if cell.get("cell_type") == "code"]
        markdown = "\n".join(_source(cell) for cell in markdown_cells)

        assert markdown.lstrip().startswith("# "), name
        assert "prerequisite" in markdown.lower(), name
        assert "## " in markdown, name
        assert "limitation" in markdown.lower(), name
        assert code_cells, name

        outputs = [
            output
            for cell in code_cells
            for output in cell.get("outputs", [])
            if isinstance(output, dict)
        ]
        assert outputs, name
        assert not any(output.get("output_type") == "error" for output in outputs)

        text_outputs = []
        png_outputs = []
        for output in outputs:
            data = output.get("data", {})
            assert isinstance(data, dict)
            if _text(output.get("text")) or _text(data.get("text/plain")):
                text_outputs.append(output)
            if _text(data.get("image/png")):
                png_outputs.append(output)

        assert text_outputs, name
        assert len(png_outputs) == EXPECTED_SAVED_PNG_OUTPUTS[name]
        for output in png_outputs:
            data = output["data"]
            assert isinstance(data, dict)
            payload = base64.b64decode(_text(data["image/png"]), validate=True)
            assert payload.startswith(PNG_SIGNATURE), name

        for index, cell in enumerate(cells):
            if cell.get("cell_type") != "code" or not _source(cell).strip():
                continue
            assert index > 0, name
            previous = cells[index - 1]
            assert previous.get("cell_type") == "markdown", name
            assert _source(previous).strip(), name


def test_notebook_site_content_includes_math_text_and_png() -> None:
    notebooks = [_load_notebook(NOTEBOOKS / name) for name in EXPECTED_NOTEBOOKS]
    cells = [cell for notebook in notebooks for cell in _cells(notebook)]
    markdown = "\n".join(
        _source(cell) for cell in cells if cell.get("cell_type") == "markdown"
    )
    outputs = [
        output
        for cell in cells
        for output in cell.get("outputs", [])
        if isinstance(output, dict)
    ]

    assert "$\\rho_c$" in markdown
    assert "$$\n\\rho_c" in markdown
    assert any(
        output.get("output_type") == "stream"
        and bool("".join(output.get("text", [])))
        for output in outputs
    )
    assert any(
        isinstance(output.get("data"), dict)
        and bool(output["data"].get("image/png"))
        for output in outputs
    )
