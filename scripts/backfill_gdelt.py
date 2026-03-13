"""Backfill recent GDELT GKG data into the database.

Downloads GKG files for the past N hours and processes them through
the pipeline (NER/geocode skipped for pre-geocoded GDELT stories).

Usage:
    python -m scripts.backfill_gdelt [--hours 24]
"""

import argparse
import io
import logging
import sys
import time
import zipfile
import urllib.request
from datetime import datetime, timezone, timedelta

# Add project root to path
sys.path.insert(0, ".")

from src.database import get_connection, init_db, insert_story
from src.pipeline import process_story
from src.gdelt import parse_gkg_csv

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

GDELT_BASE = "http://data.gdeltproject.org/gdeltv2/"


def generate_gkg_urls(hours: int) -> list[str]:
    """Generate GKG file URLs for the past N hours (every 15 min)."""
    now = datetime.now(timezone.utc)
    # Round down to nearest 15 minutes
    now = now.replace(minute=(now.minute // 15) * 15, second=0, microsecond=0)
    urls = []
    intervals = hours * 4  # 4 per hour
    for i in range(1, intervals + 1):  # start from 1 to skip current (might not exist yet)
        t = now - timedelta(minutes=15 * i)
        ts = t.strftime("%Y%m%d%H%M%S")
        urls.append(f"{GDELT_BASE}{ts}.gkg.csv.zip")
    return urls


def download_and_parse_gkg(url: str) -> list[dict]:
    """Download a GKG zip file and parse into story dicts."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "thisminute-news-map/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            zip_data = resp.read()
    except Exception as e:
        logger.warning("Failed to download %s: %s", url.split("/")[-1], e)
        return []

    try:
        with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
            csv_name = zf.namelist()[0]
            raw = zf.read(csv_name).decode("utf-8", errors="replace")
    except Exception as e:
        logger.warning("Failed to unzip %s: %s", url.split("/")[-1], e)
        return []

    return parse_gkg_csv(raw)


def main():
    parser = argparse.ArgumentParser(description="Backfill GDELT GKG data")
    parser.add_argument("--hours", type=int, default=24, help="Hours to backfill (default: 24)")
    args = parser.parse_args()

    init_db()
    urls = generate_gkg_urls(args.hours)
    logger.info("Backfilling %d GKG files (%d hours)", len(urls), args.hours)

    total_new = 0
    total_processed = 0
    conn = get_connection()

    for i, url in enumerate(urls):
        stories = download_and_parse_gkg(url)
        if not stories:
            continue

        new_count = 0
        for story in stories:
            try:
                processed = process_story(story)
                was_new = insert_story(conn, processed)
                if was_new:
                    new_count += 1
            except Exception as e:
                continue

        total_new += new_count
        total_processed += len(stories)
        logger.info("[%d/%d] %s: %d stories, %d new",
                    i + 1, len(urls), url.split("/")[-1], len(stories), new_count)

        # Be polite — small delay between downloads
        time.sleep(0.5)

    conn.close()
    logger.info("Backfill complete: %d files, %d stories processed, %d new",
                len(urls), total_processed, total_new)


if __name__ == "__main__":
    main()
