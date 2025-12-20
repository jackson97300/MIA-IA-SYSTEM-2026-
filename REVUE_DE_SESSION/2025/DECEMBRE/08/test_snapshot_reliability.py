#!/usr/bin/env python3
"""
Test de fiabilite des donnees snapshot
Verifie si volatility_regime, mia_bullish_score, position_in_range sont fiables
"""

import json
import os
from pathlib import Path
from datetime import datetime

print("=" * 60)
print("AUDIT FIABILITE DES DONNEES SNAPSHOT")
print("=" * 60)

# Chercher les snapshots recents dans plusieurs endroits
found_files = []

# 1. Chercher dans snapshots/daily/
snapshots_daily = Path("D:/MIA_IA_system/snapshots/daily")
if snapshots_daily.exists():
    files = sorted(snapshots_daily.glob("*.json"), key=os.path.getmtime, reverse=True)[:10]
    found_files.extend(files)
    print(f"snapshots/daily: {len(files)} fichiers")

# 2. Chercher dans DATA_SIERRA_CHART
data_path = Path("D:/MIA_IA_system/DATA_SIERRA_CHART")
if data_path.exists():
    ml_ready_dirs = list(data_path.glob("**/ML_READY"))
    for ml_dir in ml_ready_dirs[:2]:
        files = sorted(ml_dir.glob("*.json"), key=os.path.getmtime, reverse=True)[:5]
        found_files.extend(files)
        print(f"{ml_dir}: {len(files)} fichiers")

print(f"\nTotal fichiers trouves: {len(found_files)}")

if not found_files:
    print("AUCUN FICHIER TROUVE!")
    exit(1)

# Analyser les snapshots
print("\n" + "=" * 60)
print("ANALYSE DES CHAMPS CLES")
print("=" * 60)

stats = {
    'total': 0,
    'volatility_regime_present': 0,
    'mia_bullish_score_present': 0,
    'position_in_range_present': 0,
    'structure_ibh_present': 0,
    'structure_ibl_present': 0,
}

samples = []

for jf in found_files[:20]:  # Max 20 fichiers
    try:
        with open(jf, 'r') as f:
            data = json.load(f)

        stats['total'] += 1

        # Verifier presence des champs
        vol_regime = data.get('volatility_regime')
        bullish_score = data.get('mia_bullish_score')
        pos_in_range = data.get('position_in_range')
        structure = data.get('structure', {})
        ibh = structure.get('ibh')
        ibl = structure.get('ibl')
        mid = data.get('mid', 0)

        if vol_regime is not None:
            stats['volatility_regime_present'] += 1
        if bullish_score is not None:
            stats['mia_bullish_score_present'] += 1
        if pos_in_range is not None:
            stats['position_in_range_present'] += 1
        if ibh is not None:
            stats['structure_ibh_present'] += 1
        if ibl is not None:
            stats['structure_ibl_present'] += 1

        # Garder un echantillon
        if len(samples) < 5:
            samples.append({
                'file': jf.name,
                'mid': mid,
                'vol_regime': vol_regime,
                'bullish_score': bullish_score,
                'pos_in_range': pos_in_range,
                'ibh': ibh,
                'ibl': ibl,
            })

    except Exception as e:
        print(f"Erreur {jf.name}: {e}")

# Afficher stats
print("\n--- STATISTIQUES PRESENCE ---")
total = stats['total']
print(f"Fichiers analyses: {total}")
print(f"volatility_regime: {stats['volatility_regime_present']}/{total} ({100*stats['volatility_regime_present']/total:.0f}%)")
print(f"mia_bullish_score: {stats['mia_bullish_score_present']}/{total} ({100*stats['mia_bullish_score_present']/total:.0f}%)")
print(f"position_in_range: {stats['position_in_range_present']}/{total} ({100*stats['position_in_range_present']/total:.0f}%)")
print(f"structure.ibh: {stats['structure_ibh_present']}/{total} ({100*stats['structure_ibh_present']/total:.0f}%)")
print(f"structure.ibl: {stats['structure_ibl_present']}/{total} ({100*stats['structure_ibl_present']/total:.0f}%)")

# Afficher echantillons
print("\n--- ECHANTILLONS ---")
for s in samples:
    print(f"\n{s['file']}:")
    print(f"  mid: {s['mid']}")
    print(f"  volatility_regime: {s['vol_regime']}")
    print(f"  mia_bullish_score: {s['bullish_score']}")
    print(f"  position_in_range: {s['pos_in_range']}")
    print(f"  ibh: {s['ibh']} / ibl: {s['ibl']}")

    # Interpretation
    if s['vol_regime'] is not None and s['bullish_score'] is not None:
        is_range = s['vol_regime'] <= 1.5 and abs(s['bullish_score']) < 0.25
        print(f"  -> RANGE: {is_range} (vol<1.5: {s['vol_regime'] <= 1.5 if s['vol_regime'] else 'N/A'}, neutral: {abs(s['bullish_score']) < 0.25 if s['bullish_score'] else 'N/A'})")

    if s['pos_in_range'] is not None:
        if s['pos_in_range'] < 25:
            zone = "BOTTOM"
        elif s['pos_in_range'] > 75:
            zone = "TOP"
        else:
            zone = "MIDDLE"
        print(f"  -> ZONE: {zone} ({s['pos_in_range']:.0f}%)")

# Verdict
print("\n" + "=" * 60)
print("VERDICT FIABILITE")
print("=" * 60)

vol_ok = stats['volatility_regime_present'] == total
bull_ok = stats['mia_bullish_score_present'] == total
pos_ok = stats['position_in_range_present'] == total
struct_ok = stats['structure_ibh_present'] == total and stats['structure_ibl_present'] == total

print(f"volatility_regime: {'OK' if vol_ok else 'MANQUANT'}")
print(f"mia_bullish_score: {'OK' if bull_ok else 'MANQUANT'}")
print(f"position_in_range: {'OK' if pos_ok else 'MANQUANT'}")
print(f"structure.ibh/ibl: {'OK' if struct_ok else 'MANQUANT'}")

if vol_ok and bull_ok and pos_ok:
    print("\n-> APPROCHE SIMPLE POSSIBLE!")
    print("   Les donnees sont presentes et utilisables.")
else:
    print("\n-> APPROCHE SIMPLE RISQUEE")
    print("   Certaines donnees manquent.")

