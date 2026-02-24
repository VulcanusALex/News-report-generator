from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import request

import yaml


NEWS_SECTIONS = ("italian_news", "world_news", "ai_news", "milan_events")


@dataclass
class SourceCheckResult:
    section: str
    name: str
    type: str
    url: str
    ok: bool
    detail: str
    status_code: int | None = None


def load_yaml(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    with p.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def dump_yaml(path: str | Path, data: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)


def check_config_sources(cfg: dict[str, Any], timeout: int = 12) -> dict[str, Any]:
    results: list[SourceCheckResult] = []
    for section in ("strikes",) + NEWS_SECTIONS:
        section_cfg = cfg.get(section, {})
        sources = section_cfg.get("sources", []) if isinstance(section_cfg, dict) else []
        for src in sources:
            if not isinstance(src, dict):
                continue
            name = str(src.get("name", "unknown"))
            src_type = str(src.get("type", "unknown"))
            url = str(src.get("url", "")).strip()
            if not url:
                results.append(
                    SourceCheckResult(section, name, src_type, url, False, "empty_url", None)
                )
                continue
            results.append(_check_one(section, name, src_type, url, timeout))

    summary = _summarize(results)
    return {
        "summary": summary,
        "results": [r.__dict__ for r in results],
    }


def build_degraded_config(cfg: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    out = json.loads(json.dumps(cfg))
    health_map: dict[tuple[str, str, str], bool] = {}
    for r in report.get("results", []):
        key = (str(r.get("section", "")), str(r.get("name", "")), str(r.get("url", "")))
        health_map[key] = bool(r.get("ok"))

    for section in ("strikes",) + NEWS_SECTIONS:
        section_cfg = out.get(section, {})
        if not isinstance(section_cfg, dict):
            continue
        old_sources = section_cfg.get("sources", [])
        if not isinstance(old_sources, list):
            continue
        new_sources = []
        for src in old_sources:
            if not isinstance(src, dict):
                continue
            key = (section, str(src.get("name", "")), str(src.get("url", "")))
            if health_map.get(key, True):
                new_sources.append(src)

        # Keep at least one source if all failed, to avoid fully empty config.
        if not new_sources and old_sources:
            new_sources = [old_sources[0]]
        section_cfg["sources"] = new_sources
    return out


def _check_one(section: str, name: str, src_type: str, url: str, timeout: int) -> SourceCheckResult:
    try:
        req = request.Request(url=url, headers={"User-Agent": "milan-brief-health/1.0"})
        with request.urlopen(req, timeout=timeout) as resp:
            code = int(getattr(resp, "status", 200))
            body = resp.read(2048)
            ok, detail = _validate_payload(src_type, body)
            return SourceCheckResult(section, name, src_type, url, ok and code < 400, detail, code)
    except Exception as exc:
        return SourceCheckResult(section, name, src_type, url, False, f"fetch_error:{exc.__class__.__name__}")


def _validate_payload(src_type: str, body: bytes) -> tuple[bool, str]:
    text = body.decode("utf-8", errors="ignore").lstrip().lower()
    if src_type == "rss":
        if "<rss" in text or "<feed" in text or text.startswith("<?xml"):
            return True, "rss_like"
        return False, "not_rss_like"
    if src_type == "json":
        if text.startswith("{") or text.startswith("["):
            return True, "json_like"
        return False, "not_json_like"
    if src_type == "html":
        if "<html" in text or "<table" in text or "<!doctype html" in text:
            return True, "html_like"
        return False, "not_html_like"
    return True, "unknown_type_assumed_ok"


def _summarize(results: list[SourceCheckResult]) -> dict[str, Any]:
    total = len(results)
    ok = sum(1 for r in results if r.ok)
    by_section: dict[str, dict[str, int]] = {}
    for r in results:
        sec = by_section.setdefault(r.section, {"ok": 0, "total": 0})
        sec["total"] += 1
        if r.ok:
            sec["ok"] += 1
    return {
        "total": total,
        "ok": ok,
        "failed": total - ok,
        "by_section": by_section,
    }
