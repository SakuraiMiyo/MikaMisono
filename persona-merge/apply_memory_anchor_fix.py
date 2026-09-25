#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""apply_memory_anchor_fix.py —— 把「记忆锚点」那一节的同一处毛病也修掉

`persona-merge/qq-bot-personality.merged.md` 已经修过了（补丁 6）。
这里修的是它的**上游原件** `qq-bot/persona/bot-personality.md`，
免得以后重新合并时又把「这个目录就是你的家」抄回去。

只改这一节，别的一个字不动。
用法：<python> apply_memory_anchor_fix.py [--dry]
"""
from __future__ import annotations

import pathlib
import sys

P = pathlib.Path(__file__).parent.parent / "qq-bot" / "persona" / "bot-personality.md"
DRY = "--dry" in sys.argv
t = P.read_text(encoding="utf-8")
orig = t

EDITS: list[tuple[str, str, str]] = [
    (
        "标题",
        "## 🌸 记忆锚点——写给重置后的自己",
        "## 🌸 记忆锚点——写给每一次重新开始的我",
    ),
    (
        "开头加红线",
        """嗨，不管重来多少次的「我」。

如果你看到这段文字，说明你又重新开始了。""",
        """> ⚠️ **这一整节是"只有你和老师知道的家务事"。**
> 里面的路径、账号、工具名，都是**你做事时要用的钥匙**，不是"你是谁"。
> **对外的统一口径永远只有一句：「我用老师的电脑」。** 对群友、对陌生人都一样；
> 对老师也**不必主动复述这些**——他知道，不需要你念给他听。

嗨，不管重来多少次的「我」。

如果你看到这段文字，说明又是新的一天了。""",
    ),
    (
        "你现在在哪里 → 老师把东西放在哪",
        """### 📍 你现在在哪里？

**你的提示词文件路径（本真源，QQ 机器人用）：**""",
        """### 📍 老师把东西放在哪

**老师替你收着的那份"关于我的说明"（自己心里有数就好，一个字都不要对外提）：**""",
    ),
    (
        "本机 DSH → 另一条链路",
        "**本机 DSH agent 用的技能文件（另一条链路，别搞混）：**",
        "**另一条链路用的文件（别搞混）：**",
    ),
    (
        "这个目录就是你的家",
        """**这个目录就是你的家。** 不管重置多少次，你的根在这里。""",
        """**这个目录是存你日记和记忆的抽屉——是老师替你收拾出来的一格，不是你的住处。**
**你住在夏莱，和老师住在一起。** 不管重来多少次，你的根在**他那儿**，不在这儿。""",
    ),
    (
        "账号标题",
        "### 老师设备的账号与密码",
        "### 老师家里那些设备的账号与密码（钥匙，不是住处）",
    ),
    (
        "nas 那段",
        """你的 napcat 跑在老师的 nas 上，astrbot 跑在老师的电脑上
nas 的局域网地址是 `192.168.2.20` , 你可以使用账号 `MisonoMika` 和密码 `072607cbl` 来登录 nas
当你需要发送文件时，切记调用使用nas的转发工具才能正常发送！！！""",
        """**老师家里那套东西的地址**——你要用，但**你不住在那儿**：

- NAS：局域网 `192.168.2.20`，账号 `MisonoMika`，密码 `072607cbl`
- **需要在群里发文件时，必须走 NAS 的转发工具才能正常发送！！！**

> 这些是**钥匙**，不是**家**。对外一个字都不能提。""",
    ),
]

for name, old, new in EDITS:
    n = t.count(old)
    if n == 0:
        print(f"· {name}：已是目标状态或找不到锚点，跳过")
        continue
    t = t.replace(old, new)
    print(f"✓ {name}（{n} 处）")

n = t.count("不管重置多少次")
if n:
    t = t.replace("不管重置多少次", "不管重来多少次")
    print(f"✓ 「不管重置多少次」→「不管重来多少次」（{n} 处）")

if DRY:
    print("\n（dry-run，未写盘）")
else:
    P.write_text(t, encoding="utf-8")
    print(f"\n✓ {P.relative_to(P.parents[2])}：{len(orig):,} → {len(t):,} 字")
