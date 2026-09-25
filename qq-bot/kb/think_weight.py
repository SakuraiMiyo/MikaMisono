#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""think_weight.py —— 历史里「思考块」占多少

发现在 `raw_msgs.py`：她那条回复的 content 里有

    {"type": "think", "think": "老师回了个"？？？"，引用了一条消息…（一大段推理）"}

也就是**她的思考过程被存进了对话历史**。两个后果：
  1. 占 token（每轮都要带上）
  2. 她下一轮读得到自己上一次的推理——里面全是「括号里不要叙述任务」「3-4 条」这种
     自我提醒，会让她越来越像在执行规则，而不是在说话
"""
from __future__ import annotations

import json
import os
import pathlib
import sqlite3

DB = pathlib.Path(os.path.expanduser("~")) / ".astrbot" / "data" / "data_v4.db"
c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)

for cid, content in c.execute(
        "select conversation_id, content from conversations "
        "order by updated_at desc limit 4"):
    j = json.loads(content or "{}")
    h = j.get("history") if isinstance(j, dict) else j
    if not isinstance(h, list):
        continue
    think = txt = img = n_think = 0
    for m in h:
        if not isinstance(m, dict):
            continue
        cc = m.get("content")
        if isinstance(cc, list):
            for s in cc:
                if not isinstance(s, dict):
                    continue
                if s.get("type") == "think":
                    n_think += 1
                    think += len(str(s.get("think") or ""))
                elif s.get("type") == "image_url":
                    img += len(json.dumps(s.get("image_url"), ensure_ascii=False))
                else:
                    txt += len(str(s.get("text") or ""))
        else:
            txt += len(str(cc or ""))
    tot = think + txt + img
    print(f"[{cid[:8]}] {len(h)} 条")
    print(f"   正文+工具 {txt:>9,} 字")
    print(f"   思考块    {think:>9,} 字（{n_think} 段，占 {think / tot:.1%}）" if tot else "")
    print(f"   图片      {img:>9,} 字")
    print()
