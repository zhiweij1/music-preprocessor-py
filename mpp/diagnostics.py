# -*- coding: utf-8 -*-
"""共享的诊断辅助：错误定位渲染、编辑距离、did-you-mean。

CLI 与 VSCode LSP 都从这里取结构化信息，避免两边各写一套。
"""
from .ir import DslError

DECLARATIONS = (
    "Key", "Time", "Tempo", "Title", "Subtitle", "Subsubtitle",
    "Composer", "Poet", "Instrument", "Arranger", "Copyright",
)
KEYWORDS = DECLARATIONS + ("H", "L", "LP")


def edit_distance(a: str, b: str) -> int:
    """Levenshtein distance, with an early cut-off for speed."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1,
                           prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def did_you_mean(value: str, candidates, limit: int = 2) -> str:
    """Return the closest candidate within `limit` edits, or ''."""
    if not value:
        return ""
    best, best_distance = "", limit + 1
    for candidate in candidates:
        distance = edit_distance(value.lower(), candidate.lower())
        if distance < best_distance:
            best, best_distance = candidate, distance
    return best


def suggest_declaration(value: str) -> str:
    head = value.split(":", 1)[0]
    return did_you_mean(head, KEYWORDS)


def suggest_key(value: str) -> str:
    from . import lilypond, musicxml
    keys = tuple(musicxml.MAJOR_SCALES) + tuple(lilypond.MINOR_TO_MAJOR)
    hint = did_you_mean(value, keys, limit=2)
    return hint if hint and hint != value else ""


def explain_bad_token(raw: str):
    """Return (message, suggestion) for an unrecognised token."""
    if raw.startswith("[") and "]" not in raw:
        return (f"chord symbol is missing a closing ']' (got '{raw}')", "")
    if raw.upper().startswith("KEY:"):
        value = raw[4:]
        hint = suggest_key(value)
        return (f"unknown key name '{value}'", hint)
    head = raw.split(":", 1)[0]
    hint = did_you_mean(head, KEYWORDS)
    if hint:
        return (f"unrecognised token '{raw}'", hint + ":")
    return (f"unrecognised token '{raw}'", "")


def render_error(message: str, line: int = 0, column: int = 0,
                 source: str = "", suggestion: str = "") -> str:
    """Human-readable diagnostic with source line and caret."""
    if line:
        lines = source.splitlines()
        text = lines[line - 1] if 0 < line <= len(lines) else ""
        caret = " " * max(0, column - 1) + "^"
        out = (f"Line {line}, column {column}:\n"
               f"  {text}\n"
               f"  {caret}\n"
               f"  {message}")
    else:
        out = message
    if suggestion:
        out += f"\n  hint: did you mean '{suggestion}'?"
    return out


def as_diagnostic(exc: Exception):
    """Convert DslError / ValueError with position into a plain dict for LSP."""
    line = getattr(exc, "line", 0) or 0
    column = getattr(exc, "column", 0) or 0
    message = getattr(exc, "message", None) or str(exc).split("\n")[0]
    suggestion = getattr(exc, "suggestion", "") or ""
    if suggestion:
        message += f" (did you mean '{suggestion}'?)"
    return {"line": line, "column": column, "message": message}
