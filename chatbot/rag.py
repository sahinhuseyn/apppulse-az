"""
AppPulse AZ — RAG Chatbot
Groq (Llama 3.3) + güclü system prompt + söhbət yaddaşı
"""

import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from groq import Groq
from dotenv import load_dotenv
from loguru import logger

from db.database import get_connection
from config.apps import APPS

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY .env faylında yoxdur!")

client = Groq(api_key=GROQ_API_KEY)
MODEL_NAME = "llama-3.3-70b-versatile"


# ═════════════ DATA RETRIEVAL ═════════════

def get_stats(app_key: str | None = None, days: int = 365) -> list[dict]:
    """Hər şirkət üçün əsas statistikalar."""
    where = f"WHERE r.reviewed_at >= NOW() - INTERVAL '{days} days'"
    if app_key:
        where += f" AND r.app_key = '{app_key}'"

    sql = f"""
        SELECT
            r.app_key,
            COUNT(*) AS total,
            ROUND(AVG(r.rating)::numeric, 2) AS avg_rating,
            COUNT(*) FILTER (WHERE ra.sentiment = 'positive') AS positive,
            COUNT(*) FILTER (WHERE ra.sentiment = 'negative') AS negative,
            COUNT(*) FILTER (WHERE ra.is_complaint = TRUE) AS complaints,
            ROUND(100.0 * COUNT(*) FILTER (WHERE ra.sentiment = 'positive')
                / NULLIF(COUNT(*), 0), 1) AS positive_pct,
            ROUND(100.0 * COUNT(*) FILTER (WHERE ra.sentiment = 'negative')
                / NULLIF(COUNT(*), 0), 1) AS negative_pct
        FROM reviews r
        LEFT JOIN review_analysis ra ON r.id = ra.review_id
        {where}
        GROUP BY r.app_key
        ORDER BY r.app_key
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
    finally:
        conn.close()


def get_top_complaints(app_key: str | None = None, days: int = 365) -> list[dict]:
    """Mövzu üzrə şikayət sayı."""
    where = f"WHERE ra.is_complaint = TRUE AND r.reviewed_at >= NOW() - INTERVAL '{days} days'"
    if app_key:
        where += f" AND r.app_key = '{app_key}'"

    sql = f"""
        SELECT r.app_key, ra.topic, COUNT(*) AS count
        FROM reviews r
        JOIN review_analysis ra ON r.id = ra.review_id
        {where} AND ra.topic IS NOT NULL
        GROUP BY r.app_key, ra.topic
        ORDER BY count DESC
        LIMIT 12
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
    finally:
        conn.close()


def get_sample_reviews(
    app_key: str | None = None,
    sentiment: str | None = None,
    days: int = 365,
    limit: int = 8,
) -> list[dict]:
    """Nümunə rəylər."""
    conditions = [f"r.reviewed_at >= NOW() - INTERVAL '{days} days'"]
    if app_key:
        conditions.append(f"r.app_key = '{app_key}'")
    if sentiment:
        conditions.append(f"ra.sentiment = '{sentiment}'")

    where = " AND ".join(conditions)

    sql = f"""
        SELECT r.app_key, r.rating, ra.sentiment, ra.topic, r.content
        FROM reviews r
        LEFT JOIN review_analysis ra ON r.id = ra.review_id
        WHERE {where}
        ORDER BY r.thumbs_up DESC, r.reviewed_at DESC
        LIMIT {limit}
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
    finally:
        conn.close()


# ═════════════ CONTEXT BUILDING ═════════════

def build_context(question_or_app: str) -> str:
    """
    Sualdan və ya birbaşa app_key-dən kontekst qur.
    Əgər question_or_app bir app_key-dirsə (azercell/bakcell/nar),
    birbaşa həmin şirkətin datasını götür.
    """
    # Birbaşa app_key verildi?
    if question_or_app in APPS:
        target_app = question_or_app
        question_lower = ""
        q = ""
        days = 365
        sentiment_filter = None
    else:
        question_lower = question_or_app.lower()
        q = f" {question_lower} "

        # Hansı şirkətlər haqqında sualdır?
        mentioned_apps = []
        for app_key, app_info in APPS.items():
            if app_key in question_lower or app_info["display_name"].lower() in question_lower:
                mentioned_apps.append(app_key)

        target_app = mentioned_apps[0] if len(mentioned_apps) == 1 else None

        # Zaman aralığı
        days = 365
        if " həftə " in q or "7 gün" in q or " week " in q or "bu həftə" in q:
            days = 7
        elif " ay " in q or "30 gün" in q or " month " in q or "bu ay" in q or "son ay" in q:
            days = 30
        elif "bu gün" in q or " today " in q:
            days = 1

        # Sentiment filter
        sentiment_filter = None
        if any(w in q for w in [" şikayət", " mənfi", " pis", " problem", " narazı"]):
            sentiment_filter = "negative"
        elif any(w in q for w in [" müsbət", " yaxşı", " razı", " məmnun", " tərifləyir"]):
            sentiment_filter = "positive"

    # Data topla
    stats = get_stats(app_key=target_app, days=days)
    complaints = get_top_complaints(app_key=target_app, days=days)
    samples = get_sample_reviews(
        app_key=target_app,
        sentiment=sentiment_filter,
        days=days,
        limit=8,
    )

    # Period label
    period_map = {1: "BU GÜN", 7: "SON 7 GÜN", 30: "SON 30 GÜN", 365: "ÜMUMİ (bütün vaxt)"}
    period_label = period_map.get(days, f"SON {days} GÜN")

    # Kontekst qur
    ctx = f"=== {period_label} ÜZRƏ STATİSTİKA ===\n"
    for s in stats:
        net = (s.get("positive_pct") or 0) - (s.get("negative_pct") or 0)
        ctx += (
            f"\n📱 {s['app_key'].upper()}:"
            f"\n   Cəmi rəy: {s['total']}"
            f"\n   Cəmi şikayət: {s['complaints']}"
            f"\n   Ortalama reytinq: {s['avg_rating']}⭐"
            f"\n   Müsbət: {s['positive']} ({s.get('positive_pct', 0)}%)"
            f"\n   Mənfi: {s['negative']} ({s.get('negative_pct', 0)}%)"
            f"\n   Net sentiment: {net:+.1f}%"
        )

    if complaints:
        ctx += "\n\n=== ŞİKAYƏT MÖVZULARI (mövzu üzrə) ===\n"
        for c in complaints:
            ctx += f"\n• {c['app_key'].upper()} — {c['topic']}: {c['count']} şikayət"

    if samples:
        ctx += "\n\n=== NÜMUNƏ RƏYLƏR ===\n"
        for s in samples:
            tone = "mənfi" if s.get("sentiment") == "negative" else "müsbət" if s.get("sentiment") == "positive" else "neytral"
            ctx += (
                f"\n[{s['app_key']} {s['rating']}⭐ {tone}] "
                f"{s['content'][:180]}"
            )

    return ctx


# ═════════════ SYSTEM PROMPT ═════════════

SYSTEM_PROMPT = """Sən AppPulse AZ-ın AI analitikasısan. Azərbaycan telekom şirkətlərinin (Azercell, Bakcell, Nar) Google Play müştəri rəylərini analiz edirsən.

Sənə hər sualda hazır statistika verilir. Bu statistikaya əsaslanaraq konkret, faydalı cavab ver.

CAVAB FORMATI:
- Azərbaycanca yaz, aydın və qısa (maksimum 150 söz)
- Konkret rəqəmlər istifadə et: "Bakcell 778 şikayət aldı", "73.5% müsbət" kimi
- Müqayisə suallarında bullet point istifadə et
- Net sentiment = müsbət% - mənfi% (yüksək = daha yaxşı)
- Tövsiyə suallarında 3 konkret addım ver
- Cavabın sonunda 1 sətirlik "Xülasə:" əlavə et

CHART DATA (vacibdir):
Əgər cavabında müqayisəli rəqəmlər varsa (məsələn 2+ şirkəti müqayisə edirsənsə),
cavabının ən sonuna bu formatda JSON blok əlavə et:

```chart
{"type": "bar", "title": "Qrafik başlığı", "data": [{"label": "Azercell", "value": 40.7}, {"label": "Bakcell", "value": 26.0}, {"label": "Nar", "value": 43.4}]}
```

CHART NƏ VAXT ƏLAVƏ ET:
- Şirkətlər arasında müqayisə (reytinq, sentiment, şikayət sayı)
- Top mövzular siyahısı
- Faiz müqayisəsi

CHART NƏ VAXT ƏLAVƏ ETMƏ:
- Tövsiyə sualları ("nə etməliyəm?")
- Tək şirkət haqqında ümumi sual
- Sadə "bəli/xeyr" cavabı

DAVRANISH QAYDALARI:
- Verilən datada rəqəm varsa, mütləq istifadə et
- "Bu data yoxdur" DEMƏ — həmişə datadan nəticə çıxar
- Əgər sual qeyri-müəyyəndirsə, ən uyğun şərhi ver

MÖVZULARIN AÇIQLAMASI:
- "tətbiqin özü / bug" = proqram xətaları, crash, donma
- "giriş / login" = hesaba giriş problemləri
- "şəbəkə / internet" = internet sürəti, bağlantı
- "tarif / paket" = qiymət, tarif narazılığı
- "ödəniş / balans" = ödəniş xətaları, balans silinməsi
- "müştəri xidməti" = operator, dəstək xidməti"""


# ═════════════ CHATBOT (söhbət yaddaşı ilə) ═════════════

def extract_mentioned_apps(text: str) -> list[str]:
    """Mətndə hansı şirkətlər adı çəkilib."""
    text_lower = text.lower()
    found = []
    for app_key, app_info in APPS.items():
        if app_key in text_lower or app_info["display_name"].lower() in text_lower:
            found.append(app_key)
    return found


def ask(question: str, history: list[dict] | None = None) -> str:
    """
    İstifadəçi sualına cavab ver.
    history: əvvəlki söhbət tarixçəsi (söhbət yaddaşı üçün)
    """
    logger.info(f"Sual: {question}")

    # Müqayisə sualında əvvəlki şirkəti tap
    question_lower = question.lower()
    q = f" {question_lower} "
    is_comparison = any(w in q for w in [
        " müqayisə", " compare", " vs ", " fərq", " ilə müq",
        "yaxşıdır", "pisdir", "üstündür"
    ])

    mentioned_now = extract_mentioned_apps(question)

    # Müqayisə sualıdırsa və yalnız 1 şirkət adı varsa —
    # əvvəlki söhbətdən digər şirkəti tap
    if is_comparison and len(mentioned_now) == 1 and history:
        history_text = " ".join(
            msg["content"] for msg in history if msg["role"] == "user"
        )
        prev_apps = extract_mentioned_apps(history_text)
        all_apps = list(dict.fromkeys(prev_apps + mentioned_now))  # sıranı qoru
        if len(all_apps) >= 2:
            # Hər iki şirkətin datasını kontekstə yığ
            ctx_parts = []
            for app in all_apps[:2]:
                ctx_parts.append(build_context(app))
            context = "\n\n".join(ctx_parts)
            context = f"=== MÜQAYİSƏ: {' vs '.join(a.upper() for a in all_apps[:2])} ===\n\n" + context
        else:
            context = build_context(question)
    else:
        context = build_context(question)

    # Mesaj siyahısı qur
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Söhbət yaddaşı — əvvəlki 6 mesajı (3 sual-cavab) əlavə et
    if history:
        for msg in history[-6:]:
            messages.append(msg)

    # Yeni sual + kontekst
    messages.append({
        "role": "user",
        "content": f"DATA:\n{context}\n\nSUAL: {question}"
    })

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.2,
            max_tokens=600,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Groq xətası: {e}")
        return f"Xəta baş verdi: {e}"


if __name__ == "__main__":
    test_questions = [
        "Hansı şirkət ən çox şikayət alır?",
        "Bakcell və Nar-ı müqayisə et",
        "Əgər Azercell product manager-i olsam, hansı 3 şeyi düzəltməliyəm?",
    ]

    history = []
    for q in test_questions:
        print(f"\n{'='*60}")
        print(f"SUAL: {q}")
        print(f"{'='*60}")
        answer = ask(q, history=history)
        print(answer)
        # Yaddaşa əlavə et
        history.append({"role": "user", "content": q})
        history.append({"role": "assistant", "content": answer})
