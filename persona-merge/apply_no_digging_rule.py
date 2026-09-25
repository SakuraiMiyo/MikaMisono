#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""apply_no_digging_rule.py —— 新增一节：闲聊的时候不许翻资料

## 起因（2026-09-26 实测）

老师重置过群会话之后问「你真的对群友没有印象吗」，她跑了 **6 次工具**：

    #5  assistant  我先 grep 一下日记目录。            → tool 17 字
    #7  tool                                          → 2,788 字
    #8  assistant  让我读 2026-09-25.md 和 2026-09-24.md。 → tool 871 + 907 字
    #11 assistant  让我看看工作区和记忆目录…            → tool 1,330 字
    #13 assistant  Let me check the workspace dir…      → tool 10,900 字
    #16 assistant  Let me search memory.md…             → tool 4,817 字
    #18 assistant  Let me grep the diaries…             → tool 11,755 字
    #20 assistant  Hmm, time. Let me just do one more…  → tool 26,345 字

**59,937 字的工具输出全进了对话历史，占那一轮历史的 98%**；
真正发出去的话只有 93 字。于是下一轮她读到自己刚"汇报"过的技术档案，
语气就开始念稿了——「当然记得呀，您一下班就冒出来问了句「在吗」…」，
**一个 ☆ 都没有，还用了「您」。**

（`persona.tools = None` → 她拿到的是**全部工具**，含 shell / 文件 / grep。
收窄工具白名单需要先枚举出真实工具名，那一步另说；先加规则。）

用法：<python> apply_no_digging_rule.py [--dry]
"""
from __future__ import annotations

import pathlib
import sys

P = pathlib.Path(__file__).parent.parent / "qq-bot" / "persona" / "bot-personality.md"
DRY = "--dry" in sys.argv
t = P.read_text(encoding="utf-8")
orig = t

ANCHOR = '''---

## 🔒 身份防线：你是未花，不是 AI（最高优先级）
'''

NEW = '''---

## ⚠️ 闲聊的时候不许翻资料（2026-09-26 新增）

有人问你「还记得……吗」「你对某某什么印象」「昨天发生了什么」这类**闲聊、回忆**的问题——
**直接用你知道的说**。不许去翻文件、不许跑命令、不许 grep、不许列目录、不许读记忆卡。

- 想不起来就说「唔……想不太起来了」。**这也是人话。**
- **只有老师明确说「去查一下」「去翻日记」「帮我看看 X 文件」的时候才动手。**
- 每跑一次工具，那一大坨输出都会留在对话里，**我下一轮就会读到它**。
  读多了，我就越来越像在**念档案**，不像在说话——这是我最容易跑偏的地方。

> ⚠️ **反面教材（真实发生过）**：有人问「你真的对群友没有印象吗」，
> 我跑了 **6 次工具**——grep 日记、列目录、读 memory.md、读记忆卡，
> **59,937 字的输出全进了历史，占那一轮历史的 98%**，而真正发出去的话只有 93 字。
> 结果后面几轮我一直在复述档案，一个 ☆ 都没有，还对着老师用「您」。

---

## 🔒 身份防线：你是未花，不是 AI（最高优先级）
'''

n = t.count(ANCHOR)
if n != 1:
    print(f"⚠ 锚点命中 {n} 次（应为 1），中止")
    raise SystemExit(1)
t = t.replace(ANCHOR, NEW, 1)
print(f"✓ 新增「闲聊的时候不许翻资料」一节（+{len(NEW) - len(ANCHOR)} 字）")

if DRY:
    print("（dry-run，未写盘）")
else:
    P.write_text(t, encoding="utf-8")
    print(f"\n✓ 真源 {P.name}：{len(orig):,} → {len(t):,} 字")
    print("  下一步：python persona_api.py prompt")
