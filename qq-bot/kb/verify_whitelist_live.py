# -*- coding: utf-8 -*-
"""verify_whitelist_live.py —— 用面板 API 的权威工具清单核验白名单

## 为什么不用静态扫源码

静态扫只能看到源码里写了 `name=` 的工具，看不到：
  · `@filter.llm_tool()` 不写名字 → 用函数名注册
  · **MCP 工具**（`mcd` / `yun` 两个服务，名字只在运行时才有）
  · 哪些工具此刻 `active=False`

而 `astr_main_agent.py:635` 是 `get_func(name)` + `if tool and tool.active`——
**名字不存在、或工具被停用，都会静默少挂**。所以必须拿运行时的真实清单来核。

面板有两个接口：
  · `GET /api/v1/tools`              → 全部工具（内置 + 插件 + MCP）
  · `GET /api/v1/tools/mcp/servers`  → MCP 服务及其 tools

用法：<python> verify_whitelist_live.py
"""
from __future__ import annotations

import datetime
import json
import pathlib
import re
import sys

import httpx
import jwt

sys.stdout.reconfigure(encoding="utf-8")

CONFIG = pathlib.Path.home() / ".astrbot" / "data" / "cmd_config.json"
BASE = "http://127.0.0.1:6185/api/v1"
WL = pathlib.Path(r"C:\OneDrive\MikaMisono\persona-merge\apply_tool_whitelist.py")


def client() -> httpx.Client:
    d = json.loads(CONFIG.read_text(encoding="utf-8-sig"))["dashboard"]
    tok = jwt.encode(
        {"username": d["username"],
         "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=2)},
        d["jwt_secret"], algorithm="HS256")
    return httpx.Client(base_url=BASE, timeout=40,
                        headers={"Authorization": f"Bearer {tok}"})


def read_whitelist() -> list[str]:
    """从 apply_tool_whitelist.py 里抠出 WHITELIST 列表项。

    ⚠️ 第一版是按行抓所有 `"..."`，结果把注释里的中文也当成了工具名
    （名单里有 `# ── 某某（老师要求）──` 这种行，还有 `"先查知识库"` 之类的说明）。
    现在只认**缩进 + 单行字符串 + 结尾逗号**那种真·列表项。
    """
    src = WL.read_text(encoding="utf-8")
    m = re.search(r"^WHITELIST: list\[str\] = \[(.*?)^\]", src, re.S | re.M)
    if not m:
        m = re.search(r"^WHITELIST = \[(.*?)^\]", src, re.S | re.M)
    if not m:
        print("✗ 抠不出 WHITELIST")
        sys.exit(1)
    names = []
    for line in m.group(1).splitlines():
        line = line.split("#", 1)[0].rstrip()      # 去掉行尾注释
        s = re.match(r'^\s*"([A-Za-z0-9_\-\.]+)",\s*$', line)
        if s:
            names.append(s.group(1))
    return names


def main() -> None:
    want = read_whitelist()

    c = client()

    # ── 权威名单 ────────────────────────────────────────────────────
    live: dict[str, bool] = {}
    for path in ("/tools", "/tools/list"):
        try:
            r = c.get(path)
            if r.status_code != 200:
                continue
            j = r.json()
            data = j.get("data", j)
            if isinstance(data, dict) and "tools" in data:
                data = data["tools"]
            if not isinstance(data, list):
                continue
            for x in data:
                if isinstance(x, dict) and x.get("name"):
                    live[x["name"]] = bool(x.get("active", True))
            if live:
                print(f"工具清单来自 {path}：{len(live)} 个")
                break
        except Exception:
            continue

    # MCP
    mcp_names: set[str] = set()
    try:
        r = c.get("/tools/mcp/servers")
        if r.status_code == 200:
            j = r.json()
            data = j.get("data", j)
            for srv in (data or []):
                for t in (srv.get("tools") or []):
                    mcp_names.add(t if isinstance(t, str) else t.get("name"))
            print(f"MCP 服务 {len(data or [])} 个，工具 {len(mcp_names)} 个")
    except Exception as e:
        print("MCP 接口没读到：", e)

    print()
    if not live:
        print("✗ 一个工具名都没读到——接口路径可能不对，下面的核验没法做。")
        sys.exit(1)

    known = set(live) | mcp_names
    print(f"权威工具总数：{len(known)}\n")
    print(f"待核验白名单：{len(want)} 个\n")

    bad = []
    for n in want:
        if n in known:
            act = live.get(n, True)
            mark = "✓" if act else "✗ 已停用"
            if not act:
                bad.append((n, "active=False"))
            print(f"  {mark:10} {n}")
        else:
            bad.append((n, "名字不存在"))
            print(f"  ✗ 找不到   {n}")

    print()
    if bad:
        print(f"⚠️ {len(bad)} 个有问题（写进白名单会静默少挂）：")
        for n, why in bad:
            print(f"   · {n}  —— {why}")
    else:
        print("✓ 白名单里每个名字都在权威清单里且已启用。")

    # 反向：被排除掉的高危工具，确认它们本来确实在
    print("\n── 被白名单排除、但确实存在的高危工具 ──")
    DANGER = ["astrbot_execute_shell", "astrbot_shell_session", "astrbot_grep_tool",
              "astrbot_cua_mouse_click", "astrbot_cua_keyboard_type",
              "astrbot_cua_screenshot", "astrbot_execute_browser",
              "astrbot_file_edit_tool", "hapi_coding_execute_command"]
    for d in DANGER:
        print(f"   {'在' if d in known else '不在':4} {d}")

    # 顺带看看有没有什么她显然用得上、但我漏了的功能
    print("\n── 权威清单里含这些关键词的工具（检查我有没有漏掉该留的）──")
    for kw in ("qzone", "feed", "photo", "draw", "image", "emoji", "sticker",
               "knowledge", "memory", "voice", "search"):
        hits = sorted(n for n in known if kw.lower() in n.lower())
        if hits:
            print(f"   [{kw}] {', '.join(hits)}")


if __name__ == "__main__":
    main()
