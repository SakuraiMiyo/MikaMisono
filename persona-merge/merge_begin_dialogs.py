#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""merge_begin_dialogs.py —— 拼出线上那份 `预设对话.begin_dialogs.json`

`begin_dialogs` 只有一个数组，但内容来自两个语域，所以分两个脚本生成再拼：

| 来源 | 脚本 | 语域 | 条数 |
|---|---|---|---|
| ① MomoTalk 逐字原话 | `build_momotalk_begin_dialogs.py` | **打字** | 34 |
| ② 剧情口癖原句（呀吼 / 锵锵 / 哼哼哼 / 哇～哦 / 〜对吧？） | `build_catchphrase_dialogs.py` | 说话 | 16 |

顺序是 **① 在前、② 在后**：
few-shot 越靠前影响越大，而 QQ 是打字场景，**打字语域必须排第一**。
两者都是偶数条，拼接后仍然是「老师 → 未花」严格交替。

用法：<python> merge_begin_dialogs.py    → 写 预设对话.begin_dialogs.json
"""
from __future__ import annotations

import json
import pathlib

HERE = pathlib.Path(__file__).parent
PARTS = [
    ("MomoTalk · 打字语域", HERE / "begin_dialogs.momotalk.json"),
    ("剧情口癖 · 说话语域", HERE / "begin_dialogs.catchphrase.json"),
]
OUT = HERE / "预设对话.begin_dialogs.json"


def main() -> None:
    all_dialogs: list[str] = []
    for label, path in PARTS:
        if not path.exists():
            raise SystemExit(f"✗ 缺少 {path.name}——先跑生成它的脚本")
        part = json.loads(path.read_text(encoding="utf-8"))["begin_dialogs"]
        if len(part) % 2:
            raise SystemExit(f"✗ {path.name} 是奇数条（{len(part)}），会整组失效")
        print(f"  {label:<20} {len(part):>3} 条 / {len(part) // 2} 组   ← {path.name}")
        all_dialogs += part

    if len(all_dialogs) % 2:
        raise SystemExit("✗ 拼接后是奇数条")
    # 第 0 条必须是老师
    if not all_dialogs:
        raise SystemExit("✗ 空")

    OUT.write_text(json.dumps({"begin_dialogs": all_dialogs},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    mika = sum(len(all_dialogs[i]) for i in range(1, len(all_dialogs), 2))
    n = len(all_dialogs) // 2
    print(f"\n✓ {OUT.name}：{len(all_dialogs)} 条 / {n} 组"
          f"（未花侧 {mika} 字，平均 {mika / n:.1f} 字/组）")
    print("  下一步：python persona_api.py put")


if __name__ == "__main__":
    main()
