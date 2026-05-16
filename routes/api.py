from __future__ import annotations

from datetime import datetime

from flask import request, url_for

from services.catalog import (
    add_category_display_data,
    categories_with_counts,
    default_software_slug,
    indexed_sites,
    load_catalog,
    primary_category_slug,
    selected_hero_sites,
    site_category_slugs,
)
from services.search import filter_sites
from utils.converters import to_int
from utils.formatters import compact_count, updated_label


def most_visited_sites(sites: list[dict], limit: int | None = None) -> list[dict]:
    sorted_sites = sorted(
        sites,
        key=lambda site: to_int(str(site.get("visits", 0)), 0),
        reverse=True,
    )
    return sorted_sites if limit is None else sorted_sites[:limit]


def latest_sites_for_home(
    sites: list[dict],
    query: str,
    default_category: str = "",
) -> list[dict]:
    if query:
        return sites[:12]

    if default_category:
        return [
            site
            for site in sites
            if default_category in site_category_slugs(site)
        ]

    return sites


def recently_added_sites(sites: list[dict], limit: int = 6) -> list[dict]:
    def added_timestamp(site: dict) -> float:
        value = str(site.get("added_at", "")).strip()
        if not value:
            return 0
        try:
            return datetime.fromisoformat(value).timestamp()
        except ValueError:
            return 0

    return sorted(
        sites,
        key=added_timestamp,
        reverse=True,
    )[:limit]


def recommended_sites_for_home(sites: list[dict]) -> list[dict]:
    return [site for site in sites if site.get("recommended")]


def serialize_site(site: dict, include_categories: bool = False) -> dict:
    data = {
        "index": site["_index"],
        "name": site.get("name", ""),
        "version": site.get("version", "Web"),
        "description": site.get("description", ""),
        "tags": site.get("tags", []),
        "visits": to_int(str(site.get("visits", 0)), 0),
        "visits_label": compact_count(site.get("visits", 0)),
        "updated_label": updated_label(site.get("added_at") or site.get("updated_at")),
        "visit_url": url_for("visit_site", site_index=site["_index"]),
        "favicon_url": site.get("_favicon_url", ""),
        "logo_text": site.get("_logo_text", ""),
        "logo_color": site.get("logo_color", "#2563eb"),
        "category": primary_category_slug(site),
        "categories": site_category_slugs(site),
    }
    if include_categories:
        data["category_names"] = site.get("_category_names", [])
    return data


def register_api_routes(app):
    @app.route("/api/categories")
    def api_categories():
        catalog = load_catalog()
        categories = categories_with_counts(catalog["categories"], catalog["sites"])
        return {
            "categories": categories,
            "default_category": default_software_slug(categories),
        }

    @app.route("/api/home")
    def api_home():
        catalog = load_catalog()
        query = request.args.get("q", "").strip()
        all_sites = indexed_sites(catalog["sites"])
        categories = categories_with_counts(catalog["categories"], catalog["sites"])
        default_category = default_software_slug(categories)
        default_category_info = next(
            (category for category in categories if category["slug"] == default_category),
            None,
        )
        sites = filter_sites(all_sites, query=query, categories=catalog["categories"])
        latest_sites = latest_sites_for_home(sites, query, default_category)
        popular_sites = most_visited_sites(all_sites, limit=5)
        recommended_sites = recommended_sites_for_home(all_sites)

        return {
            "query": query,
            "result_count": len(sites),
            "latest_sites": [serialize_site(site) for site in latest_sites],
            "recent_sites": [serialize_site(site) for site in recently_added_sites(all_sites)],
            "popular_sites": [serialize_site(site) for site in popular_sites],
            "recommended_sites": [serialize_site(site) for site in recommended_sites],
            "hero_sites": [
                serialize_site(site)
                for site in selected_hero_sites(catalog["settings"], catalog["sites"])
            ],
            "default_category": default_category,
            "default_category_name": (default_category_info or {}).get("name", ""),
            "default_category_count": (default_category_info or {}).get("count", 0),
        }

    @app.route("/api/category/<slug>")
    def api_category(slug: str):
        catalog = load_catalog()
        categories = categories_with_counts(catalog["categories"], catalog["sites"])
        category_info = next((item for item in categories if item["slug"] == slug), None)
        if category_info is None:
            return {"error": "category not found"}, 404

        sites = filter_sites(
            indexed_sites(catalog["sites"]),
            category=slug,
            categories=catalog["categories"],
        )

        return {
            "category": category_info,
            "sites": [serialize_site(site) for site in sites],
        }

    @app.route("/api/rankings")
    def api_rankings():
        catalog = load_catalog()
        sites = most_visited_sites(
            add_category_display_data(
                indexed_sites(catalog["sites"]),
                catalog["categories"],
            )
        )
        return {"sites": [serialize_site(site, include_categories=True) for site in sites]}

    @app.route("/api/stats")
    def api_stats():
        catalog = load_catalog()
        return {
            "sites": [
                {
                    "index": index,
                    "visits": to_int(str(site.get("visits", 0)), 0),
                    "visits_label": compact_count(site.get("visits", 0)),
                }
                for index, site in enumerate(catalog["sites"])
            ],
            "categories": [
                {
                    "slug": category["slug"],
                    "count": category["count"],
                }
                for category in categories_with_counts(catalog["categories"], catalog["sites"])
            ],
        }

    @app.route("/api/search")
    def api_search():
        catalog = load_catalog()
        query = request.args.get("q", "").strip()
        category_slug = request.args.get("category", "").strip() or None
        results = filter_sites(
            indexed_sites(catalog["sites"]),
            category=category_slug,
            query=query,
            categories=catalog["categories"],
        )[:10]

        return {
            "results": [
                {
                    "name": site["name"],
                    "description": site["description"],
                    "category": primary_category_slug(site),
                    "categories": site_category_slugs(site),
                    "visits": to_int(str(site.get("visits", 0)), 0),
                    "url": url_for("visit_site", site_index=site["_index"]),
                    "icon": site.get("_favicon_url", ""),
                    "logo_text": site.get("_logo_text", ""),
                }
                for site in results
            ]
        }


