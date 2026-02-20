/**
 * YouTube 双语字幕 - 后台服务
 * 优先使用 Google 翻译（非官方接口），备用 Lingva / LibreTranslate / MyMemory
 */

const GOOGLE_URL = 'https://translate.googleapis.com/translate_a/single';
const LINGVA_INSTANCES = [
  'https://lingva.ml',
  'https://translate.plausibility.cloud',
  'https://lingva.lunar.icu',
];
const LIBRE_URL = 'https://libretranslate.com/translate';
const MYMEMORY_URL = 'https://api.mymemory.translated.net/get';
const CACHE_MAX = 200;
const translationCache = new Map();

function getCached(key) {
  if (!translationCache.has(key)) return null;
  const entry = translationCache.get(key);
  entry.lastUsed = Date.now();
  return entry.text;
}

function setCache(key, text) {
  if (translationCache.size >= CACHE_MAX) {
    const oldest = [...translationCache.entries()]
      .sort((a, b) => a[1].lastUsed - b[1].lastUsed)[0];
    if (oldest) translationCache.delete(oldest[0]);
  }
  translationCache.set(key, { text, lastUsed: Date.now() });
}

/** 若为 MyMemory 的额度/警告文案则视为无效 */
function isValidTranslation(text) {
  if (!text || typeof text !== 'string') return false;
  const t = text.trim().toUpperCase();
  return !t.startsWith('MYMEMORY WARNING') && !t.includes('AVAILABLE FREE');
}

/** Google 翻译（非官方接口，与 translate.google.com 同源） */
function translateWithGoogle(text) {
  const params = new URLSearchParams({
    client: 'gtx',
    sl: 'en',
    tl: 'zh-CN',
    dt: 't',
    q: text,
  });
  return fetch(`${GOOGLE_URL}?${params}`, {
    headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; rv:109.0) Gecko/20100101 Firefox/115.0' },
  })
    .then((r) => r.json())
    .then((data) => {
      if (!Array.isArray(data) || !data[0]) return '';
      const parts = [];
      for (const block of data[0]) {
        if (block && block[0]) parts.push(block[0]);
      }
      return parts.join('').trim();
    });
}

/** Lingva 公开实例（后端为 Google 翻译）GET /api/v1/en/zh/encoded */
function translateWithLingva(text) {
  const encoded = encodeURIComponent(text);
  let lastErr;
  function tryNext(i) {
    if (i >= LINGVA_INSTANCES.length) return Promise.reject(lastErr || new Error('Lingva failed'));
    const base = LINGVA_INSTANCES[i];
    return fetch(`${base}/api/v1/en/zh/${encoded}`, {
      headers: { 'Accept': 'application/json' },
    })
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(r.status))))
      .then((data) => (data && data.translation ? String(data.translation).trim() : ''))
      .catch((err) => {
        lastErr = err;
        return tryNext(i + 1);
      });
  }
  return tryNext(0);
}

function translateWithLibre(text) {
  return fetch(LIBRE_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ q: text, source: 'en', target: 'zh' }),
  })
    .then((r) => (r.ok ? r.json() : Promise.reject(new Error(r.status))))
    .then((data) => (data && data.translatedText ? String(data.translatedText).trim() : ''));
}

function translateWithMyMemory(text) {
  const params = new URLSearchParams({ q: text, langpair: 'en|zh' });
  return fetch(`${MYMEMORY_URL}?${params}`)
    .then((r) => r.json())
    .then((data) => {
      const raw = data?.responseData?.translatedText || '';
      return isValidTranslation(raw) ? String(raw).trim() : '';
    });
}

function doTranslate(text, sendResponse) {
  const cacheKey = `en|zh|${text}`;
  const cached = getCached(cacheKey);
  if (cached !== null) {
    sendResponse({ ok: true, translated: cached });
    return;
  }
  translateWithGoogle(text)
    .then((translated) => {
      if (translated) {
        setCache(cacheKey, translated);
        sendResponse({ ok: true, translated });
        return undefined;
      }
      return translateWithLingva(text);
    })
    .then((fallback) => {
      if (fallback === undefined) return;
      if (fallback) {
        setCache(cacheKey, fallback);
        sendResponse({ ok: true, translated: fallback });
        return undefined;
      }
      return translateWithLibre(text);
    })
    .then((fallback2) => {
      if (fallback2 === undefined) return;
      if (fallback2) {
        setCache(cacheKey, fallback2);
        sendResponse({ ok: true, translated: fallback2 });
        return undefined;
      }
      return translateWithMyMemory(text);
    })
    .then((fallback3) => {
      if (fallback3 === undefined) return;
      if (fallback3) {
        setCache(cacheKey, fallback3);
        sendResponse({ ok: true, translated: fallback3 });
      } else {
        sendResponse({ ok: true, translated: '' });
      }
    })
    .catch(() => {
      translateWithLingva(text)
        .then((t) => {
          if (t) {
            setCache(cacheKey, t);
            sendResponse({ ok: true, translated: t });
          } else {
            return translateWithMyMemory(text).then((m) => {
              if (m) {
                setCache(cacheKey, m);
                sendResponse({ ok: true, translated: m });
              } else {
                sendResponse({ ok: false, error: 'all sources failed' });
              }
            });
          }
        })
        .catch(() =>
          translateWithMyMemory(text).then((m) => {
            if (m) {
              setCache(cacheKey, m);
              sendResponse({ ok: true, translated: m });
            } else {
              sendResponse({ ok: false, error: 'all sources failed' });
            }
          })
        );
    });
}

chrome.runtime.onMessage.addListener((request, _sender, sendResponse) => {
  if (request.type !== 'TRANSLATE') return false;
  const text = (request.text || '').trim();
  if (!text) {
    sendResponse({ ok: false, error: 'empty' });
    return false;
  }
  doTranslate(text, sendResponse);
  return true;
});
