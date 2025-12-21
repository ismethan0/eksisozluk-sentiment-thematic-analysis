"""
TestVeri_Duygulu.xlsx dosyasındaki entry'leri okuyup 
duygu analizini yapıp Twitter sütununa yazan script
"""

import os
import sys
import unicodedata
import pandas as pd
from dotenv import load_dotenv

# .env dosyasını yükle
load_dotenv()

# NLP servisini import et
from services.nlp_service import NLPService

def analyze_test_data(input_file='TestVeri_Duygulu.xlsx', output_file='TestVeri_Duygulu_Analyzed.xlsx', samples_per_category=10):
    """
    Excel dosyasındaki entry'leri okuyup duygu ve tema analizi yap
    Her kategoriden dengeli sayıda örnek seçer
    
    Sütunlar:
        body: Analiz edilecek metin
        RDuygu: Gerçek duygu etiketi
        Rkategori: Gerçek kategori
        Tduygu: Model tahmini (0=negative, 1=neutral, 2=positive)
        Tkategori: Model kategori tahmini
        topic: Gerçek kategori adı (Rkategori'den kopyalanır)
    
    Args:
        input_file: Okunacak Excel dosyası
        output_file: Sonuçların yazılacağı Excel dosyası
        samples_per_category: Her kategoriden kaç örnek alınacak (varsayılan: 10)
    """
    print(f"📖 Reading file: {input_file}")
    
    try:
        # Excel dosyasını oku
        df = pd.read_excel(input_file)
        print(f"   Found {len(df)} rows")
        
        # Sütun isimlerini kontrol et
        print(f"   Columns: {list(df.columns)}")
        
        # Gerekli sütunları kontrol et
        required_cols = ['body', 'RDuygu', 'Rkategori']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            print(f"❌ Gerekli sütunlar bulunamadı: {missing_cols}")
            print(f"   Mevcut sütunlar: {list(df.columns)}")
            return
        
        # Boş değerleri filtrele
        df_clean = df[(df['body'].notna()) & (df['body'] != '') & 
                      (df['RDuygu'].notna()) & (df['RDuygu'] != '') &
                      (df['Rkategori'].notna()) & (df['Rkategori'] != '')].copy()
        
        print(f"   Valid rows after filtering: {len(df_clean)}")
        
        # Her kategoriden dengeli örnekleme yap
        print(f"\n📊 Sampling {samples_per_category} entries per category...")
        
        # Kategori dağılımını göster
        category_counts = df_clean['Rkategori'].value_counts()
        print(f"   Available categories:")
        for cat, count in category_counts.items():
            print(f"      {cat}: {count} entries")
        
        # Her kategoriden örnek seç
        sampled_dfs = []
        for category in category_counts.index:
            cat_df = df_clean[df_clean['Rkategori'] == category]
            sample_size = min(samples_per_category, len(cat_df))
            sampled = cat_df.sample(n=sample_size, random_state=42)
            sampled_dfs.append(sampled)
            print(f"      Selected {sample_size} from {category}")
        
        # Örnekleri birleştir ve karıştır
        df_sampled = pd.concat(sampled_dfs, ignore_index=True)
        df_sampled = df_sampled.sample(frac=1, random_state=42).reset_index(drop=True)
        
        print(f"\n   Total samples selected: {len(df_sampled)}")
        
        # Yeni sütunlar ekle
        df_sampled['Tduygu'] = ''
        df_sampled['Tkategori'] = ''
        df_sampled['topic'] = df_sampled['Rkategori']  # topic = Rkategori
        
        print(f"   Columns: body, RDuygu, Rkategori, topic")
        print(f"   Will predict: Tduygu, Tkategori")
        
        # NLP servisini başlat
        print("\n🤖 Initializing NLP service...")
        nlp_service = NLPService()
        
        # Her entry için duygu ve tema analizi yap
        print(f"\n🔬 Analyzing {len(df_sampled)} entries...")
        
        sentiment_results = []
        category_results = []
        
        for idx, row in df_sampled.iterrows():
            body_text = str(row['body'])
            
            try:
                # Hem duygu hem tema analizi yap
                combined_result = nlp_service.analyze_combined(body_text)
                
                # Duygu analizi sonucu -> 0, 1, 2 formatında
                sentiment = combined_result['sentiment']['sentiment']
                sentiment_map = {
                    'negative': 0,
                    'neutral': 1,
                    'positive': 2
                }
                sentiment_code = sentiment_map.get(sentiment, 1)
                
                # Tema analizi sonucu
                main_topic = combined_result['theme']['main_topic']
                
                sentiment_results.append(sentiment_code)
                category_results.append(main_topic)
                
                # İlerleme göster (her 5 kayıtta bir)
                if (len(sentiment_results)) % 5 == 0:
                    print(f"   Progress: {len(sentiment_results)}/{len(df_sampled)}")
                
            except Exception as e:
                print(f"   [Row {idx}] Error: {e}")
                sentiment_results.append('')
                category_results.append('')
        
        # Sonuçları sütunlara yaz
        df_sampled['Tduygu'] = sentiment_results
        df_sampled['Tkategori'] = category_results
        
        print(f"\n   ✅ Analysis completed: {len(sentiment_results)} entries processed")
        
        # Sonuçları kaydet
        print(f"\n💾 Saving results to: {output_file}")
        df_sampled.to_excel(output_file, index=False)
        
        # Özet istatistikler
        total_samples = len(df_sampled)
        print("\n📊 Summary:")
        
        print("\n   Topic (Rkategori) Distribution:")
        topic_counts = df_sampled['topic'].value_counts()
        for topic, count in topic_counts.items():
            percentage = (count / total_samples) * 100
            print(f"      {topic}: {count} ({percentage:.1f}%)")
        
        print("\n   Tduygu Distribution:")
        sentiment_counts = df_sampled['Tduygu'].value_counts()
        sentiment_labels = {0: 'negative', 1: 'neutral', 2: 'positive'}
        for code, count in sentiment_counts.items():
            if code != '':
                percentage = (count / total_samples) * 100
                label = sentiment_labels.get(code, 'unknown')
                print(f"      {code} ({label}): {count} ({percentage:.1f}%)")
        
        print("\n   Tkategori Distribution:")
        category_counts = df_sampled['Tkategori'].value_counts()
        for category, count in category_counts.items():
            if category != '':
                percentage = (count / total_samples) * 100
                print(f"      {category}: {count} ({percentage:.1f}%)")
        
        # Doğruluk hesaplama
        print(f"\n🎯 Accuracy Metrics:")
        
        # RDuygu'yu 0,1,2 formatına çevir
        rduygu_map = {
            'negative': 0, 'neg': 0, 'olumsuz': 0, '-1': 0, -1: 0, 0: 0, '0': 0,
            'neutral': 1, 'neu': 1, 'nötr': 1, 'notr': 1, '0': 1, 0: 1, 1: 1, '1': 1,
            'positive': 2, 'pos': 2, 'olumlu': 2, '1': 2, 1: 2, 2: 2, '2': 2
        }
        
        # Geçerli satırları filtrele
        valid_mask = (df_sampled['Tduygu'] != '') & (df_sampled['RDuygu'] != '')
        valid_df = df_sampled[valid_mask].copy()
        
        if len(valid_df) > 0:
            # RDuygu'yu normalize et
            valid_df['RDuygu_normalized'] = valid_df['RDuygu'].apply(
                lambda x: rduygu_map.get(str(x).lower().strip(), rduygu_map.get(x, -1))
            )
            
            # Sadece başarıyla eşleşenleri al
            valid_df = valid_df[valid_df['RDuygu_normalized'].isin([0, 1, 2])]
            
            if len(valid_df) > 0:
                true_labels = valid_df['RDuygu_normalized']
                pred_labels = valid_df['Tduygu']
                
                print("\n   === SENTIMENT ACCURACY ===")
                
                # Accuracy hesapla
                correct = (true_labels == pred_labels).sum()
                total = len(valid_df)
                accuracy = correct / total
                
                print(f"   Total valid samples: {total}")
                print(f"   Correct predictions: {correct}")
                print(f"   Accuracy: {accuracy:.2%}")
                
                # Sklearn varsa detaylı metrikler
                try:
                    from sklearn.metrics import classification_report, confusion_matrix
                    
                    print("\n📈 Classification Report:")
                    target_names = ['negative (0)', 'neutral (1)', 'positive (2)']
                    print(classification_report(true_labels, pred_labels, target_names=target_names, zero_division=0))
                    
                    print("\n🔢 Confusion Matrix:")
                    cm = confusion_matrix(true_labels, pred_labels, labels=[0, 1, 2])
                    
                    # Confusion matrix'i güzel formatta yazdır
                    print(f"{'':15} {'Pred-0':>10} {'Pred-1':>10} {'Pred-2':>10}")
                    labels_text = ['True-0 (neg)', 'True-1 (neu)', 'True-2 (pos)']
                    for i, label in enumerate(labels_text):
                        print(f"{label:15}", end='')
                        for j in range(3):
                            print(f"{cm[i][j]:>10}", end='')
                        print()
                    
                except ImportError:
                    print("\n   💡 Tip: Install scikit-learn for detailed metrics:")
                    print("      pip install scikit-learn")
                
                # Kategori doğruluğu (Rkategori vs Tkategori)
                print("\n   === CATEGORY ACCURACY ===")
                valid_cat_mask = (df_sampled['Tkategori'] != '') & (df_sampled['Rkategori'] != '')
                valid_cat_df = df_sampled[valid_cat_mask].copy()
                
                if len(valid_cat_df) > 0:
                    def _normalize(label: object) -> str:
                        text = str(label).strip().lower().replace('’', "'").replace('‘', "'")
                        text = unicodedata.normalize('NFKD', text)
                        return text.encode('ascii', 'ignore').decode()

                    valid_cat_df['Rkategori_norm'] = valid_cat_df['Rkategori'].apply(_normalize)
                    valid_cat_df['Tkategori_norm'] = valid_cat_df['Tkategori'].apply(_normalize)

                    true_cat = valid_cat_df['Rkategori_norm']
                    pred_cat = valid_cat_df['Tkategori_norm']
                    
                    cat_correct = (true_cat == pred_cat).sum()
                    cat_total = len(valid_cat_df)
                    cat_accuracy = cat_correct / cat_total
                    
                    print(f"   Total samples: {cat_total}")
                    print(f"   Correct predictions: {cat_correct}")
                    print(f"   Category Accuracy: {cat_accuracy:.2%}")
                    
                    try:
                        from sklearn.metrics import classification_report
                        print("\n📈 Category Classification Report:")
                        print(classification_report(true_cat, pred_cat, zero_division=0))
                    except ImportError:
                        pass
                
            else:
                print("   ⚠️ No valid RDuygu labels found after normalization")
        else:
            print("   ⚠️ No valid samples found (both RDuygu and Tduygu must be non-empty)")
        
        print(f"\n✅ Analysis complete! Results saved to: {output_file}")
        
    except FileNotFoundError:
        print(f"❌ File not found: {input_file}")
        print("   Please make sure the file exists in the current directory.")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Komut satırından dosya adı ve örnek sayısı alınabilir
    input_file = sys.argv[1] if len(sys.argv) > 1 else 'TestVeri_Duygulu.xlsx'
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'TestVeri_Duygulu_Analyzed.xlsx'
    samples_per_category = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    
    analyze_test_data(input_file, output_file, samples_per_category)
