#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""extract_mika_lines.py —— 从未花剧情 JSON 里抽出「她本人说过的话」

## 数据来源（公开库；2026-09-24 验证可用）

碧蓝档案剧情站（ba-archive）的预览数据：
  · 羁绊剧情  https://preview.blue-archive.io/story/favor/<groupId前5位>/<groupId>.json
  · 主线/其他 https://preview.blue-archive.io/story/main/<storyId>.json
  · 学生索引  https://preview.blue-archive.io/story/favor/<前5位>/index.json
  ⚠️ 必须带浏览器 User-Agent，否则 Cloudflare 返回 403

JSON 结构：{GroupId, translator, proofreader, content:[单元…]}
单元字段：TextCn/TextJp/TextTw/TextEn/TextKr、ScriptKr、VoiceJp、BGMId、BGName、Sound…

## 说话人约定（实测确认）

  `[s]` / `[s1][s2]`  → 老师（Sensei）的台词
  `[ns]`              → 旁白 / 叙述
  无前缀              → 该场景里说话的学生
  `#n`                → 换行占位符

## ⚠️ 归属可靠性（这个区别很重要）

  · **favor / 10059x（未花的羁绊剧情）** —— 场景里基本只有她和老师，
    所以「无前缀 = 未花」成立 → **采信**
  · **main / 主线** —— 多角色群像；「这一章里有未花」只证明她在场，
    不能证明每句无前缀台词都是她说 → **不采信，另存待核**

## 未花的剧情 ID

  羁绊组 10059：100592 重归平稳的日常 / 100593 义务劳动 /
                100595 阁楼里的公主殿下 / 100596 伤痕
  （100594「巧克力瑞士卷」在剧情站尚未上线）

## 用法

    <python> extract_mika_lines.py
"""
from __future__ import annotations

import json
import pathlib
import re
from collections import Counter

ROOT = pathlib.Path(r"C:\OneDrive\MikaMisono\assets\story-cn")
OUT = ROOT / "mika-corpus"

SENSEI = re.compile(r"^\[s\d*\]")
NARR = re.compile(r"^\[ns\]")

MIKA_FAVOR = {"100592", "100593", "100595", "100596"}
TITLES = {
    "100592": "第1话 重归平稳的日常",
    "100593": "第2话 义务劳动",
    "100595": "第3话 阁楼里的公主殿下",
    "100596": "第4话 伤痕",
}


def clean(t: str) -> str:
    t = t.replace("#n", "\n").strip()
    t = re.sub(r"^\[[a-z0-9]+\]\s*", "", t)
    return t.strip().strip('"').strip("“”").strip()


def is_student_line(text_cn: str) -> bool:
    """无 [s]/[ns] 前缀、且不是纯演出标记的行 = 该场景学生说的话。"""
    t = text_cn.strip()
    if not t:
        return False
    if SENSEI.match(t) or NARR.match(t):
        return False
    if re.fullmatch(r"[\[\(].*[\]\)]", t):      # 纯 [Image:…] 之类的标记
        return False
    return True


def is_trustworthy(src: str, sid: str) -> bool:
    """只有整篇都是未花的文件才能采信（见模块 docstring）。"""
    return src == "favor" and sid in MIKA_FAVOR


def iter_units(path: pathlib.Path):
    j = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(j, dict) or "content" not in j:
        return                                   # 跳过非剧情 JSON（如索引清单）
    src = path.parent.name
    sid = path.stem.split("_")[0]
    for i, u in enumerate(j.get("content", [])):
        yield src, sid, i, u


def cjk_count(s: str) -> int:
    return sum(1 for ch in s if "\u4e00" <= ch <= "\u9fff")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in ROOT.rglob("*.json") if p.parent.name != "mika-corpus")
    if not files:
        print("没有找到剧情 JSON，请先下载到", ROOT)
        return

    lines: list[dict] = []
    pending: list[dict] = []
    for f in files:
        for src, sid, idx, u in iter_units(f):
            cn = (u.get("TextCn") or "").strip()
            if not cn or not is_student_line(cn):
                continue
            c = clean(cn)
            if len(c) < 2:
                continue
            rec = {
                "src": src, "story": sid, "idx": idx, "cn": c,
                "jp": clean(u.get("TextJp") or ""),
                "voice": u.get("VoiceJp") or "",
                "bg": u.get("BGName") or "",
            }
            (lines if is_trustworthy(src, sid) else pending).append(rec)

    (OUT / "mika-lines.json").write_text(
        json.dumps(lines, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / "main-needs-review.json").write_text(
        json.dumps(pending, ensure_ascii=False, indent=1), encoding="utf-8")

    by_story: dict[str, list[dict]] = {}
    for l in lines:
        by_story.setdefault(l["story"], []).append(l)

    md = [
        "# 未花台词语料（游戏剧情原文）",
        "",
        "> 来源：碧蓝档案剧情站公开数据（社区翻译，原文带译者/校对署名）",
        f"> 共 {len(lines)} 条 · {len(by_story)} 篇 · 抽取规则见 `extract_mika_lines.py`",
        "",
    ]
    for sid in sorted(by_story):
        ls = by_story[sid]
        md.append(f"\n## {TITLES.get(sid, sid)}  （{len(ls)} 条）\n")
        md.extend(f"- {l['cn']}" for l in ls)
    (OUT / "mika-lines.md").write_text("\n".join(md), encoding="utf-8")

    total = sum(cjk_count(l["cn"]) for l in lines)
    ptotal = sum(cjk_count(l["cn"]) for l in pending)
    print(f"✓ 可信语料（羁绊全篇）：{len(lines)} 条，{total} 汉字")
    print(f"    {OUT / 'mika-lines.md'}")
    print(f"    {OUT / 'mika-lines.json'}")
    print(f"\n△ 待核语料（主线·她在场的章节）：{len(pending)} 条，{ptotal} 汉字")
    print(f"    {OUT / 'main-needs-review.json'}（说话人归属未定，暂不并入语料）")
    print("\n各篇：")
    for sid in sorted(by_story):
        ls = by_story[sid]
        print(f"   {TITLES.get(sid, sid):<24} {len(ls):>4} 条  "
              f"{sum(cjk_count(l['cn']) for l in ls):>6} 汉字")
    if pending:
        print("\n待核语料来源分布：")
        for k, v in Counter(l["src"] for l in pending).most_common():
            print(f"   {k:<8} {v:>5} 条")


if __name__ == "__main__":
    main()
