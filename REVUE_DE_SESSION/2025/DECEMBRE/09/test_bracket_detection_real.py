#!/usr/bin/env python3
"""
Test de detection de bracket sur les vraies donnees du 09/12/2025
Analyse du trade ES LONG @ 6861 pour determiner la meilleure solution
"""

import json
from datetime import datetime
from pathlib import Path

# Chemin vers les snapshots UNIFIES
UNIFIED_FILE = Path(r"D:\MIA_IA_system\DATA_SIERRA_CHART\DATA_2025\DECEMBRE\20251209\CHART_3\unified\chart_3_unified_ESZ25_FUT_CME_20251209.jsonl")

def load_snapshots_around_trade(target_time_str="12:42"):
    """Charge les snapshots autour du moment du trade"""
    snapshots = []

    print(f"Chargement depuis: {UNIFIED_FILE}")
    print(f"Taille: {UNIFIED_FILE.stat().st_size / 1024 / 1024:.1f} MB")

    # Parser le fichier JSONL
    with open(UNIFIED_FILE, 'r', encoding='utf-8') as f:
        line_count = 0
        for line in f:
            line_count += 1
            if line.strip():
                try:
                    data = json.loads(line.strip())
                    # Skip heartbeat messages
                    if data.get('summary', {}).get('heartbeat'):
                        continue

                    # Calculer mid depuis best_bid/best_ask ou close
                    best_bid = data.get('best_bid', 0)
                    best_ask = data.get('best_ask', 0)
                    close = data.get('close', 0)

                    if best_bid and best_ask:
                        mid = (best_bid + best_ask) / 2
                    elif close:
                        mid = close
                    else:
                        continue

                    data['mid'] = mid

                    # Convertir timestamp
                    t_ms = data.get('t_ms', 0)
                    if t_ms:
                        dt = datetime.fromtimestamp(t_ms / 1000)
                        data['_time'] = dt.strftime("%H:%M:%S")
                        data['_hour'] = dt.hour
                        data['_minute'] = dt.minute
                        snapshots.append(data)
                except Exception as e:
                    continue

    print(f"Lignes lues: {line_count}")
    print(f"Snapshots valides: {len(snapshots)}")

    return snapshots

def analyze_bracket_at_trade_time(snapshots, trade_time_hour=12, trade_time_minute=42):
    """Analyse le bracket au moment du trade"""

    # Filtrer les snapshots des 30 minutes avant le trade
    start_minute = trade_time_minute - 30
    start_hour = trade_time_hour
    if start_minute < 0:
        start_minute += 60
        start_hour -= 1

    filtered = []
    for s in snapshots:
        h = s.get('_hour', 0)
        m = s.get('_minute', 0)

        # Entre start_hour:start_minute et trade_time_hour:trade_time_minute
        if h == start_hour and m >= start_minute:
            filtered.append(s)
        elif h == trade_time_hour and m <= trade_time_minute:
            filtered.append(s)
        elif start_hour < trade_time_hour and h == start_hour:
            if m >= start_minute:
                filtered.append(s)

    if len(filtered) < 10:
        print(f"Pas assez de snapshots filtres: {len(filtered)}")
        # Prendre les derniers snapshots avant le trade
        before_trade = [s for s in snapshots
                       if s.get('_hour', 0) < trade_time_hour or
                       (s.get('_hour', 0) == trade_time_hour and s.get('_minute', 0) <= trade_time_minute)]
        filtered = before_trade[-100:] if len(before_trade) > 100 else before_trade
        print(f"Utilisation des {len(filtered)} derniers snapshots avant le trade")

    if not filtered:
        print("Aucun snapshot disponible!")
        return None

    # Extraire les prix
    prices = [s.get('mid', 0) for s in filtered if s.get('mid')]

    if not prices:
        print("Aucun prix valide")
        return None

    high = max(prices)
    low = min(prices)
    current = prices[-1]
    range_ticks = (high - low) / 0.25

    print(f"\n{'='*70}")
    print(f"ANALYSE BRACKET ES - {len(filtered)} snapshots (30 min avant trade)")
    print(f"Periode: {filtered[0].get('_time', '?')} -> {filtered[-1].get('_time', '?')}")
    print(f"{'='*70}")
    print(f"High: {high:.2f}")
    print(f"Low: {low:.2f}")
    print(f"Current: {current:.2f}")
    print(f"Range: {range_ticks:.0f} ticks ({high-low:.2f} pts)")

    # Position dans le range
    if high != low:
        position_pct = ((current - low) / (high - low)) * 100
    else:
        position_pct = 50

    print(f"Position dans le range: {position_pct:.1f}%")

    # Dernier snapshot pour les metriques
    last_snap = filtered[-1]

    print(f"\n--- METRIQUES DU SNAPSHOT AU MOMENT DU TRADE ---")
    print(f"Heure: {last_snap.get('_time', '?')}")
    print(f"Mid: {last_snap.get('mid', 0):.2f}")
    print(f"Volatility Regime: {last_snap.get('volatility_regime', 'N/A')}")
    print(f"MIA Bullish Score: {last_snap.get('mia_bullish_score', 'N/A')}")
    print(f"ATR: {last_snap.get('atr', 'N/A')}")
    print(f"ATR Ratio: {last_snap.get('atr_ratio', 'N/A')}")

    # Niveaux GEX
    print(f"\n--- NIVEAUX GEX ---")
    gex_keys = ['gex_1', 'gex_2', 'gex_3', 'gex_4', 'gex_5', 'hvl_0dte', 'hvl']
    for key in gex_keys:
        level = last_snap.get(key, 0)
        if level:
            dist = (level - current) / 0.25
            print(f"  {key}: {level:.2f} ({dist:+.0f}t du prix)")

    # Structure
    structure = last_snap.get('structure', {})
    if structure:
        print(f"\n--- STRUCTURE INTRADAY ---")
        print(f"  IBH: {structure.get('ibh', 'N/A')}")
        print(f"  IBL: {structure.get('ibl', 'N/A')}")
        print(f"  ONH: {structure.get('onh', 'N/A')}")
        print(f"  ONL: {structure.get('onl', 'N/A')}")

    # Detection bracket
    print(f"\n{'='*70}")
    print("CRITERES DE DETECTION BRACKET:")
    print(f"{'='*70}")

    vol_regime = last_snap.get('volatility_regime', 2)
    mia_score = last_snap.get('mia_bullish_score', 0)

    # Criteres
    is_range_valid = 12 <= range_ticks <= 60
    is_low_vol = vol_regime is not None and float(vol_regime) <= 1.5

    if mia_score is not None:
        if float(mia_score) > 0.25:
            bias = "BULLISH"
        elif float(mia_score) < -0.25:
            bias = "BEARISH"
        else:
            bias = "NEUTRAL"
    else:
        bias = "UNKNOWN"

    print(f"1. Taille range (12-60t): {range_ticks:.0f}t -> {'PASS' if is_range_valid else 'FAIL'}")
    print(f"2. Volatility regime (<=1.5): {vol_regime} -> {'PASS' if is_low_vol else 'FAIL'}")
    print(f"3. Bias (mia_bullish_score): {mia_score} -> {bias}")

    is_bracket = is_range_valid and is_low_vol

    # Zones
    if is_bracket:
        print(f"\n4. ZONES DU BRACKET:")
        bottom_zone = low + (high - low) * 0.25
        top_zone = low + (high - low) * 0.75
        middle_low = low + (high - low) * 0.40
        middle_high = low + (high - low) * 0.60

        print(f"   ZONE HAUTE (SHORT): >= {top_zone:.2f} (75%)")
        print(f"   ZONE MILIEU (NO TRADE): {middle_low:.2f} - {middle_high:.2f} (40-60%)")
        print(f"   ZONE BASSE (LONG): <= {bottom_zone:.2f} (25%)")

    # VERDICT
    print(f"\n{'='*70}")
    print("VERDICT:")
    print(f"{'='*70}")

    if is_bracket:
        print("*** BRACKET DETECTE! ***")

        if 40 <= position_pct <= 60:
            print(f"-> Position: {position_pct:.1f}% = MILIEU DU BRACKET")
            print("-> DECISION: NE PAS TRADER!")
            print("")
            print("TRADE LONG @ 6861.00 AURAIT DU ETRE BLOQUE!")
        elif position_pct < 25:
            if bias != "BEARISH":
                print(f"-> Position: {position_pct:.1f}% = BAS DU BRACKET")
                print("-> DECISION: LONG FADE AUTORISE")
            else:
                print(f"-> Position: {position_pct:.1f}% = BAS mais BIAS BEARISH")
                print("-> DECISION: PRUDENCE - Attendre confirmation")
        elif position_pct > 75:
            if bias != "BULLISH":
                print(f"-> Position: {position_pct:.1f}% = HAUT DU BRACKET")
                print("-> DECISION: SHORT FADE AUTORISE")
            else:
                print(f"-> Position: {position_pct:.1f}% = HAUT mais BIAS BULLISH")
                print("-> DECISION: PRUDENCE - Attendre confirmation")
        else:
            print(f"-> Position: {position_pct:.1f}% = ZONE NEUTRE")
            print("-> DECISION: ATTENDRE MEILLEURE ENTREE")
    else:
        print("PAS DE BRACKET CLAIR DETECTE")
        if not is_range_valid:
            print(f"   Raison: Range {range_ticks:.0f}t hors limites (12-60t)")
        if not is_low_vol:
            print(f"   Raison: Volatilite trop haute ({vol_regime})")

    # Meilleures options
    print(f"\n{'='*70}")
    print("MEILLEURES OPTIONS POUR CE SETUP:")
    print(f"{'='*70}")

    entry = 6861.00
    entry_pos = ((entry - low) / (high - low)) * 100 if high != low else 50

    print(f"\nTrade actuel: LONG @ {entry:.2f} ({entry_pos:.1f}% du range)")
    print(f"SL: 6855.38 | TP: 6869.50 | R:R: 1.5:1")

    if is_bracket:
        bottom_25 = low + (high - low) * 0.25
        top_75 = low + (high - low) * 0.75
        middle = (high + low) / 2

        print(f"\nOption 1 - LONG FADE (au bas du range):")
        print(f"  Entry: {bottom_25:.2f} ou moins")
        print(f"  SL: {low - 2*0.25:.2f} (sous le range, 2t buffer)")
        print(f"  TP: {middle:.2f} (milieu du range)")
        sl_dist = (bottom_25 - (low - 2*0.25)) / 0.25
        tp_dist = (middle - bottom_25) / 0.25
        rr = tp_dist / sl_dist if sl_dist > 0 else 0
        print(f"  R:R: {rr:.1f}:1")

        print(f"\nOption 2 - SHORT FADE (au haut du range):")
        print(f"  Entry: {top_75:.2f} ou plus")
        print(f"  SL: {high + 2*0.25:.2f} (au-dessus du range, 2t buffer)")
        print(f"  TP: {middle:.2f} (milieu du range)")
        sl_dist = ((high + 2*0.25) - top_75) / 0.25
        tp_dist = (top_75 - middle) / 0.25
        rr = tp_dist / sl_dist if sl_dist > 0 else 0
        print(f"  R:R: {rr:.1f}:1")

        print(f"\nOption 3 - NE PAS TRADER (attendre sortie du range)")
        print(f"  Breakout UP: > {high:.2f} -> LONG tendance")
        print(f"  Breakdown: < {low:.2f} -> SHORT tendance")

    return {
        'is_bracket': is_bracket,
        'range_ticks': range_ticks,
        'position_pct': position_pct,
        'bias': bias,
        'high': high,
        'low': low,
        'vol_regime': vol_regime,
        'mia_score': mia_score
    }

def main():
    print("="*70)
    print("ANALYSE BRACKET - TRADE ES LONG @ 6861.00 du 09/12/2025 12:42")
    print("="*70)

    if not UNIFIED_FILE.exists():
        print(f"Fichier non trouve: {UNIFIED_FILE}")
        return

    # Charger les snapshots
    snapshots = load_snapshots_around_trade()

    if not snapshots:
        print("Aucun snapshot charge!")
        return

    # Analyser au moment du trade (12:42)
    result = analyze_bracket_at_trade_time(snapshots, 12, 42)

    if result:
        print(f"\n{'='*70}")
        print("CONCLUSION FINALE:")
        print(f"{'='*70}")

        if result['is_bracket'] and 40 <= result['position_pct'] <= 60:
            print("\nLE TRADE AURAIT DU ETRE BLOQUE PAR LE FILTRE BRACKET!")
            print("-> Entry @ 6861.00 = milieu du range")
            print("-> Le MarketRegimeDetector doit etre ameliore pour detecter")
            print("   les brackets INTRADAY courts (< 1h), pas juste le range journalier.")
        else:
            print("\nLe setup etait acceptable selon les criteres actuels.")

if __name__ == "__main__":
    main()
