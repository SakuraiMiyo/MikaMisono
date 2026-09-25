#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_stats_dialogs.py —— 打印线上那份 begin_dialogs 的各项统计（给文档用）"""
from __future__ import annotations

import json
import pathlib

HERE = pathlib.Path(__file__).parent


def stat(name: str, b: list[str]) -> None:
    mika = [b[i] for i in range(1, len(b), 2)]
    chars = sum(len(x) for x in mika)
    blank = [i // 2 + 1 for i in range(1, len(b), 2)
             if not any(c in b[i] for c in "☆♪")]
    print(f"{name}: {len(b)} 条 / {len(mika)} 组 | 未花侧 {chars} 字 | "
          f"平均 {chars / len(mika):.1f} 字/组 | ☆ {sum(x.count('☆') for x in b)} "
          f"♪ {sum(x.count('♪') for x in b)} | 无符号组 {len(blank)}/{len(mika)} {blank}")
    burst = [len(b[i].split("\n")) for i in range(1, len(b), 2)]
    print(f"   连发条数：最多 {max(burst)}，平均 {sum(burst) / len(burst):.2f}")


for name, f in (("MomoTalk", "begin_dialogs.momotalk.json"),
                ("剧情口癖", "begin_dialogs.catchphrase.json"),
                ("线上合并版", "预设对话.begin_dialogs.json")):
    p = HERE / f
    if p.exists():
        stat(name, json.loads(p.read_text(encoding="utf-8"))["begin_dialogs"])
print(f"\nJSON 体积：{(HERE / '预设对话.begin_dialogs.json').stat().st_size} 字节")
