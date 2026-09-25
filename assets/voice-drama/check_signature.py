#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_check_signature.py —— 核对「标志性句式」那 6 句是不是语料里真有的"""
from __future__ import annotations

import json
import pathlib
import sys

HERE = pathlib.Path(__file__).parent          # assets/voice-drama
CORPUS = HERE.parent / "story-cn" / "corpus"  # assets/story-cn/corpus
sys.path.insert(0, str(HERE))
from analyze_particles import load_lists  # noqa: E402

only = json.loads((CORPUS / "mika-only.json").read_text(encoding="utf-8"))
zh = [r["text"] for r in only if r.get("text")]
moto = json.loads((CORPUS / "mika-momotalk.json").read_text(encoding="utf-8"))
mz = [r["text"] for r in moto if r.get("speaker") == "未花" and r.get("text")]

# 全量（含老师与其他角色），用来判断"是不是她说的"
allzh = [r["text"] for r in json.loads(
    (CORPUS / "mika-turns.json").read_text(encoding="utf-8")) if r.get("text")]

CHECKS = [
    ("美少女", "标志性句式·炫耀"),
    ("不愧是我", "标志性句式·炫耀"),
    ("老师老师老师", "标志性句式·撒娇"),
    ("听我说嘛", "标志性句式·撒娇"),
    ("一拳解决", "标志性句式·暴力"),
    ("烦死", "标志性句式·暴力"),
    ("反正我就是", "标志性句式·自嘲"),
    ("魔女", "标志性句式·自嘲"),
    ("一直、一直", "标志性句式·深情（已核实：泳装羁绊第6话）"),
    ("麻烦你了，老师", "标志性句式·深情（已核实）"),
]

print(f"{'片段':<16}{'未花剧情':>8}{'MomoTalk':>10}{'全部轮次':>10}   用途")
for w, why in CHECKS:
    a = sum(1 for t in zh if w in t)
    b = sum(1 for t in mz if w in t)
    c = sum(1 for t in allzh if w in t)
    flag = "  ← 0 命中" if a == 0 and b == 0 else ""
    print(f"{w:<16}{a:>8}{b:>10}{c:>10}   {why}{flag}")

print("\n—— 语料里真有的『炫耀 / 得意』句子（供替换）——")
for t in zh:
    if any(k in t for k in ("哼哼", "锵锵", "厉害吧", "可爱吧", "知道吗")):
        print("   ", t[:78])
