"""
AppPulse AZ — Google Play Store scraper
google-play-scraper paketi ilə rəyləri çəkir (tamamilə pulsuz).
"""

from google_play_scraper import reviews, Sort
from loguru import logger

from config.apps import APPS, LOCALES
from db.database import insert_reviews


MAX_REVIEWS_PER_LOCALE = 1000  # Hər dil + ölkə üçün


def scrape_app(app_key: str) -> list[dict]:
    """
    Bir tətbiq üçün bütün dil/ölkə kombinasiyalarından rəyləri çək.
    Qaytarır: unikal rəy dict siyahısı.
    """
    app = APPS[app_key]
    package = app["package"]

    logger.info(f"[{app['display_name']}] Scrape başladı — {package}")

    seen_ids: set[str] = set()
    all_reviews: list[dict] = []

    for lang, country in LOCALES:
        try:
            result, _ = reviews(
                package,
                lang=lang,
                country=country,
                sort=Sort.NEWEST,
                count=MAX_REVIEWS_PER_LOCALE,
            )

            for r in result:
                review_id = r["reviewId"]
                if review_id in seen_ids:
                    continue
                seen_ids.add(review_id)

                content = r.get("content") or ""
                if not content.strip():
                    continue  # boş rəyləri keç

                all_reviews.append({
                    "id":             review_id,
                    "app_key":        app_key,
                    "package":        package,
                    "username":       r.get("userName"),
                    "content":        content,
                    "rating":         r.get("score", 0),
                    "thumbs_up":      r.get("thumbsUpCount", 0),
                    "app_version":    r.get("reviewCreatedVersion"),
                    "language":       lang,
                    "country":        country,
                    "reply_content":  r.get("replyContent"),
                    "reply_at":       r.get("repliedAt"),
                    "reviewed_at":    r["at"],
                })

            logger.info(
                f"  [{lang}/{country}] {len(result)} rəy alındı "
                f"(unikal: {len(seen_ids)})"
            )

        except Exception as e:
            logger.error(f"  [{lang}/{country}] Xəta: {e}")

    logger.success(
        f"[{app['display_name']}] Cəmi {len(all_reviews)} unikal rəy."
    )
    return all_reviews


def run_scraper(app_keys: list[str] | None = None) -> dict[str, int]:
    """
    Bütün (və ya seçilmiş) tətbiqlər üçün scraper-i işlət.
    Qaytarır: {app_key: inserted_count}.
    """
    targets = app_keys or list(APPS.keys())
    summary: dict[str, int] = {}

    for app_key in targets:
        reviews_list = scrape_app(app_key)
        inserted = insert_reviews(reviews_list)
        summary[app_key] = inserted
        logger.success(
            f"[{APPS[app_key]['display_name']}] "
            f"{inserted}/{len(reviews_list)} rəy DB-ə yazıldı."
        )

    return summary


if __name__ == "__main__":
    from db.database import init_db

    logger.info("AppPulse scraper başladı...")
    init_db()
    result = run_scraper()

    logger.info("─── Nəticə ───")
    for app_key, count in result.items():
        name = APPS[app_key]["display_name"]
        logger.info(f"  {name}: {count} yeni rəy")
