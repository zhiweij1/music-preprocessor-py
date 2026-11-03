# -*- coding: utf-8 -*-
"""Test suite: `python -m unittest discover -s tests` (or `python tests/test_mpp.py`)."""
import os
import sys
import unittest
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from mpp import lilypond, musicxml                      # noqa: E402
from mpp.parser import DslError, parse_text             # noqa: E402

FIXTURES = os.path.join(HERE, "fixtures")


def load(name: str) -> str:
    path = os.path.join(FIXTURES, name)
    with open(path, encoding="utf-8-sig") as fh:
        return fh.read()


def score_of(name: str):
    return parse_text(load(name))


def xml_of(name: str):
    return ET.fromstring(musicxml.to_musicxml(score_of(name)))


def xml_of_text(text: str):
    return ET.fromstring(musicxml.to_musicxml(parse_text(text)))


def pitches(measure):
    out = []
    for note in measure.findall("note"):
        p = note.find("pitch")
        if p is None:
            out.append(None)
            continue
        step = p.findtext("step")
        alter = int(p.findtext("alter") or 0)
        octave = int(p.findtext("octave"))
        out.append((step, alter, octave))
    return out


class TestParsing(unittest.TestCase):
    def test_all_fixtures_convert(self):
        names = sorted(f for f in os.listdir(FIXTURES) if f.endswith(".dsl"))
        names += sorted("mirror/" + f for f in os.listdir(os.path.join(FIXTURES, "mirror"))
                        if f.endswith(".dsl"))
        self.assertGreaterEqual(len(names), 19)
        for name in names:
            with self.subTest(name=name):
                score = score_of(name)
                self.assertTrue(score.measures, f"{name}: no measures")
                xml = musicxml.to_musicxml(score)
                root = ET.fromstring(xml)
                self.assertEqual(len(root.findall(".//measure")), len(score.measures))
                self.assertTrue(lilypond.generate(score).startswith('\\version'))

    def test_note_token_forms(self):
        score = parse_text("Key:C Time:4/4\nq#4' 8 9 0 x | 1. 2 - |")
        notes = [n for m in score.measures for n in m.notes]
        self.assertEqual(notes[0].base_duration, 8)
        self.assertEqual(notes[0].alteration, 1)
        self.assertEqual(notes[0].octave_shift, 1)
        self.assertEqual((notes[1].scale_degree, notes[1].octave_shift), (1, 1))
        self.assertEqual((notes[2].scale_degree, notes[2].octave_shift), (2, 1))
        self.assertTrue(notes[3].is_rest)
        self.assertTrue(notes[4].is_rest)
        self.assertTrue(notes[5].dotted)
        self.assertEqual(notes[6].dash_count, 1)

    def test_repeat_rejected(self):
        with self.assertRaises(DslError):
            parse_text("Key:C Time:4/4\nR{ 1 2 }")

    def test_dash_without_note_rejected(self):
        with self.assertRaises(DslError):
            parse_text("Key:C Time:4/4\n- 1")

    def test_unknown_key_rejected(self):
        with self.assertRaises(ValueError):
            musicxml.to_musicxml(parse_text("Key:H Time:4/4\n1"))


class TestMusicXml(unittest.TestCase):
    def test_key_signature_and_pitch(self):
        root = xml_of("twinkle_chords.dsl")          # Key:G
        self.assertEqual(root.findtext(".//fifths"), "1")
        self.assertEqual(root.findtext(".//mode"), "major")
        first = pitches(root.findall(".//measure")[0])[0]
        self.assertEqual(first, ("G", 0, 3))

    def test_chords(self):
        root = xml_of("twinkle_chords.dsl")
        harmonies = root.findall(".//harmony")
        self.assertEqual(len(harmonies), 8)
        roots = [h.findtext("root/root-step") for h in harmonies]
        self.assertEqual(roots, ["C", "G", "A", "D", "C", "G", "C", "G"])
        kinds = [h.find("kind").text for h in harmonies]
        self.assertEqual(kinds, ["major", "other", "other", "other",
                                 "major", "major", "major", "other"])

    def test_chord_suffix_and_slash(self):
        score = parse_text("Key:C Time:4/4\n[F#m7b5] 1 [C6/9] 1 [C/E] 1 [G7sus4] 1 |")
        root = ET.fromstring(musicxml.to_musicxml(score))
        kinds = [h.find("kind") for h in root.findall(".//harmony")]
        self.assertEqual(kinds[0].get("text"), "m7b5")
        self.assertEqual(kinds[1].get("text"), "6/9")
        self.assertEqual(root.findtext(".//harmony[3]/bass/bass-step"), "E")
        self.assertEqual(kinds[3].get("text"), "7sus4")

    def test_pickup_measure(self):
        root = xml_of("anacrusis_ties.dsl")          # Time:3/4,4
        measures = root.findall(".//measure")
        self.assertEqual(measures[0].get("implicit"), "yes")
        self.assertEqual(measures[0].get("number"), "0")
        self.assertEqual(root.findtext(".//beats"), "3")

    def test_lyrics_verses(self):
        root = xml_of("song_full.dsl")
        lyrics = root.findall(".//lyric")
        numbers = {l.get("number") for l in lyrics}
        self.assertEqual(numbers, {"1", "2"})
        texts = [l.findtext("text") for l in lyrics[:2]]
        self.assertEqual(texts, ["春", "秋"])

    def test_scale_ascends_in_every_key(self):
        """1 2 3 4 5 6 7 must ascend from the tonic (regression: used to drop an
        octave at degree 4 in non-C keys)."""
        for key, expected in {
            "C": ["C4", "D4", "E4", "F4", "G4", "A4", "B4"],
            "G": ["G3", "A3", "B3", "C4", "D4", "E4", "F#4"],
            "Bb": ["Bb3", "C4", "D4", "Eb4", "F4", "G4", "A4"],
            "Am": ["A3", "B3", "C4", "D4", "E4", "F4", "G4"],
        }.items():
            with self.subTest(key=key):
                root = xml_of_text(f"Key:{key} Time:4/4\n1 2 3 4 5 6 7 |")
                got = []
                for note in root.findall(".//note"):
                    p = note.find("pitch")
                    if p is None:
                        continue
                    step = p.findtext("step")
                    alter = int(p.findtext("alter") or 0)
                    acc = "#" if alter > 0 else ("b" if alter < 0 else "")
                    got.append(step + acc + p.findtext("octave"))
                self.assertEqual(got, expected)

    def test_lyric_line_after_music_anchors_to_that_line(self):
        # lyrics written under a music line belong to that line
        text = ("Key:C Time:4/4\n"
                "1 2 3 4 | 1 2 3 4 |\n"
                "H: a b c d e f g h\n")
        root = xml_of_text(text)
        notes = root.findall(".//note")
        texts = [l.findtext("text") for n in notes for l in n.findall("lyric")]
        self.assertEqual(texts, list("abcdefgh"))

    def test_second_verse_can_start_later(self):
        text = ("Key:C Time:4/4\n"
                "1 2 3 4 | 1 2 3 4 |\n"
                "H1: a b c d e f g h\n"
                "1 2 3 4 | 1 2 3 4 |\n"
                "H2: i j k l m n o p\n")
        root = xml_of_text(text)
        notes = root.findall(".//note")
        verse2 = [i for i, n in enumerate(notes)
                  if any(l.get("number") == "2" for l in n.findall("lyric"))]
        self.assertEqual(verse2[0], 8)

    def test_tied_notes_do_not_take_a_syllable(self):
        text = ("Key:C Time:4/4\n"
                "1 ~ 1 2 3 |\n"
                "H: a b c\n")
        root = xml_of_text(text)
        texts = [l.findtext("text") for n in root.findall(".//note")
                 for l in n.findall("lyric")]
        self.assertEqual(texts, ["a", "b", "c"])

    def test_inline_verse_marker(self):
        root = xml_of_text("Key:C Time:4/4\nH: a b H1: c d\n1 2 3 4 |\n")
        got = [l.findtext("text")
               for n in root.findall(".//note") for l in n.findall("lyric")]
        self.assertEqual(got, ["a", "b", "c", "d"])

    def test_tie_and_slur(self):
        root = xml_of("anacrusis_ties.dsl")
        self.assertTrue(root.findall(".//tie[@type='start']"))
        self.assertTrue(root.findall(".//slur[@type='start']"))
        self.assertTrue(root.findall(".//slur[@type='stop']"))

    def test_source_line_breaks_become_systems(self):
        score = parse_text("Key:C Time:4/4\n1 2 3 4 | 5 6 7 1' |\n1' 7 6 5 |")
        self.assertFalse(score.measures[1].break_before)
        self.assertTrue(score.measures[2].break_before)
        root = ET.fromstring(musicxml.to_musicxml(score))
        prints = [p for p in root.findall(".//print") if p.get("new-system") == "yes"]
        self.assertEqual(len(prints), 2)
        self.assertIn("\\break", lilypond.generate(score))

    def test_break_becomes_new_system(self):
        root = xml_of("song_full.dsl")
        prints = [p for p in root.findall(".//print") if p.get("new-system") == "yes"]
        self.assertGreaterEqual(len(prints), 2)

    def test_duration_sum_matches_time_signature(self):
        for name in ("twinkle.dsl", "twinkle_chords.dsl", "song_full.dsl", "key_g.dsl"):
            with self.subTest(name=name):
                score = score_of(name)
                beats = int(score.time_signature.split("/")[0])
                for measure in score.measures:
                    total = sum(musicxml.note_beats(n) for n in measure.notes)
                    self.assertEqual(float(total), beats, f"{name}: bar with {total} beats")

    def test_rest_is_written_as_rest(self):
        score = parse_text("Key:C Time:4/4\n1 0 2 0 |")
        root = ET.fromstring(musicxml.to_musicxml(score))
        self.assertEqual(len(root.findall(".//rest")), 2)

    def test_lyrics_melisma_glue(self):
        score = parse_text("Key:C Time:4/4\nH: 啦_啦 啦\n1 2 3 |")
        root = ET.fromstring(musicxml.to_musicxml(score))
        self.assertEqual([l.findtext("text") for l in root.findall(".//lyric")],
                         ["啦啦", "啦"])


class TestLilyPond(unittest.TestCase):
    def test_basic_shape(self):
        text = lilypond.generate(score_of("twinkle_chords.dsl"))
        self.assertIn('\\version "2.24.0"', text)
        self.assertIn("\\chordmode", text)
        self.assertIn("c4 s4 g4:7 s4", text)
        self.assertIn("\\key g \\major", text)
        self.assertIn("\\time 4/4", text)

    def test_no_chords_no_chordnames(self):
        text = lilypond.generate(score_of("twinkle.dsl"))
        self.assertNotIn("ChordNames", text)

    def test_partial(self):
        text = lilypond.generate(score_of("anacrusis_ties.dsl"))
        self.assertIn("\\partial 4", text)
        self.assertIn("\\time 3/4", text)

    def test_lyrics_block(self):
        text = lilypond.generate(score_of("song_full.dsl"))
        self.assertIn('\\new Lyrics = "lyrics1"', text)
        self.assertIn("\\set stanza = #\"1.\"", text)


class TestCli(unittest.TestCase):
    def test_ly_to_stdout(self):
        import subprocess
        out = subprocess.run([sys.executable, os.path.join(ROOT, "mpp.py"),
                              os.path.join(FIXTURES, "twinkle.dsl")],
                             capture_output=True, text=True)
        self.assertEqual(out.returncode, 0)
        self.assertTrue(out.stdout.startswith('\\version "2.24.0"'))

    def test_musicxml_file(self):
        import subprocess
        tmp = os.path.join(HERE, "out", "tmp")
        os.makedirs(tmp, exist_ok=True)
        target = os.path.join(tmp, "out.musicxml")
        out = subprocess.run([sys.executable, os.path.join(ROOT, "mpp.py"),
                              os.path.join(FIXTURES, "twinkle.dsl"),
                              "-f", "musicxml", "-o", target],
                             capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertTrue(os.path.exists(target))
        ET.parse(target)

    def test_bad_input_reports_error(self):
        import subprocess
        out = subprocess.run([sys.executable, os.path.join(ROOT, "mpp.py"),
                              os.path.join(FIXTURES, "does-not-exist.dsl")],
                             capture_output=True, text=True)
        self.assertEqual(out.returncode, 1)
        self.assertIn("Error:", out.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
