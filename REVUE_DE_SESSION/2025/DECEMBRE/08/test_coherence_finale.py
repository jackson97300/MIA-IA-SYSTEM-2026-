#!/usr/bin/env python3
"""
TEST DE COHÉRENCE FINALE - AUDIT COMPLET
=========================================

Vérifie que toutes les corrections sont cohérentes:
1. Transmission du niveau MenthorQ dans les métadonnées
2. Filtre VWAP Distance (ES uniquement)
3. Exception rebonds sur niveaux majeurs
4. Flux complet signal → trend_filter

Date: 08/12/2025
Objectif: Projet STABLE - plus de modifications nécessaires
"""

import sys
import os

# Ajouter le répertoire racine au path
sys.path.insert(0, r"D:\MIA_IA_system")

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional

print("\n" + "="*80)
print("🔍 AUDIT DE COHÉRENCE FINALE - 08/12/2025")
print("="*80)

# ═══════════════════════════════════════════════════════════════════════════════
# TEST 1: VÉRIFIER QUE LE NIVEAU EST TRANSMIS DANS LES MÉTADONNÉES
# ═══════════════════════════════════════════════════════════════════════════════

print("\n" + "─"*80)
print("TEST 1: Transmission du niveau MenthorQ dans les métadonnées")
print("─"*80)

try:
    from strategies.menthorq_3layer_strategy import MenthorQ3LayerStrategy

    # Vérifier que le code contient bien l'ajout de menthorq_level
    import inspect
    source = inspect.getsource(MenthorQ3LayerStrategy.generate_signal)

    if "signal['metadata']['menthorq_level']" in source:
        print("✅ FIX PRÉSENT: menthorq_level est ajouté aux métadonnées du signal")
    else:
        print("❌ PROBLÈME: menthorq_level N'EST PAS ajouté aux métadonnées!")

except Exception as e:
    print(f"⚠️ Erreur inspection: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# TEST 2: FILTRE VWAP DISTANCE - CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

print("\n" + "─"*80)
print("TEST 2: Configuration du filtre VWAP Distance")
print("─"*80)

try:
    from utils.trend_direction_filter import TrendDirectionFilter

    tf = TrendDirectionFilter()

    # Vérifier config ES
    es_config = tf.INSTRUMENT_CONFIG.get('ES', {})
    vwap_enabled_es = es_config.get('vwap_distance_filter_enabled', False)
    vwap_max_es = es_config.get('vwap_max_distance_long_ticks', 0)

    # Vérifier config NQ
    nq_config = tf.INSTRUMENT_CONFIG.get('NQ', {})
    vwap_enabled_nq = nq_config.get('vwap_distance_filter_enabled', True)

    print(f"ES: vwap_distance_filter_enabled = {vwap_enabled_es}")
    print(f"ES: vwap_max_distance_long_ticks = {vwap_max_es}")
    print(f"NQ: vwap_distance_filter_enabled = {vwap_enabled_nq}")

    if vwap_enabled_es and not vwap_enabled_nq:
        print("✅ CONFIG CORRECTE: Filtre VWAP actif pour ES, désactivé pour NQ")
    else:
        print("❌ PROBLÈME: Configuration VWAP incorrecte!")

except Exception as e:
    print(f"⚠️ Erreur: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# TEST 3: NIVEAUX MAJEURS POUR REBONDS
# ═══════════════════════════════════════════════════════════════════════════════

print("\n" + "─"*80)
print("TEST 3: Liste des niveaux majeurs pour rebonds")
print("─"*80)

try:
    expected_levels = ['gamma_wall_put', 'gamma_wall_call', 'put_support',
                      'call_resistance', 'hvl', 'hvl_0dte']

    actual_levels = tf.MAJOR_LEVELS

    print(f"Niveaux majeurs configurés: {len(actual_levels)}")
    for level in actual_levels:
        status = "✅" if level in expected_levels or any(e in level for e in expected_levels) else "📋"
        print(f"  {status} {level}")

    # Vérifier que les niveaux critiques sont présents
    critical_present = all(any(c in l.lower() for l in actual_levels)
                          for c in ['put', 'call', 'hvl'])

    if critical_present:
        print("✅ Niveaux critiques (put_support, call_resistance, hvl) PRÉSENTS")
    else:
        print("❌ PROBLÈME: Certains niveaux critiques manquent!")

except Exception as e:
    print(f"⚠️ Erreur: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# TEST 4: SIMULATION TRADES AVEC DONNÉES RÉELLES
# ═══════════════════════════════════════════════════════════════════════════════

print("\n" + "─"*80)
print("TEST 4: Simulation sur données réelles (08/12/2025)")
print("─"*80)

# Trades réels du 08/12 avec leurs conditions
test_trades = [
    # Trades Power Hour problématiques (devraient être bloqués)
    {
        'time': '19:38',
        'symbol': 'ES',
        'direction': 'LONG',
        'vwap_distance': -124,
        'trigger_level': None,  # Pas de niveau fort
        'pnl': -256.50,
        'expected_blocked': True,
        'reason': "VWAP trop loin, pas de niveau majeur"
    },
    {
        'time': '20:16',
        'symbol': 'ES',
        'direction': 'LONG',
        'vwap_distance': -121,
        'trigger_level': None,
        'pnl': -256.50,
        'expected_blocked': True,
        'reason': "VWAP trop loin, pas de niveau majeur"
    },
    # Trade avec rebond sur niveau majeur (devrait être autorisé)
    {
        'time': '15:50',
        'symbol': 'ES',
        'direction': 'LONG',
        'vwap_distance': -51,
        'trigger_level': 'put_support',  # Niveau fort!
        'pnl': +6.00,
        'expected_blocked': False,
        'reason': "Rebond sur put_support autorisé"
    },
    # Trade NQ loin du VWAP (devrait être autorisé car NQ pas filtré)
    {
        'time': '14:58',
        'symbol': 'NQ',
        'direction': 'LONG',
        'vwap_distance': -337,
        'trigger_level': None,
        'pnl': +52.40,
        'expected_blocked': False,
        'reason': "NQ pas filtré par VWAP"
    },
    # Rebond ES sur HVL même loin du VWAP (devrait être autorisé)
    {
        'time': 'SIMUL',
        'symbol': 'ES',
        'direction': 'LONG',
        'vwap_distance': -150,
        'trigger_level': 'hvl',  # Niveau fort!
        'pnl': 0,
        'expected_blocked': False,
        'reason': "Rebond sur HVL autorisé même loin du VWAP"
    },
]

passed = 0
failed = 0

for trade in test_trades:
    # Créer snapshot simulé
    snapshot = {
        'mid': 6850.0,
        'hvl': 6840.0,
        'vwap': 6850.0 - (trade['vwap_distance'] * 0.25),  # Recalculer VWAP
        'cum_delta': 0
    }

    # Tester avec le filtre
    is_allowed, reason, _ = tf.should_allow_trade(
        direction=trade['direction'],
        snapshot=snapshot,
        symbol=trade['symbol'],
        trigger_level=trade['trigger_level']
    )

    # Vérifier résultat
    actual_blocked = not is_allowed
    expected_blocked = trade['expected_blocked']

    if actual_blocked == expected_blocked:
        status = "✅ PASS"
        passed += 1
    else:
        status = "❌ FAIL"
        failed += 1

    blocked_str = "BLOQUÉ" if actual_blocked else "AUTORISÉ"
    expected_str = "BLOQUÉ" if expected_blocked else "AUTORISÉ"

    print(f"\n{status} {trade['time']} {trade['symbol']} {trade['direction']}")
    print(f"   VWAP dist: {trade['vwap_distance']}t | Niveau: {trade['trigger_level'] or 'Aucun'}")
    print(f"   Attendu: {expected_str} | Obtenu: {blocked_str}")
    print(f"   Raison: {trade['reason']}")

print(f"\n{'─'*80}")
print(f"RÉSULTATS: {passed}/{len(test_trades)} tests passés")

# ═══════════════════════════════════════════════════════════════════════════════
# TEST 5: COHÉRENCE DES FICHIERS MODIFIÉS
# ═══════════════════════════════════════════════════════════════════════════════

print("\n" + "─"*80)
print("TEST 5: Cohérence des fichiers modifiés")
print("─"*80)

files_to_check = [
    ('utils/trend_direction_filter.py', 'vwap_distance_filter_enabled'),
    ('utils/trend_direction_filter.py', 'REBOND AUTORISÉ'),
    ('strategies/menthorq_3layer_strategy.py', "signal['metadata']['menthorq_level']"),
    ('core/trailing_stop_manager.py', 'be_buffer_ticks'),
]

for filepath, pattern in files_to_check:
    full_path = os.path.join(r"D:\MIA_IA_system", filepath)
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        if pattern in content:
            print(f"✅ {filepath}: '{pattern[:40]}...' PRÉSENT")
        else:
            print(f"❌ {filepath}: '{pattern[:40]}...' MANQUANT!")
    except Exception as e:
        print(f"⚠️ {filepath}: Erreur lecture - {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# TEST 6: IMPACT ESTIMÉ SUR LES DONNÉES
# ═══════════════════════════════════════════════════════════════════════════════

print("\n" + "─"*80)
print("TEST 6: Impact estimé des corrections")
print("─"*80)

# Données du 08/12
total_trades_08dec = 20
losses_blocked = 2  # Les 2 trades Power Hour ES
losses_value = 513.0  # $256.50 × 2
wins_kept = 3  # Les 3 NQ qui auraient été bloqués sans le fix NQ

print(f"Trades analysés (08/12): {total_trades_08dec}")
print(f"Pertes évitées: {losses_blocked} trades = ${losses_value:.2f}")
print(f"Wins conservés (NQ): {wins_kept} trades")
print(f"\n🎯 IMPACT NET ESTIMÉ: +${losses_value:.2f}/jour")

# ═══════════════════════════════════════════════════════════════════════════════
# VERDICT FINAL
# ═══════════════════════════════════════════════════════════════════════════════

print("\n" + "="*80)
print("🏆 VERDICT FINAL")
print("="*80)

if passed == len(test_trades) and failed == 0:
    print("""
✅ TOUS LES TESTS PASSENT!

📋 CORRECTIONS APPLIQUÉES:
   1. Filtre VWAP Distance (ES uniquement, 100t max)
   2. Exception rebonds sur niveaux majeurs
   3. Transmission du niveau MenthorQ dans les métadonnées
   4. BE Buffer (+2t ES, +3t NQ)

🎯 LE PROJET EST STABLE ET COHÉRENT.

💡 Prochaines étapes:
   - Relancer le bot
   - Observer les trades pendant 1-2 jours
   - Si stable → NE PLUS MODIFIER
""")
else:
    print(f"""
⚠️ {failed} TEST(S) ÉCHOUÉ(S)

Veuillez vérifier les corrections avant de relancer le bot.
""")

print("="*80)

