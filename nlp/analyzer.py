"""
AppPulse AZ — NLP analiz runner
DB-dən analiz edilməmiş rəyləri çəkir, sentiment-i hesablayır,
nəticəni review_analysis cədvəlinə yazır.
"""

from loguru import logger

from db.database import get_connection, get_unanalyzed_reviews
from nlp.sentiment import SentimentAnalyzer
from config.apps import TOPIC_KEYWORDS


# Şikayət siqnalları — sentiment + keyword birləşməsi
COMPLAINT_WORDS = [
    "işləmir", "bağlanır", "yavaş", "problem", "xəta", "şikayət", "pis",
    "не работает", "медленно", "проблема", "жалоба", "ужасно", "плохо",
    "not working", "slow", "bug", "crash", "terrible", "worst", "bad",
]

# Müsbət siqnallar — 3 ulduzlu rəyləri dəqiq təhlil üçün
POSITIVE_WORDS = [
    "yaxşı", "əla", "super", "mükəmməl", "təşəkkür", "bəyənirəm", "rahatdır",
    "хорошо", "отлично", "супер", "классно", "нравится", "спасибо", "удобно",
    "good", "great", "excellent", "love", "perfect", "awesome", "nice",
]

# Güclü mənfi siqnallar — 3 ulduzlu rəyləri dəqiq təhlil üçün
NEGATIVE_WORDS = COMPLAINT_WORDS + [
    "bezmişəm", "əsəblərim", "berbat", "dəhşət", "rezalet",
    "надоело", "бесит", "кошмар", "отстой", "ужас",
    "annoying", "useless", "hate", "awful", "horrible",
]


def has_any(text: str, words: list[str]) -> bool:
    """Mətndə sözlərdən birini axtar (case-insensitive)."""
    text_lower = text.lower()
    return any(w in text_lower for w in words)


def classify_topic(text: str) -> str | None:
    """
    Sadə keyword-əsaslı mövzu təsnifatı.
    (Sonra BERTopic ilə daha inkişaf etmiş versiya yazılacaq.)
    """
    text_lower = text.lower()
    scores: dict[str, int] = {}

    for topic, keywords in TOPIC_KEYWORDS.items():
        count = sum(1 for kw in keywords if kw in text_lower)
        if count > 0:
            scores[topic] = count

    if not scores:
        return None
    return max(scores, key=scores.get)


def hybrid_sentiment(rating: int, text: str, model_sentiment: str) -> str:
    """
    Hibrid sentiment qaydası — 3 səviyyəli:

    1. Ulduz 1-2 → həmişə negative (ulduza güvən)
    2. Ulduz 4-5 → həmişə positive (ulduza güvən)
    3. Ulduz 3   → mətn analizinin prioriteti:
        a) Mətndə güclü mənfi söz varsa → negative
        b) Mətndə güclü müsbət söz varsa → positive
        c) Yalnız model rəyinə güvən → modelin cavabı
        d) Heç biri yoxsa → neutral (default)

    Bu 3 ulduzlu rəylərdə səhv etiketləmələri minimuma endirir —
    məsələn "iki həftədir pis işləyir" (3⭐) artıq düzgün negative kimi
    təsnif edilir.
    """
    # Qayda 1 & 2 — ulduza güvən
    if rating <= 2:
        return "negative"
    if rating >= 4:
        return "positive"

    # Qayda 3 — 3 ulduzlu rəylər (mətni də analiz et)
    has_negative = has_any(text, NEGATIVE_WORDS)
    has_positive = has_any(text, POSITIVE_WORDS)

    # Hər iki tərəf siqnal göndərirsə → modelə güvən
    if has_negative and has_positive:
        return model_sentiment

    # Yalnız mənfi
    if has_negative:
        return "negative"

    # Yalnız müsbət
    if has_positive:
        return "positive"

    # Heç bir keyword yoxsa → model rəyi (adətən neutral)
    return model_sentiment


def is_complaint(text: str, sentiment: str, rating: int) -> bool:
    """Şikayətdir? 3 siqnalın ən azı 2-si uyğun gəlsə."""
    has_complaint_word = any(w in text.lower() for w in COMPLAINT_WORDS)
    low_rating         = rating <= 2
    negative_sentiment = sentiment == "negative"

    signals = sum([has_complaint_word, low_rating, negative_sentiment])
    return signals >= 2


def save_analysis(review_id: str, sentiment: str, score: float,
                  topic: str | None, complaint: bool):
    """Analiz nəticəsini review_analysis cədvəlinə yaz."""
    sql = """
        INSERT INTO review_analysis
            (review_id, sentiment, sentiment_score, topic, is_complaint)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (review_id) DO UPDATE
          SET sentiment       = EXCLUDED.sentiment,
              sentiment_score = EXCLUDED.sentiment_score,
              topic           = EXCLUDED.topic,
              is_complaint    = EXCLUDED.is_complaint,
              analyzed_at     = NOW()
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (review_id, sentiment, score, topic, complaint))
        conn.commit()
    finally:
        conn.close()


def get_all_reviews(limit: int = 500, offset: int = 0) -> list[dict]:
    """Bütün rəyləri qaytar (təkrar analiz üçün)."""
    sql = """
        SELECT id, app_key, content, rating, language, reviewed_at
        FROM reviews
        ORDER BY reviewed_at DESC
        LIMIT %s OFFSET %s
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (limit, offset))
            cols = [desc[0] for desc in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
    finally:
        conn.close()


def run_analysis(batch_size: int = 500, reanalyze_all: bool = False):
    """
    Rəyləri emal et.
    reanalyze_all=True → bütün rəyləri yenidən analiz et (qayda dəyişdikdə)
    reanalyze_all=False → yalnız analiz edilməmişləri
    """
    analyzer = SentimentAnalyzer()
    total = 0
    offset = 0

    while True:
        if reanalyze_all:
            reviews = get_all_reviews(limit=batch_size, offset=offset)
        else:
            reviews = get_unanalyzed_reviews(limit=batch_size)

        if not reviews:
            break

        logger.info(f"Emal edilir: {len(reviews)} rəy...")

        for i, r in enumerate(reviews, 1):
            try:
                result         = analyzer.analyze(r["content"])
                final_sentiment = hybrid_sentiment(
                    rating=r["rating"],
                    text=r["content"],
                    model_sentiment=result["sentiment"],
                )
                topic          = classify_topic(r["content"])
                complaint      = is_complaint(
                    r["content"], final_sentiment, r["rating"]
                )

                save_analysis(
                    review_id=r["id"],
                    sentiment=final_sentiment,
                    score=result["score"],
                    topic=topic,
                    complaint=complaint,
                )

                if i % 20 == 0:
                    logger.info(f"  {i}/{len(reviews)} tamamlandı")

            except Exception as e:
                logger.error(f"Rəy {r['id']} xətası: {e}")

        total += len(reviews)

        if reanalyze_all:
            offset += batch_size

        if len(reviews) < batch_size:
            break

    logger.success(f"Cəmi {total} rəy analiz edildi.")


if __name__ == "__main__":
    import sys

    reanalyze = "--reanalyze" in sys.argv
    mode = "təkrar analiz" if reanalyze else "yeni rəylər"
    logger.info(f"AppPulse NLP analizi başladı ({mode})...")
    run_analysis(reanalyze_all=reanalyze)
