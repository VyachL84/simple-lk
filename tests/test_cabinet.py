import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

from app import create_app
from app.core import DAY, PRICE, now
from app.db import db


class CabinetCase(unittest.TestCase):
    mode = "demo"
    origin = "https://buro.example.test"

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.config = {
            "TESTING": True,
            "MODE": self.mode,
            "DATABASE": str(Path(self.folder.name) / "test.sqlite"),
            "APP_SECRET": "test-secret-not-used-outside-tests-0123456789",
            "PUBLIC_URL": self.origin,
            "POLICY_URL": self.origin + "/policy",
            "CONSENT_URL": self.origin + "/agreement",
            "CONSENT_VERSION": "v1",
            "OPERATOR_CONTACT": "operator@example.test",
            "SMS_API_ID": "test-sms",
            "YANDEX_CLIENT_ID": "test-yandex",
            "YANDEX_CLIENT_SECRET": "fixture",
            "ESIA_CLIENT_ID": "test-esia",
            "ESIA_CLIENT_SECRET": "fixture",
            "ESIA_ISSUER": "https://broker.example.test",
            "YOO_SHOP_ID": "fixture-shop",
            "YOO_SECRET": "fixture",
        }
        self.app = create_app(self.config)
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
        self.addCleanup(self.ctx.pop)
        self.agree = {"version": "demo-1" if self.mode == "demo" else "v1", "consent": True}
        self.w = self.post("/open", {"preview": True}).json

    def post(self, path, payload=None, client=None, method="POST"):
        return (client or self.client).open(
            "/api" + path,
            base_url=self.origin,
            method=method,
            json=payload or {},
            headers={"X-Buro-Request": "1", "Origin": self.origin},
        )

    def get(self, path, client=None):
        return (client or self.client).get("/api" + path, base_url=self.origin)


class DemoTests(CabinetCase):
    def test_isolated_workspaces_and_crud(self):
        other = self.app.test_client()
        self.assertNotEqual(
            self.w["user"]["id"], self.post("/open", {"preview": True}, other).json["user"]["id"]
        )
        self.assertEqual(
            self.post(
                "/clients", {"name": "Пример", "company": "Тест", "email": "user@example.test"}
            ).status_code,
            200,
        )
        row = self.get("/clients?q=ПРИМЕР").json["items"][0]
        self.assertEqual(
            self.post("/clients/" + str(row["id"]), {"name": "Обновлено"}, other, "PUT").status_code, 404
        )
        self.assertEqual(self.post("/clients/" + str(row["id"]), {}, other, "DELETE").status_code, 404)
        self.assertEqual(self.get("/clients?q=Пример", other).json["total"], 0)
        self.assertEqual(
            self.post("/clients/" + str(row["id"]), {"name": "Обновлено"}, method="PUT").status_code, 200
        )
        self.assertEqual(self.get("/clients?q=Обновлено").json["total"], 1)
        self.assertEqual(self.post("/clients/" + str(row["id"]), method="DELETE").status_code, 200)
        self.assertEqual(self.get("/workspace").json["stats"]["clients"], 12)
        tid = self.get("/tasks").json["items"][0]["id"]
        self.assertEqual(self.post(f"/tasks/{tid}", {"done": True}, other, "PUT").status_code, 404)

    def test_goals_idempotent_profile_and_persistence(self):
        for _ in range(2):
            r = self.post("/goals", {"goals": ["clients", "tasks"]})
            self.assertEqual(r.json["stats"]["tasks"], 6)
        self.assertEqual(self.post("/goals", {"goals": ["not-a-goal"]}).status_code, 400)
        self.post("/profile", {"name": "Демо", "company": "Мастерская"})
        app2 = create_app(self.config)
        c = app2.test_client()
        # A different app instance sees the same persisted session, not a global sample account.
        c.set_cookie("buro_sid", self.w["demoSession"], domain="buro.example.test")
        restored = self.get("/workspace", c).json
        self.assertEqual(restored["user"]["company"], "Мастерская")
        self.assertEqual(restored["user"]["goals"], ["clients", "tasks"])
        self.assertTrue(restored["user"]["profile_ready"])

    def test_demo_expiry_and_upgrade(self):
        db().execute("UPDATE accounts SET trial_until=?", (now() - 10,))
        self.assertEqual(self.post("/tasks", {"title": "Тест", "category": "Работа"}).status_code, 403)
        self.assertEqual(self.get("/clients/export").status_code, 403)
        self.assertFalse(self.get("/workspace").json["user"]["active"])
        result = self.post("/billing/checkout", {"plan": "business", "confirmed": True})
        self.assertTrue(result.json["workspace"]["user"]["paid"])
        self.assertEqual(
            self.post("/billing/checkout", {"plan": "business", "confirmed": True}).status_code, 409
        )
        self.assertEqual(self.get("/billing").json["items"][0]["amount"], PRICE)
        self.assertEqual(self.get("/clients/export").status_code, 200)

    def test_request_limits_and_csv(self):
        self.assertEqual(self.client.post("/api/open", json={}).status_code, 403)
        self.assertEqual(self.get("/clients?page=not-an-integer").status_code, 400)
        self.assertEqual(self.post("/clients", {"name": "x" * 101}).status_code, 400)
        self.assertEqual(self.post("/clients", {"name": "=test", "email": "bad"}).status_code, 400)
        self.post("/clients", {"name": "=test"})
        self.post("/billing/checkout", {"plan": "business", "confirmed": True})
        self.assertIn("'=test", self.get("/clients/export").get_data(as_text=True))

    def test_quota_also_applies_to_recommended_tasks(self):
        aid = self.w["user"]["id"]
        db().executemany(
            "INSERT INTO tasks(account_id,title,created) VALUES (?,?,?)", [(aid, "Тест", now())] * 26
        )
        self.assertEqual(self.post("/goals", {"goals": ["sales"]}).status_code, 409)
        self.assertEqual(self.get("/workspace").json["user"]["goals"], [])
        self.assertEqual(self.get("/workspace").json["stats"]["tasks"], 30)

    def test_demo_phone_session_rotation_and_logout(self):
        self.assertEqual(
            self.post("/auth/phone/request", {"phone": "+79990000001", **self.agree}).status_code, 400
        )
        p = self.post("/auth/phone/request", {"phone": "+7 900 000-00-00", **self.agree}).json
        self.assertEqual(
            self.post("/auth/phone/request", {"phone": "79000000000", **self.agree}).status_code, 429
        )
        res = self.post("/auth/phone/verify", {"code": p["demoCode"], "challenge": p["challenge"]})
        self.assertEqual(res.json["user"]["login_method"], "phone")
        self.assertNotEqual(res.json["demoSession"], self.w["demoSession"])
        self.assertEqual(
            self.client.get(
                "/api/workspace", base_url=self.origin, headers={"X-Demo-Session": self.w["demoSession"]}
            ).status_code,
            401,
        )
        self.assertEqual(
            self.post("/auth/phone/verify", {"code": p["demoCode"], "challenge": p["challenge"]}).status_code,
            400,
        )
        self.post("/logout")
        self.assertEqual(self.get("/workspace").status_code, 401)

    def test_phone_attempt_limit_and_expiry(self):
        p = self.post("/auth/phone/request", {"phone": "79000000000", **self.agree}).json
        for _ in range(5):
            self.assertEqual(
                self.post("/auth/phone/verify", {"challenge": p["challenge"], "code": "x"}).status_code, 400
            )
        self.assertEqual(
            self.post("/auth/phone/verify", {"challenge": p["challenge"], "code": p["demoCode"]}).status_code,
            400,
        )
        db().execute("UPDATE challenges SET attempts=0,expires=?", (now() - 1,))
        self.assertEqual(
            self.post("/auth/phone/verify", {"challenge": p["challenge"], "code": p["demoCode"]}).status_code,
            400,
        )

    def test_consent_and_demo_identity(self):
        self.assertEqual(
            self.post("/auth/demo/esia", {"consent": False, "version": "demo-1"}).status_code, 400
        )
        for method in ["yandex", "esia"]:
            self.assertEqual(
                self.post("/auth/demo/" + method, self.agree).json["user"]["id"], self.w["user"]["id"]
            )
        self.assertEqual(db().execute("SELECT count(*) FROM identities").fetchone()[0], 0)
        self.assertEqual(db().execute("SELECT count(*) FROM consents").fetchone()[0], 1)

    def test_backup_and_cleanup(self):
        dest = Path(self.folder.name) / "copy.sqlite"
        cli = self.app.test_cli_runner()
        self.assertEqual(cli.invoke(args=["backup", str(dest)]).exit_code, 0)
        import sqlite3

        target = sqlite3.connect(dest)
        self.assertEqual(target.execute("SELECT count(*) FROM clients").fetchone()[0], 12)
        target.close()
        db().execute("UPDATE accounts SET created=?", (now() - 31 * DAY,))
        self.assertEqual(cli.invoke(args=["cleanup"]).exit_code, 0)
        self.assertEqual(db().execute("SELECT count(*) FROM sessions").fetchone()[0], 0)


class ProviderTests(CabinetCase):
    mode = "production"

    def yandex_flow(self, identity="user-1"):
        url = self.post("/auth/yandex/start", self.agree).json["url"]
        query = parse_qs(urlsplit(url).query)
        self.assertEqual(query["code_challenge_method"], ["S256"])
        callback = "/auth/yandex/callback?code=test&state=" + query["state"][0]
        with patch(
            "app.auth.provider_json",
            side_effect=[{"access_token": "fixture"}, {"id": identity, "client_id": "test-yandex"}],
        ) as provider:
            r = self.get(callback)
            self.assertNotIn("failed", r.location)
            self.assertTrue(provider.call_args_list[0].kwargs["data"]["code_verifier"])
        return callback

    def test_no_demo_bypass_no_client_tokens(self):
        self.assertIsNone(self.w["user"])
        self.assertNotIn("demoSession", self.w)
        self.assertEqual(self.get("/workspace").status_code, 401)
        self.assertEqual(self.post("/auth/demo/yandex", self.agree).status_code, 404)
        self.assertEqual(
            self.post("/billing/checkout", {"plan": "business", "confirmed": True}).status_code, 401
        )
        self.assertEqual(
            self.client.post(
                "/api/open",
                base_url=self.origin,
                json={"preview": True},
                headers={"Origin": "https://other.example.test", "X-Buro-Request": "1"},
            ).status_code,
            403,
        )
        self.assertIn("Secure", self.post("/logout").headers["Set-Cookie"])
        with self.assertRaises(RuntimeError):
            create_app({**self.config, "APP_SECRET": ""})
        with self.assertRaises(RuntimeError):
            create_app({**self.config, "MODE": "demo"})

    def test_yandex_real_path_state_reuse_and_returning_user(self):
        with patch("app.auth.provider_json") as mock:
            self.assertIn("failed", self.get("/auth/yandex/callback?code=fixture&state=absent").location)
            mock.assert_not_called()
        callback = self.yandex_flow()
        aid = self.get("/workspace").json["user"]["id"]
        self.assertEqual(self.get("/workspace").json["stats"]["clients"], 0)
        self.assertIn("failed", self.get(callback).location)
        self.post("/logout")
        self.yandex_flow()
        self.assertEqual(self.get("/workspace").json["user"]["id"], aid)
        self.assertNotIn("user-1", db().execute("SELECT subject FROM identities").fetchone()[0])

    def test_new_document_version_requires_reconfirmation(self):
        self.yandex_flow()
        self.app.config["CONSENT_VERSION"] = "v2"
        self.assertEqual(self.get("/workspace").status_code, 401)
        self.assertIsNone(self.post("/open").json["user"])
        self.assertEqual(self.post("/auth/yandex/start", self.agree).status_code, 400)

    def test_operator_hold_and_erasure(self):
        self.yandex_flow()
        aid = str(self.get("/workspace").json["user"]["id"])
        cli = self.app.test_cli_runner()
        self.assertEqual(cli.invoke(args=["hold-account", aid]).exit_code, 0)
        self.assertEqual(self.get("/workspace").status_code, 401)
        self.assertEqual(cli.invoke(args=["erase-account", aid, "--yes"]).exit_code, 0)
        self.assertEqual(db().execute("SELECT count(*) FROM identities").fetchone()[0], 0)

    def test_phone_delivery_and_same_account(self):
        codes = []

        def provider(method, url, *, data):
            self.assertEqual(url, "https://sms.ru/sms/send")
            codes.append(data["msg"].split(": ")[1].split(".")[0])
            return {"sms": {data["to"]: {"status_code": 100}}}

        with patch("app.auth.provider_json", side_effect=provider):
            p = self.post("/auth/phone/request", {"phone": "+7 900 000-00-00", **self.agree}).json
        self.assertNotIn("demoCode", p)
        stored = db().execute("SELECT * FROM challenges").fetchone()
        self.assertNotEqual(stored["proof"], codes[0])
        self.assertNotEqual(stored["subject"], "79000000000")
        self.assertEqual(
            self.post("/auth/phone/verify", {"code": codes[0], "challenge": p["challenge"]}).json["user"][
                "login_method"
            ],
            "phone",
        )

    def test_delivery_failure_does_not_leave_code(self):
        with patch("app.auth.provider_json", return_value={"sms": {}}):
            self.assertEqual(
                self.post("/auth/phone/request", {"phone": "79000000000", **self.agree}).status_code, 502
            )
        self.assertEqual(db().execute("SELECT count(*) FROM challenges").fetchone()[0], 0)

    def esia_flow(self, bad_nonce=False, provider="esia"):
        issuer = self.config["ESIA_ISSUER"]
        meta = {
            "issuer": issuer,
            "authorization_endpoint": issuer + "/authorize",
            "token_endpoint": issuer + "/token",
            "jwks_uri": issuer + "/keys",
        }
        with patch("app.auth.provider_json", return_value=meta):
            r = self.post("/auth/esia/start", self.agree)
        args = parse_qs(urlsplit(r.json["url"]).query)
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        jwk = jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key(), as_dict=True)
        jwk["kid"] = "fixture-key"
        token = jwt.encode(
            {
                "sub": "fixture-sub",
                "iss": issuer,
                "aud": self.config["ESIA_CLIENT_ID"],
                "iat": now(),
                "exp": now() + 60,
                "idp": provider,
                "nonce": "other" if bad_nonce else args["nonce"][0],
            },
            key,
            algorithm="RS256",
            headers={"kid": "fixture-key"},
        )
        with patch("app.auth.provider_json", side_effect=[meta, {"id_token": token}, {"keys": [jwk]}]):
            return self.get("/auth/esia/callback?state=" + args["state"][0] + "&code=fixture")

    def test_esia_validates_broker_signed_id_token(self):
        self.assertIn("failed", self.esia_flow(True).location)
        self.assertIn("failed", self.esia_flow(provider="other").location)
        self.assertIsNone(self.post("/open").json["user"])
        self.assertNotIn("failed", self.esia_flow().location)
        self.assertEqual(self.get("/workspace").json["user"]["login_method"], "esia")

    def test_billing_verified_and_idempotent(self):
        self.yandex_flow()
        with patch(
            "app.billing.provider_json",
            return_value={
                "id": "pay-1",
                "confirmation": {"confirmation_url": "https://pay.example.test/order"},
            },
        ) as provider:
            order = {"plan": "business", "confirmed": True, "amount": 1}
            self.post("/billing/checkout", order)
            self.post("/billing/checkout", order)
            provider.assert_called_once()
            args = provider.call_args.kwargs
            self.assertEqual(args["json"]["amount"]["value"], "990.00")
            order_id = args["headers"]["Idempotence-Key"]
        self.assertFalse(self.get("/workspace").json["user"]["paid"])
        resp = {
            "id": "pay-1",
            "metadata": {"order": order_id},
            "recipient": {"account_id": "fixture-shop"},
            "test": False,
            "amount": {"value": "990.00", "currency": "RUB"},
            "status": "succeeded",
            "paid": True,
        }
        for invalid in (
            {"test": True},
            {"amount": {"value": "1.00", "currency": "RUB"}},
            {"recipient": {"account_id": "other"}},
        ):
            with patch("app.billing.provider_json", return_value={**resp, **invalid}):
                self.assertEqual(self.post("/billing/check").status_code, 409)
        with patch("app.billing.provider_json", return_value=resp) as provider:
            first = self.post("/billing/check").json["user"]["paid_until"]
            self.assertGreaterEqual(first, now() + 30 * DAY - 1)
            self.assertEqual(self.post("/billing/check").json["user"]["paid_until"], first)
            provider.assert_called_once()
