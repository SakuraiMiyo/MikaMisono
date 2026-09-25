# -*- coding: utf-8 -*-
"""test_check_feelings.py —— 给判据本身做单元测试

`check_feelings.py` 会判"合格/不合格"，而它自己判错的时候**没人会发现**——
批 6 就抓到了第一版的两个反向错误（只看开头）。所以判据要自己有测试。

做法：把 `check_feelings.py` 的源码读进来，**只执行到 `def is_bare` 结束为止**
（不跑它的 main），拿到 `is_bare` 和它的词表，然后逐条断言。

用法：<python> test_check_feelings.py
"""
import pathlib
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

SRC = pathlib.Path(r"C:\OneDrive\MikaMisono\agent\tools\check_feelings.py")
code = SRC.read_text(encoding="utf-8")

# 取「词表常量（BODY / ACT / LABEL）+ THINGS/PERSON/VERB + _has_concrete + is_bare」这一整段。
# ⚠️ 必须把常量一起取进来——第一版只截了 def，跑起来 NameError: LABEL。
start = code.index("# A 身体感觉")
m = re.search(r"^def load\(.*?(?=^\S)", code, re.S | re.M) or re.search(r"^def is_bare\(.*?(?=^\S)", code, re.S | re.M)
assert m, "没找到 is_bare 的定义"
ns: dict = {}
exec(compile(code[start:m.start()], "<is_bare>", "exec"), ns)
is_bare = ns["is_bare"]
for need in ("LABEL", "BODY", "ACT", "THINGS", "PERSON", "VERB", "_has_concrete"):
    assert need in ns, f"没取到 {need}"

CASES = [
    # ── 合格：具体反应（三种形状都要覆盖）───────────────────────
    ("心里烫了一下", False),                     # A 身体感觉
    ("手心里全是汗，可我没慌", False),             # A
    ("脑子不飘了，手也稳了", False),               # A
    ("认号码不认名字，从未含糊", False),           # B 动作/决定
    ("不想变成仗着温柔乱咬人的人", False),         # B
    ("他中午没吃饭，心疼", False),                 # 标签在后 + 有具体事
    ("心疼他一中午没吃饭", False),                 # 标签在前 + 有具体事 ← 批 6 抓到的
    ("被他信得过，比什么都好呢", False),           # C 挂件具体物
    ("舍不得先睡……这种话我才不会说出口呢", False),  # C 省略号
    ("他要是因为这个丢学分，我才是真的心疼呢", False),
    ("这句我要记一辈子呢", False),                 # B
    # ── 不合格：纯情绪标签（加语气词也是标签）─────────────────
    ("幸福", True),
    ("期待", True),
    ("害羞", True),
    ("开心", True),
    ("开心得不行", True),
    ("充实呢", True),
    ("原谅了", True),
    ("得意得不行", True),
    ("无奈", True),
    ("被惦记的温暖", True),
    ("有点心虚", True),
    ("热闹", True),
    ("", True),
]

bad = 0
for s, want in CASES:
    got = is_bare(s)
    ok = got == want
    if not ok:
        bad += 1
    print(f"  {'✓' if ok else '✗ 判错'}  {'不合格' if got else '合格  '}  {s or '(空)'}")

print(f"\n判错 {bad} / {len(CASES)}")
sys.exit(1 if bad else 0)
