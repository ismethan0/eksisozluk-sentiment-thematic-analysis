const url = require('url');
const querystring = require('querystring');

const axios = require('axios');
const cheerio = require('cheerio');
const puppeteer = require('puppeteer');
const URLS = require('./constants');

exports.list = async function (reqUrl) {
  let type = parseUrl(reqUrl);
  let response;
  try {
    response = await axios.get(URLS.THREAD + "/" + type, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
        'Connection': 'keep-alive'
      }
    });
  } catch (err) {
    return { error: err.message };
  }

  let $ = cheerio.load(response.data, { decodeEntities: false });

  let title, slug, entry_count, id, disambiguations;
  let threads = [];
  let thread = {};

  $(".topic-list").find("li > a").each(function (index, element) {
    title = $(element).contents().filter(function () {
      return this.nodeType === 3;
    }).text().trim();

    // slug = EKSI_URL + $(element).attr("href");
    slug = $(element).attr("href");
    entry_count = $(element).find("small").text() || 1;
    id = exports.idFromSlug(slug);
    thread = {
      id: parseInt(id),
      title,
      slug,
      entry_count
    };
    threads.push(thread);
  });
  return threads;
}


exports.detail = async function (reqUrl) {
  console.log('DEBUG - Original reqUrl:', reqUrl);

  // Query parametrelerini ayır
  const fullUrl = reqUrl.split("/baslik/")[1];
  let pageParam = '';
  let slug = fullUrl;

  if (fullUrl && fullUrl.includes('?')) {
    const [slugPart, query] = fullUrl.split('?');
    slug = slugPart;
    pageParam = '?' + query; // ?p=2 gibi
  }

  reqUrl = slug;
  console.log('DEBUG - Parsed reqUrl:', reqUrl);
  console.log('DEBUG - Page param:', pageParam);

  // Eğer slug'da ID yoksa (-- içermiyorsa), önce arama yaparak ID'yi bul
  if (!reqUrl.includes('--')) {
    console.log('DEBUG - Slug has no ID, searching for:', reqUrl);
    const searchModule = require('./search');
    const searchResult = await searchModule.getSearch(reqUrl);
    console.log('DEBUG - Search returned', searchResult.threads?.length, 'results');

    if (searchResult.error || !searchResult.threads || searchResult.threads.length === 0) {
      console.log('DEBUG - No results found');
      return { error: 'Başlık bulunamadı' };
    }

    // Tam eşleşen başlığı bul
    const searchQuery = reqUrl.toLowerCase().trim();

    // Debug: İlk 5 sonucu göster
    console.log('DEBUG - First 5 search results:');
    searchResult.threads.slice(0, 5).forEach((t, i) => {
      console.log(`  ${i + 1}. "${t.title}" (${t.slug})`);
    });

    // 1. Önce tam eşleşme ara
    let matchedResult = searchResult.threads.find(t =>
      t.title && t.title.toLowerCase().trim() === searchQuery
    );

    console.log('DEBUG - Exact match result:', matchedResult ? matchedResult.title : 'none');

    // 2. Tam eşleşme yoksa, tek kelime olan başlıkları ara (örn: "adam", "teknoloji")
    if (!matchedResult) {
      matchedResult = searchResult.threads.find(t => {
        const title = t.title ? t.title.toLowerCase().trim() : '';
        // Başlık tek kelimeden oluşuyor ve aranan kelimeye eşit mi?
        return title.split(/\s+/).length === 1 && title === searchQuery;
      });
      console.log('DEBUG - Single word match:', matchedResult ? matchedResult.title : 'none');
    }

    // 3. Hala bulunamadıysa, başlık aranan kelime ile başlıyor mu?
    if (!matchedResult) {
      matchedResult = searchResult.threads.find(t => {
        const title = t.title ? t.title.toLowerCase().trim() : '';
        return title.startsWith(searchQuery + ' ') || title === searchQuery;
      });
      console.log('DEBUG - Starts-with match:', matchedResult ? matchedResult.title : 'none');
    }

    // 4. Hiçbir sonuç yoksa ve tek kelimeyse, direkt URL dene
    if (!matchedResult && searchQuery.split(/\s+/).length === 1) {
      console.log('DEBUG - No match for single word, trying direct URL');
      // Ekşi Sözlük otomatik redirect yapacak
      reqUrl = searchQuery; // ID'yi Puppeteer sayfadan bulacak
    } else if (matchedResult) {
      // Match bulundu, slug'ı temizle
      console.log('DEBUG - Found matching result:', matchedResult.title);
      let cleanSlug = matchedResult.slug;
      if (cleanSlug.startsWith(URLS.BASE)) {
        cleanSlug = cleanSlug.replace(URLS.BASE, '');
      }
      if (cleanSlug.startsWith('/')) {
        cleanSlug = cleanSlug.substring(1);
      }
      reqUrl = cleanSlug;
    } else {
      // Son çare: ilk sonucu kullan
      matchedResult = searchResult.threads[0];
      console.log('DEBUG - Using first result:', matchedResult.title);
      let cleanSlug = matchedResult.slug;
      if (cleanSlug.startsWith(URLS.BASE)) {
        cleanSlug = cleanSlug.replace(URLS.BASE, '');
      }
      if (cleanSlug.startsWith('/')) {
        cleanSlug = cleanSlug.substring(1);
      }
      reqUrl = cleanSlug;
    }

    console.log('DEBUG - New reqUrl after search:', reqUrl);
  }

  const finalUrl = URLS.BASE + "/" + reqUrl + pageParam; // Sayfa parametresini ekle
  console.log('DEBUG - Final URL:', finalUrl);

  // Puppeteer ile sayfayı yükle
  let browser;
  let pageContent;
  try {
    browser = await puppeteer.launch({
      headless: 'new',
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-accelerated-2d-canvas',
        '--disable-gpu',
        '--disable-blink-features=AutomationControlled'
      ]
    });

    const page = await browser.newPage();

    // Daha gerçekçi browser ayarları
    await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36');
    await page.setExtraHTTPHeaders({
      'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
      'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    });

    // Automation tespit engelleyicileri devre dışı bırak
    await page.evaluateOnNewDocument(() => {
      Object.defineProperty(navigator, 'webdriver', {
        get: () => false,
      });
    });

    console.log('DEBUG - Navigating with Puppeteer...');
    await page.goto(finalUrl, {
      waitUntil: 'domcontentloaded',
      timeout: 30000
    });

    // Sayfanın yüklenmesini bekle - yeni Puppeteer versiyonu için
    await new Promise(resolve => setTimeout(resolve, 2000));

    console.log('DEBUG - Page loaded successfully');
    pageContent = await page.content();

    // HTML içeriğinin ilk 500 karakterini debug için göster
    console.log('DEBUG - Page HTML preview:', pageContent.substring(0, 500));

    await browser.close();
  } catch (err) {
    if (browser) await browser.close();
    console.error('DEBUG - Puppeteer failed:', err.message);
    return { error: err.message, url: finalUrl };
  }

  let entries = [];
  let entry = {};
  let thread = {};
  let title, id, body, date, author, author_id, fav_count, created_at, updated_at, total_page, tags, disambiguations;
  let current_page;
  let disambiguation_links = [];
  let disambiguation_titles = [];
  let $ = cheerio.load(pageContent, { decodeEntities: false });

  title = $("#title").attr("data-title");
  threadID = $("#title").attr("data-id");

  console.log('DEBUG - Parsed title:', title);
  console.log('DEBUG - Found entries:', $("#entry-item-list li").length);

  slug = $("#title").attr("data-slug") + "--" + threadID;
  total_page = parseInt($(".pager").attr("data-pagecount")) || 1;
  current_page = parseInt($(".pager").attr("data-currentpage")) || 1;
  tags = $("#hidden-channels").text().trim().split(",") || null;
  tags = tags[0] == "" ? null : tags;

  disambiguations = $("#disambiguations").find("ul > li").each(function (index, element) {
    disambiguation_links.push($(element).find("a").attr("href"));
    disambiguation_titles.push($(element).text());
  });

  $("#entry-item-list").find("li").each(function (index, element) {
    id = $(element).attr("data-id");
    fav_count = $(element).attr("data-favorite-count");
    author_id = $(element).attr("data-author-id");

    const contentHtml = $(element).find(".content").html();
    body = contentHtml ? contentHtml.trim() : '';

    date = $(element).find(".entry-date").text();
    author = $(element).find(".entry-author").text();
    date = $(element).find(".entry-date").text();
    [created_at, updated_at] = parseDate(date);

    // Boş entry'leri atla (body, author veya id yoksa)
    if (!body || !author || !id) {
      return; // Bu entry'i atla
    }

    entry = {
      id,
      body,
      author,
      author_id,
      fav_count,
      created_at,
      updated_at
    };
    entries.push(entry);
  });

  console.log('DEBUG - Total entries after filtering:', entries.length);

  thread = {
    id: threadID,
    disambiguation_titles,
    disambiguation_links,
    title,
    slug,
    total_page,
    current_page,
    tags,
    entries
  }

  return thread;
}

/*
  parse endpoint url: basliklar/  
*/
function parseUrl(reqUrl) {
  let parsedUrl = url.parse(reqUrl); //    /api/basliklar?kanal=spor?p=2
  let parsedQs = querystring.parse(parsedUrl.query);

  let retUrl = "gundem";

  if (parsedQs.kanal)
    retUrl = "kanal/" + encodeURIComponent(parsedQs.kanal); // /kanal/spor

  if (parsedQs.p)
    retUrl += "?p=" + parsedQs.p; //      /kanal/spor?p=2

  return retUrl;
}

function parseDetailUrl(reqUrl) {
  // /baslik/adam?p=2 -> adam?p=2 gibi durumları ayır
  const urlPart = reqUrl.split("/baslik/")[1];

  // ?p=2 gibi query parametrelerini ayır
  if (urlPart && urlPart.includes('?')) {
    const [slug, queryString] = urlPart.split('?');
    return slug; // Sadece slug'ı döndür, sayfa parametresini Puppeteer URL'sine ekleyeceğiz
  }

  return urlPart;
}

exports.idFromSlug = function (slug) {   //slug = "https://eksisozluk.com/pena--31782"
  let pathname = url.parse(slug).pathname; // pathname = "/pena--31782"
  let splar = pathname.split("--"); // ["/pena", "31782"]
  return splar[splar.length - 1];   // id = "31782"
}

function parseDate(date) {
  let created_at = date;
  let updated_at = created_at.includes("~") ? created_at.split("~")[1].trim() : null;
  if (updated_at) {
    created_at = created_at.slice(0, -1 * (updated_at.length + 2)).trim();
    if (created_at.length > updated_at.length) {
      updated_at = created_at.slice(0, -1 * (updated_at.length)) + updated_at;
    }
  }
  return [created_at, updated_at]
}