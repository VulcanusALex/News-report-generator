#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def main() -> int:
    parser = argparse.ArgumentParser(description="Check configured feeds/APIs health")
    parser.add_argument("--config", default="config/sources.yaml", help="Config YAML path")
    parser.add_argument("--timeout", type=int, default=12, help="Per-source timeout seconds")
    parser.add_argument("--write-report", default="", help="Optional report JSON output path")
    args = parser.parse_args()

    root = repo_root()
    sys.path.insert(0, str(root))
    from src.news_briefing.health import check_config_sources, load_yaml  # noqa: E402

    cfg = load_yaml(root / args.config)
    report = check_config_sources(cfg, timeout=max(1, args.timeout))
    text = json.dumps(report, ensure_ascii=False, indent=2)
    print(text)

    if args.write_report:
        out = root / args.write_report
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")

    return 0 if report["summary"]["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
