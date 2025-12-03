"""
Ekşi Sözlük Veri Toplama Script'i
Localde API'den veri çeker ve JSON formatında kaydeder
"""

import requests
import json
import time
from datetime import datetime

# Localdeki Node.js API'nize bağlanır
API_BASE = "http://localhost:3000"

def collect_topic_data(slug, max_pages=5):
    """Bir başlıktan tüm entryleri toplar"""
    all_entries = []
    
    for page in range(1, max_pages + 1):
        try:
            url = f"{API_BASE}/api/baslik/{slug}?p={page}"
            print(f"Fetching: {slug} - Page {page}")
            
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                data = response.json()
                
                if 'entries' in data and data['entries']:
                    for entry in data['entries']:
                        all_entries.append({
                            'id': entry.get('id'),
                            'author': entry.get('author'),
                            'body': entry.get('body'),
                            'date': entry.get('date'),
                            'fav_count': entry.get('fav_count', 0),
                            'topic': slug,
                            'page': page
                        })
                    print(f"  ✓ {len(data['entries'])} entries collected")
                else:
                    print(f"  ⚠ No more entries on page {page}")
                    break
            else:
                print(f"  ✗ Error: {response.status_code}")
                break
                
            time.sleep(2)  # Rate limiting
            
        except Exception as e:
            print(f"  ✗ Exception: {str(e)}")
            break
    
    return all_entries

def main():
    # Çeşitli başlıklardan veri toplayın
    topics = [
        'teknoloji',
        'politika', 
        'spor',
        'sinema',
        'muzik',
        'kitap',
        'oyun',
        'yemek',
        'seyahat',
        'egitim',
        'ekonomi',
        'saglik',
        'bilim',
        'sanat',
        'iliskiler'
    ]
    
    dataset = []
    
    for topic in topics:
        print(f"\n{'='*60}")
        print(f"Collecting: {topic}")
        print(f"{'='*60}")
        
        entries = collect_topic_data(topic, max_pages=10)
        dataset.extend(entries)
        
        print(f"Total entries for {topic}: {len(entries)}")
        time.sleep(3)  # Başlıklar arası bekleme
    
    # JSON olarak kaydet
    output_file = f'eksisozluk_dataset_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'metadata': {
                'total_entries': len(dataset),
                'topics': topics,
                'collected_at': datetime.now().isoformat()
            },
            'entries': dataset
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*60}")
    print(f"✓ Dataset saved: {output_file}")
    print(f"✓ Total entries: {len(dataset)}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
