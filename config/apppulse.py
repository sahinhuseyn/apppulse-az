"""
AppPulse AZ — İzlənən tətbiqlər
Google Play Store paket adları (package name / app ID)

Yoxlamaq üçün: https://play.google.com/store/apps/details?id=PACKAGE_NAME
"""

APPS = {
    "azercell": {
        "display_name": "Azercell",
        "package": "com.azercell.ss.app",
        "company": "Azercell",
        "category": "telecom",
    },
    "bakcell": {
        "display_name": "Bakcell",
        "package": "az.azerconnect.bakcell",
        "company": "Bakcell",
        "category": "telecom",
    },
    "nar": {
        "display_name": "Nar",
        "package": "az.azerconnect.nar",
        "company": "Nar",
        "category": "telecom",
    },
}

# Hansı dillərdə və ölkələrdə rəy çəkək
LOCALES = [
    ("az", "az"),   # Azərbaycanca, Azərbaycan
    ("ru", "az"),   # Rusca, Azərbaycan
    ("en", "az"),   # İngiliscə, Azərbaycan
]

# Mövzu keyword-ləri — NLP layer-də istifadə olunacaq
TOPIC_KEYWORDS = {
    "giriş / login": [
        "giriş", "login", "şifrə", "parol", "otp", "daxil ola bilmir",
        "вход", "войти", "пароль", "не могу войти",
        "sign in", "can't log", "password",
    ],
    "şəbəkə / internet": [
        "şəbəkə", "internet", "bağlantı", "signal", "yavaş",
        "сеть", "интернет", "связь", "медленно",
        "network", "connection", "slow",
    ],
    "ödəniş / balans": [
        "ödəniş", "balans", "ödəmək", "kart", "köçürmə",
        "оплата", "баланс", "платеж", "карта",
        "payment", "balance", "top up",
    ],
    "tarif / paket": [
        "tarif", "paket", "qiymət", "kampaniya", "endirim",
        "тариф", "пакет", "цена", "скидка",
        "plan", "package", "price",
    ],
    "müştəri xidməti": [
        "operator", "call center", "müştəri xidməti", "cavab vermir",
        "оператор", "служба", "не отвечают",
        "support", "customer service",
    ],
    "tətbiqin özü / bug": [
        "tətbiq", "app", "bağlanır", "işləmir", "xəta", "update", "yenilən",
        "приложение", "вылетает", "не работает", "обновление",
        "crash", "bug", "not working", "error",
    ],
}
