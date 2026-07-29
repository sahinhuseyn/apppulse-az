"""
AppPulse AZ — PostgreSQL bağlantı və schema
Google Play Store rəyləri üçün
"""

import os
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv
from loguru import logger

load_dotenv()


def get_connection():
    """PostgreSQL bağlantısı qaytar."""
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 5432)),
        dbname=os.getenv("DB_NAME", "apppulse"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
    )


def init_db():
    """Cədvəlləri yarat (əgər mövcud deyilsə)."""
    schema = """
    -- Ham rəylər cədvəli
    CREATE TABLE IF NOT EXISTS reviews (
        id              VARCHAR(100) PRIMARY KEY,   -- Google review ID
        app_key         VARCHAR(50)  NOT NULL,      -- azercell / bakcell / nar
        package         VARCHAR(200) NOT NULL,
        username        VARCHAR(200),
        content         TEXT         NOT NULL,
        rating          SMALLINT     NOT NULL,      -- 1-5 (ground truth!)
        thumbs_up       INT          DEFAULT 0,
        app_version     VARCHAR(50),
        language        VARCHAR(10),                -- az / ru / en
        country         VARCHAR(10),
        reply_content   TEXT,                       -- şirkətin cavabı
        reply_at        TIMESTAMPTZ,
        reviewed_at     TIMESTAMPTZ  NOT NULL,
        scraped_at      TIMESTAMPTZ  DEFAULT NOW()
    );

    -- NLP analiz nəticələri
    CREATE TABLE IF NOT EXISTS review_analysis (
        review_id       VARCHAR(100) PRIMARY KEY REFERENCES reviews(id),
        sentiment       VARCHAR(20),    -- positive / negative / neutral
        sentiment_score FLOAT,
        topic           VARCHAR(100),   -- giriş / şəbəkə / ödəniş ...
        is_complaint    BOOLEAN DEFAULT FALSE,
        key_phrases     TEXT[],
        analyzed_at     TIMESTAMPTZ DEFAULT NOW()
    );

    -- Günlük xülasə (dashboard üçün)
    CREATE TABLE IF NOT EXISTS daily_summary (
        id              SERIAL PRIMARY KEY,
        app_key         VARCHAR(50)  NOT NULL,
        date            DATE         NOT NULL,
        total_reviews   INT          DEFAULT 0,
        avg_rating      FLOAT,
        rating_1_count  INT          DEFAULT 0,
        rating_5_count  INT          DEFAULT 0,
        positive_count  INT          DEFAULT 0,
        negative_count  INT          DEFAULT 0,
        top_topic       VARCHAR(100),
        complaint_count INT          DEFAULT 0,
        UNIQUE(app_key, date)
    );

    -- Index-lər
    CREATE INDEX IF NOT EXISTS idx_reviews_app_key     ON reviews(app_key);
    CREATE INDEX IF NOT EXISTS idx_reviews_reviewed_at ON reviews(reviewed_at);
    CREATE INDEX IF NOT EXISTS idx_reviews_rating      ON reviews(rating);
    CREATE INDEX IF NOT EXISTS idx_reviews_language    ON reviews(language);
    """

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(schema)
        conn.commit()
        logger.success("DB schema hazırdır.")
    except Exception as e:
        conn.rollback()
        logger.error(f"Schema yaradılarkən xəta: {e}")
        raise
    finally:
        conn.close()


def insert_reviews(reviews: list[dict]) -> int:
    """Rəy siyahısını DB-ə yaz, dublikatları keç."""
    if not reviews:
        return 0

    sql = """
        INSERT INTO reviews
            (id, app_key, package, username, content, rating, thumbs_up,
             app_version, language, country, reply_content, reply_at, reviewed_at)
        VALUES %s
        ON CONFLICT (id) DO NOTHING
    """

    rows = [
        (
            r["id"],
            r["app_key"],
            r["package"],
            r.get("username"),
            r["content"],
            r["rating"],
            r.get("thumbs_up", 0),
            r.get("app_version"),
            r.get("language"),
            r.get("country"),
            r.get("reply_content"),
            r.get("reply_at"),
            r["reviewed_at"],
        )
        for r in reviews
    ]

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            execute_values(cur, sql, rows)
            inserted = cur.rowcount
        conn.commit()
        return inserted
    except Exception as e:
        conn.rollback()
        logger.error(f"Rəy yazılarkən xəta: {e}")
        raise
    finally:
        conn.close()


def get_unanalyzed_reviews(limit: int = 200) -> list[dict]:
    """Hələ NLP analizi edilməmiş rəyləri qaytar."""
    sql = """
        SELECT r.id, r.app_key, r.content, r.rating, r.language, r.reviewed_at
        FROM reviews r
        LEFT JOIN review_analysis ra ON r.id = ra.review_id
        WHERE ra.review_id IS NULL
        ORDER BY r.reviewed_at DESC
        LIMIT %s
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (limit,))
            cols = [desc[0] for desc in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
    finally:
        conn.close()


def get_app_stats(app_key: str, days: int = 7) -> dict:
    """Son N gün üçün tətbiq statistikası."""
    sql = """
        SELECT
            COUNT(*)                           AS total,
            ROUND(AVG(rating)::numeric, 2)     AS avg_rating,
            COUNT(*) FILTER (WHERE rating = 1) AS one_star,
            COUNT(*) FILTER (WHERE rating = 5) AS five_star
        FROM reviews
        WHERE app_key = %s
          AND reviewed_at >= NOW() - INTERVAL '%s days'
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (app_key, days))
            cols = [desc[0] for desc in cur.description]
            return dict(zip(cols, cur.fetchone()))
    finally:
        conn.close()
