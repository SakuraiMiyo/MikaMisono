#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_corpus.py —— 从未花剧情原文构建「蒸馏用」语料

## 输入

    raw/Vol.3/*.json          Vol.3 伊甸条约篇 全 76 节
    raw/原版羁绊/*.json        未花原版羁绊 1-4 话
    raw/泳装羁绊/*.json        未花泳装羁绊 1-6 话
    raw/其他/*.json            任务剧情（未花未出场，仅存档）

## 说话人判定（`ba_speaker.speaker_of_unit`）

  ScriptKr 里 `{槽位};{角色};{表情};{台词}` 形式 → **精确说话人**（主力）
  中文侧 `[s]`   → 老师
  中文侧 `[ns]`  → 旁白
  中文侧 `[sN]`  → 多角色共用文本框，说话人未标明（置信度 none）
  其余           → 未知

## 输出（`corpus/`）

  mika-turns.json       全部对话轮（含出处、说话人、立绘表情、背景、BGM）
  mika-only.md/.json    ★ 只有未花说的话（895 句）
  mika-scenes.jsonl     未花参与的对话场景窗口（含对手台词）—— RAG / 风格模仿
  mika-pairs.jsonl      (上下文 → 未花回应) 对 —— SFT 最直接
  vol3-full.md          Vol.3 全文，未花台词标 ★
  favor-full.md         10 话羁绊全文，未花台词标 ★
  stats.json            统计

## 用法

    <python> build_corpus.py
"""
from __future__ import annotations

import json
import pathlib
import re
from collections import Counter, defaultdict

import ba_speaker as bs

ROOT = pathlib.Path(r"C:\OneDrive\MikaMisono\assets\story-cn")
RAW = ROOT / "raw"
OUT = ROOT / "corpus"
OUT.mkdir(parents=True, exist_ok=True)

# 卷 → 展示顺序 / 中文名
CAT_ORDER = {"Vol.3": 0, "原版羁绊": 1, "泳装羁绊": 2, "其他": 3}
CAT_LABEL = {"Vol.3": "Vol.3 伊甸条约篇", "原版羁绊": "原版羁绊剧情",
             "泳装羁绊": "泳装羁绊剧情", "其他": "任务剧情"}

# ⚠️ 立绘编号（ScriptKr 第 3 段）**不是情绪标签**——实测同一个编号下
# 既有狂笑也有冷淡，它只是立绘资源号。真正的情绪在那个角色的 `#N;em;[X]`
# 气泡命令里（见 `ba_speaker.EMOTE_CN`），不要拿立绘号当情绪用。

WINDOW = 3          # (上下文 → 未花这一句) 里留几轮上下文

BOX_TAG = re.compile(r"^\[(s|ns)(\d*)\]\s*")


def split_boxes(raw_cn: str) -> list[tuple[str | None, str]]:
    """把「一个单元里塞了好几个文本框」拆开。

    例：`'[s1] “我把你带出那片黑暗的。”\\n[s2] “然后，我绝对会……'`
    → `[('[s1]', '我把你带出那片黑暗的。'), ('[s2]', '然后，我绝对会……')]`

    不拆的话两句会粘成一句，既污染文本也丢说话人。
    """
    out: list[tuple[str | None, str]] = []
    cur_tag: str | None = None
    buf: list[str] = []

    def flush():
        if any(x.strip() for x in buf):
            out.append((cur_tag, "\n".join(buf)))

    for line in raw_cn.split("\n"):
        m = BOX_TAG.match(line)
        if m:
            flush()
            buf.clear()
            cur_tag = m.group(0).strip()
            buf.append(line[m.end():])
        else:
            buf.append(line)
    flush()
    return out


def load_turns() -> list[dict]:
    turns: list[dict] = []
    for cat, order in sorted(CAT_ORDER.items(), key=lambda kv: kv[1]):
        d = RAW / cat
        if not d.exists():
            continue
        for f in sorted(d.glob("*.json")):
            j = json.loads(f.read_text(encoding="utf-8"))
            content = j.get("content", [])
            # 羁绊文件的 `GroupId` 是「组+话」的长号（1005902），
            # 对外统一成剧情站索引里的 6 位 groupId（100592），免得下游对不上。
            if cat.endswith("羁绊"):
                story_id = f.stem.split("_")[0]
            else:
                story_id = str(j.get("GroupId", f.stem.split("_")[0]))
            title_cn = title_jp = ""
            for u in content:
                t = (u.get("TextCn") or "").strip()
                if t and not t.startswith("["):
                    title_cn = t.replace("#n", " ").strip()
                    title_jp = (u.get("TextJp") or "").replace("#n", " ").strip()
                    break
            for i, u in enumerate(content):
                raw_cn = (u.get("TextCn") or "").strip()
                if not raw_cn or i == 0 or raw_cn.startswith("#title"):
                    continue                        # 空行 / 章节标题行
                kr, kr_cn, sprite = bs.parse_speaker(u.get("ScriptKr") or "")
                emotes = bs.parse_emotes(u.get("ScriptKr") or "", kr)
                for bi, (tag, chunk) in enumerate(split_boxes(raw_cn)):
                    text = bs.clean_text(chunk)
                    if not text:
                        continue
                    if tag is None:
                        who, conf = (kr_cn, "high") if kr else ("未知", "none")
                    elif tag == "[s]":
                        who, conf = "老师", "high"
                    elif tag.startswith("[ns"):
                        who, conf = "旁白", "high"
                    else:                            # [s1][s2]… 说话人未标明
                        who, conf = "（未标明）", "none"
                    turns.append({
                        "cat": cat, "story": story_id, "story_title": title_cn,
                        "story_title_jp": title_jp, "idx": i, "box": bi,
                        "speaker": who, "speaker_kr": kr, "conf": conf,
                        "sprite": sprite,           # 立绘资源号（不是情绪）
                        "emote": emotes if bi == 0 else [],
                        "text": text, "jp": bs.clean_text(u.get("TextJp") or ""),
                        "bg": u.get("BGName") or "", "bgm": u.get("BGMId") or 0,
                        "mika": bs.is_mika(kr),
                    })
    return turns


def mika_name(kr: str | None) -> str:
    return {"미카 수영복": "未花（泳装）", "미카 비무장": "未花（无武装）",
            "미카 케이프오프": "未花（披风）", "미카 학교 체육복": "未花（体育服）",
            "미카 학교 수영복": "未花（学校泳装）"}.get(kr or "", "未花")


def build_scenes(turns: list[dict]) -> list[dict]:
    """按「故事 + 场景（bg/bgm 变化或标题）切分」，取未花参与的窗口。"""
    scenes: list[dict] = []
    by_story: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for t in turns:
        by_story[(t["cat"], t["story"])].append(t)

    for (cat, sid), ts in by_story.items():
        # 切场景
        cuts = [0]
        for i in range(1, len(ts)):
            a, b = ts[i - 1], ts[i]
            if (a["bg"], a["bgm"]) != (b["bg"], b["bgm"]):
                cuts.append(i)
        cuts.append(len(ts))
        for s, e in zip(cuts, cuts[1:]):
            seg = ts[s:e]
            if not any(x["mika"] for x in seg):
                continue
            scenes.append({
                "cat": cat, "story": sid, "story_title": seg[0]["story_title"],
                "mika_lines": sum(1 for x in seg if x["mika"]),
                "bg": seg[0]["bg"], "bgm": seg[0]["bgm"],
                "turns": [{"sp": x["speaker"], "t": x["text"],
                           "emote": x["emote"] if x["mika"] else None}
                          for x in seg],
            })
    return scenes


def build_pairs(turns: list[dict]) -> list[dict]:
    """(前面 N 轮上下文 → 未花这一句) —— SFT 最直接可用的形状。"""
    pairs: list[dict] = []
    by_story: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for t in turns:
        by_story[(t["cat"], t["story"])].append(t)
    for (cat, sid), ts in by_story.items():
        for i, t in enumerate(ts):
            if not t["mika"]:
                continue
            ctx = [{"sp": x["speaker"], "t": x["text"]}
                   for x in ts[max(0, i - WINDOW):i]]
            pairs.append({
                "cat": cat, "story": sid, "story_title": t["story_title"],
                "context": ctx, "reply": t["text"],
                "reply_jp": t["jp"], "emote": t["emote"],
                "sprite": t["sprite"],
                "mika_name": mika_name(t["speaker_kr"]),
            })
    return pairs


def cjk(s: str) -> int:
    return bs.cjk_len(s)


def main() -> None:
    turns = load_turns()
    mika = [t for t in turns if t["mika"]]
    print(f"总对话轮 {len(turns)}；未花 {len(mika)} 轮 / {sum(cjk(t['text']) for t in mika)} 汉字")

    (OUT / "mika-turns.json").write_text(
        json.dumps(turns, ensure_ascii=False, indent=1), encoding="utf-8")

    # ── 只有未花的台词 ────────────────────────────────────────────────────
    (OUT / "mika-only.json").write_text(
        json.dumps(mika, ensure_ascii=False, indent=1), encoding="utf-8")

    lines = ["# 未花台词全集（仅她本人说的话）", "",
             f"> {len(mika)} 句 / {sum(cjk(t['text']) for t in mika)} 汉字",
             "> 说话人由游戏韩文演出脚本 `ScriptKr` 的 `槽位;角色;表情;台词` 精确判定，"
             "非猜测。", ""]
    cur = None
    for t in mika:
        key = (t["cat"], t["story"])
        if key != cur:
            cur = key
            n = sum(1 for x in mika if (x["cat"], x["story"]) == key)
            lines += ["", f"## [{t['cat']}] {t['story']} {t['story_title']}"
                         f"　（未花 {n} 句）", ""]
        tail = f"　`{'/'.join(t['emote'])}`" if t["emote"] else ""
        lines.append(f"- {t['text']}{tail}")
    (OUT / "mika-only.md").write_text("\n".join(lines), encoding="utf-8")

    # ── 场景窗口 ──────────────────────────────────────────────────────────
    scenes = build_scenes(turns)
    with (OUT / "mika-scenes.jsonl").open("w", encoding="utf-8") as fh:
        for s in scenes:
            fh.write(json.dumps(s, ensure_ascii=False) + "\n")

    # ── 上下文→回应 对 ────────────────────────────────────────────────────
    pairs = build_pairs(turns)
    with (OUT / "mika-pairs.jsonl").open("w", encoding="utf-8") as fh:
        for p in pairs:
            fh.write(json.dumps(p, ensure_ascii=False) + "\n")

    # ── 全文（未花标 ★）──────────────────────────────────────────────────
    for cat, fname in (("Vol.3", "vol3-full.md"), ("原版羁绊", "favor-full.md"),
                       ("泳装羁绊", "favor-swim-full.md")):
        ts = [t for t in turns if t["cat"] == cat]
        if not ts:
            continue
        md = [f"# {CAT_LABEL[cat]}　全文（★ = 未花台词）", "",
              "> 来源：碧蓝档案剧情站公开数据（社区中译）；说话人取自韩文演出脚本。", ""]
        cur = None
        for t in ts:
            if (t["cat"], t["story"]) != cur:
                cur = (t["cat"], t["story"])
                n = sum(1 for x in ts if (x["cat"], x["story"]) == cur and x["mika"])
                md += ["", f"\n---\n", f"## {t['story']} {t['story_title']}"
                                      f"　（未花 {n} 句）", ""]
            if t["mika"]:
                md.append(f"**★【{mika_name(t['speaker_kr'])}】** {t['text']}")
            elif t["speaker"] == "旁白":
                md.append(f"*（旁白）{t['text']}*")
            else:
                md.append(f"**{t['speaker']}**：{t['text']}")
        (OUT / fname).write_text("\n\n".join(md), encoding="utf-8")

    # ── 统计 ──────────────────────────────────────────────────────────────
    stats = {
        "total_turns": len(turns),
        "mika_turns": len(mika),
        "mika_cjk": sum(cjk(t["text"]) for t in mika),
        "mika_avg_len": round(sum(len(t["text"]) for t in mika) / max(1, len(mika)), 2),
        "by_cat": {},
        "mika_variants": dict(Counter(t["speaker_kr"] for t in mika)),
        "emote_dist": dict(Counter(
            e for t in mika for e in t["emote"]).most_common()),
        "speaker_top": dict(Counter(t["speaker"] for t in turns).most_common(30)),
        "unknown_ratio": round(
            sum(1 for t in turns if t["conf"] == "none") / max(1, len(turns)), 4),
        "scenes": len(scenes),
        "pairs": len(pairs),
    }
    for cat in CAT_ORDER:
        ts = [t for t in turns if t["cat"] == cat]
        mk = [t for t in ts if t["mika"]]
        stats["by_cat"][cat] = {"turns": len(ts), "mika": len(mk),
                                "mika_cjk": sum(cjk(t["text"]) for t in mk),
                                "stories": len({t["story"] for t in ts})}
    (OUT / "stats.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=1), encoding="utf-8")

    # ── 未花出场清单（下游选材用）────────────────────────────────────────
    index = []
    for cat in CAT_ORDER:
        for sid in sorted({t["story"] for t in turns if t["cat"] == cat}):
            ts = [t for t in turns if t["cat"] == cat and t["story"] == sid]
            mk = [t for t in ts if t["mika"]]
            if not mk:
                continue
            index.append({
                "cat": cat, "story": sid, "story_title": ts[0]["story_title"],
                "story_title_jp": ts[0]["story_title_jp"],
                "turns": len(ts), "mika": len(mk),
                "mika_cjk": sum(cjk(t["text"]) for t in mk),
                "variants": sorted({t["speaker_kr"] for t in mk}),
                "co_stars": [k for k, _ in Counter(
                    t["speaker"] for t in ts if not t["mika"]).most_common(6)],
            })
    (ROOT / "mika-story-index.json").write_text(
        json.dumps({"mika_total": len(mika),
                    "mika_cjk_total": sum(cjk(t["text"]) for t in mika),
                    "stories": index}, ensure_ascii=False, indent=1),
        encoding="utf-8")

    print(json.dumps({k: v for k, v in stats.items()
                      if k in ("by_cat", "mika_variants", "emote_dist",
                               "scenes", "pairs", "unknown_ratio",
                               "mika_avg_len")},
                     ensure_ascii=False, indent=1))
    print(f"\n→ {OUT}")


if __name__ == "__main__":
    main()
