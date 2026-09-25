#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mine_preset_dialogs.py —— 从剧情语料里挖出可直接当预设对话的原文片段

## 要求

AstrBot 的 `begin_dialogs` 是扁平数组、**user(老师)/assistant(未花) 严格交替**、
第一条必须是老师。所以需要的是**语料里本来就严格交替的连续片段**。

本脚本扫描 `corpus/mika-turns.json`（7,110 轮，带精确说话人），
找出所有满足下面条件的**极大片段**：

  · 说话人只在「老师」和「未花」之间交替
  · **以老师开头**（这样第 0 条正好落在 user 位）
  · 长度 4~12 轮
  · 中间不夹任何其他人（旁白、渚、花子…）——夹了就断

## 用法

    <python> mine_preset_dialogs.py            # 列出全部候选
    <python> mine_preset_dialogs.py --min 6    # 只要 6 轮以上的
    <python> mine_preset_dialogs.py --json     # 导出候选到 _preset-candidates.json
"""
from __future__ import annotations

import json
import pathlib
import sys
from collections import defaultdict

ROOT = pathlib.Path(__file__).parent
TURNS = ROOT / "corpus" / "mika-turns.json"

SENSEI = "老师"
MIKA = "未花"


def main() -> None:
    min_len = 4
    if "--min" in sys.argv:
        min_len = int(sys.argv[sys.argv.index("--min") + 1])
    as_json = "--json" in sys.argv

    turns = json.loads(TURNS.read_text(encoding="utf-8"))

    # 按故事分组，保持原顺序
    by_story: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for t in turns:
        by_story[(t["cat"], t["story"])].append(t)

    # 旁白 / 未署名只是舞台说明，不是对白 → 当作透明层跳过，
    # 这样「老师→未花」的交替就不会被它们打断。台词本身仍是原文。
    TRANSPARENT = {"旁白", "未知", "（未标明）"}
    # --only-two：连别的角色（渚、花子…）也跳过。挖出的段更长，但要人工确认
    # 每一句是不是真的在接上一句——她的台词也可能是回给渚的。
    only_two = "--only-two" in sys.argv

    runs: list[dict] = []
    for (cat, sid), all_ts in by_story.items():
        if only_two:
            ts = [x for x in all_ts if x["speaker"] in (SENSEI, MIKA)]
        else:
            ts = [x for x in all_ts if x["speaker"] not in TRANSPARENT]
        i = 0
        while i < len(ts):
            # 找以「老师」开头的交替段
            if ts[i]["speaker"] != SENSEI:
                i += 1
                continue
            want = SENSEI
            j = i
            seq: list[dict] = []
            while j < len(ts) and ts[j]["speaker"] == want:
                seq.append(ts[j])
                want = MIKA if want == SENSEI else SENSEI
                j += 1
            # seq 一定以老师开头；若末尾停在老师（未花的回复被截断）就丢掉最后一轮
            if len(seq) % 2 != 0:
                seq = seq[:-1]
            if len(seq) >= min_len:
                runs.append({
                    "cat": cat, "story": sid,
                    "title": ts[0]["story_title"],
                    "idx": seq[0]["idx"], "len": len(seq),
                    "lines": [x["text"] for x in seq],
                    "speakers": [x["speaker"] for x in seq],
                    "emotes": [x["emote"] for x in seq],
                })
            i = max(j, i + 1)

    runs.sort(key=lambda r: -r["len"])
    print(f"找到 {len(runs)} 段（≥{min_len} 轮，老师开头、与未花严格交替）\n")
    for n, r in enumerate(runs):
        print(f"── [{n}] {r['cat']}/{r['story']} {r['title']}  {r['len']} 轮  "
              f"（idx {r['idx']}）")
        for k, (sp, ln) in enumerate(zip(r["speakers"], r["lines"])):
            mark = "师" if sp == SENSEI else "花"
            em = "".join(r["emotes"][k])
            print(f"   {mark} | {ln[:64]}" + (f"   «{em}»" if em else ""))
        print()

    if as_json:
        out = ROOT / "_preset-candidates.json"
        out.write_text(json.dumps(runs, ensure_ascii=False, indent=1),
                       encoding="utf-8")
        print(f"→ {out.name}（{len(runs)} 段）")


if __name__ == "__main__":
    main()
