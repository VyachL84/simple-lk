import csv
import io
import json
import re

from flask import Blueprint, Response, g, request

from .core import (
    DAY,
    GOALS,
    Problem,
    account,
    body,
    config_public,
    demo,
    event,
    limit,
    new_account,
    new_session,
    now,
    page_args,
    require_session,
    rows,
    session_row,
    text,
)
from .db import db, transaction

bp = Blueprint("workspace", __name__, url_prefix="/api")


def snapshot(aid=None):
    out = {"config": config_public(), "user": None}
    if demo() and "new_sid" in g:
        out["demoSession"] = g.new_sid
    if not aid:
        return out
    a = dict(db().execute("SELECT * FROM accounts WHERE id=?", (aid,)).fetchone())
    a["goals"] = json.loads(a["goals"])
    a["paid"] = a["paid_until"] > now()
    a["active"] = a["paid"] or a["trial_until"] > now()
    a["days"] = max(0, (max(a["trial_until"], a["paid_until"]) - now() + DAY - 1) // DAY)
    nc = db().execute("SELECT count(*) FROM clients WHERE account_id=?", (aid,)).fetchone()[0]
    nt, done = (
        db().execute("SELECT count(*),coalesce(sum(done),0) FROM tasks WHERE account_id=?", (aid,)).fetchone()
    )
    recent = rows(
        "SELECT id,kind,title,detail,created FROM events WHERE account_id=? ORDER BY id DESC LIMIT 4", (aid,)
    )
    end = (now() // DAY + 1) * DAY
    growth = [
        db()
        .execute("SELECT count(*) FROM clients WHERE account_id=? AND created<?", (aid, end - i * DAY))
        .fetchone()[0]
        for i in range(6, -1, -1)
    ]
    out.update(user=a, stats={"clients": nc, "tasks": nt, "done": done, "growth": growth}, events=recent)
    return out


@bp.post("/open")
def enter():
    old = session_row()
    if old and (old["account_id"] or not (demo() and body().get("preview") is True)):
        return snapshot(old["account_id"])
    limit("open:" + str(request.remote_addr), 180 if demo() else 100, 3600)
    with transaction():
        aid = new_account("guest", True) if demo() and body().get("preview") is True else None
        new_session(aid, old)
    return snapshot(aid)


@bp.get("/workspace")
def overview():
    return snapshot(account()["id"])


@bp.post("/logout")
def logout():
    s = require_session()
    with transaction():
        new_session(None, s)
    return snapshot()


@bp.post("/profile")
def profile():
    a = account(write=True)
    name, company = text("name", 64), text("company", 80)
    with transaction():
        db().execute(
            "UPDATE accounts SET name=?,company=?,profile_ready=1 WHERE id=?", (name, company, a["id"])
        )
        event(a["id"], "account", "Профиль обновлён", "Сохранены настройки кабинета")
    return snapshot(a["id"])


@bp.post("/goals")
def goals():
    a = account(write=True)
    chosen = body().get("goals")
    if (
        not isinstance(chosen, list)
        or not 1 <= len(chosen) <= len(GOALS)
        or not all(isinstance(k, str) and k in GOALS for k in chosen)
    ):
        raise Problem("Выберите от одной до трёх целей.")
    chosen = list(dict.fromkeys(chosen))
    with transaction():
        db().execute("UPDATE accounts SET goals=? WHERE id=?", (json.dumps(chosen), a["id"]))
        for k in chosen:
            if (
                not db()
                .execute("SELECT 1 FROM tasks WHERE account_id=? AND template=?", (a["id"], k))
                .fetchone()
            ):
                enforce_quota(a, "tasks")
            db().execute(
                "INSERT OR IGNORE INTO tasks(account_id,title,category,template,created) VALUES (?,?,?,?,?)",
                (
                    a["id"],
                    GOALS[k][1],
                    {"clients": "Клиенты", "tasks": "Работа", "sales": "Продажи"}[k],
                    k,
                    now(),
                ),
            )
        event(a["id"], "tasks", "Цели бизнеса сохранены", "Подготовлен персональный список задач")
    return snapshot(a["id"])


@bp.get("/events")
def history():
    a = account()
    n, off = page_args()
    return {
        "items": rows(
            "SELECT id,kind,title,detail,created FROM events WHERE account_id=? ORDER BY id DESC LIMIT ? OFFSET ?",
            (a["id"], n, off),
        ),
        "total": db().execute("SELECT count(*) FROM events WHERE account_id=?", (a["id"],)).fetchone()[0],
    }


@bp.post("/notifications/read")
def read_notifications():
    a = account()
    db().execute(
        "UPDATE accounts SET notification_seen=coalesce((SELECT max(id) FROM events WHERE account_id=?),0) WHERE id=?",
        (a["id"], a["id"]),
    )
    return snapshot(a["id"])


@bp.get("/clients")
@bp.get("/tasks")
def listing():
    a = account()
    n, off = page_args()
    clients = request.path.endswith("clients")
    table, name = ("clients", "name") if clients else ("tasks", "title")
    fields = "id,name,email,company,created" if clients else "id,title,done,category,created"
    q = request.args.get("q", "")[:100].strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    filt = " WHERE account_id=?"
    args = [a["id"]]
    if q:
        filt += f" AND casefold({name}) LIKE ? ESCAPE '\\'"
        args.append("%" + q.casefold() + "%")
    if not clients and request.args.get("status") in ("open", "done"):
        filt += " AND done=?"
        args.append(int(request.args["status"] == "done"))
    order = "id DESC" if clients else "done,id DESC"
    return {
        "items": rows(
            f"SELECT {fields} FROM {table}{filt} ORDER BY {order} LIMIT ? OFFSET ?", (*args, n, off)
        ),
        "total": db().execute(f"SELECT count(*) FROM {table}{filt}", args).fetchone()[0],
    }


def enforce_quota(a, table):
    maximum = (
        (2000 if table == "clients" else 500)
        if a["paid_until"] > now()
        else (100 if table == "clients" else 30)
    )
    if db().execute(f"SELECT count(*) FROM {table} WHERE account_id=?", (a["id"],)).fetchone()[0] >= maximum:
        raise Problem("Достигнут лимит записей по вашему тарифу.", 409)


@bp.post("/clients")
@bp.put("/clients/<int:cid>")
def save_client(cid=None):
    a = account(write=True)
    name, company, email = text("name", 100), text("company", 100, False), text("email", 180, False)
    if email and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise Problem("Проверьте адрес электронной почты.")
    with transaction():
        if cid is None:
            enforce_quota(a, "clients")
            db().execute(
                "INSERT INTO clients(account_id,name,company,email,created) VALUES (?,?,?,?,?)",
                (a["id"], name, company, email, now()),
            )
        elif (
            not db()
            .execute(
                "UPDATE clients SET name=?,company=?,email=? WHERE id=? AND account_id=?",
                (name, company, email, cid, a["id"]),
            )
            .rowcount
        ):
            raise Problem("Клиент не найден.", 404)
        event(
            a["id"],
            "clients",
            "Клиент добавлен" if cid is None else "Карточка обновлена",
            "Изменение в клиентской базе",
        )
    return snapshot(a["id"])


@bp.post("/tasks")
def add_task():
    a = account(write=True)
    title, category = text("title", 150), text("category", 20)
    if category not in ["Работа", "Клиенты", "Продажи", "Настройка"]:
        raise Problem("Неизвестная категория.")
    with transaction():
        enforce_quota(a, "tasks")
        db().execute(
            "INSERT INTO tasks(account_id,title,category,created) VALUES (?,?,?,?)",
            (a["id"], title, category, now()),
        )
        event(a["id"], "tasks", "Задача добавлена", category)
    return snapshot(a["id"])


@bp.put("/tasks/<int:tid>")
def toggle(tid):
    a = account(write=True)
    done = body().get("done")
    if not isinstance(done, bool):
        raise Problem("Некорректный статус.")
    with transaction():
        if (
            not db()
            .execute("UPDATE tasks SET done=? WHERE id=? AND account_id=?", (done, tid, a["id"]))
            .rowcount
        ):
            raise Problem("Задача не найдена.", 404)
        event(a["id"], "tasks", "Задача выполнена" if done else "Задача вновь в работе", "Статус обновлён")
    return snapshot(a["id"])


@bp.delete("/tasks/<int:item>")
@bp.delete("/clients/<int:item>")
def remove(item):
    a = account(write=True)
    tab = "tasks" if request.path.startswith("/api/tasks/") else "clients"
    with transaction():
        if not db().execute(f"DELETE FROM {tab} WHERE account_id=? AND id=?", (a["id"], item)).rowcount:
            raise Problem("Запись не найдена.", 404)
        event(a["id"], tab, "Запись удалена", "Список обновлён")
    return snapshot(a["id"])


@bp.get("/clients/export")
def export():
    a = account()
    if a["paid_until"] <= now():
        raise Problem("Экспорт доступен на тарифе Бизнес.", 403)
    out = io.StringIO()
    writer = csv.writer(out, delimiter=";")
    writer.writerow(["Имя", "Компания", "Почта"])
    for r in db().execute(
        "SELECT name,company,email FROM clients WHERE account_id=? ORDER BY id", (a["id"],)
    ):
        writer.writerow(
            [
                "'" + v
                if v.lstrip().startswith(("=", "+", "-", "@")) or v.startswith(("\t", "\r", "\n"))
                else v
                for v in r
            ]
        )
    return Response(
        "\ufeff" + out.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": 'attachment; filename="buro-clients.csv"'},
    )
