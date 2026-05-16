from __future__ import annotations

from flask import abort, redirect, render_template

from services.catalog import load_catalog, save_sites, write_catalog
from utils.auth import admin_required
from utils.converters import to_int
from utils.urls import is_http_url


def register_public_routes(app):
    @app.route("/")
    def index():
        return render_template("index.html")


    @app.route("/category/<slug>")
    def category(slug: str):
        if not any(item.get("slug") == slug for item in load_catalog()["categories"]):
            abort(404)

        return render_template("category.html", category_slug=slug)


    @app.route("/rankings")
    def rankings():
        return render_template("rankings.html")


    @app.route("/visit/<int:site_index>")
    def visit_site(site_index: int):
        with write_catalog():
            sites = load_catalog()["sites"]
            if site_index < 0 or site_index >= len(sites):
                abort(404)

            site = sites[site_index]
            if not is_http_url(site.get("url", "")):
                abort(404)
            site["visits"] = to_int(str(site.get("visits", 0)), 0) + 1
            save_sites(sites, backup=False)

        return redirect(site["url"])


    @app.route("/refresh-data")
    @admin_required
    def refresh_data():
        load_catalog.cache_clear()
        return {"status": "ok", "message": "数据缓存已刷新"}


