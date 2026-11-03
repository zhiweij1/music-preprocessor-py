# music-preprocessor (Python edition)

简谱 DSL → **LilyPond** / **MusicXML** / **MuseScore 4**（`.mscz` / `.pdf` / `.png`）。

C++ 版的功能等价移植（lexer / parser / IR / LilyPond 后端保持一致），新增 MusicXML 后端和
MuseScore 调用，用来在 Windows（只有 MuseScore、没有 LilyPond）上出 lead sheet。

📖 **简谱 DSL 语法参考：[docs/DSL.md](docs/DSL.md)**（速查卡 + 完整记号表 + 示例）

## 安装 / 依赖

| 依赖 | 说明 |
|---|---|
| Python 3.9+ | 必填 |
| MuseScore 4 | 仅 `-f mscz/pdf/png` 需要；自动在 `C:\Program Files\MuseScore 4\bin\MuseScore4.exe` 等位置查找 |

没有 MuseScore 时，仍然可以输出 `.ly` 和 `.musicxml`（MuseScore 手工打开也行）。

## 用法

```bash
# 1) 输出 LilyPond（默认，保持旧行为：无 -o 时打到 stdout）
python mpp.py song.dsl
python mpp.py song.dsl -o song.ly

# 2) 输出 MusicXML
python mpp.py song.dsl -f musicxml -o song.musicxml

# 3) 直接出 MuseScore 文件（自动套 Jazz Lead Sheet 样式）
python mpp.py song.dsl -f mscz
python mpp.py song.dsl -f pdf
python mpp.py song.dsl -f mscz,pdf --keep-xml
```

Windows 上也可以直接双击/命令行用 `mpp.cmd`：

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

## 与 C++ 版的差异

| 项 | 说明 |
|---|---|
| LilyPond 输出 | 结构、空白与 C++ 版基本一致（和弦 `g4:7`、`\partial` 等） |
| **八度修正** | C++ 版在非 C 调时 4–7 级会低一个八度（Bb 调 `1 2 3 4` = Bb4 C4 D4 Eb4）；Python 版已修正为 Bb4 C5 D5 Eb5 |
| `(2` / `2)` 贴写圆滑线 | Python 版额外支持把括号贴在音符上（`5 2 ~ q2`、`(2 q2)`），C++ 版只认空格分开的 `(` `)` |
| `\|\|` 双小节线 | Python 版支持（`\|\|` 渲染成 double bar；也支持 `\|.` `.\|`），C++ 版当错误 |
| `LP:` 块 | MusicXML 后端没有对应概念 → 忽略；LilyPond 后端原样保留 |
| `\命令` / `^"文字"` | MusicXML 后端只映射 `\break`、`\bar "…"`、`^"…"`/`_"…"`，其余给 warning；LilyPond 后端原样保留 |
| 和弦写法 | 交给 MuseScore 解析；`C6/9` 会正确保留，`G7sus4` 会被规范成 `G7sus⁴` |
| 反复 `R{}` / `A{}` | 仍然报 “Phase 2” 错误（与 C++ 版一致） |

## 目录结构

```
music-preprocessor-py/
├── mpp.py                 # 入口
├── mpp/
│   ├── lexer.py           # 词法
│   ├── parser.py          # 语法 → IR
│   ├── ir.py              # IR 数据结构
│   ├── lilypond.py        # LilyPond 后端
│   ├── musicxml.py        # MusicXML 后端（lead sheet）
│   ├── musescore.py       # MuseScore CLI 调用
│   └── cli.py             # 命令行
├── assets/jazz-lead-sheet.mss   # 从 MuseScore 模板复制的样式
└── tests/                 # 21 个用例 + 19 个 demo 作为 fixtures
```

## 测试

```bash
python -m unittest discover -s tests
```

覆盖：19 个 demo 全部转换、音高/调号/和弦/歌词/弱起/连音线、错误输入、CLI 行为。
