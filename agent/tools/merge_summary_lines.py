# -*- coding: utf-8 -*-
"""
merge_summary_lines.py —— 把各批产出的小结行合并进 summaries/memory.md

为什么不让改写者直接编辑 memory.md：
    6 个批次并行，各自 `edit` 同一个文件必然互相覆盖。所以约定——
    **每批只产出自己那几天的行**（一条一个 JSON 文件），最后在这里统一合并。

用法：
    <python> merge_summary_lines.py            # 预演，只看会变成什么
    <python> merge_summary_lines.py --apply    # 真的写
"""
from __future__ import annotations

import argparse
import datetime
import json
import pathlib
import re
import shutil
import sys

# Windows 控制台默认 GBK，输出里的 ✓/✗ 会直接把脚本搞崩。自己掰成 UTF-8。
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

AGENT = pathlib.Path(r"C:\OneDrive\MikaMisono\agent")
MEM = AGENT / "memory" / "summaries" / "memory.md"
PARTS = AGENT / "memory" / "summaries" / "_parts"
BAK = pathlib.Path(r"C:\OneDrive\MikaMisono\_archive-20260924")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    if not PARTS.is_dir():
        print(f"✗ 没有分片目录 {PARTS}")
        sys.exit(1)

    lines = MEM.read_text(encoding="utf-8").splitlines()
    # 索引：日期 -> 行号
    idx: dict[str, int] = {}
    for i, ln in enumerate(lines):
        m = re.match(r"^-\s+(\d{4}-\d{2}-\d{2})\s", ln)
        if m:
            idx[m.group(1)] = i
    print(f"memory.md 共 {len(lines)} 行，认出 {len(idx)} 个日期行")

    # 收分片
    new: dict[str, str] = {}
    for f in sorted(PARTS.glob("*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"  ✗ {f.name} 解析失败：{e}")
            continue
        for date, line in (d or {}).items():
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
                print(f"  ✗ {f.name}：日期格式不对 {date!r}")
                continue
            if not line.startswith("- "):
                print(f"  ✗ {f.name} / {date}：行首必须是 '- '")
                continue
            if not line.startswith(f"- {date} "):
                print(f"  ✗ {f.name} / {date}：行里的日期和键对不上")
                continue
            if date in new:
                print(f"  ! {date} 在两个分片里都出现，后者覆盖前者（{f.name}）")
            new[date] = line
        print(f"  ✓ {f.name}：{len(d)} 行")

    print(f"\n收到 {len(new)} 天的新行")

    miss = sorted(set(idx) - set(new))
    extra = sorted(set(new) - set(idx))
    if miss:
        print(f"⚠️ memory.md 里这 {len(miss)} 天没拿到新行（会保持原样）：{miss}")
    if extra:
        print(f"✗ 这些天在 memory.md 里找不到位置：{extra}")

    out = list(lines)
    for date, line in new.items():
        if date in idx:
            out[idx[date]] = line
    txt = "\n".join(out) + "\n"
    print(f"\n合并后 {len(txt):,} 字符（原 {len(MEM.read_text(encoding='utf-8')):,}）")

    if not a.apply:
        print("\n（预演。加 --apply 才写。）")
        for date in sorted(new)[:3]:
            print(f"  {new[date][:110]}")
        return

    BAK.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    dst = BAK / f"memory-before-merge-{stamp}.md"
    shutil.copy2(MEM, dst)
    MEM.write_text(txt, encoding="utf-8")
    print(f"✓ 已备份 -> {dst}")
    print("✓ 已写入 memory.md")


if __name__ == "__main__":
    main()
