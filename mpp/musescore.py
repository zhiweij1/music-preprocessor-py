# -*- coding: utf-8 -*-
"""Locate and drive the MuseScore 4 command line to export .mscz/.pdf/.png."""
import glob
import os
import shutil
import subprocess
import sys

CANDIDATES = [
    r"C:\Program Files\MuseScore 4\bin\MuseScore4.exe",
    r"C:\Program Files\MuseScore 4\MuseScore4.exe",
    r"C:\Program Files (x86)\MuseScore 4\bin\MuseScore4.exe",
    r"C:\Program Files (x86)\MuseScore 4\MuseScore4.exe",
]

EXE_NAMES = ["MuseScore4", "mscore4", "mscore", "MuseScore4.exe"]


def find(explicit: str = None) -> str:
    """Return the MuseScore executable path, or None."""
    if explicit:
        return explicit if os.path.isfile(explicit) else None
    env = os.environ.get("MPP_MUSESCORE")
    if env and os.path.isfile(env):
        return env
    for path in CANDIDATES:
        if os.path.isfile(path):
            return path
    for name in EXE_NAMES:
        found = shutil.which(name)
        if found:
            return found
    return None


def convert(xml_path: str, out_path: str, exe: str, style: str = None,
            timeout: int = 180):
    """Run `MuseScore4 -o out in`, optionally applying a style file.

    Page-based formats (png/svg) are written as `<name>-1.png`, `<name>-2.png`…
    Returns the list of files actually created.
    """
    if not exe:
        raise RuntimeError("MuseScore executable not found")
    args = [exe, "-f"]
    if style:
        args += ["-S", style]
    args += ["-o", out_path, xml_path]
    proc = subprocess.run(args, capture_output=True, timeout=timeout)

    created = []
    if os.path.exists(out_path):
        created = [out_path]
    else:
        base, ext = os.path.splitext(out_path)
        created = sorted(glob.glob(f"{base}-*{ext}"))
    if proc.returncode != 0 or not created:
        err = (proc.stderr or b"").decode("utf-8", "replace").strip()
        err = "\n".join(line for line in err.splitlines() if "log file" not in line)
        raise RuntimeError(f"MuseScore failed for {out_path}: {err or 'unknown error'}")
    return created


def convert_many(xml_path: str, targets: list, exe: str, style: str = None):
    """Convert one MusicXML file into several outputs: [(ext, path), ...]."""
    results = []
    for ext, path in targets:
        results.extend(convert(xml_path, path, exe, style))
    return results
