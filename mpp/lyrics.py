# -*- coding: utf-8 -*-
"""Lyrics: split lines into syllables and lay them over the melody notes.

A lyric line is anchored at the note where it appears in the source, so a new
verse can start halfway through a piece:

    [Bb] 0 q1 q2 ...            % verse 1 covers the first part
    H: we are one family ...
    [F] 2' - 7 6 ...            % two verses start here
    H1: verse one, part two ...
    H2: verse two, part two ...

Lines with the same verse number are segments of one verse and simply follow
each other.
"""
from .ir import Score

PUNCT = "，。、；：？！,.;:?!"


def split_line(line) -> list:
    """One syllable per note: hanzi by character, latin by whitespace."""
    if not line.hanzi:
        return line.text.split()
    out = []
    glue = False
    for ch in line.text:
        if ch.isspace():
            continue
        if ch == "_":                     # melisma: join next char to previous
            glue = True
            continue
        if ch in PUNCT and out:
            out[-1] += ch
        elif glue and out:
            out[-1] += ch
            glue = False
        else:
            out.append(ch)
    return out


def _sort_key(item):
    index, key = item
    return (0, int(key), index) if key.isdigit() else (1, 0, index)


def _anchor(line, key, music_first, ends):
    """Where a lyric line starts.

    A line written under a music line belongs to that music line; a line that
    starts a new verse but sits between lyric lines joins the next music line;
    a segment written inline (H1: in the middle of a line) simply continues.
    """
    if line.inline:
        return ends.get(key, line.start)
    previous_music = music_first.get(line.line - 1)
    if previous_music is not None:
        return previous_music
    following = [l for l in music_first if l > line.line]
    if following:
        return music_first[min(following)]
    return ends.get(key, line.start)


def sung_slots(score) -> list:
    """Notes that carry a syllable: no rests, no tie continuations."""
    slots = []
    tied = False
    for measure in score.measures:
        for note in measure.notes:
            if note.is_rest:
                tied = False
                continue
            if not tied:
                slots.append(note)
            tied = note.tie_to_next
    return slots


def build(score: Score):
    """Return (verse_keys, {verse_key: {note_index: syllable}}).

    * a line under a music line starts with that music line (verse 1)
    * a further line of the same verse keeps flowing from where the text is
    * a new verse starts where the preceding lyric line started, so parallel
      verses share the same music position
    """
    slots = sung_slots(score)
    total = len(slots)

    # first sung note of every source line that carries music
    music_first = {}
    for i, note in enumerate(slots):
        if note.line and note.line not in music_first:
            music_first[note.line] = i

    tables = {}
    order = []
    ends = {}
    last_start = None
    for line in score.lyrics:
        key = line.verse or "1"
        if key in tables:                       # next line of a known verse
            pos = ends[key]
        else:                                   # first line of a new verse
            order.append(key)
            above = music_first.get(line.line - 1)
            if above is not None:
                pos = above
            elif last_start is not None:
                pos = last_start
            else:
                pos = 0
            tables[key] = {}
        last_start = pos
        table = tables[key]
        for syllable in split_line(line):
            if pos >= total:
                break
            table[pos] = syllable
            pos += 1
        ends[key] = pos

    ordered = [k for _, k in sorted(enumerate(order), key=_sort_key)]
    return ordered, tables
