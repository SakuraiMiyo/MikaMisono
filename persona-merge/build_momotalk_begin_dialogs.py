#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_momotalk_begin_dialogs.py —— 用 MomoTalk 真实短句重做 begin_dialogs

## 为什么要重做

旧的 begin_dialogs 是从**主线剧情**窗口抽的（平均 21 字/句、带场景感），
few-shot 对文风的影响力最大——等于亲手教了模型"用剧情文风打字"。
结果就是它每条回复都写 5~8 段完整长句、还带舞台指示「（抬头，手停在半空，两秒没动）」。

MomoTalk 才是**打字**的真身：平均 8.5 字/条、一句话拆成好几条连发、☆☆☆ 会连甩。

## 规则

- **未花那一边逐字照抄**，一个字不改（`corpus/mika-momotalk.json`）。
- 老师那一边：原文能独立成句的就照用；上下文依赖太强的，**只为让它读起来成句而重写**
  （标了 `adapted`）——因为 few-shot 里老师的台词只是"引子"，重点是她怎么接。
- 输出是 AstrBot `begin_dialogs` 要的扁平数组：偶数个元素，`[0]` 是老师，
  严格 user/assistant 交替，assistant 那一条内部用 `\\n` 表示"连发多条"。

用法：<python> build_momotalk_begin_dialogs.py
输出：begin_dialogs.momotalk.json + begin_dialogs.momotalk.md
"""
from __future__ import annotations

import json
import pathlib

HERE = pathlib.Path(__file__).parent
SRC = HERE.parent / "assets" / "story-cn" / "corpus" / "mika-momotalk.json"
OUT_JSON = HERE / "begin_dialogs.momotalk.json"
OUT_MD = HERE / "begin_dialogs.momotalk.md"

# 未花最多连发几条的默认上限
MAX_BURST = 4

# 挑中的窗口：(老师消息的 id, 覆盖用的老师台词或 None 照用原文, 备注, 该窗口连发上限)
# 上限按话题边界人工定——原作里她换话题时不会打招呼，多吞一条就会把下一段的意思带进来。
#
# ⚠️ 2026-09-24 第二版：按「语气词密度」重选（排序脚本：rank_momotalk_windows.py）。
#    原版漏掉了最富的一条（100590090，9 种语气词：吧/呢/啊/哦/啦/诶/嘿/♪/☆），
#    而那正是 few-shot 最该教的东西——语气词是她人味的地基，比 ☆ 重要得多。
#    同一次补进来的还有 100590230：**全库唯一出现（＞＜）的一条**，
#    提示词里让小表情用（＞＜），few-shot 里就得真有一处，否则那只是个空口号。
SELECTED: list[tuple[int, str | None, str, int]] = [
    (100590090, None, "打招呼 + 诶嘿嘿（语气词最密的一条：诶嘿/吧/啊/呢/哦/啦/♪/☆）", 8),
    (100590290, None, "日常·她主动找人撒娇（～拖长音）", 3),
    (100590230, None, "排满了啊……强撑 + 抱怨（全库唯一的（＞＜）小表情，还有「好——热——啊」）", 5),
    (100590040, "欢迎回来，未花。", "重归学校生活·兴奋（是呀是呀 / 所以说啊 / ☆☆☆）", 4),
    (100590320, None, "撒娇完又反悔·「其实老师可以不来的哦」", 4),
    (100590440, None, "被夸之后·感谢 + 追问（啦☆☆☆☆）", 3),
    (100590480, None, "失落但强撑·连发 6 条，最后就剩单字「老」「师」", 6),
    (100590660, None, "只是想找老师·没有理由", 1),
    (100590700, None, "做了坏事·反复道歉到说不下去", 6),
    (100590770, None, "求和·愧疚到句子都断掉", 4),
    (100590910, "诶！？未花，你刚才是在骗我吗？", "调皮 + 怕被讨厌（核心性格）", 4),
    (101220030, None, "重新打招呼·拘谨 + 怕添麻烦（欸嘿嘿 / 没给老师添麻烦吧？）", 4),
    (101220280, None, "有空·极短的高兴（哇哦〜 / 太好了）", 2),
    (101220380, None, "欸嘿嘿·招牌笑声", 2),
    (101220450, None, "调情 + 自己掩饰（啊哈哈，开玩笑的☆）", 4),
    (101220810, None, "活泼·逗老师（〜 反问连发）", 4),
    (101220940, "那我先睡了，晚安，未花。", "最深情·符号全消失（对照用）", 3),
]


def main() -> None:
    rows = json.loads(SRC.read_text(encoding="utf-8"))
    rows.sort(key=lambda r: r["id"])
    idx = {r["id"]: i for i, r in enumerate(rows)}

    dialogs: list[str] = []
    preview: list[str] = []

    for qid, override, note, cap in SELECTED:
        qi = idx[qid]
        q = rows[qi]
        assert q["speaker"] == "老师", f"{qid} 不是老师发的"

        burst: list[str] = []
        j = qi + 1
        while j < len(rows) and rows[j]["speaker"] != "老师" and len(burst) < cap:
            burst.append(rows[j]["text"])
            j += 1
        assert burst, f"{qid} 后面没有未花的话"

        qtext = override if override is not None else q["text"]
        answer = "\n".join(burst)

        dialogs.append(qtext)
        dialogs.append(answer)

        tag = "（老师那句为改写）" if override else ""
        preview.append(
            f"\n**[{note}]** {tag}\n"
            f"> 老师：{qtext}\n" + "".join(f"> 未花：{b}\n" for b in burst)
            + f"　　（{len(burst)} 条 / {len(answer)} 字）"
        )

    assert len(dialogs) % 2 == 0, "必须偶数条"

    OUT_JSON.write_text(
        json.dumps({"begin_dialogs": dialogs}, ensure_ascii=False, indent=1),
        encoding="utf-8")

    total_mika = sum(1 for i in range(1, len(dialogs), 2))
    chars = sum(len(dialogs[i]) for i in range(1, len(dialogs), 2))
    md = (f"# begin_dialogs（MomoTalk 版）\n\n"
          f"> 来源：`corpus/mika-momotalk.json`（**未花那一边逐字照抄**）。\n"
          f"> {len(dialogs)} 条 / {total_mika} 组；未花侧共 {chars} 字，"
          f"平均 {chars / total_mika:.1f} 字/组。\n"
          f"> 旧版是 66 条剧情台词，平均每句 21 字——那是「说话」，不是「打字」。\n"
          + "\n".join(preview) + "\n")
    OUT_MD.write_text(md, encoding="utf-8")

    print(f"✓ {OUT_JSON.name}：{len(dialogs)} 条（{total_mika} 组）")
    print(f"✓ {OUT_MD.name}：未花侧 {chars} 字，平均 {chars/total_mika:.1f} 字/组")
    print(f"  旧版对照：66 条 / 剧情台词，平均 21 字/句\n")
    print(md)


if __name__ == "__main__":
    main()
