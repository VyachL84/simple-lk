"""Render only the three trusted, versioned guides shipped with the application."""

from functools import lru_cache
from pathlib import Path

import markdown
from flask import Blueprint, render_template, request, send_from_directory

from .core import Problem

bp = Blueprint("guides", __name__, url_prefix="/guides")
ROOT = Path(__file__).resolve().parent.parent
GUIDES = {
    "integrations.md": "Вход и оплата",
    "database.md": "База и нагрузка",
    "personal-data.md": "Персональные данные",
}


@lru_cache(maxsize=3)
def render(name):
    source = (
        (ROOT / "docs" / name)
        .read_text(encoding="utf-8")
        .replace("(../app/schema.sql)", "(/guides/schema.sql)")
    )
    return markdown.markdown(source, extensions=["tables", "fenced_code", "sane_lists"])


@bp.get("/<name>")
def guide(name):
    if name == "schema.sql":
        return send_from_directory(ROOT / "app", name, mimetype="text/plain")
    if name not in GUIDES:
        raise Problem("Документ не найден.", 404)
    if request.args.get("raw") == "1":
        return send_from_directory(ROOT / "docs", name, mimetype="text/plain")
    style = next((ROOT / "frontend/dist/assets").glob("index-*.css"), None)
    return render_template(
        "guide.html", guides=GUIDES, name=name, article=render(name), css=style.name if style else None
    )
