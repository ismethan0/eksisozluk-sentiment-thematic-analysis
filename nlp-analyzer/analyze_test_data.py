"""
TestVeri_Duygulu.xlsx dosyasındaki entry'leri okuyup 
duygu analizini yapıp Twitter sütununa yazan script
"""

import os
import sys
import time
import unicodedata
import pandas as pd
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

# .env dosyasını yükle
load_dotenv()

# NLP servisini import et
from services.nlp_service import NLPService

def analyze_test_data(input_file='TestVeri_Duygulu.xlsx', output_file='TestVeri_Duygulu_Analyzed.xlsx', samples_per_category=None):
    """
    Excel dosyasındaki entry'leri okuyup duygu ve tema analizi yap.
    İsteğe bağlı: Her kategoriden dengeli sayıda örnek seçer.
    
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
        samples_per_category: Her kategoriden kaç örnek alınacak.
                      None, 'all', 0 veya 'none' ise örnekleme yapılmaz
                      ve tüm geçerli satırlar işlenir.
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
        
        # Örnekleme: isteğe bağlı
        if samples_per_category is None or (isinstance(samples_per_category, int) and samples_per_category <= 0):
            print("\n📊 No sampling: processing all valid rows")
            df_sampled = df_clean.copy()
        else:
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
                sample_size = min(int(samples_per_category), len(cat_df))
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

        # Her çağrı için zaman aşımı (saniye)
        try:
            per_call_timeout = int(os.getenv('NLP_TIMEOUT_SEC', '45'))
        except Exception:
            per_call_timeout = 45
        print(f"   Per-entry timeout: {per_call_timeout}s (set NLP_TIMEOUT_SEC to change)")

        def _analyze_one(text: str):
            return nlp_service.analyze_combined(text)
        
        # Her entry için duygu ve tema analizi yap
        print(f"\n🔬 Analyzing {len(df_sampled)} entries...")
        
        sentiment_results = []
        category_results = []

        # Checkpoint ayarları
        try:
            save_every = int(os.getenv('CHECKPOINT_EVERY', '20'))
        except Exception:
            save_every = 20
        checkpoint_path = os.getenv('CHECKPOINT_PATH', output_file.replace('.xlsx', '_partial.xlsx'))

        def _save_partial(k: int):
            try:
                tmp_df = df_sampled.copy()
                if k > 0:
                    idxs = tmp_df.index[:k]
                    tmp_df.loc[idxs, 'Tduygu'] = sentiment_results[:k]
                    tmp_df.loc[idxs, 'Tkategori'] = category_results[:k]
                tmp_df.to_excel(checkpoint_path, index=False)
                print(f"   💾 Checkpoint saved ({k} rows) -> {checkpoint_path}")
            except Exception as e:
                print(f"   ⚠️ Checkpoint save failed: {e}")
        
        try:
            for idx, row in df_sampled.iterrows():
                body_text = str(row['body'])
                
                try:
                    # Hem duygu hem tema analizi yap (zaman aşımı ile)
                    start_ts = time.time()
                    # Her olası takılmada ana iş parçacığını korumak için tek kullanımlık executor
                    executor = ThreadPoolExecutor(max_workers=1)
                    future = executor.submit(_analyze_one, body_text)
                    try:
                        combined_result = future.result(timeout=per_call_timeout)
                    except FuturesTimeout:
                        print(f"   [Row {idx}] ⏳ Timeout after {per_call_timeout}s — skipping entry")
                        # Bu executor artık beklenmeden kapatılır; arka planda çalışan thread bırakılabilir
                        executor.shutdown(wait=False)
                        raise TimeoutError(f"analyze_combined timeout > {per_call_timeout}s")
                    except Exception as e_call:
                        executor.shutdown(wait=False)
                        raise e_call
                    else:
                        executor.shutdown(wait=True)
                    elapsed = time.time() - start_ts
                    if elapsed > per_call_timeout * 0.7:
                        print(f"   [Row {idx}] ⚠️ Slow call took {elapsed:.1f}s")

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
                        print(f"   Progress: {len(sentiment_results)}/{len(df_sampled)}", flush=True)

                    # Periyodik checkpoint
                    if save_every > 0 and (len(sentiment_results) % save_every == 0):
                        _save_partial(len(sentiment_results))
                
                except Exception as e:
                    print(f"   [Row {idx}] Error: {e}")
                    sentiment_results.append('')
                    category_results.append('')
                    if save_every > 0 and (len(sentiment_results) % save_every == 0):
                        _save_partial(len(sentiment_results))
        except KeyboardInterrupt:
            print("\n🛑 Interrupted by user. Saving checkpoint before exit...")
            _save_partial(len(sentiment_results))
            raise
        
        # Sonuçları sütunlara yaz
        df_sampled['Tduygu'] = sentiment_results
        df_sampled['Tkategori'] = category_results
        
        print(f"\n   ✅ Analysis completed: {len(sentiment_results)} entries processed")
        
        # Sonuçları kaydet
        print(f"\n💾 Saving results to: {output_file}")
        df_sampled.to_excel(output_file, index=False)
        
        # Özet istatistikler
        metrics_lines = []
        def mprint(s: str):
            print(s)
            metrics_lines.append(s)
        total_samples = len(df_sampled)
        mprint("\n📊 Summary:")
        
        mprint("\n   Topic (Rkategori) Distribution:")
        topic_counts = df_sampled['topic'].value_counts()
        for topic, count in topic_counts.items():
            percentage = (count / total_samples) * 100
            mprint(f"      {topic}: {count} ({percentage:.1f}%)")
        
        mprint("\n   Tduygu Distribution:")
        sentiment_counts = df_sampled['Tduygu'].value_counts()
        sentiment_labels = {0: 'negative', 1: 'neutral', 2: 'positive'}
        for code, count in sentiment_counts.items():
            if code != '':
                percentage = (count / total_samples) * 100
                label = sentiment_labels.get(code, 'unknown')
                mprint(f"      {code} ({label}): {count} ({percentage:.1f}%)")
        
        mprint("\n   Tkategori Distribution:")
        category_counts = df_sampled['Tkategori'].value_counts()
        for category, count in category_counts.items():
            if category != '':
                percentage = (count / total_samples) * 100
                mprint(f"      {category}: {count} ({percentage:.1f}%)")
        
        # Doğruluk hesaplama
        mprint(f"\n🎯 Accuracy Metrics:")
        
        # RDuygu'yu 0,1,2 formatına çevir (sağlam normalize)
        # Not: 0=olumsuz, 1=nötr, 2=olumlu
        rduygu_map = {
            'negative': 0, 'neg': 0, 'olumsuz': 0, '-1': 0, '0': 0,
            'neutral': 1, 'neu': 1, 'nötr': 1, 'notr': 1, '1': 1,
            'positive': 2, 'pos': 2, 'olumlu': 2, '2': 2
        }
        
        # Geçerli satırları filtrele
        valid_mask = (df_sampled['Tduygu'] != '') & (df_sampled['RDuygu'] != '')
        valid_df = df_sampled[valid_mask].copy()
        
        if len(valid_df) > 0:
            # RDuygu'yu normalize et (int/float/string varyantlarını yakala)
            def _normalize_rduygu(x):
                try:
                    # Sayısal ise doğrudan kontrol et
                    if isinstance(x, (int, float)):
                        xi = int(x)
                        return xi if xi in (0, 1, 2) else -1
                    # Metinsel ise sözlükten eşle
                    s = str(x).lower().strip()
                    return rduygu_map.get(s, -1)
                except Exception:
                    return -1

            valid_df['RDuygu_normalized'] = valid_df['RDuygu'].apply(_normalize_rduygu)
            
            # Sadece başarıyla eşleşenleri al
            valid_df = valid_df[valid_df['RDuygu_normalized'].isin([0, 1, 2])]
            
            if len(valid_df) > 0:
                # Tduygu'yu güvenli şekilde int'e çevir ve sadece 0/1/2 olanları kullan
                valid_df['Tduygu_int'] = pd.to_numeric(valid_df['Tduygu'], errors='coerce')
                valid_df = valid_df[valid_df['Tduygu_int'].isin([0, 1, 2])]
                true_labels = valid_df['RDuygu_normalized'].astype(int)
                pred_labels = valid_df['Tduygu_int'].astype(int)
                
                mprint("\n   === SENTIMENT ACCURACY ===")
                
                # Accuracy hesapla
                correct = (true_labels == pred_labels).sum()
                total = len(valid_df)
                accuracy = correct / total
                
                mprint(f"   Total valid samples: {total}")
                mprint(f"   Correct predictions: {correct}")
                mprint(f"   Accuracy: {accuracy:.2%}")
                
                # Sklearn varsa detaylı metrikler
                try:
                    from sklearn.metrics import classification_report, confusion_matrix

                    mprint("\n📈 Classification Report:")
                    target_names = ['negative (0)', 'neutral (1)', 'positive (2)']
                    try:
                        report_text = classification_report(true_labels, pred_labels, labels=[0, 1, 2], target_names=target_names, zero_division=0)
                        mprint(report_text)
                    except Exception as e:
                        mprint(f"   ⚠️ Could not compute classification report: {e}")

                    mprint("\n🔢 Confusion Matrix:")
                    cm = confusion_matrix(true_labels, pred_labels, labels=[0, 1, 2])

                    # Confusion matrix'i güzel formatta yazdır
                    mprint(f"{'':15} {'Pred-0':>10} {'Pred-1':>10} {'Pred-2':>10}")
                    labels_text = ['True-0 (neg)', 'True-1 (neu)', 'True-2 (pos)']
                    for i, label in enumerate(labels_text):
                        row_str = f"{label:15}"
                        for j in range(3):
                            row_str += f"{cm[i][j]:>10}"
                        mprint(row_str)

                except ImportError:
                    mprint("\n   💡 Tip: Install scikit-learn for detailed metrics:")
                    mprint("      pip install scikit-learn")
                
                # Kategori doğruluğu (Rkategori vs Tkategori)
                mprint("\n   === CATEGORY ACCURACY ===")
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
                    
                    mprint(f"   Total samples: {cat_total}")
                    mprint(f"   Correct predictions: {cat_correct}")
                    mprint(f"   Category Accuracy: {cat_accuracy:.2%}")
                    
                    try:
                        from sklearn.metrics import classification_report
                        mprint("\n📈 Category Classification Report:")
                        try:
                            cat_report_text = classification_report(true_cat, pred_cat, zero_division=0)
                            mprint(cat_report_text)
                        except Exception as e:
                            mprint(f"   ⚠️ Could not compute category classification report: {e}")
                    except ImportError:
                        pass
                
            else:
                mprint("   ⚠️ No valid RDuygu labels found after normalization")
        else:
            mprint("   ⚠️ No valid samples found (both RDuygu and Tduygu must be non-empty)")
        
        # Metrikleri dosyaya kaydet
        base, ext = os.path.splitext(output_file)
        metrics_file = f"{base}_metrics.txt"
        try:
            with open(metrics_file, 'w', encoding='utf-8') as f:
                f.write("\n".join(metrics_lines) + "\n")
            print(f"\n📝 Metrics saved to: {metrics_file}")
        except Exception as e:
            print(f"\n⚠️ Could not save metrics file: {e}")

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
    if len(sys.argv) > 3:
        arg = sys.argv[3].strip().lower()
        if arg in ('all', 'none', '0'):
            samples = None
        else:
            try:
                samples = int(arg)
            except Exception:
                samples = None
    else:
        samples = None
    
    analyze_test_data(input_file, output_file, samples)
