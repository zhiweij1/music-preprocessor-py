# -*- coding: utf-8 -*-
"""Intermediate representation for the 简谱 DSL."""
from dataclasses import dataclass, field


@dataclass
class Note:
    scale_degree: int = 1      # 1-7, 0 = rest
    octave_shift: int = 0      # ' up, , down
    alteration: int = 0        # # +1, b -1
    base_duration: int = 4     # denominator: 4, 8, 16, 32, 64
    dash_count: int = 0        # trailing "-" beat extensions
    dotted: bool = False
    chord: str = ""            # chord symbol attached to this note
    tie_to_next: bool = False
    slur_begin: bool = False
    slur_end: bool = False
    after: list = field(default_factory=list)   # verbatim \commands / ^"text"
    line: int = 0              # source line (used to place lyrics)

    @property
    def is_rest(self) -> bool:
        return self.scale_degree == 0


@dataclass
class Measure:
    notes: list = field(default_factory=list)
    end_bar: str = ""          # raw bar token: "", "||", "|.", ".|", ...
    break_before: bool = False # source line break before this measure


@dataclass
class LyricsLine:
    verse: str
    text: str
    hanzi: bool
    start: int = 0             # note index this line starts at
    line: int = 0              # source line
    inline: bool = False       # more than one lyric segment on that source line


@dataclass
class Score:
    key: str = ""
    time_signature: str = ""
    tempo: str = ""
    measures: list = field(default_factory=list)
    headers: dict = field(default_factory=dict)
    lp_blocks: list = field(default_factory=list)
    lyrics: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    def warn(self, message: str) -> None:
        self.warnings.append(message)
