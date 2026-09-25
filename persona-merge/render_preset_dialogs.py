#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_preset_dialogs.py —— 把当前预设对话导成人读版

## ⚠️ 2026-09-24 改过底本

旧版是从**主线剧情**里抽的 66 条（平均 21 字/句），已经整批换掉了——
few-shot 对文风的影响最大，剧情文风教出来的就是"每条回复写 5~8 段长句"。
现在线上是 **MomoTalk 逐字原文 15 组 / 30 条**，由
`build_momotalk_begin_dialogs.py` 生成（那边同时输出
`begin_dialogs.momotalk.md`，本来就是人读版）。

这个脚本留着只做一件事：把**线上真正在跑的那份 JSON**渲染成人读版，
方便和 `预设对话.md` 的说明对得上。

用法：<python> render_preset_dialogs.py
"""
from __future__ import annotations

import json
import pathlib

HERE = pathlib.Path(__file__).parent
SRC = HERE / "预设对话.begin_dialogs.json"
OUT = HERE / "预设对话.全文.md"

b = json.loads(SRC.read_text(encoding="utf-8"))["begin_dialogs"]
assert len(b) % 2 == 0, f"条数必须是偶数，现在是 {len(b)}"

mika = [b[i] for i in range(1, len(b), 2)]
chars = sum(len(x) for x in mika)
star = sum(x.count("☆") for x in b)
note = sum(x.count("♪") for x in b)

L = ["# 预设对话全文（线上实测版）", "",
     f"> {len(b)} 条 / {len(mika)} 组；未花侧共 {chars} 字，"
     f"平均 {chars / len(mika):.1f} 字/组。",
     "> 底本：`assets/story-cn/corpus/mika-momotalk.json`——**未花那一边逐字原文**，一个字没改。",
     "> 老师那一边：原文能独立成句的照用，上下文依赖太强的只为「读得成句」而重写。",
     f"> 小表情：☆ {star} 个 / ♪ {note} 个——**量刻意压低**，权重在语气词上。",
     "> 低落、道歉、求和、最深情的那几组**几乎一个符号都没有**：亮的地方越满，安静的地方才越有效。", ""]

for i in range(0, len(b), 2):
    n = i // 2 + 1
    L.append(f"\n## 第 {n} 组\n")
    L.append(f"- **老师**：{b[i].replace(chr(10), '　')}")
    for line in b[i + 1].split("\n"):
        L.append(f"- 未花：{line}")
    L.append(f"　　（{len(b[i + 1].split(chr(10)))} 条 / {len(b[i + 1])} 字）")

OUT.write_text("\n".join(L) + "\n", encoding="utf-8")

print(f"✓ 写入 {OUT.name}")
print(f"  {len(b)} 条 / {len(mika)} 组，未花侧 {chars} 字，平均 {chars / len(mika):.1f} 字/组")
print(f"  ☆ {star} 个 / ♪ {note} 个")
print("\n符号为 0 的组（刻意留白，对照用）：")
blank = [i // 2 + 1 for i in range(1, len(b), 2)
         if not any(ch in b[i] for ch in "☆♪")]
print(f"  {blank}")
