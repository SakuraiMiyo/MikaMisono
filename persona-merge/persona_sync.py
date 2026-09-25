#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""persona_sync.py —— 把「我真在改的那份」同步到「线上真正生效的那份」

## 事故现场（2026-09-25 发现）

`persona_mgr.resolve_selected_persona()` 的取用顺序：

    1. session_service_config.persona_id        （会话级强制，一般没有）
    2. conversation.persona_id                  （会话自己的，全是 None）
    3. provider_settings.default_personality    ← 兜底

而库里是这样：

| 人格 | 字数 | 内容 |
|---|---:|---|
| `未小花！` | 23,161 | **今天所有改动都写在这**（语气词/吃音/口头禅/称呼/身份防线…） |
| `未小花0924` ★默认 | 19,592 | **只有最早那两三个补丁**，停在 09-24 08:40 |

`cmd_config.json` 里 `default_personality = '未小花0924'`，
**所以线上跑的是一份过期的稿子**——「你住在夏莱」那条根本没生效。

## 这个脚本做什么

把 `未小花！` 的 `system_prompt` / `begin_dialogs` / `skills` **原样复制到 `未小花0924`**，
让线上那一份立刻追上。（只传这三个字段，不动 `tools` / `folder_id` 等。）

用法：
    <python> persona_sync.py --check     # 只看两份差多少，不写
    <python> persona_sync.py             # 真的同步
    <python> persona_sync.py --to 未小花！  # 反过来，把默认切到 未小花！
"""
from __future__ import annotations

import datetime
import json
import os
import pathlib
import sys

import httpx
import jwt

HOME = pathlib.Path.home()
CONFIG = HOME / ".astrbot" / "data" / "cmd_config.json"
BASE = "http://127.0.0.1:6185/api/v1"
HERE = pathlib.Path(__file__).resolve().parent
BAK = HERE / "_live-persona-backup"


def live_name() -> str:
    """线上真正生效的人格名 = provider_settings.default_personality"""
    cfg = json.loads(CONFIG.read_text(encoding="utf-8-sig"))
    return cfg.get("provider_settings", {}).get("default_personality") or ""


def client() -> httpx.Client:
    d = json.loads(CONFIG.read_text(encoding="utf-8-sig"))["dashboard"]
    tok = jwt.encode(
        {"username": d["username"],
         "exp": datetime.datetime.now(datetime.timezone.utc)
         + datetime.timedelta(hours=2)},
        d["jwt_secret"], algorithm="HS256")
    return httpx.Client(base_url=BASE, timeout=30,
                        headers={"Authorization": f"Bearer {tok}"})


def get(c: httpx.Client, pid: str) -> dict:
    r = c.get("/personas/by-id", params={"persona_id": pid})
    r.raise_for_status()
    return r.json()["data"]


def main() -> None:
    check = "--check" in sys.argv
    target = None
    if "--to" in sys.argv:
        target = sys.argv[sys.argv.index("--to") + 1]
    SOURCE = "未小花！"
    TARGET = target or live_name()

    c = client()
    live = live_name()
    print(f"配置里的默认人格（= 线上生效）: {live!r}")

    src = get(c, SOURCE)
    dst = get(c, TARGET)
    print(f"\n源   [{SOURCE}]  system_prompt {len(src.get('system_prompt') or ''):,} 字  "
          f"begin_dialogs {len(src.get('begin_dialogs') or [])} 条  "
          f"skills={src.get('skills')}")
    print(f"目标 [{TARGET}]  system_prompt {len(dst.get('system_prompt') or ''):,} 字  "
          f"begin_dialogs {len(dst.get('begin_dialogs') or [])} 条  "
          f"skills={dst.get('skills')}")

    if not target and live != SOURCE:
        print(f"\n⚠️ 线上生效的是 [{live}]，不是你一直在改的 [{SOURCE}]——这就是刚才那份过期稿的问题。")

    if check:
        d_sp = (src.get("system_prompt") or "") == (dst.get("system_prompt") or "")
        d_bd = (src.get("begin_dialogs") or []) == (dst.get("begin_dialogs") or [])
        d_sk = (src.get("skills") or []) == (dst.get("skills") or [])
        print(f"\n一致？ system_prompt={d_sp}  begin_dialogs={d_bd}  skills={d_sk}")
        return

    # 备份目标
    BAK.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    (BAK / f"persona-{TARGET}-{stamp}.json").write_text(
        json.dumps(dst, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n✓ 已备份目标人格 → {BAK / f'persona-{TARGET}-{stamp}.json'}")

    payload = {
        "persona_id": TARGET,
        "system_prompt": src.get("system_prompt") or "",
        "begin_dialogs": src.get("begin_dialogs") or [],
        "skills": src.get("skills"),
    }
    r = c.put("/personas/by-id", json=payload)
    print("PUT ->", r.status_code)
    if r.status_code != 200:
        print(r.text[:600])
        raise SystemExit(1)

    got = get(c, TARGET)
    ok_sp = (got.get("system_prompt") or "") == payload["system_prompt"]
    ok_bd = (got.get("begin_dialogs") or []) == payload["begin_dialogs"]
    ok_sk = (got.get("skills") or []) == (payload["skills"] or [])
    print(f"✓ 已写入 [{TARGET}]：system_prompt {len(got.get('system_prompt') or ''):,} 字  "
          f"begin_dialogs {len(got.get('begin_dialogs') or [])} 条  skills={got.get('skills')}")
    print(f"  回读校验：prompt={ok_sp}  dialogs={ok_bd}  skills={ok_sk}")
    assert ok_sp and ok_bd and ok_sk, "回读不一致"


if __name__ == "__main__":
    main()
