import uuid

from flask import Blueprint

from .auth import provider_json
from .core import (
    DAY,
    PRICE,
    Problem,
    account,
    body,
    cfg,
    config_public,
    demo,
    event,
    https_url,
    limit,
    now,
    rows,
)
from .db import db, transaction
from .workspace import snapshot

bp = Blueprint("billing", __name__, url_prefix="/api/billing")
API = "https://api.yookassa.ru/v3/payments"


def activate(order):
    # Caller holds a write transaction. A repeated confirmation cannot extend the period twice.
    if (
        db()
        .execute("UPDATE payments SET state='succeeded' WHERE id=? AND state='pending'", (order["id"],))
        .rowcount
    ):
        db().execute(
            "UPDATE accounts SET paid_until=max(paid_until,?)+? WHERE id=?",
            (now(), 30 * DAY, order["account_id"]),
        )
        event(order["account_id"], "billing", "Тариф Бизнес подключён", "Доступ на 30 дней без автопродления")


@bp.get("")
def status():
    a = account()
    return {
        "items": rows(
            "SELECT id,amount,state,created,url FROM payments WHERE account_id=? ORDER BY created DESC LIMIT 20",
            (a["id"],),
        )
    }


@bp.post("/checkout")
def checkout():
    if not config_public()["billing"]:
        raise Problem("Приём платежей пока не настроен.", 503)
    a = account()
    if body().get("plan") != "business" or body().get("confirmed") is not True:
        raise Problem("Подтвердите подключение тарифа Бизнес.")
    with transaction() as con:
        if con.execute("SELECT paid_until FROM accounts WHERE id=?", (a["id"],)).fetchone()[0] > now():
            raise Problem("Тариф уже подключён.", 409)
        order = con.execute(
            "SELECT * FROM payments WHERE account_id=? AND state='pending'", (a["id"],)
        ).fetchone()
        if not order:
            oid = str(uuid.uuid4())
            con.execute(
                "INSERT INTO payments(id,account_id,amount,state,created) VALUES (?,?,?,'pending',?)",
                (oid, a["id"], PRICE, now()),
            )
            order = con.execute("SELECT * FROM payments WHERE id=?", (oid,)).fetchone()
        if demo():
            activate(order)
            return {"workspace": snapshot(a["id"])}
    if order["url"]:
        return {"url": order["url"]}
    if order["created"] + 23 * 3600 < now():
        raise Problem("Нужна сверка платежа оператором. Не создавайте новый платёж.", 409)
    result = provider_json(
        "POST",
        API,
        auth=(cfg("YOO_SHOP_ID"), cfg("YOO_SECRET")),
        headers={"Idempotence-Key": order["id"]},
        json={
            "amount": {"value": f"{order['amount'] / 100:.2f}", "currency": "RUB"},
            "capture": True,
            "confirmation": {"type": "redirect", "return_url": cfg("PUBLIC_URL") + "/#/billing"},
            "description": "Бюро — тариф Бизнес на 30 дней",
            "metadata": {"order": order["id"]},
        },
    )
    payid, url = result.get("id", ""), result.get("confirmation", {}).get("confirmation_url", "")
    if not payid or not https_url(url):
        raise Problem("Не удалось получить ссылку на оплату.", 502)
    db().execute("UPDATE payments SET external_id=?,url=? WHERE id=?", (payid, url, order["id"]))
    return {"url": url}


def reconcile(order):
    if not order["external_id"] or demo():
        return
    from urllib.parse import quote

    result = provider_json(
        "GET", API + "/" + quote(order["external_id"], safe=""), auth=(cfg("YOO_SHOP_ID"), cfg("YOO_SECRET"))
    )
    if (
        result.get("id") != order["external_id"]
        or result.get("metadata", {}).get("order") != order["id"]
        or result.get("amount") != {"value": f"{order['amount'] / 100:.2f}", "currency": "RUB"}
        or result.get("recipient", {}).get("account_id") != cfg("YOO_SHOP_ID")
        or result.get("test") is not False
    ):
        raise Problem("Платёж не прошёл проверку. Обратитесь к оператору.", 409)
    with transaction():
        if result["status"] == "succeeded" and result.get("paid") is True:
            activate(order)
        elif result["status"] == "canceled":
            db().execute(
                "UPDATE payments SET state='canceled' WHERE id=? AND state='pending'", (order["id"],)
            )


@bp.post("/check")
def check():
    a = account()
    order = (
        db().execute("SELECT * FROM payments WHERE account_id=? AND state='pending'", (a["id"],)).fetchone()
    )
    if order:
        limit("payment-check:" + str(a["id"]), 15, 300)
        reconcile(order)
    return snapshot(a["id"])
