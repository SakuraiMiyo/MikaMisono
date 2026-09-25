# -*- coding: utf-8 -*-
"""check_summary_parts.py —— 分片的标题必须和卡片的新 title 逐字一致

`summaries/memory.md` 每行的格式是：
    - YYYY-MM-DD <title>｜<复述>

如果 <title> 和 `cards/<date>.json` 的 `title` 对不上，
检索时同一个事件会出现两种说法——所以这里逐条核。
"""
import json
import pathlib
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

M = pathlib.Path(r"C:\OneDrive\MikaMisono\agent\memory")
PARTS = M / "summaries" / "_parts"

rows: dict[str, tuple[str, str]] = {}
for f in sorted(PARTS.glob("*.json")):
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"✗ {f.name} 解析失败 {e}")
        continue
    for date, line in d.items():
        rows[date] = (f.name, line)

print(f"分片共 {len(rows)} 天\n")

ok = bad = noc = 0
for date in sorted(rows):
    part, line = rows[date]
    cp = M / "cards" / f"{date}.json"
    if not cp.exists():
        print(f"✗ {date}：卡片不存在")
        bad += 1
        continue
    try:
        title = json.loads(cp.read_text(encoding="utf-8")).get("title", "")
    except Exception:
        print(f"✗ {date}：卡片 JSON 坏了")
        bad += 1
        continue

    # 行首 "- date " 之后到第一个 ｜ 之间应是标题
    m = re.match(rf"^-\s+{re.escape(date)}\s+(.*?)｜", line)
    if not m:
        print(f"✗ {date}（{part}）：行首格式不对 → {line[:60]}")
        bad += 1
        continue
    head = m.group(1).strip()
    if head == title:
        ok += 1
    else:
        print(f"✗ {date}（{part}）标题不一致")
        print(f"      卡片：{title}")
        print(f"      分片：{head}")
        bad += 1

print(f"\n一致 {ok} · 不一致 {bad}")
sys.exit(1 if bad else 0)
