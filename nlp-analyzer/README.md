# 🧠 Ekşi Sözlük NLP Analiz Uygulaması

Modern ve profesyonel bir doğal dil işleme uygulaması. Ekşi Sözlük başlıklarını arayıp, entry'leri analiz ederek **duygu analizi** ve **tema analizi** yapar.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-3.0.0-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

---

## 📋 İçindekiler

- [Özellikler](#-özellikler)
- [Teknolojiler](#-teknolojiler)
- [Kurulum](#-kurulum)
- [Kullanım](#-kullanım)
- [API Dokümantasyonu](#-api-dokümantasyonu)
- [Yapay Zeka Entegrasyonu](#-yapay-zeka-entegrasyonu)
- [Proje Yapısı](#-proje-yapısı)
- [Ekran Görüntüleri](#-ekran-görüntüleri)
- [Geliştirme](#-geliştirme)

---

## ✨ Özellikler

### 🎯 Temel Özellikler
- ✅ Ekşi Sözlük başlık arama
- ✅ Otomatik tamamlama (autocomplete)
- ✅ Entry'leri sayfa sayfa görüntüleme
- ✅ Tek tek veya toplu entry analizi
- ✅ Duygu analizi (Pozitif/Nötr/Negatif)
- ✅ Tema analizi (Kategoriler ve anahtar kelimeler)
- ✅ Filtreleme (Duygu ve tema bazlı)
- ✅ İstatistikler ve grafikler
- ✅ Modern ve responsive tasarım

### 🎨 UI/UX Özellikleri
- Modern gradient renk paleti
- Smooth animasyonlar ve geçişler
- Responsive tasarım (Mobil uyumlu)
- Loading ve error state'leri
- Skeleton loading animasyonları
- Koyu/Açık tema desteği (gelecekte)

---

## 🛠 Teknolojiler

### Backend
- **Flask 3.0.0** - Web framework
- **Flask-CORS** - Cross-origin resource sharing
- **Requests** - HTTP kütüphanesi
- **Python-dotenv** - Environment variables

### Frontend
- **HTML5** - Semantic markup
- **CSS3** - Modern styling (Grid, Flexbox, CSS Variables)
- **JavaScript (ES6+)** - Vanilla JS (Framework yok!)
- **Font Awesome 6** - İkonlar

### NLP (Entegrasyon için hazır)
- PyTorch / TensorFlow
- Hugging Face Transformers
- NLTK / spaCy
- Scikit-learn

---

## 🚀 Kurulum

### Ön Gereksinimler

1. **Python 3.8+** yüklü olmalı
2. **Node.js** ve **npm** yüklü olmalı (Ekşi Sözlük API için)
3. **Git** yüklü olmalı

### Adım 1: Ekşi Sözlük API'yi Başlatın

Önce mevcut Ekşi Sözlük API'sini çalıştırın:

```bash
cd eksisozluk-api-master
npm install
npm run serve
```

API şu adreste çalışacak: `http://localhost:3000`

### Adım 2: NLP Analyzer'ı Kurun

```bash
# Proje dizinine gidin
cd nlp-analyzer

# Virtual environment oluşturun (önerilen)
python -m venv venv

# Virtual environment'ı aktif edin
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Gereksinimleri yükleyin
pip install -r requirements.txt

# Environment dosyasını oluşturun
copy .env.example .env
```

### Adım 3: Uygulamayı Başlatın

```bash
python app.py
```

Uygulama şu adreste çalışacak: `http://localhost:5000`

---

## 💻 Kullanım

### 1. Tarayıcıda Açın
```
http://localhost:5000
```

### 2. Başlık Arayın
- Arama kutusuna bir başlık yazın (örn: "yazılım", "teknoloji")
- Enter tuşuna basın veya ara butonuna tıklayın

### 3. Entry'leri İnceleyin
- Entry'ler sayfa sayfa görüntülenir
- Her entry için "Analiz Et" butonuna tıklayın
- Veya "Tümünü Analiz Et" ile hepsini birden analiz edin

### 4. Sonuçları Filtreleyin
- Duygu filtresinden pozitif/nötr/negatif seçin
- Tema filtresinden ilgilendiğiniz temayı seçin

### 5. İstatistikleri Görün
- Toplu analiz sonrası istatistikler otomatik görünür
- Pozitif, nötr, negatif dağılımını görün

---

## 📡 API Dokümantasyonu

### Base URL
```
http://localhost:5000/api
```

### Endpoints

#### 1. Başlık Arama
```http
GET /api/search?q={query}
```

**Örnek:**
```bash
curl "http://localhost:5000/api/search?q=yazilim"
```

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "title": "yazılım",
      "slug": "yazilim"
    }
  ]
}
```

#### 2. Otomatik Tamamlama
```http
GET /api/autocomplete?q={query}
```

#### 3. Başlık Detayı ve Entry'ler
```http
GET /api/topic/{slug}?page={page}
```

**Örnek:**
```bash
curl "http://localhost:5000/api/topic/yazilim?page=1"
```

**Response:**
```json
{
  "success": true,
  "data": {
    "title": "yazılım",
    "slug": "yazilim",
    "page": 1,
    "entries": [
      {
        "id": "123",
        "author": "yazar_nick",
        "content": "entry içeriği...",
        "date": "01.01.2025"
      }
    ],
    "total_entries": 10
  }
}
```

#### 4. Duygu Analizi
```http
POST /api/analyze/sentiment
Content-Type: application/json

{
  "text": "Analiz edilecek metin",
  "entry_id": "123"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "entry_id": "123",
    "sentiment": "positive",
    "score": 0.85,
    "confidence": 0.92
  }
}
```

#### 5. Tema Analizi
```http
POST /api/analyze/theme
Content-Type: application/json

{
  "text": "Analiz edilecek metin",
  "entry_id": "123"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "entry_id": "123",
    "themes": ["Teknoloji", "Eğitim"],
    "keywords": ["yazılım", "öğrenme", "kod"],
    "main_topic": "Teknoloji"
  }
}
```

#### 6. Toplu Analiz
```http
POST /api/analyze/batch
Content-Type: application/json

{
  "entries": [
    {
      "id": "123",
      "text": "entry metni 1"
    },
    {
      "id": "124",
      "text": "entry metni 2"
    }
  ]
}
```

#### 7. Sistem Durumu
```http
GET /api/stats
```

---

## 🤖 Yapay Zeka Entegrasyonu

Uygulama, yapay zeka modellerinizi kolayca entegre edebilmeniz için hazırlanmıştır.

### Duygu Analizi Entegrasyonu

`services/nlp_service.py` dosyasındaki `analyze_sentiment` metodunu düzenleyin:

```python
def analyze_sentiment(self, text):
    # ÖRNEKler:
    
    # 1. Hugging Face Transformers ile
    from transformers import pipeline
    sentiment_pipeline = pipeline("sentiment-analysis", 
                                  model="savasy/bert-base-turkish-sentiment-cased")
    result = sentiment_pipeline(text)[0]
    
    return {
        'sentiment': result['label'].lower(),  # positive/negative/neutral
        'score': result['score'],
        'confidence': result['score']
    }
    
    # 2. Custom Model ile
    # model = load_your_model()
    # prediction = model.predict(text)
    # return format_prediction(prediction)
```

### Tema Analizi Entegrasyonu

```python
def analyze_theme(self, text):
    # ÖRNEKler:
    
    # 1. Zero-shot Classification ile
    from transformers import pipeline
    classifier = pipeline("zero-shot-classification",
                         model="facebook/bart-large-mnli")
    
    candidate_labels = ["Teknoloji", "Politika", "Spor", "Sanat", ...]
    result = classifier(text, candidate_labels)
    
    return {
        'themes': result['labels'][:3],
        'keywords': extract_keywords(text),
        'main_topic': result['labels'][0]
    }
    
    # 2. Topic Modeling ile (LDA, NMF)
    # topics = topic_model.transform(text)
    # return format_topics(topics)
```

### Model Önerileri

#### Türkçe Duygu Analizi için:
- `savasy/bert-base-turkish-sentiment-cased`
- `dbmdz/bert-base-turkish-cased`
- Custom BERT modeli (kendi veri setinizle eğitebilirsiniz)

#### Türkçe Tema Analizi için:
- Zero-shot classification
- Topic Modeling (LDA, NMF)
- Named Entity Recognition (NER)
- Custom classification model

### Model Yükleme

`requirements.txt` dosyasındaki ilgili satırları aktif edin:

```txt
torch==2.1.0
transformers==4.35.0
nltk==3.8.1
```

Sonra yükleyin:
```bash
pip install -r requirements.txt
```

---

## 📁 Proje Yapısı

```
nlp-analyzer/
│
├── app.py                      # Flask ana uygulama
├── requirements.txt            # Python bağımlılıkları
├── .env.example               # Environment değişkenleri örneği
├── .gitignore                 # Git ignore dosyası
├── package.json               # Node.js metadata
├── README.md                  # Bu dosya
│
├── services/                  # İş mantığı katmanı
│   ├── __init__.py
│   ├── nlp_service.py        # NLP servisi (AI entegrasyonu buraya)
│   └── eksisozluk_service.py # Ekşi Sözlük API servisi
│
├── templates/                 # HTML şablonları
│   └── index.html            # Ana sayfa
│
└── static/                    # Statik dosyalar
    ├── css/
    │   └── style.css         # Ana CSS dosyası
    └── js/
        └── app.js            # Frontend JavaScript
```

---

## 📸 Ekran Görüntüleri

### Ana Sayfa
Modern ve sade arayüz ile başlık arama.

### Entry Listesi
Entry'leri sayfa sayfa görüntüleme ve analiz etme.

### Analiz Sonuçları
Duygu ve tema analizi badge'leri ile görselleştirme.

### İstatistikler
Toplu analiz sonrası duygu dağılımı ve tema istatistikleri.

---

## 🔧 Geliştirme

### Debug Modu

`.env` dosyasında:
```env
DEBUG=True
```

### Test Etme

```bash
# Unit testler için
pip install pytest pytest-flask
pytest tests/
```

### API Test Etme

```bash
# Curl ile
curl -X POST http://localhost:5000/api/analyze/sentiment \
  -H "Content-Type: application/json" \
  -d '{"text":"Bu çok güzel bir yazı"}'

# Postman veya Insomnia kullanabilirsiniz
```

### Loglama

`app.py` dosyasında Flask logging kullanılır:
```python
app.logger.info("Bilgi mesajı")
app.logger.error("Hata mesajı")
```

## 📝 Notlar

### Önemli Uyarılar

⚠️ **Şu anda NLP modelleri simüle edilmiştir!** Gerçek duygu ve tema analizleri için kendi modellerinizi entegre etmeniz gerekmektedir.

⚠️ **Ekşi Sözlük API'si çalışıyor olmalıdır** (`http://localhost:3000`)

⚠️ **Rate limiting yoktur** - Production için eklenmeli

### Performans İpuçları

- Toplu analiz yaparken API çağrıları paralel yapılır
- Büyük veri setleri için cache kullanın
- Model yükleme süresi ilk çağrıda uzun olabilir



## 🙏 Teşekkürler

- [Ekşi Sözlük API](https://github.com/coluck/eksisozluk-api) - Veri kaynağı
- Flask ve Python topluluğu
- Font Awesome - İkonlar


<div align="center">

**⭐ Projeyi beğendiyseniz yıldız vermeyi unutmayın!**

Made with ❤️ and ☕

</div>
