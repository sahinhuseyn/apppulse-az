-- Ümumi statistika
SELECT 
    app_key,
    COUNT(*) AS total_reviews,
    ROUND(AVG(rating)::numeric, 2) AS avg_rating,
    MIN(reviewed_at)::date AS oldest,
    MAX(reviewed_at)::date AS newest
FROM reviews
GROUP BY app_key
ORDER BY total_reviews DESC;
-- Nümunə rəylər (ən mənfilər)
SELECT app_key, rating, language, LEFT(content, 150) AS preview
FROM reviews
WHERE rating <= 2
ORDER BY thumbs_up DESC
LIMIT 10;
-- 1. Ulduz vs Sentiment
SELECT 
    r.rating, ra.sentiment, COUNT(*) AS count
FROM reviews r
JOIN review_analysis ra ON r.id = ra.review_id
GROUP BY r.rating, ra.sentiment
ORDER BY r.rating, ra.sentiment;


-- 2. Hər tətbiq üçün sentiment paylanması
SELECT 
    r.app_key, ra.sentiment, COUNT(*) AS count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY r.app_key), 1) AS percent
FROM reviews r
JOIN review_analysis ra ON r.id = ra.review_id
GROUP BY r.app_key, ra.sentiment
ORDER BY r.app_key, ra.sentiment;


-- 3. Şikayət mövzuları
SELECT 
    r.app_key, ra.topic, COUNT(*) AS complaints
FROM reviews r
JOIN review_analysis ra ON r.id = ra.review_id
WHERE ra.is_complaint = TRUE AND ra.topic IS NOT NULL
GROUP BY r.app_key, ra.topic
ORDER BY r.app_key, complaints DESC;


-- 4. Yanlış təsnifatlar
SELECT 
    r.rating, ra.sentiment, r.language,
    LEFT(r.content, 120) AS preview
FROM reviews r
JOIN review_analysis ra ON r.id = ra.review_id
WHERE (r.rating <= 2 AND ra.sentiment = 'positive')
   OR (r.rating >= 4 AND ra.sentiment = 'negative')
LIMIT 10;