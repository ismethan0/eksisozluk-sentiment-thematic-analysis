# Ekşi Sözlük NLP Model Eğitimi
# Google Colab'da Çalıştırın

"""
KULLANIM:
1. collect_data.py ile localde veri toplayın
2. Oluşan JSON dosyasını Google Drive'a yükleyin
3. Bu notebook'u Colab'da çalıştırın
4. Eğitilen modelleri Drive'a kaydedin
5. Localde modelleri yükleyin ve kullanın
"""

# =============================================================================
# CELL 1: GPU Kontrolü ve Drive Bağlama
# =============================================================================
# GPU'nun aktif olduğunu kontrol edin
import torch
print(f"CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")

# Google Drive'ı bağla
from google.colab import drive
drive.mount('/content/drive')


# =============================================================================
# CELL 2: Gerekli Paketleri Yükle
# =============================================================================
!pip install transformers datasets accelerate sentencepiece torch
!pip install bertopic sentence-transformers umap-learn hdbscan
!pip install scikit-learn pandas matplotlib seaborn


# =============================================================================
# CELL 3: Veriyi Yükle
# =============================================================================
import json
import pandas as pd

# JSON dosyanızın Drive'daki yolunu güncelleyin
DATA_PATH = '/content/drive/MyDrive/eksisozluk_dataset_20250129_120000.json'

with open(DATA_PATH, 'r', encoding='utf-8') as f:
    data = json.load(f)

entries = data['entries']
df = pd.DataFrame(entries)

print(f"Total entries: {len(df)}")
print(f"\nSample data:")
print(df.head())

# Temiz veri kontrolü
df = df.dropna(subset=['body'])  # Boş entryleri çıkar
df = df[df['body'].str.len() > 10]  # Çok kısa entryleri çıkar

print(f"\nCleaned entries: {len(df)}")


# =============================================================================
# CELL 4: Duygu Analizi Modeli - XLM-RoBERTa Turkish Sentiment
# =============================================================================
from transformers import (
    AutoTokenizer, 
    AutoModelForSequenceClassification,
    pipeline
)
import numpy as np

# Türkçe duygu analizi için önceden eğitilmiş model
model_name = "incidelen/xlm-roberta-base-turkish-sentiment-analysis"
print(f"Loading sentiment model: {model_name}")

sentiment_tokenizer = AutoTokenizer.from_pretrained(model_name)
sentiment_model = AutoModelForSequenceClassification.from_pretrained(model_name)

# Pipeline oluştur (daha kolay kullanım için)
sentiment_pipeline = pipeline(
    "sentiment-analysis",
    model=sentiment_model,
    tokenizer=sentiment_tokenizer,
    device=0 if torch.cuda.is_available() else -1
)

print("✓ Sentiment model loaded (pre-trained, no training needed)")

# Test modeli sample verilerle
print("\nTesting sentiment model on sample texts...")
test_samples = [
    "Bu film gerçekten çok güzeldi, herkese tavsiye ederim!",
    "Rezalet bir ürün, paramın boşa gitmesi",
    "Normal bir deneyimdi, ne iyi ne kötü"
]

for text in test_samples:
    result = sentiment_pipeline(text[:512])[0]  # Max 512 token
    print(f"Text: {text[:50]}...")
    print(f"  → {result['label']}: {result['score']:.2%}\n")

# Modeli Drive'a kaydet
sentiment_model.save_pretrained('/content/drive/MyDrive/eksisozluk_sentiment_model')
sentiment_tokenizer.save_pretrained('/content/drive/MyDrive/eksisozluk_sentiment_model')
print("✓ Sentiment model saved to Drive!")


# =============================================================================
# CELL 5: Tema Analizi (BERTopic)
# =============================================================================
from bertopic import BERTopic
from sentence_transformers import SentenceTransformer

# Türkçe için sentence transformer
embedding_model = SentenceTransformer("emrecan/bert-base-turkish-cased-mean-nli-stsb-tr")

# BERTopic modeli
topic_model = BERTopic(
    embedding_model=embedding_model,
    language="turkish",
    calculate_probabilities=True,
    verbose=True,
    min_topic_size=10
)

# Entry metinleri
docs = df['body'].tolist()

# Modeli eğit
print("Training BERTopic model...")
topics, probs = topic_model.fit_transform(docs)

# Tema bilgilerini görüntüle
print("\nTop topics:")
print(topic_model.get_topic_info().head(10))

# Modeli kaydet
topic_model.save('/content/drive/MyDrive/eksisozluk_topic_model')
print("✓ Topic model saved to Drive!")

# Visualizations (opsiyonel)
fig = topic_model.visualize_topics()
fig.write_html('/content/drive/MyDrive/topic_visualization.html')

fig = topic_model.visualize_barchart(top_n_topics=10)
fig.write_html('/content/drive/MyDrive/topic_barchart.html')


# =============================================================================
# CELL 6: Model Testleri
# =============================================================================
# Duygu analizi testi
test_texts = [
    "Bu film gerçekten çok güzeldi, herkese tavsiye ederim!",
    "Rezalet bir ürün, paramın boşa gitmesi",
    "Normal bir deneyimdi, ne iyi ne kötü"
]

print("\nSentiment Analysis Test:")
for text in test_texts:
    result = sentiment_pipeline(text[:512])[0]
    print(f"\nText: {text}")
    print(f"Sentiment: {result['label']} ({result['score']:.2%})")

# Tema analizi testi
print("\n" + "="*60)
print("Topic Analysis Test:")
test_topics, test_probs = topic_model.transform(test_texts)
for text, topic in zip(test_texts, test_topics):
    if topic != -1:
        topic_words = topic_model.get_topic(topic)[:5]
        print(f"\nText: {text}")
        print(f"Topic {topic}: {', '.join([word for word, _ in topic_words])}")


# =============================================================================
# CELL 7: Sonuçları Kaydet
# =============================================================================
# Model performans metrikleri
results = {
    'sentiment_model': {
        'model_name': 'incidelen/xlm-roberta-base-turkish-sentiment-analysis',
        'type': 'pre-trained',
        'model_path': '/content/drive/MyDrive/eksisozluk_sentiment_model'
    },
    'topic_model': {
        'total_documents': len(docs),
        'num_topics': len(topic_model.get_topic_info()) - 1,  # -1 for outlier topic
        'model_path': '/content/drive/MyDrive/eksisozluk_topic_model'
    }
}

with open('/content/drive/MyDrive/model_training_results.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print("✓ Training complete! Models saved to Google Drive")
print("\nNext steps:")
print("1. Download models from Drive to your local machine")
print("2. Update Flask app to load these models")
print("3. Run predictions locally")
