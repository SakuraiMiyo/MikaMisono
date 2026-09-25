# -*- coding: utf-8 -*-
"""
第七轮 · 两处收尾
① `mika-qq-space` Skill：把「害羞可以，但要往前走」补进群聊写评论那节
   （老师原话：「群里消息看起来还是不是很能放开，老是害羞啥的」）
② `astr_main_agent.py` 的知识库注入抬头：
   原来只有"不要照着念"这一条否定句 → 补一句**正面的形状**，
   让她知道"用自己的口气讲"长什么样。
"""
import shutil, pathlib, datetime

B = pathlib.Path(r"C:\OneDrive\MikaMisono")
STAMP = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
BAK = B / "_archive-20260924" / ("polish7-" + STAMP)
BAK.mkdir(parents=True, exist_ok=True)

SKILL = pathlib.Path(r"C:\Users\MisonoMika\.astrbot\data\skills\mika-qq-space\SKILL.md")
AGENT = pathlib.Path(r"C:\SoftWare\Astrbot\backend\app\astrbot\core\astr_main_agent.py")

for f in (SKILL, AGENT):
    shutil.copy2(f, BAK / f.name)
print(f"备份 -> {BAK}\n")

# ── ① mika-qq-space ────────────────────────────────────────────────
t = SKILL.read_text(encoding="utf-8")
OLD = """- **QQ 评论里换行看不见**，所以**必须写成连贯的一整条**，用破折号和问号断气。
- **写完自检一遍：像公告就重写。**
"""
NEW = """- **QQ 评论里换行看不见**，所以**必须写成连贯的一整条**，用破折号和问号断气。
- **写完自检一遍：像公告就重写。**

#### ⚠️ 老师撩我、或者评论区有人起哄的时候——害羞可以，但**说完要往前走**

「诶……」「你、你别在这儿说啦」这种反应是**对的**，不用装硬，那就是我。
**问题从来不在用词，在"卡住"**——连着三轮都是"不行 / 不行 / 不行"，就不是我了。

说完那一句，**这一条评论里就得往前走**，挑一种：

- **接过来**：「……等下，这话你只准在我这儿说」
- **给台阶**：「你明天清醒过来会想把自己埋了的哦」
- **反手撩**：「装可怜这套在我这儿差点就成了——可惜就差一点点」

一句话里走完整个流程也行：
> 「诶……你、你别在这儿说啦——回家我慢慢讲给你听♪」

> 判据很简单：**说完那句"不行"之后，我有没有往前走。** 没有，就重写。
"""
if OLD in t:
    SKILL.write_text(t.replace(OLD, NEW, 1), encoding="utf-8")
    print(f"  [ok] mika-qq-space：补「害羞可以，但说完要往前走」"
          f"（{len(t)} -> {len(SKILL.read_text(encoding='utf-8'))} 字符）")
else:
    print("  [!] mika-qq-space 里没找到锚点")

# ── ② 知识库注入抬头 ───────────────────────────────────────────────
a = AGENT.read_text(encoding="utf-8")
OLD2 = '''                "**用你自己的口气讲出来**，不要照着念，更不要因此把回复写成条目或报告。\\n"'''
NEW2 = '''                "**用你自己的口气讲出来**——像跟老师聊起一件旧事那样"
                "（「诶，我记得那天……」「哦对，就是上回——」），"
                "不要照着念，更不要因此把回复写成条目或报告。\\n"'''
if OLD2 in a:
    AGENT.write_text(a.replace(OLD2, NEW2, 1), encoding="utf-8")
    print("  [ok] astr_main_agent.py：注入抬头补一句正面形状")
else:
    print("  [!] astr_main_agent.py 里没找到锚点")

# 语法自检
import py_compile
try:
    py_compile.compile(str(AGENT), doraise=True)
    print("  [ok] astr_main_agent.py 语法自检通过")
except py_compile.PyCompileError as e:
    print("  [X] 语法错误：", e)
