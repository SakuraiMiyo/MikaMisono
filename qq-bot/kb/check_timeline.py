#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_timeline.py —— timeline.json / emotion_state.json 的结构校验器

时间线和情绪状态是「注入她上下文」的活数据，写错字段就是静默失效
（patch_context_timeline.py 对损坏文件会静默跳过——这是容错，不是校验）。
改完任何一个文件，跑一下这个：

    & 'C:\\SoftWare\\Astrbot\\backend\\python\\python.exe' qq-bot\\kb\\check_timeline.py

检查项：
  timeline.json
    t1  JSON 可解析、有 version / facts 数组
    t2  每条 fact：id 唯一；entity/attribute/value/source 非空
    t3  valid_from / valid_to 是 YYYY-MM-DD 或 null；valid_from <= valid_to
    t4  同一 entity+attribute 至多一条「当前有效」（valid_to 为空或未到期）
    t5  value 里不出现 AI 破绽词（内核/重置/模型/提示词/版本号等——身份防线）
  emotion_state.json
    e1  JSON 可解析；mood.valence 是 -5..5 整数；energy 是 0..100 整数
    e2  toward_teacher.warmth 是 0..5 整数
    e3  events_log 每条有 date/event/delta；date 倒序（最新在前）
    e4  updated_at 不早于最新 event 的 date（改了事件就要动 updated_at）
"""
from __future__ import annotations

import datetime
import json
import pathlib
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

MEM = pathlib.Path(r"C:\OneDrive\MikaMisono\agent\memory")
TL = MEM / "timeline.json"
EMO = MEM / "emotion_state.json"

# 身份防线：这些词不该出现在「她的生活事实」的 value 里（source 字段除外，她看不到）
SLOP_RE = re.compile(r"内核|重置|模型|提示词|prompt|AstrBot|插件|上下文|token|v4\.\d+")

ok = True


def bad(msg):
    global ok
    ok = False
    print(f"  ✗ {msg}")


def good(msg):
    print(f"  ✓ {msg}")


DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def is_date(s) -> bool:
    try:
        datetime.date.fromisoformat(str(s)[:10])
        return bool(DATE_RE.match(str(s)[:10]))
    except Exception:
        return False


print("=" * 60)
print("timeline.json")
print("=" * 60)
try:
    tl = json.loads(TL.read_text(encoding="utf-8"))
except Exception as e:
    bad(f"JSON 解析失败：{e}")
    tl = None

today = datetime.date.today()
if tl is not None:
    if not isinstance(tl.get("facts"), list):
        bad("t1 facts 不是数组")
    else:
        good(f"t1 共 {len(tl['facts'])} 条事实")
        ids = set()
        current_keys: dict[str, int] = {}
        for i, f in enumerate(tl["facts"]):
            fid = f.get("id")
            if not fid or fid in ids:
                bad(f"t2 [{i}] id 缺失或重复：{fid!r}")
            ids.add(fid)
            for k in ("entity", "attribute", "value", "source"):
                if not str(f.get(k, "")).strip():
                    bad(f"t2 [{fid}] {k} 为空")
            vf, vt = f.get("valid_from"), f.get("valid_to")
            if vf and not is_date(vf):
                bad(f"t3 [{fid}] valid_from 不是日期：{vf!r}")
            if vt is not None and not is_date(vt):
                bad(f"t3 [{fid}] valid_to 不是日期或 null：{vt!r}")
            if vf and vt and is_date(vf) and is_date(vt) and str(vt)[:10] < str(vf)[:10]:
                bad(f"t3 [{fid}] valid_to 早于 valid_from")
            if SLOP_RE.search(str(f.get("value", ""))):
                bad(f"t5 [{fid}] value 含 AI 破绽词：{SLOP_RE.search(f['value']).group()}")
            still = True
            try:
                if vf and datetime.date.fromisoformat(str(vf)[:10]) > today:
                    still = False
                if vt and datetime.date.fromisoformat(str(vt)[:10]) < today:
                    still = False
            except Exception:
                still = False
            if still:
                key = f"{f.get('entity')}|{f.get('attribute')}"
                current_keys[key] = current_keys.get(key, 0) + 1
        for key, n in current_keys.items():
            if n > 1:
                bad(f"t4 当前有效的事实里 {key!r} 有 {n} 条（至多 1 条）")
        if ok:
            good("t2-t5 全部通过")

print()
print("=" * 60)
print("emotion_state.json")
print("=" * 60)
try:
    emo = json.loads(EMO.read_text(encoding="utf-8"))
except Exception as e:
    bad(f"JSON 解析失败：{e}")
    emo = None

if emo is not None:
    mood = emo.get("mood") or {}
    v = mood.get("valence")
    if not isinstance(v, int) or not (-5 <= v <= 5):
        bad(f"e1 mood.valence 应为 -5..5 整数，现在是 {v!r}")
    en = emo.get("energy")
    if not isinstance(en, int) or not (0 <= en <= 100):
        bad(f"e1 energy 应为 0..100 整数，现在是 {en!r}")
    else:
        good(f"e1 valence={v} energy={en}")
    tt = (emo.get("toward_teacher") or {}).get("warmth")
    if not isinstance(tt, int) or not (0 <= tt <= 5):
        bad(f"e2 warmth 应为 0..5 整数，现在是 {tt!r}")
    log = emo.get("events_log") or []
    dates = []
    for i, ev in enumerate(log):
        if not ev.get("date") or not ev.get("event") or "delta" not in ev:
            bad(f"e3 events_log[{i}] 缺 date/event/delta")
        dates.append(str(ev.get("date")))
    if dates and dates != sorted(dates, reverse=True):
        bad(f"e3 events_log 不是最新在前：{dates}")
    if dates:
        upd = str(emo.get("updated_at", ""))[:10]
        if upd and upd < dates[0]:
            bad(f"e4 updated_at({upd}) 早于最新事件({dates[0]})——改了事件要动 updated_at")
    if ok:
        good("e1-e4 全部通过")

print()
print("结论：" + ("全部通过 ✓" if ok else "有问题 ✗（上面的 ✗ 都要修）"))
sys.exit(0 if ok else 1)
