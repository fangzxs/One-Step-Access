from __future__ import annotations

from urllib.parse import urlsplit


def is_http_url(value: str) -> bool:
    parsed = urlsplit(str(value or "").strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
