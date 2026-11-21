# Jianpu DSL reference

[简体中文](DSL.md) · **English**

> For the `music-preprocessor-py` tool.
> One sentence: **whitespace-separated jianpu tokens plus a few `Xxx:` declarations**;
> `|` separates bars, and a whole song can be written on one line.

## Cheat sheet

```text
Title:小星星            % header info (whole line)
Key:C Time:4/4          % key / time signature (required)
Tempo:4=100             % tempo (optional)

H: 一闪一闪亮晶晶        % hanzi lyrics, one syllable per note (H1:/H2: = verse no.)
[C] 1 1 [G7] 5 5 | [Am] 6 6 [D7] 5 - |
q1 q2 q3 q4
```

| Token | Meaning |
|---|---|
| `1`…`7` | scale degree (do…si) |
| `0` / `x` | rest |
| `8` / `9` | shorthand for `1'` / `2'` (octave up) |
| `'` / `,` | octave up / down (can repeat: `1''`) |
| `#` / `b` | sharp / flat, written before the degree: `#4`, `b7` |
| `.` | dot, written last: `1.` |
| `-` | extend by one beat (can repeat) |
| `~` | tie to the next note |
| `(` `)` | slur start / end (after the previous note; may also be written `(2`, `2)`) |
| `[C]` | chord symbol, applies to the **next** note |
| `\|` | barline; `\|\|` double barline |
| `q` `s` `d` `c` `h` | duration prefix: eighth, 16th, 32nd, quarter, 64th |
| `\break` | system break (after a note) |
| `^"text"` / `_"text"` | text above / below the staff |
| `%` | comment to end of line |

---

## 1. File structure

- Tokens are separated by **whitespace** (spaces, tabs, newlines); a newline has no musical meaning.
- Three things are **whole-line** syntax and must start at the beginning of a line:
  - header fields `Title:` `Subtitle:` `Composer:` …
  - lyrics `H:` `L:`
  - raw LilyPond blocks `LP: … :LP`
- Everything from `%` to the end of the line is a comment.

```text
% this is a comment
Key:C Time:4/4
1 2 3 4 | 5 6 7 1' |
```

## 2. Header fields

| Field | Meaning | MusicXML / MuseScore |
|---|---|---|
| `Title:` | title | title |
| `Subtitle:` | subtitle | subtitle (merged with Subsubtitle into one line) |
| `Subsubtitle:` | second subtitle | same as above |
| `Composer:` | composer | top right |
| `Poet:` | lyricist | top left |
| `Instrument:` | instrument / note | currently ignored (written into the LilyPond header) |
| `Arranger:` `Copyright:` | arranger / copyright | currently ignored |

- Field names are **case-sensitive** and the colon must be the ASCII `:`.
- The value is everything after the colon, spaces and Chinese included.

```text
Title:小星星
Subtitle:带和弦的 Lead Sheet
Composer:曲：传统
Poet:词：佚名
```

## 3. Key, time signature, tempo

```text
Key:C  Key:G  Key:F#  Key:Bb  Key:Am  Key:F#m
Time:4/4  Time:3/4  Time:6/8  Time:2/2
Time:3/4,4          % pickup: 3/4 with a one-beat anacrusis (4 = quarter, 8 = eighth)
Tempo:4=100         % quarter note = 100
```

- `Key:` and `Time:` are **required**; the parser errors without them.
- The three declarations may appear anywhere, including on the same line as notes
  (`Key:C Time:4/4` is the usual form).
- If a declaration is repeated, **the last one wins** (it applies to the whole piece).

**Supported keys** (15 major, 15 minor):

```text
major: C G D A E B F# C#  F Bb Eb Ab Db Gb Cb
minor: Am Em Bm F#m C#m G#m D#m A#m  Dm Gm Cm Fm Bbm Ebm Abm
```

> Minor keys take their scale from the relative major; in `Key:Am` the degree `1` is A.

## 4. Notes

Full form of a note token:

```
[duration] [accidental] degree [octave] [dot]
 q/s/d/c/h     #/b     0-7/8/9/x  ' or ,    .
```

Examples: `q#4'` = eighth note, sharp fourth, one octave up; `b7,` = flat seventh,
one octave down; `1.` = dotted quarter.

### 4.1 Duration prefixes

| Prefix | Duration | Beats in 4/4 |
|---|---|---|
| (none) | quarter note | 1 |
| `c` | quarter note (explicit) | 1 |
| `q` | eighth note | 1/2 |
| `s` | 16th note | 1/4 |
| `d` | 32nd note | 1/8 |
| `h` | 64th note | 1/16 |

Upper or lower case both work (`q` and `Q` are equivalent).

### 4.2 Degrees

| Token | Meaning |
|---|---|
| `1`–`7` | scale degree (movable do) |
| `0` | rest |
| `x` / `X` | rest (same as `0`, spelling borrowed from percussion) |
| `8` | shorthand for `1'` |
| `9` | shorthand for `2'` |

### 4.3 Octaves

`'` raises one octave, `,` lowers one octave; they can repeat:

```text
1      middle register (C4 in C, G3 in G, Bb3 in Bb)
1'     one octave up (Bb4 in Bb)
1''    two octaves up
1,     one octave down
```

`1` sits **next to middle C** (within six semitones either way) and degrees count upward
from the tonic, so `1 2 3 4 5 6 7` always ascends in every key:

```text
Key:C   C4  D4  E4  F4  G4  A4  B4
Key:G   G3  A3  B3  C4  D4  E4  F#4
Key:Bb  Bb3 C4  D4  Eb4 F4  G4  A4
```

### 4.4 Accidentals

Only a single `#` or `b`, written **before** the degree and **after** the duration prefix:

```text
#4    sharp fourth
b7    flat seventh
q#4'  eighth, sharp fourth, octave up
```

Accidentals are **added on top of the key signature**: in `Key:G` the degree `4` is already
C, so `#4` gives C♯.

### 4.5 Dots

A trailing `.` multiplies the duration by 1.5. **Only a single dot** is supported:

```text
1.   dotted quarter (1.5 beats)
q3.  dotted eighth
```

## 5. Extensions, ties, slurs

### Extension `-`

Every `-` makes the **previous note** sound one beat longer (a quarter note), regardless of
its own duration:

```text
1 -        2 beats
1 - -      3 beats
1 - - -    4 beats (a whole bar)
q1 -       0.5 + 1 = 1.5 beats
```

### Tie `~`

Connects the previous note to the next one (across beats or bars):

```text
1 ~ 1 3       the first 1 is tied to the second
1 ~ | 1 2 3   tie across a barline
```

### Slur `(` `)`

Two equivalent spellings:

```text
4 ( 5 ) 6      separate brackets: "(" after 4 means the slur goes 4 → 5
(4 5)          attached brackets: (4 starts on 4, 5) ends on 5
```

Note that the separated form starts on the **previous** note, so `4 ( 5 )` slurs 4 → 5,
not 5 → the next note.

## 6. Chords

`[ChordName]` is written **before** a note and binds to it:

```text
[C] 1 1 [G7] 5 5 | [Am] 6 6 [D7] 5 - |
```

Chord names are passed through almost verbatim (root letter + suffix); the usual jazz
spellings all work:

```text
[C] [Am] [G7] [Cmaj7] [Cm7] [Dm9] [G13] [C6/9]
[F#m7b5] [Bb] [Eb] [C/E] [G7sus4] [A7]
```

> - Slash chords like `C/E`: whatever follows the slash must be a note name, otherwise it is
>   treated as part of the quality (the `/9` in `C6/9` is not mistaken for a bass note).
> - MuseScore normalises chord symbols a little: `G7sus4` is displayed as `G7sus⁴`, same meaning.
> - A `[C]` only applies to the next note, even if a rest comes first.

## 7. Lyrics

| Syntax | Rule |
|---|---|
| `H: 一闪一闪亮晶晶` | hanzi lyrics, **one character per note**, punctuation sticks to the previous character |
| `L: twin-kle twin-kle` | latin lyrics, split on **spaces** |
| `H1: …` / `H2: …` / `L1: …` | explicit verse number (1–9) |

### Basic use: one line per verse

```text
H1: 春天来了花儿开
H2: 秋天到了果实熟
```

`H1` is printed above `H2`; both verses share the same melody.

### Where a lyric line starts

**A lyric line written under a music line belongs to that music line** and starts on its
first note:

```text
[Bb] 0 q1 q2 q3 q5 q6 q3 | ...     % bar 1, beat 1 is a rest
H: 我们成为一家人……                % → "我" lands on beat 2 of bar 1
```

- One verse **may be split over several lines** (long sentences); the text simply continues.
- Verses can also switch in the middle of a line:
  `H: 耶稣，成为神国的子民。H1: 因着耶稣得洁净，`
- The old spelling `H: 1. 春天…` / `H: 2. 秋天…` (verse number as text prefix) is still
  accepted and is equivalent to `H1:` / `H2:`.

### Starting a second verse halfway through

A new verse (`H2`) starts where **the preceding lyric line started**, i.e. it aligns to the
same music position:

```text
...
H: 耶稣，成为神国的子民。H1: 因着耶稣得洁净，   ← H1 continues after "子民。"
H2: 因着耶稣同敬拜，                             ← H2 also starts after "子民。"
```

So both chorus verses are sung over the same melody and line up vertically.

### Details

- Lyrics attach in order to **every sung note**; when the text runs out the remaining notes
  carry no lyric, and extra text is dropped.
- **The note after a tie does not take a syllable** (`q2' ~ | 2'` is one sung note), which is
  why `97 notes − 5 ties = 92 syllables`.
- `_` means **join**: the next character is merged into the previous syllable, so two
  characters are sung on one note, e.g. `H: 啦_啦`.
- Verse numbers are only data — MuseScore does not print "1." / "2." by default.

## 8. Barlines and layout

**Line breaks in the source are line breaks on the page**: one line of music = one system.
To make a system longer or shorter, just move the line break in the source.

| Syntax | Effect |
|---|---|
| `\|` | barline (may be omitted at the end of a line) |
| `\|\|` | double barline (common at section ends); `\|.` `.\|` `\|:` `:\|` also work |
| (newline) | source line break = system break |
| `\break` | forced break (same as a plain newline, written after a note) |
| `\bar "\|\|"` | equivalent to `\|\|`, native LilyPond spelling |
| `^"text"` | text above the note |
| `_"text"` | text below the note |

```text
[C] 1 2 3 4 \break | [G7] 5 6 7 1' |
1' ^"副歌" 7 6 5 |
```

- The beats in a bar should match the time signature; the MusicXML backend warns otherwise
  (MuseScore still opens the file but pads the bar with rests).
- Consecutive `|` do not create empty bars.

## 9. Raw LilyPond

Only meaningful for `-f ly`; the MusicXML backend **ignores it with a warning**.

```text
LP:
\paper { top-margin = 20\mm left-margin = 20\mm }
:LP
```

- Everything between `LP:` and `:LP` is copied to the top level of the `.ly` file.
- Tokens starting with `\`, and `^"…"`, `_"…"`, `"…"`, are **appended to the previous note**
  verbatim.
- The MusicXML backend only understands `\break`, `\bar "…"`, `^"…"` and `_"…"`; anything
  else produces a warning and is dropped.

## 10. Comments

```text
% everything from the percent sign to the end of the line is a comment
```

## 11. Not implemented / errors

| Syntax | Status |
|---|---|
| `R{ … }` repeats | error: `repeat/alternate notation not supported yet` |
| `A{ … }` alternate endings | same |
| `-` without a preceding note | error: `'-' dash must follow a note` |
| `~` `(` `)` without a preceding note | error |
| missing `Key:` or `Time:` | error: `No Key: declaration found` |
| unknown key (`Key:H`) | error: `Unknown key 'H'` |

Errors include line/column and a `^` caret; misspelled keywords/keys also get a
`did you mean` hint:

```text
Line 1, column 7:
  Key:C Tiem:4/4
        ^
  unrecognised token 'Tiem:4/4'
  hint: did you mean 'Time:'?
```

The same diagnostics appear live as squiggles in the VSCode extension.

## 12. Complete examples

Four runnable examples live in `examples/`:

| File | Contents |
|---|---|
| [`examples/01_basics.dsl`](../examples/01_basics.dsl) | degrees, octaves, accidentals, durations, dots, extensions, rests |
| [`examples/02_lead_sheet.dsl`](../examples/02_lead_sheet.dsl) | 小星星: chords + hanzi lyrics + header |
| [`examples/03_pickup.dsl`](../examples/03_pickup.dsl) | 3/4 pickup + ties + slurs |
| [`examples/04_verses.dsl`](../examples/04_verses.dsl) | two verses + latin lyrics + text marks + line breaks |

Minimal runnable example:

```text
Key:C Time:4/4
1 1 5 5 | 6 6 5 - | 4 4 3 3 | 2 2 1 - |
```

## 13. Commands

```bash
python mpp.py song.dsl                    # default: MuseScore project song.mscz
python mpp.py song.dsl -f pdf             # printable PDF
python mpp.py song.dsl -f mscz,pdf        # both at once
python mpp.py song.dsl -f musicxml        # MusicXML
python mpp.py song.dsl -f ly              # LilyPond source (legacy, stdout)
python mpp.py song.dsl --transpose Bb -f pdf  # transpose to Bb, then engrave
```

On Windows you can also use `mpp.cmd song.dsl -f pdf`.

`-t` / `--transpose KEY` transposes the whole song. Jianpu degrees are movable-do, so
note tokens stay the same and only the key changes; chord roots (including slash basses)
shift by the interval between the old and new tonics and are respelled for the target key.
Chord suffixes (`m7`, `maj7`, `6/9`, ...) are preserved. `KEY` uses the same names as
section 3.

Options: `-f` (`mscz` (default) | `pdf` | `png` | `musicxml` | `ly`, comma-separated),
`-o`, `-t`/`--transpose`, `--musescore`, `--style`, `--no-style`, `--keep-xml`, `-q`.
