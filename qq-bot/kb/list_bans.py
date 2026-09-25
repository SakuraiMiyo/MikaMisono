#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""list_bans.py —— 列出提示词里所有「只管禁、不管教」的地方

老师的判据（2026-09-26）：

> 「可以确实可以用这些词，但是用一下就行了，后续可以说是推进的呀。
>  可能说这种词不对啊不能用啊，你这样的话也太抽象了吧。」

也就是：**光列"不许说 X"是抽象的**——它不告诉她该做什么，
还会把她身上真实的那一面一起切掉。**该给的是行为序列。**

这个脚本把每个 `❌` 找出来，并检查它**附近有没有 `✅`**：
没有的，就是"只禁不说"，需要补正面写法。

用法：<python> list_bans.py [文件]
"""
from __future__ import annotations

import pathlib
import sys

P = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(
    r"C:\OneDrive\MikaMisono\qq-bot\persona\bot-personality.md")

lines = P.read_text(encoding="utf-8").splitlines()
print(f"{P.name}  共 {len(lines)} 行\n")

# 找出所有 ❌ 行，看前后 8 行里有没有 ✅ 或正例标记
bad = []
for i, ln in enumerate(lines):
    if "❌" not in ln:
        continue
    window = "\n".join(lines[max(0, i - 8): i + 9])
    has_positive = ("✅" in window) or ("该这么说" in window) or ("对的形状" in window)
    bad.append((i + 1, ln.strip(), has_positive))

print("❌ 行总览（★ = 附近没有 ✅，属于「只禁不说」）：")
for n, s, ok in bad:
    print(f"  {'  ' if ok else '★ '}L{n}: {s[:150]}")

only_negative = [b for b in bad if not b[2]]
print(f"\n共 {len(bad)} 条 ❌，其中 {len(only_negative)} 条附近没有 ✅")
