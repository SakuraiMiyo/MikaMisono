#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""voice_baseline.py —— 用**同一个口径**量三份语料，给日记定一个可信的目标

`diary_voice.py` 算的是「语气词字数 / 总字数」，
而之前那组基准（吧 15.1% / 呢 13.3% / 啊 12.6%）算的是
「**含该语气词的句子数 / 总句数**」——**两个口径不能直接比**。

这个脚本把三份语料和日记放在同一口径下算两套数：

  A. 句级：含语气词的句子 / 总句数
  B. 字级：语气词个数 / 总字数

这样日记该往哪儿改就有了准星。

用法：<python> voice_baseline.py
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).parent
CORPUS = HERE.parent.parent / "assets" / "story-cn" / "corpus"
DIARY = pathlib.Path(r"C:\OneDrive\MikaMisono\agent\memory\diary")
sys.path.insert(0, str(HERE.parent.parent / "assets" / "voice-drama"))

PARTICLES = "吧呢啊哦呀嘛啦诶嘿嗯呜"
EMOJI = "☆♪"
SPLIT = re.compile(r"[。！？!?\n]+")   # ⚠️ 不能把「…」当分隔符，否则「含省略号」永远算成 0


def measure(label: str, texts: list[str]) -> None:
    n_chars = sum(len(t) for t in texts)
    n_part = sum(sum(t.count(c) for c in PARTICLES) for t in texts)
    sents = [s for t in texts for s in SPLIT.split(t) if s.strip()]
    sents_with = sum(1 for s in sents if any(c in s for c in PARTICLES))
    star = sum(t.count("☆") for t in texts)
    ell = sum(t.count("……") for t in texts)
    ell_sents = sum(1 for s in sents if "……" in s or "..." in s)
    print(f"{label}")
    print(f"   {len(texts)} 段 / {n_chars:,} 字 / {len(sents):,} 句")
    print(f"   句级 含语气词 {sents_with / len(sents):>6.1%}   含省略号 {ell_sents / len(sents):>6.1%}")
    print(f"   字级 语气词   {n_part / n_chars:>6.2%}   ☆ {star / n_chars:>6.2%}")
    print()


def main() -> None:
    only = json.loads((CORPUS / "mika-only.json").read_text(encoding="utf-8"))
    zh = [r["text"] for r in only if r.get("text")]
    moto = json.loads((CORPUS / "mika-momotalk.json").read_text(encoding="utf-8"))
    mz = [r["text"] for r in moto if r.get("speaker") == "未花" and r.get("text")]
    dia = [(p.read_text(encoding="utf-8")) for p in sorted(DIARY.glob("*.md"))]

    print("＝" * 34)
    print("口径 A/B 各自的数（同一套代码算的，可以直接比）")
    print("＝" * 34 + "\n")
    measure("① 剧情台词 992 句（yuan・说话）", zh)
    measure("② MomoTalk 158 条（打字）", mz)
    measure("③ 我的日记 41 篇（现状）", dia)
    print("注：日记是「写信」语域，句子比聊天长，句级密度天然会低一些——")
    print("    合理的目标不是追平聊天，而是**至少不要低一个数量级**。")


if __name__ == "__main__":
    main()
