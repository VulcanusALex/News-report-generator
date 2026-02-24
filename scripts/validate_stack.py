#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def run(cmd: list[str], cwd: Path, env: dict[str, str] | None = None) -> int:
    print("$", " ".join(cmd))
    proc = subprocess.run(cmd, cwd=str(cwd), env=env)
    return proc.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Milan briefing stack")
    parser.add_argument("--skip-network", action="store_true", help="Skip feed health check")
    args = parser.parse_args()

    root = repo_root()
    py = sys.executable
    rc = 0
    env = os.environ.copy()
    env["PYTHONPYCACHEPREFIX"] = str(root / ".pycache")

    rc |= run([py, "-m", "py_compile", *[str(p) for p in (root / "src/news_briefing").glob("*.py")]], root, env=env)
    rc |= run(
        [py, "-m", "py_compile", *[str(p) for p in (root / "skills/milan-news-briefing/scripts").glob("*.py")]],
        root,
        env=env,
    )
    rc |= run([py, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"], root, env=env)

    if not args.skip_network:
        rc |= run([py, "skills/milan-news-briefing/scripts/check_feeds.py", "--timeout", "8"], root, env=env)

    return 1 if rc else 0


if __name__ == "__main__":
    raise SystemExit(main())
