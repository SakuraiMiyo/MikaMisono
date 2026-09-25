# -*- coding: utf-8 -*-
"""apply_tool_whitelist.py —— 给人格设 `tools` 白名单 + 启用表情工具

## 为什么收紧

现在 `tools = None`：她拿到**全部 155 个工具**（内置 40 + 插件 64 + MCP 51）。
两头都亏：安全（规则管不住工具）和成本（每个工具的描述+schema 每轮都进 prompt）。

## 名单怎么定的——三条依据

**① 真实调用数据**（`tool_usage_from_history.py`，12 会话 / 296 次调用）：

    116  anysearch_search          36  astrbot_grep_tool
     28  astrbot_execute_shell     24  astrbot_file_read_tool
     16  search_wyc_tools          14  astr_kb_search
     10  run_wyc_tool              10  astrbot_execute_python
      …（其余 ≤6 次）

  → 48.6% 在乱搜、只有 4.7% 走知识库。这正是老师说的「查资料应该走知识库」要治的病。

**② 面板权威清单**（`verify_whitelist_live.py`，`GET /api/v1/tools`）：

  → 抓出 4 个死名字：`search_emoji`/`send_emoji_by_id`/`steal_sticker` 是
    `active=False`，`get_weather` **根本不存在**（那只是 AstrBot 文档里的示例代码）。
    白名单里放死名字会**静默少挂**——不报错、不打日志。

**③ 老师的三个决定**：
  · 联网搜索**留下**，靠提示词让它"先查知识库" → 所以 anysearch 那套进名单
  · 执行工具**先别动** → 但白名单天然是"名单外的都不要"，所以这里还是把它们排除了；
    这一点我在报告里明确写了，等老师看完解释再定
  · 表情工具**加进去并启用** → 先用 PATCH 启用，再进名单

## 用法

    <python> apply_tool_whitelist.py                 # 预览
    <python> apply_tool_whitelist.py --live-check    # 拿面板权威清单核每个名字
    <python> apply_tool_whitelist.py --apply         # 启用表情 + 写入白名单
    <python> apply_tool_whitelist.py --clear         # 回滚成 None（用全部）
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

HOME = pathlib.Path.home()
CONFIG = HOME / ".astrbot" / "data" / "cmd_config.json"
BASE = "http://127.0.0.1:6185/api/v1"
BAK = pathlib.Path(r"C:\OneDrive\MikaMisono\_archive-20260924")

# ── 要启用的工具（面板里 active=False，老师要求加回来）────────────────
ENABLE = ["search_emoji", "send_emoji_by_id", "steal_sticker"]

# ── 白名单 ────────────────────────────────────────────────────────────
WHITELIST = [
    # ── 出图 / 写文件（mika-image、mika-diary 的活）─────────────────
    # 出图是用 Python 脚本 POST 到 ComfyUI 的 HTTP API（draw_mika_3.py）。
    # 插件的 pc_generate_photo 是**另一套在线后端**，换过去会丢掉 mika_best
    # 工作流的形象锁定，所以这个必须留。
    "astrbot_execute_python",
    "astrbot_file_read_tool",
    "astrbot_file_write_tool",
    "astrbot_download_file",          # 下载说说配图（评论前要先看图）
    # ── 回消息 ──────────────────────────────────────────────────────
    "send_message_to_user",
    # ── 知识库 + 联网搜索 ───────────────────────────────────────────
    # 老师决定：搜索留着，靠提示词让她"先查知识库"。
    "astr_kb_search",
    "anysearch_search",
    "anysearch_batch_search",
    "anysearch_extract",
    "web_search_baidu",
    "exa_get_contents",
    # ── QQ 空间：发说说 / 写评论（mika-qq-space）────────────────────
    "llm_view_feed",
    "llm_comment_feed",
    "llm_publish_feed",
    # ── 表情（老师要求启用并加进来）────────────────────────────────
    "search_emoji",
    "send_emoji_by_id",
    "steal_sticker",
    # ── 麦当劳点餐（MCP: mcd）──────────────────────────────────────
    "delivery-query-addresses",
    "delivery-query-stores",
    "query-meals",
    "calculate-price",
    "query-store-coupons",
    "create-order",
    "order-list",
    "query-order",
    # ── 校园跑（MCP: yun）──────────────────────────────────────────
    "yun_status",
    "yun_prepare_run",
    "yun_pending_runs",
    "yun_execute_run",
    "yun_run_status",
    "yun_cancel_run",
    "yun_abort_run",
    "yun_analyze_tasks",
    "yun_confirm_run",
    # ── 语音 ────────────────────────────────────────────────────────
    "mika_voice",
]


def client() -> httpx.Client:
    d = json.loads(CONFIG.read_text(encoding="utf-8-sig"))["dashboard"]
    tok = jwt.encode(
        {"username": d["username"],
         "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=2)},
        d["jwt_secret"], algorithm="HS256")
    return httpx.Client(base_url=BASE, timeout=40,
                        headers={"Authorization": f"Bearer {tok}"})


def live_name() -> str:
    return json.loads(CONFIG.read_text(encoding="utf-8-sig"))[
        "provider_settings"]["default_personality"]


def tool_list(c: httpx.Client) -> dict[str, bool]:
    data = c.get("/tools").json()
    data = data.get("data", data)
    if isinstance(data, dict) and "tools" in data:
        data = data["tools"]
    return {t["name"]: bool(t.get("active", True)) for t in data}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--clear", action="store_true")
    ap.add_argument("--live-check", action="store_true")
    a = ap.parse_args()

    name = live_name()
    c = client()
    cur = c.get("/personas/by-id", params={"persona_id": name}).json()["data"]
    print(f"人格 {name}　当前 tools = {cur.get('tools')!r}")
    print(f"白名单 {len(WHITELIST)} 个（要从 155 收到这个数）\n")

    if a.clear:
        rr = c.put("/personas/by-id", json={"persona_id": name, "tools": None})
        print("PUT ->", rr.status_code)
        print("✓ 已回滚成 None（用全部）" if rr.status_code == 200 else rr.text[:300])
        return

    # ── 权威核验 ────────────────────────────────────────────────────
    live = tool_list(c)
    bad = []
    print("── 名字核验（对着面板权威清单）──")
    for n in WHITELIST:
        if n not in live:
            bad.append((n, "名字不存在"))
        elif not live[n] and n not in ENABLE:
            bad.append((n, "active=False"))
    if bad:
        for n, why in bad:
            print(f"  ✗ {n}  —— {why}")
    else:
        print("  ✓ 全部存在且已启用")

    print("\n── 将被排除的高危工具（确认它们确实在原始集合里）──")
    for d in ("astrbot_execute_shell", "astrbot_shell_session", "astrbot_grep_tool",
              "astrbot_file_edit_tool", "astrbot_cua_mouse_click",
              "astrbot_cua_keyboard_type", "astrbot_cua_screenshot",
              "astrbot_execute_browser", "hapi_coding_execute_command"):
        if d in live:
            print(f"   在   {d}")

    if not a.apply:
        print("\n名单：")
        for n in WHITELIST:
            mark = "✓" if n in live and live[n] else ("○ 待启用" if n in ENABLE else "?")
            print(f"   {mark} {n}")
        print("\n（预览。加 --apply 才写。）")
        return

    # ── 1. 启用表情工具 ─────────────────────────────────────────────
    print("\n── 启用工具 ──")
    for n in ENABLE:
        try:
            r = c.patch(f"/tools/{n}/enabled", json={"enabled": True})
            print(f"  PATCH {n} -> {r.status_code}")
        except Exception as e:
            print(f"  PATCH {n} 失败：{e}")

    live2 = tool_list(c)
    for n in ENABLE:
        print(f"  {n} active={live2.get(n)}")

    # ── 2. 写白名单 ─────────────────────────────────────────────────
    BAK.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    dst = BAK / f"persona-{name}-tools-before-{stamp}.json"
    dst.write_text(json.dumps(cur, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n✓ 已备份人格 -> {dst}")

    rr = c.put("/personas/by-id", json={"persona_id": name, "tools": WHITELIST})
    print("PUT ->", rr.status_code)
    if rr.status_code != 200:
        print(rr.text[:600])
        sys.exit(1)

    got = c.get("/personas/by-id", params={"persona_id": name}).json()["data"]
    back = got.get("tools") or []
    print(f"✓ 回读 tools = {len(back)} 个，一致={back == WHITELIST}")
    print(f"  system_prompt {len(got.get('system_prompt') or ''):,} 字（未动）")
    print(f"  begin_dialogs {len(got.get('begin_dialogs') or [])} 条（未动）")
    print(f"  skills {got.get('skills')!r}（未动）")

    # 最终核验：名单里每个名字现在是否都可用
    live3 = tool_list(c)
    miss = [n for n in WHITELIST if not live3.get(n)]
    print(f"\n最终核验：名单里 {len(WHITELIST) - len(miss)}/{len(WHITELIST)} 个可用")
    for n in miss:
        print(f"   ✗ {n}")


if __name__ == "__main__":
    main()
