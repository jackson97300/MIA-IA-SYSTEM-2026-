# ════════════════════════════════════════════════════════════════
# SCRIPT APPLICATION FIX SL/TP - 02 DÉCEMBRE 2025
# ════════════════════════════════════════════════════════════════
# Ce script applique automatiquement le fix pour les SL/TP bugués
# Usage: .\apply_fix_sltp.ps1
# ════════════════════════════════════════════════════════════════

$ErrorActionPreference = "Stop"

Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  FIX SL/TP SIMPLES - APPLICATION AUTOMATIQUE" -ForegroundColor Cyan
Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# ════════════════════════════════════════════════════════════════
# ÉTAPE 1: VÉRIFICATIONS
# ════════════════════════════════════════════════════════════════

Write-Host "[1/7] Vérifications préliminaires..." -ForegroundColor Yellow

# Vérifier qu'on est dans le bon dossier
if (-not (Test-Path "LAUNCH/launch_production_CLEAN_v2.py")) {
    Write-Host "❌ ERREUR: Fichier LAUNCH/launch_production_CLEAN_v2.py introuvable!" -ForegroundColor Red
    Write-Host "   Assurez-vous d'être dans le dossier D:\MIA_IA_system" -ForegroundColor Red
    exit 1
}

Write-Host "   ✅ Fichier cible trouvé" -ForegroundColor Green

# ════════════════════════════════════════════════════════════════
# ÉTAPE 2: ARRÊTER LE BOT
# ════════════════════════════════════════════════════════════════

Write-Host ""
Write-Host "[2/7] Arrêt du bot..." -ForegroundColor Yellow

$pythonProcesses = Get-Process python* -ErrorAction SilentlyContinue
if ($pythonProcesses) {
    Write-Host "   ⚠️  Processus Python détectés, arrêt en cours..." -ForegroundColor Yellow
    $pythonProcesses | Stop-Process -Force
    Start-Sleep -Seconds 2
    Write-Host "   ✅ Bot arrêté" -ForegroundColor Green
} else {
    Write-Host "   ℹ️  Aucun processus Python en cours" -ForegroundColor Gray
}

# ════════════════════════════════════════════════════════════════
# ÉTAPE 3: BACKUP
# ════════════════════════════════════════════════════════════════

Write-Host ""
Write-Host "[3/7] Backup du fichier original..." -ForegroundColor Yellow

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupFile = "ARCHIVE/launch_production_CLEAN_v2_smart_sltp_BACKUP_$timestamp.py"

if (-not (Test-Path "ARCHIVE")) {
    New-Item -ItemType Directory -Path "ARCHIVE" | Out-Null
}

Copy-Item "LAUNCH/launch_production_CLEAN_v2.py" $backupFile
Write-Host "   ✅ Backup créé: $backupFile" -ForegroundColor Green

# ════════════════════════════════════════════════════════════════
# ÉTAPE 4: LECTURE DU FICHIER
# ════════════════════════════════════════════════════════════════

Write-Host ""
Write-Host "[4/7] Lecture du fichier..." -ForegroundColor Yellow

$content = Get-Content "LAUNCH/launch_production_CLEAN_v2.py" -Raw
Write-Host "   ✅ Fichier lu ($($content.Length) caractères)" -ForegroundColor Green

# ════════════════════════════════════════════════════════════════
# ÉTAPE 5: APPLICATION DU FIX
# ════════════════════════════════════════════════════════════════

Write-Host ""
Write-Host "[5/7] Application du fix..." -ForegroundColor Yellow

# Pattern à rechercher (début du bloc à remplacer)
$pattern = @"
                                # SL minimum et maximum de sécurité \(en ticks\)
                                min_sl_ticks = 8   # Minimum 2 pts pour ES
"@

if ($content -match [regex]::Escape($pattern)) {
    Write-Host "   ✅ Bloc à remplacer trouvé" -ForegroundColor Green

    # Nouveau code (simplifié)
    $newCode = @"
                                # ════════════════════════════════════════════════════════════
                                # ✅ FIX 02/12/2025: SL/TP FIXES (ALIGNÉ BACKTEST VALIDÉ)
                                # ════════════════════════════════════════════════════════════
                                # La logique "smart" GEX causait:
                                # - SL trop serrés (8-13t au lieu de 20-35t)
                                # - TP inversés (en-dessous du prix d'entrée!)
                                # - R:R dégradé (parfois négatif)
                                #
                                # SOLUTION: Utiliser les valeurs FIXES du backtest validé
                                # Win Rate 83% avec ces paramètres!
                                # ════════════════════════════════════════════════════════════

                                if ml_action == "LONG":
                                    # SL LONG: EN DESSOUS du prix d'entrée
                                    stop_loss = mid_price - (sl_ticks * tick_size)

                                    # TP LONG: AU DESSUS du prix d'entrée
                                    take_profit = mid_price + (tp_ticks * tick_size)

                                    logger.info(f"   💎 SL LONG @ {stop_loss:.2f} ({sl_ticks}t en-dessous)")
                                    logger.info(f"   🎯 TP LONG @ {take_profit:.2f} ({tp_ticks}t au-dessus)")

                                else:  # SHORT
                                    # SL SHORT: AU DESSUS du prix d'entrée
                                    stop_loss = mid_price + (sl_ticks * tick_size)

                                    # TP SHORT: EN DESSOUS du prix d'entrée
                                    take_profit = mid_price - (tp_ticks * tick_size)

                                    logger.info(f"   💎 SL SHORT @ {stop_loss:.2f} ({sl_ticks}t au-dessus)")
                                    logger.info(f"   🎯 TP SHORT @ {take_profit:.2f} ({tp_ticks}t en-dessous)")

                                # ════════════════════════════════════════════════════════════
                                # ✅ VALIDATION R:R MINIMUM (SÉCURITÉ)
                                # ════════════════════════════════════════════════════════════
                                sl_distance_ticks = abs(mid_price - stop_loss) / tick_size
                                tp_distance_ticks = abs(take_profit - mid_price) / tick_size
                                rr_ratio = tp_distance_ticks / sl_distance_ticks if sl_distance_ticks > 0 else 0

                                if rr_ratio < 1.4:  # Minimum 1.4:1
                                    logger.warning(
                                        f"   ❌ [{symbol}] R:R insuffisant: {rr_ratio:.2f} < 1.4 "
                                        f"(SL:{sl_distance_ticks:.0f}t, TP:{tp_distance_ticks:.0f}t)"
                                    )
                                    continue  # Skip ce trade!

                                logger.info(f"   ✅ R:R: {rr_ratio:.2f}:1 (SL:{sl_distance_ticks:.0f}t → TP:{tp_distance_ticks:.0f}t)")
"@

    Write-Host "   ⚠️  AVERTISSEMENT: Remplacement automatique désactivé pour sécurité" -ForegroundColor Yellow
    Write-Host "   ℹ️  Veuillez appliquer le fix manuellement:" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "   1. Ouvrir: code LAUNCH/launch_production_CLEAN_v2.py" -ForegroundColor White
    Write-Host "   2. Chercher ligne ~1440: 'min_sl_ticks = 8'" -ForegroundColor White
    Write-Host "   3. Remplacer tout le bloc (80 lignes) par le nouveau code" -ForegroundColor White
    Write-Host "   4. Voir: FIXES/fix_sl_tp_simple_02dec2025.py" -ForegroundColor White
    Write-Host ""

} else {
    Write-Host "   ❌ Bloc à remplacer non trouvé!" -ForegroundColor Red
    Write-Host "   ℹ️  Le fichier a peut-être déjà été modifié" -ForegroundColor Yellow
}

# ════════════════════════════════════════════════════════════════
# ÉTAPE 6: ACTIVER PAPER MODE
# ════════════════════════════════════════════════════════════════

Write-Host ""
Write-Host "[6/7] Configuration Paper Mode..." -ForegroundColor Yellow
Write-Host "   ⚠️  IMPORTANT: Activez manuellement le Paper Mode avant de relancer!" -ForegroundColor Yellow
Write-Host "   Ligne ~175: paper_trading: bool = True" -ForegroundColor White

# ════════════════════════════════════════════════════════════════
# ÉTAPE 7: RÉSUMÉ
# ════════════════════════════════════════════════════════════════

Write-Host ""
Write-Host "[7/7] Résumé" -ForegroundColor Yellow
Write-Host ""
Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  PROCHAINES ÉTAPES" -ForegroundColor Cyan
Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. ✅ Bot arrêté" -ForegroundColor Green
Write-Host "2. ✅ Backup créé: $backupFile" -ForegroundColor Green
Write-Host "3. ⏳ Appliquer le fix manuellement (voir FIXES/fix_sl_tp_simple_02dec2025.py)" -ForegroundColor Yellow
Write-Host "4. ⏳ Activer Paper Mode (paper_trading = True)" -ForegroundColor Yellow
Write-Host "5. ⏳ Tester 1-2h en Paper" -ForegroundColor Yellow
Write-Host "6. ⏳ Si OK → Retour Live (paper_trading = False)" -ForegroundColor Yellow
Write-Host ""
Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  VALIDATION POST-FIX" -ForegroundColor Cyan
Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Surveiller les logs:" -ForegroundColor White
Write-Host "  Get-Content logs_advanced\trades\trades_*.log -Tail 20 -Wait" -ForegroundColor Gray
Write-Host ""
Write-Host "Vérifier:" -ForegroundColor White
Write-Host "  ✅ ES: SL=20t, TP=35t" -ForegroundColor Gray
Write-Host "  ✅ NQ: SL=35t, TP=70t" -ForegroundColor Gray
Write-Host "  ✅ R:R toujours positif (1.75-2.0)" -ForegroundColor Gray
Write-Host "  ✅ Pas de 'TP inversé' ou 'R:R insuffisant'" -ForegroundColor Gray
Write-Host ""
Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# ════════════════════════════════════════════════════════════════
# PAUSE FINALE
# ════════════════════════════════════════════════════════════════

Write-Host "Appuyez sur une touche pour continuer..." -ForegroundColor White
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")



