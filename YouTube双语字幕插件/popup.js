const STORAGE_KEY = 'ytBilingualEnabled';
const DEBUG_KEY = 'ytBilingualDebug';
const checkbox = document.getElementById('enabled');
const debugCheckbox = document.getElementById('debug');

chrome.storage.sync.get([STORAGE_KEY, DEBUG_KEY], (data) => {
  checkbox.checked = data[STORAGE_KEY] !== false;
  debugCheckbox.checked = data[DEBUG_KEY] === true;
});

checkbox.addEventListener('change', () => {
  chrome.storage.sync.set({ [STORAGE_KEY]: checkbox.checked });
});
debugCheckbox.addEventListener('change', () => {
  chrome.storage.sync.set({ [DEBUG_KEY]: debugCheckbox.checked });
});
