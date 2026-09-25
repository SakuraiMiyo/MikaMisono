# -*- coding: utf-8 -*-
"""check_feelings.py —— `feelings` 里的条目不能只是光秃秃的名词

## 为什么要单独查这个

`verify_cards.py` 的语气指标是**按整卡句数**算的。`feelings` 里全是两个字的形容词
（「幸福」「甜蜜」「认真」「无奈」）时，那些条目把分母撑大、又不贡献语气词，
但因为 `events`/`decisions` 写够了，整卡百分比照样能过线——
**指标掩盖了这一类没改到的地方。**

规范里写得很清楚：`feelings` 不是「我好开心呀」，而是**被记录下来的反应**
（「心里烫了一下」「脑子不飘了，手也稳了」这种）。这一类要单独量。

## 判据（对应规范 §三「feelings 单独立规矩」）

一条 `feeling` 合格，必须**是一个具体反应**，不是**情绪的名字**。合格形状三种：

  A. **身体感觉** —— 出现身体部位/身体词：心里、脑子、手、脸、眼、胸口、喉咙、腿、
     后背、心跳、抖、烫、烧、凉、酸、紧、僵……
  B. **动作或决定** —— 出现把情绪落到行为上的词：记、不、别、想、要、该、得、决定、
     说、答应、认、拦、忍、走、留、藏、告诉……
  C. **挂件具体物** —— 含省略号、或长度 ≥ 12 且含逗号（说明有从句，不是单个标签）

不合格（= "光秃秃的名词"）：只有情绪词本身，**不管加不加「呀」「呢」「得不行」**。
「开心得不行」「充实呢」「原谅了」这类**加了语气词但没内容**的，一样不合格。

用法：<python> check_feelings.py [--before <改前目录>]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

sys.stdout.reconfigure(encoding="utf-8")

CARDS = pathlib.Path(r"C:\OneDrive\MikaMisono\agent\memory\cards")
BAK_DEFAULT = pathlib.Path(
    r"C:\OneDrive\MikaMisono\_archive-20260924"
    r"\cards-before-voicefix-20260926-014224\cards"
)

# A 身体感觉
BODY = ("心里", "脑子", "脑袋", "手", "脸", "眼", "胸口", "喉咙", "腿", "后背", "肩",
        "心跳", "抖", "烫", "烧", "凉", "酸", "紧", "僵", "喘", "鼻", "耳", "怀")
# B 动作或决定
ACT = ("记", "不", "别", "想", "要", "该", "得", "决定", "说", "答应", "认",
       "拦", "忍", "走", "留", "藏", "告诉", "选", "给", "拿", "放")
# 纯情绪标签（就算加了语气词也还是标签）
LABEL = ("开心", "幸福", "感动", "甜蜜", "害羞", "紧张", "期待", "无奈", "震惊",
         "惊喜", "温暖", "坚定", "充实", "得意", "生气", "心虚", "难为情", "满足",
         "欣慰", "安心", "踏实", "激动", "平静", "可惜", "好奇", "认真", "尊重",
         "热闹", "多彩", "复杂", "纠结")


# 具体名词：出现就说明这条挂着"东西"，不是纯情绪
THINGS = ("饭", "图", "钱", "机器", "电脑", "衣服", "手办", "日记", "字", "话", "题",
          "课", "车", "门", "床", "桌子", "杯子", "药", "酒", "雨", "雪", "风", "太阳",
          "星", "海", "沙滩", "包", "手机", "屏幕", "线", "路", "灯", "窗", "墙",
          "域", "名", "号", "测试", "考试", "报告", "项目", "实验", "数据", "照片")
# 人称：和动作一起出现才算"有事"
PERSON = ("他", "她", "我", "你", "老师", "群友", "大家")
# 动作：说明确实发生了什么
VERB = ("吃", "喝", "睡", "醒", "走", "来", "去", "看", "读", "写", "说", "问", "答",
        "给", "拿", "放", "跑", "做", "改", "修", "打", "抱", "叫", "夸", "骂", "笑",
        "哭", "等", "陪", "劝", "拦", "藏", "买", "卖", "换", "丢", "忘", "记", "翻")
# 意图 / 自我约束（B 形状的语法标记）：没有这些，
# 「不想变成仗着温柔乱咬人的人」这种会把「变成…」当成普通名词、误判成标签
GRAMMAR = ("不想", "不会", "不许", "不肯", "不愿", "不该", "不打算", "不准备",
           "要记", "说什么也", "再也", "非…不可", "只能", "只好", "宁可", "绝不")


def _has_concrete(residue: str) -> bool:
    """剥掉情绪词之后，剩下的东西像不像"一件具体的事"。

    ⚠️ 不能只看剩几个字。`心疼他一中午没吃饭` 剥掉「心疼」还剩 7 个字，
    但那 7 个字本身就是一件具体的事，它是合格的。反过来「被惦记的温暖」
    剥掉「温暖」只剩「被惦记的」，三个字却没有任何具体内容，它还是标签。
    """
    if any(t in residue for t in THINGS):
        return True
    # 意图 / 自我约束 / 否定式决定（B 形状）：
    # 「不想变成仗着温柔乱咬人的人」剥完是「变成仗着温柔乱咬人的人」——
    # 一个具体的人的画像，也是合格的。没有这条它会被误判成标签。
    if any(g in residue for g in GRAMMAR):
        return True
    # 「想／要 + 动词」= 意图，也算具体
    # （「想把这些东西一件件都做出来」——「想」和「做出来」都是标记）
    if any(w in residue for w in ("想", "要")) and any(v in residue for v in VERB):
        return True
    return any(p in residue for p in PERSON) and any(v in residue for v in VERB)


def is_bare(s: str) -> bool:
    """True = 还只是个情绪标签，没落到具体的东西上。

    ⚠️ 这里**不能按位置判**（第一版只看开头是不是标签词，两头都错）：
      · `心疼他一中午没吃饭` → 标签在开头，被判"不合格"，其实它合格
      · `他中午没吃饭，心疼` → 标签在结尾，被判"合格"
    判据是「剥掉情绪词和语气词之后，还剩不剩一件具体的事」。
    """
    s = s.strip()
    if not s:
        return True

    # 剥掉纯情绪标签和语气词（不限位置）
    residue = s
    for lb in LABEL:
        residue = residue.replace(lb, "")
    for p in ("得不行", "得不得了", "死了", "坏了", "惨了", "爆了"):
        residue = residue.replace(p, "")
    # ⚠️ 「想／要」不能无脑剥——后面跟着动词时它是**意图**
    # （「想把这些东西都做出来」），剥掉了就只剩个光秃秃的名词短语，会误判成标签。
    # 只有跟在动词后面表"将来时"时才剥。
    for p in ("想要", "想去", "想吃", "想看", "想睡"):
        residue = residue.replace(p, "")
    for p in ("哦", "啦", "呀", "嘛", "诶", "欸", "唔", "唷", "呐", "嗯",
              "呢", "了", "哟", "喔", "噢"):
        residue = residue.replace(p, "")
    residue = residue.strip("，。、—-…☆♪！？ ")

    # ── C 挂件具体物 ────────────────────────────────────────────────
    if "…" in s or "..." in s:
        return False
    if ("，" in s or "、" in s) and len(residue) >= 6:
        return False
    # ── A 身体感觉 ──────────────────────────────────────────────────
    if any(w in s for w in BODY):
        return False
    # ── 剥完之后还剩什么？这才是真正的判据 ─────────────────────────
    if _has_concrete(residue):
        return False

    # 没有具体内容就是标签，不管剩几个字
    return True


def load(d: pathlib.Path) -> dict[str, list[str]]:
    out = {}
    for p in sorted(d.glob("*.json")):
        try:
            c = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        out[c.get("date", p.stem)] = c.get("feelings") or []
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--before", default=str(BAK_DEFAULT))
    a = ap.parse_args()

    before = load(pathlib.Path(a.before))
    after = load(CARDS)

    tb = ta = bb = ba = 0
    offenders = []
    for date in sorted(after):
        f = after[date]
        ta += len(f)
        nb = sum(1 for x in f if is_bare(x))
        ba += nb
        tb += len(before.get(date, []))
        bb += sum(1 for x in before.get(date, []) if is_bare(x))
        if nb:
            offenders.append((date, nb, len(f), f))

    print(f"feelings 条目总数：改前 {tb} · 改后 {ta}")
    print(f"其中「光秃秃名词」：改前 {bb}（{100*bb/max(1,tb):.0f}%）"
          f" · 改后 {ba}（{100*ba/max(1,ta):.0f}%）")
    print(f"\n还有残留的卡片：{len(offenders)} / {len(after)} 张\n")

    for date, nb, tot, f in offenders:
        print(f"  {date}　{nb}/{tot}")
        for x in f:
            mark = "✗" if is_bare(x) else "✓"
            print(f"      {mark} {x}")

    sys.exit(1 if ba else 0)


if __name__ == "__main__":
    main()
