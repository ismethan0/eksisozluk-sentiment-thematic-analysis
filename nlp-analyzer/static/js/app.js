/**
 * Ekşi Sözlük NLP Analiz - Frontend JavaScript
 * Modern ve responsive arayüz kontrolü
 */

// API Base URL
const API_BASE_URL = window.location.origin;

// Global State
let currentTopic = null;
let currentPage = 1;
let allEntries = [];
let analyzedEntries = new Map();

// DOM Elements
const searchInput = document.getElementById('searchInput');
const searchBtn = document.getElementById('searchBtn');
const autocompleteDropdown = document.getElementById('autocompleteDropdown');
const trendingList = document.getElementById('trendingList');
const loadingIndicator = document.getElementById('loadingIndicator');
const errorMessage = document.getElementById('errorMessage');
const errorText = document.getElementById('errorText');
const resultsSection = document.getElementById('resultsSection');
const topicTitle = document.getElementById('topicTitle');
const entryCount = document.getElementById('entryCount');
const currentPageEl = document.getElementById('currentPage');
const entriesContainer = document.getElementById('entriesContainer');
const sentimentFilter = document.getElementById('sentimentFilter');
const themeFilter = document.getElementById('themeFilter');
const analyzeAllBtn = document.getElementById('analyzeAllBtn');
const prevPageBtn = document.getElementById('prevPage');
const nextPageBtn = document.getElementById('nextPage');
const pageNumbers = document.getElementById('pageNumbers');
const statsSection = document.getElementById('statsSection');

// Update CSS variable for header offset dynamically
function updateHeaderOffset() {
    const header = document.querySelector('.header');
    if (header) {
        const h = header.offsetHeight;
        document.documentElement.style.setProperty('--header-offset', `${h}px`);
    }
}

// Debounce utility
function debounce(func, delay) {
    let timeoutId;
    return function (...args) {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => func.apply(this, args), delay);
    };
}

// Show/Hide UI elements
function showElement(element) {
    element?.classList.remove('hidden');
}

function hideElement(element) {
    element?.classList.add('hidden');
}

function showLoading() {
    showElement(loadingIndicator);
    hideElement(errorMessage);
}

function hideLoading() {
    hideElement(loadingIndicator);
}

function showError(message) {
    errorText.textContent = message;
    showElement(errorMessage);
    hideElement(loadingIndicator);
}

// Initialize App
async function initApp() {
    console.log('🚀 Uygulama başlatılıyor...');

    // Set header offset for fixed header spacing
    updateHeaderOffset();
    window.addEventListener('resize', updateHeaderOffset);

    // Load trending topics
    await loadTrendingTopics();

    // Event listeners
    searchBtn.addEventListener('click', handleSearch);
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleSearch();
    });

    // Autocomplete
    searchInput.addEventListener('input', debounce(handleAutocomplete, 300));

    // Click outside to close autocomplete
    document.addEventListener('click', (e) => {
        if (!searchInput.contains(e.target)) {
            hideElement(autocompleteDropdown);
        }
    });

    // Filters
    sentimentFilter.addEventListener('change', applyFilters);
    themeFilter.addEventListener('change', applyFilters);

    // Analyze all button
    analyzeAllBtn.addEventListener('click', analyzeAllEntries);

    // Pagination
    prevPageBtn.addEventListener('click', () => changePage(currentPage - 1));
    nextPageBtn.addEventListener('click', () => changePage(currentPage + 1));

    console.log('✅ Uygulama hazır!');
}

// Load trending topics
async function loadTrendingTopics() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/search?q=gundem`);
        const data = await response.json();

        if (data.success && data.data && data.data.length > 0) {
            trendingList.innerHTML = '';
            data.data.slice(0, 8).forEach(topic => {
                const div = document.createElement('div');
                div.className = 'trending-item-sidebar';
                div.textContent = topic.title || topic;

                // Slug'ı sakla ve direkt yükle
                div.addEventListener('click', () => {
                    // Eğer slug tam URL ise, slug kısmını çıkar
                    let slug = topic.slug;
                    if (slug && slug.includes('eksisozluk.com/')) {
                        // https://eksisozluk.com/baslik-adi--123456 -> baslik-adi--123456
                        slug = slug.split('eksisozluk.com/')[1];
                    }

                    // Slug varsa direkt yükle, yoksa arama yap
                    if (slug) {
                        loadTopicBySlug(slug);
                    } else {
                        searchInput.value = topic.title || topic;
                        handleSearch();
                    }
                });
                trendingList.appendChild(div);
            });
        } else {
            trendingList.innerHTML = '<div class="trending-item-sidebar">Gündem yüklenemedi</div>';
        }
    } catch (error) {
        console.error('Gündem yüklenemedi:', error);
        trendingList.innerHTML = '<div class="trending-item-sidebar">Gündem yüklenemedi</div>';
    }
}

// Handle autocomplete
async function handleAutocomplete() {
    const query = searchInput.value.trim();

    if (query.length < 2) {
        hideElement(autocompleteDropdown);
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/api/autocomplete?q=${encodeURIComponent(query)}`);
        const data = await response.json();

        if (data.success && data.data && data.data.length > 0) {
            autocompleteDropdown.innerHTML = '';
            data.data.slice(0, 8).forEach(item => {
                const div = document.createElement('div');
                div.className = 'autocomplete-item';
                div.textContent = item.title || item;
                div.addEventListener('click', () => {
                    searchInput.value = item.title || item;
                    hideElement(autocompleteDropdown);
                    handleSearch();
                });
                autocompleteDropdown.appendChild(div);
            });
            showElement(autocompleteDropdown);
        } else {
            hideElement(autocompleteDropdown);
        }
    } catch (error) {
        console.error('Autocomplete hatası:', error);
        hideElement(autocompleteDropdown);
    }
}

// Handle search
async function handleSearch() {
    const query = searchInput.value.trim();

    if (!query) {
        showError('Lütfen bir başlık girin');
        return;
    }

    hideElement(autocompleteDropdown);
    hideElement(resultsSection);
    hideElement(statsSection);
    hideElement(errorMessage);
    showLoading();

    // Convert query to slug (basic conversion)
    const slug = query.toLowerCase()
        .replace(/ı/g, 'i')
        .replace(/ğ/g, 'g')
        .replace(/ü/g, 'u')
        .replace(/ş/g, 's')
        .replace(/ö/g, 'o')
        .replace(/ç/g, 'c')
        .replace(/[^a-z0-9\s-]/g, '')
        .replace(/\s+/g, '-');

    await loadTopic(slug, 1);
}

// Load topic directly by slug (for trending/popular topics)
async function loadTopicBySlug(slug) {
    hideElement(resultsSection);
    hideElement(statsSection);
    hideElement(errorMessage);
    showLoading();

    // Slug'dan başlık adını çıkar ve search input'a yaz
    const titleFromSlug = slug.split('--')[0].replace(/-/g, ' ');
    searchInput.value = titleFromSlug;

    await loadTopic(slug, 1);
}

// Load topic entries
async function loadTopic(slug, page = 1) {
    try {
        const response = await fetch(`${API_BASE_URL}/api/topic/${slug}?page=${page}`);
        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error || 'Başlık bulunamadı');
        }

        currentTopic = slug;
        currentPage = page;
        allEntries = data.data.entries || [];
        analyzedEntries.clear();

        // Reset analyze all button
        analyzeAllBtn.disabled = false;
        analyzeAllBtn.innerHTML = '<i class="fas fa-chart-line"></i> Tümünü Analiz Et';

        // Update UI
        topicTitle.textContent = data.data.title || slug;
        entryCount.querySelector('span').textContent = `${allEntries.length} entry`;
        currentPageEl.querySelector('span').textContent = `Sayfa ${page}`;

        // Render entries
        renderEntries(allEntries);

        // Update filters
        updateThemeFilter();

        // Hide stats section on new topic
        hideElement(statsSection);

        // Show results
        hideLoading();
        showElement(resultsSection);

        // Scroll to results
        resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });

    } catch (error) {
        console.error('Başlık yükleme hatası:', error);
        hideLoading();
        showError(error.message || 'Başlık yüklenirken bir hata oluştu');
    }
}

// Render entries
function renderEntries(entries) {
    if (!entries || entries.length === 0) {
        entriesContainer.innerHTML = '<p class="text-center">Entry bulunamadı</p>';
        return;
    }

    entriesContainer.innerHTML = '';

    entries.forEach((entry, index) => {
        const entryCard = createEntryCard(entry, index);
        entriesContainer.appendChild(entryCard);
    });

    updatePagination();
}

// Show skeleton loading for entries
function showEntriesSkeleton(count = 10) {
    entriesContainer.innerHTML = '';

    for (let i = 0; i < count; i++) {
        const skeleton = document.createElement('div');
        skeleton.className = 'entry-card skeleton-card';
        skeleton.innerHTML = `
            <div class="entry-header">
                <div class="skeleton-author skeleton"></div>
                <div class="skeleton-date skeleton"></div>
            </div>
            <div class="entry-content">
                <div class="skeleton-line skeleton"></div>
                <div class="skeleton-line skeleton"></div>
                <div class="skeleton-line skeleton" style="width: 80%;"></div>
            </div>
            <div class="entry-footer">
                <div class="skeleton-button skeleton"></div>
            </div>
        `;
        entriesContainer.appendChild(skeleton);
    }
}

// Create entry card
function createEntryCard(entry, index) {
    const card = document.createElement('div');
    card.className = 'entry-card';
    card.dataset.entryId = entry.id || index;

    // Entry header
    const header = document.createElement('div');
    header.className = 'entry-header';

    const author = document.createElement('div');
    author.className = 'entry-author';
    author.innerHTML = `<i class="fas fa-user"></i> ${entry.author || entry.owner || 'Anonim'}`;

    const date = document.createElement('div');
    date.className = 'entry-date';
    date.innerHTML = `<i class="far fa-clock"></i> ${entry.date || entry.created || 'Tarih bilinmiyor'}`;

    header.appendChild(author);
    header.appendChild(date);

    // Entry content
    const content = document.createElement('div');
    content.className = 'entry-content';
    content.textContent = entry.content || entry.text || entry.entry || 'İçerik bulunamadı';

    // Entry footer with analysis
    const footer = document.createElement('div');
    footer.className = 'entry-footer';

    const analysisSection = document.createElement('div');
    analysisSection.className = 'analysis-section';
    analysisSection.id = `analysis-${index}`;

    const analyzeBtn = document.createElement('button');
    analyzeBtn.className = 'analyze-btn';
    analyzeBtn.innerHTML = '<i class="fas fa-chart-line"></i> Analiz Et';
    analyzeBtn.addEventListener('click', () => analyzeEntry(entry, index));

    analysisSection.appendChild(analyzeBtn);
    footer.appendChild(analysisSection);

    // Assemble card
    card.appendChild(header);
    card.appendChild(content);
    card.appendChild(footer);

    return card;
}

// Analyze single entry
async function analyzeEntry(entry, index) {
    const analysisSection = document.getElementById(`analysis-${index}`);
    const text = entry.content || entry.text || entry.entry;

    if (!text) {
        alert('Analiz edilecek metin bulunamadı');
        return;
    }

    // Show loading
    analysisSection.innerHTML = '<span class="analysis-badge">Analiz ediliyor...</span>';

    try {
        // Call sentiment and theme analysis APIs
        const [sentimentResponse, themeResponse] = await Promise.all([
            fetch(`${API_BASE_URL}/api/analyze/sentiment`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text, entry_id: entry.id || index })
            }),
            fetch(`${API_BASE_URL}/api/analyze/theme`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text, entry_id: entry.id || index })
            })
        ]);

        const sentimentData = await sentimentResponse.json();
        const themeData = await themeResponse.json();

        if (!sentimentData.success || !themeData.success) {
            throw new Error('Analiz başarısız');
        }

        // Store results
        analyzedEntries.set(index, {
            sentiment: sentimentData.data,
            theme: themeData.data
        });

        // Render results
        renderAnalysisResults(analysisSection, sentimentData.data, themeData.data);

        // Update stats
        updateStats();

    } catch (error) {
        console.error('Analiz hatası:', error);
        analysisSection.innerHTML = '<span class="analysis-badge" style="background: #ffe5e5; color: #e74c3c;">Analiz hatası</span>';
    }
}

// Render analysis results
function renderAnalysisResults(container, sentiment, theme) {
    container.innerHTML = '';

    // Debug log
    console.log('📊 Analiz sonuçları:', { sentiment, theme });

    // Sentiment badge
    const sentimentBadge = document.createElement('div');
    sentimentBadge.className = `sentiment-badge ${sentiment.sentiment}`;

    const sentimentIcon = {
        'positive': 'fa-smile',
        'neutral': 'fa-meh',
        'negative': 'fa-frown'
    }[sentiment.sentiment] || 'fa-meh';

    const sentimentText = {
        'positive': 'Pozitif',
        'neutral': 'Nötr',
        'negative': 'Negatif'
    }[sentiment.sentiment] || 'Bilinmiyor';

    sentimentBadge.innerHTML = `
        <i class="fas ${sentimentIcon}"></i>
        ${sentimentText} (${(sentiment.confidence * 100).toFixed(0)}%)
    `;

    // Theme badges
    const themesContainer = document.createElement('div');
    themesContainer.style.display = 'flex';
    themesContainer.style.gap = '0.5rem';
    themesContainer.style.flexWrap = 'wrap';

    if (theme.themes && theme.themes.length > 0) {
        theme.themes.forEach((t, idx) => {
            const themeBadge = document.createElement('div');
            themeBadge.className = 'theme-badge';

            // Tema skorunu göster
            const score = theme.scores && theme.scores[t]
                ? ` (${(theme.scores[t] * 100).toFixed(0)}%)`
                : '';

            themeBadge.innerHTML = `<i class="fas fa-tag"></i> ${t}${score}`;

            // Ana temayı vurgula
            if (idx === 0) {
                themeBadge.style.fontWeight = 'bold';
                themeBadge.style.borderWidth = '2px';
            }

            themesContainer.appendChild(themeBadge);
        });
    } else {
        // Fallback - eğer themes boşsa main_topic göster
        const themeBadge = document.createElement('div');
        themeBadge.className = 'theme-badge';
        themeBadge.innerHTML = `<i class="fas fa-tag"></i> ${theme.main_topic || 'Genel'}`;
        themesContainer.appendChild(themeBadge);
    }

    container.appendChild(sentimentBadge);
    if (themesContainer.children.length > 0) {
        container.appendChild(themesContainer);
    }
}

// Analyze all entries
async function analyzeAllEntries() {
    if (allEntries.length === 0) return;

    analyzeAllBtn.disabled = true;
    analyzeAllBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Analiz ediliyor...';

    try {
        // Prepare batch request
        const entries = allEntries.map((entry, index) => ({
            id: entry.id || index,
            text: entry.content || entry.text || entry.entry || ''
        }));

        const response = await fetch(`${API_BASE_URL}/api/analyze/batch`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ entries })
        });

        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error || 'Toplu analiz başarısız');
        }

        console.log('Batch analysis response:', data);

        // API'den gelen data formatı: { success: true, data: { summary: {...}, entries: [...] } }
        const results = data.data.entries || data.data || [];

        if (!Array.isArray(results)) {
            throw new Error('API geçersiz format döndürdü');
        }

        // Update UI with results
        results.forEach((result, index) => {
            const analysisSection = document.getElementById(`analysis-${index}`);
            if (analysisSection && result.sentiment && result.theme) {
                analyzedEntries.set(index, result);
                renderAnalysisResults(analysisSection, result.sentiment, result.theme);
            }
        });

        // Update stats with summary data if available
        if (data.data.summary) {
            updateStatsFromSummary(data.data.summary);
        } else {
            updateStats();
        }

        showElement(statsSection);

        analyzeAllBtn.innerHTML = '<i class="fas fa-check"></i> Tümü Analiz Edildi';

    } catch (error) {
        console.error('Toplu analiz hatası:', error);
        alert('Toplu analiz sırasında bir hata oluştu: ' + error.message);
        analyzeAllBtn.innerHTML = '<i class="fas fa-chart-line"></i> Tümünü Analiz Et';
        analyzeAllBtn.disabled = false;
    }
}

// Update statistics from API summary
function updateStatsFromSummary(summary) {
    const sentimentDist = summary.sentiment_distribution || {};
    const themeDist = summary.theme_distribution || {};

    // Sentiment counts - API'den gelen label'lar büyük harf (POSITIVE, NEGATIVE, NEUTRAL)
    const positive = sentimentDist.positive || sentimentDist.POSITIVE || sentimentDist.Positive || 0;
    const neutral = sentimentDist.neutral || sentimentDist.NEUTRAL || sentimentDist.Neutral || 0;
    const negative = sentimentDist.negative || sentimentDist.NEGATIVE || sentimentDist.Negative || 0;

    document.getElementById('positiveCount').textContent = positive;
    document.getElementById('neutralCount').textContent = neutral;
    document.getElementById('negativeCount').textContent = negative;
    document.getElementById('themeCount').textContent = Object.keys(themeDist).length;
}

// Update statistics
function updateStats() {
    let positive = 0, neutral = 0, negative = 0;
    const themesSet = new Set();

    analyzedEntries.forEach(result => {
        if (result.sentiment) {
            const sentiment = result.sentiment.sentiment;
            if (sentiment === 'positive') positive++;
            else if (sentiment === 'neutral') neutral++;
            else if (sentiment === 'negative') negative++;
        }

        if (result.theme && result.theme.themes) {
            result.theme.themes.forEach(theme => themesSet.add(theme));
        }
    });

    document.getElementById('positiveCount').textContent = positive;
    document.getElementById('neutralCount').textContent = neutral;
    document.getElementById('negativeCount').textContent = negative;
    document.getElementById('themeCount').textContent = themesSet.size;
}

// Apply filters
function applyFilters() {
    const sentiment = sentimentFilter.value;
    const theme = themeFilter.value;

    const filteredEntries = allEntries.filter((entry, index) => {
        const analysis = analyzedEntries.get(index);

        if (!analysis) return true; // Show unanalyzed entries

        // Sentiment filter
        if (sentiment !== 'all' && analysis.sentiment?.sentiment !== sentiment) {
            return false;
        }

        // Theme filter
        if (theme !== 'all' && analysis.theme?.themes && !analysis.theme.themes.includes(theme)) {
            return false;
        }

        return true;
    });

    renderEntries(filteredEntries);
}

// Update theme filter options
function updateThemeFilter() {
    const themes = new Set();

    analyzedEntries.forEach(result => {
        if (result.theme && result.theme.themes) {
            result.theme.themes.forEach(theme => themes.add(theme));
        }
    });

    // Keep "Tümü" option and add themes
    const currentValue = themeFilter.value;
    themeFilter.innerHTML = '<option value="all">Tümü</option>';

    Array.from(themes).sort().forEach(theme => {
        const option = document.createElement('option');
        option.value = theme;
        option.textContent = theme;
        themeFilter.appendChild(option);
    });

    // Restore selection if possible
    if (currentValue !== 'all' && themes.has(currentValue)) {
        themeFilter.value = currentValue;
    }
}

// Change page
async function changePage(page) {
    if (page < 1 || !currentTopic) return;

    // Show skeleton loading
    showEntriesSkeleton(10);

    // Scroll to entries section
    entriesContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });

    await loadTopic(currentTopic, page);
}

// Update pagination
function updatePagination() {
    // Simple pagination - you can enhance this
    prevPageBtn.disabled = currentPage <= 1;

    // Update page numbers (basic implementation)
    pageNumbers.innerHTML = `<span class="page-number active">${currentPage}</span>`;
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', initApp);

// Export for debugging
window.nlpApp = {
    loadTopic,
    analyzeEntry,
    analyzeAllEntries,
    currentTopic,
    currentPage,
    allEntries,
    analyzedEntries
};
