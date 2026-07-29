"""
AppPulse AZ — Dashboard data queries
Streamlit-dən çağırılan bütün SQL sorğuları buradadır.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from db.database import get_connection


def load_overview() -> pd.DataFrame:
    sql = """
        SELECT
            r.app_key,
            COUNT(*)                                             AS total_reviews,
            ROUND(AVG(r.rating)::numeric, 2)                     AS avg_rating,
            COUNT(*) FILTER (WHERE ra.sentiment = 'positive')    AS positive,
            COUNT(*) FILTER (WHERE ra.sentiment = 'negative')    AS negative,
            COUNT(*) FILTER (WHERE ra.sentiment = 'neutral')     AS neutral,
            COUNT(*) FILTER (WHERE ra.is_complaint = TRUE)       AS complaints,
            ROUND(100.0 * COUNT(*) FILTER (WHERE ra.sentiment = 'positive')
                  / NULLIF(COUNT(*), 0), 1)                      AS positive_pct,
            ROUND(100.0 * COUNT(*) FILTER (WHERE ra.sentiment = 'negative')
                  / NULLIF(COUNT(*), 0), 1)                      AS negative_pct
        FROM reviews r
        LEFT JOIN review_analysis ra ON r.id = ra.review_id
        GROUP BY r.app_key
        ORDER BY r.app_key
    """
    conn = get_connection()
    try:
        return pd.read_sql(sql, conn)
    finally:
        conn.close()


def load_sentiment_distribution() -> pd.DataFrame:
    sql = """
        SELECT r.app_key, ra.sentiment, COUNT(*) AS count
        FROM reviews r
        JOIN review_analysis ra ON r.id = ra.review_id
        GROUP BY r.app_key, ra.sentiment
        ORDER BY r.app_key, ra.sentiment
    """
    conn = get_connection()
    try:
        return pd.read_sql(sql, conn)
    finally:
        conn.close()


def load_topic_breakdown() -> pd.DataFrame:
    sql = """
        SELECT r.app_key, ra.topic, COUNT(*) AS complaints
        FROM reviews r
        JOIN review_analysis ra ON r.id = ra.review_id
        WHERE ra.is_complaint = TRUE AND ra.topic IS NOT NULL
        GROUP BY r.app_key, ra.topic
        ORDER BY r.app_key, complaints DESC
    """
    conn = get_connection()
    try:
        return pd.read_sql(sql, conn)
    finally:
        conn.close()


def load_rating_distribution() -> pd.DataFrame:
    sql = """
        SELECT app_key, rating, COUNT(*) AS count
        FROM reviews
        GROUP BY app_key, rating
        ORDER BY app_key, rating
    """
    conn = get_connection()
    try:
        return pd.read_sql(sql, conn)
    finally:
        conn.close()


def load_timeline(days: int = 30) -> pd.DataFrame:
    sql = f"""
        SELECT
            r.app_key,
            DATE(r.reviewed_at) AS day,
            COUNT(*)                                          AS total,
            COUNT(*) FILTER (WHERE ra.sentiment = 'positive') AS positive,
            COUNT(*) FILTER (WHERE ra.sentiment = 'negative') AS negative,
            ROUND(AVG(r.rating)::numeric, 2)                  AS avg_rating
        FROM reviews r
        LEFT JOIN review_analysis ra ON r.id = ra.review_id
        WHERE r.reviewed_at >= NOW() - INTERVAL '{days} days'
        GROUP BY r.app_key, DATE(r.reviewed_at)
        ORDER BY day, r.app_key
    """
    conn = get_connection()
    try:
        return pd.read_sql(sql, conn)
    finally:
        conn.close()


def load_anomalies(days: int = 30, threshold: float = 2.0) -> pd.DataFrame:
    """
    Anomal günləri tap: normaldan N dəfə çox rəy gələn günlər.
    threshold=2.0 → orta günlük rəy sayından 2x çox.
    """
    sql = f"""
        WITH daily AS (
            SELECT
                app_key,
                DATE(reviewed_at) AS day,
                COUNT(*) AS total
            FROM reviews
            WHERE reviewed_at >= NOW() - INTERVAL '{days} days'
            GROUP BY app_key, DATE(reviewed_at)
        ),
        avgs AS (
            SELECT app_key, AVG(total) AS avg_daily
            FROM daily
            GROUP BY app_key
        )
        SELECT
            d.app_key,
            d.day,
            d.total,
            ROUND(a.avg_daily::numeric, 1) AS avg_daily,
            ROUND((d.total / NULLIF(a.avg_daily, 0))::numeric, 1) AS spike_ratio
        FROM daily d
        JOIN avgs a ON d.app_key = a.app_key
        WHERE d.total >= a.avg_daily * {threshold}
          AND d.total >= 10
        ORDER BY d.day DESC, spike_ratio DESC
    """
    conn = get_connection()
    try:
        return pd.read_sql(sql, conn)
    finally:
        conn.close()


def load_reviews_filtered(
    app_key: str | None = None,
    sentiment: str | None = None,
    topic: str | None = None,
    language: str | None = None,
    limit: int = 100,
) -> pd.DataFrame:
    conditions = []
    params: list = []

    if app_key and app_key != "Hamısı":
        conditions.append("r.app_key = %s")
        params.append(app_key)
    if sentiment and sentiment != "Hamısı":
        conditions.append("ra.sentiment = %s")
        params.append(sentiment)
    if topic and topic != "Hamısı":
        conditions.append("ra.topic = %s")
        params.append(topic)
    if language and language != "Hamısı":
        conditions.append("r.language = %s")
        params.append(language)

    where_clause = " AND ".join(conditions) if conditions else "1 = 1"

    sql = f"""
        SELECT
            r.app_key, r.rating, r.language,
            ra.sentiment, ra.topic, ra.is_complaint,
            r.content, r.reviewed_at, r.thumbs_up
        FROM reviews r
        LEFT JOIN review_analysis ra ON r.id = ra.review_id
        WHERE {where_clause}
        ORDER BY r.reviewed_at DESC
        LIMIT {limit}
    """
    conn = get_connection()
    try:
        return pd.read_sql(sql, conn, params=params)
    finally:
        conn.close()


def load_topics_list() -> list[str]:
    sql = "SELECT DISTINCT topic FROM review_analysis WHERE topic IS NOT NULL ORDER BY topic"
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            return [row[0] for row in cur.fetchall()]
    finally:
        conn.close()
