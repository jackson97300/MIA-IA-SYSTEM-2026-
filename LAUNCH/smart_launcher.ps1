# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                    MIA SMART LAUNCHER - POWERSHELL                           ║
# ╠══════════════════════════════════════════════════════════════════════════════╣
# ║  Lance le bot MIA avec le watchdog pour auto-restart                         ║
# ║  Version: 1.0 | Date: 04 Décembre 2025                                       ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

param(
    [switch]$WatchdogOnly,  # Ne lance que le watchdog (bot déjà lancé)
    [switch]$BotOnly,       # Ne lance que le bot (sans watchdog)
    [switch]$Stop           # Arrête tout
)

$ProjectRoot = "D:\MIA_IA_system"
$BotScript = "$ProjectRoot\LAUNCH\launch_production_CLEAN_v2.py"
$WatchdogScript = "$ProjectRoot\LAUNCH\mia_watchdog.py"

# ═══════════════════════════════════════════════════════════════════════════════
# FONCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

function Show-Banner {
    Write-Host ""
    Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║           MIA SMART LAUNCHER v1.0                            ║" -ForegroundColor Cyan
    Write-Host "║           Trading Bot avec Auto-Restart                      ║" -ForegroundColor Cyan
    Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""
}

function Stop-AllProcesses {
    Write-Host "[STOP] Arrêt de tous les processus MIA..." -ForegroundColor Yellow

    # Arrêter via PID si disponible
    $pidFile = "$ProjectRoot\logs\bot.pid"
    if (Test-Path $pidFile) {
        $pid = Get-Content $pidFile
        try {
            Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
            Write-Host "[OK] Bot (PID $pid) arrêté" -ForegroundColor Green
        } catch {
            Write-Host "[INFO] Bot PID $pid déjà arrêté" -ForegroundColor Gray
        }
        Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
    }

    # Arrêter tous les Python liés à MIA
    $pythonProcesses = Get-Process python -ErrorAction SilentlyContinue | Where-Object {
        $_.Path -like "*python*"
    }

    if ($pythonProcesses) {
        $pythonProcesses | Stop-Process -Force
        Write-Host "[OK] $($pythonProcesses.Count) processus Python arrêtés" -ForegroundColor Green
    } else {
        Write-Host "[INFO] Aucun processus Python en cours" -ForegroundColor Gray
    }

    Write-Host "[OK] Tous les processus arrêtés" -ForegroundColor Green
}

function Start-Bot {
    Write-Host "[START] Démarrage du bot MIA..." -ForegroundColor Cyan

    # Vérifier que le script existe
    if (-not (Test-Path $BotScript)) {
        Write-Host "[ERREUR] Script non trouvé: $BotScript" -ForegroundColor Red
        return $false
    }

    # Se positionner dans le projet
    Set-Location $ProjectRoot

    # Créer le dossier logs si nécessaire
    New-Item -ItemType Directory -Path "$ProjectRoot\logs" -Force | Out-Null

    # Lancer le bot
    $process = Start-Process python -ArgumentList $BotScript -WorkingDirectory $ProjectRoot -PassThru -WindowStyle Normal

    Write-Host "[OK] Bot démarré (PID: $($process.Id))" -ForegroundColor Green

    # Sauvegarder le PID
    $process.Id | Out-File "$ProjectRoot\logs\bot.pid" -Force

    return $true
}

function Start-Watchdog {
    Write-Host "[START] Démarrage du watchdog..." -ForegroundColor Cyan

    # Vérifier que le script existe
    if (-not (Test-Path $WatchdogScript)) {
        Write-Host "[ERREUR] Script non trouvé: $WatchdogScript" -ForegroundColor Red
        return $false
    }

    # Se positionner dans le projet
    Set-Location $ProjectRoot

    # Lancer le watchdog dans une nouvelle fenêtre
    Start-Process python -ArgumentList $WatchdogScript -WorkingDirectory $ProjectRoot -WindowStyle Normal

    Write-Host "[OK] Watchdog démarré" -ForegroundColor Green
    return $true
}

function Show-Status {
    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Gray
    Write-Host "                         STATUS" -ForegroundColor White
    Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Gray

    # Vérifier le bot
    $pidFile = "$ProjectRoot\logs\bot.pid"
    if (Test-Path $pidFile) {
        $botPid = Get-Content $pidFile
        $process = Get-Process -Id $botPid -ErrorAction SilentlyContinue
        if ($process) {
            Write-Host "[BOT] En cours (PID: $botPid)" -ForegroundColor Green
        } else {
            Write-Host "[BOT] Arrêté (PID obsolète: $botPid)" -ForegroundColor Red
        }
    } else {
        Write-Host "[BOT] Arrêté (pas de PID)" -ForegroundColor Red
    }

    # Vérifier le heartbeat
    $heartbeatFile = "$ProjectRoot\logs\heartbeat.json"
    if (Test-Path $heartbeatFile) {
        $heartbeat = Get-Content $heartbeatFile | ConvertFrom-Json
        $lastBeat = [DateTime]::Parse($heartbeat.timestamp)
        $age = (Get-Date) - $lastBeat

        if ($age.TotalSeconds -lt 120) {
            Write-Host "[HEARTBEAT] OK (il y a $([int]$age.TotalSeconds)s)" -ForegroundColor Green
        } else {
            Write-Host "[HEARTBEAT] STALE (il y a $([int]$age.TotalSeconds)s)" -ForegroundColor Yellow
        }

        Write-Host "   Cycles: $($heartbeat.cycles)" -ForegroundColor Gray
        Write-Host "   Trades: $($heartbeat.trades_today)" -ForegroundColor Gray
        Write-Host "   P&L: `$$($heartbeat.pnl_today)" -ForegroundColor Gray
    } else {
        Write-Host "[HEARTBEAT] Pas de fichier" -ForegroundColor Red
    }

    Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Gray
    Write-Host ""
}

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

Show-Banner

if ($Stop) {
    Stop-AllProcesses
    Show-Status
    exit 0
}

if ($WatchdogOnly) {
    Start-Watchdog
    Show-Status
    exit 0
}

if ($BotOnly) {
    Start-Bot
    Show-Status
    exit 0
}

# Mode par défaut: Arrêter tout, puis lancer bot + watchdog
Write-Host "[MODE] Lancement complet (Bot + Watchdog)" -ForegroundColor Magenta
Write-Host ""

Stop-AllProcesses
Start-Sleep -Seconds 2

if (Start-Bot) {
    Start-Sleep -Seconds 5  # Attendre que le bot démarre
    # Lancer le watchdog pour protection crash
    Start-Watchdog
}

Show-Status

Write-Host ""
Write-Host "Appuyez sur une touche pour fermer cette fenêtre..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
