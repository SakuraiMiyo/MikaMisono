#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""rank_momotalk_windows.py —— 按「语气词密度」给 MomoTalk 的问答窗口排序

## 为什么需要它

`begin_dialogs` 里挑哪些窗口，决定了模型学到的说话方式。
第一版挑窗口时看的是 **☆ 的数量**——挑偏了：`☆` 只占 8.9%，而
`吧` 15.1% / `呢` 13.3% / `啊` 12.6%。真正让句子「像她」的是语气词。

所以第二版改成按**语气词种类的丰富度**排序：一个窗口里出现过多少"种"语气词，
比出现过多少个 `☆` 有用得多——few-shot 教的是**分布**，不是数量。

用法：
    <python> rank_momotalk_windows.py          # 前 20 个窗口
    <python> rank_momotalk_windows.py 40       # 前 40 个
"""
from __future__ import annotations

import json
import pathlib
import sys

SRC = (pathlib.Path(__file__).parent.parent / "assets" / "story-cn"
       / "corpus" / "mika-momotalk.json")

# 语气词 / 小表情的判定集合。分三类只是为了输出好看。
PARTICLES = "吧呢啊哦呀嘛啦诶嘿呜哼嗯欸唉唷呦"
INTERJ = "哇吼呼噢哟"
MARKS = "～〜♪☆"


def kinds(text: str) -> str:
    """返回这段文字里出现过的语气词种类（去重、保持固定顺序）。"""
    seen = [c for c in PARTICLES + INTERJ + MARKS if c in text]
    return "".join(seen)


def main() -> None:
    top = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    rows = json.loads(SRC.read_text(encoding="utf-8"))
    rows.sort(key=lambda r: r["id"])

    windows = []
    for i, r in enumerate(rows):
        if r["speaker"] != "老师":
            continue
        burst = []
        for x in rows[i + 1:]:
            if x["speaker"] == "老师":
                break
            burst.append(x["text"])
        if not burst:
            continue
        body = "".join(burst)
        k = kinds(body)
        windows.append((len(k), len(burst), len(body), r["id"], k, body))

    windows.sort(key=lambda w: (-w[0], -w[1]))
    print(f"共 {len(windows)} 个「老师→未花」窗口，按语气词种类数排序：\n")
    for n, cnt, chars, qid, k, body in windows[:top]:
        print(f"{qid}  {n:>2} 种 / {cnt} 条 / {chars:>3} 字  {k}")
        print(f"      {body[:60]}{'…' if len(body) > 60 else ''}")

    # 对照：按 ☆ 排序会挑出什么
    print("\n（对照）按 ☆ 数量排序的前 5 个：")
    star = sorted(windows, key=lambda w: -w[5].count("☆"))[:5]
    for n, cnt, chars, qid, k, body in star:
        print(f"{qid}  ☆×{body.count('☆')}  {k}  {body[:40]}…")


if __name__ == "__main__":
    main()
