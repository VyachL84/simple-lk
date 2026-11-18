"""Host-operator commands. Intentionally not exposed as HTTP/admin endpoints."""

import click

from .core import DAY, Problem, demo, now
from .db import db, transaction


def register(app):
    @app.cli.command("hold-account")
    @click.argument("account_id", type=click.IntRange(min=1))
    def hold(account_id):
        """Block login and revoke sessions while a verified request is examined."""
        with transaction() as con:
            if not con.execute("SELECT id FROM accounts WHERE id=?", (account_id,)).fetchone():
                raise click.ClickException("Кабинет не найден.")
            con.execute("INSERT OR IGNORE INTO holds VALUES (?,?)", (account_id, now()))
            con.execute("DELETE FROM sessions WHERE account_id=?", (account_id,))
        click.echo("Кабинет заблокирован, сессии отозваны.")

    @app.cli.command("release-account")
    @click.argument("account_id", type=click.IntRange(min=1))
    def release(account_id):
        """Restore access after review; a fresh authentication is required."""
        with transaction() as con:
            if not con.execute("DELETE FROM holds WHERE account_id=?", (account_id,)).rowcount:
                raise click.ClickException("Блокировка не найдена.")
        click.echo("Блокировка снята. Требуется новый вход.")

    @app.cli.command("erase-account")
    @click.argument("account_id", type=click.IntRange(min=1))
    @click.confirmation_option(prompt="Основания и сроки проверены? Удалить заблокированный кабинет?")
    def erase(account_id):
        """Erase a held account with no financial records, after operator review."""
        with transaction() as con:
            if not con.execute("SELECT 1 FROM holds WHERE account_id=?", (account_id,)).fetchone():
                raise click.ClickException("Сначала проверьте обращение и заблокируйте кабинет.")
            if con.execute("SELECT 1 FROM payments WHERE account_id=? LIMIT 1", (account_id,)).fetchone():
                raise click.ClickException(
                    "Есть платёжные записи. Нужен отдельный порядок архивирования/уничтожения."
                )
            con.execute("DELETE FROM accounts WHERE id=?", (account_id,))
        click.echo(
            "Данные кабинета удалены из действующей базы. Оформите акт и обработайте копии по регламенту."
        )


def cleanup_expired():
    with transaction() as con:
        for tab in ("sessions", "challenges"):
            con.execute(f"DELETE FROM {tab} WHERE expires<=?", (now(),))
        con.execute("DELETE FROM rate_limits WHERE resets<=?", (now(),))
        con.execute("DELETE FROM events WHERE created<?", (now() - 90 * DAY,))
        if demo():
            con.execute(
                "DELETE FROM payments WHERE account_id IN (SELECT id FROM accounts WHERE created<?)",
                (now() - 30 * DAY,),
            )
            con.execute("DELETE FROM accounts WHERE created<?", (now() - 30 * DAY,))


def reconcile_pending(stop=None):
    from .billing import reconcile

    failed = 0
    for order in (
        db().execute("SELECT * FROM payments WHERE state='pending' AND external_id IS NOT NULL").fetchall()
    ):
        if stop and stop.is_set():
            break
        try:
            reconcile(order)
        except Problem:
            failed += 1
    return failed
