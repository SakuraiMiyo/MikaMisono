#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fetch_momotalk.py —— 抓未花的 MomoTalk（手机聊天）文本

## 为什么重要

`agent/SKILL.md` 把 `☆`/`♪` 写成「高频、会连着甩」，但**剧情台词里**
☆ 只占 2.9%、♪ 只占 0.2%（`check_expression_stats.py` 实测）。
两者矛盾的原因很可能是 **register 不同**：
剧情是「说话」，MomoTalk 是「打字」，后者才是 QQ 机器人真正要对齐的语气。

MomoTalk 的取数路径（从前端 `MomotalkContainer-*.js` 挖出来）：
    https://preview.blue-archive.io/config/json/momotalk/{CharacterId}.json

用法：<python> fetch_momotalk.py
"""
from __future__ import annotations
import json
import pathlib
import re
from collections import Counter

import httpx

ROOT = pathlib.Path(__file__).parent
OUTDIR = ROOT / "raw" / "MomoTalk"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"}
HOST = "https://preview.blue-archive.io"
TARGETS = {"10059": "未花", "10122": "未花（泳装）"}
SENSEI_RE = re.compile(r"^\[s\]|^\[s\d+\]")


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    c = httpx.Client(headers=UA, timeout=60, follow_redirects=True)

    all_msgs: list[dict] = []
    for cid, name in TARGETS.items():
        r = c.get(f"{HOST}/config/json/momotalk/{cid}.json")
        if r.status_code != 200:
            print(f"  ✗ {cid} HTTP {r.status_code}")
            continue
        j = r.json()
        (OUTDIR / f"{cid}_{name}.json").write_text(
            json.dumps(j, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"  ✓ {cid} {name}: {len(r.content)} bytes  顶层键 {list(j.keys())}")

        # 结构探查
        for k, v in j.items():
            if isinstance(v, list) and v and isinstance(v[0], dict):
                print(f"      {k}: list[{len(v)}] 样例键 {list(v[0].keys())[:8]}")

    # ⚠️ 说话人靠 MessageCondition 区分：
    #      Answer   = 老师的回复
    #      其余（None / FavorRankUp / Feedback）= 未花发的
    #    不区分的话，老师的话会被当成未花的语录收进语料——统计和台词库都会被污染。
    print("\n── 提取消息（按 MessageCondition 分说话人）──")
    all_msgs: list[dict] = []
    for cid, name in TARGETS.items():
        p = OUTDIR / f"{cid}_{name}.json"
        if not p.exists():
            continue
        j = json.loads(p.read_text(encoding="utf-8"))
        rows: list[dict] = []
        for u in j.get("content", []):
            txt = (u.get("MessageCN") or "").strip()
            if not txt:
                continue
            rows.append({
                "character": name,
                "speaker": "老师" if u.get("MessageCondition") == "Answer" else name,
                "id": u.get("Id"),
                "text": txt,
            })
        if not rows:
            continue
        msgs = [r["text"] for r in rows if r["speaker"] != "老师"]
        n = len(msgs)
        star = sum(1 for s in msgs if "☆" in s)
        note = sum(1 for s in msgs if "♪" in s)
        multi = sum(1 for s in msgs if s.count("☆") + s.count("♪") >= 2)
        ell = sum(1 for s in msgs if "…" in s)
        q = sum(1 for s in msgs if "？" in s or "?" in s)
        print(f"\n  == {name} ==  未花 {n} 条 / 老师 {len(rows)-n} 条，"
              f"平均 {sum(map(len, msgs))/n:.1f} 字/条")
        print(f"     ☆ {star} 条 ({star/n*100:.1f}%)   ♪ {note} 条 ({note/n*100:.1f}%)"
              f"   ≥2 个符号 {multi} 条")
        print(f"     …… {ell/n*100:.1f}%   ？{q/n*100:.1f}%")
        for s in msgs[:5]:
            print(f"       {s[:56]}")
        all_msgs += rows

    if all_msgs:
        (ROOT / "corpus" / "mika-momotalk.json").write_text(
            json.dumps(all_msgs, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\n→ corpus/mika-momotalk.json（{len(all_msgs)} 条）")
        print("   提示：剧情台词 ☆ 占 2.9%、平均 21 字；"
              "MomoTalk 只算未花 158 条，☆ 8.9%、平均 8.5 字"
              "（原版线 ☆ 15.6% / 泳装线 ☆ 2.5%，两条线差异很大）。"
              "\n   —— 两种 register 别混着用；MomoTalk 内部也分两条线。")


if __name__ == "__main__":
    main()
