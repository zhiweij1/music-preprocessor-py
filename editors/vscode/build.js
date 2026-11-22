// Bundle extension.js (and its npm deps) into dist/extension.js, then copy the
// Python LSP server and the mpp modules into dist/ so the extension is
// self-contained (`path.join(__dirname, 'lsp_server.py')`, `dist/mpp`).
const fs = require('fs');
const path = require('path');
const esbuild = require('esbuild');

const root = __dirname;
const repoRoot = path.dirname(path.dirname(root));
const dist = path.join(root, 'dist');
fs.mkdirSync(dist, { recursive: true });

esbuild.buildSync({
  entryPoints: [path.join(root, 'extension.js')],
  bundle: true,
  platform: 'node',
  format: 'cjs',
  target: 'node20',
  external: ['vscode'],
  minify: true,
  outfile: path.join(dist, 'extension.js'),
});

fs.copyFileSync(path.join(root, 'lsp_server.py'), path.join(dist, 'lsp_server.py'));

// Only the modules the LSP server needs (mirrors web/sync_mpp.py).
const MODULES = [
  '__init__.py', 'ir.py', 'lexer.py', 'parser.py', 'lyrics.py',
  'lilypond.py', 'musicxml.py', 'transpose.py', 'diagnostics.py',
];
const destMpp = path.join(dist, 'mpp');
fs.mkdirSync(destMpp, { recursive: true });
for (const name of MODULES) {
  fs.copyFileSync(path.join(repoRoot, 'mpp', name), path.join(destMpp, name));
}

console.log('Built dist/extension.js, dist/lsp_server.py and dist/mpp/');
