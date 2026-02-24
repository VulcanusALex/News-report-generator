from __future__ import annotations

import hashlib


def dedupe_key(title: str, url: str, source: str) -> str:
    raw = f"{title.strip().lower()}||{url.strip()}||{source.strip().lower()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
