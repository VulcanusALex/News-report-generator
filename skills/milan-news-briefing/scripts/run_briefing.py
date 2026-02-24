#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Milan daily briefing pipeline")
    parser.add_argument("--date", default="", help="Report date in YYYY-MM-DD")
    parser.add_argument("--config", default="config/sources.yaml", help="Config path")
    parser.add_argument("--dry-run", action="store_true", help="Do not persist outputs")
    parser.add_argument("--layout", default="", choices=["classic", "editorial", "brief"], help="Render layout")
    parser.add_argument("--section-order", default="", help="Comma separated section order")
    parser.add_argument("--output-format", default="markdown", choices=["markdown", "json", "both"], help="Output format")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[3]
    cmd = [sys.executable, "-m", "src.news_briefing.main", "--config", args.config]
    if args.date:
        cmd.extend(["--date", args.date])
    if args.dry_run:
        cmd.append("--dry-run")
    if args.layout:
        cmd.extend(["--layout", args.layout])
    if args.section_order:
        cmd.extend(["--section-order", args.section_order])
    if args.output_format:
        cmd.extend(["--output-format", args.output_format])

    return subprocess.call(cmd, cwd=str(root))


if __name__ == "__main__":
    raise SystemExit(main())
