#!/usr/bin/env python3
"""Copy the bundled static web-deck template into a new output directory."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, help="New output directory")
    parser.add_argument("--title", required=True, help="Deck title")
    args = parser.parse_args()

    output = Path(args.output).expanduser().resolve()
    template = Path(__file__).resolve().parents[1] / "assets" / "web-deck-template"
    if output.exists() and any(output.iterdir()):
        parser.error(f"output directory is not empty: {output}")
    if not template.is_dir():
        parser.error(f"template is missing: {template}")

    output.mkdir(parents=True, exist_ok=True)
    shutil.copytree(template, output, dirs_exist_ok=True)
    index_path = output / "index.html"
    index_path.write_text(
        index_path.read_text(encoding="utf-8").replace("__DECK_TITLE__", args.title),
        encoding="utf-8",
    )
    (output / "assets").mkdir(exist_ok=True)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
