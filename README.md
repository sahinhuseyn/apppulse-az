# AppPulse AZ

Azərbaycan tətbiqləri üçün Google Play rəy izləmə və analiz sistemi.

MVP — telekom sektoru: **Azercell, Bakcell, Nar**.

## Niyə Google Play?

- Pulsuz və rəsmi scraping (API açarı yox)
- Hər rəydə ulduz reytinqi = **ground truth** sentiment
- İnsanlar konkret şikayət yazır (20-300 söz) — Twitter-dən keyfiyyətli
- Azərbaycanca + Rusca + İngiliscə rəylər mövcuddur

## Quraşdırma

### 1. Virtual mühit
```bash
python -m venv venv
source venv/bin/activate       # Mac / Linux
# venv\Scripts\activate         # Windows
```

### 2. Paketlər
```bash
pip install -r requirements.txt
```

### 3. PostgreSQL
```bash
psql -U postgres -c "CREATE DATABASE apppulse;"
```

### 4. .env hazırla
```bash
cp .env.example .env
# DB_PASSWORD-u doldur
```

## İşə salma

### Bir dəfəlik:
```bash
python -m scraper.scraper
```

### Avtomatik (hər 12 saatda):
```bash
python scheduler.py
```

### DB-də yoxlamaq:
```sql
SELECT app_key, COUNT(*), AVG(rating)::numeric(3,2) AS avg_rating
FROM reviews
GROUP BY app_key;
```

## Struktur
```
apppulse/
├── config/
│   └── apps.py          # Package adları, mövzu keyword-ləri
├── db/
│   └── database.py      # PostgreSQL + schema
├── scraper/
│   └── scraper.py       # Google Play rəy toplama
├── nlp/                 # (növbəti mərhələ)
├── scheduler.py         # Avtomatik işləmə
├── requirements.txt
└── .env.example
```

## Növbəti mərhələ

- `nlp/sentiment.py` — XLM-RoBERTa sentiment (ulduz reytinqi ilə təlim)
- `nlp/topic.py` — BERTopic mövzu klasterləşməsi
- `dashboard/` — Streamlit vizuallaşdırma
- Həftəlik hesabat — PDF / email avtomatik
