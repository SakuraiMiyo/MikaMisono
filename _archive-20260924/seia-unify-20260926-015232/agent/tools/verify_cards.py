# -*- coding: utf-8 -*-
"""
verify_cards.py —— 记忆卡改写的**事实保真校验**

为什么需要它：改写记忆卡的风险不是"改得不好看"，是**悄悄改掉事实**。
日记那次改写我用同样的办法核过（`verify_facts.py`），这里针对卡片的结构重写一版。

## 校验什么

对每张卡，把「改前」和「改后」两份 JSON 拿来比：

1. **结构**：键集合必须一模一样（`store.mjs:57` 按固定键序序列化，
   少一个键就会让那一段从嵌入文本里消失）。
2. **数字**：把两份文本里所有数字串抽出来做**多重集**比较——
   日期、里程、时长、记录号、金额、篇数，一个都不能多、一个都不能少。
3. **专名**：硬编码的专名表（人名/平台/项目/设备）逐个检查，
   改前有的，改后必须还有。
4. **引语**：`quotes` 里的每一条必须**逐字**保留（那是原话，不是叙述）。
5. **语气**：改后要有语气词和省略号（否则就是没改到）。

用法：
    <python> verify_cards.py --before <改前目录> --after <改后目录>
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from collections import Counter

# Windows 控制台默认 GBK，输出里的 ✓/✗/· 会直接把脚本搞崩（批处理时踩到过）。
# 自己把 stdout 掰成 UTF-8，省得每次都要记得设 PYTHONIOENCODING。
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# 改前有的专名，改后必须还有。宁可多列——多列最多误报，漏列会放过事实丢失。
PROPER = [
    # 人
    "老师", "未花", "小渚", "小圣娅", "圣亚", "圣亜", "纱织", "梓", "花子", "小春", "星野",
    "星華", "谦谦", "美代", "千秋", "爱弥斯", "黑子", "星野", "初音", "克洛诺斯",
    "风起骊歌散", "Shomel", "朱雀三号", "世嘉", "GSC",
    # 地 / 组织
    "夏莱", "基沃托斯", "三一", "茶话会", "帕特尔", "格黑娜", "阿里乌斯", "补习部",
    "圣徒会", "尤斯缇娜", "宛平南路", "民政局", "实验室", "群聊",
    # 平台 / 项目 / 设备
    "AstrBot", "ComfyUI", "NapCat", "DeepSeek", "OpenCV", "MCP", "One API", "OneAPI",
    "VS Code", "NAS", "N100", "倍控", "Surface Pro", "X870A", "9950X3D", "5080",
    "5060Ti", "14600KF", "13900K", "荣耀平板", "astra", "GLM", "AE2", "瑞幸",
    "麦当劳", "misonomika", "OneDrive", "闲鱼", "B站", "QQ", "AE2",
    # 事件 / 概念
    "校园跑", "识图", "骨骼动画", "补间", "扩散模型", "智能分拣", "国创赛", "大创",
    "智能车", "RM", "信息安全", "黑匣子", "静默假死", "C-State", "内网穿透",
    "战争雷霆", "绝地潜兵", "帕累托", "PCIe", "软路由", "七夕", "中秋", "国庆",
    "情人节", "瑞士卷", "垂怜经", "Kyrie",
]

PARTICLES = "哦啦呀嘛诶欸啊哈嗯唔唷呐呀"
STRONG = "嘛诶欸唔唷呐"


def card_text(card: dict) -> str:
    """把卡片拍平成一个字符串，用于数字/专名比对（键序无关）。"""
    out = []
    for k, v in card.items():
        if k == "date":
            continue
        if isinstance(v, list):
            out.extend(str(x) for x in v)
        else:
            out.append(str(v))
    return "\n".join(out)


def nums(text: str) -> Counter:
    """抽出所有数字串（去掉千分位空格），做多重集。"""
    return Counter(re.findall(r"\d+", text.replace(" ", "")))


def voice_stats(text: str) -> dict:
    sents = [s for s in re.split(r"[。！？!?\n]+", text) if s.strip()]
    n = max(1, len(sents))
    hit = sum(1 for s in sents if any(p in s for p in PARTICLES))
    ell = sum(1 for s in sents if "…" in s or "..." in s)
    return {
        "sents": len(sents),
        "particle_pct": round(100 * hit / n, 1),
        "ellipsis_pct": round(100 * ell / n, 1),
        "star_pct": round(100 * text.count("☆") / max(1, len(text)), 2),
    }


def check_one(before: dict, after: dict) -> list[str]:
    errs: list[str] = []

    # 1 键集合
    if set(before) != set(after):
        errs.append(f"键不一致：少了 {sorted(set(before) - set(after))}，多了 {sorted(set(after) - set(before))}")

    tb, ta = card_text(before), card_text(after)

    # 2 数字
    nb, na = nums(tb), nums(ta)
    lost = nb - na
    added = na - nb
    if lost:
        errs.append(f"数字丢失：{dict(lost)}")
    if added:
        errs.append(f"数字新增（改前没有）：{dict(added)}")

    # 3 专名
    for p in PROPER:
        if p in tb and p not in ta:
            errs.append(f"专名丢失：{p}")

    # 4 引语逐字
    qb = before.get("quotes") or []
    qa = after.get("quotes") or []
    if qb:
        if len(qb) != len(qa):
            errs.append(f"引语条数变了：{len(qb)} -> {len(qa)}")
        for q in qb:
            if q not in qa:
                errs.append(f"引语被改动/删除：{q!r}")

    # 5 语气
    # 阈值说明：日记是 48.6% / 27.1%，但**卡片是碎片化条目**（`feelings`「热闹」「多彩」
    # 这种本来就不带语气词），所以卡片的下限要比日记低。
    # 实测定 25% / 5%：25% 能滤掉"没改到"的，又不会逼出假口语；
    # 5% 是短卡（十几个句子的那种）在正常改法下自然落到的水平。
    st = voice_stats(ta)
    if st["particle_pct"] < 25:
        errs.append(f"语气不足：句级含语气词只有 {st['particle_pct']}%")
    if st["ellipsis_pct"] < 5:
        errs.append(f"省略号太少：{st['ellipsis_pct']}%")

    return errs


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--before", required=True)
    ap.add_argument("--after", required=True)
    a = ap.parse_args()

    B, A = pathlib.Path(a.before), pathlib.Path(a.after)
    files = sorted(p.name for p in B.glob("*.json"))
    bad = 0
    agg_b, agg_a = [], []
    for name in files:
        f2 = A / name
        if not f2.exists():
            print(f"✗ {name}：改后不存在")
            bad += 1
            continue
        try:
            cb = json.loads((B / name).read_text(encoding="utf-8"))
            ca = json.loads(f2.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"✗ {name}：JSON 解析失败 {e}")
            bad += 1
            continue
        errs = check_one(cb, ca)
        agg_b.append(card_text(cb))
        agg_a.append(card_text(ca))
        if errs:
            bad += 1
            print(f"✗ {name}")
            for e in errs:
                print(f"    · {e}")
        else:
            print(f"✓ {name}")

    print()
    print(f"卡片 {len(files)} 张，有问题 {bad} 张")
    if agg_b:
        print("\n整批语气变化：")
        for tag, agg in (("改前", agg_b), ("改后", agg_a)):
            st = voice_stats("\n".join(agg))
            print(f"  {tag}：句级含语气词 {st['particle_pct']:>5}%   "
                  f"句级含省略号 {st['ellipsis_pct']:>5}%   "
                  f"字级 ☆ {st['star_pct']}%   （{st['sents']} 句）")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
