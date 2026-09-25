#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""show_catchphrase_lines.py —— 把口癖的**原句**打出来

统计只能说明"有"，看不出"怎么用"。这个脚本按关键词把原文连上下文一起打出来，
用来判断该把它归到哪一类（招呼 / 笑 / 语气 / 自我掩饰）。

用法：<python> show_catchphrase_lines.py 呀吼 嘿嘿 啊哈哈 唔 哇
      <python> show_catchphrase_lines.py          # 跑默认的一组
"""
from __future__ import annotations

import json
import pathlib
import sys

CORPUS = pathlib.Path(__file__).parent.parent / "story-cn" / "corpus"
DEFAULT = ["呀吼", "哇～哦", "啊哈哈", "嘿嘿", "唔", "呜", "哼哼", "对吧", "来着"]


def main() -> None:
    words = sys.argv[1:] or DEFAULT
    only = json.loads((CORPUS / "mika-only.json").read_text(encoding="utf-8"))
    moto = json.loads((CORPUS / "mika-momotalk.json").read_text(encoding="utf-8"))

    for w in words:
        print(f"\n{'=' * 74}\n「{w}」\n{'=' * 74}")
        hits = [r for r in only if w in (r.get("text") or "")]
        print(f"—— 剧情台词（{len(hits)} 条）——")
        for r in hits[:14]:
            jp = r.get("jp") or ""
            sid = r.get("story") or ""
            print(f"  [{sid}] {r['text']}")
            if jp:
                print(f"        JP: {jp}")
        mh = [r for r in moto if w in (r.get("text") or "")]
        if mh:
            print(f"—— MomoTalk（{len(mh)} 条）——")
            for r in mh[:10]:
                print(f"  [{r['id']}] {r['text']}")

    # 日文配音侧：招呼语全打出来
    sys.path.insert(0, str(pathlib.Path(__file__).parent))
    from analyze_particles import load_lists
    ja = [r for r in load_lists()]
    print(f"\n{'=' * 74}\n配音转写里所有「打招呼 / 挂け声」\n{'=' * 74}")
    keys = ["やっほ", "イヤッハー", "レッツゴ", "よースター", "えへへ", "うふふ",
            "ふふん", "うはは", "おー", "うへー", "わーお", "はーん", "ふーん"]
    for r in ja:
        if any(k in r["text"] for k in keys):
            print(f"  [{r['src'][:12]:<12}] {r['text']}")


if __name__ == "__main__":
    main()
