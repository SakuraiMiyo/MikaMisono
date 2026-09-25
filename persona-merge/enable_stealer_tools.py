# -*- coding: utf-8 -*-
"""enable_stealer_tools.py —— 启用「表情包小偷」插件及其三个 LLM 工具

## 为什么单独一个脚本

`search_emoji` / `send_emoji_by_id` / `steal_sticker` 三个工具启不动，
PATCH 返回 400：

    此函数调用工具所属的插件 astrbot_plugin_stealer 已被禁用，
    请先在管理面板启用再激活此工具。

**顺序不能反**：插件禁用 → 它下面所有 LLM 工具都激不活。
所以是「先启插件 → 再逐个启工具 → 回读确认」。

## 用法

    <python> enable_stealer_tools.py            # 只看状态
    <python> enable_stealer_tools.py --apply    # 启用
"""
from __future__ import annotations

import argparse
import datetime
import json
import pathlib
import sys

import httpx
import jwt

sys.stdout.reconfigure(encoding="utf-8")

CONFIG = pathlib.Path.home() / ".astrbot" / "data" / "cmd_config.json"
BASE = "http://127.0.0.1:6185/api/v1"
BAK = pathlib.Path(r"C:\OneDrive\MikaMisono\_archive-20260924")

PLUGIN = "astrbot_plugin_stealer"
TOOLS = ["search_emoji", "send_emoji_by_id", "steal_sticker"]


def client() -> httpx.Client:
    d = json.loads(CONFIG.read_text(encoding="utf-8-sig"))["dashboard"]
    tok = jwt.encode(
        {"username": d["username"],
         "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=2)},
        d["jwt_secret"], algorithm="HS256")
    return httpx.Client(base_url=BASE, timeout=60,
                        headers={"Authorization": f"Bearer {tok}"})


def plugin_state(c: httpx.Client) -> dict:
    r = c.get(f"/plugins/{PLUGIN}")
    if r.status_code != 200:
        return {}
    j = r.json()
    return j.get("data", j) or {}


def tool_state(c: httpx.Client) -> dict[str, bool]:
    data = c.get("/tools").json()
    data = data.get("data", data)
    if isinstance(data, dict) and "tools" in data:
        data = data["tools"]
    return {t["name"]: bool(t.get("active", True)) for t in data}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    c = client()
    p = plugin_state(c)
    print(f"插件 {PLUGIN}")
    for k in ("name", "display_name", "activated", "enabled", "version", "reserved"):
        if k in p:
            print(f"   {k:16} {p[k]!r}")
    if not p:
        print("   （读不到插件详情）")

    st = tool_state(c)
    print("\n工具状态：")
    for t in TOOLS:
        print(f"   {t:22} active={st.get(t)}")

    if not a.apply:
        print("\n（预览。加 --apply 才启用。）")
        return

    BAK.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    (BAK / f"plugin-{PLUGIN}-before-{stamp}.json").write_text(
        json.dumps(p, ensure_ascii=False, indent=1), encoding="utf-8")

    print("\n── 1. 启用插件 ──")
    r = c.patch(f"/plugins/{PLUGIN}/enabled", json={"enabled": True})
    print(f"   PATCH -> {r.status_code}  {r.text[:200]}")
    if r.status_code != 200:
        # 退到 legacy 路径
        r = c.post("/api/plugin/on", json={"name": PLUGIN})
        print(f"   legacy /api/plugin/on -> {r.status_code}  {r.text[:200]}")

    # 插件启用可能要一点时间重新注册 llm 工具
    import time
    for _ in range(10):
        time.sleep(1.5)
        if tool_state(c).get(TOOLS[0]) is not None:
            break

    print("\n── 2. 逐个启用工具 ──")
    for t in TOOLS:
        rr = c.patch(f"/tools/{t}/enabled", json={"enabled": True})
        body = rr.text[:160]
        print(f"   {t:22} -> {rr.status_code}  {body}")

    print("\n── 3. 回读 ──")
    st2 = tool_state(c)
    ok = 0
    for t in TOOLS:
        v = st2.get(t)
        print(f"   {t:22} active={v}")
        if v:
            ok += 1
    print(f"\n{ok}/{len(TOOLS)} 已启用")


if __name__ == "__main__":
    main()
