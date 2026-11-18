import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import create_app
from app.db import db


class LegalTests(unittest.TestCase):
    origin = "https://cabinet.example.test"
    documents = (
        ("policyUrl", "/privacy", "/legal/policy", "Политика обработки персональных данных"),
        ("consentUrl", "/consent", "/legal/consent", "Согласие на обработку персональных данных"),
    )

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.database = str(Path(folder.name) / "cabinet.sqlite")
        self.production = {
            "MODE": "production",
            "PUBLIC_URL": self.origin,
            "APP_SECRET": "x" * 32,
            "POLICY_URL": self.origin + "/legal/policy",
            "CONSENT_URL": self.origin + "/legal/consent",
            "CONSENT_VERSION": "operator-rev-2",
            "OPERATOR_NAME": "Иван Пупкин",
            "OPERATOR_CONTACT": "operator@example.test",
            "OPERATOR_HOSTING": "Тестовая площадка & тестовое место хранения",
            "YANDEX_CLIENT_ID": "fixture-client",
            "YANDEX_CLIENT_SECRET": "fixture-secret",
        }

    def make_app(self, **config):
        with patch.dict("os.environ", clear=True):
            return create_app({"TESTING": True, "DATABASE": self.database, **config})

    def get_document(self, client, path, title):
        response = client.get(path, base_url=self.origin)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "text/html")
        self.assertNotIn("Set-Cookie", response.headers)
        html = response.get_data(as_text=True)
        self.assertIn(f"<h1>{title}</h1>", html)
        self.assertIn("Иван Пупкин", html)
        return html

    def test_anonymous_demo_and_consent_version(self):
        app = self.make_app()
        client = app.test_client()
        for _, legacy, path, title in self.documents:
            self.assertEqual(client.get(legacy).location, path)
            html = self.get_document(client, path, title)
            self.assertIn("test-login-v1", html)
            self.assertIn("Сейчас это демо", html)
        with app.app_context():
            for table in ("accounts", "sessions", "consents"):
                self.assertEqual(db().execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0], 0)

        headers = {"X-Buro-Request": "1"}
        config = client.post("/api/open", json={}, headers=headers).json["config"]
        for key, _, path, _ in self.documents:
            self.assertEqual(config[key], path)
        self.assertEqual(config["consentVersion"], "test-login-v1")
        login = client.post(
            "/api/auth/demo/yandex",
            json={"consent": True, "version": config["consentVersion"]},
            headers=headers,
        )
        self.assertEqual(login.status_code, 200)
        with app.app_context():
            self.assertEqual(db().execute("SELECT version FROM consents").fetchone()[0], "test-login-v1")

    def test_public_production_documents_show_current_details(self):
        client = self.make_app(**self.production).test_client()
        for _, legacy, path, title in self.documents:
            self.assertEqual(client.get(legacy).location, self.origin + path)
            html = self.get_document(client, path, title)
            self.assertNotIn("Сейчас это демо", html)
            self.assertIn('href="mailto:operator@example.test"', html)
            self.assertIn("Тестовая площадка &amp; тестовое место хранения", html)
            self.assertIn("operator-rev-2", html)
            self.assertNotIn("fixture-secret", html)

    def test_external_documents_remain_authoritative(self):
        custom = {
            **self.production,
            "POLICY_URL": "https://docs.example.test/legal/policy",
            "CONSENT_URL": "https://docs.example.test/legal/consent",
            "OPERATOR_NAME": "",
            "OPERATOR_HOSTING": "",
            "SMS_API_ID": "fixture",
        }
        client = self.make_app(**custom).test_client()
        config = client.post("/api/open", json={}, headers={"X-Buro-Request": "1"}).json["config"]
        for key, legacy, path, _ in self.documents:
            target = "https://docs.example.test" + path
            self.assertEqual(config[key], target)
            for link in (legacy, path):
                response = client.get(link)
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.location, target)

    def test_incomplete_or_mismatched_builtin_setup_is_rejected(self):
        for override in (
            {"OPERATOR_HOSTING": ""},
            {"OPERATOR_CONTACT": ""},
            {"OPERATOR_NAME": ""},
            {"SMS_API_ID": "fixture"},
            {"YOO_SHOP_ID": "fixture", "YOO_SECRET": "fixture"},
            {"POLICY_URL": self.origin + "/privacy"},
            {"CONSENT_URL": self.origin + "/login"},
            {"POLICY_URL": self.origin + "/legal/consent/"},
            {"CONSENT_URL": "/legal/consent"},
        ):
            with self.subTest(override=override), self.assertRaises(RuntimeError):
                self.make_app(**{**self.production, **override})
