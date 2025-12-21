# Python Script Rehberi

Bu dosya `nlp-analyzer` klasöründeki `.py` dosyalarının ne işe yaradığını özetler. Senaryoları hızlıca hatırlamak için kategorilere ayrılmış durumda.

## 1. Analiz ve Değerlendirme Scriptleri

| Dosya | Açıklama | Tipik Kullanım |
| --- | --- | --- |
| `analyze_test_data_simple.py` | Excel'deki `body` + `RDuygu` kolonlarını okuyup NLP servisinin duygu ve tema tahminlerini `Tduygu` / `Tkategori` olarak yazar. Sonuçları dağılım tabloları, sınıflandırma raporu ve karışıklık matrisiyle özetler. | Etiketli ama kategori içermeyen küçük doğrulama setlerini otomatik değerlendirmek. |
| `analyze_test_data.py` | `body`, `RDuygu`, `Rkategori` bulunan dosyayı dengeli bir şekilde örnekleyip hem duygu hem tema tahmini yapar. Çok daha kapsamlı istatistik, doğruluk ve kategori kıyaslaması verir. | Farklı kategorilerden eşit örnek alarak modeli stres testine sokmak. |
| `analyze_errors.py` | `Sonuc.xlsx` içindeki gerçek (`RDuygu`) ve tahmin (`Tduygu`) farklarını çıkarır. Hata tiplerini, örnek yanlışları ve örnek doğruları yazdırır, ayrıca `Errors_Analysis.xlsx` dosyası üretir. | Modelin en çok zorlandığı sınıf kombinasyonlarını keşfetmek. |
| `check_data.py` | `test2.xlsx` dosyasını hızlıca inceleyip kolon listesini, null/boş alan sayılarını ve örnek satırları basar. | Dosya geldiğinde format ve eksik alan kontrolü yapmak. |
| `test_models.py` | Çeşitli Hugging Face model/adaptor kombinasyonlarını (örn. TurkishBERTweet + LoRA, XLM-RoBERTa) sırayla deneyip doğruluklarını karşılaştırır ve `model_comparison.csv` oluşturur. | Hangi modelin proje verisinde daha iyi performans verdiğini ölçmek. |
| `test_import.py` | Ortam testi: pandas/openpyxl importu, Excel okuma, `NLPService` yükleme gibi adımları tek seferde dener. | Yeni makinede bağımlılıkların doğru kurulup kurulmadığını kontrol etmek. |

## 2. Veri Hazırlama ve Temizlik Araçları

| Dosya | Açıklama | Tipik Kullanım |
| --- | --- | --- |
| `clean_excel.py` | Excel'deki tüm metin kolonlarını HTML'den arındırır, Türkçe karakter bozukluklarını düzeltir, boş satırları, sadece link içerenleri ve kısa `bkz` satırlarını filtreler. | Etiketleme veya eğitime girmeden önce ham veriyi temizlemek. |
| `collect_data.py` | Yerelde çalışan Node.js Ekşi API'sine istek atarak seçilen başlıklardan entry toplar, JSON dataset ve metadata üretir. | Eğitim için yeni veri partileri oluşturmak. |
| `json_to_csv.py` | Ekşi dataset JSON'unu temizlenmiş `body` + boş `sentiment` kolonlu CSV'ye çevirir. HTML ve kodlama problemlerini çözer. | Manuel etiketleme için CSV formatına geçmek. |
| `json_to_excel.py` | JSON veya JSONL dosyalarını Excel'e aktarır; entries ve metadata sayfalarını ayrı yazar. | Analistlerin Excel üzerinden veriyi inceleyebilmesi için. |

## 3. Model Eğitimi ve Deneyler

| Dosya | Açıklama | Tipik Kullanım |
| --- | --- | --- |
| `colab_training.py` | Colab ortamında GPU kontrolü, Drive bağlantısı, veri yükleme, hazır sentiment modeli kaydetme ve BERTopic tabanlı tema modeli eğitimi adımlarını içerir. | Google Colab'da yeni modeller eğitip Drive'a kaydetmek. |
| `app.py` | Flask tabanlı servis: Ekşi API'den veri çekme uçları, duygu/tema analizi uçları ve toplu analiz endpoint'leri sağlar. CORS, logging ve durum kontrolleri de içerir. | Web arayüzü veya diğer servislerin çağıracağı ana backend. |

## 4. Servis Katmanı Modülleri

| Dosya | Açıklama | Tipik Kullanım |
| --- | --- | --- |
| `services/__init__.py` | Paket dışına `NLPService` ve `EksiSozlukService` sınıflarını export eder. | `from services import NLPService` şeklinde kısayol import. |
| `services/nlp_service.py` | Üretim odaklı NLP servisi. VNLP tabanlı ön işleme, XLM-RoBERTa sentiment pipeline'ı, savasy haber sınıflandırıcıyla tema tespiti, keyword çıkarımı ve kombine analiz fonksiyonlarını içerir. | Flask API ve analiz scriptlerinin kullandığı ana model servis katmanı. |
| `services/trained_nlp_service.py` | Daha esnek, GPU farkındalığı olan ve gerçek modeller entegre edilene kadar placeholder sonuçlar üreten alternatif servis sınıfı. | Geliştirmenin erken safhalarında mock sonuç üretmek veya özel modelleri manuel bağlamak. |
| `services/eksisozluk_service.py` | Node.js tabanlı Ekşi API'ye istek gönderen, tekrar deneme & circuit breaker mekanizmalı HTTP istemcisi. Başlık arama, autocomplete, entry çekme, debe, kullanıcı bilgisi vb. uçları sarmalar. | Flask API'nin Ekşi Sözlük verisiyle konuşurken kullandığı arabirim. |

## 5. Yardımcı Scriptler

| Dosya | Açıklama | Tipik Kullanım |
| --- | --- | --- |
| `analyze_errors.py` | (bkz. 1. bölüm) Hatalı tahminleri Excel'e yazar. | Model hatalarını sınıflandırmak. |
| `app.py` | (bkz. 3. bölüm) Ana Flask uygulaması. | API’yi ayağa kaldırmak. |

> Not: Scriptlerin çoğu `.env` ayarlarına ve `services` paketindeki modellere dayanır. NLP servisindeki modelleri değiştirmek için ortam değişkenlerini (`SENTIMENT_MODEL_NAME`, `SENTIMENT_ADAPTER_NAME` vb.) güncellemeniz yeterlidir.
