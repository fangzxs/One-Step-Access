from __future__ import annotations

from datetime import datetime

from utils.converters import to_int

def compact_count(value: int | str | None) -> str:
    count = to_int(str(value) if value is not None else None, 0)
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M".replace(".0M", "M")
    if count >= 1_000:
        return f"{count / 1_000:.1f}K".replace(".0K", "K")
    return str(count)


def updated_label(value: str | None) -> str:
    if not value:
        return "刚刚"

    try:
        updated_at = datetime.fromisoformat(value)
    except ValueError:
        return value

    if updated_at.tzinfo is None:
        now = datetime.now()
    else:
        now = datetime.now(updated_at.tzinfo).astimezone(updated_at.tzinfo)
    seconds = max(0, int((now - updated_at).total_seconds()))

    if seconds < 60:
        return "刚刚"
    if seconds < 3600:
        return f"{seconds // 60} 分钟前"
    if seconds < 86400:
        return f"{seconds // 3600} 小时前"
    if seconds < 172800:
        return "昨天"
    if seconds < 604800:
        return f"{seconds // 86400} 天前"
    return updated_at.strftime("%Y-%m-%d")

