"""
Sadece duygu analizi için basitleştirilmiş script
Rkategori olmadan çalışır
"""

import os
import sys
import pandas as pd
from dotenv import load_dotenv

# .env dosyasını yükle
load_dotenv()

# NLP servisini import et
from services.nlp_service import NLPService

def analyze_test_data_simple(input_file='test2.xlsx', output_file='Sonuc.xlsx'):
    """
    Excel dosyasındaki entry'leri okuyup sadece duygu analizi yap
    Rkategori'ye ihtiyaç duymaz
    
    Args:
        input_file: Okunacak Excel dosyası
        output_file: Sonuçların yazılacağı Excel dosyası
    """
    print(f"📖 Reading file: {input_file}")
    
    try:
        # Excel dosyasını oku
        df = pd.read_excel(input_file)
        print(f"   Found {len(df)} rows")
        print(f"   Columns: {list(df.columns)}")
        
        # Gerekli sütunları kontrol et
        if 'body' not in df.columns or 'RDuygu' not in df.columns:
            print("❌ Required columns not found: body, RDuygu")
            return
        
        # Boş değerleri filtrele
        df_clean = df[(df['body'].notna()) & (df['body'] != '') & 
                      (df['RDuygu'].notna())].copy()
        
        print(f"   Valid rows: {len(df_clean)}")
        
        if len(df_clean) == 0:
            print("❌ No valid data found!")
            return
        
        # Tduygu ve Tkategori sütunları ekle
        df_clean['Tduygu'] = ''
        df_clean['Tkategori'] = ''
        
        # NLP servisini başlat
        print("\n🤖 Initializing NLP service...")
        nlp_service = NLPService()
        
        # Her entry için analiz yap
        print(f"\n🔬 Analyzing {len(df_clean)} entries...")
        
        sentiment_results = []
        category_results = []
        
        for idx, row in df_clean.iterrows():
            body_text = str(row['body'])
            
            try:
                # Hem duygu hem tema analizi
                combined_result = nlp_service.analyze_combined(body_text)
                
                # Duygu -> 0, 1, 2
                sentiment = combined_result['sentiment']['sentiment']
                sentiment_map = {
                    'negative': 0,
                    'neutral': 1,
                    'positive': 2
                }
                sentiment_code = sentiment_map.get(sentiment, 1)
                
                # Tema
                main_topic = combined_result['theme']['main_topic']
                
                sentiment_results.append(sentiment_code)
                category_results.append(main_topic)
                
                # İlerleme
                if len(sentiment_results) % 10 == 0:
                    print(f"   Progress: {len(sentiment_results)}/{len(df_clean)}")
                
            except Exception as e:
                print(f"   Error at row {idx}: {e}")
                sentiment_results.append('')
                category_results.append('')
        
        # Sonuçları yaz
        df_clean['Tduygu'] = sentiment_results
        df_clean['Tkategori'] = category_results
        
        # Kaydet
        print(f"\n💾 Saving results to: {output_file}")
        df_clean.to_excel(output_file, index=False)
        
        # Özet
        print("\n📊 Summary:")
        print("\n   RDuygu Distribution:")
        rduygu_counts = df_clean['RDuygu'].value_counts()
        for val, count in rduygu_counts.items():
            print(f"      {val}: {count}")
        
        print("\n   Tduygu Distribution:")
        tduygu_counts = df_clean['Tduygu'].value_counts()
        labels = {0: 'negative', 1: 'neutral', 2: 'positive'}
        for val, count in tduygu_counts.items():
            if val != '':
                print(f"      {val} ({labels.get(val, 'unknown')}): {count}")
        
        print("\n   Tkategori Distribution:")
        tkat_counts = df_clean['Tkategori'].value_counts().head(7)
        for cat, count in tkat_counts.items():
            print(f"      {cat}: {count}")
        
        # Accuracy
        print("\n🎯 Sentiment Accuracy:")
        valid = df_clean[df_clean['Tduygu'] != ''].copy()
        
        if len(valid) > 0:
            correct = (valid['RDuygu'] == valid['Tduygu']).sum()
            total = len(valid)
            accuracy = correct / total
            
            print(f"   Total: {total}")
            print(f"   Correct: {correct}")
            print(f"   Accuracy: {accuracy:.2%}")
            
            try:
                from sklearn.metrics import classification_report, confusion_matrix
                
                print("\n📈 Classification Report:")
                target_names = ['negative (0)', 'neutral (1)', 'positive (2)']
                print(classification_report(valid['RDuygu'], valid['Tduygu'], 
                                           target_names=target_names, zero_division=0))
                
                print("\n🔢 Confusion Matrix:")
                cm = confusion_matrix(valid['RDuygu'], valid['Tduygu'], labels=[0, 1, 2])
                
                print(f"{'':15} {'Pred-0':>10} {'Pred-1':>10} {'Pred-2':>10}")
                labels_text = ['True-0 (neg)', 'True-1 (neu)', 'True-2 (pos)']
                for i, label in enumerate(labels_text):
                    print(f"{label:15}", end='')
                    for j in range(3):
                        print(f"{cm[i][j]:>10}", end='')
                    print()
                
            except ImportError:
                print("   💡 Install scikit-learn: pip install scikit-learn")
        
        print(f"\n✅ Complete! Results saved to: {output_file}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    input_file = sys.argv[1] if len(sys.argv) > 1 else 'test2.xlsx'
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'Sonuc.xlsx'
    
    analyze_test_data_simple(input_file, output_file)
