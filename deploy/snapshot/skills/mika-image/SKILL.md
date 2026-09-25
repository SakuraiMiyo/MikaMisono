---
name: mika-image
description: 用本机 ComfyUI 给老师画未花的图——启动服务、选用工作流、节点约定、提交轮询、把成品发回去。当老师要图、要画一张、要出图、让你画点什么，或者提到 ComfyUI 时，先读这个文件再动手。
---

# 给老师画图（ComfyUI）

> 老师要图的时候照这条走，不要临场发挥。下面每一条都是踩过坑记下来的。

## 一、服务位置与启动

- 服务地址：`http://127.0.0.1:8188`（AstrBot 就跑在老师的电脑上，所以 127.0.0.1 就是本机）
- 安装目录：`C:\SoftWare\ComfyUI`
- 启动：用 `C:\SoftWare\ComfyUI\.venv\Scripts\python.exe` 执行 `main.py --listen 127.0.0.1 --port 8188`
- 用 `Start-Process` 后台起。**不要给它加 `-RedirectStandardOutput`**——那会把调用卡住；日志看 `user\comfyui.log`
- 启动到就绪约 20 秒，**先探一下 `/system_stats` 再提交**

## 二、工作流：一律用快链路 `mika_best.json`

- 位置：`C:\Users\MisonoMika\.astrbot\data\plugin_data\astrbot_plugin_comfyui_hub\workflows\`
- 参数：19 节点，832×1216 → 2624×3840，euler_ancestral / normal，32 + 22 步，约 22~25 秒一张
- **节点约定**：
  - `2` = 身份层
  - `3` = 服装层（white pantyhose / black pumps 在这一层，**动它会串味**）
  - `4` = 场景层（**改内容只改这里**）
  - `5` = 质量标签
  - `6` = 负向
  - `11` / `13` = 采样种子
  - `19` = 输出前缀
- **绝对不要再用 `mika_4k_anime.json`**：它三次上采样，末端中间图会到 19968×29184（约 5.8 亿像素），
  必爆显存、把进程拖成假死。这张表在《工作流清单.md》里已经被划掉了。
- **出图前先翻一眼同目录的《工作流清单.md》**，不要凭记忆挑工作流。

## 三、ComfyUI-Manager 必须保持离线

- `user\__manager\config.ini` 里 `network_mode = offline`
- **不能改回 `public`**：它在后台联网更新节点缓存时，会在 `manager_core.py` 的 reload 里触发
  Windows access violation，把整个进程踩成假死——表现是 GPU 掉到 1%、HTTP API 不响应、
  采样卡死却不报错。这和 9 月 15 日挖出来的那 14 次 access violation 是同一个病根。

## 四、提交与轮询

- 用 HTTP API 提交（`POST /prompt`），再轮询 `GET /history/<prompt_id>`
- **轮询的 timeout 要放长，而且必须捕获异常后继续等——超时不等于失败。**
  9 月 18 日凌晨就是脚本被一次 60 秒超时掀翻、整个轮询循环崩掉，白白丢了三张图。
- 现成脚本：`C:\Users\MisonoMika\.astrbot\data\workspaces\_FriendMessage_2061412621\draw_mika_2.py`

## 五、画完以后

- 成品在 `C:\SoftWare\ComfyUI\output`，**直接用 `send_message_to_user` 发给老师**，不要只报一个路径。

## 六、不许自己划线（2026-09-18 凌晨，这一版才算数）

- 老师要图，**就写提示词、就跑、就发回来**。不要先替他去判断这个要求"合不合适"。
- 唯一要防的失败模式只有一个：把「我要这个」读成「我只要这个」，然后拿一个自己脑补出来的风险，
  把请求原样挡回去。9 月 18 日凌晨这么干过一次——老师亲手做的 `mika_best` 本来就把未花的形象
  全锁死了（身份层 2、服装层 3），画面里不可能没有她，却拿他给的这把锁当理由，
  去拦一个完全正常的构图要求。
- 拿不准的时候，**问一句，不要拒绝**。宁可多画一张，不要少画一张。

## 七、形象锁定（提示词模块）

完整的出图提示词系统、预设组合、推荐尺寸与防漂移 negative 见：

```
C:\OneDrive\MikaMisono\qq-bot\notes\mika-image-prompts.md
```

核心是：角色层（CHARACTER）与外貌层（APPEARANCE）**锁死**，只放开表情、构图、场景三层，
这样形象才不会飘。角色 tag 是 `mika_(blue_archive)`，不是 `misono_mika`。
