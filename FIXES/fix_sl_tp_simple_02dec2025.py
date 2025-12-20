#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FIX: SL/TP SIMPLES - 02 DÉCEMBRE 2025
=====================================

PROBLÈME DÉTECTÉ:
- SL trop serrés (8-13 ticks au lieu de 20-35)
- TP inversés (en-dessous du prix d'entrée pour LONG!)
- R:R non respecté (parfois négatif!)

CAUSE:
Logique "smart" SL/TP basée sur niveaux GEX trop agressive et bugée.

SOLUTION:
Revenir aux valeurs FIXES du backtest validé (Win Rate 83%).

FICHIER À MODIFIER:
LAUNCH/launch_production_CLEAN_v2.py, lignes ~1440-1520

BACKUP AVANT:
Sauvegarder l'ancien code dans ARCHIVE/launch_production_CLEAN_v2_smart_sltp_BACKUP.py
"""

# ════════════════════════════════════════════════════════════════
# CODE À REMPLACER
# ════════════════════════════════════════════════════════════════

OLD_CODE = """
                                # SL minimum et maximum de sécurité (en ticks)
                                min_sl_ticks = 8   # Minimum 2 pts pour ES
                                max_sl_ticks = 40  # Maximum 10 pts pour ES (permet SL au-dessus/dessous GEX)
                                buffer_ticks = 2   # Buffer au-dessus/dessous du niveau GEX (0.50 pts)

                                # Buffer pour SL/TP
                                tp_buffer_ticks = 3  # Buffer AVANT le niveau (0.75 pts)

                                if ml_action == "LONG":
                                    # ═══════════════════════════════════════════════════════════
                                    # SL LONG: EN DESSOUS du support le plus proche
                                    # ═══════════════════════════════════════════════════════════
                                    stop_loss = mid_price - (sl_ticks * tick_size)  # Default

                                    supports_below = [g for g in gex_levels if g < mid_price]
                                    if supports_below:
                                        nearest_support = max(supports_below)
                                        smart_sl = nearest_support - (buffer_ticks * tick_size)
                                        dist_ticks = (mid_price - smart_sl) / tick_size

                                        if min_sl_ticks <= dist_ticks <= max_sl_ticks:
                                            stop_loss = smart_sl
                                            logger.info(f"   🎯 SL LONG @ {stop_loss:.2f} (sous GEX {nearest_support:.2f}, {dist_ticks:.0f}t)")
                                        else:
                                            logger.info(f"   ⚠️ SL: GEX {nearest_support:.2f} trop loin ({dist_ticks:.0f}t), default")

                                    # ═══════════════════════════════════════════════════════════
                                    # TP LONG: Calculer TP par défaut, puis vérifier si obstacle
                                    # ═══════════════════════════════════════════════════════════
                                    default_tp = mid_price + (tp_ticks * tick_size)
                                    take_profit = default_tp  # Par défaut

                                    # Chercher si un niveau GEX est ENTRE le prix et le TP default
                                    obstacles = [g for g in gex_levels if mid_price < g < default_tp]
                                    if obstacles:
                                        # Il y a un obstacle! TP = AVANT ce niveau
                                        first_obstacle = min(obstacles)  # Le plus proche
                                        smart_tp = first_obstacle - (tp_buffer_ticks * tick_size)
                                        take_profit = smart_tp
                                        logger.info(f"   🎯 TP LONG @ {take_profit:.2f} (AVANT obstacle GEX {first_obstacle:.2f})")
                                    else:
                                        # Pas d'obstacle → garder TP par défaut
                                        logger.info(f"   ✅ TP LONG @ {take_profit:.2f} (pas d'obstacle, {tp_ticks}t)")

                                else:  # SHORT
                                    # ═══════════════════════════════════════════════════════════
                                    # SL SHORT: AU DESSUS de la résistance la plus proche
                                    # ═══════════════════════════════════════════════════════════
                                    stop_loss = mid_price + (sl_ticks * tick_size)  # Default

                                    resistances_above = [g for g in gex_levels if g > mid_price]
                                    if resistances_above:
                                        nearest_resistance = min(resistances_above)
                                        smart_sl = nearest_resistance + (buffer_ticks * tick_size)
                                        dist_ticks = (smart_sl - mid_price) / tick_size

                                        if min_sl_ticks <= dist_ticks <= max_sl_ticks:
                                            stop_loss = smart_sl
                                            logger.info(f"   🎯 SL SHORT @ {stop_loss:.2f} (au-dessus GEX {nearest_resistance:.2f}, {dist_ticks:.0f}t)")
                                        else:
                                            logger.info(f"   ⚠️ SL: GEX {nearest_resistance:.2f} trop loin ({dist_ticks:.0f}t), default")

                                    # ═══════════════════════════════════════════════════════════
                                    # TP SHORT: Calculer TP par défaut, puis vérifier si obstacle
                                    # ═══════════════════════════════════════════════════════════
                                    default_tp = mid_price - (tp_ticks * tick_size)
                                    take_profit = default_tp  # Par défaut

                                    # Chercher si un niveau GEX est ENTRE le TP default et le prix
                                    obstacles = [g for g in gex_levels if default_tp < g < mid_price]
                                    if obstacles:
                                        # Il y a un obstacle! TP = APRÈS ce niveau
                                        first_obstacle = max(obstacles)  # Le plus proche
                                        smart_tp = first_obstacle + (tp_buffer_ticks * tick_size)
                                        take_profit = smart_tp
                                        logger.info(f"   🎯 TP SHORT @ {take_profit:.2f} (APRÈS obstacle GEX {first_obstacle:.2f})")
                                    else:
                                        # Pas d'obstacle → garder TP par défaut
                                        logger.info(f"   ✅ TP SHORT @ {take_profit:.2f} (pas d'obstacle, {tp_ticks}t)")
"""

# ════════════════════════════════════════════════════════════════
# NOUVEAU CODE (SIMPLE ET ROBUSTE)
# ════════════════════════════════════════════════════════════════

NEW_CODE = """
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
"""

# ════════════════════════════════════════════════════════════════
# INSTRUCTIONS D'APPLICATION
# ════════════════════════════════════════════════════════════════

INSTRUCTIONS = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                    INSTRUCTIONS APPLICATION DU FIX                            ║
╚══════════════════════════════════════════════════════════════════════════════╝

1. ARRÊTER LE BOT
   Get-Process python | Stop-Process -Force

2. BACKUP DU FICHIER ORIGINAL
   Copy-Item "LAUNCH/launch_production_CLEAN_v2.py" `
             "ARCHIVE/launch_production_CLEAN_v2_smart_sltp_BACKUP_02dec2025.py"

3. OUVRIR LE FICHIER
   code LAUNCH/launch_production_CLEAN_v2.py

4. CHERCHER LA LIGNE ~1440 (Ctrl+G → 1440)
   Chercher: "min_sl_ticks = 8"

5. SÉLECTIONNER TOUT LE BLOC (lignes ~1440-1520)
   Depuis "min_sl_ticks = 8"
   Jusqu'à la fin du bloc "else: # SHORT" avec TP SHORT

6. REMPLACER PAR LE NOUVEAU CODE CI-DESSUS (NEW_CODE)

7. SAUVEGARDER (Ctrl+S)

8. VÉRIFIER LA SYNTAXE
   python -m py_compile LAUNCH/launch_production_CLEAN_v2.py

   Si erreur → vérifier l'indentation (doit être alignée avec le code autour)

9. TESTER EN PAPER MODE FIRST!
   Modifier ligne ~175:
   paper_trading: bool = True  # ✅ PAPER MODE

10. RELANCER LE BOT
    python LAUNCH/launch_production_CLEAN_v2.py

11. SURVEILLER LES LOGS
    Get-Content logs_advanced\trades\trades_20251202.log -Tail 20 -Wait

    Vérifier:
    ✅ ES: SL=20t, TP=35t → R:R=1.75
    ✅ NQ: SL=35t, TP=70t → R:R=2.0
    ✅ Pas de "R:R insuffisant" messages
    ✅ Tous les TP AU DESSUS du prix d'entrée pour LONG
    ✅ Tous les TP EN DESSOUS du prix d'entrée pour SHORT

12. SI TOUT OK APRÈS 1-2H: RETOUR LIVE
    paper_trading: bool = False

    Relancer le bot

13. MONITORING CONTINU
    Surveiller Win Rate:
    - Attendu: 75-83% (comme backtest)
    - Si < 70% → recheck les paramètres

╔══════════════════════════════════════════════════════════════════════════════╗
║                         VALIDATION POST-FIX                                   ║
╚══════════════════════════════════════════════════════════════════════════════╝

Dans les logs, vous devriez voir:

✅ BON EXEMPLE (ES LONG):
   💎 SL LONG @ 6825.00 (20t en-dessous)
   🎯 TP LONG @ 6833.75 (35t au-dessus)
   ✅ R:R: 1.75:1 (SL:20t → TP:35t)

✅ BON EXEMPLE (NQ SHORT):
   💎 SL SHORT @ 25450.00 (35t au-dessus)
   🎯 TP SHORT @ 25375.00 (70t en-dessous)
   ✅ R:R: 2.00:1 (SL:35t → TP:70t)

❌ MAUVAIS EXEMPLE (À NE PLUS VOIR):
   SL @ 6825.00
   TP @ 6824.78  ← TP EN-DESSOUS DU PRIX!
   R:R: -0.04:1  ← NÉGATIF!

╔══════════════════════════════════════════════════════════════════════════════╗
║                         ROLLBACK SI PROBLÈME                                  ║
╚══════════════════════════════════════════════════════════════════════════════╝

Si le fix cause des problèmes:

1. ARRÊTER LE BOT
   Get-Process python | Stop-Process -Force

2. RESTAURER LE BACKUP
   Copy-Item "ARCHIVE/launch_production_CLEAN_v2_smart_sltp_BACKUP_02dec2025.py" `
             "LAUNCH/launch_production_CLEAN_v2.py" -Force

3. RELANCER
   python LAUNCH/launch_production_CLEAN_v2.py

╔══════════════════════════════════════════════════════════════════════════════╗
║                            SUPPORT                                            ║
╚══════════════════════════════════════════════════════════════════════════════╝

En cas de problème:
- Vérifier logs: logs_advanced/bot_production_*.log
- Vérifier erreurs: logs_advanced/bot_ERROR_*.log
- Contacter Claude avec les logs des 50 dernières lignes

"""

if __name__ == "__main__":
    print(INSTRUCTIONS)
    print("\n" + "="*80)
    print("CODE À REMPLACER:")
    print("="*80)
    print(OLD_CODE)
    print("\n" + "="*80)
    print("NOUVEAU CODE:")
    print("="*80)
    print(NEW_CODE)



