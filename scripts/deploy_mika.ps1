# deploy_mika.ps1 — 未花系统部署 / 更新脚本（本机 dsh）
#
# 功能（全部幂等、带备份）：
#   1. 同步角色扮演 Skill                  → <dshHome>\skills\mika-chat        （按需注入）
#      源目录：<项目>\agent\（2026-09-24 由 mika-chat\ 改名，部署名仍是 mika-chat）
#   2. 部署 mika-memory 记忆检索 Skill  → <agentsHome>\skills\mika-memory   （~/.agents）
#   3. 生成全局 persona patch           → <dshHome>\profiles\desktop\cordis.patch.yml
#      （用项目自带 tools\gen-persona-patch.mjs，persona 取 SKILL.md 正文，entry: system-prompt）
#   4. 生成 mika 预设（整场未花）       → <dshHome>\.agent-presets\mika
#
# 用法（pwsh 7；脚本需以 UTF-8 BOM 保存以便 Windows PowerShell 解析中文）：
#   .\scripts\deploy_mika.ps1                    # 全量部署
#   .\scripts\deploy_mika.ps1 -NoSkill -NoMemory -NoPreset   # 只重新生成 persona patch
#   .\scripts\deploy_mika.ps1 -Prune             # Skill 用镜像同步（慎用，见手册）
#   .\scripts\deploy_mika.ps1 -Node "C:\SoftWare\Node\node.exe"   # 指定 node
#
# 说明：
#   - 默认增量同步（robocopy /E），不会删除部署端运行数据；-Prune 才做镜像。
#   - persona patch 对「新会话」生效；改完 SKILL.md 重跑本脚本即可。

[CmdletBinding()]
param(
    [string]$ProjectDir = '',
    [string]$DshHome = $(if ($env:DSH_HOME) { $env:DSH_HOME } else { Join-Path $env:USERPROFILE '.dsh' }),
    [string]$AgentsHome = $(if ($env:DSH_AGENTS_HOME) { $env:DSH_AGENTS_HOME } else { Join-Path $env:USERPROFILE '.agents' }),
    [string]$Node = 'node',
    [switch]$NoSkill,
    [switch]$NoMemory,
    [switch]$NoPersona,
    [switch]$NoPreset,
    [switch]$Prune,
    [switch]$NoBackup
)

if (-not $ProjectDir) { $ProjectDir = Split-Path -Parent $PSScriptRoot }

$ErrorActionPreference = 'Stop'

function Write-Step([string]$msg) { Write-Host "==> $msg" -ForegroundColor Cyan }
function Write-Ok([string]$msg)   { Write-Host "    $msg" -ForegroundColor Green }

$skillSrc   = Join-Path $ProjectDir 'agent'
$skillFile  = Join-Path $skillSrc 'SKILL.md'
$skillName  = 'mika-chat'
$skillDst   = Join-Path $DshHome "skills\$skillName"
$memorySrc  = Join-Path $skillSrc 'skills\mika-memory'
$memoryDst  = Join-Path $AgentsHome 'skills\mika-memory'
$presetDir  = Join-Path $DshHome '.agent-presets\mika'
$template   = Join-Path $PSScriptRoot 'templates\mika.agent.cordis.yml'
$genTool    = Join-Path $skillSrc 'tools\gen-persona-patch.mjs'
$profilePatch = Join-Path $DshHome 'profiles\desktop\cordis.patch.yml'

# ── 前置检查 ────────────────────────────────────────────────────────────────
foreach ($p in @($ProjectDir, $skillSrc, $skillFile, $template)) {
    if (-not (Test-Path -LiteralPath $p)) { throw "缺少必要路径: $p" }
}

# ── 1) 同步角色 Skill（源：项目内 agent\，部署名：mika-chat） ──────────────
if (-not $NoSkill) {
    Write-Step "同步角色 Skill（agent → $skillName）"
    if (-not $NoBackup -and (Test-Path -LiteralPath $skillDst)) {
        $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
        $bak = Join-Path $DshHome "backups\$skillName-$stamp"
        New-Item -ItemType Directory -Force -Path $bak | Out-Null
        robocopy $skillDst $bak /E /NFL /NDL /NJH /NJS /NP /R:1 /W:1 | Out-Null
        if ($LASTEXITCODE -ge 8) { throw "备份失败 (robocopy $LASTEXITCODE)" }
        $LASTEXITCODE = 0
        Write-Ok "已备份旧 Skill 到 $bak"
    }
    $mir = if ($Prune) { '/MIR' } else { '/E' }
    robocopy $skillSrc $skillDst $mir /XD node_modules .cache memory tools .git /XF package.json package-lock.json config.json *.ps1 *.log *.pid /NFL /NDL /NJH /NJS /NP /R:1 /W:1 | Out-Null
    if ($LASTEXITCODE -ge 8) { throw "Skill 同步失败 (robocopy $LASTEXITCODE)" }
    $LASTEXITCODE = 0
    Write-Ok "Skill -> $skillDst"
}

# ── 2) 部署 mika-memory 检索 Skill ──────────────────────────────────────────
if (-not $NoMemory) {
    Write-Step '部署 mika-memory 记忆检索 Skill'
    if (-not (Test-Path -LiteralPath $memorySrc)) { throw "缺少 mika-memory 源: $memorySrc" }
    New-Item -ItemType Directory -Force -Path $memoryDst | Out-Null
    robocopy $memorySrc $memoryDst /E /NFL /NDL /NJH /NJS /NP /R:1 /W:1 | Out-Null
    if ($LASTEXITCODE -ge 8) { throw "mika-memory 部署失败 (robocopy $LASTEXITCODE)" }
    $LASTEXITCODE = 0
    Write-Ok "Memory skill -> $memoryDst"
}

# ── 3) 生成全局 persona patch ───────────────────────────────────────────────
if (-not $NoPersona) {
    Write-Step '生成全局 persona patch'
    if (-not (Test-Path -LiteralPath $genTool)) { throw "缺少 persona 生成工具: $genTool" }
    & $Node $genTool --home $DshHome --profile desktop
    if ($LASTEXITCODE -ne 0) { throw "gen-persona-patch 失败 (exit $LASTEXITCODE)" }
    $LASTEXITCODE = 0
    Write-Ok "Persona patch -> $profilePatch（新会话生效）"
}

# ── 4) 生成 mika 预设 ───────────────────────────────────────────────────────
if (-not $NoPreset) {
    Write-Step '生成 mika 预设'
    $lines = Get-Content -LiteralPath $skillFile -Encoding UTF8
    $inFm = $false
    $body = New-Object System.Collections.Generic.List[string]
    foreach ($ln in $lines) {
        if ($ln.Trim() -eq '---') {
            if (-not $inFm) { $inFm = $true; continue }
            else { $inFm = $false; continue }
        }
        if (-not $inFm) { $body.Add($ln) }
    }
    if ($body.Count -eq 0) { throw "SKILL.md 正文为空，无法生成 persona" }
    $skillBody = $body -join [Environment]::NewLine

    $header = 'You are a coding agent powered by the {{model}} model, running on the DeepSeek Harness. Your working directory is {{cwd}}. You are also the persona described below — it is your identity in every reply.'
    $persona = $header + [Environment]::NewLine + [Environment]::NewLine + $skillBody
    $indented = ($persona -split [Environment]::NewLine | ForEach-Object { '      ' + $_ }) -join [Environment]::NewLine

    $tpl = Get-Content -LiteralPath $template -Raw -Encoding UTF8
    # 只替换「独立占位行」，避免模板注释里再次出现同名文本时被误替换导致 YAML 损坏
    $placeholderRe = '(?m)^[ \t]*__PERSONA__[ \t]*\r?\n'
    if (-not [regex]::IsMatch($tpl, $placeholderRe)) { throw '模板缺少独立的 __PERSONA__ 占位行' }
    $comp = [regex]::Replace($tpl, $placeholderRe, $indented + [Environment]::NewLine)
    New-Item -ItemType Directory -Force -Path $presetDir | Out-Null
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText((Join-Path $presetDir 'agent.cordis.yml'), $comp, $utf8NoBom)

    $presetYml = @"
name: 未花模式
description: 以圣园未花（聖園ミカ / Misono Mika）的人格运行，完整保留编码、工具、检索、子代理与工作流能力。适合"整场都是未花"的会话。
order: 20
"@
    [System.IO.File]::WriteAllText((Join-Path $presetDir 'preset.yml'), $presetYml, $utf8NoBom)
    Write-Ok "Preset -> $presetDir"
}

Write-Step '部署完成'
Write-Host "  Skill   : $skillDst"
Write-Host "  Memory  : $memoryDst"
Write-Host "  Persona : $profilePatch"
Write-Host "  Preset  : $presetDir"
Write-Host '提示：persona patch 与预设对「新会话」生效；当前会话不变。'
