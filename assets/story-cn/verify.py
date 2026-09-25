#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify.py —— 交付前自检

## ⚠️ 这个脚本**证明不了「收全了」**

它只能证明「本地文件 ↔ 官方目录表」两边一致。而那个目录表是从**同一个源站**抽的，
所以这是**自洽性检查，不是完整性检查**。踩过的坑：

  · 曾经用 `31000 <= i < 34000` 硬编码 Vol.3 的范围，
    结果 Vol.3 第四章（34xxx）被整个排除；
  · 又拿自己抽的目录去比自己的结果，报了个漂亮的「✅ 一致」——
    **两边都被同一个错误假设污染了**。

真正的完整性必须靠**外部事实**来验，见文件末尾的 EXTERNAL_CHECKLIST。

用法：<python> verify.py
"""
from __future__ import annotations
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).parent
OUT = ROOT / "corpus"

# 外部事实：Vol.3「エデン条約編」= 4 章（不是 3 章）
#   第1章 補習授業部        17 話
#   第2章 イーデン条約      20 話 + 後日談
#   第3章 私たちの物語      25 話 + 後日談
#   第4章 忘れられた神々のためのキリエ  前/中/後編（2022-05-25 / 06-08 / 08-10 配信）
EXTERNAL_CHECKLIST = [
    ("Vol.3 第1章 収録", "31010–31170"),
    ("Vol.3 第2章 収録", "32010–32200"),
    ("Vol.3 第3章 収録", "33010–33250"),
    ("Vol.3 第4章 収録", "**未取得** —— 公开站不含，需本地解包或其它来源"),
]


def main() -> None:
    turns = json.loads((OUT / "mika-turns.json").read_text(encoding="utf-8"))
    stats = json.loads((OUT / "stats.json").read_text(encoding="utf-8"))
    index = json.loads((ROOT / "mika-story-index.json").read_text(encoding="utf-8"))
    cat = json.loads((ROOT / "catalog-ba-archive.json").read_text(encoding="utf-8"))

    want = {s["id"] for v in cat for s in v["sections"] if 31000 <= s["id"] < 35000}
    have = {int(p.stem) for p in (ROOT / "raw" / "Vol.3").glob("*.json")}
    hang = sum(1 for t in turns if re.search(r"[가-힣]", t["speaker"] or ""))

    print("── 规模 ──")
    print(f"  未花台词      {stats['mika_turns']} 句 / {stats['mika_cjk']} 汉字"
          f"（平均 {stats['mika_avg_len']} 字）")
    print(f"  对话轮        {stats['total_turns']}")
    print(f"  场景窗口      {stats['scenes']}")
    print(f"  上下文→回应    {stats['pairs']}")
    print(f"  未花出场篇数   {len(index['stories'])}")
    print(f"  精确归属率     {(1 - stats['unknown_ratio']) * 100:.1f}%")
    print(f"  说话人未中文化  {hang} 条（{hang / len(turns) * 100:.2f}%）")

    print("\n── 本地 ↔ 源站目录（自洽性检查，**不等于**完整性）──")
    print(f"  源站目录 31xxx–34xxx {len(want)} 节 / 本地 {len(have)} 节 → "
          f"{'自洽' if want == have else '❌ 不一致'}")
    if want != have:
        print("   缺:", sorted(want - have), " 多:", sorted(have - want))
    by_ch: dict[str, list[int]] = {}
    for i in sorted(have):
        by_ch.setdefault(str(i)[1], []).append(i)
    for ch in sorted(by_ch):
        print(f"   第{ch}章 {len(by_ch[ch]):>3} 节  {by_ch[ch][0]} … {by_ch[ch][-1]}")

    print("\n── 分类构成 ──")
    for k, v in stats["by_cat"].items():
        print(f"  {k:<8} {v['stories']:>3} 篇  {v['turns']:>5} 轮  未花 {v['mika']:>4} 句"
              f" / {v['mika_cjk']:>6} 汉字")

    print("\n── 外部事实核对（这个才叫完整性）──")
    for name, note in EXTERNAL_CHECKLIST:
        mark = "❌" if "未取得" in note else "✅"
        print(f"  {mark} {name:<16} {note}")

    print("\n提示：第4章缺失会让「未花台词总数」少一大块（那是她的救赎弧）。")
    print("详见 `game/README.md` 与 `未花-剧情时间线.md` 第八节。")


if __name__ == "__main__":
    main()
