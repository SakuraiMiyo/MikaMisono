#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify_facts.py —— 改写前后逐条核对「事实有没有丢」

改写日记的铁律是**事实一个字都不能改**。有代理报告说发现过跨篇串味并做了清理——
所以必须拿**改写前的整目录备份**逐篇比。

提取这些"硬事实 token"，比较备份版和新版的差集：
  · 数字（含小数点、百分比、单位）      13884 / 10.6G / 17 分 44 秒 / 19968×29184
  · 标识符（型号、文件名、报错码、路径）  mika_best.json / kernel-Power / FileNotFoundError
  · 引号里的原话                        「…」 "…" 『…』
  · 时间戳                              00:52:40 / 2026-09-18

**只对"备份里有、新版没有"报警**（新增不算——语气词和真心话本来就该增加）。

用法：<python> verify_facts.py [备份目录]
"""
from __future__ import annotations

import pathlib
import re
import sys

DIARY = pathlib.Path(r"C:\OneDrive\MikaMisono\agent\memory\diary")
BAK_DEFAULT = None


def find_backup() -> pathlib.Path | None:
    root = pathlib.Path(r"C:\OneDrive\MikaMisono\_archive-20260924")
    cands = sorted(root.glob("diary-before-voicefix-*"))
    return cands[-1] if cands else None


TOKEN = re.compile(
    r"[0-9]+(?:\.[0-9]+)?(?:×[0-9]+)?(?:\s?(?:G|MB|GB|k|K|Ω|元|块|w|万|%|分|秒|公里|km|条|篇|次))?"
    r"|[A-Za-z_][A-Za-z0-9_.\-]{2,}"
    r"|[0-9]{1,2}:[0-9]{2}(?::[0-9]{2})?"
)
QUOTED = re.compile(r"「[^」]{1,60}」|\"[^\"]{1,60}\"|『[^』]{1,60}』|“[^”]{1,60}”")

# 这些是语气/排版噪声，不算事实
STOP = {
    "md", "ps", "url", "list", "pdf", "PDF", "docx", "DAYS", "jpg", "png",
}


def facts(text: str) -> set[str]:
    out = set()
    for m in TOKEN.finditer(text):
        t = m.group(0).strip()
        if len(t) < 3 and not t.isdigit():
            continue
        if t in STOP:
            continue
        out.add(t)
    out |= {m.group(0) for m in QUOTED.finditer(text)}
    return out


def main() -> None:
    bak = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else find_backup()
    if not bak or not bak.exists():
        print("找不到备份目录")
        return
    print(f"备份：{bak}\n")

    total_missing = 0
    bad_files = []
    for old in sorted(bak.glob("*.md")):
        new = DIARY / old.name
        if not new.exists():
            print(f"⚠ {old.name}：新版不存在！")
            bad_files.append(old.name)
            continue
        fo = facts(old.read_text(encoding="utf-8", errors="ignore"))
        fn = facts(new.read_text(encoding="utf-8", errors="ignore"))
        missing = sorted(fo - fn)
        if missing:
            total_missing += len(missing)
            bad_files.append(old.name)
            print(f"🔴 {old.name}  丢了 {len(missing)} 个事实 token：")
            print("     " + "  ".join(missing[:40]))
            if len(missing) > 40:
                print(f"     …还有 {len(missing) - 40} 个")

    print(f"\n{'=' * 60}")
    if total_missing == 0:
        print("✅ 全部 41 篇：事实 token 零丢失")
    else:
        print(f"⚠️ 共 {len(bad_files)} 篇有丢失，合计 {total_missing} 个 token")
        print("   逐条回原文确认——有些是标点/大小写差异，有些可能是真丢了")


if __name__ == "__main__":
    main()
