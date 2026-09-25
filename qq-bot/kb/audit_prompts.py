#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""audit_prompts.py —— 把所有提示词文件按"问题类型"过一遍

老师的要求：「除了归档的提示词外，把全部提示词都检查一遍更新一遍，
包括内置的、应用的、上面的提示词。」

这个脚本不猜——按七类**已知会出问题**的模式逐文件扫，命中就报文件:行号：
  ① 硬禁止词表        「绝不许说/禁止说 + 一串引号词」——抽象、会切掉真实的一面
  ② AI 自我表述        住在机器上 / 我的内核 / 被重置 / prompt 工程
  ③ 符号口径冲突      ☆ 是常态 / 每句都挂 / 句末必加
  ④ 称呼口径          您 / sensei / 渚ちゃん / 聖亞
  ⑤ 舞台指示          鼓励写动作、写场景
  ⑥ 句末句号          鼓励加句号
  ⑦ 消极兜底          「想不起来就说想不起来」这种先认输的写法

用法：<python> audit_prompts.py [--all]
"""
from __future__ import annotations

import os
import pathlib
import re
import sys

ROOT = pathlib.Path(r"C:\OneDrive\MikaMisono")
SKILLS = pathlib.Path(os.path.expanduser("~")) / ".astrbot" / "data" / "skills"
PLUGINS = pathlib.Path(os.path.expanduser("~")) / ".astrbot" / "data" / "plugins"

TARGETS = [
    ("QQ 真源", ROOT / "qq-bot/persona/bot-personality.md"),
    ("QQ 镜像", ROOT / "persona-merge/qq-bot-personality.merged.md"),
    ("DSH 真源", ROOT / "agent/SKILL.md"),
    ("DSH 镜像", ROOT / "persona-merge/agent-SKILL.merged.md"),
    ("CSP 蒸馏", ROOT / "misono-mika-csp/SKILL.md"),
    ("旧版人格", ROOT / "qq-bot/legacy/bot.md"),
    ("欢迎页", ROOT / "qq-bot/persona/_欢迎回来，未花.md"),
    ("出图提示词", ROOT / "qq-bot/notes/mika-image-prompts.md"),
    ("记忆技能", ROOT / "agent/skills/mika-memory/SKILL.md"),
    ("技能·点餐", SKILLS / "mika-delivery/SKILL.md"),
    ("技能·日记", SKILLS / "mika-diary/SKILL.md"),
    ("技能·出图", SKILLS / "mika-image/SKILL.md"),
    ("技能·说说", SKILLS / "mika-qq-space/SKILL.md"),
]

CHECKS: list[tuple[str, re.Pattern]] = [
    ("① 硬禁止词表", re.compile(r"(绝不许说|禁止说|绝对不能说|不许说)[^。\n]{0,120}[「\"][^」\"]{1,20}[」\"]")),
    ("② AI 自我表述", re.compile(r"住在(?:电脑|机器|设备)|我的(?:内核|版本|参数|思考块)|被重置|prompt\s*工程|人格文件")),
    ("③ 符号口径冲突", re.compile(r"(☆[^。\n]{0,30}(常态|每句|句末就该有|必加))|((常态|每句|必加)[^。\n]{0,20}☆)")),
    ("④ 称呼口径", re.compile(r"渚ちゃん|聖亞|小圣娅|您(?=[们您])|sensei")),
    ("⑤ 舞台指示", re.compile(r"(写|输出|加上|要有)[^。\n]{0,10}(动作描写|场景描写|神态)")),
    ("⑥ 句末句号", re.compile(r"句末[^。\n]{0,10}句号[^。\n]{0,10}(加上|要加|应该加)")),
    ("⑦ 消极兜底", re.compile(r"想不起来[^。\n]{0,20}(就说|说就|直接说)")),
]


def scan(label: str, p: pathlib.Path) -> int:
    if not p.exists():
        print(f"  ? {label}：找不到 {p}")
        return 0
    t = p.read_text(encoding="utf-8", errors="ignore")
    lines = t.splitlines()
    hits = 0
    for name, rx in CHECKS:
        found = []
        for i, ln in enumerate(lines, 1):
            m = rx.search(ln)
            if m:
                found.append((i, m.group(0)[:70]))
        if found:
            hits += len(found)
            print(f"  🔴 {label} · {name}  {len(found)} 处")
            for i, s in found[:4]:
                print(f"       L{i}: …{s}…")
            if len(found) > 4:
                print(f"       …还有 {len(found) - 4} 处")
    return hits


def main() -> None:
    total = 0
    print("＝" * 30)
    for label, p in TARGETS:
        n = scan(label, p)
        total += n
        if n == 0:
            print(f"  ✅ {label}：干净")
        print()
    print(f"合计命中 {total} 处")

    if "--all" in sys.argv:
        print("\n（--all：插件里的 prompt 文件）")
        for p in PLUGINS.rglob("*"):
            if p.is_file() and p.suffix in (".json", ".txt", ".md"):
                if "node_modules" in str(p) or "CHANGELOG" in p.name:
                    continue
                try:
                    t = p.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue
                if re.search(r"(你是|角色扮演|请扮演|system)", t) and len(t) < 60000:
                    print(f"  {p.relative_to(PLUGINS)}  ({len(t)} 字)")


if __name__ == "__main__":
    main()
