const url = require('url');
const querystring = require('querystring');

const axios = require('axios');
const cheerio = require('cheerio');

const URLS = require('./constants');
const thradJs = require('./thread');


exports.getSearch = async function (query) {
  let response;
  query = parseQuery(query);
  const searchUrl = URLS.SEARCH + encodeURIComponent(query);
  console.log('DEBUG - Search URL:', searchUrl);

  try {
    response = await axios.get(searchUrl, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
        'Connection': 'keep-alive'
      }
    });
    console.log('DEBUG - Search successful, status:', response.status);
  } catch (err) {
    console.error('DEBUG - Search failed:', err.message);
    console.error('DEBUG - Search error status:', err.response?.status);
    return { error: err.message };
  }

  let $ = cheerio.load(response.data, { decodeEntities: false });
  let search_result = {};
  let threads = [];
  let title, entry_count_total, thread = {};

  $("#content-body > .topic-list").find("li > a").each(function (index, element) {
    title = $(element).contents().filter(function () {
      return this.nodeType === 3;
    }).text().trim();
    entry_count_total = $(element).find("small").text() || '1';
    const href = $(element).attr("href");
    console.log('DEBUG - Search result item:', { title, href });
    slug = URLS.BASE + href;
    id = thradJs.idFromSlug(slug);
    thread = {
      id: parseInt(id),
      title,
      slug,
      entry_count_total,
    }
    console.log('DEBUG - Thread object:', thread);
    threads.push(thread)
  });

  search_result = {
    thread_count: $(".topic-list-description").text().trim(),
    threads
  }
  return search_result;
}

exports.autoComplete = async function (query) {
  let response;
  try {
    response = await axios.get(URLS.AUTO_SEARCH + encodeURIComponent(query), {
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
  return response.data;
}

// NOT implemented yet
function parseSearchUrl(reqUrl) {
  let parsedUrl = url.parse(reqUrl);
  let parsedQs = querystring.parse(parsedUrl.query);
  // console.log(parsedQs);
}


function parseQuery(query) {
  console.log('DEBUG - parseQuery input:', query);
  let q = query;

  // Eğer URL formatındaysa parse et
  if (query.includes("/ara/")) {
    q = query.split("/ara/")[1];
  }

  console.log('DEBUG - parseQuery output:', q);
  return q;
}
