from __future__ import annotations

import json
import secrets
from urllib.parse import urlsplit, urlunsplit

from flask import Response, abort, flash, redirect, render_template, request, session, url_for

import config
from services.catalog import (
    _write_json,
    add_category_display_data,
    categories_with_counts,
    indexed_sites,
    load_catalog,
    save_categories,
    save_settings,
    save_sites,
    site_category_slugs,
    write_catalog,
)
from services.imports import (
    normalize_imported_categories,
    normalize_imported_sites,
    validate_import_data,
)
from utils.auth import admin_required, validate_csrf
from utils.converters import to_int
from utils.forms import (
    category_from_form,
    form_text,
    safe_next_url,
    selected_indexes_from_form,
    site_from_form,
)
from utils.urls import is_http_url


EXPORT_TARGETS = {
    "sites": "sites.json",
    "categories": "categories.json",
    "settings": "settings.json",
}


def ordered_items_from_form(items: list[dict]) -> list[dict] | None:
    indexes: list[int] = []
    for value in request.form.getlist("order"):
        try:
            indexes.append(int(value))
        except ValueError:
            return None

    if sorted(indexes) != list(range(len(items))):
        return None
    return [items[index] for index in indexes]


def json_download(filename: str, data) -> Response:
    payload = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    response = Response(payload, mimetype="application/json; charset=utf-8")
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return response


def normalize_site_url(value: str) -> str:
    raw_url = str(value or "").strip()
    if not raw_url:
        return ""

    parsed = urlsplit(raw_url if "://" in raw_url else f"https://{raw_url}")
    scheme = (parsed.scheme or "https").lower()
    hostname = (parsed.hostname or "").lower()
    port = parsed.port
    netloc = hostname
    if port and not ((scheme == "http" and port == 80) or (scheme == "https" and port == 443)):
        netloc = f"{hostname}:{port}"

    path = parsed.path.rstrip("/") or "/"
    normalized = urlunsplit((scheme, netloc, path, parsed.query, ""))
    return normalized.rstrip("/")


def url_is_used_by_other_site(
    sites: list[dict],
    url: str,
    current_index: int | None = None,
) -> bool:
    normalized_url = normalize_site_url(url)
    return any(
        index != current_index
        and normalize_site_url(site.get("url", "")) == normalized_url
        for index, site in enumerate(sites)
    )


def register_admin_routes(app):
    @app.before_request
    def protect_admin_posts():
        if request.method == "POST" and request.endpoint and request.endpoint.startswith("admin_"):
            validate_csrf()


    @app.route("/admin/login", methods=["GET", "POST"])
    def admin_login():
        if request.method == "POST":
            username = form_text("username")
            password = form_text("password")
            if secrets.compare_digest(username, config.ADMIN_USERNAME) and secrets.compare_digest(password, config.ADMIN_PASSWORD):
                session["admin_logged_in"] = True
                flash("登录成功。")
                return redirect(safe_next_url())
            flash("账号或密码不正确。")

        return render_template("admin/login.html")


    @app.route("/admin/logout")
    def admin_logout():
        session.clear()
        return redirect(url_for("admin_login"))


    @app.route("/admin")
    @admin_required
    def admin_dashboard():
        catalog = load_catalog()
        return render_template(
            "admin/dashboard.html",
            site_count=len(catalog["sites"]),
            category_count=len(catalog["categories"]),
            recommended_count=len(
                [site for site in catalog["sites"] if site.get("recommended")]
            ),
        )


    @app.route("/admin/sites")
    @admin_required
    def admin_sites():
        catalog = load_catalog()
        sites = add_category_display_data(
            indexed_sites(catalog["sites"]),
            catalog["categories"],
        )
        return render_template("admin/sites.html", sites=sites)


    @app.route("/admin/sites/new", methods=["GET", "POST"])
    @admin_required
    def admin_site_new():
        catalog = load_catalog()
        if request.method == "POST":
            with write_catalog():
                sites = load_catalog()["sites"]
                site = site_from_form()
                if not is_http_url(site["url"]):
                    flash("URL 必须是 http:// 或 https:// 开头的有效地址。")
                    return redirect(url_for("admin_site_new"))
                if url_is_used_by_other_site(sites, site["url"]):
                    flash("这个 URL 已经存在，不能重复添加同一个软件。")
                    return redirect(url_for("admin_site_new"))

                sites.append(site)
                save_sites(sites)
            flash("软件已新增。")
            return redirect(url_for("admin_sites"))

        return render_template(
            "admin/site_form.html",
            title="新增软件",
            site={"_category_slugs": []},
            site_index=None,
            categories=catalog["categories"],
        )


    @app.route("/admin/sites/<int:site_index>/edit", methods=["GET", "POST"])
    @admin_required
    def admin_site_edit(site_index: int):
        catalog = load_catalog()
        sites = catalog["sites"]
        if site_index < 0 or site_index >= len(sites):
            abort(404)

        if request.method == "POST":
            with write_catalog():
                sites = load_catalog()["sites"]
                if site_index < 0 or site_index >= len(sites):
                    abort(404)
                site = site_from_form(sites[site_index])
                if not is_http_url(site["url"]):
                    flash("URL 必须是 http:// 或 https:// 开头的有效地址。")
                    return redirect(url_for("admin_site_edit", site_index=site_index))
                if url_is_used_by_other_site(sites, site["url"], current_index=site_index):
                    flash("这个 URL 已经被其他软件使用，不能保存重复软件。")
                    return redirect(url_for("admin_site_edit", site_index=site_index))

                sites[site_index] = site
                save_sites(sites)
            flash("软件已保存。")
            return redirect(url_for("admin_sites"))

        return render_template(
            "admin/site_form.html",
            title="编辑软件",
            site={
                **sites[site_index],
                "_category_slugs": site_category_slugs(sites[site_index]),
            },
            site_index=site_index,
            categories=catalog["categories"],
        )


    @app.route("/admin/sites/<int:site_index>/delete", methods=["POST"])
    @admin_required
    def admin_site_delete(site_index: int):
        with write_catalog():
            sites = load_catalog()["sites"]
            if site_index < 0 or site_index >= len(sites):
                abort(404)

            deleted = sites.pop(site_index)
            save_sites(sites)
        flash(f"{deleted['name']} 已删除。")
        return redirect(url_for("admin_sites"))


    @app.route("/admin/sites/batch", methods=["POST"])
    @admin_required
    def admin_sites_batch():
        selected_indexes = selected_indexes_from_form(len(load_catalog()["sites"]))
        action = form_text("action")

        if not selected_indexes:
            flash("请先选择要操作的软件。")
            return redirect(url_for("admin_sites"))

        if action not in {"delete", "recommend", "unrecommend"}:
            flash("未知的批量操作。")
            return redirect(url_for("admin_sites"))

        with write_catalog():
            sites = load_catalog()["sites"]
            if action == "delete":
                deleted_count = len(selected_indexes)
                for index in sorted(selected_indexes, reverse=True):
                    sites.pop(index)
                save_sites(sites)
                flash(f"已删除 {deleted_count} 个软件。")
            elif action == "recommend":
                for index in selected_indexes:
                    sites[index]["recommended"] = True
                save_sites(sites)
                flash(f"已将 {len(selected_indexes)} 个软件设为推荐。")
            elif action == "unrecommend":
                for index in selected_indexes:
                    sites[index]["recommended"] = False
                save_sites(sites)
                flash(f"已取消 {len(selected_indexes)} 个软件的推荐。")
        return redirect(url_for("admin_sites"))


    @app.route("/admin/sites/reorder", methods=["POST"])
    @admin_required
    def admin_sites_reorder():
        with write_catalog():
            sites = load_catalog()["sites"]
            ordered_sites = ordered_items_from_form(sites)
            if ordered_sites is None:
                flash("排序数据无效，请刷新页面后重试。")
                return redirect(url_for("admin_sites"))

            save_sites(ordered_sites)
        flash("软件排序已保存。")
        return redirect(url_for("admin_sites"))


    @app.route("/admin/hero", methods=["GET", "POST"])
    @admin_required
    def admin_hero():
        if request.method == "POST":
            with write_catalog():
                catalog = load_catalog()
                sites = add_category_display_data(
                    indexed_sites(catalog["sites"]),
                    catalog["categories"],
                )
                settings = catalog["settings"]
                selected_indexes = selected_indexes_from_form(len(sites))[:4]
                settings["hero_site_indexes"] = selected_indexes
                save_settings(settings)
            flash("首页展示软件已保存。")
            return redirect(url_for("admin_hero"))

        load_catalog.cache_clear()
        catalog = load_catalog()
        sites = add_category_display_data(
            indexed_sites(catalog["sites"]),
            catalog["categories"],
        )
        settings = catalog["settings"]
        selected = {
            to_int(str(value), -1)
            for value in settings.get("hero_site_indexes", [])
        }
        return render_template("admin/hero.html", sites=sites, selected=selected)


    @app.route("/admin/categories")
    @admin_required
    def admin_categories():
        catalog = load_catalog()
        sites = add_category_display_data(
            indexed_sites(catalog["sites"]),
            catalog["categories"],
        )
        sites_by_category = {
            category["slug"]: [
                site for site in sites if category["slug"] in site_category_slugs(site)
            ]
            for category in catalog["categories"]
        }
        return render_template(
            "admin/categories.html",
            categories=categories_with_counts(catalog["categories"], catalog["sites"]),
            sites_by_category=sites_by_category,
        )


    @app.route("/admin/categories/new", methods=["GET", "POST"])
    @admin_required
    def admin_category_new():
        if request.method == "POST":
            with write_catalog():
                categories = load_catalog()["categories"]
                categories.append(category_from_form(categories=categories))
                save_categories(categories)
            flash("分类已新增。")
            return redirect(url_for("admin_categories"))

        return render_template(
            "admin/category_form.html",
            title="新增分类",
            category={},
            category_index=None,
        )


    @app.route("/admin/categories/<int:category_index>/edit", methods=["GET", "POST"])
    @admin_required
    def admin_category_edit(category_index: int):
        categories = load_catalog()["categories"]
        if category_index < 0 or category_index >= len(categories):
            abort(404)

        if request.method == "POST":
            with write_catalog():
                categories = load_catalog()["categories"]
                if category_index < 0 or category_index >= len(categories):
                    abort(404)
                categories[category_index] = category_from_form(
                    existing_category=categories[category_index],
                    categories=categories,
                    current_index=category_index,
                )
                save_categories(categories)
            flash("分类已保存。")
            return redirect(url_for("admin_categories"))

        return render_template(
            "admin/category_form.html",
            title="编辑分类",
            category=categories[category_index],
            category_index=category_index,
        )


    @app.route("/admin/categories/<int:category_index>/delete", methods=["POST"])
    @admin_required
    def admin_category_delete(category_index: int):
        with write_catalog():
            catalog = load_catalog()
            categories = catalog["categories"]
            if category_index < 0 or category_index >= len(categories):
                abort(404)

            category = categories[category_index]
            used_count = len(
                [site for site in catalog["sites"] if category["slug"] in site_category_slugs(site)]
            )
            if used_count:
                flash(f"这个分类下还有 {used_count} 个软件，先移动或删除这些软件后再删除分类。")
                return redirect(url_for("admin_categories"))

            deleted = categories.pop(category_index)
            save_categories(categories)
        flash(f"{deleted['name']} 已删除。")
        return redirect(url_for("admin_categories"))


    @app.route("/admin/categories/batch", methods=["POST"])
    @admin_required
    def admin_categories_batch():
        selected_indexes = selected_indexes_from_form(len(load_catalog()["categories"]))

        if not selected_indexes:
            flash("请先选择要操作的分类。")
            return redirect(url_for("admin_categories"))

        with write_catalog():
            catalog = load_catalog()
            categories = catalog["categories"]

            used_slugs = {
                slug
                for site in catalog["sites"]
                for slug in site_category_slugs(site)
            }
            deletable_indexes = [
                index
                for index in selected_indexes
                if categories[index]["slug"] not in used_slugs
            ]
            blocked_count = len(selected_indexes) - len(deletable_indexes)

            for index in sorted(deletable_indexes, reverse=True):
                categories.pop(index)

            if deletable_indexes:
                save_categories(categories)

            if blocked_count:
                flash(
                    f"已删除 {len(deletable_indexes)} 个分类，另有 {blocked_count} 个分类正在被软件使用，未删除。"
                )
            else:
                flash(f"已删除 {len(deletable_indexes)} 个分类。")

        return redirect(url_for("admin_categories"))


    @app.route("/admin/categories/reorder", methods=["POST"])
    @admin_required
    def admin_categories_reorder():
        with write_catalog():
            categories = load_catalog()["categories"]
            ordered_categories = ordered_items_from_form(categories)
            if ordered_categories is None:
                flash("排序数据无效，请刷新页面后重试。")
                return redirect(url_for("admin_categories"))

            save_categories(ordered_categories)
        flash("分类排序已保存。")
        return redirect(url_for("admin_categories"))


    @app.route("/admin/import", methods=["GET", "POST"])
    @admin_required
    def admin_import():
        if request.method == "POST":
            target = form_text("target", "sites")
            if target not in {"sites", "categories"}:
                abort(400)

            raw_json = form_text("json_text")
            upload = request.files.get("json_file")
            if upload and upload.filename:
                raw_json = upload.read().decode("utf-8-sig")

            try:
                imported_data = json.loads(raw_json)
            except json.JSONDecodeError as error:
                flash(f"JSON 格式错误：{error.msg}。")
                return redirect(url_for("admin_import"))

            is_valid, message = validate_import_data(target, imported_data)
            if not is_valid:
                flash(message)
                return redirect(url_for("admin_import"))

            if target == "categories":
                imported_data = normalize_imported_categories(imported_data)
            elif target == "sites":
                imported_data = normalize_imported_sites(imported_data)

            with write_catalog():
                _write_json(f"{target}.json", imported_data)
                load_catalog.cache_clear()
            flash(f"{target}.json 已导入，共 {len(imported_data)} 条。")
            return redirect(url_for("admin_import"))

        return render_template("admin/import.html")


    @app.route("/admin/export/<target>")
    @admin_required
    def admin_export(target: str):
        catalog = load_catalog()
        if target == "all":
            return json_download("softhub-data.json", catalog)

        filename = EXPORT_TARGETS.get(target)
        if filename is None:
            abort(404)

        return json_download(filename, catalog[target])


