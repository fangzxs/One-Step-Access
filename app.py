from __future__ import annotations

from datetime import datetime

from flask import Flask, render_template

import config
from routes.admin import register_admin_routes
from routes.api import register_api_routes
from routes.public import register_public_routes
from services.catalog import (
    categories_with_counts,
    default_software_slug,
    load_catalog,
)
from utils.auth import csrf_token
from utils.formatters import compact_count, updated_label


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = config.SECRET_KEY

    for warning in config.check_security():
        app.logger.warning(f"[安全警告] {warning}")
    app.jinja_env.filters["compact_count"] = compact_count
    app.jinja_env.filters["updated_label"] = updated_label

    @app.context_processor
    def inject_global_data() -> dict:
        catalog = load_catalog()
        categories = categories_with_counts(catalog["categories"], catalog["sites"])
        return {
            "categories": categories,
            "csrf_token": csrf_token,
            "current_year": datetime.now().year,
            "default_software_slug": default_software_slug(categories),
            "tags": sorted(
                {tag for site in catalog["sites"] for tag in site.get("tags", [])}
            ),
        }

    @app.errorhandler(404)
    def not_found(error):
        return render_template("404.html"), 404

    register_public_routes(app)
    register_api_routes(app)
    register_admin_routes(app)
    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
