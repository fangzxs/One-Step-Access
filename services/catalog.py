from __future__ import annotations

import json
import re
import shutil
from contextlib import contextmanager
from datetime import datetime
from functools import lru_cache
from hashlib import sha1
from pathlib import Path
from threading import Lock
from urllib.parse import urlparse

import config
from utils.converters import to_int

_write_lock = Lock()


@contextmanager
def write_catalog():
    """上下文管理器，保证读-改-写操作的原子性，防止并发写导致数据丢失。"""
    with _write_lock:
        load_catalog.cache_clear()
        yield


def _read_json(filename: str):
    path = config.DATA_DIR / filename
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _backup_json(path: Path) -> None:
    if not config.ENABLE_DATA_BACKUPS or not path.exists():
        return

    config.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup_path = config.BACKUP_DIR / f"{path.stem}-{timestamp}{path.suffix}"
    shutil.copy2(path, backup_path)

    backups = sorted(
        config.BACKUP_DIR.glob(f"{path.stem}-*{path.suffix}"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    for old_backup in backups[config.BACKUP_KEEP_PER_FILE:]:
        old_backup.unlink(missing_ok=True)


def _write_json(filename: str, data, backup: bool = True) -> None:
    path = config.DATA_DIR / filename
    if backup:
        _backup_json(path)

    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def clean_site(site: dict) -> dict:
    return {key: value for key, value in site.items() if not key.startswith("_")}


def site_category_slugs(site: dict) -> list[str]:
    raw_categories = site.get("categories")
    values = raw_categories if isinstance(raw_categories, list) else [site.get("category", "")]

    slugs: list[str] = []
    for value in values:
        slug = str(value or "").strip()
        if slug and slug not in slugs:
            slugs.append(slug)
    return slugs


def primary_category_slug(site: dict) -> str:
    slugs = site_category_slugs(site)
    return slugs[0] if slugs else ""


def initials_from_name(name: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", name)
    if len(words) >= 2:
        return "".join(word[0] for word in words[:2]).upper()
    if words:
        return words[0][:2].upper()
    return name[:2] or "S"


def favicon_url(site_url: str) -> str:
    parsed = urlparse(site_url if "://" in site_url else f"https://{site_url}")
    domain = parsed.netloc or parsed.path
    if not domain:
        return ""
    return f"https://www.google.com/s2/favicons?domain={domain}&sz=64"


def site_icon_data(site: dict) -> dict:
    logo_text = str(site.get("logo_text") or "").strip()
    return {
        "_logo_text": (logo_text or initials_from_name(str(site.get("name", ""))))[:3],
        "_favicon_url": favicon_url(str(site.get("url", ""))),
    }


def indexed_sites(sites: list[dict]) -> list[dict]:
    return [
        {**site, "_index": index, **site_icon_data(site)}
        for index, site in enumerate(sites)
    ]


def category_name_map(categories: list[dict]) -> dict[str, str]:
    return {
        category.get("slug", ""): category.get("name", "")
        for category in categories
    }


def add_category_display_data(sites: list[dict], categories: list[dict]) -> list[dict]:
    names_by_slug = category_name_map(categories)
    return [
        {
            **site,
            "_category_slugs": site_category_slugs(site),
            "_category_names": [
                names_by_slug.get(slug, slug)
                for slug in site_category_slugs(site)
            ],
        }
        for site in sites
    ]


def category_counts(sites: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for site in sites:
        for slug in site_category_slugs(site):
            counts[slug] = counts.get(slug, 0) + 1
    return counts


def categories_with_counts(categories: list[dict], sites: list[dict]) -> list[dict]:
    counts = category_counts(sites)
    return [
        {
            **category,
            "icon": category.get("icon") or category.get("name", "分")[:1],
            "count": counts.get(category.get("slug", ""), 0),
        }
        for category in categories
    ]


def default_software_slug(categories: list[dict]) -> str:
    if not categories:
        return ""

    common_category = next(
        (category for category in categories if category.get("name") == "常用软件"),
        None,
    )
    return (common_category or categories[0]).get("slug", "")


def slug_from_name(name: str) -> str:
    ascii_slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    if ascii_slug:
        return ascii_slug
    return f"cat-{sha1(name.encode('utf-8')).hexdigest()[:8]}"


def unique_slug(
    base_slug: str,
    categories: list[dict],
    current_index: int | None = None,
) -> str:
    used_slugs = {
        category["slug"]
        for index, category in enumerate(categories)
        if index != current_index and category.get("slug")
    }
    slug = base_slug or "category"
    candidate = slug
    suffix = 2
    while candidate in used_slugs:
        candidate = f"{slug}-{suffix}"
        suffix += 1
    return candidate


@lru_cache(maxsize=1)
def load_catalog() -> dict:
    return {
        "categories": _read_json("categories.json"),
        "sites": _read_json("sites.json"),
        "settings": _read_json("settings.json"),
    }


def save_sites(sites: list[dict], backup: bool = True) -> None:
    _write_json("sites.json", [clean_site(site) for site in sites], backup=backup)
    load_catalog.cache_clear()


def save_categories(categories: list[dict]) -> None:
    _write_json("categories.json", categories)
    load_catalog.cache_clear()


def save_settings(settings: dict) -> None:
    _write_json("settings.json", settings)
    load_catalog.cache_clear()


def selected_hero_sites(settings: dict, sites: list[dict]) -> list[dict]:
    indexed = indexed_sites(sites)
    selected: list[dict] = []

    for value in settings.get("hero_site_indexes", []):
        index = to_int(str(value), -1)
        if 0 <= index < len(indexed):
            selected.append(indexed[index])

    if selected:
        return selected[:4]

    recommended = [site for site in indexed if site.get("recommended")]
    fallback = recommended or sorted(
        indexed,
        key=lambda site: to_int(str(site.get("visits", 0)), 0),
        reverse=True,
    )
    return fallback[:4]
