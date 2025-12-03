"""
NLP Servis Katmanı
Gerçek transformer modelleriyle duygu ve tema analizi
"""

import os
import torch
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification


class NLPService:
    """Sadece duygu ve tema analizi yapan NLP servis sınıfı"""
    
    def __init__(self):
        """Servis başlatıcı - Gerçek modelleri yükle"""
        print("🔄 Loading NLP models...")

        # Bu dosyanın konumuna göre ../models dizinini belirle
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.model_cache_dir = os.path.join(base_dir, "..", "models")
        os.makedirs(self.model_cache_dir, exist_ok=True)
        print(f"  📂 Model cache directory: {self.model_cache_dir}")
        
        try:
            device = 0 if torch.cuda.is_available() else -1

            # Duygu analizi modeli - Türkçe XLM-RoBERTa
            print("  📥 Loading sentiment model: incidelen/xlm-roberta-base-turkish-sentiment-analysis")
            self.sentiment_pipeline = pipeline(
                "sentiment-analysis",
                model="incidelen/xlm-roberta-base-turkish-sentiment-analysis",
                device=device,
                use_fast=False,              # Slow tokenizer kullan (bug workaround)
                cache_dir=self.model_cache_dir
            )
            print("  ✅ Sentiment model loaded")
            
            # Tema/Konu analizi modeli - Türkçe haber sınıflandırma (savasy)
            print("  📥 Loading topic model: savasy/bert-turkish-text-classification")
            self.topic_model_name = "savasy/bert-turkish-text-classification"
            self.topic_tokenizer = AutoTokenizer.from_pretrained(
                self.topic_model_name,
                cache_dir=self.model_cache_dir
            )
            self.topic_model = AutoModelForSequenceClassification.from_pretrained(
                self.topic_model_name,
                cache_dir=self.model_cache_dir
            )
            
            # Tüm skorları almak için return_all_scores=True
            self.topic_pipeline = pipeline(
                "text-classification",
                model=self.topic_model,
                tokenizer=self.topic_tokenizer,
                device=device,
                return_all_scores=True
            )

            # Modelin label -> insan okunur tema isimleri
            # Model İngilizce etiket döndürüyor: world, economy, culture, health, politics, sport, technology
            self.topic_code_to_label = {
                "LABEL_0": "Dünya",
                "LABEL_1": "Ekonomi",
                "LABEL_2": "Kültür",
                "LABEL_3": "Sağlık",
                "LABEL_4": "Siyaset",
                "LABEL_5": "Spor",
                "LABEL_6": "Teknoloji",
            }
            
            # İngilizce -> Türkçe mapping
            self.english_to_turkish = {
                "world": "Dünya",
                "economy": "Ekonomi",
                "culture": "Kültür",
                "health": "Sağlık",
                "politics": "Siyaset",
                "sport": "Spor",
                "technology": "Teknoloji"
            }
            
            print("  ✅ Topic model loaded")
            print("✅ All NLP models loaded successfully!\n")
            
        except Exception as e:
            print(f"❌ Error loading models: {e}")
            raise
        
    def analyze_sentiment(self, text: str) -> dict:
        """
        Duygu analizi yap - XLM-RoBERTa modeli ile
        
        Args:
            text (str): Analiz edilecek metin
            
        Returns:
            dict: {
                'sentiment': 'positive'|'negative'|'neutral',
                'score': float (-1 ile 1 arası),
                'confidence': float (0 ile 1 arası),
                'label': str (modelin orijinal etiketi)
            }
        """
        try:
            # Basit karakter bazlı kesme (token değil ama pratik)
            if len(text) > 512:
                text = text[:512]
            
            # Model ile duygu analizi yap
            result = self.sentiment_pipeline(text)[0]
            
            # Model çıktısını normalize et
            label = result['label'].lower()
            confidence = float(result['score'])
            
            # Sentiment etiketini standartlaştır
            if 'pos' in label or 'olumlu' in label:
                sentiment = 'positive'
                score = confidence
            elif 'neg' in label or 'olumsuz' in label:
                sentiment = 'negative'
                score = -confidence
            else:
                sentiment = 'neutral'
                score = 0.0
            
            return {
                'sentiment': sentiment,
                'score': round(score, 2),
                'confidence': round(confidence, 2),
                'label': result['label']  # Orijinal model etiketi
            }
            
        except Exception as e:
            print(f"❌ Sentiment analysis error: {e}")
            return {
                'sentiment': 'neutral',
                'score': 0.0,
                'confidence': 0.0,
                'error': str(e)
            }
    
    def analyze_theme(self, text: str, threshold: float = 0.15) -> dict:
        """
        Tema analizi yap - Türkçe haber sınıflandırma modeli (savasy/bert-turkish-text-classification) ile
        
        Args:
            text (str): Analiz edilecek metin
            threshold (float): Minimum tema skoru eşiği (varsayılan: 0.15)
            
        Returns:
            dict: {
                'themes': [list of themes],      # ['Siyaset', 'Ekonomi', ...]
                'keywords': [list of keywords],  # ['ekonomi', 'piyasa', ...]
                'main_topic': str,               # 'Siyaset'
                'scores': { 'Siyaset': 0.92, ... },
                'is_ambiguous': bool             # Birden fazla yüksek skorlu tema var mı?
            }
        """
        try:
            # Token bazlı kesme (daha akıllı)
            tokens = self.topic_tokenizer.encode(text, add_special_tokens=True)
            if len(tokens) > 512:
                # Son 512 token'ı al (genelde sonuç yazının sonunda)
                tokens = tokens[-512:]
                text = self.topic_tokenizer.decode(tokens, skip_special_tokens=True)
            
            # Dönen yapı: [[{'label': 'LABEL_0', 'score': ...}, ...]]
            raw_result = self.topic_pipeline(text)[0]
            
            # Skora göre sırala (azalan)
            raw_result_sorted = sorted(raw_result, key=lambda x: x['score'], reverse=True)
            
            themes = []
            scores = {}
            
            # Threshold'u geçen temaları al (max 3)
            for item in raw_result_sorted:
                code = item['label']
                score = float(item['score'])
                
                # Eşik değerini geçenler
                if score >= threshold:
                    # İngilizce veya LABEL_X formatını Türkçe'ye çevir
                    human_label = self._get_turkish_label(code)
                    themes.append(human_label)
                    scores[human_label] = round(score, 2)
                    
                    if len(themes) >= 3:
                        break
            
            # Hiç tema bulunamadıysa en yüksek skorluyu al
            if not themes:
                best = raw_result_sorted[0]
                human_label = self._get_turkish_label(best['label'])
                themes = [human_label]
                scores = {human_label: round(float(best['score']), 2)}
            
            main_topic = themes[0] if themes else 'Genel'
            
            # Belirsizlik kontrolü (birden fazla yakın skorlu tema varsa)
            is_ambiguous = False
            if len(themes) >= 2:
                top_score = scores[themes[0]]
                second_score = scores[themes[1]]
                # Fark 0.1'den küçükse belirsiz
                is_ambiguous = (top_score - second_score) < 0.1
            
            # Gelişmiş keyword extraction
            keywords = self._extract_keywords(text, n=8)
            
            return {
                'themes': themes,
                'keywords': keywords,
                'main_topic': main_topic,
                'scores': scores,
                'is_ambiguous': is_ambiguous,
                'threshold_used': threshold
            }
            
        except Exception as e:
            print(f"❌ Theme analysis error: {e}")
            return {
                'themes': ['Genel'],
                'keywords': [],
                'main_topic': 'Genel',
                'scores': {},
                'is_ambiguous': False,
                'error': str(e)
            }
    
    def _get_turkish_label(self, label: str) -> str:
        """
        Model etiketini Türkçe'ye çevir
        
        Args:
            label (str): Model etiketi (LABEL_0, world, economy, vb.)
            
        Returns:
            str: Türkçe etiket
        """
        # Önce LABEL_X formatını kontrol et
        if label in self.topic_code_to_label:
            return self.topic_code_to_label[label]
        
        # İngilizce etiketi kontrol et (küçük harfe çevir)
        label_lower = label.lower().strip()
        if label_lower in self.english_to_turkish:
            return self.english_to_turkish[label_lower]
        
        # Bulunamazsa capitalize et ve döndür
        return label.capitalize()
    
    def _extract_keywords(self, text: str, n: int = 8) -> list:
        """
        Gelişmiş keyword extraction - Türkçe için optimize edilmiş
        
        Args:
            text (str): Metin
            n (int): Kaç keyword çıkarılacak
            
        Returns:
            list: Anahtar kelimeler
        """
        # Genişletilmiş Türkçe stop-words
        stop_words = {
            'bir', 've', 'bu', 'da', 'de', 'için', 'ile', 'mi', 'mı', 'mu', 'mü',
            'daha', 'çok', 'ama', 'ya', 'gibi', 'şu', 'o', 'ki', 'her', 'ne', 
            'var', 'yok', 'ben', 'sen', 'biz', 'siz', 'onlar', 'şey', 'kadar',
            'sonra', 'önce', 'artık', 'henüz', 'bile', 'sadece', 'ancak', 'veya',
            'ise', 'eğer', 'nasıl', 'neden', 'niçin', 'nerede', 'ne zaman',
            'hiç', 'bazen', 'belki', 'mutlaka', 'kesinlikle', 'zaten', 'aslında',
            'yani', 'mesela', 'örneğin', 'şimdi', 'böyle', 'şöyle', 'benim',
            'senin', 'onun', 'bizim', 'sizin', 'diye', 'demek', 'olmak',
            'etmek', 'yapmak', 'vermek', 'almak', 'görmek', 'buna', 'şunu',
            'bunu', 'bunun', 'şunun', 'onun', 'olan', 'oldu', 'olur', 'olarak'
        }
        
        # Kelime ayırma ve temizleme
        import re
        words = re.findall(r'\b[a-zçğıöşü]+\b', text.lower())
        
        # Filtreleme
        keywords = [w for w in words 
                   if len(w) > 3 and w not in stop_words and not w.isdigit()]
        
        # Frekans analizi
        from collections import Counter
        keyword_counts = Counter(keywords)
        
        # En sık geçen n kelime
        top_keywords = [word for word, count in keyword_counts.most_common(n)]
        
        return top_keywords
    
    def analyze_combined(self, text: str) -> dict:
        """
        Hem duygu hem tema analizini birlikte yap
        
        Args:
            text (str): Analiz edilecek metin
            
        Returns:
            dict: {
                'sentiment': {...},
                'theme': {...}
            }
        """
        sentiment = self.analyze_sentiment(text)
        theme = self.analyze_theme(text)
        
        return {
            'sentiment': sentiment,
            'theme': theme
        }
