#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib import request


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Daily operations wrapper: run briefing with retry, logs, and webhook alerts."
    )
    p.add_argument("--date", default="", help="Report date in YYYY-MM-DD")
    p.add_argument("--config", default="config/sources.yaml", help="Config path")
    p.add_argument("--layout", default="", choices=["classic", "editorial", "brief"], help="Render layout")
    p.add_argument("--section-order", default="", help="Comma separated section order")
    p.add_argument("--output-format", default="markdown", choices=["markdown", "json", "both"], help="Output format")
    p.add_argument("--precheck-timeout", type=int, default=12, help="Per-source precheck timeout")
    p.add_argument("--skip-precheck", action="store_true", help="Skip source health precheck")
    p.add_argument("--auto-degrade", action="store_true", help="Auto build degraded config from precheck result")
    p.add_argument("--max-retries", type=int, default=2, help="Retries after first failure")
    p.add_argument("--retry-delay", type=int, default=120, help="Seconds between retries")
    p.add_argument("--alert-webhook", default="", help="Webhook URL for alerts")
    p.add_argument("--alert-success", action="store_true", help="Send webhook on success too")
    p.add_argument("--dry-run", action="store_true", help="Run briefing in dry-run mode")
    p.add_argument(
        "--print-cron",
        action="store_true",
        help="Print cron line for daily run and exit",
    )
    p.add_argument("--cron-hour", type=int, default=7, help="Hour for cron example")
    p.add_argument("--cron-minute", type=int, default=0, help="Minute for cron example")
    return p


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def run_once(args: argparse.Namespace, log_file: Path, config_path: str) -> tuple[int, str]:
    root = repo_root()
    cmd = [
        sys.executable,
        "skills/milan-news-briefing/scripts/run_briefing.py",
        "--config",
        config_path,
    ]
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

    started = datetime.now().isoformat(timespec="seconds")
    header = f"[{started}] command: {' '.join(cmd)}\n"
    proc = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True)
    output = header + "\n[stdout]\n" + proc.stdout + "\n[stderr]\n" + proc.stderr + "\n"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open("a", encoding="utf-8") as f:
        f.write(output)
    return proc.returncode, output


def send_webhook(url: str, payload: dict[str, Any]) -> None:
    if not url:
        return
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(url=url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    with request.urlopen(req, timeout=12):
        return


def build_cron_line(hour: int, minute: int) -> str:
    root = repo_root()
    runner = root / "skills/milan-news-briefing/scripts/daily_ops.py"
    py = sys.executable
    return f'{minute} {hour} * * * cd "{root}" && "{py}" "{runner}" >> "{root}/output/logs/cron.log" 2>&1'


def main() -> int:
    args = build_parser().parse_args()
    if args.print_cron:
        print(build_cron_line(args.cron_hour, args.cron_minute))
        return 0

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_file = repo_root() / "output" / "logs" / f"daily-ops-{ts}.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    attempts = 1 + max(args.max_retries, 0)
    last_output = ""
    health_summary: dict[str, Any] | None = None
    runtime_config = args.config

    if not args.skip_precheck:
        sys.path.insert(0, str(repo_root()))
        from src.news_briefing.health import build_degraded_config, check_config_sources, dump_yaml, load_yaml  # noqa: E402

        cfg_path = repo_root() / args.config
        cfg = load_yaml(cfg_path)
        report = check_config_sources(cfg, timeout=max(1, args.precheck_timeout))
        health_summary = report["summary"]
        with log_file.open("a", encoding="utf-8") as f:
            f.write("[precheck]\n")
            f.write(json.dumps(report, ensure_ascii=False, indent=2))
            f.write("\n")
        if args.auto_degrade and report["summary"]["failed"] > 0:
            degraded = build_degraded_config(cfg, report)
            runtime_path = repo_root() / "output" / "runtime_configs" / f"degraded-{ts}.yaml"
            dump_yaml(runtime_path, degraded)
            runtime_config = str(runtime_path.relative_to(repo_root()))

    for attempt in range(1, attempts + 1):
        code, output = run_once(args, log_file, config_path=runtime_config)
        last_output = output
        if code == 0:
            message = {
                "status": "success",
                "attempt": attempt,
                "attempts_total": attempts,
                "log_file": str(log_file),
                "date": args.date or "",
                "config_used": runtime_config,
                "precheck": health_summary,
            }
            print(json.dumps(message, ensure_ascii=False))
            if args.alert_success and args.alert_webhook:
                send_webhook(args.alert_webhook, message)
            return 0

        if attempt < attempts:
            time.sleep(max(args.retry_delay, 0))

    fail_msg = {
        "status": "failed",
        "attempt": attempts,
        "attempts_total": attempts,
        "log_file": str(log_file),
        "date": args.date or "",
        "config_used": runtime_config,
        "precheck": health_summary,
        "tail": last_output[-1500:],
    }
    print(json.dumps(fail_msg, ensure_ascii=False))
    if args.alert_webhook:
        try:
            send_webhook(args.alert_webhook, fail_msg)
        except Exception:
            pass
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
