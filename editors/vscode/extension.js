const path = require('path');
const vscode = require('vscode');
const { LanguageClient, TransportKind } = require('vscode-languageclient/node');

let client;

function activate(context) {
  const config = vscode.workspace.getConfiguration('jianpu');
  const python = config.get('pythonPath') || 'python';
  const server = path.join(__dirname, 'lsp_server.py');
  const serverOptions = {
    command: python,
    args: [server],
    transport: TransportKind.stdio,
  };
  const clientOptions = {
    documentSelector: [{ scheme: 'file', language: 'jianpu' }],
    synchronize: { fileEvents: vscode.workspace.createFileSystemWatcher('**/*.dsl') },
  };
  client = new LanguageClient('jianpu', '简谱 DSL', serverOptions, clientOptions);
  client.start();
}

function deactivate() {
  return client ? client.stop() : undefined;
}

module.exports = { activate, deactivate };
