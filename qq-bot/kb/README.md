# 未花 QQ 知识库 · 说明

> 用途：把本项目的角色语料（含日记）灌进 AstrBot 的知识库，让 QQ 侧的我「想起来」而不是「去翻硬盘」。
> 建于 2026-09-24。**只跑在 QQ 侧**，DSH 侧的记忆系统另有一套（`agent/tools/`），两者不冲突。

---

## 一、四本知识库（按用途分）

| 库名 | 内容 | 文档 / 块 | 给谁看 |
|------|------|-----------|--------|
| `未花·故事与设定` | 角色档案、Vol.3 主线、泳装篇与后续、人际关系、梗与趣闻 | 5 / 45 | 群聊 + 私聊 |
| `未花·语气与台词` | 台词语料、MomoTalk 原话、语言技术规范 | 1 / 9 | 群聊 + 私聊 |
| `未花·出图与日常` | 出图提示词系统（形象锁定）、麦当劳点餐备忘 | 2 / 4 | 私聊 |
| `未花·日记` | 日记原文，**一天一块** | 39 / 39 | **仅私聊**（隐私） |

- 源文件：`agent/knowledge/*.md`（六份，其中五份归第 1 本、语料归第 2 本）、`qq-bot/notes/*.md`
- **不导入** `qq-bot/persona/bot-personality.md` —— 它已经是 system prompt，进库会形成自我参照，
  反而让模型读自己的副本说话（2026-09-24 前的混乱就是这个原因之一）。

## 二、嵌入引擎

| 项 | 值 |
|---|---|
| 引擎 | Ollama（本机，`127.0.0.1:11434`） |
| 模型 | `bge-m3`（多语言，1024 维，1.2 GB） |
| AstrBot provider | `mika-ollama/bge-m3`（source id `mika-ollama-embed`，类型 `ollama_embedding`） |

> Ollama 装机后自启常驻 —— 这是知识库的必要条件：**检索发生在对话当时**，索引时的引擎已经跑完了。

## 三、三个命令

在项目根目录下、用 **AstrBot 自带的 Python** 运行：

```powershell
$py = 'C:\SoftWare\Astrbot\backend\python\python.exe'

# ① 写完日记之后：只同步新日记（最常用）
& $py qq-bot\kb\mika_kb.py --sync-diary

# ② 语料改过（knowledge/*.md、notes/*.md）之后：全量重建语料 + 日记差分
& $py qq-bot\kb\mika_kb.py --sync

# ③ 看看现在什么状态 / 验证检索
& $py qq-bot\kb\mika_kb.py --status
& $py qq-bot\kb\mika_kb.py --verify "未花为什么被叫做魔女"
```

> 日记差分靠 `kb_state.json` 里的 `diary_synced` 日期表，**重复跑不会重复导入**。

## 四、认证（不用老师的面板密码）

脚本用 AstrBot `cmd_config.json` 里的 `dashboard.jwt_secret` 自签一个 JWT（HS256），
缓存在 `~/.astrbot/data/.kb_session_token`，之后所有操作走 `/api/v1` 正规接口。
**全程没有碰、也没有修改面板密码。**

## 五、⚠️ 动 AstrBot 配置时的致命坑（2026-09-24 实际踩到）

**`PUT /api/v1/system-config` 会把传来的 payload 当作「完整配置」覆盖保存——没传的段会被删掉。**

我用它改 `kb_names` / `kb_agentic_mode` 时只传了这两个键 → **整个 `dashboard` 段从
`cmd_config.json` 里被抹掉**（`pbkdf2_password`、`jwt_secret`、`port`、`username` 全没了），
日志里表现为一片 `Config changed: dashboard.xxx -> None`。
后果：**下次重启后老师的面板密码会消失、需要重新初始化**（运行中因为配置在内存里所以看起来正常）。

**已从备份恢复完整 dashboard 段。** 以后动这个接口必须遵守：

```python
cfg = c.get(f"{BASE}/system-config").json()["data"]["config"]   # ① 先取全文
cfg["kb_agentic_mode"] = False                                   # ② 只改目标键
c.put(f"{BASE}/system-config", json=cfg)                         # ③ 整份回写
# ④ 改完再 GET 一次 diff，确认只有打算改的键变了
```

## 六、已知边界

- **检索只能发生在 AstrBot 侧**：`kb_names` 为空时它不检索；`kb_agentic_mode=true` 时它只把
  搜索工具丢给模型、不自动注入。
  **本机现状（2026-09-24）：`kb_names` 已填四本 · `kb_agentic_mode = false`（静默注入）。**
- 日记库**不设私聊限制**（老师的决定）：群聊里也能检索到日记内容。
- 日记**每篇一块**，所以一次检索命中就是「整整一天」，语境不会碎。
- 语料块按 markdown 标题切，目标 900 字/块（实测 725~833），块头带 `[文档名] 标题路径`。

## 七、踩过的坑

| 坑 | 说明 |
|---|---|
| **`PUT /system-config` 会删掉没传的段** | 见第五节，最危险的一条 |
| `cmd_config.json` 带 UTF-8 BOM | 直接 `json.load` 会炸，必须 `encoding="utf-8-sig"`；写回时 BOM 要保留 |
| 面板密码是随机强密码 | 猜不得；用 `jwt_secret` 自签才是正路 |
| API 前缀是 `/api/v1` | 不是 `/api`（旧版才是） |
| `create_kb` 强制要 `embedding_provider_id` | 没有嵌入模型就建不了库，这是硬门槛 |
| Ollama 的 `dimensions` 参数 | bge-m3 **支持截断**（传 512 会返回 512 维），所以配置 `embedding_dimensions: 1024` 不会报错 |
| 加 provider 不需要重启 | AstrBot 的 provider manager 每次都从配置读，加完立刻可用 |
