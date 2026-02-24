from __future__ import annotations

import argparse
import json
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from .config import load_config
from .pipeline import BriefingPipeline


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Generate Milan daily news briefing")
    p.add_argument("--config", default="config/sources.yaml", help="Path to source config YAML")
    p.add_argument("--date", default="", help="Report date, format YYYY-MM-DD")
    p.add_argument("--dry-run", action="store_true", help="Do not persist to disk/database")
    p.add_argument("--layout", default="", choices=["classic", "editorial", "brief"], help="Render layout")
    p.add_argument(
        "--section-order",
        default="",
        help="Comma separated sections, e.g. weather,strikes,ai_news,world_news,italian_news,milan_events",
    )
    p.add_argument("--output-format", default="markdown", choices=["markdown", "json", "both"], help="Stdout format")
    return p


def main() -> int:
    args = build_parser().parse_args()
    cfg = load_config(args.config)
    tz_name = cfg.get("timezone", "Europe/Rome")
    if args.date:
        report_day = datetime.strptime(args.date, "%Y-%m-%d").date()
    else:
        report_day = datetime.now(ZoneInfo(tz_name)).date()

    section_order = [x.strip() for x in args.section_order.split(",") if x.strip()] if args.section_order else None
    pipeline = BriefingPipeline(cfg)
    try:
        brief, markdown, meta = pipeline.generate(
            report_day=report_day,
            dry_run=args.dry_run,
            layout=(args.layout or None),
            section_order=section_order,
        )
    finally:
        pipeline.close()

    if args.output_format in ("markdown", "both"):
        print(markdown)
    if args.output_format in ("json", "both"):
        payload = {
            "brief": _json_ready(brief),
            "meta": _json_ready(meta),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    elif not args.dry_run:
        print("\n[meta]", meta)
    return 0


def _json_ready(value: Any) -> Any:
    if is_dataclass(value):
        return _json_ready(asdict(value))
    if isinstance(value, dict):
        return {k: _json_ready(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_ready(x) for x in value]
    if isinstance(value, datetime):
        return value.isoformat()
    return value


if __name__ == "__main__":
    raise SystemExit(main())
