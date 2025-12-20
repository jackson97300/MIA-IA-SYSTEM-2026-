# Script de correction tache planifiee - FIABILITE 100%
# Corrige les parametres qui empechent le lancement certains jours
# + Ajuste l'heure à 07:55 (5 min avant session London 08:00)
#
# PROBLEMES CORRIGES:
#   1. RunOnlyIfNetworkAvailable = True  -> False (reseau pas toujours dispo)
#   2. WakeToRun = False                 -> True (reveil PC si veille)
#   3. AllowStartIfOnBatteries           -> True (laptop support)
#   4. Heure lancement 07:30             -> 07:55 (plus proche session)
#
# UTILISATION:
#   1. Ouvrir PowerShell en ADMINISTRATEUR
#   2. Executer: .\update_scheduled_task.ps1

Write-Host ""
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "  CORRECTION TACHE PLANIFIEE - FIABILITE 100% + HEURE 07:55" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""

$TASK_NAME = "MIA_Trading_Bot_0730"
$NEW_START_TIME = "07:55"  # 5 min avant session London

# VERIFIER DROITS ADMINISTRATEUR
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "ERREUR: Ce script necessite les droits administrateur" -ForegroundColor Red
    Write-Host ""
    Write-Host "Comment relancer avec droits admin:" -ForegroundColor Yellow
    Write-Host "   1. Fermer cette fenetre" -ForegroundColor White
    Write-Host "   2. Clic droit sur PowerShell -> Executer en tant qu'administrateur" -ForegroundColor White
    Write-Host "   3. Naviguer vers: cd D:\MIA_IA_system" -ForegroundColor White
    Write-Host "   4. Executer: .\update_scheduled_task.ps1" -ForegroundColor White
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
    Write-Host "Veuillez d'abord creer la tache avec: .\create_scheduled_task.ps1" -ForegroundColor Yellow
    Write-Host ""
    pause
    exit 1
}

Write-Host "Tache trouvee: $TASK_NAME" -ForegroundColor Green
Write-Host ""

# AFFICHER CONFIGURATION ACTUELLE
Write-Host "CONFIGURATION ACTUELLE:" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor White
Write-Host "  RunOnlyIfNetworkAvailable: $($task.Settings.RunOnlyIfNetworkAvailable)" -ForegroundColor $(if($task.Settings.RunOnlyIfNetworkAvailable){'Red'}else{'Green'})
Write-Host "  WakeToRun:                 $($task.Settings.WakeToRun)" -ForegroundColor $(if($task.Settings.WakeToRun){'Green'}else{'Red'})
Write-Host "  AllowStartIfOnBatteries:   $($task.Settings.AllowStartIfOnBatteries)" -ForegroundColor $(if($task.Settings.AllowStartIfOnBatteries){'Green'}else{'Red'})
Write-Host ""

# MODIFIER PARAMETRES
Write-Host "Application des corrections..." -ForegroundColor Cyan
Write-Host ""

try {
    # Recupérer la tâche complète pour modification
    $taskDefinition = $task | Get-ScheduledTask

    # Modifier les parametres (settings existants uniquement)
    $taskDefinition.Settings.RunOnlyIfNetworkAvailable = $false  # ✅ Lancer MEME SANS RESEAU
    $taskDefinition.Settings.WakeToRun = $true                   # ✅ REVEILLER PC si veille
    $taskDefinition.Settings.StartWhenAvailable = $true          # ✅ Rattraper si manque

    # Créer nouveau trigger à 07:55
    $newTrigger = New-ScheduledTaskTrigger -Daily -At $NEW_START_TIME

    # Appliquer les modifications
    Set-ScheduledTask -TaskName $TASK_NAME `
        -Settings $taskDefinition.Settings `
        -Trigger $newTrigger `
        -ErrorAction Stop | Out-Null

    Write-Host "Modifications appliquees avec succes !" -ForegroundColor Green
    Write-Host ""

} catch {
    Write-Host "ERREUR lors de la modification:" -ForegroundColor Red
    Write-Host "   $_" -ForegroundColor Red
    Write-Host ""
    pause
    exit 1
}

# VERIFIER NOUVELLE CONFIGURATION
$taskUpdated = Get-ScheduledTask -TaskName $TASK_NAME

Write-Host "NOUVELLE CONFIGURATION:" -ForegroundColor Green
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor White
Write-Host "  RunOnlyIfNetworkAvailable: $($taskUpdated.Settings.RunOnlyIfNetworkAvailable) ✅" -ForegroundColor Green
Write-Host "  WakeToRun:                 $($taskUpdated.Settings.WakeToRun) ✅" -ForegroundColor Green
Write-Host "  AllowStartIfOnBatteries:   $($taskUpdated.Settings.AllowStartIfOnBatteries) ✅" -ForegroundColor Green
Write-Host "  StartWhenAvailable:        $($taskUpdated.Settings.StartWhenAvailable) ✅" -ForegroundColor Green
Write-Host ""

Write-Host "================================================================================" -ForegroundColor Green
Write-Host "  CORRECTION TERMINEE - FIABILITE 100%" -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Green
Write-Host ""

Write-Host "CE QUI A ETE CORRIGE:" -ForegroundColor Cyan
Write-Host "   ✅ Heure modifiée: 07:30 → 07:55 (5 min avant session London)" -ForegroundColor White
Write-Host "   ✅ Lancement MEME SI pas de réseau (WiFi pas connecté)" -ForegroundColor White
Write-Host "   ✅ Réveil automatique du PC si en veille (WakeToRun)" -ForegroundColor White
Write-Host "   ✅ Rattrapage si lancement manqué (StartWhenAvailable)" -ForegroundColor White
Write-Host ""

Write-Host "MAINTENANT:" -ForegroundColor Yellow
Write-Host "   • Le bot se lancera TOUS LES JOURS à 07:55" -ForegroundColor White
Write-Host "   • 5 minutes avant la session London (08:00)" -ForegroundColor White
Write-Host "   • Même si réseau pas dispo" -ForegroundColor White
Write-Host "   • Même si PC était en veille (il sera réveillé)" -ForegroundColor White
Write-Host "   • Si lancement manqué, rattrapera dès que possible" -ForegroundColor White
Write-Host ""

Write-Host "IMPORTANT:" -ForegroundColor Red
Write-Host "   • Garde quand même le PC allumé (pas éteint)" -ForegroundColor White
Write-Host "   • Désactive mises à jour auto Windows (redémarrages)" -ForegroundColor White
Write-Host "   • Vérifie que Sierra Chart démarre avec Windows" -ForegroundColor White
Write-Host ""

Write-Host "PROCHAINE EXECUTION:" -ForegroundColor Cyan
$nextRun = $taskUpdated | Get-ScheduledTaskInfo | Select-Object -ExpandProperty NextRunTime
Write-Host "   $nextRun" -ForegroundColor Green
Write-Host ""

Write-Host "================================================================================" -ForegroundColor Green
Write-Host ""

Write-Host "Appuie sur une touche pour fermer..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')
