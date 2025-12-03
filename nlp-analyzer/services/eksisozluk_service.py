"""
Ekşi Sözlük API Servis Katmanı
Mevcut eksisozluk-api ile iletişim kurar
"""

import requests
from typing import Optional, Dict, List


class EksiSozlukService:
    """Ekşi Sözlük API ile iletişim için servis sınıfı"""
    
    def __init__(self, base_url="http://localhost:3000"):
        """
        Servis başlatıcı
        
        Args:
            base_url (str): Ekşi Sözlük API'nin base URL'i
        """
        self.base_url = base_url.rstrip('/')
        self.api_endpoint = f"{self.base_url}/api"
        
    def search_topics(self, query: str) -> List[Dict]:
        """
        Başlık arama
        
        Args:
            query (str): Arama sorgusu
            
        Returns:
            list: Bulunan başlıklar
        """
        try:
            url = f"{self.api_endpoint}/ara/{query}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            # API { thread_count, threads } formatında döndürüyor
            if isinstance(data, dict) and 'threads' in data:
                return data['threads']
            return data if data else []
        except requests.RequestException as e:
            print(f"Arama hatası: {e}")
            return []
    
    def autocomplete(self, query: str) -> List[Dict]:
        """
        Otomatik tamamlama
        
        Args:
            query (str): Arama sorgusu
            
        Returns:
            list: Önerilen başlıklar
        """
        try:
            url = f"{self.api_endpoint}/autocomplete/{query}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            return data if data else []
        except requests.RequestException as e:
            print(f"Autocomplete hatası: {e}")
            return []
    
    def get_topic_entries(self, slug: str, page: int = 1) -> Optional[Dict]:
        """
        Başlık entry'lerini getir
        
        Args:
            slug (str): Başlık slug'ı
            page (int): Sayfa numarası
            
        Returns:
            dict: Başlık bilgileri ve entry'ler
        """
        try:
            # Sayfa numarasını URL'e ekle
            if page > 1:
                url = f"{self.api_endpoint}/baslik/{slug}?p={page}"
            else:
                url = f"{self.api_endpoint}/baslik/{slug}"
            
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            print(f"DEBUG - API Response: {type(data)}, Keys: {data.keys() if isinstance(data, dict) else 'N/A'}")
            
            if not data:
                return None
            
            # Hata kontrolü - Ekşi Sözlük API hata dönerse
            if isinstance(data, dict) and 'error' in data:
                print(f"DEBUG - API Error: {data['error']}")
                return None
            
            # Ekşi Sözlük API'den gelen veri yapısını parse et
            entries = []
            title = slug
            current_page = page
            total_page = 1
            
            # Veri dict ise
            if isinstance(data, dict):
                # Başlık ismini bul
                title = data.get('title') or data.get('baslik') or slug
                
                # Sayfa bilgilerini al
                current_page = data.get('current_page', page)
                total_page = data.get('total_page', 1)
                
                # Entry'leri bul
                if 'entries' in data:
                    entries = data['entries']
                elif 'guncel' in data:
                    entries = data['guncel']
                elif 'data' in data:
                    entries = data['data']
                else:
                    # Eğer doğrudan entry objesi ise
                    possible_entries = [v for k, v in data.items() 
                                      if isinstance(v, list) and len(v) > 0]
                    if possible_entries:
                        entries = possible_entries[0]
            # Veri list ise doğrudan kullan
            elif isinstance(data, list):
                entries = data
            
            # Entry'leri normalize et
            normalized_entries = []
            for entry in entries:
                if isinstance(entry, dict):
                    # Ekşi Sözlük API'de 'body' field'ı kullanılıyor
                    content = (entry.get('body') or 
                              entry.get('entry') or 
                              entry.get('content') or 
                              entry.get('text') or '')
                    
                    # HTML etiketlerini temizle (basit)
                    if content:
                        # <br> etiketlerini newline'a çevir
                        content = content.replace('<br>', '\n').replace('<br/>', '\n').replace('<br />', '\n')
                        # Diğer HTML etiketlerini kaldır (basit regex)
                        import re
                        content = re.sub(r'<[^>]+>', '', content)
                        # HTML entities'i decode et
                        import html
                        content = html.unescape(content)
                    
                    normalized_entries.append({
                        'id': entry.get('id') or entry.get('entryId'),
                        'content': content.strip(),
                        'author': entry.get('author') or entry.get('owner') or entry.get('nick') or 'Anonim',
                        'date': entry.get('created_at') or entry.get('date') or entry.get('tarih') or entry.get('created') or '',
                        'fav_count': entry.get('fav_count') or entry.get('favCount') or 0
                    })
                elif isinstance(entry, str):
                    normalized_entries.append({
                        'id': None,
                        'content': entry,
                        'author': 'Bilinmiyor',
                        'date': '',
                        'fav_count': 0
                    })
            
            print(f"DEBUG - Parsed {len(normalized_entries)} entries")
            
            if len(normalized_entries) == 0:
                return None
            
            return {
                'title': title,
                'slug': slug,
                'page': current_page,
                'total_pages': total_page,
                'entries': normalized_entries,
                'total_entries': len(normalized_entries),
                'raw_data': data
            }
        except requests.RequestException as e:
            print(f"Entry getirme hatası: {e}")
            return None
        except Exception as e:
            print(f"Parse hatası: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_entry_by_id(self, entry_id: str) -> Optional[Dict]:
        """
        ID'ye göre entry getir
        
        Args:
            entry_id (str): Entry ID'si
            
        Returns:
            dict: Entry bilgileri
        """
        try:
            url = f"{self.api_endpoint}/entry/{entry_id}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            return response.json()
        except requests.RequestException as e:
            print(f"Entry getirme hatası: {e}")
            return None
    
    def get_trending_topics(self) -> List[Dict]:
        """
        Gündem başlıklarını getir
        
        Returns:
            list: Gündem başlıkları
        """
        try:
            url = f"{self.api_endpoint}/basliklar"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            return data if isinstance(data, list) else []
        except requests.RequestException as e:
            print(f"Gündem getirme hatası: {e}")
            return []
    
    def get_debe(self) -> Optional[Dict]:
        """
        Debe (Dün en beğenilenler) getir
        
        Returns:
            dict: Debe bilgileri
        """
        try:
            url = f"{self.api_endpoint}/debe"
            response = requests.get(url, timeout=30)  # Debe yavaş olabilir
            response.raise_for_status()
            
            return response.json()
        except requests.RequestException as e:
            print(f"Debe getirme hatası: {e}")
            return None
    
    def get_user_info(self, username: str) -> Optional[Dict]:
        """
        Kullanıcı bilgilerini getir
        
        Args:
            username (str): Kullanıcı adı
            
        Returns:
            dict: Kullanıcı bilgileri
        """
        try:
            url = f"{self.api_endpoint}/biri/{username}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            return response.json()
        except requests.RequestException as e:
            print(f"Kullanıcı bilgisi getirme hatası: {e}")
            return None
    
    def check_status(self) -> str:
        """
        API durumunu kontrol et
        
        Returns:
            str: 'online' veya 'offline'
        """
        try:
            response = requests.get(self.api_endpoint, timeout=5)
            return 'online' if response.status_code == 200 else 'offline'
        except:
            return 'offline'
