#!/usr/bin/env python3
"""
Analyse du snapshot REEL envoye par l'utilisateur (8 Dec 2025)
"""

# Snapshot ESZ25 du 8 decembre 2025 (extrait de la conversation)
snapshot = {
    "volatility_regime": 1.000000,
    "volatility_regime5": 2.000000,
    "volatility_regime_cont": 0.115833,
    "mia_bullish_score": -0.110554,
    "position_in_range": 20.725389,
    "structure": {
        "onh": 6889.13,
        "onl": 6888.63,
        "ibh": 6885.88,
        "ibl": 6866.63,
    },
    "mid": 6866.88,
    "vwap": 6886.82,
    "d_vwap_ticks": -79.789063,
    "atr": 2.39,
}

print("=" * 60)
print("ANALYSE DU SNAPSHOT REEL (ES - 8 Dec 2025)")
print("=" * 60)

# Presence des champs
print("\n--- PRESENCE DES CHAMPS ---")
fields = [
    ("volatility_regime", snapshot.get("volatility_regime")),
    ("mia_bullish_score", snapshot.get("mia_bullish_score")),
    ("position_in_range", snapshot.get("position_in_range")),
    ("structure.ibh", snapshot["structure"]["ibh"]),
    ("structure.ibl", snapshot["structure"]["ibl"]),
    ("d_vwap_ticks", snapshot.get("d_vwap_ticks")),
    ("atr", snapshot.get("atr")),
]

for name, val in fields:
    status = "OK" if val is not None else "MANQUANT"
    print(f"  {name}: {val} - {status}")

# Interpretation
print("\n--- INTERPRETATION RANGE ---")
vol = snapshot["volatility_regime"]
bull = snapshot["mia_bullish_score"]
pos = snapshot["position_in_range"]
ibh = snapshot["structure"]["ibh"]
ibl = snapshot["structure"]["ibl"]
mid = snapshot["mid"]

# Critere Range: volatility_regime <= 1.5 AND abs(bullish_score) < 0.25
is_low_vol = vol <= 1.5
is_neutral = abs(bull) < 0.25
is_range = is_low_vol and is_neutral

print(f"  volatility_regime <= 1.5: {is_low_vol} (valeur: {vol})")
print(f"  abs(bullish_score) < 0.25: {is_neutral} (valeur: {abs(bull):.3f})")
print(f"  => EST UN RANGE: {is_range}")

# Zone dans le range (IB range)
ib_range = ibh - ibl
print(f"\n--- ZONE DANS LE RANGE (Initial Balance) ---")
print(f"  IBH: {ibh}")
print(f"  IBL: {ibl}")
print(f"  IB Range: {ib_range:.2f} points ({ib_range/0.25:.0f} ticks)")
print(f"  Mid: {mid}")

# Position par rapport a IB
if ib_range > 0:
    pos_in_ib = ((mid - ibl) / ib_range) * 100
    print(f"  Position dans IB: {pos_in_ib:.1f}%")
    if pos_in_ib < 25:
        zone_ib = "BOTTOM (LONG autorise)"
    elif pos_in_ib > 75:
        zone_ib = "TOP (SHORT autorise)"
    else:
        zone_ib = "MIDDLE (pas de trade)"
    print(f"  => ZONE via IB: {zone_ib}")

# Comparer avec position_in_range du snapshot
print(f"\n--- POSITION_IN_RANGE (snapshot) ---")
print(f"  position_in_range: {pos:.1f}%")
if pos < 25:
    zone_snap = "BOTTOM"
elif pos > 75:
    zone_snap = "TOP"
else:
    zone_snap = "MIDDLE"
print(f"  => ZONE via snapshot: {zone_snap}")

# VWAP distance
print(f"\n--- VWAP DISTANCE ---")
d_vwap = snapshot["d_vwap_ticks"]
print(f"  d_vwap_ticks: {d_vwap:.1f}t")
if d_vwap < -50:
    print(f"  => Prix TRES EN-DESSOUS du VWAP (potentiel rebond)")
elif d_vwap > 50:
    print(f"  => Prix TRES AU-DESSUS du VWAP (potentiel rejet)")
else:
    print(f"  => Prix PROCHE du VWAP")

# VERDICT FINAL
print("\n" + "=" * 60)
print("VERDICT FINAL")
print("=" * 60)

all_present = all([
    snapshot.get("volatility_regime") is not None,
    snapshot.get("mia_bullish_score") is not None,
    snapshot.get("position_in_range") is not None,
    snapshot["structure"].get("ibh") is not None,
    snapshot["structure"].get("ibl") is not None,
])

print(f"\n1. TOUTES LES DONNEES PRESENTES: {all_present}")

print(f"\n2. COHERENCE DES DONNEES:")
print(f"   - position_in_range ({pos:.0f}%) vs calcul IB ({pos_in_ib:.0f}%)")
coherent = abs(pos - pos_in_ib) < 30  # Tolerance 30%
print(f"   - Ecart: {abs(pos - pos_in_ib):.0f}% - {'COHERENT' if coherent else 'DIVERGENT'}")

print(f"\n3. RECOMMANDATION:")
if all_present:
    print("   APPROCHE SIMPLE POSSIBLE!")
    print("   Les donnees volatility_regime, mia_bullish_score, position_in_range")
    print("   sont presentes et utilisables directement depuis le snapshot.")
    print("")
    print("   => Pas besoin de 900 lignes de code pour recalculer!")
else:
    print("   APPROCHE SIMPLE RISQUEE")
    print("   Certaines donnees manquent.")

print("\n4. EXEMPLE DE DETECTION SIMPLE:")
print("   ```python")
print("   # Detection Range en 5 lignes")
print("   is_range = (")
print("       snapshot['volatility_regime'] <= 1.5 and")
print("       abs(snapshot['mia_bullish_score']) < 0.25")
print("   )")
print("   ")
print("   # Position dans le range")
print("   pos = snapshot['position_in_range']")
print("   if pos < 25: zone = 'BOTTOM'  # LONG")
print("   elif pos > 75: zone = 'TOP'   # SHORT")
print("   else: zone = 'MIDDLE'         # No trade")
print("   ```")

