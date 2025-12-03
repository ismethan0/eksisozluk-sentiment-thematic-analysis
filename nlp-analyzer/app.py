"""
Eksi Sozluk NLP Analiz Uygulamasi - Flask backend API
"""

import os
import logging
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix

from services.nlp_service import NLPService
from services.eksisozluk_service import EksiSozlukService

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": os.getenv('CORS_ORIGINS', '*')}})
app.wsgi_app = ProxyFix(app.wsgi_app)

# Logging
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s %(levelname)s %(name)s %(message)s'
)
logger = logging.getLogger("nlp-analyzer")

# Services
nlp_service = NLPService()
eksi_service = EksiSozlukService()

logger.info("✅ NLP service loaded successfully")

# Configuration
app.config['JSON_AS_ASCII'] = False
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True


@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')


@app.route('/api/search', methods=['GET'])
def search_topics():
    """Search for topics by query."""
    query = request.args.get('q', '')

    if not query or not isinstance(query, str) or len(query.strip()) < 2:
        return jsonify({'success': False, 'error': 'Arama sorgusu en az 2 karakter olmalıdır'}), 400

    try:
        results = eksi_service.search_topics(query)
        return jsonify({'success': True, 'data': results})
    except Exception as e:
        logger.exception("Search error")
        return jsonify({'success': False, 'error': 'Arama sırasında hata oluştu'}), 500


@app.route('/api/autocomplete', methods=['GET'])
def autocomplete():
    """Return autocomplete suggestions for a query."""
    query = request.args.get('q', '')

    if not query or not isinstance(query, str) or len(query.strip()) < 2:
        return jsonify({'success': False, 'error': 'Sorgu en az 2 karakter olmalıdır'}), 400

    try:
        results = eksi_service.autocomplete(query)
        return jsonify({'success': True, 'data': results})
    except Exception as e:
        logger.exception("Autocomplete error")
        return jsonify({'success': False, 'error': 'Otomatik tamamlama sırasında hata oluştu'}), 500


@app.route('/api/topic/<slug>', methods=['GET'])
def get_topic_entries(slug):
    """Fetch topic details and entries."""
    page = request.args.get('page', 1, type=int)

    try:
        data = eksi_service.get_topic_entries(slug, page)

        if not data:
            return jsonify({'success': False, 'error': 'Baslik bulunamadi veya entry yok'}), 404

        if 'entries' not in data or len(data['entries']) == 0:
            return jsonify({'success': False, 'error': 'Bu baslikta entry bulunamadi'}), 404

        return jsonify({'success': True, 'data': data})
    except Exception as e:
        logger.exception("Topic entries error")
        return jsonify({'success': False, 'error': 'Başlık entryleri alınırken hata oluştu'}), 500


@app.route('/api/analyze/sentiment', methods=['POST'])
def analyze_sentiment():
    """Run sentiment analysis for a single text."""
    data = request.get_json()

    if not data or 'text' not in data:
        return jsonify({'success': False, 'error': 'Metin gereklidir'}), 400
    
    text = str(data.get('text', '')).strip()
    if len(text) < 3:
        return jsonify({'success': False, 'error': 'Metin en az 3 karakter olmalıdır'}), 400
    if len(text) > 5000:
        return jsonify({'success': False, 'error': 'Metin çok uzun (maksimum 5000 karakter)'}), 400

    try:
        text = text
        entry_id = data.get('entry_id')

        result = nlp_service.analyze_sentiment(text)
        return jsonify({
            'success': True,
            'data': {
                'entry_id': entry_id,
                'sentiment': result['sentiment'],
                'label': result.get('label', result['sentiment']),
                'score': result['score'],
                'confidence': result['confidence'],
                'model': 'nlp_service'
            }
        })
    except Exception as e:
        logger.exception("Sentiment analysis error")
        return jsonify({'success': False, 'error': 'Duygu analizi sırasında hata oluştu'}), 500


@app.route('/api/analyze/theme', methods=['POST'])
def analyze_theme():
    """Run topic/theme analysis for a single text."""
    data = request.get_json()

    if not data or 'text' not in data:
        return jsonify({'success': False, 'error': 'Metin gereklidir'}), 400
    
    text = str(data.get('text', '')).strip()
    if len(text) < 3:
        return jsonify({'success': False, 'error': 'Metin en az 3 karakter olmalıdır'}), 400
    if len(text) > 5000:
        return jsonify({'success': False, 'error': 'Metin çok uzun (maksimum 5000 karakter)'}), 400

    try:
        text = text
        entry_id = data.get('entry_id')

        result = nlp_service.analyze_theme(text)
        return jsonify({
            'success': True,
            'data': {
                'entry_id': entry_id,
                'themes': result['themes'],
                'keywords': result['keywords'],
                'main_topic': result['main_topic'],
                'scores': result.get('scores', {}),
                'is_ambiguous': result.get('is_ambiguous', False),
                'label': result['main_topic'],  # Frontend için
                'model': 'nlp_service'
            }
        })
    except Exception as e:
        logger.exception("Theme analysis error")
        return jsonify({'success': False, 'error': 'Tema analizi sırasında hata oluştu'}), 500


@app.route('/api/analyze/batch', methods=['POST'])
def analyze_batch():
    """Batch analysis for multiple entries."""
    data = request.get_json()

    if not data or 'entries' not in data or not isinstance(data['entries'], list):
        return jsonify({'success': False, 'error': 'Entries listesi gereklidir'}), 400

    try:
        entries = data['entries']

        logger.info(f"🔍 Analyzing {len(entries)} entries...")
        
        results = []
        sentiment_counts = {}
        theme_counts = {}
        
        texts = []
        ids = []
        for entry in entries:
            text = str(entry.get('text', '')).strip()
            if len(text) < 3:
                continue
            texts.append(text)
            ids.append(entry.get('id'))

        try:
            sentiment_results = [nlp_service.analyze_sentiment(t) for t in texts]
            theme_results = [nlp_service.analyze_theme(t) for t in texts]
        except Exception:
            sentiment_results = []
            theme_results = []
            for t in texts:
                sentiment_results.append(nlp_service.analyze_sentiment(t))
                theme_results.append(nlp_service.analyze_theme(t))

            # Count sentiments
        for s in sentiment_results:
            label = s.get('sentiment', 'neutral')
            sentiment_counts[label] = sentiment_counts.get(label, 0) + 1
            
            # Count themes (use main_topic instead of label)
        for th in theme_results:
            theme_label = th.get('main_topic', 'Genel')
            theme_counts[theme_label] = theme_counts.get(theme_label, 0) + 1

        for i, t in enumerate(texts):
            results.append({
                'entry_id': ids[i],
                'text': t[:100] + '...' if len(t) > 100 else t,
                'sentiment': sentiment_results[i],
                'theme': theme_results[i]
            })

        return jsonify({
            'success': True,
            'data': {
                'summary': {
                    'total_entries': len(entries),
                    'sentiment_distribution': sentiment_counts,
                    'theme_distribution': theme_counts
                },
                'entries': results,
                'model': 'nlp_service'
            }
        })
    except Exception as e:
        logger.exception("Batch analysis error")
        return jsonify({'success': False, 'error': 'Toplu analiz sırasında hata oluştu'}), 500


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Return API status information."""
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
    """Handle 404 errors."""
    return jsonify({'success': False, 'error': 'Endpoint bulunamadi'}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return jsonify({'success': False, 'error': 'Sunucu hatasi'}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'True') == 'True'

    logger.info(f"Starting server at http://localhost:{port}")
    logger.info("API root: http://localhost:{0}/api".format(port))

    # Disable auto-reloader to avoid double-loading models
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
