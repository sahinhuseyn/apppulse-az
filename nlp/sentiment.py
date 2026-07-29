"""
AppPulse AZ — Sentiment analizi
Hazır model: tabularisai/multilingual-sentiment-analysis
- Azərbaycan, Rus, İngilis dillərini dəstəkləyir
- XLM-RoBERTa əsaslıdır
- 5 sinif çıxarır: Very Positive / Positive / Neutral / Negative / Very Negative
"""

from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
from loguru import logger


MODEL_NAME = "tabularisai/multilingual-sentiment-analysis"

# 5 sinifi 3-ə yığışdırırıq (sadəlik üçün)
LABEL_MAP = {
    "Very Negative": "negative",
    "Negative":      "negative",
    "Neutral":       "neutral",
    "Positive":      "positive",
    "Very Positive": "positive",
}


class SentimentAnalyzer:
    """Tək dəfə yüklənən, təkrar istifadə edilən sentiment modeli."""

    def __init__(self):
        logger.info(f"Model yüklənir: {MODEL_NAME}")
        self.tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        self.model     = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)
        self.model.eval()
        self.id2label  = self.model.config.id2label
        logger.success("Model hazırdır.")

    def analyze(self, text: str) -> dict:
        """
        Tək mətn üçün sentiment qaytar.
        Return: {'sentiment': 'positive'|'negative'|'neutral', 'score': float}
        """
        if not text or not text.strip():
            return {"sentiment": "neutral", "score": 0.0}

        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=512,
            padding=True,
        )

        with torch.no_grad():
            outputs = self.model(**inputs)

        probs   = torch.softmax(outputs.logits, dim=1)[0]
        pred_id = torch.argmax(probs).item()
        raw_label = self.id2label[pred_id]

        return {
            "sentiment": LABEL_MAP.get(raw_label, "neutral"),
            "score":     float(probs[pred_id]),
        }

    def analyze_batch(self, texts: list[str]) -> list[dict]:
        """Batch emal — sürət üçün."""
        return [self.analyze(t) for t in texts]
