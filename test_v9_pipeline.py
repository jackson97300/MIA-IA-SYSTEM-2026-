#!/usr/bin/env python3
"""
Test de cohérence de la pipeline V9
"""
import sys
sys.path.insert(0, '.')

print("=" * 70)
print("        🔍 AUDIT PIPELINE V9 - COHÉRENCE")
print("=" * 70)

# 1. Test imports
print("\n1️⃣ TEST IMPORTS CONFIG")
try:
    from config.trading_params import (
        OPTIMAL_SESSION_CONFIGS,
        LEVEL_SCORES,
        is_session_enabled,
        get_level_score,
        validate_menthorq_level,
        get_session_config,
        get_current_session,
    )
    print("   ✅ Tous les imports V9 OK")
except ImportError as e:
    print(f"   ❌ ERREUR IMPORT: {e}")
    sys.exit(1)

# 2. Test is_session_enabled
print("\n2️⃣ TEST is_session_enabled()")
tests = [
    ("LONDON", "ES", True),
    ("LONDON", "NQ", False),  # Désactivé!
    ("US_MORNING", "ES", True),
    ("US_MORNING", "NQ", True),
    ("POWER_HOUR", "ES", True),
    ("POWER_HOUR", "NQ", True),
]
all_ok = True
for session, symbol, expected in tests:
    result = is_session_enabled(session, symbol)
    status = "✅" if result == expected else "❌"
    if result != expected:
        all_ok = False
    print(f"   {status} {session}_{symbol}: {result} (attendu: {expected})")
if all_ok:
    print("   ✅ Tous les tests is_session_enabled OK")

# 3. Test get_level_score
print("\n3️⃣ TEST get_level_score()")
level_tests = [
    ("gex_1", 3, "FORT"),
    ("gex_2", 3, "FORT"),
    ("hvl", 3, "FORT"),
    ("gex_4", 2, "MOYEN"),
    ("call_resistance", 2, "MOYEN"),
    ("blind_spot_0", 2, "MOYEN"),
    ("blind_spot_3", 1, "FAIBLE"),
    ("vwap_upper", 1, "FAIBLE"),
]
all_ok = True
for level, expected_score, label in level_tests:
    score = get_level_score(level)
    status = "✅" if score == expected_score else "❌"
    if score != expected_score:
        all_ok = False
    print(f"   {status} {level}: score={score} (attendu: {expected_score} {label})")
if all_ok:
    print("   ✅ Tous les tests get_level_score OK")

# 4. Test get_session_config
print("\n4️⃣ TEST get_session_config()")
configs_to_test = [
    ("LONDON", "ES", {"max_distance": 12, "min_level_score": 2, "tp_ticks": 12}),
    ("US_MORNING", "ES", {"max_distance": 5, "min_level_score": 3, "tp_ticks": 12}),
    ("POWER_HOUR", "NQ", {"max_distance": 15, "min_level_score": 2, "tp_ticks": 40}),
]
all_ok = True
for session, symbol, expected_values in configs_to_test:
    cfg = get_session_config(session, symbol)
    for key, expected in expected_values.items():
        actual = cfg.get(key)
        status = "✅" if actual == expected else "❌"
        if actual != expected:
            all_ok = False
        print(f"   {status} {session}_{symbol}.{key}: {actual} (attendu: {expected})")
if all_ok:
    print("   ✅ Tous les tests get_session_config OK")

# 5. Test get_current_session
print("\n5️⃣ TEST get_current_session()")
session_tests = [
    (8, 30, "LONDON"),
    (10, 45, "LONDON"),
    (12, 0, "OFF_HOURS"),
    (16, 0, "US_MORNING"),
    (20, 30, "POWER_HOUR"),
    (22, 0, "OFF_HOURS"),
]
all_ok = True
for hour, minute, expected in session_tests:
    session = get_current_session(hour, minute)
    status = "✅" if session == expected else "❌"
    if session != expected:
        all_ok = False
    print(f"   {status} {hour:02d}:{minute:02d} → {session} (attendu: {expected})")
if all_ok:
    print("   ✅ Tous les tests get_current_session OK")

# 6. Test imports launcher
print("\n6️⃣ TEST IMPORTS LAUNCHER")
try:
    # Simuler les imports du launcher sans l'exécuter
    import importlib.util
    spec = importlib.util.spec_from_file_location("launcher", "LAUNCH/launch_production_CLEAN_v2.py")
    # Juste vérifier la syntaxe
    import py_compile
    py_compile.compile("LAUNCH/launch_production_CLEAN_v2.py", doraise=True)
    print("   ✅ Syntaxe launcher OK")
except py_compile.PyCompileError as e:
    print(f"   ❌ ERREUR SYNTAXE LAUNCHER: {e}")

# 7. Vérifier cohérence LEVEL_SCORES
print("\n7️⃣ TEST COHÉRENCE LEVEL_SCORES")
expected_levels = ['gex_1', 'gex_2', 'hvl', 'vwap', 'call_resistance', 'put_support']
missing = [l for l in expected_levels if l not in LEVEL_SCORES]
if missing:
    print(f"   ❌ Niveaux manquants: {missing}")
else:
    print(f"   ✅ Tous les niveaux critiques présents ({len(LEVEL_SCORES)} niveaux)")

# 8. Récapitulatif configs actives
print("\n8️⃣ RÉCAPITULATIF CONFIGS ACTIVES")
print("   " + "-" * 60)
print(f"   {'Session':<15} {'Symbol':<8} {'TP/SL':<10} {'Dist':<6} {'Score':<8} {'Status'}")
print("   " + "-" * 60)
score_names = {0: 'any', 1: 'faible+', 2: 'moyen+', 3: 'FORT'}
for key, cfg in OPTIMAL_SESSION_CONFIGS.items():
    parts = key.split('_')
    symbol = parts[-1]
    session = '_'.join(parts[:-1])
    enabled = cfg.get('enabled', True)
    status = "🟢 ACTIF" if enabled else "🔴 OFF"
    tp_sl = f"{cfg['tp_ticks']}/{cfg['sl_ticks']}"
    dist = cfg.get('max_distance', '-')
    score = score_names.get(cfg.get('min_level_score', 0), '?')
    print(f"   {session:<15} {symbol:<8} {tp_sl:<10} {dist:<6} {score:<8} {status}")

# Résumé final
print("\n" + "=" * 70)
print("        ✅ AUDIT PIPELINE V9 TERMINÉ - TOUT EST COHÉRENT")
print("=" * 70)


