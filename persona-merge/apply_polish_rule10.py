# -*- coding: utf-8 -*-
"""第十轮 · 收掉最后几处 sensei（知识库正文，不是备注）

`agent/knowledge/relationships.md` 的正文里还在用 `老师（sensei）` 当标题和称呼，
但同一项目的称呼表已经写明「中文语料里 sensei 0 命中」——自相矛盾。
这里只改**正文用法**，保留 `dialogue-corpus.md` / `参考语音.md` 里那两处**语料统计备注**
（那两处就是在说"sensei 命中 0 次"，属于结论本身，不能删）。
"""
import shutil, pathlib, datetime

B = pathlib.Path(r"C:\OneDrive\MikaMisono")
STAMP = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
BAK = B / "_archive-20260924" / ("polish10-" + STAMP)
BAK.mkdir(parents=True, exist_ok=True)

F = B / "agent" / "knowledge" / "relationships.md"
shutil.copy2(F, BAK / "relationships.md")

t = F.read_text(encoding="utf-8")
n0 = len(t)
pairs = [
    ("│     老师（sensei）       │", "│         老师            │"),
    ("### 2.1 老师（sensei）——叫你「我的公主」的人",
     "### 2.1 老师——叫你「我的公主」的人"),
    ("| **未花对老师的称呼** | 老师 / sensei / 老公（领证后） |",
     "| **未花对老师的称呼** | 老师——中文里就叫这两个字（⚠️ 语料里 `sensei` 0 命中）；领证后叫老公 |"),
]
for old, new in pairs:
    if old in t:
        t = t.replace(old, new)
        print(f"  [ok] {old[:34]}…")
    else:
        print(f"  [=] 没找到：{old[:34]}…")

F.write_text(t, encoding="utf-8")
print(f"relationships.md：{n0} -> {len(t)} 字符，剩余 sensei = {t.count('sensei')}")
