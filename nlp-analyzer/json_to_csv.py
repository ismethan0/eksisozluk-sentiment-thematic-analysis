"""
JSON dataset'i CSV'ye dönüştürür
Sadece body'leri alır ve sentiment sütunu ekler
Türkçe karakter düzeltmeleri ve HTML temizleme yapar
"""

import json
import csv
import sys
import re
import html

import html

def clean_text(text):
    """Metni temizle: HTML etiketleri kaldır, Türkçe karakterleri düzelt"""
    if not text:
        return ""
    
    # HTML entity'lerini decode et (&amp; -> &, &quot; -> ", vb.)
    text = html.unescape(text)
    
    # Yaygın HTML etiketlerini kaldır
    # <b>, <i>, <a>, <br>, <p>, vb.
    text = re.sub(r'<br\s*/?>', ' ', text)  # <br> -> boşluk
    text = re.sub(r'</?(?:b|i|u|strong|em|a|p|div|span)[^>]*>', '', text)  # Diğer etiketler
    text = re.sub(r'<[^>]+>', '', text)  # Kalan tüm HTML etiketleri
    
    # Türkçe karakter düzeltmeleri
    replacements = {
        'Ä±': 'ı', 'Ä°': 'İ',
        'ÄŸ': 'ğ', 'Äž': 'Ğ',
        'Ã§': 'ç', 'Ã‡': 'Ç',
        'ÅŸ': 'ş', 'Åž': 'Ş',
        'Ã¼': 'ü', 'Ãœ': 'Ü',
        'Ã¶': 'ö', 'Ã–': 'Ö',
        'Ã¢': 'â', 'Ã®': 'î', 'Ã»': 'û',
        'â€™': "'", 'â€œ': '"', 'â€': '"',
        'â€"': '–', 'â€"': '—',
        'â€¦': '...',
        # Daha fazla yaygın hatalı kodlamalar
        'Å': 'Ş', 'Ä': 'ğ',
        'Ã¼': 'ü', 'Ã§': 'ç',
    }
    
    for wrong, correct in replacements.items():
        text = text.replace(wrong, correct)
    
    # Fazla boşlukları temizle
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    return text

def convert_json_to_csv(json_file, csv_file):
    """JSON'u CSV'ye dönüştür"""
    
    # JSON dosyasını oku
    print(f"Reading: {json_file}")
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    entries = data.get('entries', [])
    print(f"Total entries: {len(entries)}")
    
    # CSV'ye yaz
    print(f"Writing to: {csv_file}")
    with open(csv_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        
        # Header
        writer.writerow(['body', 'sentiment'])
        
        # Body'leri temizle ve yaz, sentiment boş bırak (manuel etiketleme için)
        valid_count = 0
        skipped_count = 0
        for entry in entries:
            body = entry.get('body', '').strip()
            
            # Metni temizle
            cleaned_body = clean_text(body)
            
            # Boş veya çok kısa body'leri atla
            if cleaned_body and len(cleaned_body) > 10:
                writer.writerow([cleaned_body, ''])  # sentiment boş
                valid_count += 1
            else:
                skipped_count += 1
                skipped_count += 1
    
    print(f"✓ {valid_count} entries written to CSV")
    print(f"✓ {skipped_count} entries skipped (empty or too short)")
    print(f"✓ Sentiment column added (empty for manual labeling)")
    print(f"✓ HTML tags removed and Turkish characters fixed")

if __name__ == "__main__":
    # Dosya adını argüman olarak al veya varsayılan kullan
    if len(sys.argv) > 1:
        json_file = sys.argv[1]
    else:
        json_file = 'eksisozluk_dataset_20251129_140117.json'
    
    # CSV dosya adı
    csv_file = json_file.replace('.json', '_for_labeling.csv')
    
    convert_json_to_csv(json_file, csv_file)
    print(f"\n{'='*60}")
    print("Next steps:")
    print("1. Open CSV in Excel/Google Sheets")
    print("2. Fill sentiment column: 0=Negative, 1=Neutral, 2=Positive")
    print("3. Save as CSV")
    print("4. Use for model training")
    print(f"{'='*60}")
