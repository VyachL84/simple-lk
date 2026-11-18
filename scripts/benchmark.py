"""Local, disposable HTTP benchmark of THIS application. Never opens an existing database."""

import argparse
import concurrent.futures
import http.client
import json
import math
import os
import random
import secrets
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app import KEYS, create_app
from app.core import DAY, digest, new_account, now
from app.db import db, transaction


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--accounts", type=int, default=10000)
    ap.add_argument("--requests", type=int, default=1200)
    ap.add_argument("--concurrency", type=int, default=12)
    args = ap.parse_args()
    if not 1 <= args.accounts <= 50000 or not 10 <= args.requests <= 50000 or not 1 <= args.concurrency <= 64:
        ap.error("Use 1–50000 accounts, 10–50000 requests and 1–64 clients.")
    secret = secrets.token_hex(32)
    with tempfile.TemporaryDirectory(prefix="buro-bench-") as tmp:
        path = str(Path(tmp) / "bench.sqlite")
        # Use the production session/consent path with fixture data. No provider calls.
        fixture = {
            **dict.fromkeys(KEYS, ""),
            "DATABASE": path,
            "APP_SECRET": secret,
            "PUBLIC_URL": "https://benchmark.invalid",
            "OPERATOR_CONTACT": "test@benchmark.invalid",
            "POLICY_URL": "https://benchmark.invalid/policy",
            "CONSENT_URL": "https://benchmark.invalid/terms",
            "CONSENT_VERSION": "bench",
            "SMS_API_ID": "unused-benchmark-fixture",
        }
        app = create_app({**fixture, "MODE": "production"})
        tokens = []
        with app.app_context(), transaction():
            for _ in range(args.accounts):
                aid = new_account("phone", True)
                raw = secrets.token_urlsafe(24)
                db().execute("INSERT INTO identities VALUES (?,?,?)", ("phone", digest(str(aid)), aid))
                db().execute("INSERT INTO sessions VALUES (?,?,?)", (digest("sid:" + raw), aid, now() + DAY))
                db().execute("INSERT INTO consents VALUES (?,?,?,?)", (aid, "bench", now(), "phone"))
                task = (
                    db()
                    .execute("SELECT id FROM tasks WHERE account_id=? AND done=0 LIMIT 1", (aid,))
                    .fetchone()[0]
                )
                tokens.append((raw, task))
        # Pass a pre-bound local socket to Gunicorn: no public target, no port allocation race.
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen(128)
            port = listener.getsockname()[1]
            proc = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "gunicorn",
                    "--bind",
                    f"fd://{listener.fileno()}",
                    "--workers=1",
                    "--threads=4",
                    "--no-control-socket",
                    "--log-level=warning",
                    "wsgi:app",
                ],
                pass_fds=(listener.fileno(),),
                cwd=ROOT,
                env={**os.environ, **fixture, "APP_MODE": "production"},
            )
            try:

                def hit(i):
                    raw, tid = tokens[random.Random(i).randrange(len(tokens))]
                    write = i % 10 == 0
                    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=15)
                    start = time.perf_counter()
                    try:
                        conn.request(
                            "PUT" if write else "GET",
                            f"/api/tasks/{tid}" if write else "/api/workspace",
                            body=json.dumps({"done": bool(i % 3)}) if write else None,
                            headers={
                                "Cookie": "buro_sid=" + raw,
                                "Content-Type": "application/json",
                                "X-Buro-Request": "1",
                            },
                        )
                        response = conn.getresponse()
                        response.read()
                        return (time.perf_counter() - start) * 1000, response.status
                    finally:
                        conn.close()

                # Warm up the worker and SQLite pages; cold-start cost is excluded.
                for i in range(20):
                    assert hit(i)[1] == 200
                start = time.perf_counter()
                with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
                    results = list(pool.map(hit, range(args.requests)))
                elapsed = time.perf_counter() - start
            finally:
                proc.terminate()
                proc.wait(timeout=15)
        times = sorted(t for t, _ in results)
        errors = sum(code != 200 for _, code in results)
        print(
            json.dumps(
                {
                    "accounts": args.accounts,
                    "clients": 12 * args.accounts,
                    "tasks": 4 * args.accounts,
                    "concurrency": args.concurrency,
                    "requests": args.requests,
                    "errors": errors,
                    "p50_ms": round(times[math.ceil(0.5 * len(times)) - 1], 2),
                    "p95_ms": round(times[math.ceil(0.95 * len(times)) - 1], 2),
                    "p99_ms": round(times[math.ceil(0.99 * len(times)) - 1], 2),
                    "rps": round(args.requests / elapsed, 1),
                    "db_mib": round(os.path.getsize(path) / 2**20, 1),
                    "sqlite": sqlite3.sqlite_version,
                },
                indent=2,
            )
        )
        return bool(errors)


if __name__ == "__main__":
    sys.exit(main())
