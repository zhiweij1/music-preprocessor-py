# -*- coding: utf-8 -*-
"""LSP server 冒烟测试：直接走 stdio JSON-RPC，不依赖任何第三方库。"""
import json
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SERVER = os.path.join(ROOT, "editors", "vscode", "lsp_server.py")


def frame(message: dict) -> bytes:
    body = json.dumps(message).encode("utf-8")
    return f"Content-Length: {len(body)}\r\n\r\n".encode("ascii") + body


def read_reply(proc):
    headers = {}
    while True:
        line = proc.stdout.readline()
        if not line:
            return None
        if line in (b"\r\n", b"\n"):
            break
        key, _, value = line.decode("ascii").partition(":")
        headers[key.strip().lower()] = value.strip()
    length = int(headers.get("content-length", 0))
    return json.loads(proc.stdout.read(length).decode("utf-8"))


class TestLsp(unittest.TestCase):
    def test_diagnostics_and_completion(self):
        messages = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "method": "initialized", "params": {}},
            {"jsonrpc": "2.0", "method": "textDocument/didOpen", "params": {
                "textDocument": {"uri": "file:///song.dsl",
                                 "text": "Key:C Tiem:4/4\n1 2 3 4 |\n"}}},
            {"jsonrpc": "2.0", "id": 2, "method": "textDocument/completion",
             "params": {"textDocument": {"uri": "file:///song.dsl"},
                        "position": {"line": 1, "character": 0}}},
            {"jsonrpc": "2.0", "id": 3, "method": "shutdown", "params": {}},
            {"jsonrpc": "2.0", "method": "exit", "params": {}},
        ]
        payload = b"".join(frame(m) for m in messages)
        proc = subprocess.run([sys.executable, SERVER], input=payload,
                              capture_output=True, timeout=30)
        self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8", "replace"))
        text = proc.stdout.decode("utf-8")
        self.assertIn("did you mean 'Time:'", text)
        self.assertIn('"severity": 1', text)
        self.assertIn('"label": "Key:"', text)


if __name__ == "__main__":
    unittest.main()
