import os
import secrets
import sqlite3
from pathlib import Path
from urllib.parse import urlsplit

import click
from flask import Flask, g, jsonify, redirect, request, send_from_directory
from werkzeug.exceptions import HTTPException

from . import auth, billing, guides, legal, operations, workspace
from .core import DAY, Problem, available_integrations, cfg, demo, https_url
from .db import db, init

ROOT = Path(__file__).resolve().parent.parent
KEYS = (
    "APP_SECRET",
    "PUBLIC_URL",
    "SMS_API_ID",
    "YANDEX_CLIENT_ID",
    "YANDEX_CLIENT_SECRET",
    "ESIA_ISSUER",
    "ESIA_CLIENT_ID",
    "ESIA_CLIENT_SECRET",
    "ESIA_SOURCE_CLAIM",
    "ESIA_SOURCE_VALUE",
    "YOO_SHOP_ID",
    "YOO_SECRET",
    "POLICY_URL",
    "CONSENT_URL",
    "OPERATOR_NAME",
    "OPERATOR_CONTACT",
    "OPERATOR_HOSTING",
    "CONSENT_VERSION",
)


def create_app(overrides=None):
    app = Flask(__name__, static_folder=None)
    app.config.update({k: os.getenv(k, "") for k in KEYS})
    app.config.update(
        MODE=os.getenv("APP_MODE", "demo"),
        DATABASE=os.getenv("DATABASE", str(ROOT / "data/buro.sqlite")),
        MAX_CONTENT_LENGTH=16384,
    )
    app.config.update(overrides or {})
    if app.config["MODE"] not in ("production", "demo"):
        raise RuntimeError("APP_MODE должен быть demo или production")
    if app.config["MODE"] == "production":
        origin = urlsplit(app.config["PUBLIC_URL"])
        if not (
            https_url(app.config["PUBLIC_URL"])
            and origin.path == ""
            and not origin.query
            and not origin.fragment
            and len(app.config["APP_SECRET"]) >= 32
            and app.config["CONSENT_VERSION"]
            and app.config["OPERATOR_CONTACT"]
            and all(https_url(app.config[k]) for k in ("POLICY_URL", "CONSENT_URL"))
            and app.config["POLICY_URL"] != app.config["CONSENT_URL"]
        ):
            raise RuntimeError(
                "Заполните секрет, HTTPS origin, контакты и отдельные утверждённые документы оператора (см. .env.example)"
            )
        if app.config["ESIA_ISSUER"] and not https_url(app.config["ESIA_ISSUER"]):
            raise RuntimeError("ESIA_ISSUER должен использовать HTTPS")
        if not any(available_integrations(app.config)["providers"].values()):
            raise RuntimeError("Подключите хотя бы один реальный провайдер входа")
    else:
        if not app.config["APP_SECRET"]:
            keyfile = Path(app.config["DATABASE"]).parent / "demo.key"
            keyfile.parent.mkdir(parents=True, exist_ok=True)
            try:
                with keyfile.open("x") as f:
                    os.chmod(keyfile, 0o600)
                    f.write(secrets.token_hex(32))
            except FileExistsError:
                pass
            app.config["APP_SECRET"] = keyfile.read_text().strip()
    legal.configure(app.config)
    init(app)
    operations.register(app)
    for bp in (workspace.bp, auth.bp, billing.bp, guides.bp, legal.bp):
        app.register_blueprint(bp)

    @app.before_request
    def guard():
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            if request.headers.get("X-Buro-Request") != "1" or not request.is_json:
                raise Problem("Требуется запрос из кабинета.", 403)
            if not demo() and request.headers.get("Origin") not in (None, cfg("PUBLIC_URL")):
                raise Problem("Недопустимый источник запроса.", 403)

    @app.after_request
    def headers(r):
        if "new_sid" in g:
            r.set_cookie(
                "buro_sid",
                g.pop("new_sid"),
                httponly=True,
                secure=not demo(),
                samesite="Lax",
                max_age=7 * DAY,
                path="/",
            )
        r.headers["X-Content-Type-Options"] = "nosniff"
        r.headers["Referrer-Policy"] = "no-referrer"
        r.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        r.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; object-src 'none'; base-uri 'none'; form-action 'self'"
            + ("" if demo() else "; frame-ancestors 'none'")
        )
        if not demo():
            r.headers["Strict-Transport-Security"] = "max-age=31536000"
        if request.path.startswith("/api") or r.mimetype == "text/html":
            r.headers["Cache-Control"] = "no-store"
        return r

    @app.errorhandler(Problem)
    def problem(e):
        return jsonify(error=e.message), e.status

    @app.errorhandler(HTTPException)
    def http_error(e):
        return jsonify(
            error="Страница не найдена." if e.code == 404 else "Запрос не может быть обработан."
        ), e.code

    @app.errorhandler(sqlite3.OperationalError)
    def db_error(e):
        if "locked" in str(e) or "busy" in str(e):
            return jsonify(error="Кабинет занят. Попробуйте ещё раз."), 503
        app.logger.error("SQLite operation failed")
        return jsonify(error="Ошибка хранилища."), 500

    @app.get("/healthz")
    def health():
        db().execute("SELECT 1 FROM meta LIMIT 1").fetchone()
        return {"ok": True}

    @app.get("/")
    @app.get("/<path:path>")
    def site(path=""):
        if path in ("privacy", "consent"):
            key = "POLICY_URL" if path == "privacy" else "CONSENT_URL"
            return redirect(legal.PATHS[key] if demo() else cfg(key))
        if path.startswith("api/"):
            raise Problem("Маршрут не найден.", 404)
        return send_from_directory(ROOT / "frontend/dist", "index.html" if path in ("", "login") else path)

    @app.cli.command("cleanup")
    def cleanup():
        operations.cleanup_expired()
        click.echo("Очистка завершена.")

    @app.cli.command("backup")
    @click.argument("destination", type=click.Path(exists=False))
    def backup(destination):
        """Make a consistent online backup to a NEW file (including committed WAL pages)."""
        with open(destination, "xb"):
            os.chmod(destination, 0o600)
        target = sqlite3.connect(destination)
        try:
            db().backup(target)
        finally:
            target.close()
        click.echo("Копия сохранена.")

    @app.cli.command("reconcile")
    def sync_payments():
        """Reconcile pending orders independently of the browser."""
        failed = operations.reconcile_pending()
        if failed:
            raise click.ClickException(f"Платежи, требующие повторной сверки: {failed}")

    return app
