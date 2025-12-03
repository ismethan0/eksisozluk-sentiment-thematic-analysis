# NLP Model Seçimi - Güncellenmiş Yaklaşım

## 🎯 Kullanılan Modeller

### Duygu Analizi
**Model:** `incidelen/xlm-roberta-base-turkish-sentiment-analysis`
- ✅ **Önceden eğitilmiş** - Ekstra eğitim gerektirmez
- ✅ XLM-RoBERTa tabanlı (çok dilli, Türkçe'de güçlü)
- ✅ Türkçe sentiment için optimize edilmiş
- ✅ HuggingFace pipeline ile kolay kullanım
- ⚡ GPU desteği (varsa otomatik kullanır)

**Çıktı Formatı:**
```json
{
  "label": "POSITIVE" | "NEUTRAL" | "NEGATIVE",
  "score": 0.95
}
```

### Tema Analizi
**Model:** `BERTopic + emrecan/bert-base-turkish-cased-mean-nli-stsb-tr`
- ✅ BERTopic - Unsupervised topic modeling
- ✅ Türkçe SentenceTransformer embeddings
- ✅ Otomatik tema keşfi
- ✅ Topic labeling ve visualization

---

## 📦 Kurulum

### 1. Gerekli Paketler
```powershell
pip install torch transformers sentencepiece
pip install bertopic sentence-transformers
pip install umap-learn hdbscan
```

### 2. Model İndirme

**Otomatik (İlk Kullanımda):**
Modeller ilk çalıştırmada HuggingFace Hub'dan otomatik indirilir.

**Manuel (Google Colab'da):**
```python
# Colab'da eğit/test, sonra Drive'a kaydet
sentiment_model.save_pretrained('/content/drive/MyDrive/eksisozluk_sentiment_model')
topic_model.save('/content/drive/MyDrive/eksisozluk_topic_model')
```

---

## 🚀 Kullanım

### Google Colab

1. `colab_training.py` içeriğini kopyala
2. Colab'da yeni notebook oluştur
3. GPU runtime seçin (T4 veya A100)
4. Hücreleri sırayla çalıştır:

```python
# CELL 1: GPU + Drive
import torch
print(f"GPU: {torch.cuda.get_device_name(0)}")
from google.colab import drive
drive.mount('/content/drive')

# CELL 2: Paket kurulumu
!pip install transformers bertopic sentence-transformers

# CELL 3: Veri yükleme
DATA_PATH = '/content/drive/MyDrive/eksisozluk_dataset.json'
# ... (veri yükleme kodu)

# CELL 4: Duygu modeli (önceden eğitilmiş)
from transformers import pipeline
sentiment_pipeline = pipeline(
    "sentiment-analysis",
    model="incidelen/xlm-roberta-base-turkish-sentiment-analysis",
    device=0
)

# CELL 5: Tema modeli eğitimi
from bertopic import BERTopic
topic_model = BERTopic(language="turkish")
topics, probs = topic_model.fit_transform(docs)

# CELL 6: Test
result = sentiment_pipeline("Bu çok güzel bir ürün!")
print(result)  # [{'label': 'POSITIVE', 'score': 0.99}]

# CELL 7: Kaydet
sentiment_pipeline.save_pretrained('/content/drive/MyDrive/models/sentiment')
topic_model.save('/content/drive/MyDrive/models/topic')
```

### Local Flask App

```python
# services/trained_nlp_service.py otomatik yükler
from services.trained_nlp_service import get_nlp_service

nlp = get_nlp_service()

# Tek metin analizi
result = nlp.analyze_sentiment("Harika bir ürün!")
# {'label': 'POSITIVE', 'score': 0.98}

# Batch analizi
results = nlp.analyze_sentiment_batch(["Güzel", "Kötü", "Normal"])

# Tema analizi
topics = nlp.analyze_topics(["Python programlama", "Makine öğrenmesi"])
```

---

## 🔄 İş Akışı

```
┌─────────────────────┐
│  1. LOCAL: Veri     │
│  collect_data.py    │
│  → JSON output      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  2. DRIVE: Upload   │
│  JSON → Drive       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  3. COLAB: Eğitim   │
│  • Sentiment: Zaten │
│    eğitilmiş ✓      │
│  • Topic: Eğit      │
│    (5-10 dk)        │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  4. DRIVE: Kaydet   │
│  Models → Drive     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  5. LOCAL: İndir    │
│  Drive → models/    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  6. LOCAL: Kullan   │
│  Flask app.py       │
│  → API endpoints    │
└─────────────────────┘
```

---

## 📊 Performans

### Duygu Analizi
| Metric | Value |
|--------|-------|
| Model Size | ~550 MB |
| Inference Time | ~50ms/text (GPU) |
| Accuracy | ~89% (Türkçe benchmark) |
| Labels | 3 (POSITIVE, NEUTRAL, NEGATIVE) |

### Tema Analizi
| Metric | Value |
|--------|-------|
| Model Size | ~420 MB (embeddings) |
| Training Time | 5-10 dk (1500 docs) |
| Topics Found | Auto (typically 10-30) |
| Visualization | ✅ HTML exports |

---

## 🎓 Avantajlar

### Önceki Yaklaşım (BERTurk Eğitimi)
- ❌ Manuel etiketleme gerekli (1000+ entry)
- ❌ Eğitim zamanı: 20-30 dakika
- ❌ Overfitting riski
- ❌ Veri kalitesi kritik

### Yeni Yaklaşım (XLM-RoBERTa Pre-trained)
- ✅ **Sıfır etiketleme** - Hemen kullan
- ✅ Eğitim zamanı: 0 dakika (zaten eğitilmiş)
- ✅ Geniş veri seti ile eğitilmiş (robust)
- ✅ Production-ready

---

## 🔍 API Örnekleri

### Sentiment Endpoint
```bash
POST /api/analyze/sentiment
{
  "text": "Bu film gerçekten çok güzeldi!"
}

# Response
{
  "success": true,
  "data": {
    "sentiment": "POSITIVE",
    "score": 0.9876,
    "model": "trained"
  }
}
```

### Batch Endpoint
```bash
POST /api/analyze/batch
{
  "entries": [
    {"id": 1, "text": "Mükemmel ürün"},
    {"id": 2, "text": "Berbat deneyim"}
  ]
}

# Response
{
  "success": true,
  "data": {
    "summary": {
      "sentiment_distribution": {
        "POSITIVE": 1,
        "NEGATIVE": 1
      }
    },
    "entries": [...]
  }
}
```

---

## 🛠️ Troubleshooting

### Problem: "Model not found"
```powershell
# İlk çalıştırmada otomatik indirilir
# Manuel indirme:
python -c "from transformers import pipeline; pipeline('sentiment-analysis', model='incidelen/xlm-roberta-base-turkish-sentiment-analysis')"
```

### Problem: CUDA Out of Memory
```python
# CPU kullan
sentiment_pipeline = pipeline(..., device=-1)
```

### Problem: Slow inference
```python
# Batch kullan (çok daha hızlı)
results = nlp.analyze_sentiment_batch(texts)  # vs tek tek
```

---

## 📚 Kaynaklar

- [XLM-RoBERTa Model](https://huggingface.co/incidelen/xlm-roberta-base-turkish-sentiment-analysis)
- [BERTopic Docs](https://maartengr.github.io/BERTopic/)
- [Turkish SentenceTransformer](https://huggingface.co/emrecan/bert-base-turkish-cased-mean-nli-stsb-tr)
- [Transformers Pipeline](https://huggingface.co/docs/transformers/main_classes/pipelines)
