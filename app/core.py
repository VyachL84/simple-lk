import hashlib
import hmac
import secrets
import time
from urllib.parse import urlsplit

from flask import current_app as app
from flask import g, request

from .db import db, transaction

DAY = 86400
PRICE = 99000  # kopecks; never accept the price from the browser
GOALS = {
    "clients": ("Вести клиентскую базу", "Добавить первого клиента"),
    "tasks": ("Организовать работу", "Составить план на неделю"),
    "sales": ("Развивать продажи", "Подготовить предложение для клиента"),
}


class Problem(Exception):
    def __init__(self, message, status=400):
        self.message, self.status = message, status


def now():
    return int(time.time())


def demo():
    return app.config["MODE"] == "demo"


def digest(value):
    return hmac.new(app.config["APP_SECRET"].encode(), value.encode(), hashlib.sha256).hexdigest()


def cfg(key):
    return app.config.get(key, "")


def https_url(value):
    u = urlsplit(value)
    return u.scheme == "https" and bool(u.hostname) and not u.username and not u.password


def body():
    value = request.get_json(silent=True)
    if not isinstance(value, dict):
        raise Problem("Ожидается JSON-объект.")
    return value


def text(key, limit, required=True):
    val = body().get(key, "")
    if not isinstance(val, str) or len(val.strip()) > limit or (required and not val.strip()):
        raise Problem("Проверьте поля формы: пустое или слишком длинное значение.")
    return val.strip()


def session_row():
    cookie = request.cookies.get("buro_sid", "")
    # Only the isolated showroom supports a tab-scoped token (embedded previews may block cookies).
    if demo():
        cookie = request.headers.get("X-Demo-Session") or cookie
    if not cookie:
        return None
    sql = "SELECT s.* FROM sessions s WHERE s.token=? AND s.expires>?"
    params = [digest("sid:" + cookie), now()]
    if not demo():
        sql += " AND (s.account_id IS NULL OR EXISTS (SELECT 1 FROM consents c WHERE c.account_id=s.account_id AND c.version=?))"
        params.append(cfg("CONSENT_VERSION"))
    return db().execute(sql, params).fetchone()


def require_session():
    s = session_row()
    if not s:
        raise Problem("Сеанс закончился. Обновите страницу и войдите снова.", 401)
    return s


def account(write=False):
    s = require_session()
    a = db().execute("SELECT * FROM accounts WHERE id=?", (s["account_id"],)).fetchone()
    if not a:
        raise Problem("Сначала войдите в кабинет.", 401)
    if write and max(a["paid_until"], a["trial_until"]) <= now():
        raise Problem("Период доступа завершён. Данные сохранены, для изменений подключите тариф.", 403)
    return a


def new_session(account_id=None, old=None):
    if old:
        db().execute("DELETE FROM sessions WHERE token=?", (old["token"],))
    raw = secrets.token_urlsafe(32)
    db().execute(
        "INSERT INTO sessions VALUES (?,?,?)",
        (digest("sid:" + raw), account_id, now() + (7 * DAY if account_id else 1800)),
    )
    g.new_sid = raw
    return raw


def limit(bucket, max_hits, seconds):
    key = digest("limit:" + bucket)
    timestamp = now()
    with transaction() as con:
        row = con.execute("SELECT * FROM rate_limits WHERE key=?", (key,)).fetchone()
        if row and row["resets"] > timestamp:
            if row["hits"] >= max_hits:
                raise Problem("Слишком много запросов. Попробуйте позже.", 429)
            con.execute("UPDATE rate_limits SET hits=hits+1 WHERE key=?", (key,))
        else:
            con.execute("INSERT OR REPLACE INTO rate_limits VALUES (?,1,?)", (key, timestamp + seconds))


def event(aid, kind, title, detail, at=None):
    db().execute(
        "INSERT INTO events(account_id,kind,title,detail,created) VALUES (?,?,?,?,?)",
        (aid, kind, title, detail, at or now()),
    )


def new_account(method, examples=False):
    ts = now()
    aid = (
        db()
        .execute(
            "INSERT INTO accounts(created,trial_until,login_method,company) VALUES (?,?,?,?)",
            (ts, ts + 14 * DAY, method, "Мой бизнес" if examples else ""),
        )
        .lastrowid
    )
    event(aid, "account", "Кабинет создан", "Новое рабочее пространство", ts)
    if examples:
        names = [
            ("Анна Белова", "Мята"),
            ("Марк Соколов", "Точка"),
            ("Ирина Лесная", "Полка"),
            ("Лев Речной", "Форма"),
            ("Ольга Ветрова", "Букет"),
            ("Пётр Клёнов", "Слой"),
            ("Яна Озёрная", "Блик"),
            ("Илья Лисов", "Север"),
            ("Вера Полевая", "Круг"),
            ("Денис Светлов", "Лист"),
            ("Алиса Мирная", "Линия"),
            ("Никита Мохов", "Холм"),
        ]
        for i, (name, company) in enumerate(names):
            db().execute(
                "INSERT INTO clients(account_id,name,company,created) VALUES (?,?,?,?)",
                (aid, name, company, ts - (12, 11, 10, 9, 7, 6, 4, 4, 3, 1, 0, 0)[i] * DAY),
            )
        for title, cat, done in [
            ("Создать рабочее пространство", "Настройка", 1),
            ("Обновить карточку клиента", "Клиенты", 0),
            ("Подготовить предложение", "Продажи", 0),
            ("Спланировать неделю", "Работа", 0),
        ]:
            db().execute(
                "INSERT INTO tasks(account_id,title,category,done,created) VALUES (?,?,?,?,?)",
                (aid, title, cat, done, ts),
            )
        event(aid, "clients", "Добавлены демоданные", "12 клиентов и 4 задачи", ts)
    event(aid, "trial", "Демо-период активирован", "Бесплатный доступ на 14 дней", ts)
    return aid


def config_public():
    return {
        "demo": demo(),
        "price": PRICE,
        "consentVersion": cfg("CONSENT_VERSION"),
        "policyUrl": cfg("POLICY_URL") or "/privacy",
        "consentUrl": cfg("CONSENT_URL") or "/consent",
        "contact": cfg("OPERATOR_CONTACT"),
        "providers": {
            "phone": demo() or bool(cfg("SMS_API_ID")),
            "yandex": demo() or bool(cfg("YANDEX_CLIENT_ID") and cfg("YANDEX_CLIENT_SECRET")),
            "esia": demo()
            or bool(cfg("ESIA_ISSUER") and cfg("ESIA_CLIENT_ID") and cfg("ESIA_CLIENT_SECRET")),
        },
        "billing": demo() or bool(cfg("YOO_SHOP_ID") and cfg("YOO_SECRET")),
    }


def consent_version():
    if body().get("consent") is not True or body().get("version") != cfg("CONSENT_VERSION"):
        raise Problem("Подтвердите отдельное согласие на обработку данных.")
    return cfg("CONSENT_VERSION")


def page_args():
    try:
        page = int(request.args.get("page", 1))
        if not 1 <= page <= 10000:
            raise ValueError
    except ValueError:
        raise Problem("Некорректная страница.")
    return 20, (page - 1) * 20


def rows(query, args):
    return [dict(row) for row in db().execute(query, args)]
