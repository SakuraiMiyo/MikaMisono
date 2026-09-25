#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""analyze_particles.py —— 从**配音转写**里量一次未花的语气词

## 这份语料是什么

`GPT-SoVITS-v2pro-20250604-nvidia50\output\asr_opt\*.list` —— TTS 训练集切完之后
ASR 出来的对照表，格式 `音频路径|说话人|语言|文本`。
音频源 6 个：未花配音素材 / 未花小剧场广播剧 / 未花小剧场 / 未花新年祝福 /
声优访谈 / 未花电视CM。**752 条去重后的日文台词。**

它和之前两份语料的关系：

| 语料 | 是什么 | 语域 |
|---|---|---|
| `mika-only.json` | 主线 + 羁绊的**剧情台词**（中日对照） | 说话，书面味重、句子长 |
| `mika-momotalk.json` | 手机聊天记录 | 打字，极短、碎 |
| **本文件** | **配音转写** | **真的在说话——语气词最全的地方** |

## 为什么要量这个

老师反馈 QQ 上「情绪表露少了、语气词很少」。
中文语气词（吧/呢/啊/哦/呀/嘛/啦）其实是日语**终助词**（よ/ね/な/の/わ/さ）的对应物。
所以真正该问的是：**她说话时，多大概率会在句末挂一个终助词？**

如果日文原文大半句都带终助词，而中文译文和现在的中文 prompt 里只有一成多，
那就说明**语气词是在翻译环节丢掉的**——prompt 里那句「每七八句就该有一个」
定得**太低**了。

用法：<python> analyze_particles.py
"""
from __future__ import annotations

import collections
import json
import pathlib
import re

HERE = pathlib.Path(__file__).parent
CORPUS = HERE.parent / "story-cn" / "corpus"

# ── 日文终助词（句末）────────────────────────────────────────────
# 长的排前面，匹配时取最长命中
FINAL_JA = [
    "かしら", "でしょ", "じゃん", "だよね", "よね", "のよね", "かも",
    "かな", "なあ", "だろ", "っけ", "もの", "もん", "けどな", "んだ", "のよ", "わよ",
    "よね", "よ", "ね", "な", "の", "わ", "さ", "か", "ぜ", "ぞ", "け", "ろ",
    "けど", "のに", "から", "し", "って", "たり", "です", "ます", "だ", "た", "る", "い",
]
# 上表里最后那批（だ/た/る/い/です/ます）是「普通终止形」，不算终助词
PLAIN_TAIL = {"だけど", "た", "る", "い", "だ", "です", "ます", "けど", "のに", "から", "し", "って", "たり"}
PARTICLES = [p for p in FINAL_JA if p not in PLAIN_TAIL]
PARTICLES.sort(key=len, reverse=True)

# ── 日文感叹词 / 间投词（句首或独立）──────────────────────────────
INTERJ = [
    "あはは", "えへへ", "うふふ", "ふふふ", "あっはっは",
    "うん", "ううん", "ええ", "いや", "へえ", "わあ", "あら", "まあ",
    "あっ", "えっ", "あー", "えー", "うー", "んー", "ふー",
    "もう", "ちょっと", "ねえ", "ほら", "やだ", "あの", "その", "なんか",
    "あ", "え", "ん", "ふ", "は", "わ",
]
INTERJ.sort(key=len, reverse=True)

# ── 中文语气词（句末）────────────────────────────────────────────
FINAL_ZH = ["吧", "呢", "啊", "哦", "呀", "嘛", "啦", "喔", "诶", "耶", "嘞", "咯",
            "吗", "呐", "嗷", "吼", "惹"]
# 吗/呢/吧 是疑问、推测，单列
ZH_WEAK = {"吧", "呢", "啊", "哦", "呀", "嘛", "啦"}

STRIP = " \u3000\t？?！!。、…‥~〜ー-—「」『』\"'“”（）()"


def strip_tail(s: str) -> str:
    return s.rstrip(STRIP)


def ja_tail(text: str) -> str:
    """返回句末命中的终助词（没有就返回 ''）。"""
    t = strip_tail(text)
    for p in PARTICLES:
        if t.endswith(p):
            return p
    return ""


def zh_tail(text: str) -> str:
    t = strip_tail(text)
    return t[-1] if t else ""


def load_lists() -> list[dict]:
    rows, seen = [], set()
    for f in sorted(HERE.glob("*.list")):
        for line in f.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            parts = line.split("|")
            if len(parts) != 4:
                continue
            path, spk, lang, text = (x.strip() for x in parts)
            if not text or lang != "JA":
                continue
            m = re.search(r"\\([^\\]+?\.(?:mp3|wav|flac))\.reformatted", path)
            src = m.group(1) if m else pathlib.Path(path).name
            key = (src, text)
            if key in seen:
                continue
            seen.add(key)
            rows.append({"src": src, "text": text})
    return rows


def report_ja(rows: list[dict]) -> None:
    n = len(rows)
    print(f"── 配音转写（日文）{n} 条去重台词 ──\n")
    print("按音频来源：")
    for s, c in collections.Counter(r["src"] for r in rows).most_common():
        print(f"  {c:>4}  {s}")

    tails = collections.Counter()
    plain = 0
    q = 0
    elong = 0
    for r in rows:
        t = strip_tail(r["text"])
        if t.endswith(("？", "?")) or r["text"].rstrip().endswith(("？", "?")):
            q += 1
        if "ー" in r["text"] or "〜" in r["text"] or "~" in r["text"]:
            elong += 1
        p = ja_tail(r["text"])
        if p:
            tails[p] += 1
        else:
            plain += 1

    with_p = sum(tails.values())
    print(f"\n句末带终助词：{with_p}/{n} = {with_p / n:.1%}")
    print(f"句末是普通终止形（だ/た/る/い…）：{plain}/{n} = {plain / n:.1%}")
    print(f"带问号：{q}/{n} = {q / n:.1%}")
    print(f"含长音符「ー」或「〜」：{elong}/{n} = {elong / n:.1%}")
    print("\n终助词排行（占全部台词）：")
    for p, c in tails.most_common(16):
        print(f"  {p:<5} {c:>4}  {c / n:>6.1%}")

    print("\n句首/独立感叹词（占全部台词）：")
    ic = collections.Counter()
    for r in rows:
        t = r["text"].lstrip(STRIP)
        for p in INTERJ:
            if t.startswith(p):
                ic[p] += 1
                break
    tot = sum(ic.values())
    print(f"  合计 {tot}/{n} = {tot / n:.1%}")
    for p, c in ic.most_common(20):
        print(f"  {p:<6} {c:>4}  {c / n:>6.1%}")

    lens = [len(r["text"]) for r in rows]
    print(f"\n平均句长：{sum(lens) / len(lens):.1f} 字（中位 {sorted(lens)[len(lens) // 2]}）")


def report_zh() -> None:
    print("\n\n── 中文对照：剧情台词 vs 译文句末语气词 ──\n")
    for name, field in (("mika-only.json", "text"), ("mika-momotalk.json", "text")):
        f = CORPUS / name
        if not f.exists():
            print(f"  跳过 {name}（不存在）")
            continue
        rows = json.loads(f.read_text(encoding="utf-8"))
        if name == "mika-only.json":
            rows = [r for r in rows if r.get("speaker") in ("ミカ", "未花") or r.get("mika")]
        texts = [r[field] for r in rows if r.get(field)]
        n = len(texts)
        tz = collections.Counter(zh_tail(t) for t in texts if zh_tail(t) in FINAL_ZH)
        with_p = sum(tz.values())
        print(f"{name}：{n} 条")
        print(f"  句末带中文语气词：{with_p}/{n} = {with_p / n:.1%}")
        for p, c in tz.most_common(12):
            print(f"    {p} {c:>4}  {c / n:>6.1%}")
        print()


def main() -> None:
    rows = load_lists()
    report_ja(rows)
    report_zh()


if __name__ == "__main__":
    main()
