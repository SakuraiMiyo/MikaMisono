#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""apply_chinese_names.py —— 把旧称呼统一成中文（小渚 / 小圣娅）

老师 2026-09-24 定：**不用日文后缀，直接中文**——
桐藤渚 → **小渚**，百合园圣娅 → **小圣娅**。

⚠️ 只改**称呼规范**（表格、系统树、语气示例），
**绝不动台词引文**——比如 33170 的原话「对不起，圣娅酱…………」是语料原文，改了就成篡改。
所以这里全部用**精确字面替换**，不做全局 圣娅→小圣娅。

用法：<python> apply_chinese_names.py [--dry]
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).parent.parent
DRY = "--dry" in sys.argv

# (相对路径, 原文, 替换)
EDITS: list[tuple[str, str, str]] = [
    # ── QQ 人格提示词（线上）──────────────────────────────
    ("persona-merge/qq-bot-personality.merged.md",
     "| 百合园圣娅 | **圣娅** | ⚠️ 是「圣**娅**」不是「圣亚」 |",
     "| 百合园圣娅 | **小圣娅** | ⚠️ 是「圣**娅**」不是「圣亚」；加「小」是亲昵 |"),
    ("persona-merge/qq-bot-personality.merged.md",
     "| **圣亚** | 愧疚最集中的一段关系",
     "| **小圣娅** | 愧疚最集中的一段关系"),

    # ── DSH 链路 prompt ───────────────────────────────────
    ("agent/SKILL.md", "| 桐藤渚 | 渚ちゃん |", "| 桐藤渚 | 小渚 |"),
    ("agent/SKILL.md", "| 百合园圣亚 | 聖亞ちゃん |", "| 百合园圣亚 | 小圣娅 |"),
    ("persona-merge/agent-SKILL.merged.md",
     "| 桐藤渚 | 渚ちゃん |", "| 桐藤渚 | 小渚 |"),
    ("persona-merge/agent-SKILL.merged.md",
     "| 百合园圣亚 | 聖亞ちゃん |", "| 百合园圣亚 | 小圣娅 |"),

    # ── 知识库底本 ────────────────────────────────────────
    ("agent/knowledge/relationships.md",
     '│   "渚ちゃん"   │   │  "聖亞ちゃん" │   │   "小春ちゃん"   │',
     '│    "小渚"      │   │   "小圣娅"    │   │    "小春"        │'),
    ("agent/knowledge/relationships.md",
     "| **未花的称呼** | 渚ちゃん |",
     "| **未花的称呼** | 小渚 |"),
    ("agent/knowledge/relationships.md",
     "| **未花的称呼** | 聖亞ちゃん |",
     "| **未花的称呼** | 小圣娅 |"),
    ("agent/knowledge/relationships.md",
     '| 渚 | 亲昵+捉弄 | "渚ちゃん又皱着眉头了呢~♪" |',
     '| 小渚 | 亲昵+捉弄 | "小渚又皱着眉头了呢~♪" |'),
    ("agent/knowledge/relationships.md",
     '| 圣亚 | 温柔+愧疚 | "聖亞ちゃん……她总是那么安静。" |',
     '| 小圣娅 | 温柔+愧疚 | "小圣娅……她总是那么安静。" |'),
    ("agent/knowledge/dialogue-corpus.md",
     "| 桐藤渚 | **小渚** 64 ／ 渚酱 20 | 84 | `渚ちゃん` 在中文语料里 0 命中 |",
     "| 桐藤渚 | **小渚** 64 ／ 渚酱 20 | 84 | `渚ちゃん` 在中文语料里 0 命中；**统一用小渚** |"),
    ("agent/knowledge/dialogue-corpus.md",
     "| 百合园圣亚 | **圣娅** | 31 | ⚠️ 官方简中是「圣**娅**」，不是「圣亚」 |",
     "| 百合园圣亚 | **小圣娅** | 31+1 | ⚠️ 官方简中是「圣**娅**」，不是「圣亚」；"
     "称「小圣娅」（语料里 `小圣娅` 41×、`圣娅酱` 也真实存在） |"),

    # ── 旧版人格稿（保持同步，避免以后又抄回去）──────────
    ("qq-bot/persona/bot-personality.md", "| 桐藤渚 | 渚ちゃん |", "| 桐藤渚 | 小渚 |"),
    ("qq-bot/persona/bot-personality.md", "| 百合园圣亚 | 聖亞ちゃん |", "| 百合园圣亚 | 小圣娅 |"),
    ("qq-bot/persona/bot-personality.md",
     "渚（渚ちゃん）—— 青梅竹马，爱逗她，关键时刻第一个站到她那边。",
     "小渚 —— 青梅竹马，爱逗她，关键时刻第一个站到她那边。"),
    ("qq-bot/persona/bot-personality.md",
     "圣亚（聖亞ちゃん）—— 愧疚最深的一环。她早就预知了一切，却选择等我回来。",
     "小圣娅 —— 愧疚最深的一环。她早就预知了一切，却选择等我回来。"),
    ("qq-bot/legacy/bot.md",
     "政变是这样、和聖亞ちゃん的关系是这样、",
     "政变是这样、和小圣娅的关系是这样、"),
]


def main() -> None:
    changed = skipped = missing = 0
    for rel, old, new in EDITS:
        p = ROOT / rel
        if not p.exists():
            print(f"  ? 找不到 {rel}")
            missing += 1
            continue
        t = p.read_text(encoding="utf-8")
        n = t.count(old)
        if n == 0:
            if new in t:
                skipped += 1
                continue
            print(f"  ⚠ {rel}：锚点 0 命中且目标也不在 → 手工看一眼\n      {old[:60]}")
            missing += 1
            continue
        t = t.replace(old, new)
        if not DRY:
            p.write_text(t, encoding="utf-8")
        print(f"  ✓ {rel}（{n} 处）")
        changed += 1
    print(f"\n{'（dry-run，未写盘）' if DRY else ''}"
          f"改了 {changed} 处，已是目标态 {skipped} 处，需人工 {missing} 处")


if __name__ == "__main__":
    main()
