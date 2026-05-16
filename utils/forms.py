from __future__ import annotations

from urllib.parse import urlsplit

from flask import request, url_for

from services.catalog import initials_from_name, now_iso, slug_from_name, unique_slug
from utils.converters import to_float, to_int


def form_text(name: str, default: str = "") -> str:
    value = request.form.get(name, default)
    if value is None:
        return default
    return value.strip()


def site_from_form(existing_site: dict | None = None) -> dict:
    existing_site = existing_site or {}
    category_slugs = [
        slug.strip()
        for slug in request.form.getlist("categories")
        if slug.strip()
    ]
    if not category_slugs:
        category_slugs = [form_text("category")]
    category_slugs = [slug for slug in dict.fromkeys(category_slugs) if slug]

    name = form_text("name")
    return {
        "name": name,
        "version": form_text("version") or "官网",
        "url": form_text("url"),
        "description": form_text("description"),
        "category": category_slugs[0] if category_slugs else "",
        "categories": category_slugs,
        "tags": existing_site.get("tags", []),
        "rating": to_float(form_text("rating"), 4.5),
        "visits": to_int(str(existing_site.get("visits", 0)), 0),
        "added_at": existing_site.get("added_at") or now_iso(),
        "updated_at": now_iso(),
        "logo_text": form_text("logo_text")[:3] or initials_from_name(name),
        "logo_color": form_text("logo_color") or "#2563eb",
        "recommended": request.form.get("recommended") == "on",
    }


def category_from_form(
    existing_category: dict | None = None,
    categories: list[dict] | None = None,
    current_index: int | None = None,
) -> dict:
    existing_category = existing_category or {}
    categories = categories or []
    name = form_text("name")
    slug = existing_category.get("slug") or unique_slug(
        slug_from_name(name),
        categories,
        current_index,
    )

    return {
        "name": name,
        "slug": slug,
        "icon": name[:1] or "分",
    }


def safe_next_url(default_endpoint: str = "admin_dashboard") -> str:
    next_url = request.args.get("next", "")
    if next_url:
        parsed = urlsplit(next_url)
        if not parsed.scheme and not parsed.netloc and next_url.startswith("/"):
            return next_url

    return url_for(default_endpoint)


def selected_indexes_from_form(max_length: int) -> list[int]:
    indexes: list[int] = []
    for value in request.form.getlist("selected"):
        try:
            index = int(value)
        except ValueError:
            continue

        if 0 <= index < max_length:
            indexes.append(index)

    return sorted(set(indexes))
