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
const keySelect = $('key-select');
const convertBtn = $('convert-btn');
const pdfBtn = $('pdf-btn');
const downloadBtn = $('download-btn');

let pyodide = null;
let osmd = null;
let lastXml = '';

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
    const result = pyodide.runPython(`
import json as _json
_score = parse_text(__source)
if __key:
    transpose_score(_score, __key)
_xml = musicxml.to_musicxml(_score)
_json.dumps({'xml': _xml, 'warnings': list(_score.warnings)})
    `);
    const payload = JSON.parse(result);
    pyodide.globals.delete('__source');
    pyodide.globals.delete('__key');

    lastXml = payload.xml;
    const diagnostics = payload.warnings.map((w) => ({ severity: 'warning', message: w }));
    showMessages(diagnostics);

    await osmd.load(lastXml);
    osmd.render();
    pdfBtn.disabled = false;
    downloadBtn.disabled = false;
  } catch (err) {
    const message = String(err.message || err).split('\n').filter(Boolean).slice(-1)[0];
    showMessages([{ severity: 'error', message: message }]);
    pdfBtn.disabled = true;
    downloadBtn.disabled = true;
  }
}

function openPdf() {
  if (!lastXml) return;
  const node = document.querySelector('#score svg');
  if (!node) return;
  const svg = node.outerHTML;
  const win = window.open('', '_blank');
  if (!win) { alert('请允许弹出窗口以打开 PDF 视图'); return; }
  win.document.write(`<!DOCTYPE html><html><head><meta charset="utf-8"><title>歌谱</title>
<style>@page{size:A4;margin:12mm}body{margin:0}svg{width:100%;height:auto}</style>
</head><body>${svg}<script>window.addEventListener('load',()=>setTimeout(()=>window.print(),400))<\/script>
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
  convertBtn.addEventListener('click', convert);
  keySelect.addEventListener('change', convert);
  pdfBtn.addEventListener('click', openPdf);
  downloadBtn.addEventListener('click', downloadXml);

  try {
    setStatus('正在加载转换引擎（Pyodide）…', 'loading');
    await initPyodide();
    osmd = new opensheetmusicdisplay.OpenSheetMusicDisplay('score', {
      autoResize: true,
      backend: 'svg',
      drawingParameters: 'compacttight',
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
