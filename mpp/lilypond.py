# -*- coding: utf-8 -*-
"""LilyPond backend."""
from .ir import Note, Score

MINOR_TO_MAJOR = {
    "Am": "C", "Em": "G", "Bm": "D", "F#m": "A", "C#m": "E", "G#m": "B",
    "D#m": "F#", "A#m": "C#", "Dm": "F", "Gm": "Bb", "Cm": "Eb", "Fm": "Ab",
    "Bbm": "Db", "Ebm": "Gb", "Abm": "Cb",
}

# (letter index 0=c..6=b, alteration)
SCALES = {
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

LETTERS = ["c", "d", "e", "f", "g", "a", "b"]


def is_minor_key(key: str) -> bool:
    return len(key) >= 2 and key.endswith("m") and key != "m"


def resolve_major_key(key: str) -> str:
    if not is_minor_key(key):
        return key
    try:
        return MINOR_TO_MAJOR[key]
    except KeyError:
        raise ValueError(f"Unknown minor key '{key}'")


def minor_degree_to_major(degree: int) -> int:
    m = degree + 5
    return m - 7 if m > 7 else m


def diatonic_scale(key: str):
    major = resolve_major_key(key)
    if major not in SCALES:
        raise ValueError(f"Unknown key '{key}'")
    return SCALES[major]


def pitch_to_lilypond(letter: int, alteration: int, octave_shift: int) -> str:
    base = LETTERS[letter]
    if alteration > 0:
        base += "is" * alteration
    elif alteration < 0:
        for _ in range(-alteration):
            base += "s" if base in ("e", "a") else "es"
    if octave_shift > 0:
        base += "'" * octave_shift
    elif octave_shift < 0:
        base += "," * (-octave_shift)
    return base


def duration_to_lilypond(note: Note):
    """Returns (lilypond duration string, needs tie)."""
    if note.dash_count == 0:
        s = str(note.base_duration)
        if note.dotted:
            s += "."
        return s, False

    if note.base_duration == 4 and not note.dotted:
        beats = 1 + note.dash_count
        merged = {1: "4", 2: "2", 3: "2.", 4: "1"}.get(beats)
        if merged:
            return merged, False

    s = str(note.base_duration)
    if note.dotted:
        s += "."
    return s, True


def chord_to_lilypond(chord: str, duration: str) -> str:
    if not chord:
        return "s" + duration
    letter = chord[0]
    i = 1
    if i < len(chord) and chord[i] in "#b":
        root = letter.lower()
        if chord[i] == "#":
            root += "is"
        else:
            if letter in "Ee":
                root = "es"
            elif letter in "Aa":
                root = "as"
            else:
                root += "es"
        i += 1
    else:
        root = letter.lower()
    quality = ""
    if i < len(chord):
        quality = ":" + chord[i:]
    return root + duration + quality


def key_signature_command(key: str) -> str:
    minor = is_minor_key(key)
    root = key[:-1] if minor else key
    return "\\key " + chord_to_lilypond(root, "") + (" \\minor" if minor else " \\major")


def time_signature_base(ts: str) -> str:
    return ts.split(",")[0] if ts else ""


def anacrusis_value(ts: str) -> str:
    return ts.split(",", 1)[1] if ts and "," in ts else ""


def hanzi_to_syllables(text: str) -> str:
    out = []
    need_space = False
    for ch in text:
        cp = ord(ch)
        is_hanzi = 0x3400 <= cp < 0xA700
        is_open_quote = cp in (0x2018, 0x201C, 0x300A)
        if need_space and (is_hanzi or is_open_quote):
            out.append(" ")
            need_space = False
        if is_hanzi:
            need_space = True
        if ch == "_":
            need_space = False
        else:
            out.append(ch)
    return "".join(out)


LETTER_ORDER = "CDEFGAB"
LETTER_SEMITONES = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def key_tonic(key: str):
    """('Bb' / 'F#m') -> (letter index, alteration)."""
    letter = key[0].upper()
    alter = 0
    if len(key) > 1 and key[1] in "#b":
        alter = 1 if key[1] == "#" else -1
    return LETTER_ORDER.index(letter), alter


def tonic_octave(key: str) -> int:
    """Octave of `1` — the tonic closest to middle C (Bb -> Bb3, C -> C4)."""
    letter, alter = key_tonic(key)
    pitch = 12 * 5 + LETTER_SEMITONES[LETTER_ORDER[letter]] + alter   # octave 4
    return 4 if abs(pitch - 60) < abs(pitch - 12 - 60) else 3


def octave_number(key: str, degree: int, octave_shift: int) -> int:
    """Scientific octave number (C4 = middle C) of a scale degree.

    Degrees are counted from the tonic, so `1 2 3 4 5 6 7` always ascends and
    `1` sits next to middle C (Bb major: Bb3 C4 D4 Eb4 F4 G4 A4, `1'` = Bb4).
    """
    letter, _ = key_tonic(key)
    pos = letter + (degree - 1) + 7 * octave_shift
    return tonic_octave(key) + pos // 7


def _melody_note(note: Note, key: str, scale, minor: bool) -> str:
    if note.is_rest:
        return "r"
    degree = note.scale_degree
    mapped = minor_degree_to_major(degree) if minor else degree
    letter, alter = scale[mapped - 1]
    pitch = pitch_to_lilypond(letter, alter + note.alteration, 0)
    marks = octave_number(key, degree, note.octave_shift) - 3   # c' == C4
    pitch += "'" * marks if marks > 0 else "," * (-marks)
    return pitch


def build_chord_buffer(score: Score) -> str:
    out = ["      \\chordmode {\n"]
    for i, measure in enumerate(score.measures):
        for note in measure.notes:
            dur, need_tie = duration_to_lilypond(note)
            out.append(chord_to_lilypond(note.chord, dur))
            if need_tie and note.dash_count > 0:
                for _ in range(note.dash_count):
                    out.append("~ " + chord_to_lilypond(note.chord, "4"))
            out.append(" ")
        if i + 1 < len(score.measures):
            out.append("|\n")
    out.append("\n      }")
    return "".join(out)


def build_melody_buffer(score: Score) -> str:
    scale = diatonic_scale(score.key)
    minor = is_minor_key(score.key)
    out = ["      \\new Voice = \"melody\" {\n"]
    out.append("      " + key_signature_command(score.key) + "\n")
    out.append("      \\time " + time_signature_base(score.time_signature) + "\n")
    ana = anacrusis_value(score.time_signature)
    if ana:
        out.append("      \\partial " + ana + "\n")

    for i, measure in enumerate(score.measures):
        for note in measure.notes:
            if note.is_rest:
                out.append("r")
            else:
                out.append(_melody_note(note, score.key, scale, minor))
            dur, need_tie = duration_to_lilypond(note)
            out.append(dur)
            if note.tie_to_next:
                out.append("~")
            if note.slur_begin:
                out.append("(")
            if note.slur_end:
                out.append(")")
            for word in note.after:
                out.append(" " + word)
            if need_tie and note.dash_count > 0:
                for _ in range(note.dash_count):
                    out.append("~")
                    out.append("r4" if note.is_rest else _melody_note(note, score.key, scale, minor) + "4")
            out.append(" ")
        if measure.end_bar:
            out.append(f' \\bar "{measure.end_bar}"')
        if i + 1 < len(score.measures):
            brk = " \\break" if score.measures[i + 1].break_before else ""
            out.append("|" + brk + "\n")

    out.append("\n      }\n")
    return "".join(out)


def build_lyrics_buffer(score: Score) -> str:
    if not score.lyrics:
        return ""
    from . import lyrics as lyr

    keys, table = lyr.build(score)
    total = len(lyr.sung_slots(score))

    out = []
    for i, key in enumerate(keys):
        out.append(f"    \\new Lyrics = \"lyrics{i + 1}\" {{\n")
        out.append("      \\lyricsto \"melody\" {\n")
        out.append("        \\override LyricText.self-alignment-X = #LEFT\n")
        if len(keys) > 1:
            out.append(f"        \\set stanza = #\"{key}.\"\n")
        words = []
        for idx in range(total):
            words.append(table[key].get(idx) or "\\skip 1")
        out.append("        " + " ".join(words) + "\n")
        out.append("      }\n")
        out.append("    }\n")
    return "".join(out)


def generate(score: Score) -> str:
    if not score.key:
        raise ValueError("No Key: declaration found")
    if not score.time_signature:
        raise ValueError("No Time: declaration found")

    melody = build_melody_buffer(score)
    chords = build_chord_buffer(score)
    lyrics = build_lyrics_buffer(score)

    has_chords = any(n.chord for m in score.measures for n in m.notes)

    out = ["\\version \"2.24.0\"\n\n"]

    if score.headers:
        out.append("\\header {\n")
        for name in sorted(score.headers):
            field = name.lower()
            out.append(f"  {field} = \"{score.headers[name]}\"\n")
        out.append("}\n\n")

    for block in score.lp_blocks:
        out.append(block + "\n\n")

    out.append("\\score {\n  <<\n")
    if has_chords:
        out.append("    \\new ChordNames {\n")
        out.append("      \\set chordChanges = ##t\n")
        out.append(chords + "\n")
        out.append("    }\n")
    out.append("    \\new Staff {\n")
    if score.tempo:
        out.append("      \\tempo " + score.tempo + "\n")
    out.append(melody + "\n")
    out.append("    }\n")
    out.append(lyrics)
    out.append("  >>\n  \\layout {}\n}\n")
    return "".join(out)
