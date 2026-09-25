#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dump_voice_lines.py —— 按音频来源抽样打印配音转写，用眼睛看语域

`analyze_particles.py` 只给数字。但「她说话什么样」这件事得用眼睛看——
每条 ASR 就是一句台词，连起来读能直接感受到断句和终助词。

用法：
    <python> dump_voice_lines.py                # 每个来源抽 15 条
    <python> dump_voice_lines.py 40             # 每个来源抽 40 条
    <python> dump_voice_lines.py 40 未花配音素材   # 只看某个来源
"""
from __future__ import annotations

import collections
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from analyze_particles import load_lists  # noqa: E402


def main() -> None:
    per = int(sys.argv[1]) if len(sys.argv) > 1 else 15
    only = sys.argv[2] if len(sys.argv) > 2 else None

    rows = load_lists()
    by = collections.defaultdict(list)
    for r in rows:
        by[r["src"]].append(r["text"])

    for src, lines in sorted(by.items(), key=lambda kv: -len(kv[1])):
        if only and only not in src:
            continue
        print(f"\n{'=' * 70}\n【{src}】{len(lines)} 条\n{'=' * 70}")
        step = max(1, len(lines) // per)
        for t in lines[::step][:per]:
            print("  " + t)
    print()


if __name__ == "__main__":
    main()
