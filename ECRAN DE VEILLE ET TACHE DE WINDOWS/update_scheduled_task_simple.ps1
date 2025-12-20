# Script simple: Juste changer l'heure et desactiver le filtre reseau
# NE TOUCHE PAS aux autres parametres (WakeToRun, etc.)
#
# MODIFICATIONS:
#   1. Heure: 07:30 -> 07:55 (5 min avant session London)
#   2. RunOnlyIfNetworkAvailable: True -> False (plus fiable)
#
# UTILISATION:
#   1. Ouvrir PowerShell en ADMINISTRATEUR
#   2. Executer: .\update_scheduled_task_simple.ps1

Write-Host ""
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "  MISE A JOUR TACHE PLANIFIEE - HEURE 07:55" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""

$TASK_NAME = "MIA_Trading_Bot_0730"
$NEW_START_TIME = "07:55"

# VERIFIER DROITS ADMINISTRATEUR
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "ERREUR: Ce script necessite les droits administrateur" -ForegroundColor Red
    Write-Host ""
    pause
    exit 1
}

Write-Host "Droits administrateur confirmes" -ForegroundColor Green
Write-Host ""

# VERIFIER TACHE EXISTE
$task = Get-ScheduledTask -TaskName $TASK_NAME -ErrorAction SilentlyContinue

if (-not $task) {
    Write-Host "ERREUR: Tache $TASK_NAME non trouvee" -ForegroundColor Red
    Write-Host ""
    pause
    exit 1
}

Write-Host "Tache trouvee: $TASK_NAME" -ForegroundColor Green
Write-Host ""

# AFFICHER CONFIGURATION ACTUELLE
Write-Host "CONFIGURATION ACTUELLE:" -ForegroundColor Yellow
Write-Host "  Heure actuelle: $($task.Triggers[0].StartBoundary)" -ForegroundColor White
Write-Host "  RunOnlyIfNetworkAvailable: $($task.Settings.RunOnlyIfNetworkAvailable)" -ForegroundColor $(if($task.Settings.RunOnlyIfNetworkAvailable){'Red'}else{'Green'})
Write-Host ""

# MODIFIER
Write-Host "Application des modifications..." -ForegroundColor Cyan
Write-Host ""

try {
    # 1. Modifier l'heure
    $newTrigger = New-ScheduledTaskTrigger -Daily -At $NEW_START_TIME

    # 2. Modifier le filtre reseau uniquement
    $taskDefinition = Get-ScheduledTask -TaskName $TASK_NAME
    $taskDefinition.Settings.RunOnlyIfNetworkAvailable = $false

    # Appliquer
    Set-ScheduledTask -TaskName $TASK_NAME `
        -Settings $taskDefinition.Settings `
        -Trigger $newTrigger `
        -ErrorAction Stop | Out-Null

    Write-Host "Modifications appliquees avec succes !" -ForegroundColor Green
    Write-Host ""

} catch {
    Write-Host "ERREUR: $_" -ForegroundColor Red
    Write-Host ""
    pause
    exit 1
}

# VERIFIER NOUVELLE CONFIGURATION
$taskUpdated = Get-ScheduledTask -TaskName $TASK_NAME

Write-Host "NOUVELLE CONFIGURATION:" -ForegroundColor Green
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor White
Write-Host "  Heure: 07:55 (5 min avant London) ✅" -ForegroundColor Green
Write-Host "  RunOnlyIfNetworkAvailable: False ✅" -ForegroundColor Green
Write-Host "  Prochaine execution: $($taskUpdated | Get-ScheduledTaskInfo | Select-Object -ExpandProperty NextRunTime)" -ForegroundColor Cyan
Write-Host ""

Write-Host "================================================================================" -ForegroundColor Green
Write-Host "  MODIFICATION TERMINEE" -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Green
Write-Host ""

Write-Host "Le bot se lancera demain a 07:55 !" -ForegroundColor Green
Write-Host ""

Write-Host "Appuie sur une touche pour fermer..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')


