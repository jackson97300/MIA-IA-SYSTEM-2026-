#!/usr/bin/env python3
"""
Analyse des trades Power Hour du 8 decembre 2025
Comprendre POURQUOI les LONG ont ete pris alors que le marche descendait
"""

import json
from datetime import datetime
from pathlib import Path

# Fichier snapshot ES du 8 decembre
file_path = Path("D:/MIA_IA_system/DATA_SIERRA_CHART/DATA_2025/DECEMBRE/20251208/CHART_3/ML_READY/ml_ESZ25_FUT_CME_3.jsonl")

# Heures des trades Power Hour (en timestamp approximatif)
# 20:38 Paris = ~19:38 UTC = timestamp autour de 1765221480000
# 21:16 Paris = ~20:16 UTC = timestamp autour de 1765223760000

# Les trades:
# 20:38:09 LONG @ 6846.13
# 21:16:29 LONG @ 6845.88

print("=" * 70)
print("ANALYSE POWER HOUR - 8 DECEMBRE 2025")
print("=" * 70)

# Charger les snapshots et chercher ceux proches des heures de trade
print("\nChargement des snapshots...")

snapshots_power_hour = []
count = 0
target_prices = [6846.13, 6845.88]  # Prix des entries

with open(file_path, 'r', encoding='utf-8') as f:
    for line in f:
        if not line.strip():
            continue
        count += 1
        try:
            snap = json.loads(line)
            mid = snap.get('mid', 0)

            # Chercher les snapshots autour des prix d'entry
            if 6840 <= mid <= 6850:
                snapshots_power_hour.append(snap)
        except:
            pass

print(f"Total snapshots: {count}")
print(f"Snapshots dans zone 6840-6850: {len(snapshots_power_hour)}")

if not snapshots_power_hour:
    print("Aucun snapshot trouve dans la zone de prix!")
    exit(1)

# Prendre quelques snapshots representatifs
print("\n" + "=" * 70)
print("ANALYSE DES CONDITIONS AU MOMENT DES TRADES")
print("=" * 70)

# Analyser les derniers snapshots (ceux du Power Hour)
for i, snap in enumerate(snapshots_power_hour[-10:]):  # Derniers 10
    mid = snap.get('mid', 0)
    t_ms = snap.get('t_ms', 0)

    # Convertir timestamp
    try:
        dt = datetime.fromtimestamp(t_ms / 1000)
        time_str = dt.strftime("%H:%M:%S")
    except:
        time_str = "N/A"

    print(f"\n--- Snapshot #{i+1} | {time_str} | Mid: {mid:.2f} ---")

    # Donnees cles
    print(f"  volatility_regime: {snap.get('volatility_regime', 'N/A')}")
    print(f"  mia_bullish_score: {snap.get('mia_bullish_score', 'N/A')}")
    print(f"  position_in_range: {snap.get('position_in_range', 'N/A')}")

    # Structure
    structure = snap.get('structure', {})
    print(f"  IBH: {structure.get('ibh', 'N/A')} | IBL: {structure.get('ibl', 'N/A')}")

    # VWAP
    print(f"  VWAP: {snap.get('vwap', 'N/A')}")
    print(f"  d_vwap_ticks: {snap.get('d_vwap_ticks', 'N/A')}")

    # MenthorQ levels
    print(f"  HVL: {snap.get('hvl', 'N/A')}")
    print(f"  HVL_0DTE: {snap.get('hvl_0dte', 'N/A')}")
    print(f"  Put Support: {snap.get('put_support', 'N/A')}")
    print(f"  Call Resistance: {snap.get('call_resistance', 'N/A')}")

    # GEX levels
    gex_levels = [snap.get(f'gex_{i}', 0) for i in range(1, 11)]
    nearby_gex = [g for g in gex_levels if abs(g - mid) < 50]
    print(f"  GEX proches (<50 pts): {nearby_gex}")

    # Next Wall
    next_wall = snap.get('next_wall', {})
    print(f"  Next Wall: {next_wall.get('price', 'N/A')} ({next_wall.get('side', 'N/A')}) @ {next_wall.get('dist_ticks', 'N/A')}t")

    # OrderFlow
    print(f"  cum_delta_day: {snap.get('cum_delta_day', 'N/A')}")
    print(f"  cum_delta_session: {snap.get('cum_delta_session', 'N/A')}")
    print(f"  delta: {snap.get('delta', 'N/A')}")
    print(f"  level1_imbalance: {snap.get('level1_imbalance', 'N/A')}")

    # Interpretation
    vol_regime = snap.get('volatility_regime', 999)
    bull_score = snap.get('mia_bullish_score', 0)
    pos_range = snap.get('position_in_range', 50)

    is_range = vol_regime <= 1.5 and abs(bull_score) < 0.25

    if pos_range < 25:
        zone = "BOTTOM"
    elif pos_range > 75:
        zone = "TOP"
    else:
        zone = "MIDDLE"

    print(f"\n  >>> INTERPRETATION:")
    print(f"      Est un RANGE: {is_range}")
    print(f"      Zone: {zone} ({pos_range:.0f}%)")

    # Pourquoi LONG aurait ete autorise?
    if is_range and zone == "BOTTOM":
        print(f"      => LONG AUTORISE (FADE en bas du range)")
    elif not is_range and bull_score > 0:
        print(f"      => LONG AUTORISE (Tendance BULLISH)")
    elif not is_range and bull_score < 0:
        print(f"      => LONG DEVRAIT ETRE BLOQUE (Tendance BEARISH)")
    else:
        print(f"      => SITUATION AMBIGUE")

# Resume
print("\n" + "=" * 70)
print("RESUME DE L'ANALYSE")
print("=" * 70)

# Calculer stats sur les snapshots
if snapshots_power_hour:
    avg_bull_score = sum(s.get('mia_bullish_score', 0) for s in snapshots_power_hour) / len(snapshots_power_hour)
    avg_vol_regime = sum(s.get('volatility_regime', 0) for s in snapshots_power_hour) / len(snapshots_power_hour)
    avg_pos_range = sum(s.get('position_in_range', 0) for s in snapshots_power_hour) / len(snapshots_power_hour)

    print(f"\nMoyennes sur {len(snapshots_power_hour)} snapshots:")
    print(f"  mia_bullish_score moyen: {avg_bull_score:.3f}")
    print(f"  volatility_regime moyen: {avg_vol_regime:.2f}")
    print(f"  position_in_range moyen: {avg_pos_range:.1f}%")

    # Verdict
    print(f"\n>>> VERDICT:")
    if avg_bull_score < -0.1:
        print(f"    Le marche etait BEARISH (score: {avg_bull_score:.3f})")
        print(f"    Les LONG auraient DU etre BLOQUES!")
    elif avg_bull_score > 0.1:
        print(f"    Le marche etait BULLISH (score: {avg_bull_score:.3f})")
        print(f"    Les LONG etaient JUSTIFIES")
    else:
        print(f"    Le marche etait NEUTRE (score: {avg_bull_score:.3f})")

    if avg_pos_range < 30:
        print(f"    Position: BAS du range ({avg_pos_range:.0f}%)")
        print(f"    => LONG pouvait etre un FADE valide")
    elif avg_pos_range > 70:
        print(f"    Position: HAUT du range ({avg_pos_range:.0f}%)")
        print(f"    => LONG au TOP = ERREUR!")

