"""Standalone pipeline daemon entrypoint.

Runs the scheduler loop outside the uvicorn process so synchronous feed
fetches don't starve HTTP handlers. Invoke via `python -m src.pipeline_daemon`.
"""

import logging
import signal
import sys
import threading

from .database import init_db
from .scheduler import PipelineScheduler


logger = logging.getLogger("pipeline_daemon")


def main():
    logging.basicConfig(
        stream=sys.stderr,
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    logger.info("Pipeline daemon starting")

    init_db()
    scheduler = PipelineScheduler()
    shutdown = threading.Event()

    def _handle_signal(signum, _frame):
        logger.info("Received signal %s, shutting down", signum)
        shutdown.set()

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    scheduler.start()
    try:
        shutdown.wait()
    finally:
        logger.info("Stopping scheduler (waiting for current cycle)")
        scheduler.stop()
        logger.info("Pipeline daemon stopped")


if __name__ == "__main__":
    main()
