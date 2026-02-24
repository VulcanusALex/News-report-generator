#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml


DEFAULT_CONFIG = "config/sources.yaml"
SECTIONS = {"strikes", "italian_news", "world_news", "ai_news", "milan_events"}


def _load(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data


def _save(path: Path, data: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)


def _emit(payload: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False))
    else:
        if "text" in payload:
            print(payload["text"])
        else:
            print(payload)


def cmd_list(data: dict[str, Any], as_json: bool = False) -> int:
    sections_payload: dict[str, Any] = {}
    lines: list[str] = []
    for section in sorted(SECTIONS):
        cfg = data.get(section, {})
        sources = cfg.get("sources", []) if isinstance(cfg, dict) else []
        lines.append(f"[{section}] {len(sources)} source(s)")
        section_rows = []
        for idx, src in enumerate(sources, start=1):
            name = src.get("name", "<unnamed>")
            src_type = src.get("type", "<unknown>")
            url = src.get("url", "")
            parser = src.get("parser", "")
            suffix = f", parser={parser}" if parser else ""
            lines.append(f"  {idx}. {name} ({src_type}{suffix}) -> {url}")
            section_rows.append({"name": name, "type": src_type, "url": url, "parser": parser})
        sections_payload[section] = section_rows
    _emit({"status": "ok", "sections": sections_payload, "text": "\n".join(lines)}, as_json)
    return 0


def cmd_add(data: dict[str, Any], args: argparse.Namespace, as_json: bool = False) -> int:
    if args.section not in SECTIONS:
        raise ValueError(f"Invalid section: {args.section}")

    bucket = data.setdefault(args.section, {})
    sources = bucket.setdefault("sources", [])

    for src in sources:
        if str(src.get("name", "")).strip() == args.name.strip():
            raise ValueError(f"Source already exists in {args.section}: {args.name}")

    item: dict[str, Any] = {
        "name": args.name,
        "type": args.type,
        "url": args.url,
    }
    if args.parser:
        item["parser"] = args.parser
    sources.append(item)
    _emit(
        {
            "status": "ok",
            "action": "add",
            "section": args.section,
            "source": item,
            "text": f"Added source '{args.name}' to section '{args.section}'.",
        },
        as_json,
    )
    return 0


def cmd_remove(data: dict[str, Any], args: argparse.Namespace, as_json: bool = False) -> int:
    if args.section not in SECTIONS:
        raise ValueError(f"Invalid section: {args.section}")

    bucket = data.get(args.section, {})
    sources = bucket.get("sources", []) if isinstance(bucket, dict) else []
    before = len(sources)
    sources[:] = [src for src in sources if str(src.get("name", "")).strip() != args.name.strip()]
    if len(sources) == before:
        _emit(
            {
                "status": "not_found",
                "action": "remove",
                "section": args.section,
                "name": args.name,
                "text": f"No source removed (name not found): {args.name}",
            },
            as_json,
        )
        return 1
    _emit(
        {
            "status": "ok",
            "action": "remove",
            "section": args.section,
            "name": args.name,
            "text": f"Removed source '{args.name}' from section '{args.section}'.",
        },
        as_json,
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Manage source pipelines for Milan briefing")
    p.add_argument("--config", default=DEFAULT_CONFIG, help="Config YAML path")
    p.add_argument("--json", action="store_true", help="Print machine-readable JSON output")

    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="List all sections and sources")

    pa = sub.add_parser("add", help="Add a source")
    pa.add_argument("--section", required=True, help="One of strikes/italian_news/world_news/ai_news/milan_events")
    pa.add_argument("--name", required=True, help="Source display name")
    pa.add_argument("--type", required=True, choices=["rss", "json", "html"], help="Source type")
    pa.add_argument("--url", required=True, help="Source URL")
    pa.add_argument("--parser", default="", help="Parser key for json source")

    pr = sub.add_parser("remove", help="Remove a source by exact name")
    pr.add_argument("--section", required=True, help="Section name")
    pr.add_argument("--name", required=True, help="Exact source name")

    return p


def main() -> int:
    args = build_parser().parse_args()
    cfg_path = Path(args.config)
    data = _load(cfg_path)

    if args.command == "list":
        return cmd_list(data, as_json=args.json)
    if args.command == "add":
        code = cmd_add(data, args, as_json=args.json)
        _save(cfg_path, data)
        return code
    if args.command == "remove":
        code = cmd_remove(data, args, as_json=args.json)
        if code == 0:
            _save(cfg_path, data)
        return code

    raise RuntimeError("Unknown command")


if __name__ == "__main__":
    raise SystemExit(main())
