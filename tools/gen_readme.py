from __future__ import annotations

import argparse
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE = REPO_ROOT / 'docs' / 'index.md'
README = REPO_ROOT / 'README.md'


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=README)
    args = parser.parse_args()
    args.output.write_text(SOURCE.read_text(encoding='utf-8'), encoding='utf-8')


if __name__ == '__main__':
    main()
