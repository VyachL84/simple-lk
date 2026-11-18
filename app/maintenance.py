"""Small Compose companion: no queue server, no traffic on a second port."""

import logging
import signal
import sqlite3
import threading
import time

from . import create_app
from .operations import cleanup_expired, reconcile_pending


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logger = logging.getLogger(__name__)
    app = create_app()
    stop = threading.Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: stop.set())
    next_cleanup = 0
    while not stop.is_set():
        with app.app_context():
            try:
                if time.monotonic() >= next_cleanup:
                    cleanup_expired()
                    next_cleanup = time.monotonic() + 86400
                    logger.info("Scheduled cleanup complete")
                failures = reconcile_pending(stop)
                if failures:
                    logger.warning("Payments awaiting retry or operator review: %d", failures)
            except sqlite3.OperationalError:
                logger.error("Storage unavailable; maintenance will retry")
        stop.wait(120)


if __name__ == "__main__":
    main()
