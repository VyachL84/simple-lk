import sqlite3
from contextlib import contextmanager
from pathlib import Path

from flask import current_app, g


def connect(path):
    conn = sqlite3.connect(path, timeout=4, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.create_function("casefold", 1, str.casefold, deterministic=True)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA secure_delete=ON")
    return conn


def db():
    if "db" not in g:
        g.db = connect(current_app.config["DATABASE"])
    return g.db


@contextmanager
def transaction():
    con = db()
    con.execute("BEGIN IMMEDIATE")
    try:
        yield con
        con.commit()
    except BaseException:
        con.rollback()
        raise


def init(app):
    path = Path(app.config["DATABASE"])
    path.parent.mkdir(parents=True, exist_ok=True)
    con = connect(path)
    try:
        version = con.execute("PRAGMA user_version").fetchone()[0]
        if version not in (0, 1):
            raise RuntimeError("Неизвестная версия схемы БД")
        con.executescript(Path(__file__).with_name("schema.sql").read_text())
        con.execute("INSERT OR IGNORE INTO meta VALUES ('mode',?)", (app.config["MODE"],))
        if con.execute("SELECT value FROM meta WHERE key='mode'").fetchone()[0] != app.config["MODE"]:
            raise RuntimeError("Для рабочего и демонстрационного режимов требуются отдельные базы")
    finally:
        con.close()

    @app.teardown_appcontext
    def close(_exc):
        if con := g.pop("db", None):
            con.close()
