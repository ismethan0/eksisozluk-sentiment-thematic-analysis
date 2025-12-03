# Ekşi Sözlük NLP - Model Eğitimi İş Akışı

Google Colab'dan localhost API'ye erişilemediği için veri toplama ve model eğitimi ayrı yapılıyor.

## 📋 İş Akışı Özeti

```
1. LOCAL: Veri Toplama (collect_data.py)
   ↓
2. DRIVE: JSON Dosyasını Yükle
   ↓
3. COLAB: Model Eğitimi (colab_training.py)
   ↓
4. DRIVE: Eğitilmiş Modelleri Kaydet
   ↓
5. LOCAL: Modelleri İndir ve Kullan
```

---

## 🔧 Adım 1: Localde Veri Toplama

### 1.1 Node.js API'yi Başlat

```powershell
cd c:\Users\ismet\Desktop\Ders\4.sınıf\Dogal_dil\eksisozluk-api-master
npm start
```

API `http://localhost:3000` adresinde çalışacak.

### 1.2 Veri Toplama Script'ini Çalıştır

```powershell
cd c:\Users\ismet\Desktop\Ders\4.sınıf\Dogal_dil\nlp-analyzer
python collect_data.py
```

Bu script:
- ✅ 15 farklı başlıktan veri toplar
- ✅ Her başlık için 10 sayfa (yaklaşık 100 entry)
- ✅ Toplam ~1500 entry beklenebilir
- ✅ JSON formatında kaydeder: `eksisozluk_dataset_YYYYMMDD_HHMMSS.json`

**Toplanan Veri Formatı:**
```json
{
  "metadata": {
    "total_entries": 1523,
    "topics": ["teknoloji", "politika", ...],
    "collected_at": "2025-01-29T12:00:00"
  },
  "entries": [
    {
      "id": "123456",
      "author": "yazar_nick",
      "body": "entry metni...",
      "date": "12.01.2025",
      "fav_count": 5,
      "topic": "teknoloji",
      "page": 1
    }
  ]
}
```

### 1.3 Özelleştirme (Opsiyonel)

`collect_data.py` dosyasını düzenleyerek:
- Daha fazla başlık ekleyin
- Sayfa sayısını artırın (max_pages=20)
- Rate limiting ayarlayın (time.sleep)

---

## 📤 Adım 2: Google Drive'a Yükleme

1. Oluşan JSON dosyasını bulun: `eksisozluk_dataset_*.json`
2. Google Drive'ınızda bir klasör oluşturun: `Eksi_NLP_Project`
3. JSON dosyasını bu klasöre yükleyin

**Dizin Yapısı:**
```
Google Drive/
└── Eksi_NLP_Project/
    ├── eksisozluk_dataset_20250129_120000.json
    └── (eğitilmiş modeller buraya kaydedilecek)
```

---

## 🎓 Adım 3: Google Colab'da Model Eğitimi

### 3.1 Colab Notebook Oluştur

1. [Google Colab](https://colab.research.google.com/) açın
2. **Runtime → Change runtime type → GPU (T4)** seçin
3. Yeni notebook oluşturun

### 3.2 `colab_training.py` İçeriğini Kopyala

Bu repodaki `colab_training.py` dosyasını açın ve içeriği Colab'a yapıştırın.

**ÖNEMLİ:** 
```python
# CELL 3'te bu satırı güncelleyin:
DATA_PATH = '/content/drive/MyDrive/Eksi_NLP_Project/eksisozluk_dataset_20250129_120000.json'
```

### 3.3 Hücreleri Sırayla Çalıştır

| Hücre | Açıklama | Süre |
|-------|----------|------|
| CELL 1 | GPU kontrolü ve Drive mount | ~30 sn |
| CELL 2 | Paket kurulumu | ~2-3 dk |
| CELL 3 | Veri yükleme ve temizleme | ~10 sn |
| CELL 4 | Duygu analizi modeli eğitimi | ~10-20 dk |
| CELL 5 | Tema analizi (BERTopic) | ~5-10 dk |
| CELL 6 | Model testleri | ~30 sn |
| CELL 7 | Sonuçları kaydetme | ~1 dk |

**Toplam Süre:** ~20-35 dakika (T4 GPU ile)

### 3.4 Eğitim Sonrası Drive Kontrolü

Drive'da şunlar oluşacak:
```
Eksi_NLP_Project/
├── eksisozluk_dataset_20250129_120000.json
├── eksisozluk_sentiment_model/  ← Duygu analizi
│   ├── config.json
│   ├── pytorch_model.bin
│   └── tokenizer_config.json
├── eksisozluk_topic_model/      ← Tema analizi
│   └── ... (BERTopic dosyaları)
├── model_training_results.json
├── topic_visualization.html
└── topic_barchart.html
```

---

## 💾 Adım 4: Modelleri İndirme

### 4.1 Drive'dan İndir

Google Drive'dan şu klasörleri indirin:
- `eksisozluk_sentiment_model/`
- `eksisozluk_topic_model/`

### 4.2 Local Projeye Yerleştir

```powershell
cd c:\Users\ismet\Desktop\Ders\4.sınıf\Dogal_dil\nlp-analyzer

# models klasörü oluştur
mkdir models

# İndirilen modelleri kopyala
# Windows Explorer'dan models/ klasörüne yapıştırın
```

**Son dizin yapısı:**
```
nlp-analyzer/
├── models/
│   ├── eksisozluk_sentiment_model/
│   │   ├── config.json
│   │   ├── pytorch_model.bin
│   │   └── tokenizer_config.json
│   └── eksisozluk_topic_model/
│       └── (BERTopic dosyaları)
├── services/
│   └── trained_nlp_service.py
└── app.py
```

---

## 🚀 Adım 5: Local'de Modeli Kullanma

### 5.1 Gerekli Paketleri Yükle

```powershell
cd c:\Users\ismet\Desktop\Ders\4.sınıf\Dogal_dil\nlp-analyzer

# Eğer daha önce yüklemediyseniz:
pip install torch transformers bertopic sentence-transformers
```

### 5.2 Flask Uygulamasını Başlat

```powershell
python app.py
```

Başlangıçta şu mesajları görmelisiniz:
```
Loading sentiment model from models/eksisozluk_sentiment_model
✓ Sentiment model loaded
Loading topic model from models/eksisozluk_topic_model
✓ Topic model loaded
✓ Trained NLP models loaded successfully
 * Running on http://localhost:5000
```

### 5.3 Test Et

Frontend'den "Tümünü Analiz Et" butonuna basın. Artık:
- ✅ Eğitilmiş BERTurk modeli duygu analizi yapıyor
- ✅ BERTopic gerçek tema keşfi yapıyor
- ✅ Batch işleme çok daha hızlı

---

## 🔍 Sonuçları Kontrol Etme

### API Response Format

**Eğitilmiş model kullanıldığında:**
```json
{
  "success": true,
  "data": {
    "sentiment": "Positive",
    "score": 0.95,
    "all_scores": {
      "Negative": 0.02,
      "Neutral": 0.03,
      "Positive": 0.95
    },
    "model": "trained"  ← Eğitilmiş model kullanılıyor
  }
}
```

**Fallback (model yoksa):**
```json
{
  "data": {
    "sentiment": "positive",
    "model": "basic"  ← Basit sözlük tabanlı
  }
}
```

---

## ⚠️ Sorun Giderme

### Problem 1: "Import torch could not be resolved"

```powershell
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### Problem 2: "Sentiment model not found"

`app.py` çıktısını kontrol edin:
```
⚠ Sentiment model not found at models/eksisozluk_sentiment_model
  Using basic NLP service as fallback
```

**Çözüm:** Model dosyalarını doğru yere kopyalayın.

### Problem 3: Eğitim çok uzun sürüyor

Colab'da:
- **Runtime → Change runtime type → GPU** seçili mi?
- `training_args` içinde `per_device_train_batch_size=8` yapın (daha hızlı ama daha az doğru)
- `num_train_epochs=2` yapın

### Problem 4: Out of Memory (OOM)

```python
# CELL 4'te batch size'ı düşürün:
per_device_train_batch_size=8  # 16 yerine
```

---

## 📊 Veri Etiketleme (Gelişmiş)

Otomatik etiketleme yerine **manuel etiketleme** daha iyi sonuç verir.

### Basit Etiketleme Tool'u

```python
# label_data.py
import json

with open('eksisozluk_dataset.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

labeled = []
for entry in data['entries'][:100]:  # İlk 100 entry
    print(f"\n{entry['body']}")
    print("0=Negative, 1=Neutral, 2=Positive, s=Skip:")
    
    label = input()
    if label in ['0', '1', '2']:
        labeled.append({
            **entry,
            'sentiment_label': int(label)
        })

# Kaydet
with open('labeled_dataset.json', 'w', encoding='utf-8') as f:
    json.dump(labeled, f, ensure_ascii=False, indent=2)
```

---

## 🎯 Sonraki Adımlar

1. **Daha Fazla Veri:**
   - 5000-10000 entry toplayın
   - Çeşitli başlıklardan dengeli veri

2. **Manuel Etiketleme:**
   - 500-1000 entry'yi manuel etiketleyin
   - Daha doğru model eğitimi

3. **Fine-tuning:**
   - Etiketli veri ile modeli tekrar eğitin
   - Ekşi Sözlük diline özelleşmiş model

4. **Model Karşılaştırma:**
   - Basit vs Eğitilmiş model performansı
   - Confusion matrix ile analiz

5. **Deployment:**
   - Modeli küçültme (quantization)
   - API caching
   - Database entegrasyonu

---

## 📚 Kaynaklar

- [Transformers Documentation](https://huggingface.co/docs/transformers)
- [BERTopic Guide](https://maartengr.github.io/BERTopic/)
- [BERTurk Model](https://huggingface.co/dbmdz/bert-base-turkish-cased)
- [Google Colab Tips](https://colab.research.google.com/notebooks/welcome.ipynb)
