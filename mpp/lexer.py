# -*- coding: utf-8 -*-
"""Tokenizer for the 简谱 DSL."""
from dataclasses import dataclass, field
from enum import Enum, auto
import re


class T(Enum):
    KEY = auto()
    TIME = auto()
    TEMPO = auto()
    NOTE = auto()
    DASH = auto()
    TIE = auto()
    SLUR_BEGIN = auto()
    SLUR_END = auto()
    BARLINE = auto()
    BARLINE_DOUBLE = auto()
    CHORD = auto()
    REPEAT_BEGIN = auto()
    REPEAT_END = auto()
    ALT_BEGIN = auto()
    LYRIC_HANZI = auto()
    LYRIC_LATIN = auto()
    LILY_WORD = auto()
    LP_BLOCK = auto()
    META = auto()
    ERROR = auto()
    EOF = auto()


@dataclass
class Token:
    type: T
    value: str
    line: int = 0
    verse: str = ""
    column: int = 0


META_NAMES = (
    "Title:", "Subtitle:", "Subsubtitle:",
    "Composer:", "Poet:", "Instrument:", "Arranger:", "Copyright:",
)

NOTE_CHARS = set("qQsSdDcChH#b0123456789xX',.")


def _meta_prefix_len(raw: str) -> int:
    for name in META_NAMES:
        if raw.startswith(name):
            return len(name)
    return 0


def is_note_token(raw: str) -> bool:
    if not raw:
        return False
    core = raw
    if core.startswith("("):          # slur marker written in front of the note
        core = core[1:]
    if core.endswith(")"):            # slur marker written after the note
        core = core[:-1]
    if not core:
        return False
    if not any(ch.isdigit() or ch in "xX" for ch in core):
        return False
    return all(ch in NOTE_CHARS for ch in core)


def classify(raw: str) -> Token:
    if raw.startswith("Key:") and len(raw) > 4:
        return Token(T.KEY, raw[4:])
    if raw.startswith("Time:") and len(raw) > 5:
        return Token(T.TIME, raw[5:])
    if raw.startswith("Tempo:") and len(raw) > 6:
        return Token(T.TEMPO, raw[6:])

    if _meta_prefix_len(raw) and len(raw) > _meta_prefix_len(raw):
        return Token(T.META, raw)

    if raw == "|":
        return Token(T.BARLINE, raw)
    if raw in ("||", "|.", ".|", "|:", ":|"):
        return Token(T.BARLINE_DOUBLE, raw)
    if raw == "-":
        return Token(T.DASH, raw)
    if raw == "~":
        return Token(T.TIE, raw)
    if raw == "(":
        return Token(T.SLUR_BEGIN, raw)
    if raw == ")":
        return Token(T.SLUR_END, raw)

    if len(raw) >= 3 and raw[0] == "[" and raw[-1] == "]":
        return Token(T.CHORD, raw[1:-1])

    if raw in ("R{", "r{"):
        return Token(T.REPEAT_BEGIN, raw)
    if raw == "}":
        return Token(T.REPEAT_END, raw)
    if raw in ("A{", "a{"):
        return Token(T.ALT_BEGIN, raw)

    if len(raw) >= 2:
        if raw[0] == "H" and raw[1] == ":":
            return Token(T.LYRIC_HANZI, raw[2:])
        if raw[0] == "L" and raw[1] == ":":
            return Token(T.LYRIC_LATIN, raw[2:])

    if raw[0] in "\\^_\"":
        return Token(T.LILY_WORD, raw)

    if raw == "LP:":
        return Token(T.LP_BLOCK, raw)

    if is_note_token(raw):
        return Token(T.NOTE, raw)

    return Token(T.ERROR, raw)


LYRIC_MARK = re.compile(r"([HL])(\d*):")


def split_lyric_line(raw: str):
    """'H:abc H2:def' -> [('', 'abc', True), ('2', 'def', True)]."""
    matches = list(LYRIC_MARK.finditer(raw))
    out = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(raw)
        out.append((m.group(2), raw[m.end():end].strip(), m.group(1) == "H"))
    return out


def tokenize(source: str) -> list:
    tokens = []
    pos = 0
    line = 1
    line_start = 0
    n = len(source)

    while pos < n:
        # skip whitespace
        while pos < n and source[pos].isspace():
            if source[pos] == "\n":
                line += 1
                line_start = pos + 1
            pos += 1
        if pos >= n:
            break

        # comment to end of line
        if source[pos] == "%":
            while pos < n and source[pos] != "\n":
                pos += 1
            continue

        start = pos
        while pos < n and not source[pos].isspace():
            pos += 1
        raw = source[start:pos]

        # lyric lines swallow the rest of the line (and may hold several
        # "H1:" / "H2:" markers inline)
        if LYRIC_MARK.match(raw):
            rest = pos
            while pos < n and source[pos] != "\n":
                pos += 1
            tail = source[rest:pos]
            if tail.endswith("\r"):
                tail = tail[:-1]
            raw += tail
            for verse, text, hanzi in split_lyric_line(raw):
                tok = Token(T.LYRIC_HANZI if hanzi else T.LYRIC_LATIN, text, line,
                            column=start - line_start + 1)
                tok.verse = verse
                tokens.append(tok)
            continue

        # metadata declarations swallow the rest of the line
        if _meta_prefix_len(raw):
            rest = pos
            while pos < n and source[pos] != "\n":
                pos += 1
            tail = source[rest:pos]
            if tail.endswith("\r"):
                tail = tail[:-1]
            raw += tail

        tok = classify(raw)
        tok.line = line
        tok.column = start - line_start + 1
        tokens.append(tok)

    tokens.append(Token(T.EOF, "", line))
    return tokens
