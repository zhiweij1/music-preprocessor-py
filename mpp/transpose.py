# -*- coding: utf-8 -*-
"""首调简谱的移调（transposition）。

简谱音级 1-7 是首调唱名，转调只需换调号（音级不变，实际音高随调号改变）。
和弦记号是绝对音名，必须按新旧主音之间的半音差整体平移，并按新调重新拼写。
"""
from . import lilypond, musicxml
from .ir import Score

LETTERS = "CDEFGAB"
SEMITONES = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}

# 调外音的兜底拼写：升号倾向 / 降号倾向（pc -> (letter, alter)）
_SHARP = {0: ("C", 0), 1: ("C", 1), 2: ("D", 0), 3: ("D", 1),
          4: ("E", 0), 5: ("F", 0), 6: ("F", 1), 7: ("G", 0),
          8: ("G", 1), 9: ("A", 0), 10: ("A", 1), 11: ("B", 0)}
_FLAT = {0: ("C", 0), 1: ("D", -1), 2: ("D", 0), 3: ("E", -1),
         4: ("E", 0), 5: ("F", 0), 6: ("G", -1), 7: ("G", 0),
         8: ("A", -1), 9: ("A", 0), 10: ("B", -1), 11: ("B", 0)}


def tonic_pc(key: str) -> int:
    """调名的主音音高类：0=C, 1=C#/Db, ..., 11=B。"""
    root = key[:-1] if lilypond.is_minor_key(key) else key
    letter, alter = lilypond.key_tonic(root)
    return (SEMITONES[LETTERS[letter]] + alter) % 12


def _diatonic_spellings(key: str) -> dict:
    """新调音阶内音的拼写：pc -> (letter, alter)；小调用关系大调音阶。"""
    table = {}
    for letter_index, alter in lilypond.diatonic_scale(key):
        letter = LETTERS[letter_index]
        table[(SEMITONES[letter] + alter) % 12] = (letter, alter)
    return table


def spell(pc: int, key: str) -> str:
    """把音高类拼成新调下最合适的音名（C# 调 pc6=F#，Db 调 pc6=Gb）。"""
    table = _diatonic_spellings(key)
    if pc in table:
        letter, alter = table[pc]
    else:
        fifths, _, _ = musicxml.key_info(key)
        letter, alter = (_SHARP if fifths >= 0 else _FLAT)[pc]
    return letter + ("#" * alter if alter > 0 else "b" * -alter)


def transpose_chord(chord: str, shift: int, key: str) -> str:
    """和弦根音与低音按 shift 半音平移，按 key 拼写；后缀（m7/maj7/6/9...）原样保留。"""
    parsed = musicxml.parse_chord_symbol(chord)
    if parsed is None:
        return chord
    letter, alter, suffix, bass_letter, bass_alter = parsed
    root_pc = (SEMITONES[letter] + alter + shift) % 12
    out = spell(root_pc, key) + suffix
    if bass_letter:
        b_alt = {"": 0, "#": 1, "b": -1}[bass_alter or ""]
        bass_pc = (SEMITONES[bass_letter] + b_alt + shift) % 12
        out += "/" + spell(bass_pc, key)
    return out


def transpose_score(score: Score, new_key: str) -> Score:
    """转调整首曲：换调号 + 和弦平移。音符首调音级不变。原地修改并返回 score。"""
    musicxml.key_info(score.key)      # 原调必须合法，否则半音差无从算起
    musicxml.key_info(new_key)        # 新调必须合法
    shift = (tonic_pc(new_key) - tonic_pc(score.key)) % 12
    score.key = new_key
    for measure in score.measures:
        for note in measure.notes:
            if note.chord:
                note.chord = transpose_chord(note.chord, shift, new_key)
    return score
