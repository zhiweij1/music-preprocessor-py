/* 浏览器端胶水：Pyodide 跑 mpp 解析器，OSMD 渲染 MusicXML。无后端。 */
const MODULES = [
  '__init__.py', 'ir.py', 'lexer.py', 'parser.py', 'lyrics.py',
  'lilypond.py', 'musicxml.py', 'transpose.py', 'diagnostics.py',
];

const DEMO = `Title:小星星
Key:C Time:4/4
Tempo:4=100

H: 一闪一闪亮晶晶，满天都是小星星

[C] 1 1 [G7] 5 5 | [Am] 6 6 [D7] 5 - |
[C] 4 4 [G] 3 3 | [C] 2 2 [G7] 1 - |`;

const $ = (id) => document.getElementById(id);
const statusEl = $('status');
const messagesEl = $('messages');
const dslInput = $('dsl-input');
const highlightEl = $('highlight');
const keySelect = $('key-select');
const convertBtn = $('convert-btn');
const pdfBtn = $('pdf-btn');
const downloadBtn = $('download-btn');
const respectBreaks = $('respect-breaks');
const measureWidth = $('measure-width');

let pyodide = null;
let osmd = null;
let lastXml = '';
let errorLine = 0;
let diagTimer = null;

/* ---- syntax highlighting (mirrors the VSCode TextMate grammar) ---- */
const DECL_NAMES = new Set([
  'Title', 'Subtitle', 'Subsubtitle', 'Composer', 'Poet', 'Instrument',
  'Arranger', 'Copyright', 'Key', 'Time', 'Tempo',
]);
const LYRIC_RE = /^\s*[HL]\d*:/;
const CHORD_RE = /^\[[^\]]*\]$/;
const BAR_RE = /^(\|\||\|\.|\.\||\|:|:\||\||:)$/;
const NOTE_RE = /^[qQsSdDcChH]?(?:#|b)?[0-9xX]['+,.]*$/;
const DECL_RE = /^([A-Za-z]+):(.*)$/;

function escapeHtml(text) {
  return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function highlightToken(part) {
  if (!part) return '';
  if (/^\s+$/.test(part)) return escapeHtml(part);
  const decl = DECL_RE.exec(part);
  if (decl && DECL_NAMES.has(decl[1])) {
    return `<span class="tok-key">${escapeHtml(decl[1] + ':')}</span>${escapeHtml(decl[2])}`;
  }
  if (CHORD_RE.test(part)) return `<span class="tok-chord">${escapeHtml(part)}</span>`;
  if (BAR_RE.test(part)) return `<span class="tok-bar">${escapeHtml(part)}</span>`;
  if (NOTE_RE.test(part)) return `<span class="tok-note">${escapeHtml(part)}</span>`;
  return escapeHtml(part);
}

function highlightLine(line) {
  const pct = line.indexOf('%');
  const code = pct >= 0 ? line.slice(0, pct) : line;
  const comment = pct >= 0 ? line.slice(pct) : '';
  let html;
  if (LYRIC_RE.test(code)) {
    html = `<span class="tok-lyric">${escapeHtml(code)}</span>`;
  } else {
    html = code.split(/(\s+)/).map(highlightToken).join('');
  }
  if (comment) html += `<span class="tok-comment">${escapeHtml(comment)}</span>`;
  return html;
}

function renderHighlight() {
  const lines = dslInput.value.split('\n');
  highlightEl.innerHTML = lines
    .map((line, i) => {
      const cls = i + 1 === errorLine ? 'hl-line err' : 'hl-line';
      return `<div class="${cls}">${highlightLine(line)}</div>`;
    })
    .join('');
  syncScroll();
}

function syncScroll() {
  highlightEl.scrollTop = dslInput.scrollTop;
  highlightEl.scrollLeft = dslInput.scrollLeft;
}

/* ---- live diagnostics: parse only, no engraving ---- */
function scheduleDiagnostics() {
  clearTimeout(diagTimer);
  diagTimer = setTimeout(runDiagnostics, 300);
}

async function runDiagnostics() {
  if (!pyodide) return;
  let result;
  try {
    pyodide.globals.set('__source', dslInput.value);
    result = pyodide.runPython(`
import json as _json
try:
    _score = parse_text(__source)
    _xml = musicxml.to_musicxml(_score)
    _json.dumps({'error': None, 'warnings': list(_score.warnings)})
except Exception as _exc:
    _json.dumps({'error': {
        'line': getattr(_exc, 'line', 0) or 0,
        'column': getattr(_exc, 'column', 0) or 0,
        'message': getattr(_exc, 'message', None) or str(_exc).split('\\n')[0],
        'suggestion': getattr(_exc, 'suggestion', '') or '',
    }, 'warnings': []})
    `);
  } catch (err) {
    errorLine = 0;
    showMessages([{ severity: 'error', message: String(err.message || err) }]);
    renderHighlight();
    return;
  } finally {
    try { pyodide.globals.delete('__source'); } catch (_) { /* ignore */ }
  }
  const payload = JSON.parse(result);
  errorLine = payload.error ? payload.error.line : 0;
  const diagnostics = [];
  if (payload.error) {
    let message = payload.error.message;
    if (payload.error.suggestion) message += ` — did you mean '${payload.error.suggestion}'?`;
    if (payload.error.line) {
      const column = payload.error.column ? `, column ${payload.error.column}` : '';
      message = `Line ${payload.error.line}${column}: ${message}`;
    }
    diagnostics.push({ severity: 'error', message });
  }
  for (const warning of payload.warnings) {
    diagnostics.push({ severity: 'warning', message: warning });
  }
  showMessages(diagnostics);
  renderHighlight();
}

function setStatus(text, kind) {
  statusEl.textContent = text;
  statusEl.className = 'status ' + (kind || '');
}

function showMessages(diagnostics) {
  messagesEl.innerHTML = '';
  for (const d of diagnostics) {
    const div = document.createElement('div');
    div.className = d.severity === 'error' ? 'err' : 'warn';
    div.textContent = (d.severity === 'error' ? '✗ ' : '⚠ ') + d.message;
    messagesEl.appendChild(div);
  }
}

function renderSheetHeader(headers) {
  $('sheet-title').textContent = headers.Title || '';
  const sub = [headers.Subtitle, headers.Subsubtitle].filter(Boolean).join(' · ');
  $('sheet-subtitle').textContent = sub;
  $('sheet-composer').textContent = headers.Composer || '';
  $('sheet-poet').textContent = headers.Poet || '';
}

function applyEngravingRules() {
  if (!osmd) return;
  const rules = osmd.EngravingRules;
  rules.NewSystemAtXMLNewSystemAttribute = respectBreaks.checked;
  // OSMD ignores MusicXML credit rendering reliably; we draw the title in HTML.
  rules.RenderTitle = false;
  rules.RenderSubtitle = false;
  rules.RenderComposer = false;
  rules.RenderLyricist = false;
  // Jazz lead-sheet look: MuseJazz Text for chords/lyrics (the same face the
  // MuseScore .mss style uses). Noteheads stay Gonville — VexFlow 1.2.93 has
  // no MuseJazz/Petaluma glyph set.
  rules.DefaultFontFamily = 'MuseJazz Text, "Songti SC", serif';
  rules.ChordSymbolTextHeight = 2.4;
  rules.LyricsHeight = 2.4;
  rules.StaffLineWidth = 0.1;
  const width = parseFloat(measureWidth.value) || 0;
  rules.FixedMeasureWidth = width > 0;
  if (width > 0) {
    rules.FixedMeasureWidthFixedValue = width;
    rules.FixedMeasureWidthUseForPickupMeasures = false;
  }
}

async function initPyodide() {
  pyodide = await loadPyodide();
  pyodide.FS.mkdir('/mpp');
  for (const name of MODULES) {
    const response = await fetch('./mpp/' + name);
    if (!response.ok) throw new Error('无法加载模块 ' + name);
    pyodide.FS.writeFile('/mpp/' + name, await response.text(), { encoding: 'utf8' });
  }
  pyodide.runPython(`
import sys
sys.path.insert(0, '/')
from mpp.parser import parse_text
from mpp import musicxml
from mpp.transpose import transpose_score
  `);
}

async function convert() {
  if (!pyodide || !osmd) return;
  const source = dslInput.value;
  const key = keySelect.value;
  showMessages([]);
  try {
    pyodide.globals.set('__source', source);
    pyodide.globals.set('__key', key || null);
    pyodide.globals.set('__respect_breaks', respectBreaks.checked);
    const result = pyodide.runPython(`
import json as _json
_score = parse_text(__source)
if __key:
    transpose_score(_score, __key)
_xml = musicxml.to_musicxml(_score, auto_break=not __respect_breaks)
_headers = {k: _score.headers[k] for k in ('Title','Subtitle','Subsubtitle','Composer','Poet') if k in _score.headers}
_json.dumps({'xml': _xml, 'headers': _headers, 'warnings': list(_score.warnings)})
    `);
    const payload = JSON.parse(result);
    pyodide.globals.delete('__source');
    pyodide.globals.delete('__key');
    pyodide.globals.delete('__respect_breaks');

    lastXml = payload.xml;
    renderSheetHeader(payload.headers || {});
    const diagnostics = payload.warnings.map((w) => ({ severity: 'warning', message: w }));
    showMessages(diagnostics);

    applyEngravingRules();
    await osmd.load(lastXml);
    osmd.render();
    pdfBtn.disabled = false;
    downloadBtn.disabled = false;
    if (errorLine) { errorLine = 0; renderHighlight(); }
  } catch (err) {
    pdfBtn.disabled = true;
    downloadBtn.disabled = true;
    try {
      await runDiagnostics();   // structured error with line/column
    } catch (_) {
      const message = String(err.message || err).split('\n').filter(Boolean).slice(-1)[0];
      showMessages([{ severity: 'error', message: message }]);
    }
  }
}

function openPdf() {
  if (!lastXml) return;
  const node = document.querySelector('#score svg');
  if (!node) return;
  const svg = node.outerHTML;
  const header = $('sheet-header').outerHTML;
  const win = window.open('', '_blank');
  if (!win) { alert('请允许弹出窗口以打开 PDF 视图'); return; }
  const fontUrl = new URL('fonts/MuseJazzText.otf', location.href).href;
  win.document.write(`<!DOCTYPE html><html><head><meta charset="utf-8"><title>Lead Sheet</title>
<style>@font-face{font-family:"MuseJazz Text";src:url("${fontUrl}") format("opentype");font-display:swap}
@page{size:A4;margin:12mm}body{margin:0;font-family:"MuseJazz Text",Georgia,"Songti SC",serif;color:#1f2430}
#sheet-header{text-align:center;padding:6px 0 2px}#sheet-title:not(:empty){font-size:26px;font-weight:600}
#sheet-subtitle:not(:empty){font-size:13px;color:#555}#sheet-composer{text-align:right;font-size:11px;min-height:14px}
#sheet-poet{text-align:left;font-size:11px;min-height:14px;margin-top:-14px}
svg{width:100%;height:auto}</style>
</head><body>${header}${svg}<script>window.addEventListener('load',()=>setTimeout(()=>window.print(),400))<\/script>
</body></html>`);
  win.document.close();
}

function downloadXml() {
  if (!lastXml) return;
  const blob = new Blob([lastXml], { type: 'application/vnd.recordare.musicxml+xml;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'score.musicxml';
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

(async function main() {
  dslInput.value = DEMO;
  renderHighlight();
  dslInput.addEventListener('input', () => {
    renderHighlight();
    scheduleDiagnostics();
  });
  dslInput.addEventListener('scroll', syncScroll);
  convertBtn.addEventListener('click', convert);
  keySelect.addEventListener('change', convert);
  respectBreaks.addEventListener('change', convert);
  measureWidth.addEventListener('change', convert);
  pdfBtn.addEventListener('click', openPdf);
  downloadBtn.addEventListener('click', downloadXml);

  // Make sure the chord/lyric face is ready before OSMD draws text.
  if (document.fonts && document.fonts.load) {
    try { await document.fonts.load('16px "MuseJazz Text"'); } catch (_) { /* serif fallback */ }
  }

  try {
    setStatus('正在加载转换引擎（Pyodide）…', 'loading');
    await initPyodide();
    osmd = new opensheetmusicdisplay.OpenSheetMusicDisplay('score', {
      autoResize: true,
      backend: 'svg',
      drawingParameters: 'compacttight',
      drawTitle: false,
      drawSubtitle: false,
      drawComposer: false,
      drawLyricist: false,
    });
    setStatus('就绪 · 转换在浏览器本地完成，文本不会上传', 'ready');
    convertBtn.disabled = false;
    pdfBtn.disabled = false;
    downloadBtn.disabled = false;
    await convert();
  } catch (err) {
    setStatus('引擎加载失败：' + (err.message || err), 'error');
  }
})();
