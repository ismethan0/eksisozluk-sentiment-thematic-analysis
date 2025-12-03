"""
NLP Servis Katmanı
Gerçek transformer modelleriyle duygu ve tema analizi
"""

import os
import torch
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
from transformers.utils import logging as hf_logging


class NLPService:
    """Sadece duygu ve tema analizi yapan NLP servis sınıfı"""
    
    def __init__(self):
        """Servis başlatıcı - Gerçek modelleri yükle"""
        print("🔄 Loading NLP models...")

        # Transformers log seviyesini kontrol et (varsayılan ERROR)
        log_level = os.getenv('HF_LOG_LEVEL', 'ERROR').upper()
        if log_level == 'ERROR':
            hf_logging.set_verbosity_error()
        elif log_level == 'WARNING':
            hf_logging.set_verbosity_warning()
        elif log_level == 'INFO':
            hf_logging.set_verbosity_info()
        else:
            hf_logging.set_verbosity_warning()

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

        # Basit Türkçe duygu sözlüğü (yüksek etki eden anahtarlar)
        self.positive_lexicon = {
            'tebrik', 'tebrikler', 'tebrik ederim', 'tebrik ediyorum', 'harika', 'mükemmel', 'süper',
            'başarılı', 'şahane', 'muhteşem', 'beğendim', 'memnun', 'iyi', 'güzel', 'takdir', 'takdir ediyorum',
            'olumlu', 'pozitif', 'seyirlik', 'efsane', 'kaliteli'
        }
        self.negative_lexicon = {
            'rezalet', 'berbat', 'kötü', 'feci', 'iğrenç', 'nefret', 'beğenmedim', 'pişman', 'yetersiz',
            'olumsuz', 'negatif', 'vasat', 'saçma', 'korkunç', 'problem', 'sorun', 'arızalı', 'şikayet'
        }
        
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
            # Ön işleme: bkz referansları, URL'ler, tekrarlı boşluklar
            text = self._preprocess_for_sentiment(text)

            # Token bazlı kesme (sentiment tokenizer kullan)
            try:
                tok = self.sentiment_pipeline.tokenizer
                tokens = tok.encode(text, add_special_tokens=True)
                if len(tokens) > 512:
                    tokens = tokens[-512:]
                    text = tok.decode(tokens, skip_special_tokens=True)
            except Exception:
                # Her ihtimale karşı karakter kesme
                if len(text) > 1024:
                    text = text[-1024:]

            # Cümle bazlı değerlendirme (çoğunluk + son cümleye ağırlık)
            sentences = self._split_sentences(text)
            # Son 5 cümleyi kullan (uzun metinlerde hız için)
            sentences = sentences[-5:] if len(sentences) > 5 else sentences
            inputs = sentences if sentences else [text]

            pipe_out = self.sentiment_pipeline(inputs)

            # Normalize etiket
            def norm(res):
                lbl = res['label'].lower()
                conf = float(res['score'])
                if 'pos' in lbl or 'olumlu' in lbl or 'positive' in lbl:
                    return 'positive', conf
                if 'neg' in lbl or 'olumsuz' in lbl or 'negative' in lbl:
                    return 'negative', conf
                return 'neutral', 0.5

            # Oylama: her cümle için skor topla, son cümleye 1.5x ağırlık
            votes = {'positive': 0.0, 'negative': 0.0, 'neutral': 0.0}
            best_res = None
            best_sent = 'neutral'
            best_conf = 0.5
            for i, res in enumerate(pipe_out):
                s, c = norm(res)
                w = 1.5 if i == len(pipe_out) - 1 and len(pipe_out) > 1 else 1.0
                votes[s] += c * w
                # En güçlü tek karar adayı
                if (best_res is None) or (c > best_conf):
                    best_res = res
                    best_sent = s
                    best_conf = c

            # Oy toplamına göre nihai duygu
            final_sent = max(votes.items(), key=lambda kv: kv[1])[0]
            # Eğer oy toplamı ile en güçlü tek karar çelişirse ve fark küçükse son cümleyi tercih et
            if final_sent != best_sent and (abs(votes[final_sent] - votes[best_sent]) < 0.2):
                final_sent = best_sent
                final_conf = best_conf
            else:
                final_conf = min(0.99, max(0.51, votes[final_sent] / max(1.0, len(pipe_out))))

            # Sözlük tabanlı düzeltme (çok kuvvetli ipuçlarında)
            lex_p, lex_n = self._lexicon_counts(inputs[-1] if inputs else text)
            if final_sent == 'negative' and lex_p >= 2 and lex_n == 0 and final_conf >= 0.75:
                # "tebrik ediyorum" gibi güçlü pozitif ipuçlarında düzelt
                final_sent = 'positive'
                # güveni çok yüksek göstermeyelim
                final_conf = max(0.6, min(0.85, final_conf - 0.05))

            if final_sent == 'positive' and lex_n >= 2 and lex_p == 0 and final_conf >= 0.75:
                final_sent = 'negative'
                final_conf = max(0.6, min(0.85, final_conf - 0.05))

            score = final_conf if final_sent == 'positive' else (-final_conf if final_sent == 'negative' else 0.0)

            return {
                'sentiment': final_sent,
                'score': round(score, 2),
                'confidence': round(final_conf, 2),
                'label': best_res['label'] if best_res else 'N/A'
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
            
            # Tüm skorları almak için top_k=None kullan (return_all_scores deprecate oldu)
            # Dönen yapı: [{'label': 'LABEL_0', 'score': ...}, ...]
            raw_result = self.topic_pipeline(text, top_k=None)
            
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

    def _last_sentence(self, text: str) -> str:
        """Basit Türkçe cümle bölme ile son cümleyi döndür."""
        import re
        parts = re.split(r"[\.\?!…\n]+", text)
        parts = [p.strip() for p in parts if p and p.strip()]
        return parts[-1] if parts else ''

    def _split_sentences(self, text: str) -> list:
        import re
        parts = re.split(r"[\.\?!…\n]+", text)
        parts = [p.strip() for p in parts if p and p.strip()]
        return parts

    def _lexicon_counts(self, text: str):
        """Pozitif/negatif sözlük eşleşmelerini say."""
        t = text.lower()
        pos = sum(1 for w in self.positive_lexicon if w in t)
        neg = sum(1 for w in self.negative_lexicon if w in t)
        return pos, neg

    def _preprocess_for_sentiment(self, text: str) -> str:
        """Duygu analizi için hafif ön işleme: bkz referansları, URL, fazla boşluk."""
        import re
        s = text
        # (bkz: ...) referanslarını kaldır
        s = re.sub(r"\(bkz:\s*[^\)]+\)", " ", s, flags=re.IGNORECASE)
        # URL'leri kaldır
        s = re.sub(r"https?://\S+", " ", s)
        # Fazla boşluk
        s = re.sub(r"\s+", " ", s)
        return s.strip()
    
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
