# -*- coding: utf-8 -*-
"""把浏览器端需要的 mpp 模块复制到 web/mpp/（保持单一代码源）。

CLI 专属模块（cli.py / musescore.py / __main__.py）不复制：它们依赖
subprocess / argparse，浏览器里用不到。GitHub Pages 部署时会自动跑本脚本。
"""
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
MPP = os.path.join(os.path.dirname(HERE), "mpp")
DEST = os.path.join(HERE, "mpp")

MODULES = (
    "__init__.py",
    "ir.py",
    "lexer.py",
    "parser.py",
    "lyrics.py",
    "lilypond.py",
    "musicxml.py",
    "transpose.py",
    "diagnostics.py",
)


def main() -> None:
    if os.path.isdir(DEST):
        shutil.rmtree(DEST)
    os.makedirs(DEST)
    for name in MODULES:
        src = os.path.join(MPP, name)
        if not os.path.isfile(src):
            raise FileNotFoundError(src)
        shutil.copy2(src, os.path.join(DEST, name))
    print(f"Synced {len(MODULES)} modules to {DEST}")


if __name__ == "__main__":
    main()
