"""Public documents for the Yandex ID login test. Reading them does not open a session."""

from pathlib import Path
from urllib.parse import unquote, urlsplit

from flask import Blueprint, current_app, redirect, render_template

from .core import cfg, demo

bp = Blueprint("legal", __name__)
PATHS = {"POLICY_URL": "/legal/policy", "CONSENT_URL": "/legal/consent"}


def _local_path(config, key):
    """Path of a document on the production HTTPS origin, or None for another site."""
    target, origin = urlsplit(config[key]), urlsplit(config["PUBLIC_URL"])
    if target.hostname == origin.hostname and (target.port or 443) == (origin.port or 443):
        return unquote(target.path).rstrip("/") or "/"
    return None


def configure(config):
    if config["MODE"] == "demo":
        for key, path in PATHS.items():
            config[key] = config[key] or path
        config["CONSENT_VERSION"] = config["CONSENT_VERSION"] or "test-login-v1"
        return

    # Installations with their own published documents need no test-specific settings.
    for key, path in PATHS.items():
        local = _local_path(config, key)
        if local in ("/privacy", "/consent", "/login", "/"):
            raise RuntimeError("Укажите опубликованный документ, а не адрес входа или перенаправления.")
        if local not in PATHS.values():
            continue
        if local != path:
            raise RuntimeError("Не меняйте местами ссылки на политику и согласие.")
        if not all(config[k].strip() for k in ("OPERATOR_NAME", "OPERATOR_HOSTING", "OPERATOR_CONTACT")):
            raise RuntimeError(
                "Для теста с реальными аккаунтами заполните OPERATOR_NAME, OPERATOR_CONTACT и OPERATOR_HOSTING."
            )
        if (
            config["SMS_API_ID"]
            or all(config[k] for k in ("ESIA_ISSUER", "ESIA_CLIENT_ID", "ESIA_CLIENT_SECRET"))
            or (config["YOO_SHOP_ID"] and config["YOO_SECRET"])
        ):
            raise RuntimeError(
                "Встроенные документы описывают только тест Яндекс ID. Для других способов входа и оплаты укажите свои документы."
            )


def _document(key, template):
    if not demo() and _local_path(current_app.config, key) != PATHS[key]:
        return redirect(cfg(key))
    assets = Path(current_app.root_path).parent / "frontend/dist/assets"
    css = next(assets.glob("index-*.css"), None)
    return render_template(
        template,
        demo=demo(),
        version=cfg("CONSENT_VERSION"),
        operator=cfg("OPERATOR_NAME") or "Иван Пупкин",
        contact=cfg("OPERATOR_CONTACT"),
        hosting=cfg("OPERATOR_HOSTING"),
        active=key,
        policy_url=cfg("POLICY_URL"),
        consent_url=cfg("CONSENT_URL"),
        css=css.name if css else None,
    )


@bp.get(PATHS["POLICY_URL"], strict_slashes=False)
def policy():
    return _document("POLICY_URL", "legal/policy.html")


@bp.get(PATHS["CONSENT_URL"], strict_slashes=False)
def consent():
    return _document("CONSENT_URL", "legal/consent.html")
