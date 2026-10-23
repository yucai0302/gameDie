# ============================================================
# setup-csgo.ps1
# Auto-locate CS2 / CS:GO install dir, write autoexec.cfg to enable
# console log output, and save the absolute log path to
# agent/.csgo-log-path for CSGOAdapter to read.
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts/setup-csgo.ps1
# ============================================================

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.Encoding]::UTF8

# Project root (this script lives at <root>/scripts/setup-csgo.ps1)
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$LogPathFile = Join-Path $Root "agent\.csgo-log-path"

function Write-Step2  { param($msg) Write-Host "[setup] $msg" -ForegroundColor Cyan }
function Write-Ok2    { param($msg) Write-Host "[ok]    $msg" -ForegroundColor Green }
function Write-Warn2  { param($msg) Write-Host "[warn]  $msg" -ForegroundColor Yellow }
function Write-Err2   { param($msg) Write-Host "[err]   $msg" -ForegroundColor Red }

# ---------- 1. Locate Steam install path ----------
Write-Step2 "Detecting Steam install path..."
$steam = $null

# 1.1 Registry HKCU\Software\Valve\Steam
try {
    $reg = Get-ItemProperty "HKCU:\Software\Valve\Steam" -ErrorAction SilentlyContinue
    if ($reg -and $reg.SteamPath) {
        $steam = $reg.SteamPath
        Write-Ok2 "Registry HKCU\Software\Valve\Steam -> $steam"
    }
} catch {}

# 1.2 Registry HKLM\SOFTWARE\WOW6432Node\Valve\Steam
if (-not $steam) {
    try {
        $reg = Get-ItemProperty "HKLM:\SOFTWARE\WOW6432Node\Valve\Steam" -ErrorAction SilentlyContinue
        if ($reg -and $reg.InstallPath) {
            $steam = $reg.InstallPath
            Write-Ok2 "Registry HKLM\...\Valve\Steam -> $steam"
        }
    } catch {}
}

# 1.3 Default path fallback
if (-not $steam) {
    $default = "${env:ProgramFiles(x86)}\Steam"
    if (Test-Path $default) {
        $steam = $default
        Write-Ok2 "Default path -> $steam"
    }
}

if (-not $steam -or -not (Test-Path $steam)) {
    Write-Err2 "Steam install path not found. Please make sure Steam is installed."
    "" | Out-File -FilePath $LogPathFile -Encoding UTF8 -NoNewline
    exit 1
}

# ---------- 2. Collect all Steam library folders ----------
Write-Step2 "Parsing Steam library folders..."
$libraries = @($steam)
$vdf = Join-Path $steam "steamapps\libraryfolders.vdf"
if (Test-Path $vdf) {
    try {
        # Use Select-String with -SimpleMatch to find lines containing "path",
        # then split by double-quote to extract the path segment.
        $pathLines = Select-String -Path $vdf -Pattern 'path' -SimpleMatch -ErrorAction SilentlyContinue
        foreach ($hit in $pathLines) {
            $line = $hit.Line
            # Line format:  "path"		"D:\\SteamLibrary"
            # Split by double-quote; parts[3] is the path.
            $parts = $line -split '"'
            if ($parts.Length -ge 4) {
                $p = $parts[3]
                # vdf uses double backslashes; revert to single.
                $p = $p -replace '\\\\', '\'
                if ($p -and (Test-Path $p) -and ($libraries -notcontains $p)) {
                    $libraries += $p
                }
            }
        }
    } catch {
        Write-Warn2 "Failed to parse libraryfolders.vdf: $_"
    }
}
Write-Ok2 "Found $($libraries.Count) Steam librar(y/ies):"
foreach ($lib in $libraries) { Write-Host "       - $lib" -ForegroundColor DarkGray }

# ---------- 3. Search each library for CS2 / CS:GO ----------
$candidates = @(
    @{ Name = "CS2";   CfgRel = "steamapps\common\Counter-Strike 2\game\csgo\cfg";            LogRel = "steamapps\common\Counter-Strike 2\game\csgo\console.log" },
    @{ Name = "CS:GO"; CfgRel = "steamapps\common\Counter-Strike Global Offensive\csgo\cfg"; LogRel = "steamapps\common\Counter-Strike Global Offensive\csgo\console.log" }
)

$found = $null
foreach ($lib in $libraries) {
    foreach ($c in $candidates) {
        $cfgDir = Join-Path $lib $c.CfgRel
        if (Test-Path $cfgDir) {
            $logPath = Join-Path $lib $c.LogRel
            $found = [pscustomobject]@{
                Game    = $c.Name
                Lib     = $lib
                CfgDir  = $cfgDir
                LogPath = $logPath
            }
            break
        }
    }
    if ($found) { break }
}

if (-not $found) {
    Write-Warn2 "CS2 or CS:GO cfg folder not found in known Steam libraries."
    Write-Warn2 "Please make sure the game is installed via Steam."
    # Write an empty path file; Agent will degrade gracefully.
    "" | Out-File -FilePath $LogPathFile -Encoding UTF8 -NoNewline
    exit 2
}

Write-Ok2 "Located $($found.Game): $($found.CfgDir)"

# ---------- 4. Write / append autoexec.cfg ----------
$autoexec = Join-Path $found.CfgDir "autoexec.cfg"

# Check whether the file already contains the needed commands.
$needWrite = $true
if (Test-Path $autoexec) {
    try {
        $existing = Get-Content $autoexec -Raw -Encoding ASCII -ErrorAction Stop
        # Use -like substring matching to avoid regex special-char issues.
        $hasLogfile = $false
        $hasLogOn = $false
        foreach ($ln in ($existing -split "`n")) {
            $trim = $ln.Trim()
            if ($trim -like "*con_logfile*") { $hasLogfile = $true }
            if ($trim -like "*con_log*1*") { $hasLogOn = $true }
        }
        if ($hasLogfile -and $hasLogOn) {
            Write-Ok2 "autoexec.cfg already contains con_logfile config, skip writing"
            $needWrite = $false
        } else {
            Write-Step2 "autoexec.cfg exists but lacks con_logfile, will append..."
        }
    } catch {
        Write-Step2 "Failed to read autoexec.cfg, will overwrite..."
    }
} else {
    Write-Step2 "autoexec.cfg does not exist, will create..."
}

if ($needWrite) {
    # Build the config block as plain ASCII lines (no here-string to avoid encoding issues).
    $lines = @(
        '// === DiePlay auto config: enable console log output ===',
        'con_logfile "console.log"',
        'con_log 1'
    )
    $block = ($lines -join "`r`n") + "`r`n"
    try {
        if (Test-Path $autoexec) {
            $existing = Get-Content $autoexec -Raw -Encoding ASCII -ErrorAction SilentlyContinue
            if (-not $existing.EndsWith("`n")) { $existing += "`n" }
            $newContent = $existing + $block
            [System.IO.File]::WriteAllText($autoexec, $newContent, [System.Text.Encoding]::ASCII)
        } else {
            [System.IO.File]::WriteAllText($autoexec, $block, [System.Text.Encoding]::ASCII)
        }
        Write-Ok2 "Written: $autoexec"
    } catch {
        Write-Err2 "Failed to write autoexec.cfg: $_"
        exit 3
    }
}

# ---------- 5. Save log path to agent/.csgo-log-path ----------
try {
    [System.IO.File]::WriteAllText($LogPathFile, $found.LogPath, [System.Text.Encoding]::UTF8)
    Write-Ok2 "Recorded log path: $($found.LogPath)"
} catch {
    Write-Err2 "Failed to write ${LogPathFile}: $_"
    exit 4
}

# ---------- 6. Next-step hint ----------
Write-Host ""
Write-Host "============================================================" -ForegroundColor DarkCyan
Write-Host " CSGO auto-config done" -ForegroundColor Green
Write-Host "------------------------------------------------------------" -ForegroundColor DarkCyan
Write-Host " Game:       $($found.Game)" -ForegroundColor White
Write-Host " Config:     $autoexec" -ForegroundColor White
Write-Host " Log path:   $($found.LogPath)" -ForegroundColor White
Write-Host "------------------------------------------------------------" -ForegroundColor DarkCyan
Write-Host " NOTE: Please restart CS2/CSGO once to let autoexec.cfg take effect." -ForegroundColor Yellow
Write-Host "       After entering the game, the Agent will start listening." -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor DarkCyan
exit 0
