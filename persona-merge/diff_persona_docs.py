#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""diff_persona_docs.py —— 对比「线上真源」和「本地原件」差在哪

两个文件：

| 文件 | 角色 |
|---|---|
| `persona-merge/qq-bot-personality.merged.md` | **今天所有改动的落点**，也是线上 `system_prompt` 的真身 |
| `qq-bot/persona/bot-personality.md` | **本地原件**（提示词里自称"本真源"），已经落后 |

一旦两边分叉，下次谁从原件重建一次，今天的活儿就全丢了。这个脚本先把差距列清楚。

用法：<python> diff_persona_docs.py
"""
from __future__ import annotations

import pathlib
import re
import sys

HERE = pathlib.Path(__file__).parent
MERGED = HERE / "qq-bot-personality.merged.md"
ORIG = HERE.parent / "qq-bot" / "persona" / "bot-personality.md"

HEAD = re.compile(r"^(#{1,4})\s+(.+?)\s*$", re.M)


def sections(p: pathlib.Path) -> tuple[str, list[tuple[int, str, int]]]:
    t = p.read_text(encoding="utf-8")
    ms = list(HEAD.finditer(t))
    out = []
    for i, m in enumerate(ms):
        end = ms[i + 1].start() if i + 1 < len(ms) else len(t)
        out.append((len(m.group(1)), m.group(2), end - m.start()))
    return t, out


def main() -> None:
    tm, sm = sections(MERGED)
    to, so = sections(ORIG)
    print(f"merged : {len(tm):>7,} 字  {len(sm):>3} 个标题  {MERGED.name}")
    print(f"原件   : {len(to):>7,} 字  {len(so):>3} 个标题  {ORIG.name}")
    print(f"差     : {len(tm) - len(to):+,} 字\n")

    dm = {n: size for _, n, size in sm}
    do = {n: size for _, n, size in so}

    only_merged = [n for n in dm if n not in do]
    only_orig = [n for n in do if n not in dm]

    if only_merged:
        print(f"只在 merged 里有的标题（{len(only_merged)}）：")
        for n in only_merged:
            print(f"   + {n}  （{dm[n]:,} 字）")
    if only_orig:
        print(f"\n只在原件里有的标题（{len(only_orig)}）：")
        for n in only_orig:
            print(f"   - {n}  （{do[n]:,} 字）")

    print("\n两边都有、但字数差得多的（>120 字）：")
    rows = []
    for n in dm:
        if n in do and abs(dm[n] - do[n]) > 120:
            rows.append((abs(dm[n] - do[n]), n, do[n], dm[n]))
    for d, n, a, b in sorted(rows, reverse=True)[:30]:
        print(f"   {n}\n      原件 {a:>7,}  →  merged {b:>7,}   ({b - a:+,})")

    common = [n for n in dm if n in do and abs(dm[n] - do[n]) <= 120]
    print(f"\n字数基本一致（≤120 字差）的标题：{len(common)} 个")


if __name__ == "__main__":
    main()
