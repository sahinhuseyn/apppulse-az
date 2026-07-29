"""
AppPulse AZ — Avtomatik işləmə cədvəli
"""

import os
import schedule
import time
from loguru import logger
from dotenv import load_dotenv

from db.database import init_db
from scraper.scraper import run_scraper

load_dotenv()

INTERVAL_HOURS = int(os.getenv("SCRAPE_INTERVAL_HOURS", 12))


def job():
    logger.info("Cədvəllənmiş iş başladı...")
    try:
        result = run_scraper()
        total = sum(result.values())
        logger.success(f"Tamamlandı. Cəmi {total} yeni rəy əlavə edildi.")
    except Exception as e:
        logger.error(f"İş zamanı xəta: {e}")


if __name__ == "__main__":
    logger.info("AppPulse scheduler başladı.")
    init_db()
    job()

    schedule.every(INTERVAL_HOURS).hours.do(job)
    logger.info(f"Növbəti iş {INTERVAL_HOURS} saatdan sonra başlayacaq.")

    while True:
        schedule.run_pending()
        time.sleep(60)
