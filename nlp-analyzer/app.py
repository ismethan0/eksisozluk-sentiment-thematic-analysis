"""
Ekşi Sözlük NLP Analiz Uygulaması
Flask Backend API
"""

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import requests
from services.nlp_service import NLPService
from services.eksisozluk_service import EksiSozlukService
import os

app = Flask(__name__)
CORS(app)

# Servisler
nlp_service = NLPService()
eksi_service = EksiSozlukService()

# Konfigurasyon
app.config['JSON_AS_ASCII'] = False
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True


@app.route('/')
def index():
    """Ana sayfa"""
    return render_template('index.html')


@app.route('/api/search', methods=['GET'])
def search_topics():
    """
    Başlık arama
    Query Params: 
        - q: arama sorgusu
    """
    query = request.args.get('q', '')
    
    if not query:
        return jsonify({
            'success': False,
            'error': 'Arama sorgusu boş olamaz'
        }), 400
    
    try:
        results = eksi_service.search_topics(query)
        return jsonify({
            'success': True,
            'data': results
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/autocomplete', methods=['GET'])
def autocomplete():
    """
    Otomatik tamamlama
    Query Params:
        - q: arama sorgusu
    """
    query = request.args.get('q', '')
    
    if not query:
        return jsonify({
            'success': False,
            'error': 'Sorgu boş olamaz'
        }), 400
    
    try:
        results = eksi_service.autocomplete(query)
        return jsonify({
            'success': True,
            'data': results
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/topic/<slug>', methods=['GET'])
def get_topic_entries(slug):
    """
    Başlık detayı ve entry'leri getir
    URL Params:
        - slug: başlık slug'ı
    Query Params:
        - page: sayfa numarası (default: 1)
    """
    page = request.args.get('page', 1, type=int)
    
    try:
        data = eksi_service.get_topic_entries(slug, page)
        
        print(f"DEBUG - Flask: slug={slug}, data={data is not None}")
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Başlık bulunamadı veya entry yok'
            }), 404
        
        if 'entries' not in data or len(data['entries']) == 0:
            return jsonify({
                'success': False,
                'error': 'Bu başlıkta entry bulunamadı'
            }), 404
        
        return jsonify({
            'success': True,
            'data': data
        })
    except Exception as e:
        print(f"ERROR - Flask: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/analyze/sentiment', methods=['POST'])
def analyze_sentiment():
    """
    Duygu analizi yap
    Body:
        - text: analiz edilecek metin
        - entry_id: (optional) entry id'si
    """
    data = request.get_json()
    
    if not data or 'text' not in data:
        return jsonify({
            'success': False,
            'error': 'Metin gereklidir'
        }), 400
    
    try:
        text = data['text']
        entry_id = data.get('entry_id', None)
        
        result = nlp_service.analyze_sentiment(text)
        
        return jsonify({
            'success': True,
            'data': {
                'entry_id': entry_id,
                'sentiment': result['sentiment'],
                'score': result['score'],
                'confidence': result['confidence']
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/analyze/theme', methods=['POST'])
def analyze_theme():
    """
    Tema analizi yap
    Body:
        - text: analiz edilecek metin
        - entry_id: (optional) entry id'si
    """
    data = request.get_json()
    
    if not data or 'text' not in data:
        return jsonify({
            'success': False,
            'error': 'Metin gereklidir'
        }), 400
    
    try:
        text = data['text']
        entry_id = data.get('entry_id', None)
        
        result = nlp_service.analyze_theme(text)
        
        return jsonify({
            'success': True,
            'data': {
                'entry_id': entry_id,
                'themes': result['themes'],
                'keywords': result['keywords'],
                'main_topic': result['main_topic']
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/analyze/batch', methods=['POST'])
def analyze_batch():
    """
    Toplu analiz - birden fazla entry'yi aynı anda analiz et
    Body:
        - entries: [
            {
                "id": entry_id,
                "text": entry_text
            }
          ]
    """
    data = request.get_json()
    
    if not data or 'entries' not in data:
        return jsonify({
            'success': False,
            'error': 'Entries listesi gereklidir'
        }), 400
    
    try:
        entries = data['entries']
        results = []
        
        for entry in entries:
            if 'text' not in entry:
                continue
                
            sentiment = nlp_service.analyze_sentiment(entry['text'])
            theme = nlp_service.analyze_theme(entry['text'])
            
            results.append({
                'entry_id': entry.get('id'),
                'sentiment': sentiment,
                'theme': theme
            })
        
        return jsonify({
            'success': True,
            'data': results
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """
    İstatistikler - API durumu ve kullanım bilgileri
    """
    return jsonify({
        'success': True,
        'data': {
            'status': 'online',
            'version': '1.0.0',
            'services': {
                'eksi_api': eksi_service.check_status(),
                'nlp_service': 'ready'
            }
        }
    })


@app.errorhandler(404)
def not_found(error):
    """404 hatası"""
    return jsonify({
        'success': False,
        'error': 'Endpoint bulunamadı'
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """500 hatası"""
    return jsonify({
        'success': False,
        'error': 'Sunucu hatası'
    }), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'True') == 'True'
    
    print(f"""
    ╔══════════════════════════════════════════╗
    ║   Ekşi Sözlük NLP Analiz Uygulaması    ║
    ╠══════════════════════════════════════════╣
    ║  🌐 URL: http://localhost:{port}         ║
    ║  📊 API: http://localhost:{port}/api     ║
    ║  🚀 Status: Running                      ║
    ╚══════════════════════════════════════════╝
    """)
    
    app.run(host='0.0.0.0', port=port, debug=debug)
