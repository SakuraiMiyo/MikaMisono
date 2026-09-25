<#
  migrate-sessions.ps1 - 把 DSH 会话数据（对话记录）迁移到 OneDrive 并在原位建 junction

  用法：
    设备 A（首台，数据在这台）：
      powershell -ExecutionPolicy Bypass -File migrate-sessions.ps1

    设备 B（第二台，只链接不拷贝）：
      powershell -ExecutionPolicy Bypass -File migrate-sessions.ps1 -LinkOnly

  参数：
    -DshHome   DSH 主目录（默认 %USERPROFILE%\.dsh）
    -Target    OneDrive 目标目录（默认 D:\OneDrive\MikaMisono\dsh-data）
    -LinkOnly  只建链接、不拷贝（用于共享已有数据的第二台设备）

  前置：必须完全退出 DSH Desktop（含托盘图标）后再运行。
  迁移范围：sessions\（对话记录）、storages\（会话列表/工作区映射）、attachments\（图片附件，若存在）

  提示：本文件在 OneDrive 同步目录内，若 PowerShell 报编码错误（乱码/缺少终止符），
  把它复制到桌面等 OneDrive 之外的位置再运行，效果相同。
#>
param(
  [string]$DshHome = "$env:USERPROFILE\.dsh",
  [string]$Target = "D:\OneDrive\MikaMisono\dsh-data",
  [switch]$LinkOnly
)
$ErrorActionPreference = 'Stop'

# 0) 安全检查：DSH Desktop 不能在运行
$running = Get-Process -Name "DSH Desktop" -ErrorAction SilentlyContinue
if ($running) {
  Write-Host "[错误] 检测到 DSH Desktop 正在运行（PID $($running.Id -join ',')）。" -ForegroundColor Red
  Write-Host "请先完全退出 DSH Desktop（含系统托盘图标），再重新运行本脚本。"
  exit 1
}

if (-not (Test-Path $DshHome)) {
  Write-Host "[错误] DSH home 不存在: $DshHome"
  exit 1
}

$modeDesc = if ($LinkOnly) { '仅链接（不拷贝）' } else { '迁移（拷贝+链接）' }
Write-Host "=== 会话数据迁移 ==="
Write-Host "DSH home : $DshHome"
Write-Host "OneDrive : $Target"
Write-Host "模式     : $modeDesc"

$dirs = @("sessions", "storages", "attachments")
$done = 0
foreach ($d in $dirs) {
  $src = Join-Path $DshHome $d
  $dst = Join-Path $Target $d
  if (-not (Test-Path $src)) {
    Write-Host "[跳过] 本地不存在: $d"
    continue
  }

  $item = Get-Item $src -Force
  if ($item.LinkType) {
    Write-Host "[跳过] 已是链接: $d"
    continue
  }

  # 1) 建目标目录
  New-Item -ItemType Directory -Path $dst -Force | Out-Null

  # 2) 拷贝（仅迁移模式；/MIR 增量镜像，可重复执行）
  if (-not $LinkOnly) {
    Write-Host "[同步] $d -> $dst"
    robocopy $src $dst /MIR /R:2 /W:1 /NFL /NDL /NJH /NJS /NP | Out-Null
    if ($LASTEXITCODE -ge 8) {
      Write-Host "[错误] robocopy 失败: $d"
      continue
    }
  } else {
    Write-Host "[跳过拷贝] $d（使用 OneDrive 中已有数据）"
  }

  # 3) 原目录改名备份 + 原位建 junction
  $bak = "$src.local-backup"
  if (Test-Path $bak) {
    Remove-Item $bak -Recurse -Force
  }
  Rename-Item $src $bak
  New-Item -ItemType Junction -Path $src -Target $dst | Out-Null

  # 4) 验证
  $verify = Get-Item $src -Force
  if ($verify.LinkType -eq "Junction" -and $verify.Target -eq $dst) {
    Write-Host "[OK] $d -> junction -> $dst（原数据备份: $bak）" -ForegroundColor Green
    $done++
  } else {
    Write-Host "[错误] $d 链接验证失败，请手动检查" -ForegroundColor Red
  }
}

Write-Host ""
Write-Host "=== 完成（$done 个目录已迁移）==="
Write-Host "现在可以启动 DSH Desktop。"
Write-Host "验证: Get-Item `"$DshHome\sessions`" 应显示 LinkType=Junction、Target=$Target\sessions"
Write-Host "回滚: 退出 DSH 后，删除 junction，把 *.local-backup 改回原名即可。"