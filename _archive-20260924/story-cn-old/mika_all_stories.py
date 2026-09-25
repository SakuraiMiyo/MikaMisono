#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mika_all_stories.py —— 未花全剧情提取器（Vol.3 + 活动 + 羁绊，标注她的台词）

## 数据来源

碧蓝档案剧情站（ba-archive）公开预览数据：
    https://preview.blue-archive.io/story/{type}/{[前5位/]id}.json
  · main / other  →  不带目录层
  · favor / event / group / mini  →  带 groupId 前 5 位作目录
  ⚠️ 必须带浏览器 User-Agent（Cloudflare）

## 抽取清单

  Vol.3 伊甸条约篇    主线 32xxx / 33xxx 全部
  泳装夏活「海边的袭击者」 other 210
  原版羁绊 1-4 话     favor 100592 / 100593 / 100595 / 100596
  泳装羁绊 1-6 话     favor 101222 / 101223 / 101225 / 101226 / 101228 / 101229

## 输出（`assets/story-cn/`）

  raw/…              各剧情的原始 JSON（带中日对照、译者署名）
  corpus/mika-all.md 可读全文，**未花的台词用 `★` 标注并加粗**
  corpus/mika-all.json  结构化（每条台词带 speaker 判定与置信度）

## 说话人判定（保守，宁缺勿错）

  单元文本前缀决定说话人：
    `[s]` `[s1]` …  → 老师        → 标 `老师`
    `[ns]` `[ns3]` …→ 旁白        → 标 `旁白`
    无前缀          → 场景里的学生 → 需要判断是不是未花：
        · 在未花的羁绊剧情里（场景只有她和老师）→ `未花`，high
        · 一行里出现「未花」二字                 → `未花`，high
        · 其余学生台词                           → `学生`，low（不确定是谁）
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

import httpx

ROOT = pathlib.Path(r"C:\OneDrive\MikaMisono\assets\story-cn")
RAW_DIR = ROOT / "raw"
CORPUS = ROOT / "corpus"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"}
HOST = "https://preview.blue-archive.io"

# ── 抽取清单 ───────────────────────────────────────────────────────────────
VOL3_MAIN = [32010 + i for i in range(0, 220, 10)] + [33010 + i for i in range(0, 250, 10)]
VOL3_MAIN = sorted(set(i for i in VOL3_MAIN if i <= 33250))

TARGETS: list[tuple[str, str, str, str]] = []   # (type, id, 分类, 标题)
for sid in VOL3_MAIN:
    TARGETS.append(("main", str(sid), "Vol.3", ""))
TARGETS.append(("other", "210", "活动", "海边的袭击者（泳装夏活）"))

FAVOR_BASE = {"100592": "第1话 重归平稳的日常", "100593": "第2话 义务劳动",
              "100595": "第3话 阁楼里的公主殿下", "100596": "第4话 伤痕"}
FAVOR_SWIM = {"101222": "第1话 连自己都不了解的自己", "101223": "第2话 课程的后续",
              "101225": "第3话 海滩上发光的东西", "101226": "第4话 从蹒跚学步的我开始……",
              "101228": "第5话 致某时某刻的自己", "101229": "第6话 已经，没关系了"}
for sid, title in FAVOR_BASE.items():
    TARGETS.append(("favor", sid, "原版羁绊", title))
for sid, title in FAVOR_SWIM.items():
    TARGETS.append(("favor", sid, "泳装羁绊", title))

SENSEI_RE = re.compile(r"^\[s\d*\]")
NARR_RE = re.compile(r"^\[[nN][sS]?\d*\]")
ANY_TAG = re.compile(r"^\[[^\]]{0,24}\]")


def url_for(kind: str, sid: str) -> str:
    if kind in ("main", "other"):
        return f"{HOST}/story/{kind}/{sid}.json"
    return f"{HOST}/story/{kind}/{sid[:5]}/{sid}.json"


def clean(t: str) -> str:
    t = (t or "").replace("#n", "\n").strip()
    t = ANY_TAG.sub("", t).strip()
    t = re.sub(r"^[（(][^）)]{0,60}[）)]\s*", lambda m: m.group(0) if "未花" in m.group(0) else "", t)
    return t.strip().strip('"').strip("“”").strip()


def classify(text_cn: str, is_mika_story: bool, is_first: bool) -> tuple[str, str]:
    """返回 (说话人, 置信度)。

    ⚠️ 关键坑（2026-09-24 修正）：**不能因为一句里出现「未花」就判成她在说**——
    旁白经常就在描述「未花同学怎么了」。判序：

      1. `[s*]`  前缀 → 老师
      2. `[ns*]` 前缀 → 旁白
      3. 首单元（idx 0）→ 章节标题
      4. 第三人称提到未花 → 旁白（"未花同学…"／"给未花…"）
      5. 其余无前缀：
           · 未花的羁绊剧情（场景只有她和老师）→ 未花，high
           · 群像场景                          → 学生，low（无法确定）
    """
    t = text_cn.strip()
    if SENSEI_RE.match(t):
        return "老师", "high"
    if NARR_RE.match(t):
        return "旁白", "high"
    if is_first:
        return "标题", "high"
    if is_mika_story:
        # 羁绊剧情：场景里只有她和老师，无前缀台词就是她
        if re.search(r"未花(同学|酱|ちゃん)", t) or t.startswith("给未花"):
            return "旁白", "high"
        return "未花", "high"
    # 主线：源数据**没有**说话人字段，无前缀台词无法确定是谁
    return "台词", "none"


def fetch(c: httpx.Client, kind: str, sid: str) -> dict | None:
    try:
        r = c.get(url_for(kind, sid), timeout=60)
        if r.status_code != 200:
            return None
        return r.json()
    except Exception as e:
        print(f"    ✗ {kind}/{sid}: {type(e).__name__}")
        return None


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    CORPUS.mkdir(parents=True, exist_ok=True)
    c = httpx.Client(headers=UA, timeout=60, follow_redirects=True)

    all_units: list[dict] = []
    missing: list[str] = []
    seen: set[tuple[str, str]] = set()

    for kind, sid, cat, title in TARGETS:
        if (kind, sid) in seen:
            continue
        seen.add((kind, sid))
        j = fetch(c, kind, sid)
        if not j or not isinstance(j, dict) or "content" not in j:
            missing.append(f"{kind}/{sid}")
            continue

        out = RAW_DIR / cat
        out.mkdir(parents=True, exist_ok=True)
        (out / f"{sid}.json").write_text(
            json.dumps(j, ensure_ascii=False, indent=1), encoding="utf-8")

        is_mika_story = cat.endswith("羁绊")
        for i, u in enumerate(j["content"]):
            cn = (u.get("TextCn") or "").strip()
            if not cn:
                continue
            who, conf = classify(cn, is_mika_story, i == 0)
            body = clean(cn)
            if not body or len(body) < 2 or who == "标题":
                continue
            all_units.append({
                "cat": cat, "kind": kind, "story": sid, "title": title,
                "idx": i, "speaker": who, "conf": conf,
                "cn": body, "jp": clean(u.get("TextJp") or ""),
                "voice": u.get("VoiceJp") or "",
            })

    (CORPUS / "mika-all.json").write_text(
        json.dumps(all_units, ensure_ascii=False, indent=1), encoding="utf-8")

    # ── 生成可读全文 ──────────────────────────────────────────────────────
    groups: dict[tuple[str, str], list[dict]] = {}
    for u in all_units:
        groups.setdefault((u["cat"], u["story"]), []).append(u)

    md: list[str] = ["# 未花 · 全剧情原文（中文）", "",
                     "> 来源：碧蓝档案剧情站公开数据（社区翻译）",
                     "> **`★` 开头的是未花的台词**（加粗）；`老师` / `旁白` / `学生` 为其他角色。",
                     "> 标注规则见 `mika_all_stories.py`；`学生` 表示群像场景中无法确定说话人。", ""]
    mika_total = 0
    for (cat, sid), us in groups.items():
        title = us[0]["title"] or sid
        mika_n = sum(1 for u in us if u["speaker"] == "未花")
        mika_total += mika_n
        md.append(f"\n---\n\n## [{cat}] {sid} {title}  （{len(us)} 句 / 未花 {mika_n} 句）\n")
        for u in us:
            if u["speaker"] == "未花":
                md.append(f"**★（未花）** {u['cn']}")
            else:
                md.append(f"（{u['speaker']}）{u['cn']}")
    (CORPUS / "mika-all.md").write_text("\n\n".join(md), encoding="utf-8")

    # ── 只含未花台词的干净语料 ─────────────────────────────────────────────
    mika_lines = [u for u in all_units if u["speaker"] == "未花"]
    (CORPUS / "mika-only.json").write_text(
        json.dumps(mika_lines, ensure_ascii=False, indent=1), encoding="utf-8")
    (CORPUS / "mika-only.md").write_text(
        "# 未花台词（仅她本人的）\n\n" +
        "\n".join(f"- {u['cn']}" for u in mika_lines), encoding="utf-8")

    def cjk(s: str) -> int:
        return sum(1 for ch in s if "\u4e00" <= ch <= "\u9fff")

    print(f"\n✓ 共提取 {len(all_units)} 句")
    print(f"  其中未花 ${mika_total} 句 / {sum(cjk(u['cn']) for u in mika_lines)} 汉字")
    print(f"\n  corpus/mika-all.md    全文（未花标 ★）")
    print(f"  corpus/mika-only.md   只有她的台词")
    print(f"  corpus/mika-all.json  结构化全量")
    print(f"  raw/                  原始 JSON（中日对照 + 译者署名）")
    if missing:
        print(f"\n△ 未取到 {len(missing)} 个：{' '.join(missing[:20])}")
    print("\n分类统计：")
    from collections import Counter
    cnt = Counter(u["cat"] for u in all_units)
    mik = Counter(u["cat"] for u in mika_lines)
    for k, v in cnt.most_common():
        print(f"   {k:<10} {v:>5} 句   未花 {mik.get(k,0):>5} 句")


if __name__ == "__main__":
    main()
