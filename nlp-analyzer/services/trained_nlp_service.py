"""
NLP Servis Katmanı
Duygu analizi ve tema analizi için GPU-aware ve debug log destekli örnek servis.
Bu sınıf, gerçek modellerinizi kolayca entegre edebilmeniz için esnek bırakılmıştır.
"""

import logging
import random
from typing import Any, Dict, List, Optional

# Torch opsiyonel; yoksa CPU'ya düşer
try:
    import torch  # type: ignore
    HAS_TORCH = True
except Exception:  # torch yoksa buraya düşer
    torch = None  # type: ignore
    HAS_TORCH = False

logger = logging.getLogger(__name__)


def _get_device() -> int:
    """
    Uygun cihazı döndürür:
    - NLP_DEVICE env değişkeni varsa onu kullanır (örn: 0, -1)
    - Aksi halde CUDA varsa GPU:0, yoksa CPU (-1)
    """
    import os

    env_device = os.getenv("NLP_DEVICE")
    if env_device is not None:
        try:
            d = int(env_device)
            logger.info("[DEVICE] NLP_DEVICE env bulundu, device=%s", d)
            return d
        except ValueError:
            logger.warning("[DEVICE] NLP_DEVICE env integer değil: %r", env_device)

    if HAS_TORCH and torch.cuda.is_available():  # type: ignore[attr-defined]
        logger.info("[DEVICE] CUDA kullanılabilir, GPU:0 seçildi (ör. RTX 3060 6GB).")
        return 0

    logger.info("[DEVICE] CUDA yok veya kullanılamıyor, CPU (-1) kullanılacak.")
    return -1


class NLPService:
    """NLP işlemleri için servis sınıfı"""

    def __init__(self) -> None:
        """
        Servis başlatıcı.
        Burada:
        - Kullanılacak cihaz (GPU/CPU) belirlenir,
        - Modeller için placeholder alanlar oluşturulur.
        """
        self.device: int = _get_device()

        # Bu alanlara kendi gerçek modellerinizi set edebilirsiniz:
        # Örnek: self.sentiment_model = my_hf_pipeline
        self.sentiment_model: Optional[Any] = None
        self.theme_model: Optional[Any] = None
        self.ner_model: Optional[Any] = None
        self.summarization_model: Optional[Any] = None
        self.toxicity_model: Optional[Any] = None

        logger.info("[NLPService] Servis başlatıldı. device=%s", self.device)

    # ------------------------------------------------------------------ #
    # Duygu Analizi
    # ------------------------------------------------------------------ #
    def _placeholder_sentiment(self, text: str) -> Dict[str, Any]:
        """Duygu analizi için placeholder (rastgele) çıktıyı üretir."""
        sentiments = ["positive", "negative", "neutral"]
        sentiment = random.choice(sentiments)

        score_map = {
            "positive": random.uniform(0.3, 1.0),
            "negative": random.uniform(-1.0, -0.3),
            "neutral": random.uniform(-0.2, 0.2),
        }

        result = {
            "sentiment": sentiment,
            "score": round(score_map[sentiment], 2),
            "confidence": round(random.uniform(0.7, 0.95), 2),
            "placeholder": True,  # debug için: gerçek model değil
        }
        logger.debug("[Sentiment][Placeholder] Sonuç: %s", result)
        return result

    def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """
        Duygu analizi yap.

        Args:
            text (str): Analiz edilecek metin

        Returns:
            dict: {
                'sentiment': 'positive'|'negative'|'neutral',
                'score': float (-1 ile 1 arası),
                'confidence': float (0 ile 1 arası),
                'placeholder': bool (True ise random üretilmiştir)
            }
        """
        if not text:
            logger.warning("[Sentiment] Boş metin alındı.")
            return self._placeholder_sentiment(text)

        # Eğer kullanıcı kendi modelini set ettiyse onu kullan
        if self.sentiment_model is not None:
            try:
                logger.debug("[Sentiment] Gerçek model ile analiz başlıyor.")
                # Örnek: HuggingFace pipeline: [{'label': 'POSITIVE', 'score': 0.98}]
                raw = self.sentiment_model(text)

                sentiment = "neutral"
                score = 0.0
                confidence = 0.0

                if isinstance(raw, list) and raw:
                    r0 = raw[0]
                    label_raw = str(r0.get("label", "")).lower()
                    score_raw = float(r0.get("score", 0.0))

                    if "neg" in label_raw:
                        sentiment = "negative"
                        score = -abs(score_raw)
                    elif "pos" in label_raw:
                        sentiment = "positive"
                        score = abs(score_raw)
                    else:
                        sentiment = "
