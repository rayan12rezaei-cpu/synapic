const state = {
  file: null,
  original: '',
  translated: '',
  activeTab: 'original',
  ocrLanguage: localStorage.getItem('synapic-ocr-language') || 'fa',
  targetLanguage: localStorage.getItem('synapic-target-language') || 'en',
  uiLanguage: localStorage.getItem('synapic-ui-language') || 'fa',
  theme: localStorage.getItem('synapic-theme') || 'system',
};

const i18n = {
  fa: {
    source: 'متن', workspace: 'استخراج و ترجمه', uploadTitle: 'تصویر یا PDF را بارگذاری کنید', uploadSub: 'PNG · JPG · WEBP · PDF',
    ocrLang: 'زبان متن', targetLang: 'ترجمه به', extract: 'استخراج متن', translate: 'ترجمه', speakOriginal: 'خواندن اصلی', speakTranslated: 'خواندن ترجمه',
    export: 'خروجی', original: 'متن اصلی', translated: 'ترجمه', settings: 'تنظیمات', uiLanguage: 'زبان سایت', theme: 'تم', system: 'سیستم', dark: 'دارک', light: 'لایت', save: 'ذخیره',
    page: 'صفحه', pages: 'صفحه', characters: 'کاراکتر', ready: 'آماده', extracting: 'در حال استخراج…', translating: 'در حال ترجمه…', done: 'انجام شد', selectFile: 'یک فایل انتخاب کنید',
    noText: 'متنی برای پردازش وجود ندارد', low: 'کیفیت OCR پایین است', medium: 'کیفیت OCR متوسط است', high: 'کیفیت OCR بالا است', translationUnavailable: 'ترجمه انجام نشد',
  },
  en: {
    source: 'TEXT', workspace: 'Extract & Translate', uploadTitle: 'Upload an image or PDF', uploadSub: 'PNG · JPG · WEBP · PDF',
    ocrLang: 'Source text', targetLang: 'Translate to', extract: 'Extract text', translate: 'Translate', speakOriginal: 'Read original', speakTranslated: 'Read translation',
    export: 'Export', original: 'Original', translated: 'Translation', settings: 'Settings', uiLanguage: 'Site language', theme: 'Theme', system: 'System', dark: 'Dark', light: 'Light', save: 'Save',
    page: 'Page', pages: 'Pages', characters: 'characters', ready: 'Ready', extracting: 'Extracting…', translating: 'Translating…', done: 'Done', selectFile: 'Choose a file',
    noText: 'There is no text to process', low: 'Low OCR confidence', medium: 'Medium OCR confidence', high: 'High OCR confidence', translationUnavailable: 'Translation failed',
  },
  zh: {
    source: '文本', workspace: '提取与翻译', uploadTitle: '上传图片或 PDF', uploadSub: 'PNG · JPG · WEBP · PDF',
    ocrLang: '原文语言', targetLang: '翻译为', extract: '提取文字', translate: '翻译', speakOriginal: '朗读原文', speakTranslated: '朗读译文',
    export: '导出', original: '原文', translated: '译文', settings: '设置', uiLanguage: '网站语言', theme: '主题', system: '系统', dark: '深色', light: '浅色', save: '保存',
    page: '页', pages: '页', characters: '字符', ready: '就绪', extracting: '正在提取…', translating: '正在翻译…', done: '完成', selectFile: '选择文件',
    noText: '没有可处理的文本', low: 'OCR 置信度低', medium: 'OCR 置信度中等', high: 'OCR 置信度高', translationUnavailable: '翻译失败',
  }
};

const $ = (id) => document.getElementById(id);
const fileInput = $('fileInput');
const dropzone = $('dropzone');
const fileName = $('fileName');
const extractBtn = $('extractBtn');
const translateBtn = $('translateBtn');
const originalText = $('originalText');
const translatedText = $('translatedText');
const emptyState = $('emptyState');
const statusDot = $('statusDot');
const pageMeta = $('pageMeta');
const confidenceMeta = $('confidenceMeta');
const charCount = $('charCount');
const liveState = $('liveState');
const progressWrap = $('progressWrap');
const progressLabel = $('progressLabel');
const progressPct = $('progressPct');
const progressBar = $('progressBar');

function t(key) { return i18n[state.uiLanguage][key] || key; }
function escapeHtml(value) { return value.replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }

function applyI18n() {
  document.querySelectorAll('[data-i18n]').forEach(el => { el.textContent = t(el.dataset.i18n); });
  document.documentElement.lang = state.uiLanguage;
  document.documentElement.dir = state.uiLanguage === 'en' || state.uiLanguage === 'zh' ? 'ltr' : 'rtl';
  $('uiLanguage').value = state.uiLanguage;
  $('themeSelect').value = state.theme;
}

function effectiveTheme() {
  if (state.theme === 'system') return matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
  return state.theme;
}
function applyTheme() { document.documentElement.dataset.theme = effectiveTheme(); }

function showToast(message) {
  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.textContent = message;
  $('toastStack').appendChild(toast);
  setTimeout(() => toast.remove(), 3200);
}

function setProgress(label, pct) {
  progressWrap.classList.remove('hidden');
  progressLabel.textContent = label;
  progressPct.textContent = `${pct}%`;
  progressBar.style.width = `${Math.max(0, Math.min(100, pct))}%`;
}
function resetProgress() { progressWrap.classList.add('hidden'); progressBar.style.width = '0%'; }

function updateEditorDirection() {
  const map = {fa: 'rtl', en: 'ltr', zh: 'ltr'};
  originalText.style.direction = map[state.ocrLanguage] || 'ltr';
  translatedText.style.direction = map[state.targetLanguage] || 'ltr';
}

function updateMeta(confidence = null, pages = null) {
  const current = state.activeTab === 'original' ? state.original : state.translated;
  charCount.textContent = `${current.length.toLocaleString()} ${t('characters')}`;
  if (pages !== null) pageMeta.textContent = `${pages} ${t('pages')}`;
  if (confidence !== null) confidenceMeta.textContent = `${Math.round(confidence * 100)}%`;
}

function updateEmptyState() { emptyState.classList.toggle('hidden', Boolean(state.original || state.translated)); }
function updateButtons() {
  const hasOriginal = Boolean(state.original.trim());
  translateBtn.disabled = !hasOriginal;
  $('speakOriginalBtn').disabled = !hasOriginal;
  $('speakTranslatedBtn').disabled = !state.translated.trim();
  document.querySelectorAll('.export-btn').forEach(b => b.disabled = !(state.activeTab === 'translated' ? state.translated.trim() : state.original.trim()));
  extractBtn.disabled = !state.file;
}

function setFile(file) {
  if (!file) return;
  const ok = /image\//.test(file.type) || /\.pdf$/i.test(file.name);
  if (!ok) { showToast('Unsupported file'); return; }
  state.file = file;
  fileName.textContent = file.name;
  statusDot.classList.add('active');
  extractBtn.disabled = false;
}
fileInput.addEventListener('change', () => setFile(fileInput.files[0]));
['dragenter','dragover'].forEach(evt => dropzone.addEventListener(evt, e => { e.preventDefault(); dropzone.classList.add('dragover'); }));
['dragleave','drop'].forEach(evt => dropzone.addEventListener(evt, e => { e.preventDefault(); dropzone.classList.remove('dragover'); }));
dropzone.addEventListener('drop', e => setFile(e.dataTransfer.files[0]));

async function extract() {
  if (!state.file) { showToast(t('selectFile')); return; }
  const form = new FormData();
  form.append('file', state.file);
  setProgress(t('extracting'), 16);
  liveState.textContent = t('extracting');
  extractBtn.disabled = true;
  try {
    const res = await fetch(`/api/ocr?language=${encodeURIComponent(state.ocrLanguage)}`, { method: 'POST', body: form });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'OCR failed');
    state.original = data.text || '';
    state.translated = '';
    originalText.value = state.original;
    translatedText.value = '';
    updateMeta(data.confidence, data.pages);
    emptyState.classList.toggle('hidden', Boolean(state.original));
    setTab('original');
    setProgress(t('done'), 100);
    liveState.textContent = t('done');
    const confidence = data.confidence;
    showToast(confidence < .4 ? t('low') : confidence < .7 ? t('medium') : t('high'));
  } catch (err) {
    showToast(err.message || 'OCR failed');
    liveState.textContent = '';
    resetProgress();
  } finally {
    extractBtn.disabled = !state.file;
    updateButtons();
    setTimeout(resetProgress, 700);
  }
}
extractBtn.addEventListener('click', extract);

async function translate() {
  if (!state.original.trim()) { showToast(t('noText')); return; }
  translateBtn.disabled = true;
  setProgress(t('translating'), 28);
  liveState.textContent = t('translating');
  try {
    const res = await fetch('/api/translate', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: state.original, source: state.ocrLanguage, target: state.targetLanguage })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || t('translationUnavailable'));
    state.translated = data.text || '';
    translatedText.value = state.translated;
    setTab('translated');
    setProgress(t('done'), 100);
    liveState.textContent = t('done');
  } catch (err) {
    showToast(err.message || t('translationUnavailable'));
    liveState.textContent = '';
    resetProgress();
  } finally {
    updateButtons();
    setTimeout(resetProgress, 700);
  }
}
translateBtn.addEventListener('click', translate);

function currentSpeechText(kind) {
  return kind === 'original' ? state.original : state.translated;
}
function speechLang(kind) {
  const lang = kind === 'original' ? state.ocrLanguage : state.targetLanguage;
  return ({fa:'fa-IR', en:'en-US', zh:'zh-CN'})[lang] || 'en-US';
}
function speak(kind) {
  const text = currentSpeechText(kind).trim();
  if (!text || !('speechSynthesis' in window)) return;
  speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = speechLang(kind);
  utterance.rate = 0.95;
  speechSynthesis.speak(utterance);
}
$('speakOriginalBtn').addEventListener('click', () => speak('original'));
$('speakTranslatedBtn').addEventListener('click', () => speak('translated'));

function setTab(tab) {
  state.activeTab = tab;
  document.querySelectorAll('.tab').forEach(btn => btn.classList.toggle('active', btn.dataset.tab === tab));
  originalText.classList.toggle('active', tab === 'original');
  translatedText.classList.toggle('active', tab === 'translated');
  updateMeta(); updateButtons();
}
document.querySelectorAll('.tab').forEach(btn => btn.addEventListener('click', () => setTab(btn.dataset.tab)));

function syncTextValues() {
  state.original = originalText.value;
  state.translated = translatedText.value;
  updateEmptyState(); updateMeta(); updateButtons();
}
originalText.addEventListener('input', syncTextValues);
translatedText.addEventListener('input', syncTextValues);

document.querySelectorAll('.export-btn').forEach(btn => btn.addEventListener('click', async () => {
  const format = btn.dataset.format;
  const text = state.activeTab === 'translated' ? state.translated : state.original;
  if (!text.trim()) { showToast(t('noText')); return; }
  try {
    const res = await fetch('/api/export', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({text, format}) });
    if (!res.ok) { const data = await res.json(); throw new Error(data.detail || 'Export failed'); }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = `synapic-export.${format}`; a.click(); URL.revokeObjectURL(url);
  } catch (err) { showToast(err.message || 'Export failed'); }
}));

$('themeToggle').addEventListener('click', () => {
  state.theme = state.theme === 'dark' ? 'light' : 'dark';
  localStorage.setItem('synapic-theme', state.theme);
  applyTheme(); $('themeSelect').value = state.theme;
});
$('settingsToggle').addEventListener('click', () => $('settingsDialog').showModal());
$('saveSettings').addEventListener('click', e => {
  e.preventDefault();
  state.uiLanguage = $('uiLanguage').value;
  state.theme = $('themeSelect').value;
  state.ocrLanguage = $('ocrLanguage').value;
  state.targetLanguage = $('targetLanguage').value;
  updateEditorDirection();
  localStorage.setItem('synapic-ui-language', state.uiLanguage);
  localStorage.setItem('synapic-theme', state.theme);
  localStorage.setItem('synapic-ocr-language', state.ocrLanguage);
  localStorage.setItem('synapic-target-language', state.targetLanguage);
  applyI18n(); applyTheme(); updateMeta(); $('settingsDialog').close();
});
matchMedia('(prefers-color-scheme: light)').addEventListener('change', applyTheme);
$('ocrLanguage').value = state.ocrLanguage;
$('targetLanguage').value = state.targetLanguage;
applyI18n(); applyTheme(); updateEditorDirection(); updateEmptyState(); updateButtons(); updateMeta();
