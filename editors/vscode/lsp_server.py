#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""极简 LSP server（纯标准库，JSON-RPC over stdio）for 简谱 DSL。

只实现诊断（parse + 拍数/调号检查）和基础补全。用 VSCode 的通用
languageclient 扩展即可对接，无需 pygls / pip 依赖。
"""
import json
import os
import sys

SERVER_ROOT = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(SERVER_ROOT))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from mpp import musicxml                      # noqa: E402
from mpp.diagnostics import as_diagnostic     # noqa: E402
from mpp.parser import parse_text             # noqa: E402

COMPLETION_KEYWORDS = [
    "Key:", "Time:", "Tempo:", "Title:", "Composer:", "Poet:",
    "H:", "L:", "H1:", "H2:",
]
CHORD_ROOTS = ["C", "D", "E", "F", "G", "A", "B",
               "C#", "F#", "Bb", "Eb", "Ab", "Db",
               "Am", "Em", "Bm", "F#m", "Cm", "Gm", "Dm"]


def _send(message: dict) -> None:
    body = json.dumps(message, ensure_ascii=False).encode("utf-8")
    sys.stdout.buffer.write(
        f"Content-Length: {len(body)}\r\n\r\n".encode("ascii") + body)
    sys.stdout.buffer.flush()


def _read_message():
    headers = {}
    while True:
        line = sys.stdin.buffer.readline()
        if not line:
            return None
        if line in (b"\r\n", b"\n"):
            break
        if b":" in line:
            key, value = line.decode("ascii").split(":", 1)
            headers[key.strip().lower()] = value.strip()
    length = int(headers.get("content-length", 0))
    if not length:
        return None
    return json.loads(sys.stdin.buffer.read(length).decode("utf-8"))


def _range(line: int, column: int, length: int = 1) -> dict:
    start = {"line": max(0, line - 1), "character": max(0, column - 1)}
    end = {"line": start["line"], "character": start["character"] + length}
    return {"start": start, "end": end}


def _diagnose(uri: str, text: str) -> None:
    diagnostics = []
    try:
        score = parse_text(text)
        musicxml.to_musicxml(score)
        for warning in score.warnings:
            diagnostics.append({
                "range": _range(1, 1),
                "severity": 2,
                "source": "jianpu",
                "message": warning,
            })
    except ValueError as exc:
        info = as_diagnostic(exc)
        message = info["message"]
        if getattr(exc, "suggestion", ""):
            message += f" (did you mean '{exc.suggestion}'?)"
        diagnostics.append({
            "range": _range(info["line"], info["column"]),
            "severity": 1,
            "source": "jianpu",
            "message": message,
        })
    _send({"jsonrpc": "2.0", "method": "textDocument/publishDiagnostics",
           "params": {"uri": uri, "diagnostics": diagnostics}})


def _completions(params: dict) -> list:
    position = params["position"]
    line = position["line"]
    character = position["character"]
    doc = DOCUMENTS.get(params["textDocument"]["uri"], "")
    lines = doc.splitlines()
    prefix = lines[line][:character] if line < len(lines) else ""

    if prefix.lstrip().startswith("["):
        fragment = prefix.strip()[1:]
        words = [f"[{root}]" for root in CHORD_ROOTS]
    elif prefix.lstrip().startswith("Key:"):
        fragment = prefix.strip()[4:]
        from mpp import lilypond, musicxml
        words = [k + ":" for k in tuple(musicxml.MAJOR_SCALES)
                 + tuple(lilypond.MINOR_TO_MAJOR)]
    elif not prefix.strip():
        fragment, words = "", COMPLETION_KEYWORDS
    else:
        return []
    return [{"label": w, "kind": 14} for w in words
            if w.lower().startswith(fragment.lower())]


DOCUMENTS = {}


def main() -> int:
    while True:
        message = _read_message()
        if message is None:
            return 0
        method = message.get("method")
        params = message.get("params") or {}
        msg_id = message.get("id")

        if method == "initialize":
            _send({"jsonrpc": "2.0", "id": msg_id, "result": {
                "capabilities": {
                    "textDocumentSync": 1,
                    "completionProvider": {"triggerCharacters": [":", "["]},
                },
                "serverInfo": {"name": "jianpu-lsp", "version": "1.0"},
            }})
        elif method == "initialized":
            continue
        elif method in ("textDocument/didOpen", "textDocument/didChange"):
            if method == "textDocument/didOpen":
                item = params["textDocument"]
                uri, text = item["uri"], item["text"]
            else:
                uri = params["textDocument"]["uri"]
                changes = params.get("contentChanges") or []
                text = changes[-1]["text"] if changes else DOCUMENTS.get(uri, "")
            DOCUMENTS[uri] = text
            _diagnose(uri, text)
        elif method == "textDocument/completion":
            _send({"jsonrpc": "2.0", "id": msg_id,
                   "result": _completions(params)})
        elif method == "shutdown":
            _send({"jsonrpc": "2.0", "id": msg_id, "result": None})
        elif method == "exit":
            return 0


if __name__ == "__main__":
    sys.exit(main())
