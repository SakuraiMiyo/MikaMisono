#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""shy_check.py —— 日记改写有没有把「害羞」写过头

老师反馈：「群里面消息看起来还是不是很能放开，老是害羞啥的。」

怀疑点：改写时为了补"人味"，代理们可能加了太多**怯生生**的标记——
`呜`、`害羞`、`脸红`、`捂脸`、`不好意思`、`（＞＜）`——
加上省略号密度从 3.3% 拉到 27%，整体读起来就变成"一直很怯"。

未花不是怯，她是**先亮后软**：嘴上炸毛、自恋、逞强，糖藏在底下。
所以这个脚本对比「怯的标记」和「张扬的标记」在改前 / 改后各占多少。

用法：<python> shy_check.py
"""
from __future__ import annotations

import pathlib

DIARY = pathlib.Path(r"C:\OneDrive\MikaMisono\agent\memory\diary")
ROOT = pathlib.Path(r"C:\OneDrive\MikaMisono\_archive-20260924")
cands = sorted(ROOT.glob("diary-before-voicefix-*"))
BAK = cands[-1] if cands else None

SHY = ["呜", "害羞", "脸红", "捂脸", "不好意思", "（＞＜）", "怯", "小声",
       "缩", "埋进", "不敢", "别过头", "低下头"]
BOLD = ["哼", "☆", "自恋", "得意", "才不", "当然", "哼哼", "厉害吧", "可爱吧",
        "☆", "最", "超", "我这样的"]
SOFT = ["老师", "老公", "抱", "暖", "亲", "喜欢", "爱"]


def count(texts: list[str], keys: list[str]) -> dict[str, int]:
    return {k: sum(t.count(k) for t in texts) for k in keys}


def main() -> None:
    if not BAK:
        print("找不到备份")
        return
    old = [p.read_text(encoding="utf-8", errors="ignore") for p in sorted(BAK.glob("*.md"))]
    new = [p.read_text(encoding="utf-8", errors="ignore") for p in sorted(DIARY.glob("*.md"))]
    no, nn = sum(len(t) for t in old), sum(len(t) for t in new)
    print(f"改前 {len(old)} 篇 / {no:,} 字      改后 {len(new)} 篇 / {nn:,} 字\n")

    for label, keys in (("怯 / 害羞 类", SHY), ("张扬 / 自恋 类", BOLD), ("亲密 / 软 类", SOFT)):
        co, cn = count(old, keys), count(new, keys)
        to, tn = sum(co.values()), sum(cn.values())
        print(f"【{label}】 改前 {to}  改后 {tn}   （每千字 {to * 1000 / no:.2f} → {tn * 1000 / nn:.2f}）")
        for k in keys:
            if co[k] or cn[k]:
                print(f"    {k:<8} {co[k]:>4} → {cn[k]:>4}")
        print()


if __name__ == "__main__":
    main()
