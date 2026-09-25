# -*- coding: utf-8 -*-
"""第六轮 · DSH 收尾小修
① 节号：十一、你不知道的事 -> 十、你不知道的事（原来的「十」已经被换成「十一」了，重了）
② 正文里两个漏下的右括号 `）`
"""
import shutil, pathlib, datetime

B = pathlib.Path(r"C:\OneDrive\MikaMisono")
STAMP = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
BAK = B / "_archive-20260924" / ("polish6-" + STAMP)
BAK.mkdir(parents=True, exist_ok=True)

DSH = B / "agent" / "SKILL.md"
shutil.copy2(DSH, BAK / "SKILL.md")

t = DSH.read_text(encoding="utf-8")
n0 = len(t)

pairs = [
    ("## 十一、你不知道的事", "## 十、你不知道的事"),
    ('> 请优先查阅对应知识库文件。以下为精简版角色核心——详细内容请参考各知识库。）',
     '> 请优先查阅对应知识库文件。以下为精简版角色核心——详细内容请参考各知识库。'),
    ('> ⚠️ **想知道"这句是原作事实还是二创"→ 查 `assets/story-cn/资料来源与核实方法.md`。**）',
     '> ⚠️ **想知道"这句是原作事实还是二创"→ 查 `assets/story-cn/资料来源与核实方法.md`。**'),
]
for old, new in pairs:
    if old in t:
        t = t.replace(old, new)
        print(f"  [ok] {old[:36]}…")
    else:
        print(f"  [=] 没找到（可能已改）：{old[:36]}…")

DSH.write_text(t, encoding="utf-8")
print(f"DSH 真源：{n0} -> {len(t)} 字符")

# 镜像同步
MIR = B / "persona-merge" / "agent-SKILL.merged.md"
MIR.write_text(t, encoding="utf-8")
print("真源 == 镜像 :", t == MIR.read_text(encoding="utf-8"))

# 列出最终节号
import re
print("\n最终 ## 标题：")
for m in re.finditer(r"^(#{2,3}) (.+)$", t, re.M):
    if m.group(2)[0] in "一二三四五六七八九十" or "、你不知道" in m.group(2):
        print(f"  {m.group(1)} {m.group(2)}")
