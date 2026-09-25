# -*- coding: utf-8 -*-
"""diagnose_card.py —— 逐卡定位"数字新增/丢失"到底出在哪一句

校验器只报「数字新增 {'35': 1}」，不说是哪来的。改写者拿到这句话会很懵——
这个脚本把两边**哪些片段含这个数字**打出来，一眼就能看出是重复叙述还是真丢了。

用法：<python> diagnose_card.py 2026-09-15 [2026-07-06 ...]
"""
import json
import pathlib
import re
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")

BAK = pathlib.Path(r"C:\OneDrive\MikaMisono\_archive-20260924\cards-before-voicefix-20260926-014224\cards")
NEW = pathlib.Path(r"C:\OneDrive\MikaMisono\agent\memory\cards")


def field_text(card: dict) -> dict[str, str]:
    out = {}
    for k, v in card.items():
        if k == "date":
            continue
        out[k] = "\n".join(map(str, v)) if isinstance(v, list) else str(v)
    return out


def nums(s: str) -> Counter:
    return Counter(re.findall(r"\d+", s.replace(" ", "")))


for date in sys.argv[1:]:
    b = json.loads((BAK / f"{date}.json").read_text(encoding="utf-8"))
    n = json.loads((NEW / f"{date}.json").read_text(encoding="utf-8"))
    fb, fa = field_text(b), field_text(n)

    tot_b = Counter()
    tot_a = Counter()
    for t in fb.values():
        tot_b += nums(t)
    for t in fa.values():
        tot_a += nums(t)

    added = tot_a - tot_b
    lost = tot_b - tot_a
    print(f"\n{'='*70}\n{date}　新增 {dict(added) or '无'}　丢失 {dict(lost) or '无'}\n{'='*70}")

    for num in list(added) + list(lost):
        print(f"\n  ── 数字 {num} ──")
        for tag, f in (("改前", fb), ("改后", fa)):
            cnt = 0
            for k, t in f.items():
                if num in t.replace(" ", ""):
                    cnt += 1
            print(f"   {tag}总计 {tot_b[num] if tag=='改前' else tot_a[num]} 次，分布在：")
            for k, t in f.items():
                hits = re.findall(rf".{{0,16}}{re.escape(num)}.{{0,16}}", t.replace(" ", ""))
                if hits:
                    print(f"      [{k}]")
                    for h in hits:
                        print(f"          …{h}…")
