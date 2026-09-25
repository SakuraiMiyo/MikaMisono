#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""catchphrase_lookup.py —— 定向查口癖 + 长一点的 n-gram

`mine_catchphrases.py` 挖 2-gram 时满屏都是「って / んだ / から」这种语法词，
没有信息量。这里做两件事：

1. **定向查**：给一张候选表，逐个数在语料里出现多少条——用来确认/否决传闻。
2. **只挖 3-gram 以上**，把语法词滤掉，剩下的才是"她自己爱说的那种话"。

用法：<python> catchphrase_lookup.py
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
from analyze_particles import load_lists  # noqa: E402

SPLIT = re.compile(r"[\s、。，．？！!?…‥「」『』（）()☆♪〜～\-ー—]+")

# ── 候选口癖表（日文侧）────────────────────────────────────────
JA_CANDIDATES = [
    # 招呼 / 开场
    "やっほ", "やっほー", "イヤッハー", "レッツゴ", "よースター", "ハロー",
    "おはよ", "こんにちは", "おつかれ", "おかえり", "ただいま",
    # 笑い声 / 掛け声
    "えへへ", "あはは", "ふふふ", "ふふん", "うふふ", "きゃは", "ははは",
    "うへー", "わーお", "わあ", "うわー", "おー", "はーん", "ふーん",
    # 縮め・語尾
    "だよね", "だもん", "なんだよ", "じゃん", "んだよ", "のかな", "かなー",
    "だよー", "ってば", "でしょ", "かもね", "じゃない", "わけじゃ",
    # 内容っぽい決まり文句
    "爆破", "約束", "ずるい", "ひどい", "しょうがない", "めんどくさい",
    "特別", "褒美", "ご褒美", "正直", "実は", "ていうか", "というか",
]
# ── 候选口癖表（中文侧）──────────────────────────────────────
ZH_CANDIDATES = [
    "呀吼", "呀吼〜", "嘿嘿", "欸嘿嘿", "诶嘿嘿", "啊哈哈", "哈哈哈", "哼哼",
    "呜", "呜呜", "唔", "哇哦", "哇～哦", "哦哦", "哦——",
    "呢", "吧", "嘛", "啦", "哦", "呀", "诶", "嗯",
    "才不是", "才没有", "骗人", "真的假的", "不是啦", "没有啦",
    "是吗", "对吧", "对不对", "不是吗", "来着",
    "老师", "sensei",
]


def count_line_hits(lines: list[str], needle: str) -> int:
    return sum(1 for t in lines if needle in t)


def main() -> None:
    ja = [r["text"] for r in load_lists()]
    only = json.loads((CORPUS / "mika-only.json").read_text(encoding="utf-8"))
    zh = [r["text"] for r in only if r.get("text")]
    moto = json.loads((CORPUS / "mika-momotalk.json").read_text(encoding="utf-8"))
    motoz = [r["text"] for r in moto
             if r.get("speaker") == "未花" and r.get("text")]

    print("=" * 78)
    print("① 定向查：日文候选口癖（配音 742 条）")
    print("=" * 78)
    rows = [(c, count_line_hits(ja, c)) for c in JA_CANDIDATES]
    for c, n in sorted(rows, key=lambda kv: -kv[1]):
        if n == 0:
            continue
        print(f"  {n:>4} 条 ({n / len(ja):>5.1%})  {c}")
        for t in ja:
            if c in t:
                print(f"           · {t[:70]}")
                break
    zeros = [c for c, n in rows if n == 0]
    print(f"\n  ⚠️ 0 命中（传闻或不适用）：{'  '.join(zeros)}")

    print("\n" + "=" * 78)
    print("② 定向查：中文候选口头禅（剧情 992 / MomoTalk 77）")
    print("=" * 78)
    for c in ZH_CANDIDATES:
        a = count_line_hits(zh, c)
        b = count_line_hits(motoz, c)
        if a == 0 and b == 0:
            continue
        print(f"  剧情 {a:>4} ({a / len(zh):>5.1%})   MomoTalk {b:>3} "
              f"({b / len(motoz):>5.1%})   「{c}」")

    print("\n" + "=" * 78)
    print('③ 只挖 3-gram 以上：剩下的才是「她爱说的那种话」')
    print("=" * 78)
    for label, lines, lo, hi, ml in (("配音（日文）", ja, 3, 6, 5),
                                     ("剧情（中文）", zh, 3, 6, 8),
                                     ("MomoTalk（中文）", motoz, 2, 6, 3)):
        c = collections.Counter()
        for t in lines:
            for seg in SPLIT.split(t):
                for k in range(lo, min(hi, len(seg)) + 1):
                    for i in range(len(seg) - k + 1):
                        c[seg[i:i + k]] += 1
        hits = [(g, n) for g, n in c.items() if n >= ml]
        hits.sort(key=lambda kv: (-kv[1], -len(kv[0])))
        keep = [x for x in hits
                if not any(x[0] != h and x[0] in h and hn >= x[1] * 0.75
                           for h, hn in hits)]
        print(f"\n【{label}】{len(lines)} 条")
        for g, n in keep[:28]:
            print(f"  {n:>4} ({n / len(lines):>5.1%})  「{g}」")


if __name__ == "__main__":
    main()
