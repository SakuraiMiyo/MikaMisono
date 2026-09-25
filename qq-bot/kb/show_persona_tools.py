# -*- coding: utf-8 -*-
"""show_persona_tools.py —— 看线上人格的 `tools` 字段，以及它怎么决定她拿到哪些工具

## 语义（`astr_main_agent.py` / `persona_mgr.py`）

    tools = None   → 全部工具都给她（默认，现在就是这个）
    tools = []     → 会被 `... or None` 折成 None，**等于没设**（坑）
    tools = [...]  → 白名单，只挂名单里的

隔离顺序：**先白名单 → 再去掉「未授权插件」的工具**。
所以插件工具必须把**插件名**也放进白名单，不能只放工具名。

用法：<python> show_persona_tools.py
"""
from __future__ import annotations

import datetime
import json
import pathlib
import sys

import httpx
import jwt

sys.stdout.reconfigure(encoding="utf-8")

HOME = pathlib.Path.home()
CONFIG = HOME / ".astrbot" / "data" / "cmd_config.json"
BASE = "http://127.0.0.1:6185/api/v1"


def client() -> httpx.Client:
    d = json.loads(CONFIG.read_text(encoding="utf-8-sig"))["dashboard"]
    tok = jwt.encode(
        {"username": d["username"],
         "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=2)},
        d["jwt_secret"], algorithm="HS256")
    return httpx.Client(base_url=BASE, timeout=30,
                        headers={"Authorization": f"Bearer {tok}"})


def main() -> None:
    cfg = json.loads(CONFIG.read_text(encoding="utf-8-sig"))
    name = cfg["provider_settings"]["default_personality"]
    c = client()
    r = c.get("/personas/by-id", params={"persona_id": name})
    r.raise_for_status()
    d = r.json()["data"]

    print(f"人格：{name}")
    print(f"  system_prompt   {len(d.get('system_prompt') or ''):,} 字")
    print(f"  begin_dialogs   {len(d.get('begin_dialogs') or [])} 条")
    print(f"  skills          {d.get('skills')!r}")
    print(f"  tools           {d.get('tools')!r}")
    print()
    if d.get("tools") is None:
        print("→ tools = None：她拿到**全部**工具。这就是要改的点。")
    print()
    print("人格对象里还有哪些键：")
    for k in sorted(d):
        v = d[k]
        if isinstance(v, str):
            print(f"   {k:22} <str {len(v)}>")
        elif isinstance(v, list):
            print(f"   {k:22} <list {len(v)}>")
        else:
            print(f"   {k:22} {v!r}")


if __name__ == "__main__":
    main()
