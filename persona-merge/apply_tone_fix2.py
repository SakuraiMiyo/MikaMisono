#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""apply_tone_fix2.py —— 清掉和新配额打架的两句残留

改完「符号」那一节之后，还有两句在旁边唱反调：

1. 语气词那节：「所以"像未花"靠的是**语气词和情绪**，不是靠多撒星星。」
   → 读起来还是"少用星星"。补一句"该挂要挂，配额见符号那节"。

2. 符号那节下面「三条写法纪律」第一条：「平均每次回复只用 **0–2 个** ☆/♪/~」
   → 和刚立的"一轮至少一个"下限直接冲突，改成 1–3 个。

用法：<python> apply_tone_fix2.py [--dry]
"""
from __future__ import annotations

import pathlib
import sys

P = pathlib.Path(__file__).parent.parent / "qq-bot" / "persona" / "bot-personality.md"
DRY = "--dry" in sys.argv
t = P.read_text(encoding="utf-8")
orig = t

EDITS = [
    ("语气词那节别唱反调",
     '''**对比一下：`☆` 只有 2.9%、`♪` 只有 0.2%——比语气词少得多。**
所以"像未花"靠的是**语气词和情绪**，不是靠多撒星星。''',
     '''**对比一下：`☆` 只有 2.9%、`♪` 只有 0.2%——比语气词少得多。**
所以"像未花"主要靠**语气词和情绪**。**但这不等于不挂符号**——
开心、撒娇、闲聊的时候该挂就挂，**一轮里至少得有一个**（配额见下面「符号」那一节）。'''),
    ("0–2 个 → 1–3 个",
     "- 平均每次回复只用 **0–2 个** ☆/♪/~；深情、道歉、恐惧的场景**一个都不用**。",
     "- 平均每次回复 **1–3 个** ☆/♪/~；深情、道歉、恐惧的场景**一个都不用**。"),
]

for name, old, new in EDITS:
    n = t.count(old)
    if n == 0:
        print(f"· {name}：锚点没命中，跳过")
        continue
    t = t.replace(old, new, 1)
    print(f"✓ {name}")

if DRY:
    print("\n（dry-run，未写盘）")
else:
    P.write_text(t, encoding="utf-8")
    print(f"\n✓ 真源：{len(orig):,} → {len(t):,} 字")
