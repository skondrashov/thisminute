"""Background scheduler that runs the pipeline periodically."""

import logging
import threading
import time

from .config import SCRAPE_INTERVAL_SECONDS
from .pipeline import run_pipeline

logger = logging.getLogger(__name__)

# Narrative analysis runs every 2 hours (separate from 15-min pipeline)
NARRATIVE_INTERVAL_SECONDS = 7200


class PipelineScheduler:
    """Runs the scraping pipeline on a timer in a background thread."""

    def __init__(self, interval: int = SCRAPE_INTERVAL_SECONDS):
        self.interval = interval
        self._stop_event = threading.Event()
        self._thread = None
        self._narrative_thread = None

    def _run_loop(self):
        """Run pipeline immediately, then every `interval` seconds."""
        logger.info("Scheduler started (interval=%ds)", self.interval)

        # Run immediately on startup
        try:
            stats = run_pipeline()
            logger.info("Initial pipeline run: %s", stats)
        except Exception as e:
            logger.error("Initial pipeline run failed: %s", e)

        # Then run periodically
        while not self._stop_event.wait(timeout=self.interval):
            try:
                stats = run_pipeline()
                logger.info("Scheduled pipeline run: %s", stats)
            except Exception as e:
                logger.error("Scheduled pipeline run failed: %s", e)

        logger.info("Scheduler stopped")

    def _narrative_loop(self):
        """Run narrative analysis on a slower cadence, one pass per domain."""
        logger.info("Narrative scheduler started (interval=%ds)", NARRATIVE_INTERVAL_SECONDS)

        # Wait a bit before first run to let pipeline populate data
        if self._stop_event.wait(timeout=300):  # 5 min delay
            return

        domains = ["news", "sports", "entertainment", "positive", "curious"]

        while not self._stop_event.is_set():
            for domain in domains:
                try:
                    from .database import get_connection
                    from .narrative_analyzer import analyze_narratives
                    conn = get_connection()
                    stats = analyze_narratives(conn, domain=domain)
                    conn.close()
                    logger.info("Narrative analysis (%s): %s", domain, stats)
                except Exception as e:
                    logger.error("Narrative analysis (%s) failed: %s", domain, e)

            if self._stop_event.wait(timeout=NARRATIVE_INTERVAL_SECONDS):
                break

        logger.info("Narrative scheduler stopped")

    def start(self):
        """Start the scheduler in a background daemon thread."""
        if self._thread and self._thread.is_alive():
            logger.warning("Scheduler already running")
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

        # Start narrative analysis thread
        self._narrative_thread = threading.Thread(target=self._narrative_loop, daemon=True)
        self._narrative_thread.start()

    def stop(self):
        """Signal the scheduler to stop."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        if self._narrative_thread:
            self._narrative_thread.join(timeout=5)
