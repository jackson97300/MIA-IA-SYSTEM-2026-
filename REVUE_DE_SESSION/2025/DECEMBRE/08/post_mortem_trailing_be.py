#!/usr/bin/env python3
"""
POST-MORTEM: Trailing Stop & Break-Even Analysis
=================================================

Analyse HONNÊTE de l'impact réel du BE et Trailing sur ES et NQ.

Questions à répondre:
1. Le BE sauve-t-il vraiment des trades?
2. Le trailing capture-t-il assez de profit?
3. Faut-il garder ces mécanismes ou les supprimer?

Date: 08/12/2025
"""

import os
import json
import glob
import re
from dataclasses import dataclass
from typing import List, Dict, Tuple
from collections import defaultdict

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

LOGS_DIR = r"D:\MIA_IA_system\logs"
SNAPSHOTS_DIR = r"D:\MIA_IA_system\snapshots_trades\daily"

TICK_VALUES = {'ES': 12.50, 'NQ': 5.00, 'RTY': 5.00}
TICK_SIZES = {'ES': 0.25, 'NQ': 0.25, 'RTY': 0.10}

# SL/TP actuels (en ticks)
CURRENT_SL = {'ES': 22, 'NQ': 25, 'RTY': 20}
CURRENT_TP = {'ES': 30, 'NQ': 35, 'RTY': 25}

# ═══════════════════════════════════════════════════════════════════════════════
# DATA EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class TradeAnalysis:
    symbol: str
    entry_time: str
    pnl: float
    pnl_ticks: float
    mfe_ticks: float  # Max profit atteint
    mae_ticks: float  # Max perte atteinte
    exit_reason: str

    @property
    def mfe_dollars(self) -> float:
        return self.mfe_ticks * TICK_VALUES.get(self.symbol, 12.5)

    @property
    def mae_dollars(self) -> float:
        return self.mae_ticks * TICK_VALUES.get(self.symbol, 12.5)

    @property
    def capture_rate(self) -> float:
        """% du MFE capturé"""
        if self.mfe_ticks <= 0:
            return 0
        return (self.pnl_ticks / self.mfe_ticks) * 100 if self.pnl_ticks > 0 else 0

def extract_trades_from_snapshots() -> List[TradeAnalysis]:
    """Extrait les trades depuis les snapshots avec résultats"""

    trades = []

    # Chercher les fichiers de résultats
    result_files = glob.glob(os.path.join(SNAPSHOTS_DIR, "TRADE_*_final_result.json"))

    for filepath in result_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            result = data.get('result', {})
            entry = data.get('entry', {})

            symbol = entry.get('symbol', 'ES')
            if 'NQ' in symbol:
                symbol = 'NQ'
            elif 'ES' in symbol:
                symbol = 'ES'
            elif 'RTY' in symbol:
                symbol = 'RTY'
            else:
                continue

            tick_value = TICK_VALUES.get(symbol, 12.5)

            pnl = result.get('pnl', 0)
            mfe = result.get('mfe', 0)
            mae = result.get('mae', 0)
            exit_reason = result.get('exit_reason', 'unknown')

            # Convertir en ticks
            pnl_ticks = pnl / tick_value
            mfe_ticks = abs(mfe) / tick_value if mfe else 0
            mae_ticks = abs(mae) / tick_value if mae else 0

            # Extraire l'heure du filename
            filename = os.path.basename(filepath)
            time_match = re.search(r'TRADE_\d{8}_(\d{6})', filename)
            entry_time = time_match.group(1) if time_match else "000000"

            trades.append(TradeAnalysis(
                symbol=symbol,
                entry_time=entry_time,
                pnl=pnl,
                pnl_ticks=pnl_ticks,
                mfe_ticks=mfe_ticks,
                mae_ticks=mae_ticks,
                exit_reason=exit_reason
            ))

        except Exception as e:
            pass

    return trades

# ═══════════════════════════════════════════════════════════════════════════════
# SIMULATION SCENARIOS
# ═══════════════════════════════════════════════════════════════════════════════

def simulate_scenario(trade: TradeAnalysis, use_be: bool, use_trailing: bool,
                      be_trigger: int = 8, be_offset: int = 2,
                      trailing_levels: List[Tuple[int, int]] = None) -> Tuple[float, str]:
    """
    Simule un trade avec différentes configurations.

    Returns: (pnl_simulé, raison_sortie)
    """

    symbol = trade.symbol
    tick_value = TICK_VALUES.get(symbol, 12.5)
    sl_ticks = CURRENT_SL.get(symbol, 22)
    tp_ticks = CURRENT_TP.get(symbol, 30)
    mfe = trade.mfe_ticks
    mae = trade.mae_ticks

    # Scénario 1: SL touché avant tout
    if mae >= sl_ticks and mfe < be_trigger:
        return -sl_ticks * tick_value, "SL_FULL"

    # Scénario 2: TP touché
    if mfe >= tp_ticks:
        return tp_ticks * tick_value, "TP_HIT"

    # Scénario 3: BE/Trailing
    if use_be or use_trailing:
        # Trouver le meilleur niveau atteint
        best_sl_offset = 0

        if use_trailing and trailing_levels:
            for trigger, offset in trailing_levels:
                if mfe >= trigger:
                    best_sl_offset = offset
        elif use_be and mfe >= be_trigger:
            best_sl_offset = be_offset

        if best_sl_offset > 0:
            # Le trade a atteint un niveau de protection
            # Si le trade original était perdant, on sort au trailing
            if trade.pnl < 0:
                return best_sl_offset * tick_value, f"BE_SAVE_{best_sl_offset}t"
            else:
                # Trade gagnant - on a capturé quelque chose
                return trade.pnl, "TRAIL_WIN"

    # Scénario 4: Pas de protection, utiliser résultat réel
    if mae >= sl_ticks:
        return -sl_ticks * tick_value, "SL_FULL"

    return trade.pnl, "ACTUAL"

# ═══════════════════════════════════════════════════════════════════════════════
# ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

def analyze_by_symbol(trades: List[TradeAnalysis]) -> Dict:
    """Analyse détaillée par symbole"""

    analysis = defaultdict(lambda: {
        'count': 0,
        'wins': 0,
        'losses': 0,
        'total_pnl': 0,
        'total_mfe': 0,
        'total_mae': 0,
        'be_saves': 0,  # Trades sauvés par BE
        'tp_hits': 0,
        'sl_hits': 0,
        'mfe_captured': 0,
        'trades': []
    })

    for trade in trades:
        sym = trade.symbol
        analysis[sym]['count'] += 1
        analysis[sym]['total_pnl'] += trade.pnl
        analysis[sym]['total_mfe'] += trade.mfe_dollars
        analysis[sym]['total_mae'] += trade.mae_dollars
        analysis[sym]['trades'].append(trade)

        if trade.pnl > 0:
            analysis[sym]['wins'] += 1
            analysis[sym]['mfe_captured'] += trade.pnl
        else:
            analysis[sym]['losses'] += 1

        if 'TP' in trade.exit_reason.upper():
            analysis[sym]['tp_hits'] += 1
        elif 'SL' in trade.exit_reason.upper() or 'BE' in trade.exit_reason.upper():
            analysis[sym]['sl_hits'] += 1
            # Vérifier si c'était un BE save
            if trade.pnl > 0 and trade.mfe_ticks >= 8:
                analysis[sym]['be_saves'] += 1

    return dict(analysis)

def compare_scenarios(trades: List[TradeAnalysis], symbol: str) -> Dict:
    """Compare différents scénarios pour un symbole"""

    symbol_trades = [t for t in trades if t.symbol == symbol]

    # Trailing levels pour simulation
    trailing_aggressive = [(8, 2), (10, 4), (12, 6), (15, 8), (20, 12)]

    scenarios = {
        'SANS_BE_NI_TRAILING': {'pnl': 0, 'wins': 0, 'losses': 0, 'details': []},
        'BE_SEULEMENT': {'pnl': 0, 'wins': 0, 'losses': 0, 'details': []},
        'TRAILING_AGRESSIF': {'pnl': 0, 'wins': 0, 'losses': 0, 'details': []},
        'ACTUEL': {'pnl': 0, 'wins': 0, 'losses': 0, 'details': []}
    }

    for trade in symbol_trades:
        # Scénario 1: Sans BE ni trailing (SL/TP purs)
        pnl1, reason1 = simulate_scenario(trade, use_be=False, use_trailing=False)
        scenarios['SANS_BE_NI_TRAILING']['pnl'] += pnl1
        if pnl1 > 0:
            scenarios['SANS_BE_NI_TRAILING']['wins'] += 1
        else:
            scenarios['SANS_BE_NI_TRAILING']['losses'] += 1

        # Scénario 2: BE seulement
        pnl2, reason2 = simulate_scenario(trade, use_be=True, use_trailing=False)
        scenarios['BE_SEULEMENT']['pnl'] += pnl2
        if pnl2 > 0:
            scenarios['BE_SEULEMENT']['wins'] += 1
        else:
            scenarios['BE_SEULEMENT']['losses'] += 1

        # Scénario 3: Trailing agressif
        pnl3, reason3 = simulate_scenario(trade, use_be=True, use_trailing=True,
                                          trailing_levels=trailing_aggressive)
        scenarios['TRAILING_AGRESSIF']['pnl'] += pnl3
        if pnl3 > 0:
            scenarios['TRAILING_AGRESSIF']['wins'] += 1
        else:
            scenarios['TRAILING_AGRESSIF']['losses'] += 1

        # Scénario 4: Actuel (résultat réel)
        scenarios['ACTUEL']['pnl'] += trade.pnl
        if trade.pnl > 0:
            scenarios['ACTUEL']['wins'] += 1
        else:
            scenarios['ACTUEL']['losses'] += 1

    return scenarios

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n" + "="*80)
    print("POST-MORTEM: TRAILING STOP & BREAK-EVEN ANALYSIS")
    print("="*80)

    # Extraire trades
    print("\n[1/4] Extraction des trades...")
    trades = extract_trades_from_snapshots()
    print(f"      {len(trades)} trades analysés")

    if len(trades) < 5:
        print("\n[WARN] Pas assez de trades pour une analyse fiable!")
        exit()

    # Analyse par symbole
    print("\n[2/4] Analyse par symbole...")
    analysis = analyze_by_symbol(trades)

    print("\n" + "="*80)
    print("STATISTIQUES PAR SYMBOLE:")
    print("="*80)

    for sym in ['ES', 'NQ']:
        if sym not in analysis:
            continue

        data = analysis[sym]
        count = data['count']

        if count == 0:
            continue

        win_rate = data['wins'] / count * 100
        avg_pnl = data['total_pnl'] / count
        mfe_capture = data['mfe_captured'] / data['total_mfe'] * 100 if data['total_mfe'] else 0

        print(f"\n{'='*40}")
        print(f"  {sym} - {count} TRADES")
        print(f"{'='*40}")
        print(f"  Wins: {data['wins']} | Losses: {data['losses']}")
        print(f"  Win Rate: {win_rate:.1f}%")
        print(f"  P&L Total: ${data['total_pnl']:+.2f}")
        print(f"  P&L Moyen: ${avg_pnl:+.2f}")
        print(f"  ")
        print(f"  MFE Total (potentiel): ${data['total_mfe']:.2f}")
        print(f"  MFE Capturé: ${data['mfe_captured']:.2f}")
        print(f"  Taux de capture MFE: {mfe_capture:.1f}%")
        print(f"  ")
        print(f"  TP Hits: {data['tp_hits']}")
        print(f"  SL/BE Hits: {data['sl_hits']}")
        print(f"  BE Saves (estimés): {data['be_saves']}")

    # Comparaison des scénarios
    print("\n" + "="*80)
    print("[3/4] COMPARAISON DES SCÉNARIOS:")
    print("="*80)

    for sym in ['ES', 'NQ']:
        scenarios = compare_scenarios(trades, sym)

        print(f"\n{'─'*60}")
        print(f"  {sym} - COMPARAISON")
        print(f"{'─'*60}")
        print(f"  {'Scénario':<25} {'P&L':>12} {'Wins':>6} {'Losses':>8}")
        print(f"  {'-'*55}")

        best_pnl = max(s['pnl'] for s in scenarios.values())

        for name, data in scenarios.items():
            is_best = "🏆" if data['pnl'] == best_pnl else "  "
            print(f"{is_best} {name:<25} ${data['pnl']:>+10.2f} {data['wins']:>6} {data['losses']:>8}")

    # Verdict
    print("\n" + "="*80)
    print("[4/4] VERDICT HONNÊTE:")
    print("="*80)

    # Calculer différences
    es_scenarios = compare_scenarios(trades, 'ES')
    nq_scenarios = compare_scenarios(trades, 'NQ')

    print("\n📊 ES:")
    es_diff_be = es_scenarios['BE_SEULEMENT']['pnl'] - es_scenarios['SANS_BE_NI_TRAILING']['pnl']
    es_diff_trail = es_scenarios['TRAILING_AGRESSIF']['pnl'] - es_scenarios['SANS_BE_NI_TRAILING']['pnl']
    print(f"   Impact BE seul: ${es_diff_be:+.2f}")
    print(f"   Impact Trailing: ${es_diff_trail:+.2f}")

    if es_diff_be > 0:
        print(f"   ✅ Le BE SAUVE de l'argent sur ES!")
    else:
        print(f"   ❌ Le BE COÛTE de l'argent sur ES (sorties trop tôt)")

    if es_diff_trail > es_diff_be:
        print(f"   ✅ Le Trailing améliore vs BE seul")

    print("\n📊 NQ:")
    nq_diff_be = nq_scenarios['BE_SEULEMENT']['pnl'] - nq_scenarios['SANS_BE_NI_TRAILING']['pnl']
    nq_diff_trail = nq_scenarios['TRAILING_AGRESSIF']['pnl'] - nq_scenarios['SANS_BE_NI_TRAILING']['pnl']
    print(f"   Impact BE seul: ${nq_diff_be:+.2f}")
    print(f"   Impact Trailing: ${nq_diff_trail:+.2f}")

    if nq_diff_be > 0:
        print(f"   ✅ Le BE SAUVE de l'argent sur NQ!")
    else:
        print(f"   ❌ Le BE COÛTE de l'argent sur NQ (sorties trop tôt)")

    print("\n" + "="*80)
    print("RECOMMANDATION FINALE:")
    print("="*80)

    total_be_impact = es_diff_be + nq_diff_be
    total_trail_impact = es_diff_trail + nq_diff_trail

    if total_be_impact > 100:
        print(f"\n✅ GARDER LE BE - Il sauve ${total_be_impact:.0f} au total")
    elif total_be_impact < -100:
        print(f"\n❌ DÉSACTIVER LE BE - Il coûte ${abs(total_be_impact):.0f} au total")
    else:
        print(f"\n⚠️ BE NEUTRE - Impact de ${total_be_impact:.0f} (marginal)")

    if total_trail_impact > total_be_impact + 50:
        print(f"✅ TRAILING AGRESSIF RECOMMANDÉ - Gain additionnel de ${total_trail_impact - total_be_impact:.0f}")
    else:
        print(f"⚠️ TRAILING apporte peu vs BE seul")

    print("\n" + "="*80)

