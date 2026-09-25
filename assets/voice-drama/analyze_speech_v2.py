#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""analyze_speech_v2.py —— 修正第一版的两个误报

`analyze_speech.py` 里两处会数多，先修掉再写结论：

1. **长音**：原来的正则 `[ぁ-んァ-ヶ]ー` 会把片假名外来语全算进去
   （エスコート / スタート / ブルーアーカイブ / アイスコーヒー…），
   那些是词里的长音符，不是拖音。改成只认**平假名 + ー**。
2. **もん/もの**：`紅茶は当然温かくして飲むものです` 里的「もの」是实义名词。
   这里改成只认句末的「もん / もの / だもん / だもんね」。

用法：<python> analyze_speech_v2.py
"""
from __future__ import annotations

import collections
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).parent
CORPUS = HERE.parent / "story-cn" / "corpus"
sys.path.insert(0, str(HERE))
from analyze_particles import load_lists, strip_tail  # noqa: E402


def main() -> None:
    rows = load_lists()
    n = len(rows)

    print("── ① 拖音：平假名 + ー（修正后）──")
    el = [r["text"] for r in rows if re.search(r"[ぁ-ん]ー", r["text"])]
    print(f"{len(el)}/{n} = {len(el) / n:.1%}")
    for t in el:
        print("   " + t)

    print("\n── ② 句末「もん / もの」（撒娇式辩解）──")
    mo = [r["text"] for r in rows
          if re.search(r"(だ)?もん(ね|だ|$)|ものです?$|んだもん", strip_tail(r["text"]))]
    print(f"{len(mo)}/{n} = {len(mo) / n:.1%}")
    for t in mo[:12]:
        print("   " + t)

    print("\n── ③ 人称（判断语料里有没有混进别的角色）──")
    for p in ("私", "あたし", "僕", "わたくし", "俺"):
        c = sum(1 for r in rows if p in r["text"])
        print(f"   {p}: {c}")

    print("\n── ④ 完整终助词表（任意位置，修正 な 的误报）──")
    # 「な」当终助词时通常跟在句读后面，或句末；这里只统计**句末**和「〜なあ/なぁ」
    fin = collections.Counter()
    for r in rows:
        t = strip_tail(r["text"])
        for p in ("よ", "ね", "の", "か", "わ", "さ", "ぜ", "ぞ", "な", "なあ",
                  "よね", "だよね", "かな", "かしら", "でしょ", "じゃん", "っけ", "かも"):
            if t.endswith(p):
                fin[p] += 1
                break
    tot = sum(fin.values())
    print(f"   句末带终助词：{tot}/{n} = {tot / n:.1%}")
    for p, c in fin.most_common():
        print(f"     {p:<6} {c:>4}  {c / n:>6.1%}")

    print("\n── ⑤ 中文语料：严格只算语气词（不含 嗯/哈/诶 这类感叹词）──")
    STRICT = ["吧", "呢", "啊", "哦", "呀", "嘛", "啦", "喔", "嘞", "咯", "吗", "呐"]
    for name, picker in (
        ("mika-only.json", lambda j: [r["text"] for r in j if r.get("text")]),
        ("mika-momotalk.json", lambda j: [r["text"] for r in j
                                          if r.get("speaker") == "未花" and r.get("text")]),
    ):
        texts = picker(json.loads((CORPUS / name).read_text(encoding="utf-8")))
        m = len(texts)
        has = sum(1 for t in texts if any(p in t for p in STRICT))
        cnt = sum(sum(t.count(p) for p in STRICT) for t in texts)
        fin2 = sum(1 for t in texts if strip_tail(t)[-1:] in STRICT)
        print(f"   {name}（{m} 条）：含 {has / m:.1%} / 句末 {fin2 / m:.1%} / "
              f"平均 {cnt / m:.2f} 个")
        c = collections.Counter()
        for t in texts:
            for p in STRICT:
                c[p] += t.count(p)
        print("      " + "  ".join(f"{p} {v}({v / m:.1%})" for p, v in c.most_common(9)))


if __name__ == "__main__":
    main()
