#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


CRON_TAG = "# milan-news-briefing-daily-ops"
CRON_TZ_TAG = "# milan-news-briefing-timezone"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def build_cron_line(
    hour: int,
    minute: int,
    webhook: str = "",
    retries: int = 2,
    delay: int = 180,
    layout: str = "",
    section_order: str = "",
    output_format: str = "markdown",
) -> str:
    root = repo_root()
    py = sys.executable
    script = root / "skills/milan-news-briefing/scripts/daily_ops.py"
    cmd = (
        f'cd "{root}" && "{py}" "{script}" --auto-degrade --max-retries {retries} --retry-delay {delay}'
    )
    if layout:
        cmd += f" --layout {layout}"
    if section_order:
        cmd += f' --section-order "{section_order}"'
    if output_format:
        cmd += f" --output-format {output_format}"
    if webhook:
        cmd += f' --alert-webhook "{webhook}"'
    cmd += f' >> "{root}/output/logs/cron.log" 2>&1'
    return f"{minute} {hour} * * * {cmd} {CRON_TAG}"


def build_cron_tz_line(timezone: str) -> str:
    return f"CRON_TZ={timezone} {CRON_TZ_TAG}"


def read_crontab() -> list[str]:
    proc = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    if proc.returncode != 0:
        return []
    return proc.stdout.splitlines()


def write_crontab(lines: list[str]) -> int:
    payload = "\n".join(lines).strip() + "\n"
    proc = subprocess.run(["crontab", "-"], input=payload, text=True)
    return proc.returncode


def _print(payload: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False))
    else:
        if payload.get("timezone_line") and payload.get("line"):
            print(payload["timezone_line"])
            print(payload["line"])
        elif payload.get("line"):
            print(payload["line"])
        elif payload.get("timezone_line"):
            print(payload["timezone_line"])
        else:
            print(payload.get("message", ""))


def cmd_show(as_json: bool = False) -> int:
    lines = read_crontab()
    tagged = [x for x in lines if CRON_TAG in x]
    tz_tagged = [x for x in lines if CRON_TZ_TAG in x]
    if not tagged:
        _print({"status": "not_found", "message": "No managed cron entry found."}, as_json)
        return 1
    payload = {
        "status": "ok",
        "timezone_line": tz_tagged[-1] if tz_tagged else "",
        "line": tagged[-1],
    }
    _print(payload, as_json)
    return 0


def cmd_install(args: argparse.Namespace, as_json: bool = False) -> int:
    if not (0 <= args.hour <= 23):
        raise ValueError("hour must be in 0..23")
    if not (0 <= args.minute <= 59):
        raise ValueError("minute must be in 0..59")
    lines = read_crontab()
    lines = [x for x in lines if CRON_TAG not in x and CRON_TZ_TAG not in x]
    tz_line = build_cron_tz_line(args.timezone)
    job_line = build_cron_line(
        hour=args.hour,
        minute=args.minute,
            webhook=args.webhook,
            retries=args.max_retries,
            delay=args.retry_delay,
            layout=args.layout,
            section_order=args.section_order,
            output_format=args.output_format,
        )
    lines.extend([tz_line, job_line])
    rc = write_crontab(lines)
    payload = {
        "status": "ok" if rc == 0 else "error",
        "timezone_line": tz_line,
        "line": job_line,
    }
    _print(payload, as_json)
    return rc


def cmd_remove(as_json: bool = False) -> int:
    lines = read_crontab()
    new_lines = [x for x in lines if CRON_TAG not in x and CRON_TZ_TAG not in x]
    if len(new_lines) == len(lines):
        _print({"status": "not_found", "message": "No managed cron entry to remove."}, as_json)
        return 1
    rc = write_crontab(new_lines)
    _print({"status": "ok" if rc == 0 else "error", "message": "Managed cron entry removed."}, as_json)
    return rc


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Install/show/remove managed cron for Milan briefing")
    p.add_argument("--json", action="store_true", help="Print machine-readable JSON output")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("show", help="Show managed cron entry")

    pin = sub.add_parser("install", help="Install or replace managed cron entry")
    pin.add_argument("--hour", type=int, default=7, help="0-23")
    pin.add_argument("--minute", type=int, default=0, help="0-59")
    pin.add_argument("--timezone", default="Europe/Rome", help="Cron timezone, e.g. Europe/Rome")
    pin.add_argument("--webhook", default="", help="Webhook URL for alerts")
    pin.add_argument("--max-retries", type=int, default=2, help="Retry count")
    pin.add_argument("--retry-delay", type=int, default=180, help="Retry delay seconds")
    pin.add_argument("--layout", default="", choices=["classic", "editorial", "brief"], help="Render layout")
    pin.add_argument("--section-order", default="", help="Comma separated section order")
    pin.add_argument("--output-format", default="markdown", choices=["markdown", "json", "both"], help="Output format")

    sub.add_parser("remove", help="Remove managed cron entry")
    return p


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "show":
        return cmd_show(as_json=args.json)
    if args.command == "install":
        return cmd_install(args, as_json=args.json)
    if args.command == "remove":
        return cmd_remove(as_json=args.json)
    raise RuntimeError("unknown command")


if __name__ == "__main__":
    raise SystemExit(main())
