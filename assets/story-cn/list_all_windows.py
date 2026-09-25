#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""list_all_windows.py —— 列出语料里**全部**可用的「老师↔未花」交替窗口

`begin_dialogs` 需要 user(老师)/assistant(未花) 严格交替。
本脚本把每个故事里所有「以老师开头、与未花严格交替、≥2 轮」的**极大窗口**列出来，
供人工挑选（挑完用 build_preset_dialogs.py 原样导出）。

用法：<python> list_all_windows.py [--min 4]
"""
from __future__ import annotations

import json
import pathlib
import sys
from collections import defaultdict

ROOT = pathlib.Path(__file__).parent
TURNS = ROOT / "corpus" / "mika-turns.json"
SENSEI, MIKA = "老师", "未花"


def main() -> None:
    min_len = 2
    if "--min" in sys.argv:
        min_len = int(sys.argv[sys.argv.index("--min") + 1])
    turns = json.loads(TURNS.read_text(encoding="utf-8"))

    by_story: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for t in turns:
        if t["speaker"] in (SENSEI, MIKA):
            by_story[(t["cat"], t["story"])].append(t)

    total = 0
    for (cat, sid), ts in by_story.items():
        wins: list[list[dict]] = []
        i = 0
        while i < len(ts):
            if ts[i]["speaker"] != SENSEI:
                i += 1
                continue
            want, j, seq = SENSEI, i, []
            while j < len(ts) and ts[j]["speaker"] == want:
                seq.append(ts[j])
                want = MIKA if want == SENSEI else SENSEI
                j += 1
            if len(seq) % 2:
                seq = seq[:-1]
            if len(seq) >= min_len:
                wins.append(seq)
            i = max(j, i + 1)
        if not wins:
            continue
        print(f"\n===== {cat}/{sid} {ts[0]['story_title'][:24]} =====")
        for w in wins:
            total += len(w)
            print(f"  ── idx {w[0]['idx']}–{w[-1]['idx']}  {len(w)} 轮 ──")
            for k, x in enumerate(w):
                mark = "师" if x["speaker"] == SENSEI else "花"
                print(f"    {mark}| {x['text'][:66].replace(chr(10), ' / ')}")
    print(f"\n合计可用轮数：{total}")


if __name__ == "__main__":
    main()
