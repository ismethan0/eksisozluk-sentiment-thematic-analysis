"""
Eksi Sozluk NLP Analiz Uygulamasi - Flask backend API
"""

import os
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

from services.nlp_service import NLPService
from services.eksisozluk_service import EksiSozlukService

app = Flask(__name__)
CORS(app)

# Services
nlp_service = NLPService()
eksi_service = EksiSozlukService()

print("✅ NLP service loaded successfully")

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

    if not query:
        return jsonify({'success': False, 'error': 'Arama sorgusu bos olamaz'}), 400

    try:
        results = eksi_service.search_topics(query)
        return jsonify({'success': True, 'data': results})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/autocomplete', methods=['GET'])
def autocomplete():
    """Return autocomplete suggestions for a query."""
    query = request.args.get('q', '')

    if not query:
        return jsonify({'success': False, 'error': 'Sorgu bos olamaz'}), 400

    try:
        results = eksi_service.autocomplete(query)
        return jsonify({'success': True, 'data': results})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


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
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/analyze/sentiment', methods=['POST'])
def analyze_sentiment():
    """Run sentiment analysis for a single text."""
    data = request.get_json()

    if not data or 'text' not in data:
        return jsonify({'success': False, 'error': 'Metin gereklidir'}), 400

    try:
        text = data['text']
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
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/analyze/theme', methods=['POST'])
def analyze_theme():
    """Run topic/theme analysis for a single text."""
    data = request.get_json()

    if not data or 'text' not in data:
        return jsonify({'success': False, 'error': 'Metin gereklidir'}), 400

    try:
        text = data['text']
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
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/analyze/batch', methods=['POST'])
def analyze_batch():
    """Batch analysis for multiple entries."""
    data = request.get_json()

    if not data or 'entries' not in data:
        return jsonify({'success': False, 'error': 'Entries listesi gereklidir'}), 400

    try:
        entries = data['entries']

        print(f"🔍 Analyzing {len(entries)} entries...")
        
        results = []
        sentiment_counts = {}
        theme_counts = {}
        
        for entry in entries:
            if 'text' not in entry:
                continue

            sentiment = nlp_service.analyze_sentiment(entry['text'])
            theme = nlp_service.analyze_theme(entry['text'])

            # Count sentiments
            sentiment_label = sentiment.get('sentiment', 'neutral')
            sentiment_counts[sentiment_label] = sentiment_counts.get(sentiment_label, 0) + 1
            
            # Count themes (use main_topic instead of label)
            theme_label = theme.get('main_topic', 'Genel')
            theme_counts[theme_label] = theme_counts.get(theme_label, 0) + 1

            results.append({
                'entry_id': entry.get('id'),
                'text': entry['text'][:100] + '...' if len(entry['text']) > 100 else entry['text'],
                'sentiment': sentiment,
                'theme': theme
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
        print(f"❌ Batch analysis error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


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

    print(f"Starting server at http://localhost:{port}")
    print("API root: http://localhost:{0}/api".format(port))

    # Disable auto-reloader to avoid double-loading models
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
