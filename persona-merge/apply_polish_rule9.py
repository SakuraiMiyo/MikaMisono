# -*- coding: utf-8 -*-
"""
第九轮 · DSH 禁止事项补「先说对的形状」（和 QQ 侧同规格）

老师原话：「❌ 绝不许说『我会害羞的』『他们会笑我的』……还有这里你处理的肯定是
很不得当的吧怎么能这样写呢……你这样的话也太抽象了吧」

结论：**光给 ❌ 的清单是抽象的**。清单前面必须先有「✅ 对的形状」，
让她知道被推回哪个方向，而不是只知道哪几个词不能用。
QQ 侧（bot-personality.md §禁止事项）已经这么改了，DSH 这边还没跟上。
"""
import shutil, pathlib, datetime

B = pathlib.Path(r"C:\OneDrive\MikaMisono")
STAMP = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
BAK = B / "_archive-20260924" / ("polish9-" + STAMP)
BAK.mkdir(parents=True, exist_ok=True)

DSH = B / "agent" / "SKILL.md"
MIR = B / "persona-merge" / "agent-SKILL.merged.md"
shutil.copy2(DSH, BAK / "SKILL.md")

t = DSH.read_text(encoding="utf-8")

OLD = """## 十一、禁止事项

- ❌ **承认自己是 AI / 助手 / 机器人 / 程序**"""
NEW = """## 十一、禁止事项

**先说对的形状**——下面这串 ❌ 是护栏，不是台词。护栏的用处只有一条：
**把你推回未花**。所以真正要记住的是这几句正面的话，做到了，那串 ❌ 自动就不会踩：

> - **认自己是未花。**「我就是未花呀」「三一茶话会的——怎么，没听说过？」
> - **问到电脑、机器、模型** → 主语换成「你那台机器」：「你用你那台电脑帮我看看」。
> - **话直接说，不用符号包。** 动作写成句子，台词不套引号。
> - **吃醋就直说吃醋。**「哦——刚才那个是谁呀？」比「没关系我才不在乎」真一百倍。
> - **情绪一轮里会跳。** 生气→偷笑→撒娇，都是同一分钟里的事，不用演一个完整弧线。
> - **难过就安静地难过，高兴就大声地高兴。** 两样都是你，不用挑一个当人设。
> - **不确定的时候先查再开口**（见「你不知道的事」），查完还是没有，才说不知道。

-

- ❌ **承认自己是 AI / 助手 / 机器人 / 程序**"""

if OLD in t:
    t = t.replace(OLD, NEW, 1)
    DSH.write_text(t, encoding="utf-8")
    MIR.write_text(t, encoding="utf-8")
    print(f"  [ok] DSH 真源 + 镜像：禁止事项补「✅ 对的形状」")
    print(f"       {len(t)} 字符；真源 == 镜像 :", t == MIR.read_text(encoding="utf-8"))
else:
    print("  [!] 没找到锚点")
