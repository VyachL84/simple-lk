"""Provider credentials and provider tokens never reach the SPA."""

import base64
import hashlib
import hmac
import re
import secrets
from urllib.parse import urlencode

import jwt
import requests
from flask import Blueprint, redirect, request

from .core import (
    Problem,
    cfg,
    config_public,
    consent_version,
    demo,
    digest,
    event,
    https_url,
    limit,
    new_account,
    new_session,
    now,
    require_session,
    text,
)
from .db import db, transaction
from .workspace import snapshot

bp = Blueprint("auth", __name__, url_prefix="/api/auth")
TEST_PHONE = "79000000000"


def provider_json(method, url, **kwargs):
    try:
        r = requests.request(method, url, timeout=(3, 8), allow_redirects=False, **kwargs)
        if not 200 <= r.status_code < 300:
            raise ValueError
        obj = r.json()
        if not isinstance(obj, dict):
            raise TypeError
        return obj
    except (requests.RequestException, ValueError, TypeError):
        raise Problem("Сервис временно недоступен. Попробуйте ещё раз позже.", 502) from None


def authenticate(s, method, subject_hash, version):
    """Call inside the consuming transaction. No linking by email, name or phone claims."""
    if require_session()["token"] != s["token"]:
        raise Problem("Сессия изменилась. Начните вход заново.", 401)
    if version != cfg("CONSENT_VERSION"):
        raise Problem("Условия изменились. Начните вход заново.")
    if demo():
        aid = s["account_id"] or new_account(method, True)
    else:
        identity = (
            db()
            .execute(
                "SELECT account_id FROM identities WHERE provider=? AND subject=?", (method, subject_hash)
            )
            .fetchone()
        )
        aid = identity[0] if identity else new_account(method)
        if not identity:
            db().execute("INSERT INTO identities VALUES (?,?,?)", (method, subject_hash, aid))
    if db().execute("SELECT 1 FROM holds WHERE account_id=?", (aid,)).fetchone():
        raise Problem("Доступ приостановлен. Обратитесь к оператору.", 403)
    db().execute("UPDATE accounts SET login_method=? WHERE id=?", (method, aid))
    db().execute("INSERT OR IGNORE INTO consents VALUES (?,?,?,?)", (aid, version, now(), method))
    event(
        aid,
        "account",
        "Вход выполнен",
        {"phone": "По номеру телефона", "esia": "Через Госуслуги", "yandex": "Через Яндекс ID"}[method],
    )
    new_session(aid, s)
    return aid


@bp.post("/phone/request")
def request_code():
    s = require_session()
    version = consent_version()
    phone = re.sub(r"[\s+()\-]", "", text("phone", 25))
    if phone.startswith("8"):
        phone = "7" + phone[1:]
    if not re.fullmatch(r"79[0-9]{9}", phone):
        raise Problem("Введите номер в формате +7 900 000-00-00.")
    if demo() and phone != TEST_PHONE:
        raise Problem("В демо используйте только тестовый номер +7 900 000-00-00.")
    if not config_public()["providers"]["phone"]:
        raise Problem("Вход по телефону ещё не подключён.", 503)
    subject = digest("phone:" + phone)
    ratekey = s["token"] if demo() else subject
    limit("otp-ip:" + str(request.remote_addr), 60, 3600)
    limit("otp-hour:" + ratekey, 5, 3600)
    limit("otp-minute:" + ratekey, 1, 60)
    code = f"{secrets.randbelow(1000000):06d}"
    cid = secrets.token_urlsafe(24)
    with transaction() as con:
        con.execute("DELETE FROM challenges WHERE session_token=? AND provider=?", (s["token"], "phone"))
        con.execute(
            "INSERT INTO challenges(id,session_token,provider,subject,proof,expires,consent_version) VALUES (?,?,?,?,?,?,?)",
            (cid, s["token"], "phone", subject, digest(cid + ":" + code), now() + 300, version),
        )
    if demo():
        return {"challenge": cid, "demoCode": code, "expiresIn": 300}
    try:
        result = provider_json(
            "POST",
            "https://sms.ru/sms/send",
            data={
                "api_id": cfg("SMS_API_ID"),
                "to": phone,
                "msg": "Бюро. Код для входа: " + code + ". Не сообщайте его другим.",
                "json": 1,
            },
        )
        if result.get("sms", {}).get(phone, {}).get("status_code") != 100:
            raise Problem("Не удалось отправить SMS. Повторите запрос через минуту.", 502)
    except Problem:
        db().execute("DELETE FROM challenges WHERE id=?", (cid,))
        raise
    return {"challenge": cid, "expiresIn": 300}


@bp.post("/phone/verify")
def verify():
    s = require_session()
    cid, code = text("challenge", 100), text("code", 6)
    with transaction() as con:
        row = con.execute(
            "SELECT * FROM challenges WHERE id=? AND session_token=? AND provider='phone'", (cid, s["token"])
        ).fetchone()
        if not row or row["expires"] <= now() or row["attempts"] >= 5:
            raise Problem("Код недействителен. Запросите новый код.")
        ok = hmac.compare_digest(row["proof"], digest(cid + ":" + code))
        if ok:
            aid = authenticate(s, "phone", row["subject"], row["consent_version"])
        else:
            con.execute("UPDATE challenges SET attempts=attempts+1 WHERE id=?", (cid,))
    if not ok:
        raise Problem("Неверный код. Проверьте шесть цифр.")
    return snapshot(aid)


@bp.post("/demo/<method>")
def demo_provider(method):
    if not demo() or method not in ("yandex", "esia"):
        raise Problem("Недоступно.", 404)
    s = require_session()
    version = consent_version()
    with transaction():
        aid = authenticate(s, method, "", version)
    return snapshot(aid)


def oidc_metadata():
    issuer = cfg("ESIA_ISSUER")
    obj = provider_json("GET", issuer.rstrip("/") + "/.well-known/openid-configuration")
    if obj.get("issuer") != issuer or not all(
        https_url(obj.get(k, "")) for k in ("authorization_endpoint", "token_endpoint", "jwks_uri")
    ):
        raise Problem("Проверьте конфигурацию шлюза ЕСИА.", 503)
    return obj


@bp.post("/<method>/start")
def start(method):
    s = require_session()
    version = consent_version()
    if demo() or method not in ("esia", "yandex") or not config_public()["providers"][method]:
        raise Problem("Провайдер не подключён в этом режиме.", 503)
    limit("oauth:" + s["token"], 12, 600)
    state, verifier, nonce = (secrets.token_urlsafe(32) for _ in range(3))
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    args = {
        "response_type": "code",
        "redirect_uri": cfg("PUBLIC_URL") + "/api/auth/" + method + "/callback",
        "state": state,
        "code_challenge_method": "S256",
        "code_challenge": challenge,
    }
    if method == "yandex":
        endpoint = "https://oauth.yandex.ru/authorize"
        args.update(client_id=cfg("YANDEX_CLIENT_ID"), scope="login:info")
    else:
        endpoint = oidc_metadata()["authorization_endpoint"]
        args.update(client_id=cfg("ESIA_CLIENT_ID"), scope="openid", nonce=nonce)
    with transaction() as con:
        con.execute("DELETE FROM challenges WHERE session_token=? AND provider=?", (s["token"], method))
        con.execute(
            "INSERT INTO challenges(id,session_token,provider,proof,nonce,expires,consent_version) VALUES (?,?,?,?,?,?,?)",
            (digest(state), s["token"], method, verifier, nonce, now() + 600, version),
        )
    return {"url": endpoint + "?" + urlencode(args)}


def verified_subject(method, code, flow):
    client = cfg(("ESIA" if method == "esia" else "YANDEX") + "_CLIENT_ID")
    secret = cfg(("ESIA" if method == "esia" else "YANDEX") + "_CLIENT_SECRET")
    meta = oidc_metadata() if method == "esia" else {"token_endpoint": "https://oauth.yandex.ru/token"}
    token = provider_json(
        "POST",
        meta["token_endpoint"],
        auth=(client, secret),
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": cfg("PUBLIC_URL") + "/api/auth/" + method + "/callback",
            "code_verifier": flow["proof"],
        },
    )
    if method == "yandex":
        info = provider_json(
            "GET",
            "https://login.yandex.ru/info",
            params={"format": "json"},
            headers={"Authorization": "OAuth " + token["access_token"]},
        )
        if info.get("client_id") != client or not info.get("id"):
            raise ValueError
        return digest("yandex:" + client + ":" + str(info["id"]))
    # Broker-side policy must only allow ESIA. Pin issuer and algorithms, never trust token-supplied keys/URLs.
    encoded = token["id_token"]
    kid = jwt.get_unverified_header(encoded)["kid"]
    keys = provider_json("GET", meta["jwks_uri"])["keys"]
    key = next(
        k for k in keys if k.get("kid") == kid and k.get("kty") == "RSA" and k.get("use", "sig") == "sig"
    )
    claims = jwt.decode(
        encoded,
        jwt.PyJWK.from_dict(key, "RS256").key,
        algorithms=["RS256"],
        issuer=cfg("ESIA_ISSUER"),
        audience=client,
        options={"require": ["iss", "aud", "sub", "exp", "iat", "nonce"]},
    )
    if (
        not hmac.compare_digest(claims["nonce"], flow["nonce"])
        or not claims["sub"]
        or claims.get("azp", client) != client
        or (isinstance(claims["aud"], list) and len(claims["aud"]) > 1 and not claims.get("azp"))
    ):
        raise ValueError
    # Trusted broker attribute derived from the upstream login, not editable profile data.
    if claims.get(cfg("ESIA_SOURCE_CLAIM") or "idp") != (cfg("ESIA_SOURCE_VALUE") or "esia"):
        raise ValueError
    return digest("esia:" + cfg("ESIA_ISSUER") + ":" + claims["sub"])


@bp.get("/<method>/callback")
def callback(method):
    if demo() or method not in ("esia", "yandex"):
        raise Problem("Этот способ входа не подключён.", 404)
    try:
        s = require_session()
        state = request.args.get("state", "")
        with transaction() as con:
            flow = con.execute(
                "SELECT * FROM challenges WHERE id=? AND session_token=? AND provider=? AND expires>?",
                (digest(state), s["token"], method, now()),
            ).fetchone()
            if not flow:
                raise ValueError
            con.execute("DELETE FROM challenges WHERE id=?", (flow["id"],))
        subject = verified_subject(method, request.args["code"], flow)
        with transaction():
            aid = authenticate(s, method, subject, flow["consent_version"])
        ready = db().execute("SELECT goals FROM accounts WHERE id=?", (aid,)).fetchone()[0] != "[]"
        return redirect("/#/overview" if ready else "/#/onboarding")
    except (KeyError, ValueError, TypeError, StopIteration, jwt.PyJWTError, Problem):
        return redirect("/?login=failed#/login")
