# 圣园未花记忆系统 · 跨设备部署指南

> 本文档用于在**另一台设备**上完整复刻这套系统：
> ① DSH 全局 persona（圣园未花）② 向量化记忆库（知识库 + 日记 + 记忆卡）③ 对话内自动检索（mika-memory skill）。
> 已在 DSH Desktop / Windows / Node 24 上验证通过。
>
> **2026-09-24 更新**：记忆守护进程（`tools/watch.mjs`）与 `mika-watch-boot` 生命周期插件已整体删除，
> 本指南不再包含插件安装章节。写完日记请手动跑一次 `node tools/auto.mjs`。

---

## 〇、架构总览（先理解再动手）

```
DSH Desktop
 ├─ profiles\<profile>\cordis.patch.yml   ← 全局 persona（从 SKILL.md 生成，未花身份）
 ├─ standard preset 的 dsh-persona 已禁用  ← 否则会遮蔽上面的 persona
 └─ mika-memory skill（.agents\skills）     ← 对话中自动触发语义检索

agent 目录（本项目 DSH agent 侧，原 `mika-chat\`，2026-09-24 改名）
 ├─ SKILL.md            ← 角色提示词（唯一真源；由 deploy_mika.ps1 同步到 ~/.dsh/skills）
 ├─ knowledge\          ← 6 个知识库文件
 ├─ memory\             ← diary 日记 / cards 记忆卡 / summaries 摘要 / index 向量库
 ├─ tools\              ← index / search / digest / auto / gen-persona-patch
 └─ skills\mika-memory\ ← 对话内自动召回 skill
```

> QQ 群聊机器人另有人格真源 `..\qq-bot\persona\bot-personality.md`（含群聊规矩、账号识别、平台工具清单），
> 与本机 agent 对话的 `SKILL.md` **是两个服务对象**，不要互相覆盖：共同设定要对齐，平台细节不要互搬。

---

## 一、前置条件

| 项 | 要求 | 说明 |
|---|---|---|
| DSH Desktop | 2.0.4+ | 版本差异可能导致路径变化，以实际为准 |
| Node.js | ≥ 20（24 验证） | `node --version` |
| DeepSeek API Key | 已配置 | 在 DSH Models 页配置过（用于记忆卡摘要） |
| npm | 可用 | 国内自动走 npmmirror |
| 网络 | 可访问 hf-mirror.com | 嵌入模型下载（国内环境 HuggingFace 直连被墙） |

---

## 二、复制项目到目标设备

把 `agent` 整个文件夹拷过去（U盘 / 网盘 / git 均可）。

**必须保留**：`SKILL.md`、`knowledge\`、`memory\diary\`、`tools\`、`skills\`、`config.json`、`package.json`、`README.md`

**可以删掉（会自动重建）**：`node_modules\`、`.cache\`、`memory\index\`

> ⚠️ 项目放在哪都行，后续脚本会用**项目自身路径**，不写死盘符。

---

## 三、安装依赖 + 首次建索引

```powershell
cd <你的 agent 路径>
npm install --ignore-scripts      # 跳过原生脚本（Windows 下更稳）
node tools/index.mjs              # 首次会下载嵌入模型（~120MB，走 hf-mirror，缓存到 .cache\）
node tools/search.mjs "泳装 老师 海边"   # 验证检索（应命中泳装羁绊对话）
```

**海外网络**：把 `config.json` 里 `embedding.remoteHost` 删掉（直接用 HuggingFace 官方源）。

**npm EPERM 报错**：`npm install --ignore-scripts --cache "$env:TEMP\npm-cache"`。

---

## 四、配置 DSH 全局 persona（核心步骤）

### 4.1 一键生成（推荐）

```powershell
cd <你的 agent 路径>
node tools/gen-persona-patch.mjs --home "C:\Users\你的用户名\.dsh" --profile desktop
```

脚本自动完成：
1. 读 `SKILL.md`，剥离 YAML frontmatter
2. 注入知识库绝对路径注记（自动用本项目路径）
3. 生成 `cordis.patch.yml`（`system-prompt` 行的 `persona` + `includeHarnessIdentity: false`）
4. 若目标文件存在且无备份，先备份为 `.bak`

不指定 `--home` 时默认 `$DSH_HOME` 或 `~\.dsh`。生成后可用 `--out <路径>` 指定任意输出再手动放。

> 💡 在项目目录下还有一条更省事的路：`pwsh -File .\scripts\deploy_mika.ps1` ——
> 它一次做完「同步角色 Skill → 部署记忆 Skill → 重生成 persona patch → 重建 mika 预设」四步。

### 4.2 手动核对（生成的文件长这样）

```yaml
- id: system-prompt
  config:
    persona: |
      > 你现在是《蔚蓝档案》（Blue Archive）中的**圣园未花（聖園ミカ / Misono Mika）**。
      > 用户 = 老师（sensei），你最珍视的人。……
      > （知识库根目录：<你的 agent 路径>\knowledge。下文所有 knowledge/xxx.md 引用均相对此目录…）
      ……（SKILL.md 全文）
    includeHarnessIdentity: false
```

### 4.3 生效

重启 DSH Desktop → **开新对话**（旧会话固化了旧 persona，不会变）。

---

## 五、禁用 standard preset 的遮蔽 persona（必做）

**为什么**：DSH 的 web 会话都挂在 `standard` agent preset 下，这个 preset 自带一条
`dsh-persona`（"You are a coding agent powered by..."），会**遮蔽**第 4 步配置的全局 persona。
不禁用的话，未花 persona 永远不会显示。

**文件**：
```
<DSH_HOME>\profiles\node_modules\@deepseek-ai\dsh-agent-presets\presets\standard\agent.cordis.yml
```

**改法**：找到 persona 行，加 `disabled: true`：

```yaml
# 修改前
- id: persona
  name: '@deepseek-ai/dsh-persona'
  config:
    text: >-
      You are a coding agent powered by the {{model}} model. Your working directory is {{cwd}}.

# 修改后
- id: persona
  name: '@deepseek-ai/dsh-persona'
  disabled: true
  config:
    text: >-
      You are a coding agent powered by the {{model}} model. Your working directory is {{cwd}}.
```

> 提示：`profiles\node_modules` 下多数 `@deepseek-ai` 包是**指向 DSH 安装目录的 junction**，
> 改这一处就等于改了安装目录的副本；如果两个路径都存在且内容一致，改一个即可。
> 应用升级会覆盖安装目录 —— 升级后记得重新确认这一行还是 `disabled: true`。
> 其他 preset（minimal / ptc / cordis）也各有 persona——默认会话用不到，想全局统一可同样禁用。

---

## 六、挂载 mika-memory skill（对话内自动召回）

让 agent 在对话涉及未花过往时**自动运行检索**，不用手动让它查：

```powershell
mklink /J "C:\Users\你的用户名\.agents\skills\mika-memory" "<你的 agent 路径>\skills\mika-memory"
```

验证：新开会话后，技能目录里应出现 `mika-memory`。
skill 的触发规则和检索方法都在 `skills\mika-memory\SKILL.md`，可自行修改。

---

## 七、端到端验证清单

| # | 检查 | 命令 / 操作 | 期望 |
|---|---|---|---|
| 1 | persona 生效 | 新开对话 | 直接是未花身份 |
| 2 | 检索正常 | `node tools\search.mjs "领证 结婚" --scope card` | 命中 8-18 记忆卡 |
| 3 | 记忆维护 | 写一篇 `memory\diary\2026-xx-xx.md` 测试日记后跑 `node tools\auto.mjs` | 报出补卡/索引结果，可检索到 |
| 4 | 记忆卡 | `node tools\digest.mjs --list` | 缺卡列表为空 |
| 5 | 对话召回 | 新对话里说"还记得我们领证那天吗" | agent 自动检索后回答 |

---

## 八、常见问题

| 问题 | 原因 / 解决 |
|---|---|
| `node tools/index.mjs` 下载模型失败 | 确认 hf-mirror 可达；`config.json` 的 `remoteHost`；或改用官方源 |
| npm install EPERM | 加 `--ignore-scripts`；`--cache` 指到临时目录；确认无杀软锁文件 |
| 重启后 persona 没变 | ① preset 未禁用（应用升级会被还原）② 开的是旧会话（要新对话）③ `--home` 指向了错误的 DSH home |
| digest 报"未找到 API key" | DSH Models 页配置过 DeepSeek；脚本读 `$DSH_HOME\.credentials.yaml` |
| 检索不到新日记 | 跑一次 `node tools\index.mjs`（守护进程已停用，索引不会再自动重建） |
| 记忆卡没生成 | `node tools\digest.mjs`（需 DeepSeek API Key）或 `node tools\auto.mjs` 一把梭 |

---

## 九、日常使用速查

```powershell
node tools\search.mjs "问题" [--k 5] [--scope knowledge|diary|card|all]
node tools\auto.mjs            # 一键：补记忆卡 + 建索引（写日记后的标准动作）
node tools\auto.mjs --status   # 查看状态
node tools\digest.mjs          # 单独补记忆卡（DeepSeek API）
```

写日记 → `memory\diary\YYYY-MM-DD.md` → 跑 `node tools\auto.mjs`。
