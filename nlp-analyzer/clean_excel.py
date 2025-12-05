import pandas as pd
import re
import html
from pathlib import Path

def clean_text(text):
    """Metni temizle: HTML, hatalı Türkçe karakterler, gereksiz boşluklar"""
    if pd.isna(text) or not isinstance(text, str):
        return text
    
    # HTML entity'lerini decode et
    text = html.unescape(text)
    
    # HTML taglerini temizle
    text = re.sub(r'<[^>]+>', '', text)
    
    # Hatalı Türkçe karakter düzeltmeleri
    char_map = {
        'Ä±': 'ı', 'Ä°': 'İ',
        'ÅŸ': 'ş', 'Åž': 'Ş',
        'Ã§': 'ç', 'Ã‡': 'Ç',
        'Ã¶': 'ö', 'Ã–': 'Ö',
        'Ã¼': 'ü', 'Ãœ': 'Ü',
        'ÄŸ': 'ğ', 'Äž': 'Ğ',
        '&#39;': "'",
        '&quot;': '"',
        '&amp;': '&',
        '&lt;': '<',
        '&gt;': '>',
    }
    
    for bad_char, good_char in char_map.items():
        text = text.replace(bad_char, good_char)
    
    # UTF-8 encoding sorunlarını düzelt
    try:
        # Eğer latin-1 olarak yanlış decode edilmişse düzelt
        if any(bad in text for bad in ['Ä±', 'Ã§', 'ÅŸ', 'Ã¶', 'Ã¼', 'ÄŸ']):
            text = text.encode('latin-1').decode('utf-8')
    except (UnicodeDecodeError, UnicodeEncodeError):
        pass
    
    # Birden fazla boşluğu tek boşluğa indir
    text = re.sub(r'\s+', ' ', text)
    
    # Başta ve sonda boşlukları temizle
    text = text.strip()
    
    # Gereksiz satır sonlarını temizle
    text = re.sub(r'\n+', ' ', text)
    
    return text

def clean_excel_file(input_file, output_file=None):
    """Excel dosyasını temizle"""
    print(f"📖 Dosya okunuyor: {input_file}")
    
    # Excel dosyasını oku
    df = pd.read_excel(input_file)
    
    print(f"📊 Toplam {len(df)} satır bulundu")
    print(f"📋 Kolonlar: {list(df.columns)}")
    
    # Tüm string kolonları temizle
    cleaned_count = 0
    for column in df.columns:
        if df[column].dtype == 'object':  # String kolonları
            print(f"🧹 '{column}' kolonu temizleniyor...")
            df[column] = df[column].apply(clean_text)
            cleaned_count += 1
    
    print(f"✅ {cleaned_count} kolon temizlendi")
    
    # Null değerleri temizle
    initial_count = len(df)
    df = df.dropna(subset=['body'])
    null_removed = initial_count - len(df)
    print(f"🗑️ {null_removed} null satır kaldırıldı")
    
    # Sadece link olan satırları kaldır
    url_pattern = r'^(https?://|www\.)[^\s]+$'
    initial_count = len(df)
    df = df[~df['body'].str.match(url_pattern, na=False)]
    link_removed = initial_count - len(df)
    print(f"🔗 {link_removed} sadece link olan satır kaldırıldı")
    
    # "bkz" geçen ve 20 harften az olan metinleri kaldır
    initial_count = len(df)
    df = df[~((df['body'].str.contains('bkz', case=False, na=False)) & (df['body'].str.len() < 20))]
    bkz_removed = initial_count - len(df)
    print(f"📝 {bkz_removed} 'bkz' geçen ve 20 harften az olan satır kaldırıldı")
    
    print(f"📊 Kalan toplam satır: {len(df)}")
    
    # Çıktı dosyası belirlenmemişse, aynı dosyanın üzerine yaz
    if output_file is None:
        output_file = input_file
    
    # Temizlenmiş veriyi kaydet
    df.to_excel(output_file, index=False, engine='openpyxl')
    print(f"💾 Temiz veri kaydedildi: {output_file}")
    
    return df

if __name__ == "__main__":
    # Dosya yolları
    workspace = Path(__file__).parent.parent
    input_file = workspace / "eksisozluk-api-master" / "eksisozluk_dataset.xlsx"
    output_file = workspace / "eksisozluk-api-master" / "eksisozluk_dataset_cleaned.xlsx"
    
    # Yedek oluştur
    backup_file = input_file.with_name(f"{input_file.stem}_backup{input_file.suffix}")
    if not backup_file.exists():
        print(f"💾 Yedek oluşturuluyor: {backup_file}")
        import shutil
        shutil.copy2(input_file, backup_file)
    
    # Excel'i temizle - yeni dosyaya kaydet
    clean_excel_file(input_file, output_file)
    
    print("\n✨ Temizleme işlemi tamamlandı!")
    print(f"📁 Temiz dosya: {output_file}")
