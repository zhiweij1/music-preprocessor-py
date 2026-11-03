# -*- coding: utf-8 -*-
"""Recursive-descent parser: tokens -> Score IR (port of the C++ Parser)."""
from .ir import LyricsLine, Measure, Note, Score
from .lexer import T, Token


class DslError(Exception):
    pass


def _trim(text: str) -> str:
    return text.strip()


class Parser:
    def __init__(self, tokens: list):
        self.tokens = tokens
        self.pos = 0
        self.pending_chord = ""
        self.last_note_line = None
        self.last_lyric_line = None
        self.note_count = 0

    # -- helpers ---------------------------------------------------------
    def current(self) -> Token:
        return self.tokens[self.pos]

    def at_end(self) -> bool:
        return self.pos >= len(self.tokens)

    def advance(self) -> Token:
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    # -- public ----------------------------------------------------------
    def parse(self) -> Score:
        score = Score()
        measure = Measure()

        def flush():
            nonlocal measure
            if measure.notes:
                score.measures.append(measure)
                measure = Measure()

        while not self.at_end():
            tok = self.current()

            if tok.type == T.KEY:
                self.advance()
                score.key = tok.value
            elif tok.type == T.TIME:
                self.advance()
                score.time_signature = tok.value
            elif tok.type == T.TEMPO:
                self.advance()
                score.tempo = tok.value
            elif tok.type == T.CHORD:
                self.advance()
                self.pending_chord = tok.value
            elif tok.type == T.NOTE:
                self.advance()
                note = self.parse_note_token(tok.value)
                note.chord = self.pending_chord
                self.pending_chord = ""
                # a new source line starts a new system
                if (not measure.notes and self.last_note_line is not None
                        and tok.line != self.last_note_line):
                    measure.break_before = True
                note.line = tok.line
                measure.notes.append(note)
                self.last_note_line = tok.line
                if not note.is_rest:
                    self.note_count += 1
            elif tok.type == T.DASH:
                self.advance()
                if not measure.notes:
                    raise DslError(f"Line {tok.line}: '-' dash must follow a note")
                measure.notes[-1].dash_count += 1
            elif tok.type in (T.TIE, T.SLUR_BEGIN, T.SLUR_END):
                self.advance()
                if not measure.notes:
                    raise DslError(f"Line {tok.line}: '{tok.value}' must follow a note")
                last = measure.notes[-1]
                if tok.type == T.TIE:
                    last.tie_to_next = True
                elif tok.type == T.SLUR_BEGIN:
                    last.slur_begin = True
                else:
                    last.slur_end = True
            elif tok.type in (T.BARLINE, T.BARLINE_DOUBLE):
                self.advance()
                if measure.notes:
                    measure.end_bar = tok.value if tok.type == T.BARLINE_DOUBLE else ""
                flush()
            elif tok.type in (T.REPEAT_BEGIN, T.REPEAT_END, T.ALT_BEGIN):
                raise DslError(
                    f"Line {tok.line}: repeat/alternate notation not yet supported (Phase 2)")
            elif tok.type in (T.LYRIC_HANZI, T.LYRIC_LATIN):
                self.advance()
                inline = (tok.line == self.last_lyric_line)
                line = LyricsLine(verse=tok.verse, text=_trim(tok.value),
                                  hanzi=(tok.type == T.LYRIC_HANZI),
                                  start=self.note_count, line=tok.line,
                                  inline=inline)
                self.last_lyric_line = tok.line
                text = line.text
                if not line.verse and len(text) >= 2 and text[0] in "123456789":
                    if text[1] == ".":
                        line.verse, line.text = text[0], text[2:].strip()
                    elif len(text) >= 4 and text[1:4] == "\uFF0E":   # fullwidth full stop
                        line.verse, line.text = text[0], text[4:].strip()
                score.lyrics.append(line)
            elif tok.type == T.LILY_WORD:
                self.advance()
                if not measure.notes:
                    raise DslError(f"Line {tok.line}: '{tok.value}' must follow a note")
                measure.notes[-1].after.append(tok.value)
            elif tok.type == T.LP_BLOCK:
                self.advance()
                block = []
                while not self.at_end():
                    t = self.current()
                    if t.value == ":LP":
                        self.advance()
                        break
                    block.append(t.value)
                    self.advance()
                if block:
                    score.lp_blocks.append(" ".join(block))
            elif tok.type == T.META:
                self.advance()
                name, sep, value = tok.value.partition(":")
                if sep:
                    score.headers[name] = _trim(value)
            elif tok.type == T.EOF:
                break
            elif tok.type == T.ERROR:
                raise DslError(f"Line {tok.line}: unrecognised token '{tok.value}'")
            else:  # pragma: no cover
                raise DslError(f"Line {tok.line}: unexpected token '{tok.value}'")

        flush()
        return score

    # -- note token ------------------------------------------------------
    @staticmethod
    def parse_note_token(raw: str) -> Note:
        note = Note()
        token = raw
        if token.startswith("("):        # "(2" == slur starts on this note
            note.slur_begin = True
            token = token[1:]
        if token.endswith(")"):          # "2)" == slur ends on this note
            note.slur_end = True
            token = token[:-1]
        i = 0
        if i < len(token) and token[i] in "qQsSdDcChH":
            note.base_duration = {"q": 8, "s": 16, "d": 32, "h": 64, "c": 4}[token[i].lower()]
            i += 1
        if i < len(token) and token[i] in "#b":
            note.alteration = 1 if token[i] == "#" else -1
            i += 1
        if i >= len(token):
            raise DslError(f"Malformed note token '{raw}': missing pitch digit")
        digit = token[i]
        if digit in "xX":
            note.scale_degree = 0
        elif digit == "8":
            note.scale_degree, note.octave_shift = 1, 1
        elif digit == "9":
            note.scale_degree, note.octave_shift = 2, 1
        elif digit in "01234567":
            note.scale_degree = int(digit)
        else:
            raise DslError(f"Malformed note token '{raw}': expected digit at position {i}")
        i += 1
        while i < len(token) and token[i] in "',":
            note.octave_shift += 1 if token[i] == "'" else -1
            i += 1
        if i < len(token) and token[i] == ".":
            note.dotted = True
            i += 1
        if i != len(token):
            raise DslError(
                f"Malformed note token '{raw}': unexpected character '{token[i]}'")
        if note.is_rest:
            note.alteration = 0
        return note


def parse_text(text: str) -> Score:
    from .lexer import tokenize
    return Parser(tokenize(text)).parse()
