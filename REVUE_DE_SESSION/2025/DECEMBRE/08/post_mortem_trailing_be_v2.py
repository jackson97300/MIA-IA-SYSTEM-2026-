#!/usr/bin/env python3
"""
POST-MORTEM V2: Trailing Stop & Break-Even Analysis
====================================================

Extraction correcte des MFE/MAE depuis les logs.

Date: 08/12/2025
"""

import os
import re
from dataclasses import dataclass
from typing import List, Dict, Tuple
from collections import defaultdict

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

LOGS_DIR = r"D:\MIA_IA_system\logs"
TICK_VALUES = {'ES': 12.50, 'NQ': 5.00, 'RTY': 5.00}
CURRENT_SL = {'ES': 22, 'NQ': 25, 'RTY': 20}
CURRENT_TP = {'ES': 30, 'NQ': 35, 'RTY': 25}

# ═══════════════════════════════════════════════════════════════════════════════
# DATA EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class TradeData:
    symbol: str
    exit_reason: str
    pnl: float
    mfe: float
    mae: float

    @property
    def pnl_ticks(self) -> float:
        return self.pnl / TICK_VALUES.get(self.symbol, 12.5)

    @property
    def mfe_ticks(self) -> float:
        return self.mfe / TICK_VALUES.get(self.symbol, 12.5)

    @property
    def mae_ticks(self) -> float:
        return abs(self.mae) / TICK_VALUES.get(self.symbol, 12.5)

def extract_trades_from_logs() -> List[TradeData]:
    """Extrait les trades depuis les logs avec MFE/MAE"""

    trades = []

    # Pattern: Trade fermé notifié (SYMBOL EXIT $PNL) [MFE: +VALUE, MAE: VALUE]
    pattern = re.compile(
        r'Trade ferm.*\((\w+)\s+(SL|TP|BE)\s+Hit\s+\$([+-]?\d+\.?\d*)\).*'
        r'\[MFE:\s*([+-]?\d+\.?\d*),\s*MAE:\s*([+-]?\d+\.?\d*)\]',
        re.IGNORECASE
    )

    # Lire les logs récents
    import glob
    log_files = sorted(glob.glob(os.path.join(LOGS_DIR, "__main___202512*.log")))[-3:]

    for log_file in log_files:
        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            matches = pattern.findall(content)

            for match in matches:
                symbol_raw, exit_type, pnl, mfe, mae = match

                # Normaliser symbole
                if 'ES' in symbol_raw.upper():
                    symbol = 'ES'
                elif 'NQ' in symbol_raw.upper():
                    symbol = 'NQ'
                elif 'RTY' in symbol_raw.upper():
                    symbol = 'RTY'
                else:
                    continue

                trades.append(TradeData(
                    symbol=symbol,
                    exit_reason=exit_type,
                    pnl=float(pnl),
                    mfe=float(mfe),
                    mae=float(mae)
                ))

        except Exception as e:
            print(f"[WARN] Erreur lecture {log_file}: {e}")

    return trades

# ═══════════════════════════════════════════════════════════════════════════════
# SIMULATION
# ═══════════════════════════════════════════════════════════════════════════════

def simulate_without_be(trade: TradeData) -> Tuple[float, str]:
    """Simule le trade SANS BE ni trailing - SL/TP purs"""

    symbol = trade.symbol
    tick_value = TICK_VALUES[symbol]
    sl_ticks = CURRENT_SL[symbol]
    tp_ticks = CURRENT_TP[symbol]

    mfe_ticks = trade.mfe_ticks
    mae_ticks = trade.mae_ticks

    # TP touché?
    if mfe_ticks >= tp_ticks:
        return tp_ticks * tick_value, "TP"

    # SL touché?
    if mae_ticks >= sl_ticks:
        return -sl_ticks * tick_value, "SL"

    # Ni l'un ni l'autre - utiliser résultat réel
    return trade.pnl, "ACTUAL"

def simulate_with_be(trade: TradeData, be_trigger: int = 8, be_offset: int = 2) -> Tuple[float, str]:
    """Simule le trade AVEC BE mais sans trailing"""

    symbol = trade.symbol
    tick_value = TICK_VALUES[symbol]
    sl_ticks = CURRENT_SL[symbol]
    tp_ticks = CURRENT_TP[symbol]

    mfe_ticks = trade.mfe_ticks
    mae_ticks = trade.mae_ticks

    # TP touché?
    if mfe_ticks >= tp_ticks:
        return tp_ticks * tick_value, "TP"

    # BE atteint puis retracé?
    if mfe_ticks >= be_trigger:
        # Le prix a atteint le BE trigger
        if trade.pnl <= be_offset * tick_value:
            # Le prix est revenu sous le BE - sortie à BE+offset
            return be_offset * tick_value, "BE"
        else:
            # Trade encore gagnant
            return trade.pnl, "WIN"

    # Pas de BE atteint - SL normal
    if mae_ticks >= sl_ticks:
        return -sl_ticks * tick_value, "SL"

    return trade.pnl, "ACTUAL"

def simulate_with_trailing(trade: TradeData,
                           levels: List[Tuple[int, int]] = None) -> Tuple[float, str]:
    """Simule le trade AVEC trailing progressif"""

    if levels is None:
        levels = [(8, 2), (10, 4), (12, 6), (15, 8), (20, 12)]

    symbol = trade.symbol
    tick_value = TICK_VALUES[symbol]
    sl_ticks = CURRENT_SL[symbol]
    tp_ticks = CURRENT_TP[symbol]

    mfe_ticks = trade.mfe_ticks
    mae_ticks = trade.mae_ticks

    # TP touché?
    if mfe_ticks >= tp_ticks:
        return tp_ticks * tick_value, "TP"

    # Trouver le meilleur niveau de trailing atteint
    best_offset = 0
    for trigger, offset in levels:
        if mfe_ticks >= trigger:
            best_offset = offset

    if best_offset > 0:
        # Trailing activé - le prix est revenu toucher le trailing SL
        if trade.pnl < best_offset * tick_value:
            # Sortie au trailing SL
            return best_offset * tick_value, f"TRAIL_{best_offset}t"
        else:
            # Trade encore au-dessus du trailing
            return trade.pnl, "WIN"

    # Pas de trailing atteint - SL normal
    if mae_ticks >= sl_ticks:
        return -sl_ticks * tick_value, "SL"

    return trade.pnl, "ACTUAL"

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n" + "="*80)
    print("POST-MORTEM V2: TRAILING STOP & BREAK-EVEN ANALYSIS")
    print("="*80)

    # Extraire trades
    print("\n[1/3] Extraction des trades depuis les logs...")
    trades = extract_trades_from_logs()
    print(f"      {len(trades)} trades avec MFE/MAE trouvés")

    if len(trades) < 5:
        print("\n[WARN] Pas assez de trades!")
        exit()

    # Séparer par symbole
    es_trades = [t for t in trades if t.symbol == 'ES']
    nq_trades = [t for t in trades if t.symbol == 'NQ']

    print(f"      ES: {len(es_trades)} trades")
    print(f"      NQ: {len(nq_trades)} trades")

    # Analyse par symbole
    print("\n" + "="*80)
    print("[2/3] ANALYSE PAR SYMBOLE:")
    print("="*80)

    for symbol, symbol_trades in [('ES', es_trades), ('NQ', nq_trades)]:
        if not symbol_trades:
            continue

        print(f"\n{'─'*70}")
        print(f"  {symbol} - {len(symbol_trades)} TRADES")
        print(f"{'─'*70}")

        # Stats de base
        total_pnl = sum(t.pnl for t in symbol_trades)
        total_mfe = sum(t.mfe for t in symbol_trades)
        wins = sum(1 for t in symbol_trades if t.pnl > 0)
        losses = len(symbol_trades) - wins

        print(f"  P&L Réel: ${total_pnl:+.2f}")
        print(f"  MFE Total: ${total_mfe:.2f} (potentiel max)")
        print(f"  Capture Rate: {(total_pnl/total_mfe*100) if total_mfe > 0 else 0:.1f}%")
        print(f"  Wins: {wins} | Losses: {losses} | WR: {wins/len(symbol_trades)*100:.1f}%")

        # Simulations
        print(f"\n  COMPARAISON DES SCÉNARIOS:")
        print(f"  {'-'*60}")

        scenarios = {
            'SANS_BE': {'pnl': 0, 'wins': 0},
            'AVEC_BE': {'pnl': 0, 'wins': 0},
            'TRAILING': {'pnl': 0, 'wins': 0},
            'RÉEL': {'pnl': total_pnl, 'wins': wins}
        }

        for trade in symbol_trades:
            # Sans BE
            pnl1, _ = simulate_without_be(trade)
            scenarios['SANS_BE']['pnl'] += pnl1
            if pnl1 > 0:
                scenarios['SANS_BE']['wins'] += 1

            # Avec BE
            pnl2, _ = simulate_with_be(trade)
            scenarios['AVEC_BE']['pnl'] += pnl2
            if pnl2 > 0:
                scenarios['AVEC_BE']['wins'] += 1

            # Trailing
            pnl3, _ = simulate_with_trailing(trade)
            scenarios['TRAILING']['pnl'] += pnl3
            if pnl3 > 0:
                scenarios['TRAILING']['wins'] += 1

        # Afficher
        print(f"  {'Scénario':<15} {'P&L':>12} {'Wins':>8} {'vs Réel':>12}")
        print(f"  {'-'*50}")

        for name, data in scenarios.items():
            diff = data['pnl'] - scenarios['RÉEL']['pnl']
            marker = "🏆" if data['pnl'] == max(s['pnl'] for s in scenarios.values()) else "  "
            print(f"{marker} {name:<15} ${data['pnl']:>+10.2f} {data['wins']:>8} {diff:>+10.2f}$")

        # Analyse détaillée
        print(f"\n  ANALYSE DÉTAILLÉE:")
        print(f"  {'-'*60}")

        # Trades sauvés par BE
        be_saves = []
        be_costs = []

        for trade in symbol_trades:
            pnl_sans_be, _ = simulate_without_be(trade)
            pnl_avec_be, reason = simulate_with_be(trade)

            if pnl_avec_be > pnl_sans_be:
                be_saves.append((trade, pnl_avec_be - pnl_sans_be))
            elif pnl_avec_be < pnl_sans_be:
                be_costs.append((trade, pnl_sans_be - pnl_avec_be))

        if be_saves:
            total_saved = sum(s[1] for s in be_saves)
            print(f"  ✅ BE a SAUVÉ {len(be_saves)} trades = +${total_saved:.2f}")
            for t, saved in be_saves[:3]:
                print(f"     - MFE: {t.mfe_ticks:.0f}t, MAE: {t.mae_ticks:.0f}t → Sauvé ${saved:.2f}")

        if be_costs:
            total_cost = sum(c[1] for c in be_costs)
            print(f"  ❌ BE a COÛTÉ sur {len(be_costs)} trades = -${total_cost:.2f}")
            for t, cost in be_costs[:3]:
                print(f"     - MFE: {t.mfe_ticks:.0f}t, MAE: {t.mae_ticks:.0f}t → Coûté ${cost:.2f}")

    # Verdict final
    print("\n" + "="*80)
    print("[3/3] VERDICT FINAL:")
    print("="*80)

    # Calculer impact global
    total_sans_be = sum(simulate_without_be(t)[0] for t in trades)
    total_avec_be = sum(simulate_with_be(t)[0] for t in trades)
    total_trailing = sum(simulate_with_trailing(t)[0] for t in trades)
    total_reel = sum(t.pnl for t in trades)

    print(f"\n  RÉSUMÉ GLOBAL ({len(trades)} trades):")
    print(f"  {'─'*50}")
    print(f"  Sans BE/Trailing: ${total_sans_be:+.2f}")
    print(f"  Avec BE seul:     ${total_avec_be:+.2f}")
    print(f"  Avec Trailing:    ${total_trailing:+.2f}")
    print(f"  Résultat Réel:    ${total_reel:+.2f}")

    impact_be = total_avec_be - total_sans_be
    impact_trail = total_trailing - total_sans_be

    print(f"\n  IMPACT:")
    print(f"  {'─'*50}")

    if impact_be > 0:
        print(f"  ✅ BE = +${impact_be:.2f} (POSITIF)")
    elif impact_be < 0:
        print(f"  ❌ BE = ${impact_be:.2f} (NÉGATIF)")
    else:
        print(f"  ⚠️ BE = ${impact_be:.2f} (NEUTRE)")

    if impact_trail > impact_be:
        print(f"  ✅ Trailing améliore de +${impact_trail - impact_be:.2f} vs BE seul")
    else:
        print(f"  ⚠️ Trailing n'améliore pas vs BE seul")

    print("\n  RECOMMANDATION:")
    print(f"  {'─'*50}")

    if impact_be > 50:
        print(f"  ✅ GARDER LE BE - Sauve ${impact_be:.0f}")
    elif impact_be < -50:
        print(f"  ❌ DÉSACTIVER LE BE pour {list(set(t.symbol for t in trades))}")
    else:
        print(f"  ⚠️ BE marginal - Garder par sécurité")

    if impact_trail > impact_be + 30:
        print(f"  ✅ GARDER LE TRAILING AGRESSIF")

    print("\n" + "="*80)

