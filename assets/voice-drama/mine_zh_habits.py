#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mine_zh_habits.py —— 中文侧的「开口第一下」和「结尾最后一下」

口癖在中文里最藏不住的两个位置：
  · **句首前两个字**——招呼、感叹、应声都在这里
  · **句末最后两个字**——「〜对吧？」「〜来着」「〜呢」这些求认同的尾巴都在这里

用法：<python> mine_zh_habits.py
"""
from __future__ import annotations

import collections
import json
import pathlib

CORPUS = pathlib.Path(__file__).parent.parent / "story-cn" / "corpus"

# 只保留"像口癖"的，滤掉纯内容的（专有名词等）
STOP_HEAD = {"所以", "但是", "不过", "而且", "因为", "如果", "虽然", "然后",
             "这样", "这种", "这个", "那个", "现在", "已经", "当然", "其实",
             "毕竟", "只是", "就算", "要是", "只是", "可是", "就是", "什么"}
STOP_TAIL = {"的话", "什么", "事情", "时候", "这样", "那种", "没有"}


def main() -> None:
    only = json.loads((CORPUS / "mika-only.json").read_text(encoding="utf-8"))
    zh = [r["text"] for r in only if r.get("text")]
    moto = json.loads((CORPUS / "mika-momotalk.json").read_text(encoding="utf-8"))
    mz = [r["text"] for r in moto if r.get("speaker") == "未花" and r.get("text")]

    for label, lines in (("剧情台词", zh), ("MomoTalk", mz)):
        n = len(lines)
        head = collections.Counter(t[:2] for t in lines if len(t) >= 2)
        tail = collections.Counter(t[-2:] for t in lines if len(t) >= 2)
        print(f"\n{'=' * 74}\n【{label}】{n} 条 · 句首前两字\n{'=' * 74}")
        for w, c in head.most_common(40):
            if w in STOP_HEAD or c < 2:
                continue
            print(f"  {c:>4} ({c / n:>5.1%})  {w}")
        print(f"\n【{label}】句末最后两字\n" + "=" * 74)
        for w, c in tail.most_common(40):
            if w in STOP_TAIL or c < 2:
                continue
            print(f"  {c:>4} ({c / n:>5.1%})  {w}")

    print(f"\n{'=' * 74}\n单独查：拟声词 / 招牌动作词（剧情 {len(zh)} 条）\n{'=' * 74}")
    for w in ["锵锵", "登！", "场！", "呀吼", "哇～哦", "哇哦", "哼哼哼", "唔嗯",
              "是呀是呀", "果然呢", "也是呢", "才不是", "才没有", "骗人",
              "好怀念", "真拿你没办法", "没办法", "好厉害", "哈哈"]:
        c = sum(1 for t in zh if w in t)
        m = sum(1 for t in mz if w in t)
        if c or m:
            print(f"  剧情 {c:>3}  MomoTalk {m:>2}   「{w}」")


if __name__ == "__main__":
    main()
