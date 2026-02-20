/**
 * YouTube 双语字幕 - 内容脚本
 * 监听 YouTube 字幕 DOM，同步显示中文翻译（支持 Shadow DOM）
 */

const ext = (typeof chrome !== 'undefined' && chrome.runtime) ? chrome : (typeof browser !== 'undefined' && browser.runtime) ? browser : null;

const CONTAINER_SELECTORS = [
  '.ytp-caption-window-container',
  '[class*="caption-window-container"]',
  '[class*="captionWindowContainer"]',
];
const WINDOW_SELECTORS = [
  '[id^="caption-window-"]',
  '[class*="caption-window"]',
  '.ytp-caption-window',
];
const SEGMENT_SELECTOR = '.ytp-caption-segment';
const STORAGE_KEY = 'ytBilingualEnabled';
const DEBUG_KEY = 'ytBilingualDebug';
const DEBOUNCE_MS = 30;
const PANEL_ID = 'yt-bilingual-panel';
const PANEL_POS_KEY = 'ytBilingualPanelPos';
const PANEL_MINIMIZED_KEY = 'ytBilingualPanelMinimized';
const POLL_INTERVAL_MS = 800;

let enabled = true;
let captionRoot = null;
let panel = null;
let observer = null;
let dragOffsetX = 0;
let dragOffsetY = 0;
let lastText = '';
let debounceTimer = null;
let pendingTranslateText = null;
let pendingTranslateCallback = null;
let debug = false;
let cachedCaptionWindow = null;
let cachedCaptionContainer = null;
let watchPlayerObserver = null;
let attachAttempts = 0;

function queryCaptionLight(selectors) {
  for (const sel of selectors) {
    const el = document.querySelector(sel);
    if (el) return el;
  }
  return null;
}

function getCaptionContainer() {
  if (cachedCaptionContainer && document.contains(cachedCaptionContainer)) {
    return cachedCaptionContainer;
  }
  const el = queryCaptionLight(CONTAINER_SELECTORS);
  if (el) {
    cachedCaptionContainer = el;
    return el;
  }
  cachedCaptionContainer = null;
  return null;
}

function getCaptionWindow() {
  if (cachedCaptionWindow && document.contains(cachedCaptionWindow)) {
    return cachedCaptionWindow;
  }
  const el = queryCaptionLight(WINDOW_SELECTORS);
  if (el) {
    cachedCaptionWindow = el;
    return el;
  }
  cachedCaptionWindow = null;
  return null;
}

function getCaptionRootOrSegmentParent() {
  const win = getCaptionWindow();
  if (win) return win;
  const segment = document.querySelector(SEGMENT_SELECTOR);
  if (segment && segment.parentElement) return segment.parentElement;
  return null;
}

function getCaptionText() {
  const root = getCaptionWindow();
  if (root) {
    const segments = root.querySelectorAll(SEGMENT_SELECTOR);
    if (segments.length) {
      return [...segments].map((el) => el.textContent).join(' ').trim();
    }
    const text = root.textContent || '';
    if (text.trim()) return text.trim();
  }
  const segment = document.querySelector(SEGMENT_SELECTOR);
  if (segment) {
    const parent = segment.parentElement;
    const segments = parent ? parent.querySelectorAll(SEGMENT_SELECTOR) : [segment];
    return [...segments].map((el) => el.textContent).join(' ').trim();
  }
  return '';
}

function ensureSidePanel() {
  if (panel && panel.parentNode) return panel;
  const root = document.body || document.documentElement;
  if (!root) {
    setTimeout(ensureSidePanel, 100);
    return null;
  }
  panel = document.createElement('div');
  panel.id = PANEL_ID;
  panel.setAttribute('aria-label', '双语字幕中文翻译');
  Object.assign(panel.style, {
    position: 'fixed',
    top: '50%',
    right: '20px',
    transform: 'translateY(-50%)',
    width: '320px',
    maxHeight: '40vh',
    overflowY: 'auto',
    padding: '14px 16px',
    background: 'rgba(28, 28, 28, 0.95)',
    border: '1px solid rgba(255,255,255,0.15)',
    borderRadius: '10px',
    boxShadow: '0 4px 24px rgba(0,0,0,0.4)',
    fontSize: '16px',
    lineHeight: '1.5',
    color: '#fff',
    fontFamily: '"Microsoft YaHei", "PingFang SC", "Hiragino Sans GB", "Roboto", sans-serif',
    wordWrap: 'break-word',
    zIndex: '2147483647',
    boxSizing: 'border-box',
    transition: 'opacity 0.2s ease',
    pointerEvents: 'auto',
    display: 'block',
    visibility: 'visible',
  });
  const header = document.createElement('div');
  header.setAttribute('data-panel-header', '1');
  Object.assign(header.style, {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: '8px',
    gap: '8px',
  });
  const title = document.createElement('div');
  title.textContent = '中文翻译';
  title.setAttribute('data-drag-handle', '1');
  Object.assign(title.style, {
    fontSize: '12px',
    color: 'rgba(255,255,255,0.65)',
    fontWeight: '600',
    cursor: 'move',
    userSelect: 'none',
    WebkitUserSelect: 'none',
    flex: '1',
    minWidth: '0',
  });
  const minBtn = document.createElement('button');
  minBtn.type = 'button';
  minBtn.setAttribute('aria-label', '最小化');
  minBtn.title = '最小化';
  minBtn.textContent = '−';
  Object.assign(minBtn.style, {
    flexShrink: '0',
    width: '24px',
    height: '24px',
    padding: '0',
    border: 'none',
    borderRadius: '4px',
    background: 'rgba(255,255,255,0.12)',
    color: 'rgba(255,255,255,0.9)',
    fontSize: '18px',
    lineHeight: '1',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  });
  header.appendChild(title);
  header.appendChild(minBtn);
  panel.appendChild(header);
  const content = document.createElement('div');
  content.id = PANEL_ID + '-content';
  content.setAttribute('data-panel-content', '1');
  content.style.whiteSpace = 'pre-wrap';
  content.textContent = '开启 CC 字幕后，翻译将显示在此';
  content.style.color = 'rgba(255,255,255,0.7)';
  panel.appendChild(content);
  root.appendChild(panel);
  setupPanelDrag(panel);
  setupPanelMinimize(panel);
  restorePanelPosition(panel);
  restorePanelMinimized(panel);
  if (debug) console.log('[YouTube双语字幕] 已创建右侧翻译面板', root.tagName);
  return panel;
}

function setupPanelMinimize(panelEl) {
  const btn = panelEl.querySelector('button[aria-label="最小化"]');
  const content = panelEl.querySelector('[data-panel-content="1"]');
  if (!btn || !content) return;
  btn.addEventListener('click', (e) => {
    e.stopPropagation();
    const minimized = content.style.display === 'none';
    if (minimized) {
      content.style.display = '';
      btn.textContent = '−';
      btn.setAttribute('aria-label', '最小化');
      btn.title = '最小化';
      panelEl.style.maxHeight = '40vh';
      if (ext && ext.storage && ext.storage.sync) {
        const data = {};
        data[PANEL_MINIMIZED_KEY] = false;
        ext.storage.sync.set(data);
      }
    } else {
      content.style.display = 'none';
      btn.textContent = '▶';
      btn.setAttribute('aria-label', '展开');
      btn.title = '展开';
      panelEl.style.maxHeight = 'none';
      if (ext && ext.storage && ext.storage.sync) {
        const data = {};
        data[PANEL_MINIMIZED_KEY] = true;
        ext.storage.sync.set(data);
      }
    }
  });
}

function restorePanelMinimized(panelEl) {
  if (!ext || !ext.storage || !ext.storage.sync) return;
  ext.storage.sync.get(PANEL_MINIMIZED_KEY, (data) => {
    if (data && data[PANEL_MINIMIZED_KEY] === true) {
      const content = panelEl.querySelector('[data-panel-content="1"]');
      const btn = panelEl.querySelector('button[aria-label="最小化"]');
      if (content) content.style.display = 'none';
      if (btn) {
        btn.textContent = '▶';
        btn.setAttribute('aria-label', '展开');
        btn.title = '展开';
      }
      panelEl.style.maxHeight = 'none';
    }
  });
}

function setupPanelDrag(panelEl) {
  const handle = panelEl.querySelector('[data-drag-handle="1"]');
  if (!handle) return;
  handle.addEventListener('mousedown', (e) => {
    if (e.button !== 0) return;
    const rect = panelEl.getBoundingClientRect();
    dragOffsetX = e.clientX - rect.left;
    dragOffsetY = e.clientY - rect.top;
    panelEl.style.right = 'auto';
    panelEl.style.top = rect.top + 'px';
    panelEl.style.left = rect.left + 'px';
    panelEl.style.transform = 'none';
    const onMove = (e2) => {
      const w = panelEl.offsetWidth || rect.width;
      const h = panelEl.offsetHeight || 80;
      const x = e2.clientX - dragOffsetX;
      const y = e2.clientY - dragOffsetY;
      panelEl.style.left = Math.max(0, Math.min(x, window.innerWidth - w)) + 'px';
      panelEl.style.top = Math.max(0, Math.min(y, window.innerHeight - h)) + 'px';
    };
    const onUp = () => {
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
      savePanelPosition(panelEl);
    };
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  });
}

function savePanelPosition(panelEl) {
  const left = panelEl.style.left;
  const top = panelEl.style.top;
  if (!left || !top || !ext || !ext.storage || !ext.storage.sync) return;
  const data = {};
  data[PANEL_POS_KEY] = { left, top };
  ext.storage.sync.set(data);
}

function restorePanelPosition(panelEl) {
  if (!ext || !ext.storage || !ext.storage.sync) return;
  ext.storage.sync.get(PANEL_POS_KEY, (data) => {
    if (data && data.left != null && data.top != null) {
      panelEl.style.right = 'auto';
      panelEl.style.transform = 'none';
      panelEl.style.left = data.left;
      panelEl.style.top = data.top;
    }
  });
}

function getPanelContent() {
  if (panel && panel.parentNode) {
    const c = panel.querySelector('#' + PANEL_ID + '-content');
    if (c) return c;
  }
  const p = document.getElementById(PANEL_ID);
  return p ? p.querySelector('#' + PANEL_ID + '-content') : null;
}

function showChinese(text) {
  if (!enabled) return;
  if (text && /MYMEMORY WARNING|AVAILABLE FREE/i.test(text)) return;
  const p = ensureSidePanel();
  if (!p) return;
  const content = getPanelContent();
  if (content) {
    content.textContent = text || '开启 CC 字幕后，翻译将显示在此';
    content.style.color = text ? '#fff' : 'rgba(255,255,255,0.7)';
  }
  p.style.display = 'block';
  p.style.visibility = 'visible';
  p.style.opacity = '1';
}

function hideChinese() {
  const content = getPanelContent();
  if (content) {
    content.textContent = '开启 CC 字幕后，翻译将显示在此';
    content.style.color = 'rgba(255,255,255,0.7)';
  }
  const p = document.getElementById(PANEL_ID);
  if (p) p.style.display = 'none';
}

function requestTranslate(text, callback) {
  if (!ext || !ext.runtime) {
    if (debug) console.warn('[YouTube双语字幕] 扩展 API 不可用');
    callback('');
    return;
  }
  ext.runtime.sendMessage(
    { type: 'TRANSLATE', text },
    (response) => {
      if (ext.runtime.lastError) {
        if (debug) console.warn('[YouTube双语字幕] 翻译请求错误', ext.runtime.lastError);
        callback('');
        return;
      }
      callback(response?.ok ? (response.translated || '') : '');
    }
  );
}

function onCaptionChange() {
  const text = getCaptionText();
  if (text === lastText) {
    if (pendingTranslateText === text && pendingTranslateText) {
      pendingTranslateText = null;
    }
    return;
  }
  lastText = text;
  if (!text) {
    pendingTranslateText = null;
    hideChinese();
    return;
  }
  if (pendingTranslateText === text) {
    return;
  }
  if (debug) console.log('[YouTube双语字幕] 字幕文本确认:', text.substring(0, 50) + (text.length > 50 ? '...' : ''));
  requestTranslate(text, (translated) => {
    if (lastText === text) {
      if (debug) console.log('[YouTube双语字幕] 翻译结果:', translated ? translated.substring(0, 50) + '...' : '(空)');
      showChinese(translated);
    }
  });
}

function scheduleCheck() {
  const text = getCaptionText();
  if (text && text !== lastText && text !== pendingTranslateText) {
    pendingTranslateText = text;
    if (debug) console.log('[YouTube双语字幕] 字幕文本:', text.substring(0, 50) + (text.length > 50 ? '...' : ''));
    requestTranslate(text, (translated) => {
      if (pendingTranslateText === text) {
        pendingTranslateText = null;
        if (lastText === text) {
          if (debug) console.log('[YouTube双语字幕] 翻译结果:', translated ? translated.substring(0, 50) + '...' : '(空)');
          showChinese(translated);
        }
      }
    });
  }
  if (debounceTimer) clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => {
    debounceTimer = null;
    onCaptionChange();
  }, DEBOUNCE_MS);
}

function clearCaches() {
  cachedCaptionWindow = null;
  cachedCaptionContainer = null;
}

function attachObserver() {
  const root = getCaptionRootOrSegmentParent();
  if (!root || root === captionRoot) return;
  if (observer) {
    observer.disconnect();
    observer = null;
  }
  captionRoot = root;
  observer = new MutationObserver(() => {
    scheduleCheck();
  });
  observer.observe(root, {
    childList: true,
    subtree: true,
    characterData: true,
  });
  if (debug) console.log('[YouTube双语字幕] 已监听字幕节点', root);
  scheduleCheck();
}

function tryAttach() {
  if (!enabled) return;
  clearCaches();
  const root = getCaptionRootOrSegmentParent();
  if (root) {
    attachObserver();
    if (watchPlayerObserver) {
      watchPlayerObserver.disconnect();
      watchPlayerObserver = null;
    }
    attachAttempts = 0;
    return;
  }
  attachAttempts++;
  if (attachAttempts > 30) {
    attachAttempts = 0;
    return;
  }
  const player = document.querySelector('#movie_player, .html5-video-player, #player, ytd-player');
  if (player && !watchPlayerObserver) {
    watchPlayerObserver = new MutationObserver(() => {
      clearCaches();
      attachObserver();
    });
    watchPlayerObserver.observe(player, { childList: true, subtree: true });
    attachObserver();
  }
}

function applyEnabled() {
  if (!enabled) {
    if (observer) {
      observer.disconnect();
      observer = null;
    }
    if (watchPlayerObserver) {
      watchPlayerObserver.disconnect();
      watchPlayerObserver = null;
    }
    captionRoot = null;
    clearCaches();
    hideChinese();
    const p = document.getElementById(PANEL_ID);
    if (p) p.style.display = 'none';
  } else {
    attachAttempts = 0;
    tryAttach();
    ensureSidePanel();
  }
}

function loadSettings() {
  if (!ext || !ext.storage || !ext.storage.sync) {
    applyEnabled();
    return;
  }
  ext.storage.sync.get([STORAGE_KEY, DEBUG_KEY], (data) => {
    enabled = data[STORAGE_KEY] !== false;
    debug = data[DEBUG_KEY] === true;
    applyEnabled();
  });
}

if (ext && ext.storage && ext.storage.onChanged) {
  ext.storage.onChanged.addListener((changes, area) => {
    if (area !== 'sync') return;
    if (changes[STORAGE_KEY]) {
      enabled = changes[STORAGE_KEY].newValue !== false;
      applyEnabled();
    }
    if (changes[DEBUG_KEY]) {
      debug = changes[DEBUG_KEY].newValue === true;
    }
  });
}

loadSettings();

function init() {
  tryAttach();
  if (enabled) setTimeout(ensureSidePanel, 300);
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}

let pollInterval = null;
function startPolling() {
  if (pollInterval) return;
  pollInterval = setInterval(() => {
    if (!enabled) {
      clearInterval(pollInterval);
      pollInterval = null;
      return;
    }
    if (!captionRoot) {
      tryAttach();
    } else {
      const text = getCaptionText();
      if (text && text !== lastText) {
        onCaptionChange();
      }
    }
    if (!document.getElementById(PANEL_ID)) {
      setTimeout(ensureSidePanel, 200);
    }
  }, POLL_INTERVAL_MS);
}

startPolling();
