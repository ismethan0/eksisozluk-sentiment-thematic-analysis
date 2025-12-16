"""
Farklı modelleri test et ve en iyisini bul
"""
import os
import pandas as pd
from services.nlp_service import NLPService

# Test edilecek model konfigürasyonları
MODEL_CONFIGS = [
    {
        'name': 'TurkishBERTweet+LoRA',
        'SENTIMENT_MODEL_NAME': 'VRLLab/TurkishBERTweet',
        'SENTIMENT_ADAPTER_NAME': 'VRLLab/TurkishBERTweet-Lora-SA',
        'SENTIMENT_NUM_LABELS': '3'
    },
    {
        'name': 'XLM-RoBERTa',
        'SENTIMENT_MODEL_NAME': 'incidelen/xlm-roberta-base-turkish-sentiment-analysis',
        'SENTIMENT_ADAPTER_NAME': '',
        'SENTIMENT_NUM_LABELS': '3'
    },
    {
        'name': 'BERTurk-Sentiment',
        'SENTIMENT_MODEL_NAME': 'savasy/bert-turkish-sentiment-cased',
        'SENTIMENT_ADAPTER_NAME': '',
        'SENTIMENT_NUM_LABELS': '3'
    }
]

def test_model(config, test_data):
    """Bir model konfigürasyonunu test et"""
    print(f"\n{'='*60}")
    print(f"Testing: {config['name']}")
    print('='*60)
    
    # Environment variables ayarla
    for key, value in config.items():
        if key != 'name':
            os.environ[key] = value
    
    try:
        # NLP servisini yeniden yükle
        nlp_service = NLPService()
        
        # Test et
        results = []
        for idx, row in test_data.iterrows():
            try:
                sentiment_result = nlp_service.analyze_sentiment(row['body'])
                sentiment_map = {'negative': 0, 'neutral': 1, 'positive': 2}
                pred = sentiment_map.get(sentiment_result['sentiment'], 1)
                results.append(pred)
            except:
                results.append(1)  # Default neutral
        
        # Accuracy hesapla
        test_data['pred'] = results
        correct = (test_data['RDuygu'] == test_data['pred']).sum()
        accuracy = correct / len(test_data)
        
        print(f"\n✅ Results:")
        print(f"   Accuracy: {accuracy:.2%} ({correct}/{len(test_data)})")
        
        return {
            'model': config['name'],
            'accuracy': accuracy,
            'correct': correct,
            'total': len(test_data)
        }
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return {
            'model': config['name'],
            'accuracy': 0.0,
            'correct': 0,
            'total': len(test_data),
            'error': str(e)
        }

if __name__ == "__main__":
    # Test verisini yükle
    print("📖 Loading test data...")
    df = pd.read_excel('test2.xlsx')
    df = df[(df['body'].notna()) & (df['RDuygu'].notna())]
    print(f"   Loaded {len(df)} samples")
    
    # Her modeli test et
    results = []
    for config in MODEL_CONFIGS:
        result = test_model(config, df.copy())
        results.append(result)
    
    # Sonuçları karşılaştır
    print(f"\n\n{'='*60}")
    print("COMPARISON")
    print('='*60)
    
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('accuracy', ascending=False)
    
    print(results_df.to_string(index=False))
    
    print(f"\n🏆 Best model: {results_df.iloc[0]['model']}")
    print(f"   Accuracy: {results_df.iloc[0]['accuracy']:.2%}")
    
    # Kaydet
    results_df.to_csv('model_comparison.csv', index=False)
    print(f"\n✅ Results saved to: model_comparison.csv")
