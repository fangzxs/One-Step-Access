from __future__ import annotations

import secrets
from functools import wraps

from flask import abort, redirect, request, session, url_for


def admin_required(view):
    """Require an active admin session before running a view."""
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login", next=request.path))
        return view(*args, **kwargs)

    return wrapped_view


def csrf_token() -> str:
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


def validate_csrf() -> None:
    token = session.get("csrf_token", "")
    form_token = request.form.get("csrf_token", "")
    if not token or not form_token or not secrets.compare_digest(token, form_token):
        abort(400)
