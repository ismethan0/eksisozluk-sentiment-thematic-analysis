"""
TestVeri_Duygulu.xlsx dosyasındaki entry'leri okuyup 
duygu analizini yapıp Twitter sütununa yazan script
"""

import os
import sys
import pandas as pd
from dotenv import load_dotenv

# .env dosyasını yükle
load_dotenv()

# NLP servisini import et
from services.nlp_service import NLPService

def analyze_test_data(input_file='TestVeri_Duygulu.xlsx', output_file='TestVeri_Duygulu_Analyzed.xlsx'):
    """
    Excel dosyasındaki entry'leri okuyup duygu analizi yap ve Twitter sütununa yaz
    
    Args:
        input_file: Okunacak Excel dosyası
        output_file: Sonuçların yazılacağı Excel dosyası
    """
    print(f"📖 Reading file: {input_file}")
    
    try:
        # Excel dosyasını oku
        df = pd.read_excel(input_file)
        print(f"   Found {len(df)} rows")
        
        # Sütun isimlerini kontrol et
        print(f"   Columns: {list(df.columns)}")
        
        # Entry sütununu bul (büyük/küçük harf duyarsız)
        entry_col = None
        twitter_col = None
        
        for col in df.columns:
            col_lower = str(col).lower()
            if 'entry' in col_lower or 'text' in col_lower or 'metin' in col_lower:
                entry_col = col
            if 'xroberta' in col_lower:
                twitter_col = col
        
        if entry_col is None:
            print("❌ Entry sütunu bulunamadı. Lütfen sütun isimlerini kontrol edin.")
            print(f"   Mevcut sütunlar: {list(df.columns)}")
            return
        
        print(f"   Entry column: {entry_col}")
        
        # Twitter sütunu yoksa oluştur
        if twitter_col is None:
            twitter_col = 'Twitter'
            df[twitter_col] = ''
            print(f"   Created new column: {twitter_col}")
        else:
            print(f"   Twitter column: {twitter_col}")
        
        # NLP servisini başlat
        print("\n🤖 Initializing NLP service...")
        nlp_service = NLPService()
        
        # Her entry için duygu analizi yap
        print(f"\n🔬 Analyzing {len(df)} entries...")
        results = []
        
        for idx, row in df.iterrows():
            entry_text = str(row[entry_col])
            
            # Boş entry'leri atla
            if pd.isna(entry_text) or entry_text.strip() == '' or entry_text == 'nan':
                results.append('neutral')
                print(f"   [{idx+1}/{len(df)}] Skipped (empty)")
                continue
            
            try:
                # Duygu analizi yap
                sentiment_result = nlp_service.analyze_sentiment(entry_text)
                sentiment = sentiment_result['sentiment']
                confidence = sentiment_result['confidence']
                
                results.append(sentiment)
                
                # İlerleme göster
                print(f"   [{idx+1}/{len(df)}] {sentiment} ({confidence:.2f}) - {entry_text[:50]}...")
                
            except Exception as e:
                print(f"   [{idx+1}/{len(df)}] Error: {e}")
                results.append('error')
        
        # Sonuçları Twitter sütununa yaz
        df[twitter_col] = results
        
        # Sonuçları kaydet
        print(f"\n💾 Saving results to: {output_file}")
        df.to_excel(output_file, index=False)
        
        # Özet istatistikler
        print("\n📊 Summary:")
        sentiment_counts = df[twitter_col].value_counts()
        for sentiment, count in sentiment_counts.items():
            percentage = (count / len(df)) * 100
            print(f"   {sentiment}: {count} ({percentage:.1f}%)")
        
        print(f"\n✅ Analysis complete! Results saved to: {output_file}")
        
    except FileNotFoundError:
        print(f"❌ File not found: {input_file}")
        print("   Please make sure the file exists in the current directory.")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Komut satırından dosya adı alınabilir
    input_file = sys.argv[1] if len(sys.argv) > 1 else 'TestVeri_Duygulu.xlsx'
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'TestVeri_Duygulu_Analyzed.xlsx'
    
    analyze_test_data(input_file, output_file)
