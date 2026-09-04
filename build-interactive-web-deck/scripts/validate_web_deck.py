#!/usr/bin/env python3
"""Validate a generated static web deck and its content contract."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlparse


REQUIRED_FILES = ("index.html", "styles.css", "app.js", "deck-data.js")
REQUIRED_PAGE_FIELDS = ("id", "title", "claim", "durationSeconds", "speakerNotes")
ALLOWED_LAYOUTS = {"left", "right", "bottom", "full"}


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def load_data(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    match = re.fullmatch(r"\s*window\.DECK_DATA\s*=\s*(\{.*\})\s*;?\s*", raw, re.S)
    if not match:
        raise ValueError("deck-data.js must contain one JSON object assigned to window.DECK_DATA")
    return json.loads(match.group(1))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("deck_dir", help="Directory containing the generated deck")
    args = parser.parse_args()
    root = Path(args.deck_dir).expanduser().resolve()
    errors: list[str] = []

    for filename in REQUIRED_FILES:
        if not (root / filename).is_file():
            fail(errors, f"missing required file: {filename}")
    if errors:
        print("\n".join(f"ERROR: {item}" for item in errors))
        return 1

    try:
        data = load_data(root / "deck-data.js")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        return 1

    meta = data.get("meta")
    pages = data.get("pages")
    if not isinstance(meta, dict) or not str(meta.get("title", "")).strip():
        fail(errors, "meta.title is required")
    if not isinstance(pages, list) or not pages:
        fail(errors, "pages must be a non-empty array")
        pages = []

    ids: set[str] = set()
    for index, page in enumerate(pages, start=1):
        prefix = f"page {index}"
        if not isinstance(page, dict):
            fail(errors, f"{prefix} must be an object")
            continue
        for field in REQUIRED_PAGE_FIELDS:
            if field not in page or page[field] in (None, "", []):
                fail(errors, f"{prefix} missing {field}")
        page_id = str(page.get("id", ""))
        if page_id in ids:
            fail(errors, f"duplicate page id: {page_id}")
        ids.add(page_id)
        if page.get("layout", "left") not in ALLOWED_LAYOUTS:
            fail(errors, f"{prefix} has invalid layout: {page.get('layout')}")
        if not isinstance(page.get("durationSeconds", 0), (int, float)) or page.get("durationSeconds", 0) <= 0:
            fail(errors, f"{prefix} durationSeconds must be positive")
        if not isinstance(page.get("speakerNotes", []), list):
            fail(errors, f"{prefix} speakerNotes must be an array")

        image = page.get("image")
        if image and not (root / image).is_file():
            fail(errors, f"{prefix} image is missing: {image}")
        if image and not str(page.get("imageAlt", "")).strip():
            fail(errors, f"{prefix} imageAlt is required when image is present")

        evidence = page.get("evidence", [])
        if not isinstance(evidence, list):
            fail(errors, f"{prefix} evidence must be an array")
            evidence = []
        for source_index, source in enumerate(evidence):
            if not isinstance(source, dict) or not str(source.get("label", "")).strip():
                fail(errors, f"{prefix} evidence {source_index} needs a label")
                continue
            url = str(source.get("url", "")).strip()
            if url and urlparse(url).scheme not in {"http", "https"}:
                fail(errors, f"{prefix} evidence {source_index} has invalid URL: {url}")

        hotspots = page.get("hotspots", [])
        if not isinstance(hotspots, list):
            fail(errors, f"{prefix} hotspots must be an array")
            continue
        for hot_index, hotspot in enumerate(hotspots):
            if not isinstance(hotspot, dict):
                fail(errors, f"{prefix} hotspot {hot_index} must be an object")
                continue
            for coordinate in ("x", "y", "w", "h"):
                value = hotspot.get(coordinate)
                if not isinstance(value, (int, float)) or not 0 <= value <= 100:
                    fail(errors, f"{prefix} hotspot {hot_index} has invalid {coordinate}")
            for source_index in hotspot.get("sources", []):
                if not isinstance(source_index, int) or not 0 <= source_index < len(evidence):
                    fail(errors, f"{prefix} hotspot {hot_index} has invalid source index {source_index}")

    for index, page in enumerate(pages, start=1):
        for hotspot in page.get("hotspots", []) if isinstance(page, dict) else []:
            target = hotspot.get("targetPage") if isinstance(hotspot, dict) else None
            if target and str(target) not in ids:
                fail(errors, f"page {index} hotspot targets unknown page: {target}")

    all_text = "\n".join((root / name).read_text(encoding="utf-8") for name in REQUIRED_FILES)
    if "__DECK_TITLE__" in all_text or re.search(r"\bTODO\b|\bPLACEHOLDER\b", all_text, re.I):
        fail(errors, "placeholder text remains")

    if errors:
        print("\n".join(f"ERROR: {item}" for item in errors))
        return 1
    print(f"OK: {len(pages)} pages validated in {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
