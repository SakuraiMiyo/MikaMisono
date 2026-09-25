#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_catchphrase_dialogs.py —— 把**口癖原句**做成 few-shot 对

## 为什么需要单独一个脚本

`begin_dialogs` 原本只吃 MomoTalk（打字语域）。但她的几个招牌口头禅
——**呀吼 / 锵锵 / 哼哼哼 / 哇～哦 / 〜对吧？**——在 MomoTalk 里一次都没出现，
全都在**剧情台词**里。而 `begin_dialogs` 要求严格 user/assistant 交替，
所以不能只放她那一句，必须有老师那一句。

## 取老师那一句的规则

1. **优先**：往前找最近的一条 `speaker == "老师"` 的台词。
2. 找不到就接受 **旁白 / 未知 /（未标明）**——BA 剧本里老师的台词经常没有署名，
   而这几种标记实际就是老师那一边（比如「未花？你在做什么呢？」）。
3. 都没有、且 `允许倒序` 为真时，取**紧跟在她后面**的老师台词，
   并在输出里标出「顺序已调」。
4. 仍然找不到就**直接报错让你换一句**——**绝不自己编台词。**

未花那一句**逐字照抄**，一个字不改。

输出：`begin_dialogs.catchphrase.json`（偶数条，可拼到 MomoTalk 版后面）
用法：<python> build_catchphrase_dialogs.py
"""
from __future__ import annotations

import json
import pathlib

HERE = pathlib.Path(__file__).parent
SRC = HERE.parent / "assets" / "story-cn" / "corpus" / "mika-turns.json"
OUT_JSON = HERE / "begin_dialogs.catchphrase.json"
OUT_MD = HERE / "begin_dialogs.catchphrase.md"

REAL_TEACHER = {"老师", "先生", "Sensei", "sensei"}
NARRATOR = {"旁白", "未知", "（未标明）", "（旁白）"}

# (story, 这句里必须唯一命中的片段, 备注, 允许倒序取后一句)
SELECTED: list[tuple[str, str, str, bool]] = [
    ("31170", "哇～哦", "被说中时的感叹（老师刚说完「我也是未花的同伴哦」）", False),
    ("101225", "哼哼哼，锵锵", "得意 + 锵锵（招牌登场）", False),
    ("100596", "锵锵", "亮东西·锵锵", False),
    ("101225", "对吧〜？", "招牌尾巴·〜对吧？（老师刚夸完）", False),
    ("101225", "老师表扬我了", "欸嘿嘿·被夸", False),
    ("100596", "啊哈哈！怎么啦", "啊哈哈·挑逗（老师刚说靠太近）", False),
    ("100596", "啊哈哈……我又", "啊哈哈·盖尴尬（负面用法）", False),
    ("101223", "呀吼", "打招呼·呀吼（招牌）", True),
]


def main() -> None:
    rows = json.loads(SRC.read_text(encoding="utf-8"))
    dialogs: list[str] = []
    preview: list[str] = []

    for story, needle, note, allow_after in SELECTED:
        cands = [i for i, r in enumerate(rows)
                 if str(r.get("story")) == story and needle in (r.get("text") or "")]
        if len(cands) != 1:
            raise SystemExit(f"✗ [{story}]「{needle}」命中 {len(cands)} 条（应为 1 条），"
                             f"请换一个更独特的片段")
        i = cands[0]
        mika = rows[i]["text"].strip()

        def speaker(j: int) -> str:
            return rows[j].get("speaker") or ""

        def join_same_idx(j: int) -> str:
            """同一 idx 往往有连续几行（老师的台词被拆成多句），要合并成一句。"""
            parts = [(rows[j].get("text") or "").strip()]
            k = j + 1
            while (k < len(rows) and rows[k].get("idx") == rows[j].get("idx")
                   and str(rows[k].get("story")) == story):
                parts.append((rows[k].get("text") or "").strip())
                k += 1
            return "\n".join(p for p in parts if p)

        teacher, how = None, ""
        for j in range(i - 1, max(-1, i - 8), -1):
            if str(rows[j].get("story")) != story:
                break
            if speaker(j) in REAL_TEACHER:
                teacher, how = join_same_idx(j), "老师原文"
                break
            if speaker(j) in NARRATOR:
                teacher, how = join_same_idx(j), "老师原文（未署名）"
                break
        if not teacher and allow_after:
            for j in range(i + 1, min(len(rows), i + 6)):
                if str(rows[j].get("story")) != story:
                    break
                if speaker(j) in REAL_TEACHER | NARRATOR:
                    teacher = join_same_idx(j)
                    how = "⚠️ 取自后一句（原文里这一句在老师那句之前）"
                    break
        if not teacher:
            raise SystemExit(f"✗ [{story}]「{needle}」前后都找不到老师台词，请换一句")

        dialogs += [teacher, mika]
        preview.append(f"\n**[{note}]**　`{how}`\n> 老师：{teacher}\n> 未花：{mika}\n")

    assert len(dialogs) % 2 == 0, "必须偶数条"
    OUT_JSON.write_text(json.dumps({"begin_dialogs": dialogs},
                                   ensure_ascii=False, indent=1), encoding="utf-8")
    md = (f"# begin_dialogs · 口癖对（剧情原句）\n\n"
          f"> 未花那一边**逐字照抄** `mika-turns.json`；\n"
          f"> 老师那一边取原文里最近的一句（BA 剧本里老师的台词常常没有署名，"
          f"标「未署名」的就是那种）。\n"
          f"> {len(dialogs)} 条 / {len(dialogs) // 2} 组。\n"
          + "\n".join(preview))
    OUT_MD.write_text(md, encoding="utf-8")

    n_after = sum(1 for p in preview if "取自后一句" in p)
    print(f"✓ {OUT_JSON.name}：{len(dialogs)} 条（{len(dialogs) // 2} 组）"
          f"{f'，其中 {n_after} 组顺序已调' if n_after else ''}")
    print(md)


if __name__ == "__main__":
    main()
