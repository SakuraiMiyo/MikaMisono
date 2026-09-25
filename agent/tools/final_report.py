# -*- coding: utf-8 -*-
"""final_report.py —— 这一轮记忆改写的前后对照（一次性验收）

统计口径（全项目统一，跟日记那次改写一致）：
  · 句级含语气词 —— 按 [。！？!?\\n]+ 切句，句子里出现 哦啦呀嘛诶欸唔唷呐嗯 任一即计入
  · 句级含省略号 —— 句子里出现 … 或 ... 即计入
  · 字级 ☆       —— ☆ 出现次数 / 总字符数
"""
import json
import pathlib
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

B = pathlib.Path(r"C:\OneDrive\MikaMisono")
AG = B / "agent"
BAK = B / "_archive-20260924" / "cards-before-voicefix-20260926-014224"

PARTICLES = "哦啦呀嘛诶欸唔唷呐嗯"


def stats(text: str) -> dict:
    sents = [s for s in re.split(r"[。！？!?\n]+", text) if s.strip()]
    n = max(1, len(sents))
    return {
        "sents": len(sents),
        "particle": round(100 * sum(1 for s in sents if any(p in s for p in PARTICLES)) / n, 1),
        "ellipsis": round(100 * sum(1 for s in sents if "…" in s or "..." in s) / n, 1),
        "star": round(100 * text.count("☆") / max(1, len(text)), 2),
        "chars": len(text),
    }


def card_text(card: dict) -> str:
    out = []
    for k, v in card.items():
        if k == "date":
            continue
        out.extend(map(str, v)) if isinstance(v, list) else out.append(str(v))
    return "\n".join(out)


def collect(d: pathlib.Path) -> str:
    parts = []
    for p in sorted(d.glob("*.json")):
        try:
            parts.append(card_text(json.loads(p.read_text(encoding="utf-8"))))
        except Exception:
            pass
    return "\n".join(parts)


rows = [
    ("日记（上一轮已改，参照标准）", "DIARY"),
    ("记忆卡 改前", collect(BAK / "cards")),
    ("记忆卡 改后", collect(AG / "memory" / "cards")),
]

print(f"{'':38} {'句数':>6} {'语气词':>7} {'省略号':>7} {'字级☆':>7} {'字符':>8}")
print("─" * 82)

DIARY = "\n".join(p.read_text(encoding="utf-8")
                  for p in sorted((AG / "memory" / "diary").glob("*.md")))

for label, text in rows:
    if text == "DIARY":
        text = DIARY
    s = stats(text)
    print(f"{label:38} {s['sents']:>6} {s['particle']:>6}% {s['ellipsis']:>6}% "
          f"{s['star']:>6}% {s['chars']:>8}")

# rolling summary
mb = B / "_archive-20260924" / "memory-before-merge-20260926-015004.md"
ma = AG / "memory" / "summaries" / "memory.md"
for label, p in (("rolling summary 改前", mb), ("rolling summary 改后", ma)):
    if p.exists():
        s = stats(p.read_text(encoding="utf-8"))
        print(f"{label:38} {s['sents']:>6} {s['particle']:>6}% {s['ellipsis']:>6}% "
              f"{s['star']:>6}% {s['chars']:>8}")

print()
# 事实保真粗核：卡片全量数字多重集
from collections import Counter


def nums(t):
    return Counter(re.findall(r"\d+", t.replace(" ", "")))


nb, na = nums(collect(BAK / "cards")), nums(collect(AG / "memory" / "cards"))
lost = nb - na
added = na - nb
print(f"卡片数字多重集：丢失 {dict(lost) or '无'}　新增 {dict(added) or '无'}")
print(f"卡片文件数：改前 {len(list((BAK/'cards').glob('*.json')))} · "
      f"改后 {len(list((AG/'memory'/'cards').glob('*.json')))}")
