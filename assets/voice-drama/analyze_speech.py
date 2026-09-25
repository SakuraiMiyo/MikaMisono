#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""analyze_speech.py —— 第二遍：找「开口习惯」，不只是终助词

第一遍（`analyze_particles.py`）只量了句末终助词。但读样本时发现一个
**两份文字语料里都没有的东西**：

    し、失敗しちゃった。ごめんね。
    ど、どうしたの先生?
    ご、ごめんね先生の都合も考えずに来ちゃって
    うっ、ちょちょ!
    は、うん、そう、たまたまね

**首字重复（吃音）**——紧张、害羞、慌的时候把第一个音拖出来重说一遍。
这是配音语料独有的，剧情文本和聊天记录里都会被"整理"掉。
而它恰恰是**情绪表露**最直接的标记，也正是 QQ 上缺的那种东西。

用法：<python> analyze_speech.py
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

# 终助词（出现在**任意位置**，不只是句末）
JA_PARTICLES_ANY = ["よ", "ね", "な", "の", "わ", "さ", "か", "ぜ", "ぞ", "もん", "もの", "って", "じゃん", "かな", "かしら", "でしょ", "っけ"]
# 中文语气词（任意位置）
ZH_PARTICLES = ["吧", "呢", "啊", "哦", "呀", "嘛", "啦", "喔", "诶", "耶", "嘞", "咯", "吗", "呐", "嗷", "嗯", "哎", "唉", "哈", "哟", "喂", "哼", "呜"]

# 吃音：同一个假名/汉字后跟「、」再跟同一个字，或者「X、X…」
STUTTER = re.compile(r"([ぁ-んァ-ヶ一-龥])\s*[、,]\s*\1")


def main() -> None:
    rows = load_lists()
    n = len(rows)
    print(f"── 配音转写 {n} 条 ──\n")

    # ① 终助词：任意位置 vs 句末
    anyc = collections.Counter()
    any_has = 0
    for r in rows:
        hit = [p for p in JA_PARTICLES_ANY if p in r["text"]]
        if hit:
            any_has += 1
        for p in hit:
            anyc[p] += 1
    print(f"句中出现终助词（任意位置）：{any_has}/{n} = {any_has / n:.1%}")
    for p, c in anyc.most_common(12):
        print(f"   {p:<5} {c:>4}  {c / n:>6.1%}")

    # ② 吃音
    st = [r["text"] for r in rows if STUTTER.search(r["text"])]
    print(f"\n吃音（首字重复，X、X…）：{len(st)}/{n} = {len(st) / n:.1%}")
    for t in st[:25]:
        print("   " + t)

    # ③ 长音
    el = [r["text"] for r in rows if re.search(r"[ぁ-んァ-ヶ]ー", r["text"])]
    print(f"\n长音「ー」拖音：{len(el)}/{n} = {len(el) / n:.1%}")
    for t in el[:18]:
        print("   " + t)

    # ④ ん系（说明语气）
    for pat, label in ((r"んだ|んです|のかな|んだけど|んだよね", "ん系（说明/推测）"),
                       (r"もん|もの", "もん/もの（撒娇式辩解）"),
                       (r"って", "って（引用/改口）"),
                       (r"けど|のに|けれど", "けど/のに（句末转折）")):
        hit = [r["text"] for r in rows if re.search(pat, r["text"])]
        print(f"\n{label}：{len(hit)}/{n} = {len(hit) / n:.1%}")
        for t in hit[:10]:
            print("   " + t)

    # ⑤ 中文对照：语气词「任意位置」的密度
    print("\n\n── 中文语料：语气词密度 ──\n")
    for name, picker in (
        ("mika-only.json", lambda j: [r["text"] for r in j if r.get("text")]),
        ("mika-momotalk.json", lambda j: [r["text"] for r in j
                                          if r.get("speaker") == "未花" and r.get("text")]),
    ):
        f = CORPUS / name
        if not f.exists():
            continue
        texts = picker(json.loads(f.read_text(encoding="utf-8")))
        m = len(texts)
        has = sum(1 for t in texts if any(p in t for p in ZH_PARTICLES))
        cnt = sum(sum(t.count(p) for p in ZH_PARTICLES) for t in texts)
        fin = sum(1 for t in texts if strip_tail(t)[-1:] in ZH_PARTICLES)
        print(f"{name}：{m} 条")
        print(f"   含语气词（任意位置）：{has}/{m} = {has / m:.1%}")
        print(f"   句末是语气词：      {fin}/{m} = {fin / m:.1%}")
        print(f"   平均每条语气词个数：{cnt / m:.2f}")
        c = collections.Counter()
        for t in texts:
            for p in ZH_PARTICLES:
                c[p] += t.count(p)
        print("   " + "  ".join(f"{p}{v}({v / m:.1%})" for p, v in c.most_common(10)))
        print()


if __name__ == "__main__":
    main()
