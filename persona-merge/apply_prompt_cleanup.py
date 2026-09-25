#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""apply_prompt_cleanup.py —— 同步之后剩下的几处小毛病

按老师要求「检查一下需要修改的点」，逐条扫过之后确认要改的只有两处（其余命中都是
规则里的 ❌ 反例，是故意留的）：

1. **第 29 行**「你擅长**调用电脑里面的 comfort ui 工具**帮老师生成任何老师想看到的图」
   —— `comfort ui` 是 ComfyUI 的错拼；而且「调用…工具」是机器口吻，
   和身份防线那条「不要主动说 ComfyUI、工作流、采样器」自相矛盾。

2. **第 42 行**「性格在线。**非常喜欢用 ☆♪~**，该自恋自恋」
   —— 和实测表（`☆` 2.9%、`♪` 0.2%）以及「☆ 是点缀不是底色」那一节打架。

⚠️ 现在真源是 `qq-bot/persona/bot-personality.md`；改完跑 `persona_api.py prompt`，
它会顺手把镜像 `persona-merge/qq-bot-personality.merged.md` 写成同一份。

用法：<python> apply_prompt_cleanup.py [--dry]
"""
from __future__ import annotations

import pathlib
import sys

P = pathlib.Path(__file__).parent.parent / "qq-bot" / "persona" / "bot-personality.md"
DRY = "--dry" in sys.argv
t = P.read_text(encoding="utf-8")
orig = t

EDITS = [
    (
        "ComfyUI 错拼 + 机器口吻",
        "- 你擅长调用电脑里面的 comfort ui 工具帮老师生成任何老师想看到的图",
        "- 老师电脑上那个画图的你用得比谁都熟——他要什么图你都能给他弄出来（**对外不要报工具名**，一句「老师电脑上那个画图的」就够）",
    ),
    (
        "☆♪~ 频率和实测打架",
        "- 性格在线。非常喜欢用 ☆♪~，该自恋自恋",
        "- 性格在线，该自恋就自恋。`☆ ♪ ~` 可以用，但那是**点缀**——别每句都挂（实测 `☆` 只占 2.9%）",
    ),
]

for name, old, new in EDITS:
    n = t.count(old)
    if n == 0:
        print(f"· {name}：已是目标态或找不到，跳过")
        continue
    t = t.replace(old, new)
    print(f"✓ {name}（{n} 处）")

if DRY:
    print("\n（dry-run，未写盘）")
else:
    P.write_text(t, encoding="utf-8")
    print(f"\n✓ {P.relative_to(P.parents[2])}：{len(orig):,} → {len(t):,} 字")
