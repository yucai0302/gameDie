# ============================================================
# monitor.ps1
# Continuously display Agent log and CSGO log status,
# so users can observe detection in real time.
#
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -NoExit -File scripts/monitor.ps1
# ============================================================

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$AgentLog = Join-Path $Root "agent\logs\agent.log"
$LogPathFile = Join-Path $Root "agent\.csgo-log-path"

# Hide cursor to reduce flicker
[Console]::CursorVisible = $false

try {
    while ($true) {
        Clear-Host
        Write-Host ""
        Write-Host "  ============================================================" -ForegroundColor Cyan
        Write-Host "   GameDie Live Monitor" -ForegroundColor Cyan
        Write-Host "  ============================================================" -ForegroundColor Cyan
        $now = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        Write-Host "   [refresh] $now" -ForegroundColor DarkGray
        Write-Host "  ------------------------------------------------------------" -ForegroundColor DarkGray

        # ---- CSGO log path & status ----
        $csgoLog = ""
        if (Test-Path $LogPathFile) {
            $raw = Get-Content $LogPathFile -Raw -ErrorAction SilentlyContinue
            if ($raw) { $csgoLog = $raw.Trim() }
        }
        if ($csgoLog) {
            Write-Host "   CSGO log path: " -NoNewline -ForegroundColor DarkGray
            Write-Host $csgoLog -ForegroundColor White
            if (Test-Path $csgoLog) {
                $item = Get-Item $csgoLog
                $size = $item.Length
                $mt = $item.LastWriteTime.ToString("HH:mm:ss")
                if ($size -ge 1KB) {
                    $sizeStr = "{0:N2} KB" -f ($size / 1KB)
                } else {
                    $sizeStr = "$size B"
                }
                Write-Host "   CSGO log size: " -NoNewline -ForegroundColor DarkGray
                Write-Host "$sizeStr  (last modified $mt)" -ForegroundColor Green
            } else {
                Write-Host "   CSGO log size: " -NoNewline -ForegroundColor DarkGray
                Write-Host "not yet created (player has not entered the game)" -ForegroundColor Yellow
            }
        } else {
            Write-Host "   CSGO log: " -NoNewline -ForegroundColor DarkGray
            Write-Host "not configured (please run scripts\setup-csgo.ps1)" -ForegroundColor Red
        }
        Write-Host "  ------------------------------------------------------------" -ForegroundColor DarkGray

        # ---- Agent log last 8 lines ----
        Write-Host "   Agent log:   " -NoNewline -ForegroundColor DarkGray
        Write-Host $AgentLog -ForegroundColor White
        if (Test-Path $AgentLog) {
            $lines = Get-Content $AgentLog -Tail 8 -ErrorAction SilentlyContinue
            if ($lines) {
                Write-Host "   Agent recent log (last 8 lines):" -ForegroundColor DarkGray
                foreach ($line in $lines) {
                    if ($line -match "WARNING") {
                        Write-Host "   | $line" -ForegroundColor Yellow
                    } elseif ($line -match "ERROR") {
                        Write-Host "   | $line" -ForegroundColor Red
                    } elseif ($line -match "INFO") {
                        Write-Host "   | $line" -ForegroundColor White
                    } else {
                        Write-Host "   | $line" -ForegroundColor DarkGray
                    }
                }
            } else {
                Write-Host "   (log empty, waiting for Agent to start...)" -ForegroundColor Yellow
            }
        } else {
            Write-Host "   (Agent log not yet created, waiting for start...)" -ForegroundColor Yellow
        }

        Write-Host "  ------------------------------------------------------------" -ForegroundColor DarkGray
        Write-Host "   Services:   " -NoNewline -ForegroundColor DarkGray
        Write-Host "backend http://localhost:8000  |  dashboard http://localhost:5173" -ForegroundColor White
        Write-Host "   Exit:        " -NoNewline -ForegroundColor DarkGray
        Write-Host "Ctrl+C (does not stop background services)" -ForegroundColor DarkGray
        Write-Host "  ============================================================" -ForegroundColor Cyan
        Write-Host ""

        Start-Sleep -Seconds 2
    }
} finally {
    [Console]::CursorVisible = $true
}
