from __future__ import annotations

from services.catalog import site_category_slugs, slug_from_name, unique_slug
from utils.urls import is_http_url


def normalize_imported_categories(imported_data: list[dict]) -> list[dict]:
    normalized: list[dict] = []
    for item in imported_data:
        category = dict(item)
        name = str(category.get("name", "")).strip()
        existing_slug = str(category.get("slug", "")).strip()
        category["name"] = name
        category["slug"] = unique_slug(existing_slug or slug_from_name(name), normalized)
        category["icon"] = str(category.get("icon", "")).strip() or name[:1] or "分"
        normalized.append(category)

    return normalized


def normalize_imported_sites(imported_data: list[dict]) -> list[dict]:
    normalized: list[dict] = []
    for item in imported_data:
        site = dict(item)
        slugs = site_category_slugs(site)
        site["category"] = slugs[0] if slugs else ""
        site["categories"] = slugs
        normalized.append(site)

    return normalized


def validate_import_data(target: str, data) -> tuple[bool, str]:
    if not isinstance(data, list):
        return False, "JSON 顶层必须是数组。"

    required_fields = {
        "sites": {"name", "url", "description"},
        "categories": {"name"},
    }
    missing_fields = required_fields[target]

    for index, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            return False, f"第 {index} 项必须是对象。"

        missing = [field for field in missing_fields if not item.get(field)]
        if target == "sites" and not item.get("category") and not item.get("categories"):
            missing.append("category/categories")
        if not missing and target == "sites" and not is_http_url(str(item.get("url", ""))):
            return False, f"第 {index} 项的 URL 必须是 http:// 或 https:// 开头的有效地址。"
        if missing:
            return False, f"第 {index} 项缺少字段：{', '.join(missing)}。"

    return True, ""
