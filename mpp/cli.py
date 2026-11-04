# -*- coding: utf-8 -*-
"""Command line interface for music-preprocessor (Python edition)."""
import argparse
import os
import sys

from . import __version__, lilypond, musicxml, musescore
from .parser import DslError, parse_text

DEFAULT_STYLE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             "assets", "jazz-lead-sheet.mss")

FORMATS = ("ly", "musicxml", "mscz", "pdf", "png")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="mpp",
        description="简谱 DSL → MuseScore (.mscz/.pdf/.png)；也可输出 MusicXML、LilyPond(legacy)")
    p.add_argument("input", help="input .dsl file")
    p.add_argument("-o", "--output", help="output path (single format only)")
    p.add_argument("-f", "--format", default="mscz",
                   help="comma separated: mscz, pdf, png, musicxml, ly (default: mscz)")
    p.add_argument("--musescore", help="path to MuseScore4.exe")
    p.add_argument("--style", help="MuseScore style file (.mss)")
    p.add_argument("--no-style", action="store_true", help="do not apply the lead-sheet style")
    p.add_argument("--keep-xml", action="store_true",
                   help="keep the intermediate .musicxml next to the output")
    p.add_argument("-q", "--quiet", action="store_true", help="suppress warnings")
    p.add_argument("--version", action="version", version=f"mpp {__version__}")
    return p


def _warn(score, quiet):
    if quiet:
        return
    for message in score.warnings:
        print(f"warning: {message}", file=sys.stderr)


def _setup_io():
    """UTF-8 when piping, never crash on an unencodable console."""
    for stream in (sys.stdout, sys.stderr):
        if stream is None:
            continue
        try:
            if stream.isatty():
                stream.reconfigure(errors="replace")
            else:
                stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass


def main(argv=None) -> int:
    _setup_io()
    args = build_parser().parse_args(argv)
    formats = [f.strip().lower() for f in args.format.split(",") if f.strip()]
    unknown = [f for f in formats if f not in FORMATS]
    if unknown:
        print(f"Error: unknown format(s): {', '.join(unknown)}", file=sys.stderr)
        return 1
    if args.output and len(formats) > 1:
        print("Error: -o can only be used with a single format", file=sys.stderr)
        return 1

    try:
        with open(args.input, encoding="utf-8-sig") as fh:
            source = fh.read()
        score = parse_text(source)
    except (OSError, DslError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    stem = os.path.splitext(args.input)[0]

    # ---- LilyPond (default, keeps the "Unix filter" behaviour) ----------
    if formats == ["ly"]:
        try:
            text = lilypond.generate(score)
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        _warn(score, args.quiet)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as fh:
                fh.write(text)
            print(f"Wrote {args.output} ({len(text)} bytes)")
        else:
            sys.stdout.write(text)
        return 0

    # ---- MusicXML / MuseScore ------------------------------------------
    try:
        xml_text = musicxml.to_musicxml(score)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    _warn(score, args.quiet)

    if formats == ["musicxml"]:
        out = args.output or stem + ".musicxml"
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(xml_text)
        print(f"Wrote {out} ({len(xml_text)} bytes)")
        return 0

    exe = musescore.find(args.musescore)
    if not exe:
        print("Error: MuseScore 4 not found. Pass --musescore <path> "
              "or set MPP_MUSESCORE.", file=sys.stderr)
        return 1

    style = None
    if not args.no_style:
        style = args.style or (DEFAULT_STYLE if os.path.isfile(DEFAULT_STYLE) else None)

    if args.keep_xml:
        base = os.path.splitext(args.output)[0] if args.output else stem
        xml_path = base + ".musicxml"
        temp_xml = False
    else:
        # keep the temporary file next to the target (predictable permissions,
        # and MuseScore always sees a local path)
        target = args.output or f"{stem}.{formats[0]}"
        folder = os.path.dirname(os.path.abspath(target))
        name = os.path.splitext(os.path.basename(target))[0]
        xml_path = os.path.join(folder, f".{name}.{os.getpid()}.tmp.musicxml")
        temp_xml = True

    try:
        with open(xml_path, "w", encoding="utf-8") as fh:
            fh.write(xml_text)
        for fmt in formats:
            if fmt == "musicxml":
                out = args.output or stem + ".musicxml"
                if os.path.abspath(out) != os.path.abspath(xml_path):
                    with open(out, "w", encoding="utf-8") as fh:
                        fh.write(xml_text)
            else:
                out = args.output or f"{stem}.{fmt}"
                musescore.convert(xml_path, out, exe, style)
            print(f"Wrote {out}")
        if args.keep_xml and not temp_xml:
            print(f"Wrote {xml_path}")
    except (OSError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        if temp_xml and os.path.exists(xml_path):
            os.remove(xml_path)
    return 0
