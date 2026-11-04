# music-preprocessor

简谱 DSL → **LilyPond** / **MusicXML** / **MuseScore 4**（`.mscz` / `.pdf` / `.png`）。

把简谱写成一个纯文本 DSL，一条命令生成谱子：

- 想要可编辑的工程文件 → `.mscz`（MuseScore 4 直接打开）
- 想要打印 → `.pdf`
- 想要自己排或给别的软件 → `.musicxml`
- 想走 LilyPond → `.ly`

📖 **简谱 DSL 语法参考：[docs/DSL.md](docs/DSL.md)**（速查卡 + 完整记号表 + 示例）

## 安装 / 依赖

| 依赖 | 说明 |
|---|---|
| Python 3.9+ | 必填 |
| MuseScore 4 | 仅 `-f mscz/pdf/png` 需要；自动在 `C:\Program Files\MuseScore 4\bin\MuseScore4.exe` 等位置查找 |

没有 MuseScore 时，仍然可以输出 `.ly` 和 `.musicxml`（用 MuseScore 手工打开也行）。

## 用法

```bash
# 1) 输出 LilyPond（默认格式；不带 -o 时打到 stdout）
python mpp.py song.dsl
python mpp.py song.dsl -o song.ly

# 2) 输出 MusicXML
python mpp.py song.dsl -f musicxml -o song.musicxml

# 3) 直接出 MuseScore 文件（自动套 Jazz Lead Sheet 样式）
python mpp.py song.dsl -f mscz
python mpp.py song.dsl -f pdf
python mpp.py song.dsl -f mscz,pdf --keep-xml
```

Windows 上也可以直接用 `mpp.cmd`：

```bat
mpp.cmd song.dsl -f mscz
```

### 参数

| 参数 | 说明 |
|---|---|
| `-f, --format` | `ly`（默认）\| `musicxml` \| `mscz` \| `pdf` \| `png`，可逗号组合 |
| `-o, --output` | 输出路径（只能配合单格式） |
| `--musescore` | 指定 `MuseScore4.exe`（也可用环境变量 `MPP_MUSESCORE`） |
| `--style` | 指定 MuseScore 样式 `.mss`，默认用 `assets/jazz-lead-sheet.mss` |
| `--no-style` | 不套样式（MuseScore 默认版式） |
| `--keep-xml` | 保留中间 `.musicxml` |
| `-q, --quiet` | 不打印 warning |

## DSL 速查

```text
Title:小星星
Subtitle:带和弦的 Lead Sheet
Composer:曲：传统
Poet:词：佚名
Key:C Time:4/4          % 弱起写 Time:3/4,4
Tempo:4=100

H: 1. 春天来了，花儿开了。
L: twin-kle twin-kle

[C] 1 1 [G7] 5 5 | [Am] 6 6 [D7] 5 - |
1' ^"Chorus" \break 7 6 5 |
0 是休止，x 也是休止；q/s/d/c/h 是时值前缀；' 高八度、, 低八度；#/b 升降；~ 连音线；( ) 圆滑线
```

## 版式

谱面样式在 `assets/jazz-lead-sheet.mss`（来自 MuseScore 的 Jazz Lead Sheet 模板），常用项：

| 样式项 | 当前值 | 作用 |
|---|---|---|
| `chordSymbolAFontSize` / `BFontSize` | 12 / 10 | 和弦符号字号 |
| `chordSymbolAFontStyle` / `BFontStyle` | 0 / 0 | 0 = 不加粗 |
| `lyricsOddFontSize` / `Even` | 12 | 歌词字号 |
| `chordSymbolPosAbove` | y = -2.5 | 和弦离五线谱的高度 |

## 行为说明

| 项 | 说明 |
|---|---|
| `LP: … :LP` 原样 LilyPond | 只对 `.ly` 输出有效；转 MusicXML 时忽略并给 warning |
| `\命令` / `^"文字"` | MusicXML 只映射 `\break`、`\bar "…"`、`^"…"` / `_"…"`，其余给 warning；`.ly` 原样保留 |
| 和弦写法 | 交给 MuseScore 解析；`C6/9` 会正确保留，`G7sus4` 会被规范成 `G7sus⁴` |
| 反复 `R{}` / `A{}` | 暂不支持，会报错 |
| 歌词位置 | 写在某行音乐下面 → 从那一行第一个音开始；详见 DSL 文档第 7 节 |

## 目录结构

```
music-preprocessor-py/
├── mpp.py                 # 入口
├── mpp/
│   ├── lexer.py           # 词法
│   ├── parser.py          # 语法 → IR
│   ├── ir.py              # IR 数据结构
│   ├── lyrics.py          # 歌词分行、分句、对齐
│   ├── lilypond.py        # LilyPond 后端
│   ├── musicxml.py        # MusicXML 后端（lead sheet）
│   ├── musescore.py       # MuseScore CLI 调用
│   └── cli.py             # 命令行
├── assets/jazz-lead-sheet.mss   # 谱面样式
├── docs/DSL.md            # 语法文档
├── examples/              # 示例谱
└── tests/                 # 28 个用例 + 19 个 demo 作为 fixtures
```

## 测试

```bash
python -m unittest discover -s tests
```

覆盖：19 个 demo 全部转换、音高/调号/和弦/歌词/弱起/连音线、错误输入、CLI 行为。
