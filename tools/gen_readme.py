"""Generate ``README.md`` from the documentation home page."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE = REPO_ROOT / "docs" / "index.md"
README = REPO_ROOT / "README.md"
DOCS_URL = "https://delonecommons.github.io/atomref"
DOCS_LINE = f"Documentation: {DOCS_URL}"
FOOTER = """

---

This README is generated from `docs/index.md`.

To regenerate it:

```bash
python tools/gen_readme.py
```

Edit the documentation sources instead of editing `README.md` directly.
"""


def _insert_documentation_line(text: str) -> str:
    """Return ``text`` with the documentation URL inserted after top badges."""

    lines = text.splitlines()
    insert_at: int | None = None
    in_badge_block = False

    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            if in_badge_block:
                insert_at = index
                break
            continue
        if stripped.startswith("[!["):
            in_badge_block = True
            continue
        if in_badge_block:
            insert_at = index
            break

    if DOCS_LINE in lines:
        return text

    if insert_at is None:
        return f"{text.rstrip()}\n\n{DOCS_LINE}\n"

    updated = lines[:insert_at] + ["", DOCS_LINE] + lines[insert_at:]
    return "\n".join(updated)


def render_readme() -> str:
    """Return the generated README text."""

    body = SOURCE.read_text(encoding="utf-8").rstrip()
    body = _insert_documentation_line(body)
    return f"{body}{FOOTER}"


def main() -> int:
    """Generate or verify the repository README file."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=README)
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit with status 1 when the target file is out of sync",
    )
    args = parser.parse_args()

    rendered = render_readme()
    if args.check:
        current = args.output.read_text(encoding="utf-8")
        if current != rendered:
            print(f"{args.output} is out of sync with docs/index.md", file=sys.stderr)
            return 1
        return 0

    args.output.write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
