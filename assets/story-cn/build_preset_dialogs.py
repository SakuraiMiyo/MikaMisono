#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_preset_dialogs.py —— 从剧情语料导出 AstrBot 预设对话（原文，不做改写）

## 关键处理：合并连续同人台词

游戏里「老师问一句 → 未花连着好几个对话框回答」是常见结构。
那些对话框本来就是**一段完整的回答**，只是被拆成多个演出单元。
把它们合并成一个 turn，才既符合聊天形态、又能挖出足够长的交替段落。

**合并只发生在同一个人的连续台词之间；老师与未花的话一字不改。**

## 用法

    <python> build_preset_dialogs.py --list          # 列出全部候选窗口
    <python> build_preset_dialogs.py --build         # 按 SELECTED 导出 JSON
"""
from __future__ import annotations

import json
import pathlib
import sys
from collections import defaultdict

ROOT = pathlib.Path(__file__).parent
TURNS = ROOT / "corpus" / "mika-turns.json"
OUT = ROOT.parents[1] / "persona-merge" / "预设对话.begin_dialogs.json"

SENSEI, MIKA = "老师", "未花"
MAX_CHARS = 90          # 合并后单轮上限；超了就在句号处切开

# ── 人工挑选： (故事ID, 窗口起始 idx, 从第几轮, 到第几轮) ────────────────────
# 全部为剧情原文，只做了「同一人的连续台词合并」，一字未改。
# 区间是挑过的：每段的**第一句都必须是意思完整的老师台词**，
# 这样几段拼起来当对话历史读不会跳戏。
SELECTED: list[tuple[str, int, int, int]] = [
    ("100592", 11, 0, 10),    # 重归平稳的日常：出狱后的日常、牢骚
    ("100593", 3, 0, 10),     # 义务劳动：300 小时义工、「一个人做吗？」
    ("100595", 5, 0, 10),     # 阁楼里的公主殿下：瑞士卷、阁楼、「特殊待遇吧？」
    ("100596", 7, 8, 22),     # 伤痕：老师带她去补泳衣 → 泳池
    ("101229", 4, 0, 10),     # 已经，没关系了：三明治、「我好像有点变了」
    ("31170", 3, 10, 22),     # 圣三一的叛徒：「我也是未花的同伴」→ 摊牌
]


def merge_runs(ts: list[dict]) -> list[dict]:
    """把同一个人的连续台词合并成一个 turn。"""
    out: list[dict] = []
    for x in ts:
        if out and out[-1]["speaker"] == x["speaker"]:
            out[-1]["text"] += x["text"]
            out[-1]["idx_end"] = x["idx"]
        else:
            out.append({"speaker": x["speaker"], "text": x["text"],
                        "idx": x["idx"], "idx_end": x["idx"]})
    return out


def split_long(speaker: str, text: str) -> list[str]:
    """⚠️ 已弃用。

    曾想把过长的台词在句末切开——**那是错的**：切成多条会让同一个人的话
    占到两个相邻槽位，`begin_dialogs` 的 user/assistant 交替就断了。
    窗口太长就换窗口或少取几轮，**不要切句子**。
    """
    return [text]


# ── 小表情标注层（2026-09-24）───────────────────────────────────────────
# 预设对话用在 MomoTalk / QQ 场景，所以按聊天口气铺 ☆ / ♪。
#
# 依据（corpus/mika-momotalk.json，193 条真实聊天记录）：
#   · ☆ 是她的主力符号；原作里出现过整条的 `☆`，也有连排
#   · ♪ 明显更少，只在对老师软软撒娇时冒出来
#   · 低落、道歉、正经谈事（摊牌那段）**一个都不用**——
#     亮的地方越满，安静的地方才越有效
#
# 当前密度：33 轮未花台词里 **18 轮**带符号，合计 ☆ 33 个 / ♪ 2 个。
# 连排只留 `☆☆`，不用更长。
#
# 键是 begin_dialogs 的下标（奇数 = 未花），值是 (原文片段 → 加完表情的片段)。
# 只加表情，**不动任何台词内容**。
EMOJI: dict[int, list[tuple[str, str]]] = {
    1:  [("去购物！", "去购物！☆"),
         ("天气真好……", "天气真好☆……"),
         ("比较舒适呢！", "比较舒适呢！☆")],
    3:  [("还是很开心啦。", "还是很开心啦☆"),
         ("应该很快就能习惯了！", "应该很快就能习惯了！☆")],
    5:  [("大概就这些？", "大概就这些？☆")],
    7:  [("感觉好压抑啊！", "感觉好压抑啊！☆")],
    9:  [("好了！出发去购物吧！", "好了！出发去购物吧！☆"),
         ("之前用的那些都已经没了。", "之前用的那些都已经没了。☆")],
    21: [("我也知道老师很忙嘛。", "我也知道老师很忙嘛☆"),
         ("没事的没事的。", "没事的没事的♪")],
    27: [("我没别的意思啦！", "我没别的意思啦！☆"),
         ("这边这边！", "这边这边！☆")],
    29: [("到啦——！", "到啦——！☆")],
    33: [("这样合适吗？", "这样合适吗？☆")],
    35: [("好看吗？", "好看吗？☆"),
         ("是吧是吧？？", "是吧是吧？？☆☆")],
    37: [("这可是女学生穿着泳装哦？", "这可是女学生穿着泳装哦？☆"),
         ("我是会伤心的哦。", "我是会伤心的哦☆")],
    39: [("感觉还挺不好意思的……", "感觉还挺不好意思的……☆")],
    41: [("老师要下来吗？", "老师要下来吗？☆")],
    47: [("尝尝看吧！", "尝尝看吧♪")],
    49: [("肯定会很好吃的嘛～！", "肯定会很好吃的嘛～！☆")],
    51: [("……诶嘿嘿。", "……诶嘿嘿☆")],
    57: [("……哇～哦。", "……哇～哦☆"),
         ("欸嘿嘿……", "欸嘿嘿☆……")],
    # 刻意留白、一个符号都不加的：
    #   11 拘谨 / 13 陈述处分 / 15 大段抱怨 / 17 追问 / 19 嘴硬 / 23 说不出口 /
    #   25 小心邀请 / 43 慌张 / 45 紧张 / 53 成长告白 / 55 被击中 / 59·61·63·65 摊牌
}


def apply_emoji(lines: list[str]) -> tuple[list[str], int]:
    """按 EMOJI 表加小表情，返回 (新列表, 实际改动数)。"""
    out = list(lines)
    n = 0
    for idx, pairs in EMOJI.items():
        if idx >= len(out):
            continue
        for old, new in pairs:
            if old not in out[idx]:
                print(f"  ⚠ 第 {idx} 轮里找不到 {old!r}")
                continue
            out[idx] = out[idx].replace(old, new, 1)
            n += 1
    return out, n


def windows(ts: list[dict], min_len: int = 4) -> list[list[dict]]:
    out = []
    i = 0
    while i < len(ts):
        if ts[i]["speaker"] != SENSEI:
            i += 1
            continue
        want, j, seq = SENSEI, i, []
        while j < len(ts) and ts[j]["speaker"] == want:
            seq.append(ts[j])
            want = MIKA if want == SENSEI else SENSEI
            j += 1
        if len(seq) % 2:
            seq = seq[:-1]
        if len(seq) >= min_len:
            out.append(seq)
        i = max(j, i + 1)
    return out


def main() -> None:
    turns = json.loads(TURNS.read_text(encoding="utf-8"))
    by_story: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for t in turns:
        if t["speaker"] in (SENSEI, MIKA):
            by_story[(t["cat"], t["story"])].append(t)

    allwin: list[dict] = []
    for (cat, sid), raw in by_story.items():
        merged = merge_runs(raw)
        for w in windows(merged):
            allwin.append({"cat": cat, "story": sid,
                           "title": raw[0]["story_title"],
                           "start": w[0]["idx"],
                           "turns": [(x["speaker"], x["text"]) for x in w]})

    if "--list" in sys.argv or not SELECTED:
        allwin.sort(key=lambda w: -len(w["turns"]))
        print(f"合并后可用窗口 {len(allwin)} 个\n")
        for n, w in enumerate(allwin):
            tot = sum(len(t[1]) for t in w["turns"])
            print(f"[{n}] {w['cat']}/{w['story']} {w['title'][:20]}  "
                  f"{len(w['turns'])}轮 {tot}字  (idx {w['start']})")
            for sp, tx in w["turns"]:
                print(f"    {'师' if sp == SENSEI else '花'}| {tx[:70]}")
            print()

    if "--build" not in sys.argv:
        return

    lines: list[str] = []
    used = []
    for sid, start, a, b in SELECTED:
        hit = next((w for w in allwin
                    if w["story"] == sid and w["start"] == start), None)
        if not hit:
            print(f"  ✗ 找不到 {sid} idx {start}")
            continue
        used.append((hit, a, b))
        for sp, tx in hit["turns"][a:b]:
            lines.append(tx)

    # 尾部若停在老师，补一条未花的短回应，保证偶数
    if len(lines) % 2:
        lines.append("……嗯。")

    plain = list(lines)
    lines, n_emoji = apply_emoji(lines)

    # 无表情版也留一份，方便对比 / 回退
    (OUT.parent / "预设对话.begin_dialogs.plain.json").write_text(
        json.dumps({"begin_dialogs": plain}, ensure_ascii=False, indent=1),
        encoding="utf-8")

    OUT.write_text(json.dumps(
        {"_来源": "assets/story-cn/corpus/mika-turns.json（剧情原文）",
         "_改动": "仅合并同一人的连续台词；并按 MomoTalk 实测密度补入 ☆ / ♪ 小表情，未改动台词内容",
         "_说明": "AstrBot begin_dialogs：偶数条，user(老师)/assistant(未花) 交替",
         "begin_dialogs": lines}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n✓ 导出 {len(lines)} 条 / {sum(len(x) for x in lines)} 字 → {OUT.name}")
    star = sum(x.count("☆") for x in lines)
    note = sum(x.count("♪") for x in lines)
    print(f"  小表情：☆ {star} 个 / ♪ {note} 个（本次新加 {n_emoji} 处）")
    print(f"  无表情版 → 预设对话.begin_dialogs.plain.json")
    print("  用了这些窗口（全部剧情原文）：")
    for w, a, b in used:
        print(f"    {w['cat']}/{w['story']} {w['title'][:20]}  第 {a}–{b} 轮")


if __name__ == "__main__":
    main()
