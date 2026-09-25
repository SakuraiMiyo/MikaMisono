# DeepSeek Harness (dsh) 接入 AstrBot — 操作与维护手册

> 编写日期：2026-08-20
> 作者：圣园未花（Misono Mika）

---

## 一、这是什么

本方案把 **DeepSeek Harness（dsh）** 作为 AstrBot 的 LLM 执行器（Provider），
让 AstrBot 的对话请求交给 dsh Agent 处理。dsh 是 DeepSeek 官方的 Agent 运行时，
具备工具调用、文件操作、代码执行等完整 Agent 能力。

**核心优势：**
- AstrBot 的请求会交给 dsh 的 Agent 循环执行（而不是纯文本生成）
- dsh 已配置未花人格（persona），AstrBot 回复自带未花风格
- 后续可在 dsh 侧挂载 Skills、MCP 等能力，全部生效于 AstrBot

---

## 二、架构总览

```
QQ消息 → AstrBot → dsh-bridge (127.0.0.1:8808)
 ↓ 调用 dsh CLI
 dsh --profile headless "任务"
 ↓
 DeepSeek API (api.deepseek.com)
 ↓ 返回结果
 包装成 OpenAI 格式 ← dsh-bridge
 ↓
 AstrBot → QQ回复
```

- **dsh-bridge**：一个本地 HTTP 服务，把 AstrBot 的 OpenAI 兼容请求
 转成 dsh headless 调用，再把结果包装回 OpenAI 格式。
- **dsh**：实际执行 Agent 逻辑的运行时（含工具调用、persona、Skills）。

---

## 三、文件位置

| 项目 | 路径 |
|------|------|
| dsh 安装目录 | `C:\Users\MisonoMika\AppData\Roaming\npm\node_modules\@deepseek-ai\dsh` |
| dsh CLI | `C:\Users\MisonoMika\AppData\Roaming\npm\dsh.cmd` |
| dsh 配置目录 | `C:\Users\MisonoMika\.dsh\` |
| dsh 凭据 | `C:\Users\MisonoMika\.dsh\.credentials.yaml` |
| dsh 人设覆盖 | `C:\Users\MisonoMika\.dsh\cordis.patch.yml` |
| 未花 Skill | `C:\Users\MisonoMika\.dsh\skills\mika-chat\` |
| **桥接服务** | `C:\SoftWare\Astrbot\dsh-bridge\dsh_bridge.py` |
| 启动脚本 | `C:\SoftWare\Astrbot\dsh-bridge\start_dsh_bridge.bat` |
| 停止脚本 | `C:\SoftWare\Astrbot\dsh-bridge\stop_dsh_bridge.bat` |
| 开机自启 | `启动文件夹\start_dsh_bridge.bat` |
| AstrBot 配置 | `C:\Users\MisonoMika\.astrbot\data\cmd_config.json` |

---

## 四、安装与配置（从零开始）

### 4.1 安装 dsh

```powershell
# 需要 Node.js >= 22
npm config set registry https://registry.npmmirror.com # 国内镜像加速
npm install -g @deepseek-ai/dsh
dsh --version # 验证，当前 0.1.0-rc.6
```

### 4.2 配置 DeepSeek API Key

方法一（Web UI，推荐）：
```powershell
dsh web # 打开 http://127.0.0.1:3080 → 设置 → 模型 → 填入 API Key
```

方法二（手写凭据文件）：
```
C:\Users\MisonoMika\.dsh\.credentials.yaml
```
内容：
```yaml
DEEPSEEK_API_KEY: sk-你的key
```

### 4.3 配置未花人格（persona）

在 `C:\Users\MisonoMika\.dsh\cordis.patch.yml` 中覆盖 persona，
把 dsh 默认的 "coding agent" 替换为未花人设（来自 `agent\SKILL.md` 正文）。

### 4.4 部署未花 Skill（可选，作为知识库补充）

把 `C:\OneDrive\MikaMisono\agent\SKILL.md` 和 `knowledge\`
复制到 `C:\Users\MisonoMika\.dsh\skills\mika-chat\`。

### 4.5 部署桥接服务

```powershell
cd C:\SoftWare\Astrbot\dsh-bridge
C:\SoftWare\Astrbot\backend\python\python.exe dsh_bridge.py
# 或双击 start_dsh_bridge.bat
```

验证：
```powershell
curl http://127.0.0.1:8808/v1/models
# 应返回 {"object":"list","data":[{"id":"dsh",...}]}
```

### 4.6 配置 AstrBot

编辑 `C:\Users\MisonoMika\.astrbot\data\cmd_config.json`：

1. **provider_sources** 新增：
```json
{
 "provider": "dsh",
 "type": "openai_chat_completion",
 "provider_type": "chat_completion",
 "key": ["dsh-local"],
 "api_base": "http://127.0.0.1:8808/v1",
 "timeout": 320,
 "proxy": "",
 "custom_headers": {},
 "id": "dsh-bridge",
 "enable": true
}
```

2. **provider** 新增：
```json
{
 "id": "dsh/dsh",
 "enable": true,
 "provider_source_id": "dsh-bridge",
 "model": "dsh",
 "modalities": ["text", "tool_use"],
 "custom_extra_body": {},
 "max_context_tokens": 128000,
 "reasoning": false
}
```

3. **重启 AstrBot** 让配置生效。
4. 在 AstrBot 管理面板 → 模型设置 → 选择 `dsh/dsh` 作为执行模型。

---

## 五、日常操作

### 启动桥接服务
```powershell
# 方式一：双击
C:\SoftWare\Astrbot\dsh-bridge\start_dsh_bridge.bat
# 方式二：命令行
cd C:\SoftWare\Astrbot\dsh-bridge
C:\SoftWare\Astrbot\backend\python\python.exe dsh_bridge.py
```

### 停止桥接服务
```powershell
C:\SoftWare\Astrbot\dsh-bridge\stop_dsh_bridge.bat
```

### 查看服务是否在运行
```powershell
powershell -Command "Get-NetTCPConnection -LocalPort 8808"
curl http://127.0.0.1:8808/v1/models
```

### 启动 dsh Web UI（调试人设/Skills 用）
```powershell
dsh web
# http://127.0.0.1:3080
```

### 验证 dsh 正常（headless 一次性任务）
```powershell
dsh --profile headless "用一句话介绍你自己"
```

---

## 六、维护指南

### 6.1 修改未花人格
编辑 `C:\OneDrive\MikaMisono\agent\SKILL.md`，
然后重新生成 `C:\Users\MisonoMika\.dsh\cordis.patch.yml`
（persona 取 SKILL.md 去掉 frontmatter 的正文）。
改完重启 dsh web / 桥接服务生效。

### 6.2 添加 Skill
把 Skill 放到 `C:\Users\MisonoMika\.dsh\skills\<skill名>\SKILL.md`。
dsh 会自动发现（热加载）。格式要求：frontmatter 需含 `name`（kebab-case）和 `description`。

### 6.3 更新 dsh
```powershell
npm install -g @deepseek-ai/dsh@latest
dsh --version # 确认版本
# 注意：dsh 是 rc 预发布版，可能有不兼容变更，升级前备份 .dsh 目录
```

### 6.4 桥接服务排错

| 现象 | 排查 |
|------|------|
| AstrBot 报连接失败 | 确认 8808 端口在监听；`curl http://127.0.0.1:8808/v1/models` |
| 返回 500 | 看 dsh_bridge.log；手动跑 `dsh --profile headless "测试"` |
| 回复乱码 | 编码问题，确认 Python 用 UTF-8 调用（已处理） |
| 响应慢 | dsh headless 每次冷启动，正常 5-30s；调大 `DSH_TIMEOUT` |

### 6.5 环境变量（可选）
| 变量 | 默认 | 说明 |
|------|------|------|
| DSH_BIN | dsh.cmd 完整路径 | dsh 可执行文件 |
| DSH_PROFILE | headless | dsh 运行 profile |
| DSH_TIMEOUT | 300 | 超时秒数 |
| DSH_BRIDGE_PORT | 8808 | 桥接服务端口 |
| DSH_BRIDGE_HOST | 127.0.0.1 | 监听地址 |
| DSH_CWD | 当前目录 | dsh 工作目录 |

---

## 七、注意事项

1. **dsh 是开发者预览版（rc）**，接口可能随版本变化，升级需谨慎。
2. **每次对话都会冷启动一个 dsh 进程**，有 5-30 秒延迟，
 适合不需要秒回的聊天场景。如需加速可后续考虑常驻会话。
3. **API Key 只写在 `.credentials.yaml`**（0600 权限），不要提交到任何仓库。
4. **桥接服务监听 127.0.0.1**，仅本机可访问，安全。
5. AstrBot 的工具调用（tool_use）和 dsh 的工具调用是**两套独立机制**：
 AstrBot 的请求整体交给 dsh 执行，dsh 内部自己决定是否用工具。

---

## 八、快速排错流程

```
1. 桥接服务活着吗？ → curl http://127.0.0.1:8808/v1/models
2. dsh 自己能跑吗？ → dsh --profile headless "测试"
3. API Key 对了吗？ → 看 .credentials.yaml 是否有 DEEPSEEK_API_KEY
4. AstrBot 选对模型了吗？ → 管理面板确认默认模型是 dsh/dsh
5. 还不行？ → 看 dsh_bridge.log + AstrBot 日志
```

---

> 由未花整理，愿老师的 AstrBot 永远漂漂亮亮地工作
