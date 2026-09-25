#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mika_kb.py —— 未花 QQ 知识库：分块 + 导入 + 差分同步

作用：把本项目的角色语料（含日记）切成语义块，通过 AstrBot 的 HTTP API 灌进知识库。
设计要点：
  · 按 markdown 标题切块（`##` / `###`），每块带标题前缀，剧情类天然成块
  · 日记按「一天一块」，检索时能精确定位到日期
  · 差分：状态文件记录已同步的日记日期，只导新增
  · 只依赖 httpx + AstrBot 自带的 dashboard token，不碰老师的面板密码

用法（在项目根目录下）：
    <AstrBot python> qq-bot/kb/mika_kb.py --sync         # 全部：建库 + 导入语料 + 同步日记
    <AstrBot python> qq-bot/kb/mika_kb.py --sync-diary   # 只同步新日记（写完日记就跑这个）
    <AstrBot python> qq-bot/kb/mika_kb.py --status       # 只看状态
    <AstrBot python> qq-bot/kb/mika_kb.py --verify "问题" # 检索验证
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import sys
import time
from pathlib import Path

import httpx

# ── 路径 ────────────────────────────────────────────────────────────────────
PROJECT = Path(__file__).resolve().parents[2]          # C:\OneDrive\MikaMisono
AGENT = PROJECT / "agent"
QQBOT = PROJECT / "qq-bot"
STATE_FILE = Path(__file__).resolve().parent / "kb_state.json"
TOKEN_FILE = Path.home() / ".astrbot" / "data" / ".kb_session_token"
CONFIG_FILE = Path.home() / ".astrbot" / "data" / "cmd_config.json"
BASE = "http://127.0.0.1:6185/api/v1"

EMBED_PROVIDER = "mika-ollama/bge-m3"

# ── 知识库定义：分用途 ───────────────────────────────────────────────────────
KBS: dict[str, dict] = {
    "故事与设定": {
        "kb_name": "未花·故事与设定",
        "emoji": "🌸",
        "description": "圣园未花的角色设定、Vol.3 主线剧情、泳装篇与婚后后续、人际关系、游戏内数值、梗与趣闻",
        "sources": [
            (AGENT / "knowledge" / "character-profile.md", "角色档案"),
            (AGENT / "knowledge" / "story-archive.md", "主线剧情 Vol.3"),
            (AGENT / "knowledge" / "swimsuit-archive.md", "泳装篇与后续"),
            (AGENT / "knowledge" / "relationships.md", "人际关系"),
            # 游戏内数值：技能名/倍率、战地适性、赠品、固有武器（日服核实版）
            (AGENT / "knowledge" / "game-data.md", "游戏数据"),
            (AGENT / "knowledge" / "trivia.md", "梗与趣闻"),
            # ⚠️ 绝对不要加 trivia-unverified.md —— 那是「不要当设定用」的待核文件。
            #    把它喂进知识库 = 让模型把存疑内容当事实检索出来。仅作线索，不进检索。
        ],
    },
    "语气与台词": {
        "kb_name": "未花·语气与台词",
        "emoji": "🎀",
        "description": "圣园未花的台词语料、MomoTalk 原话、语言技术规范——说话像不像未花看这本",
        "sources": [
            (AGENT / "knowledge" / "dialogue-corpus.md", "台词语料库"),
            # MomoTalk 逐字原话（未花 158 条 / 老师 35 条）。由
            # `assets/story-cn/build_momotalk_md.py` 从 corpus 渲染成按话题分块的 md。
            # ⚠️ 说话人必须保留：老师的话是上下文，但不能被当成她的口吻。
            (QQBOT / "kb" / "docs" / "MomoTalk原话.md", "MomoTalk原话"),
        ],
    },
    "出图与日常": {
        "kb_name": "未花·出图与日常",
        "emoji": "🎨",
        "description": "出图提示词系统（形象锁定）、平台流程（点餐 / ComfyUI 出图 / 发说说 / 写评论）——"
                       "「老师让你做事」的时候查这本",
        "sources": [
            (QQBOT / "notes" / "mika-image-prompts.md", "出图提示词系统"),
            # 平台流程：原先常驻在 QQ 人格提示词里占 4,000+ 字，实际只在用到那一刻才需要。
            # 点餐的门店码/商品码已从「麦当劳点餐备忘.md」并进来，那边不再单独入索引（避免两份真源）。
            (QQBOT / "kb" / "docs" / "平台流程.md", "平台流程"),
        ],
    },
    "日记": {
        "kb_name": "未花·日记",
        "emoji": "📔",
        "description": "未花的日记原文，按天成块——「那天发生了什么」从这里找",
        "diary": True,
    },
    "原作考据": {
        "kb_name": "未花·原作考据",
        "emoji": "🔍",
        "description": "外部 CSP 研究稿（2026-09-24 截止）：设定与世界观、人格与行为动态、表达质感、"
                       "关系与社会认知、关键场景与决策、行为蒸馏链、媒体覆盖、联网补充、语料验收。"
                       "记录的是「这条结论是怎么来的」——含原始证据、来源编号与可信度标注。"
                       "⚠️ 研究口吻（带「可能」「本轮未覆盖」这类限定），**不要当台词直接说出口**。",
        "sources": [
            # 来自 misono-mika-csp/references/ 的九篇研究稿（正文逐字复制，只加了警示头）。
            # 与 agent/knowledge/ 的区别：那边是「结论」，这边是「证据链与可信度」。
            # ⚠️ 这里有几处会**撤回现有 KB 的说法**（如小春的重要性、☆/♪ 频率的旧描述），
            #    取用冲突时以提示词和「语气与台词」「故事与设定」为准。
            (QQBOT / "kb" / "docs" / "csp" / "CSP·设定与世界观.md", "CSP·设定与世界观"),
            (QQBOT / "kb" / "docs" / "csp" / "CSP·人格与行为动态.md", "CSP·人格与行为动态"),
            (QQBOT / "kb" / "docs" / "csp" / "CSP·表达质感.md", "CSP·表达质感"),
            (QQBOT / "kb" / "docs" / "csp" / "CSP·关系与社会认知.md", "CSP·关系与社会认知"),
            (QQBOT / "kb" / "docs" / "csp" / "CSP·关键场景与决策.md", "CSP·关键场景与决策"),
            (QQBOT / "kb" / "docs" / "csp" / "CSP·行为蒸馏链.md", "CSP·行为蒸馏链"),
            (QQBOT / "kb" / "docs" / "csp" / "CSP·媒体覆盖与资料边界.md", "CSP·媒体覆盖与资料边界"),
            (QQBOT / "kb" / "docs" / "csp" / "CSP·联网补充与纠错.md", "CSP·联网补充与纠错"),
            (QQBOT / "kb" / "docs" / "csp" / "CSP·语料验收记录.md", "CSP·语料验收记录"),
        ],
    },
}

MAX_CHUNK_CHARS = 900     # 目标块大小（中文），超过就切
MIN_CHUNK_CHARS = 120     # 太短的块并入上一块
HEADING_RE = re.compile(r"^(#{2,4})\s+(.+?)\s*$", re.MULTILINE)


# ── 认证 ────────────────────────────────────────────────────────────────────
def get_token() -> str:
    if TOKEN_FILE.exists():
        tok = TOKEN_FILE.read_text(encoding="utf-8").strip()
        if tok:
            return tok
    # 没有就现签一个（用 dashboard 的 jwt_secret，不碰面板密码）
    import datetime
    import jwt
    cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8-sig"))
    dash = cfg["dashboard"]
    tok = jwt.encode(
        {"username": dash["username"],
         "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7)},
        dash["jwt_secret"], algorithm="HS256")
    TOKEN_FILE.write_text(tok, encoding="utf-8")
    return tok


def client() -> httpx.Client:
    return httpx.Client(timeout=300, headers={"Authorization": f"Bearer {get_token()}"})


# ── 分块 ────────────────────────────────────────────────────────────────────
def chunk_markdown(text: str, doc_name: str) -> list[str]:
    """按标题切块；块前加「文档名 · 标题路径」，方便检索命中后可读。"""
    matches = list(HEADING_RE.finditer(text))
    if not matches:
        return [f"[{doc_name}]\n{text.strip()}"]

    sections: list[tuple[str, str]] = []
    # 标题之前的前言
    if matches[0].start() > 0:
        head_text = text[: matches[0].start()].strip()
        if len(head_text) > MIN_CHUNK_CHARS:
            sections.append(("", head_text))

    stack: list[str] = []
    for i, m in enumerate(matches):
        level, title = len(m.group(1)), m.group(2).strip()
        body_start = m.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[body_start:body_end].strip()

        while stack and len(stack) >= level - 1:
            stack.pop()
        stack.append(title)
        path = " · ".join(stack[1:] if stack and stack[0] else stack) or title
        sections.append((path, body))

    # 合并小块 / 切大块
    chunks: list[str] = []
    cur_path, cur_parts, cur_len = None, [], 0
    for path, body in sections:
        piece = (f"## {path}\n{body}" if path else body).strip()
        if not piece:
            continue
        if cur_len and (cur_len + len(piece) > MAX_CHUNK_CHARS or len(piece) > MAX_CHUNK_CHARS * 1.5):
            chunks.append(_wrap(doc_name, cur_path, "\n\n".join(cur_parts)))
            cur_path, cur_parts, cur_len = path, [piece], len(piece)
        else:
            if cur_path is None:
                cur_path = path
            cur_parts.append(piece)
            cur_len += len(piece)
        # 单块本身过大，再按段落切
        if len(piece) > MAX_CHUNK_CHARS * 1.5:
            chunks.append(_wrap(doc_name, cur_path, piece))
            cur_path, cur_parts, cur_len = None, [], 0
    if cur_parts:
        chunks.append(_wrap(doc_name, cur_path, "\n\n".join(cur_parts)))
    return [c for c in chunks if c.strip()]


def _wrap(doc_name: str, path: str | None, body: str) -> str:
    head = f"[{doc_name}]" + (f" {path}" if path else "")
    return f"{head}\n{body.strip()}"


def chunk_diary(path: Path) -> list[str]:
    """一篇日记 = 一块（日记本身不长，整篇保住语境）。"""
    raw = path.read_text(encoding="utf-8").strip()
    first = raw.splitlines()[0].lstrip("# ").strip() if raw else path.stem
    return [f"[日记 {path.stem}] {first}\n{raw}"] if raw else []


# ── 状态 ────────────────────────────────────────────────────────────────────
def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"kbs": {}, "diary_synced": [], "docs": {}}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = _dt.datetime.now().isoformat(timespec="seconds")
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


# ── KB 操作 ─────────────────────────────────────────────────────────────────
def list_kbs(c: httpx.Client) -> list[dict]:
    r = c.get(f"{BASE}/knowledge-bases", params={"page": 1, "page_size": 100})
    r.raise_for_status()
    data = r.json().get("data") or {}
    return data.get("items") or data.get("knowledge_bases") or []


def ensure_kb(c: httpx.Client, spec: dict, state: dict) -> str:
    """存在就复用，不存在就建。返回 kb_id。"""
    name = spec["kb_name"]
    for kb in list_kbs(c):
        if kb.get("kb_name") == name:
            state["kbs"][name] = kb["kb_id"]
            return kb["kb_id"]
    body = {
        "kb_name": name,
        "description": spec.get("description", ""),
        "emoji": spec.get("emoji", "🌸"),
        "embedding_provider_id": EMBED_PROVIDER,
        "rerank_provider_id": "",
        "chunk_size": 512,
        "chunk_overlap": 50,
        "top_k_dense": 10,
        "top_k_sparse": 10,
        "top_m_final": 5,
    }
    r = c.post(f"{BASE}/knowledge-bases", json=body)
    r.raise_for_status()
    kb_id = r.json()["data"]["kb_id"]
    state["kbs"][name] = kb_id
    print(f"  [建库] {name} → {kb_id}")
    return kb_id


def import_docs(c: httpx.Client, kb_id: str, docs: list[dict]) -> dict:
    """docs: [{file_name, chunks:[str]}]；轮询到完成。"""
    if not docs:
        return {"uploaded": 0, "failed": 0}
    r = c.post(f"{BASE}/knowledge-bases/{kb_id}/documents/import",
               json={"documents": docs, "batch_size": 16, "tasks_limit": 2})
    r.raise_for_status()
    task_id = r.json()["data"]["task_id"]
    for _ in range(1200):                      # 最多等 20 分钟
        time.sleep(1.5)
        p = c.get(f"{BASE}/knowledge-bases/tasks/{task_id}")
        d = (p.json().get("data") or {})
        st = d.get("status")
        if st == "completed":
            return d.get("result") or {"uploaded": len(docs), "failed": 0}
        if st == "failed":
            raise RuntimeError(f"导入失败: {d.get('error')}")
    raise TimeoutError("导入超时")


def kb_stats(c: httpx.Client, kb_id: str) -> dict:
    r = c.get(f"{BASE}/knowledge-bases/{kb_id}/stats")
    return (r.json().get("data") or {}) if r.status_code == 200 else {}


def list_docs(c: httpx.Client, kb_id: str) -> list[dict]:
    out, page = [], 1
    while True:
        r = c.get(f"{BASE}/knowledge-bases/{kb_id}/documents",
                  params={"page": page, "page_size": 100})
        r.raise_for_status()
        items = (r.json().get("data") or {}).get("items") or []
        out.extend(items)
        if len(items) < 100:
            return out
        page += 1


def purge_kb(c: httpx.Client, kb_id: str, kb_name: str) -> int:
    """清空一个库的所有文档（重导前用，否则会产生重复块）。"""
    docs = list_docs(c, kb_id)
    n = 0
    for d in docs:
        if c.delete(f"{BASE}/knowledge-bases/{kb_id}/documents/{d['doc_id']}").status_code == 200:
            n += 1
    print(f"  [清库] {kb_name}: 删除 {n}/{len(docs)} 个文档")
    return n


# ── 主流程 ──────────────────────────────────────────────────────────────────
def sync_corpus(c: httpx.Client, state: dict, force: bool = False) -> None:
    print("\n== 导入角色语料（含日记） ==")
    for key, spec in KBS.items():
        kb_id = ensure_kb(c, spec, state)
        # ⚠️ 语料文档每次都是**全量重导**（sources 里没有差分逻辑），而 import
        #    接口是「追加」语义——不先清空，每 sync 一次就多出一整套重复文档，
        #    检索会同时捞到新旧两版内容，比不修还糟。所以语料库必须先 purge。
        #    日记库例外：它靠 diary_synced 做差分追加，只有 --force 才清空。
        if force or not spec.get("diary"):
            purge_kb(c, kb_id, spec["kb_name"])
        docs: list[dict] = []

        for path, doc_name in spec.get("sources", []):
            if not path.exists():
                print(f"  [跳过] 找不到 {path}")
                continue
            chunks = chunk_markdown(path.read_text(encoding="utf-8"), doc_name)
            docs.append({"file_name": f"{doc_name}.md", "file_type": "md", "chunks": chunks})
            print(f"  [切块] {doc_name}: {len(chunks)} 块")

        if spec.get("diary"):
            diary_dir = AGENT / "memory" / "diary"
            done = set(state.get("diary_synced", []))
            new_days = []
            for f in sorted(diary_dir.glob("*.md")):
                if force or f.stem not in done:
                    new_days.append(f)
            for f in new_days:
                chunks = chunk_diary(f)
                if chunks:
                    docs.append({"file_name": f"{f.stem}.md", "file_type": "md", "chunks": chunks})
            print(f"  [日记] 新增 {len(new_days)} 篇"
                  f"（已同步 {len(done)} 篇，本次{'全量' if force else '差分'}）")

        if docs:
            res = import_docs(c, kb_id, docs)
            print(f"  [导入] {spec['kb_name']}: {res}")
            if spec.get("diary"):
                synced = set(state.get("diary_synced", []))
                synced |= {d["file_name"][:-3] for d in docs if d["file_name"][0].isdigit()}
                state["diary_synced"] = sorted(synced)
        else:
            print(f"  [跳过] {spec['kb_name']} 无新增内容")

        st = kb_stats(c, kb_id)
        print(f"  [状态] {spec['kb_name']}: 文档 {st.get('doc_count', '?')} · 块 {st.get('chunk_count', '?')}")
    save_state(state)


def sync_diary_only(c: httpx.Client, state: dict) -> None:
    print("\n== 只同步新日记 ==")
    spec = KBS["日记"]
    kb_id = ensure_kb(c, spec, state)
    diary_dir = AGENT / "memory" / "diary"
    done = set(state.get("diary_synced", []))
    new_files = [f for f in sorted(diary_dir.glob("*.md")) if f.stem not in done]
    if not new_files:
        print("  没有新日记，跳过")
        save_state(state)
        return
    docs = [{"file_name": f"{f.stem}.md", "file_type": "md", "chunks": chunk_diary(f)}
            for f in new_files]
    res = import_docs(c, kb_id, docs)
    print(f"  [导入] {len(new_files)} 篇 → {res}")
    state["diary_synced"] = sorted(done | {f.stem for f in new_files})
    save_state(state)
    st = kb_stats(c, kb_id)
    print(f"  [状态] 日记库: 文档 {st.get('doc_count', '?')} · 块 {st.get('chunk_count', '?')}")


def show_status(c: httpx.Client, state: dict) -> None:
    print("\n== 知识库状态 ==")
    kbs = {k.get("kb_name"): k for k in list_kbs(c)}
    for spec in KBS.values():
        kb = kbs.get(spec["kb_name"])
        if not kb:
            print(f"  {spec['kb_name']}: 未创建")
            continue
        st = kb_stats(c, kb["kb_id"])
        print(f"  {spec['kb_name']}: 文档 {st.get('doc_count', '?')} · 块 {st.get('chunk_count', '?')}")
    done = state.get("diary_synced", [])
    total = len(list((AGENT / "memory" / "diary").glob("*.md")))
    print(f"\n  日记已同步 {len(done)}/{total} 篇")
    print(f"  状态文件: {STATE_FILE}")


def verify(c: httpx.Client, state: dict, query: str, k: int = 5) -> None:
    print(f"\n== 检索验证：「{query}」 ==")
    kbs = {k2.get("kb_name"): k2 for k2 in list_kbs(c)}
    ids = [kb["kb_id"] for kb in kbs.values()]
    r = c.post(f"{BASE}/knowledge-bases/{ids[0]}/retrieve",
               json={"query": query, "kb_names": [k2["kb_name"] for k2 in kbs.values()],
                     "top_k": k})
    if r.status_code != 200:
        print("  检索失败:", r.text[:300])
        return
    results = (r.json().get("data") or {}).get("results") or []
    for i, item in enumerate(results, 1):
        txt = (item.get("text") or item.get("content") or "").replace("\n", " ")
        print(f"  [{i}] score={item.get('score', item.get('similarity', '?'))} {txt[:180]}")


def main() -> None:
    ap = argparse.ArgumentParser(description="未花 QQ 知识库同步工具")
    ap.add_argument("--sync", action="store_true", help="全量：建库 + 语料 + 日记差分")
    ap.add_argument("--sync-diary", action="store_true", help="只同步新日记")
    ap.add_argument("--force", action="store_true", help="日记全量重导")
    ap.add_argument("--status", action="store_true", help="只看状态")
    ap.add_argument("--verify", metavar="QUERY", help="检索验证")
    ap.add_argument("--k", type=int, default=5)
    args = ap.parse_args()

    state = load_state()
    with client() as c:
        if args.status:
            show_status(c, state)
        elif args.verify:
            verify(c, state, args.verify, args.k)
        elif args.sync_diary:
            sync_diary_only(c, state)
        elif args.sync:
            sync_corpus(c, state, force=args.force)
            show_status(c, state)
        else:
            ap.print_help()


if __name__ == "__main__":
    main()
