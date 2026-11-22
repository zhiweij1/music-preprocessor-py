# -*- coding: utf-8 -*-
"""MusicXML backend: DSL score -> MusicXML 4.0 (lead-sheet layout).

MuseScore imports this format natively, so the CLI can turn it into .mscz/.pdf.
"""
import re
from fractions import Fraction

from .ir import Note, Score
from . import lyrics

DIVISIONS = 384           # ticks per quarter note (64th = 6, dotted 64th = 9)
WHOLE = 4                 # quarter beats in a whole note

LETTER_SEMITONES = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}

MAJOR_SCALES = {
    "C":  [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (5, 0), (6, 0)],
    "G":  [(4, 0), (5, 0), (6, 0), (0, 0), (1, 0), (2, 0), (3, 1)],
    "D":  [(1, 0), (2, 0), (3, 1), (4, 0), (5, 0), (6, 0), (0, 1)],
    "A":  [(5, 0), (6, 0), (0, 1), (1, 0), (2, 0), (3, 1), (4, 1)],
    "E":  [(2, 0), (3, 1), (4, 1), (5, 0), (6, 0), (0, 1), (1, 1)],
    "B":  [(6, 0), (0, 1), (1, 1), (2, 0), (3, 1), (4, 1), (5, 1)],
    "F#": [(3, 1), (4, 1), (5, 1), (6, 0), (0, 1), (1, 1), (2, 1)],
    "C#": [(0, 1), (1, 1), (2, 1), (3, 1), (4, 1), (5, 1), (6, 1)],
    "F":  [(3, 0), (4, 0), (5, 0), (6, -1), (0, 0), (1, 0), (2, 0)],
    "Bb": [(6, -1), (0, 0), (1, 0), (2, -1), (3, 0), (4, 0), (5, 0)],
    "Eb": [(2, -1), (3, 0), (4, 0), (5, -1), (6, -1), (0, 0), (1, 0)],
    "Ab": [(5, -1), (6, -1), (0, 0), (1, -1), (2, -1), (3, 0), (4, 0)],
    "Db": [(1, -1), (2, -1), (3, 0), (4, -1), (5, -1), (6, -1), (0, 0)],
    "Gb": [(4, -1), (5, -1), (6, -1), (0, -1), (1, -1), (2, -1), (3, 0)],
    "Cb": [(0, -1), (1, -1), (2, -1), (3, -1), (4, -1), (5, -1), (6, -1)],
}

FIFTHS = {"C": 0, "G": 1, "D": 2, "A": 3, "E": 4, "B": 5, "F#": 6, "C#": 7,
          "F": -1, "Bb": -2, "Eb": -3, "Ab": -4, "Db": -5, "Gb": -6, "Cb": -7}

# (beats, type, dots) from longest to shortest
NOTE_VALUES = [
    (Fraction(4), "whole", 0), (Fraction(3), "half", 1),
    (Fraction(2), "half", 0), (Fraction(3, 2), "quarter", 1),
    (Fraction(1), "quarter", 0), (Fraction(3, 4), "eighth", 1),
    (Fraction(1, 2), "eighth", 0), (Fraction(3, 8), "16th", 1),
    (Fraction(1, 4), "16th", 0), (Fraction(3, 16), "32nd", 1),
    (Fraction(1, 8), "32nd", 0), (Fraction(3, 32), "64th", 1),
    (Fraction(1, 16), "64th", 0),
]

# MusicXML <bar-style> for the bar tokens the DSL understands
BARLINE_STYLES = {
    "||": "light-light",
    "|.": "light-heavy",
    ".|": "heavy-light",
    "|:": "heavy-light",
    ":|": "light-heavy",
    ":|:": "light-light",
}


def esc(text: str) -> str:
    return (str(text).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def is_minor_key(key: str) -> bool:
    return len(key) >= 2 and key.endswith("m") and key != "m"


def key_info(key: str):
    """Return (fifths, mode, scale)."""
    from .lilypond import MINOR_TO_MAJOR
    if is_minor_key(key):
        major = MINOR_TO_MAJOR.get(key)
        if major is None:
            raise ValueError(f"Unknown minor key '{key}'")
        mode = "minor"
    else:
        major, mode = key, "major"
    if major not in MAJOR_SCALES:
        raise ValueError(f"Unknown key '{key}'")
    return FIFTHS[major], mode, MAJOR_SCALES[major]


def note_beats(note: Note) -> Fraction:
    base = Fraction(WHOLE, note.base_duration)
    if note.dotted:
        base *= Fraction(3, 2)
    return base + Fraction(note.dash_count)


def split_duration(total: Fraction):
    """Greedy split of a duration into notatable values."""
    parts = []
    remaining = total
    guard = 0
    while remaining > 0:
        for beats, typ, dots in NOTE_VALUES:
            if beats <= remaining:
                parts.append((beats, typ, dots))
                remaining -= beats
                break
        else:
            raise ValueError(f"cannot notate duration {total}")
        guard += 1
        if guard > 64:
            raise ValueError(f"cannot notate duration {total}")
    return parts


def parse_chord_symbol(text: str):
    """'F#m7b5/A' -> ('F', 1, 'm7b5', 'A', 0); 'C6/9' -> ('C', 0, '6/9', None, None)."""
    root, bass = text, ""
    if "/" in text:
        head, _, tail = text.rpartition("/")
        if re.fullmatch(r"[A-Ga-g][#b]?", tail):
            root, bass = head, tail
    m = re.match(r"^([A-Ga-g])([#b]?)(.*)$", root)
    if not m:
        return None
    letter, acc, suffix = m.group(1).upper(), m.group(2), m.group(3)
    bass_letter = bass_alt = None
    if bass:
        bm = re.match(r"^([A-Ga-g])([#b]?)", bass)
        if bm:
            bass_letter, bass_alt = bm.group(1).upper(), bm.group(2)
    return letter, {"": 0, "#": 1, "b": -1}[acc], suffix, bass_letter, bass_alt


def harmony_xml(text: str) -> str:
    parsed = parse_chord_symbol(text)
    if parsed is None:
        return ""
    letter, alter, suffix, bass_letter, bass_alter = parsed
    root_alter = f"<root-alter>{alter}</root-alter>" if alter else ""
    if suffix:
        kind = f'<kind text="{esc(suffix)}">other</kind>'
    else:
        kind = "<kind>major</kind>"
    bass = ""
    if bass_letter:
        if bass_alter == "#":
            ba = "<bass-alter>1</bass-alter>"
        elif bass_alter == "b":
            ba = "<bass-alter>-1</bass-alter>"
        else:
            ba = ""
        bass = f"<bass><bass-step>{bass_letter}</bass-step>{ba}</bass>"
    return (f"<harmony><root><root-step>{letter}</root-step>{root_alter}</root>"
            f"{kind}{bass}</harmony>")


def to_musicxml(score: Score, auto_break: bool = False) -> str:
    if not score.key:
        raise ValueError("No Key: declaration found")
    if not score.time_signature:
        raise ValueError("No Time: declaration found")

    try:
        fifths, mode, scale = key_info(score.key)
    except ValueError as exc:
        from .diagnostics import suggest_key
        from .ir import DslError
        hint = suggest_key(score.key)
        raise DslError(exc.args[0], score.key_line, score.key_column,
                       score.source, hint) from exc
    minor = is_minor_key(score.key)
    from .lilypond import minor_degree_to_major, octave_number

    for block in score.lp_blocks:
        score.warn(f"ignored raw LilyPond block '{block[:40]}' (no MusicXML equivalent)")

    time_parts = score.time_signature.split(",")
    beats, beat_type = time_parts[0].split("/")
    anacrusis = time_parts[1] if len(time_parts) > 1 else ""
    expected = Fraction(int(beats) * 4, int(beat_type))
    # the anacrusis value is a note-value denominator: 4 = quarter, 8 = eighth
    pickup_expected = Fraction(4, int(anacrusis)) if anacrusis.isdigit() else None

    total_notes = sum(1 for m in score.measures for n in m.notes if not n.is_rest)
    verse_keys, verse_map = lyrics.build(score)

    out = []
    A = out.append
    A('<?xml version="1.0" encoding="UTF-8"?>')
    A('<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 4.0 Partwise//EN" '
      '"http://www.musicxml.org/dtds/partwise.dtd">')
    A('<score-partwise version="4.0">')
    if "Title" in score.headers:
        A(f'<work><work-title>{esc(score.headers["Title"])}</work-title></work>')
    A('<identification>')
    if "Composer" in score.headers:
        A(f'<creator type="composer">{esc(score.headers["Composer"])}</creator>')
    if "Poet" in score.headers:
        A(f'<creator type="lyricist">{esc(score.headers["Poet"])}</creator>')
    A('<encoding><software>music-preprocessor (python)</software></encoding>')
    A('</identification>')
    A('<defaults><scaling><millimeters>7</millimeters><tenths>40</tenths></scaling>'
      '<page-layout><page-height>1683.78</page-height><page-width>1190.55</page-width>'
      '<page-margins type="both"><left-margin>85</left-margin><right-margin>85</right-margin>'
      '<top-margin>85</top-margin><bottom-margin>85</bottom-margin></page-margins>'
      '</page-layout></defaults>')

    # title block
    # MuseScore derives the title frame (VBox) height from these credit font
    # sizes; the actual glyph sizes come from the .mss style. Smaller numbers
    # tighten the gap between the title block and the first staff without
    # shrinking the printed text.
    y = 1600
    subtitles = [score.headers[k] for k in ("Subtitle", "Subsubtitle") if k in score.headers]
    if "Title" in score.headers:
        A(f'<credit page="1"><credit-type>title</credit-type>'
          f'<credit-words default-x="595" default-y="{y}" justify="center" valign="top" '
          f'font-size="14">{esc(score.headers["Title"])}</credit-words></credit>')
        y -= 48
    if subtitles:
        A(f'<credit page="1"><credit-type>subtitle</credit-type>'
          f'<credit-words default-x="595" default-y="{y}" justify="center" valign="top" '
          f'font-size="11">{esc(" · ".join(subtitles))}</credit-words></credit>')
    if "Composer" in score.headers:
        A(f'<credit page="1"><credit-type>composer</credit-type>'
          f'<credit-words default-x="1050" default-y="1470" justify="right" valign="top" '
          f'font-size="9">{esc(score.headers["Composer"])}</credit-words></credit>')
    if "Poet" in score.headers:
        A(f'<credit page="1"><credit-type>lyricist</credit-type>'
          f'<credit-words default-x="140" default-y="1470" justify="left" valign="top" '
          f'font-size="9">{esc(score.headers["Poet"])}</credit-words></credit>')

    A('<part-list><score-part id="P1"><part-name></part-name>'
      '<score-instrument id="P1-I1"><instrument-name>Voice</instrument-name></score-instrument>'
      '<midi-instrument id="P1-I1"><midi-channel>1</midi-channel>'
      '<midi-program>54</midi-program></midi-instrument></score-part></part-list>')
    A('<part id="P1">')

    pending_tie = False
    slur_open = False
    pending_break = False
    pending_bar_style = None
    note_index = 0

    for mi, measure in enumerate(score.measures):
        is_pickup = (mi == 0 and anacrusis)
        number = 0 if is_pickup else mi + 1
        attrs = ' implicit="yes"' if is_pickup else ""
        A(f'<measure number="{number}"{attrs}>')
        if not auto_break and (mi == 0 or pending_break or measure.break_before):
            A('<print new-system="yes"/>')
        pending_break = False

        measure_beats = sum((note_beats(n) for n in measure.notes), Fraction(0))
        want = pickup_expected if is_pickup else expected
        if want is not None and measure_beats != want:
            score.warn(f"measure {mi + 1}: {float(measure_beats):g} beats, expected {float(want):g}")

        if mi == 0:
            A(f'<attributes><divisions>{DIVISIONS}</divisions>'
              f'<key><fifths>{fifths}</fifths><mode>{mode}</mode></key>'
              f'<time><beats>{beats}</beats><beat-type>{beat_type}</beat-type></time>'
              '<clef><sign>G</sign><line>2</line></clef></attributes>')
            if score.tempo:
                m = re.match(r"([1-8])=(\d+)", score.tempo)
                if m:
                    unit = {"1": "whole", "2": "half", "4": "quarter",
                            "8": "eighth"}.get(m.group(1), "quarter")
                    A(f'<direction placement="above"><direction-type><metronome>'
                      f'<beat-unit>{unit}</beat-unit><per-minute>{m.group(2)}</per-minute>'
                      f'</metronome></direction-type><sound tempo="{m.group(2)}"/></direction>')
                else:
                    score.warn(f"unsupported tempo '{score.tempo}'")

        for note in measure.notes:
            tie_in = pending_tie
            # -- verbatim marks attached to this note (rendered above it)
            words = note.after
            wi = 0
            while wi < len(words):
                word = words[wi]
                if word == "\\bar" and wi + 1 < len(words) and words[wi + 1].startswith('"'):
                    # the lexer yields "\bar" and "|." as two tokens
                    pending_bar_style = BARLINE_STYLES.get(words[wi + 1].strip('"'))
                    if pending_bar_style is None:
                        score.warn(f"unsupported barline \\bar {words[wi + 1]}")
                    wi += 2
                    continue
                if word == "\\break":
                    pending_break = True
                elif re.fullmatch(r'\\bar\s+"(.*)"', word):
                    style = BARLINE_STYLES.get(re.fullmatch(r'\\bar\s+"(.*)"', word).group(1))
                    if style:
                        pending_bar_style = style
                    else:
                        score.warn(f"unsupported barline {word}")
                elif re.match(r'[\^_]"', word):
                    placement = "above" if word[0] == "^" else "below"
                    text = word[2:-1]
                    A(f'<direction placement="{placement}"><direction-type>'
                      f'<words>{esc(text)}</words></direction-type></direction>')
                else:
                    score.warn(f"ignored LilyPond token '{word}' (no MusicXML equivalent)")
                wi += 1

            if note.chord:
                A(harmony_xml(note.chord))

            segments = split_duration(note_beats(note))
            for si, (length, typ, dots) in enumerate(segments):
                duration = int(length * DIVISIONS)
                tie_start = (si < len(segments) - 1 or note.tie_to_next) and not note.is_rest
                tie_stop = (si > 0 or pending_tie) and not note.is_rest
                A('<note>')
                if note.is_rest:
                    A('<rest/>')
                else:
                    degree = note.scale_degree
                    mapped = minor_degree_to_major(degree) if minor else degree
                    letter_index, alter = scale[mapped - 1]
                    alter += note.alteration
                    octave = octave_number(score.key, degree, note.octave_shift)
                    step = "CDEFGAB"[letter_index]
                    A(f'<pitch><step>{step}</step>'
                      + (f'<alter>{alter}</alter>' if alter else "")
                      + f'<octave>{octave}</octave></pitch>')
                A(f'<duration>{duration}</duration>')
                if tie_stop:
                    A('<tie type="stop"/>')
                if tie_start:
                    A('<tie type="start"/>')
                A('<voice>1</voice>')
                A(f'<type>{typ}</type>')
                for _ in range(dots):
                    A('<dot/>')
                if si == 0 and not note.is_rest and not tie_in and verse_keys:
                    for key in verse_keys:
                        syl = verse_map[key].get(note_index)
                        if syl is None:
                            continue
                        A(f'<lyric number="{key}"><syllabic>single</syllabic>'
                          f'<text>{esc(syl)}</text></lyric>')
                notations = []
                if tie_stop:
                    notations.append('<tied type="stop"/>')
                if tie_start:
                    notations.append('<tied type="start"/>')
                if note.slur_begin and si == 0:
                    notations.append('<slur type="start" number="1"/>')
                if note.slur_end and si == len(segments) - 1:
                    notations.append('<slur type="stop" number="1"/>')
                if notations:
                    A('<notations>' + "".join(notations) + '</notations>')
                A('</note>')

            pending_tie = note.tie_to_next and not note.is_rest
            if note.slur_begin:
                slur_open = True
            if note.slur_end:
                slur_open = False
            if not note.is_rest and not tie_in:
                note_index += 1

        bar_style = BARLINE_STYLES.get(measure.end_bar) or pending_bar_style
        if bar_style:
            A(f'<barline location="right"><bar-style>{bar_style}</bar-style>'
              '</barline>')
            pending_bar_style = None
        if mi == len(score.measures) - 1 and not bar_style:
            A('<barline location="right"><bar-style>light-heavy</bar-style></barline>')
        A('</measure>')

    A('</part></score-partwise>')
    return "\n".join(out)
