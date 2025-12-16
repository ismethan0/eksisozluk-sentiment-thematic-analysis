"""
NLP Servis Katmanı
Gerçek transformer modelleriyle duygu ve tema analizi
"""

import os
import torch
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
from transformers.utils import logging as hf_logging
from vnlp import SentenceSplitter, Normalizer

class NLPService:
    def __init__(self):
        try:
            print("Loading NLP models...")
            # HF logging seviyesini azalt
            hf_logging.set_verbosity_error()
            
            # VNLP araçları
            print("  Loading VNLP tools...")
            self.sentence_splitter = SentenceSplitter()
            self.normalizer = Normalizer()
            print("  VNLP tools loaded")
            
            # Model cache
            self.model_cache_dir = os.path.join(os.path.dirname(__file__), "..", "models")
            os.makedirs(self.model_cache_dir, exist_ok=True)
            print(f"  Model cache directory: {os.path.abspath(self.model_cache_dir)}")

            # Device seçimi (env ile override: NLP_DEVICE=cpu|cuda)
            env_dev = os.getenv("NLP_DEVICE", "").strip().lower()
            if env_dev in ("cpu", "cuda"):
                device = 0 if env_dev == "cuda" and torch.cuda.is_available() else -1
            else:
                device = 0 if torch.cuda.is_available() else -1
            self.device = device
            # Dinamik son cümle ağırlıkları (env ile konfigüre)
            def _env_float(name: str, default: float) -> float:
                try:
                    return float(os.getenv(name, str(default)).strip())
                except Exception:
                    return default
            self.last_weight_short = _env_float('LAST_WEIGHT_SHORT', 1.1)   # 1–3 cümle
            self.last_weight_medium = _env_float('LAST_WEIGHT_MEDIUM', 2.0) # 4–7 cümle
            self.last_weight_long = _env_float('LAST_WEIGHT_LONG', 3.0)     # 8+ cümle
            if device == 0:
                print("  Using GPU:", torch.cuda.get_device_name(0))
            else:
                print("  Using CPU")

            # Sentiment modeli (env ile seçilebilir)
            self.sentiment_model_name = os.getenv(
                "SENTIMENT_MODEL_NAME",
                "incidelen/xlm-roberta-base-turkish-sentiment-analysis"
            ).strip()
            print(f"  Loading sentiment model: {self.sentiment_model_name}")

            trust_remote = os.getenv('HF_TRUST_REMOTE_CODE', 'true').lower() in ('1','true','yes')
            sentiment_adapter = os.getenv('SENTIMENT_ADAPTER_NAME')
            sentiment_num_labels = int(os.getenv('SENTIMENT_NUM_LABELS', '3'))

            # Adapter varsa: base=sentiment_model_name üzerinden yükle ve adapter'ı bağla
            if sentiment_adapter:
                print(f"  Using PEFT adapter: {sentiment_adapter}")
                try:
                    from peft import PeftModel, PeftConfig
                except ImportError:
                    raise RuntimeError("PEFT not installed. Please run 'pip install peft'.")

                tok = AutoTokenizer.from_pretrained(
                    self.sentiment_model_name,
                    cache_dir=self.model_cache_dir,
                    trust_remote_code=trust_remote
                )
                base_cls = AutoModelForSequenceClassification.from_pretrained(
                    self.sentiment_model_name,
                    cache_dir=self.model_cache_dir,
                    trust_remote_code=trust_remote,
                    num_labels=sentiment_num_labels
                )
                try:
                    _ = PeftConfig.from_pretrained(sentiment_adapter)
                except Exception as e0:
                    print(f"  PeftConfig load warning: {e0}")
                model = PeftModel.from_pretrained(
                    base_cls,
                    sentiment_adapter,
                    cache_dir=self.model_cache_dir
                )
                model.eval()
                self.sentiment_pipeline = pipeline(
                    "text-classification",
                    model=model,
                    tokenizer=tok,
                    device=device,
                    top_k=None
                )
            else:
                # Doğrudan pipeline ile dene (trust_remote_code destekli)
                try:
                    self.sentiment_pipeline = pipeline(
                        "sentiment-analysis",
                        model=self.sentiment_model_name,
                        tokenizer=self.sentiment_model_name,
                        device=device,
                        use_fast=False,
                        cache_dir=self.model_cache_dir,
                        trust_remote_code=trust_remote
                    )
                except Exception as e1:
                    print(f"  \u26a0\ufe0f Pipeline load failed, trying Auto* loaders: {e1}")
                    tok = AutoTokenizer.from_pretrained(
                        self.sentiment_model_name,
                        cache_dir=self.model_cache_dir,
                        trust_remote_code=trust_remote
                    )
                    mdl = AutoModelForSequenceClassification.from_pretrained(
                        self.sentiment_model_name,
                        cache_dir=self.model_cache_dir,
                        trust_remote_code=trust_remote
                    )
                    self.sentiment_pipeline = pipeline(
                        "text-classification",
                        model=mdl,
                        tokenizer=tok,
                        device=device,
                        top_k=None
                    )
            print("  Sentiment model loaded")

            # Tema/Konu analizi modeli - Türkçe haber sınıflandırma (savasy)
            print("  Loading topic model: savasy/bert-turkish-text-classification")
            self.topic_model_name = "savasy/bert-turkish-text-classification"
            self.topic_tokenizer = AutoTokenizer.from_pretrained(
                self.topic_model_name,
                cache_dir=self.model_cache_dir
            )
            self.topic_model = AutoModelForSequenceClassification.from_pretrained(
                self.topic_model_name,
                cache_dir=self.model_cache_dir
            )
            # top_k=None kullanarak tüm skorları al (return_all_scores yerine)
            self.topic_pipeline = pipeline(
                "text-classification",
                model=self.topic_model,
                tokenizer=self.topic_tokenizer,
                device=device,
                top_k=None
            )

            self.topic_code_to_label = {
                "LABEL_0": "Dünya",
                "LABEL_1": "Ekonomi",
                "LABEL_2": "Kültür",
                "LABEL_3": "Sağlık",
                "LABEL_4": "Siyaset",
                "LABEL_5": "Spor",
                "LABEL_6": "Teknoloji",
            }
            self.english_to_turkish = {
                "world": "Dünya",
                "economy": "Ekonomi",
                "culture": "Kültür",
                "health": "Sağlık",
                "politics": "Siyaset",
                "sport": "Spor",
                "technology": "Teknoloji"
            }

            print("  Topic model loaded")
            print("All NLP models loaded successfully!\n")

        except Exception as e:
            print(f"Error loading models: {e}")
            raise

        # Basit Türkçe duygu sözlüğü + domain ifadeleri
        self.positive_lexicon = {
            'tebrik', 'tebrikler', 'tebrik ederim', 'tebrik ediyorum', 'harika', 'mükemmel', 'süper',
            'başarılı', 'şahane', 'muhteşem', 'beğendim', 'memnun', 'iyi', 'güzel', 'takdir', 'takdir ediyorum',
            'olumlu', 'pozitif', 'seyirlik', 'efsane', 'kaliteli',
            'memnun kaldım', 'tavsiye ederim', 'çok iyi', 'olumlu izlenim', 'fiyat/performans iyi',
            'beklediğim gibi', 'sorunsuz', 'iyi çalışıyor', 'hızlı', 'dayanıklı', 'stabil'
        }
        self.negative_lexicon = {
            'rezalet', 'berbat', 'kötü', 'feci', 'iğrenç', 'nefret', 'beğenmedim', 'pişman', 'yetersiz',
            'olumsuz', 'negatif', 'vasat', 'saçma', 'korkunç', 'problem', 'sorun', 'arızalı', 'şikayet',
            'ısınma sorunu', 'ısınma problemi', 'şarjı çabuk bitiyor', 'batarya kötü', 'donuyor', 'takılıyor',
            'yavaş', 'geri iade', 'iade ettim', 'hatalı', 'kusurlu', 'servis kötü', 'garanti sorunlu',
            'memnun değilim', 'beklentiyi karşılamadı'
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
            # Son 10 cümleyi kullan (daha geniş bağlam)
            sentences = sentences[-10:] if len(sentences) > 10 else sentences
            inputs = sentences if sentences else [text]

            pipe_out = self.sentiment_pipeline(inputs)

            # Normalize outputs: pipeline may return list or list-of-lists
            def to_dict(res):
                # If already dict with 'label' and 'score'
                if isinstance(res, dict) and 'label' in res and 'score' in res:
                    return {'label': res['label'], 'score': float(res['score'])}
                # If list of candidates, pick max score
                if isinstance(res, list) and res and isinstance(res[0], dict):
                    best = max(res, key=lambda x: float(x.get('score', 0.0)))
                    return {'label': best.get('label', 'neutral'), 'score': float(best.get('score', 0.0))}
                # Fallback neutral
                return {'label': 'neutral', 'score': 0.5}

            # Normalize etiket
            def norm(res):
                lbl_raw = res.get('label', 'neutral')
                lbl = str(lbl_raw).lower().strip()
                conf = float(res.get('score', 0.5))
                # Map LABEL_0/1/2 to neg/neu/pos (common for 3-class Turkish models)
                if lbl.startswith('label_'):
                    try:
                        idx = int(lbl.split('_')[-1])
                        if idx == 0:
                            return 'negative', conf
                        if idx == 1:
                            return 'neutral', conf
                        if idx == 2:
                            return 'positive', conf
                    except Exception:
                        pass
                if 'pos' in lbl or 'olumlu' in lbl or 'positive' in lbl:
                    return 'positive', conf
                if 'neg' in lbl or 'olumsuz' in lbl or 'negative' in lbl:
                    return 'negative', conf
                if 'neutral' in lbl or 'nötr' in lbl:
                    return 'neutral', conf
                return 'neutral', 0.5

            # Oylama: her cümle için skor topla, son cümleye 2.0x ağırlık (nötr kaymayı azaltmak için)
            votes = {'positive': 0.0, 'negative': 0.0, 'neutral': 0.0}
            best_res = None
            best_sent = 'neutral'
            best_conf = 0.5
            # Dinamik son cümle ağırlığı: kısa metinlerde düşük, uzunlarda yüksek
            total_sentences = len(pipe_out)
            if total_sentences <= 3:
                last_weight = self.last_weight_short
            elif total_sentences <= 7:
                last_weight = self.last_weight_medium
            else:
                last_weight = self.last_weight_long

            for i, res in enumerate(pipe_out):
                res_norm = to_dict(res)
                s, c = norm(res_norm)
                w = last_weight if i == total_sentences - 1 and total_sentences > 1 else 1.0
                votes[s] += c * w
                # En güçlü tek karar adayı
                if (best_res is None) or (c > best_conf):
                    best_res = res_norm
                    best_sent = s
                    best_conf = c

            # Oy toplamına göre nihai duygu
            final_sent = max(votes.items(), key=lambda kv: kv[1])[0]
            # Eğer oy toplamı ile en güçlü tek karar çelişirse ve fark küçükse son cümleyi tercih et
            if final_sent != best_sent and (abs(votes[final_sent] - votes[best_sent]) < 0.35):
                final_sent = best_sent
                final_conf = best_conf
            else:
                # Nötr'e aşırı kaymayı azalt: pozitif/negatif kazandıysa minimum güveni artır
                base_conf = votes[final_sent] / max(1.0, len(pipe_out))
                if final_sent in ('positive', 'negative'):
                    final_conf = min(0.99, max(0.65, base_conf))  # pos/neg minimum 0.65
                else:
                    # Neutral için daha sıkı kontrol: sadece gerçekten belirsiz durumlarda
                    if base_conf < 0.55:  # Düşük güvenli neutral'ı en yüksek skorlu karar lehine çevir
                        alternatives = sorted(votes.items(), key=lambda kv: kv[1], reverse=True)
                        if len(alternatives) > 1 and alternatives[1][1] > 0.3:
                            final_sent = alternatives[1][0]  # İkinci en yüksek skoru al
                            final_conf = min(0.85, max(0.60, alternatives[1][1] / max(1.0, len(pipe_out))))
                        else:
                            final_conf = min(0.85, max(0.45, base_conf))
                    else:
                        final_conf = min(0.85, max(0.50, base_conf))

            # Sözlük tabanlı düzeltme (opsiyonel, çok kuvvetli ipuçlarında)
            lexicon_enabled = os.getenv('SENTIMENT_LEXICON_ENABLE', 'false').lower() in ('1','true','yes')
            if lexicon_enabled:
                lex_p, lex_n = self._lexicon_counts(inputs[-1] if inputs else text)
                if final_sent == 'negative' and lex_p >= 2 and lex_n == 0 and final_conf >= 0.75:
                    final_sent = 'positive'
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
        """Türkçe için VNLP ile yüksek doğruluklu cümle bölme."""
        try:
            sentences = self.sentence_splitter.split(text)
            # Trim + boşluk temizliği
            return [s.strip() for s in sentences if s.strip()]
        except Exception:
            # VNLP bir hata verirse regex fallback olsun
            import re
            parts = re.split(r"[\.\?!…\n]+", text)
            return [p.strip() for p in parts if p.strip()]

    def _lexicon_counts(self, text: str):
        """Pozitif/negatif sözlük eşleşmelerini say."""
        t = text.lower()
        pos = sum(1 for w in self.positive_lexicon if w in t)
        neg = sum(1 for w in self.negative_lexicon if w in t)
        return pos, neg

    def _preprocess_for_sentiment(self, text: str) -> str:
        """Duygu analizi için VNLP Normalizer ile gelişmiş ön işleme."""
        import re
        s = text
        
        try:
            # VNLP Normalizer ile yazım hatalarını düzelt ve normalizasyon yap
            s = self.normalizer.normalize(
                s,
                correct_typos=True,          # Yazım hatalarını düzelt
                deasciify=True,              # Türkçe karakterleri düzelt (e.g., "cok" -> "çok")
                remove_accent_marks=False,   # Aksanları koruy
                lower_case=True             # Büyük-küçük harf yapısını koru
            )
        except Exception as e:
            print(f"⚠️ Normalizer error: {e}, using basic preprocessing")
        
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
