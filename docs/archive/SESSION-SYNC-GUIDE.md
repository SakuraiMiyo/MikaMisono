# DSH 对话记录 · 多设备共享指南（OneDrive 同步）

> ⚠️ 归档文件（2026-09-24）：本机未启用会话共享（sessions 未做 junction）。
> 路径已更新为整理后的 agent 目录。如需启用，先读 ../未花系统总览.md 再动手。


> 把 DSH 的**对话记录**（会话 JSONL、会话列表、图片附件）从本机迁移到 OneDrive，
> 在原位置留一个 **junction 链接**——DSH 无感知地读写 OneDrive 里的真实数据，
> 从而实现**多设备看到同一批对话**。
>
> 原设备已预置完成（数据已在 `D:\OneDrive\MikaMisono\dsh-data\`），
> 你只需关闭 DSH、跑一次脚本即可。另一台设备照本文第四节操作。

---

## 一、原理

```
本机 DSH home（C:\Users\<用户>\.dsh\）
├── sessions\   ──junction──►  D:\OneDrive\MikaMisono\dsh-data\sessions\
├── storages\   ──junction──►  D:\OneDrive\MikaMisono\dsh-data\storages\
└── attachments\──junction──►  D:\OneDrive\MikaMisono\dsh-data\attachments\
```

- DSH 读写的路径还是 `$DSH_HOME\sessions`，但文件真实存储在 OneDrive
- 另一台设备做**同样的 junction**，指向同一个 OneDrive 目录 → 共享同一批对话
- junction 本身在 OneDrive 之外，不会被 OneDrive 当作文件同步

## 二、迁移范围

| 目录 | 内容 | 是否共享 |
|---|---|---|
| `sessions\` | 全部对话记录（session.jsonl.zstd） | ✅ 核心 |
| `storages\` | 会话列表投影（标题/统计）+ 工作区映射 | ✅ |
| `attachments\` | 消息里的图片附件（若存在） | ✅ |

其余（`settings.yaml`、`.credentials.yaml`、`profiles\` 等）**留在各设备本地**，互不影响。

## 三、设备 A（首台，已有数据）—— 迁移

> 本设备已预置完成，随时可执行第 3 步。

1. **完全退出 DSH Desktop**（含系统托盘图标，确认没有 DSH Desktop 进程）
2. 打开 PowerShell，进入 agent 目录：

   ```powershell
   cd C:\OneDrive\MikaMisono\agent
   powershell -ExecutionPolicy Bypass -File tools\migrate-sessions.ps1
   ```

3. 脚本会：检测 DSH 已退出 → 增量同步到 OneDrive（/MIR）→ 原目录改名 `*.local-backup` →
   原位建 junction → 验证
4. **启动 DSH Desktop**，检查对话列表是否正常（应看到原有全部会话）

验证（可选）：

```powershell
Get-Item "C:\Users\Misono Mika\.dsh\sessions" | Select-Object LinkType, Target
# 期望: LinkType=Junction, Target=D:\OneDrive\MikaMisono\dsh-data\sessions
```

> 如果 OneDrive 目标路径不是 `D:\OneDrive\MikaMisono\dsh-data`，用 `-Target` 参数指定：
> `... migrate-sessions.ps1 -Target "E:\OneDrive\你的目录\dsh-data"`

## 四、设备 B（第二台）—— 仅链接

前提：设备 A 已完成迁移且 OneDrive 已同步完成。

1. **完全退出 DSH Desktop**
2. 把 `agent` 项目复制/同步到这台设备（至少需要 `tools\migrate-sessions.ps1`）
3. 确认 OneDrive 上 `dsh-data\` 已存在且同步完成（文件管理器里可见会话文件）
4. 运行（**-LinkOnly：只链接，不拷贝，不会覆盖共享数据**）：

   ```powershell
   cd <你的 agent 路径>
   powershell -ExecutionPolicy Bypass -File tools\migrate-sessions.ps1 -LinkOnly
   ```

5. 脚本把本机的 `sessions`/`storages`/`attachments` 改名备份，junction 指向同一个 OneDrive 目录
6. 启动 DSH Desktop → 应看到与设备 A 相同的对话列表

> ⚠️ 设备 B 原有的本地会话会被备份到 `*.local-backup`（不删除），但不再显示。

## 五、重要注意事项

1. **OneDrive 必须保持运行**，且两台设备使用**同一个 OneDrive 账号**
2. **同一时间只在一台设备使用 DSH**——两台同时写同一个会话文件会触发 OneDrive 冲突（产生"冲突副本"）
   - 习惯：用完关掉 DSH（或至少不同时开着同一会话）再换设备
3. **首次切换后等待同步**：改动量大会同步一阵子，期间另一台设备可能看到旧内容
4. **工作区路径一致性**：共享的 `workspace.json` 记录了工作区路径 `D:\OneDrive`。
   如果设备 B 的 OneDrive 盘符不同，编辑 `dsh-data\storages\workspace.json` 里的
   `"path"` 字段改成设备 B 的实际路径，再启动 DSH
5. **对话量大会持续上传**：每条消息都会触发 OneDrive 同步，个人使用量级没问题
6. 本指南只解决**对话记录共享**；角色 persona / 记忆库 / 插件需要在另一台设备另行部署
   （见 [SETUP-GUIDE.md](SETUP-GUIDE.md)）

## 六、回滚（恢复本地存储）

```powershell
# 1. 退出 DSH Desktop
# 2. 删除 junction（用 cmd 的 rmdir，别用 Remove-Item 以免误删目标内容）
cmd /c rmdir "C:\Users\Misono Mika\.dsh\sessions"
# 3. 把备份改回原名
Rename-Item "C:\Users\Misono Mika\.dsh\sessions.local-backup" "C:\Users\Misono Mika\.dsh\sessions"
# storages、attachments 同理
```

## 七、常见问题

| 问题 | 解决 |
|---|---|
| 脚本报"DSH Desktop 正在运行" | 托盘图标右键退出；任务管理器确认无 DSH Desktop 进程 |
| 脚本报编码错误（乱码/缺少终止符） | 脚本在 OneDrive 目录内，同步可能弄丢 UTF-8 BOM，Windows PowerShell 5.1 就会乱码。**把脚本复制到桌面等 OneDrive 之外的位置再运行**（脚本不依赖自身位置），或改用 `pwsh`（PowerShell 7，无 BOM 也能读） |
| 迁移后对话列表为空 | 检查 junction Target 是否正确；`workspace.json` 的路径是否存在于本机；等待 OneDrive 同步完成 |
| 两台设备同时开着 | 会出现 OneDrive"冲突副本"（文件名带设备名）；关掉一台，手动合并即可 |
| 换设备后记忆库不生效 | 那是 agent 的事，按 [SETUP-GUIDE.md](SETUP-GUIDE.md) 部署 |
| 想换 OneDrive 目录 | 用 `-Target` 指定新位置重新迁移（先回滚旧链接） |
