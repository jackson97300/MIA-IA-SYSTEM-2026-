#!/usr/bin/env python3
"""
AUDIT PROFOND - 4 AXES DE RENTABILITÉ
======================================

1. Réduire les pertes (SL)
2. Augmenter les gains (Trailing)
3. Éviter les ranges
4. Moins de trades, meilleure qualité

Date: 08/12/2025
"""

import os
import re
import glob
from collections import defaultdict
from dataclasses import dataclass
from typing import List, Dict, Tuple

LOGS_DIR = r"D:\MIA_IA_system\logs"
TICK_VALUES = {'ES': 12.50, 'NQ': 5.00}

# ═══════════════════════════════════════════════════════════════════════════════
# EXTRACTION DES DONNÉES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class TradeData:
    symbol: str
    pnl: float
    mfe: float
    mae: float
    exit_reason: str

    @property
    def pnl_ticks(self) -> float:
        return self.pnl / TICK_VALUES.get(self.symbol, 12.5)

    @property
    def mfe_ticks(self) -> float:
        return self.mfe / TICK_VALUES.get(self.symbol, 12.5)

    @property
    def mae_ticks(self) -> float:
        return abs(self.mae) / TICK_VALUES.get(self.symbol, 12.5)

def extract_trades() -> List[TradeData]:
    """Extrait les trades depuis les logs"""
    trades = []
    pattern = re.compile(
        r'Trade ferm.*\((\w+)\s+(SL|TP|BE)\s+Hit\s+\$([+-]?\d+\.?\d*)\).*'
        r'\[MFE:\s*([+-]?\d+\.?\d*),\s*MAE:\s*([+-]?\d+\.?\d*)\]',
        re.IGNORECASE
    )

    log_files = sorted(glob.glob(os.path.join(LOGS_DIR, "__main___202512*.log")))[-5:]

    for log_file in log_files:
        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            for match in pattern.findall(content):
                symbol_raw, exit_type, pnl, mfe, mae = match
                symbol = 'ES' if 'ES' in symbol_raw.upper() else 'NQ' if 'NQ' in symbol_raw.upper() else 'ES'

                trades.append(TradeData(
                    symbol=symbol,
                    pnl=float(pnl),
                    mfe=float(mfe),
                    mae=float(mae),
                    exit_reason=exit_type
                ))
        except:
            pass

    return trades

# ═══════════════════════════════════════════════════════════════════════════════
# AXE 1: RÉDUIRE LES PERTES (SL)
# ═══════════════════════════════════════════════════════════════════════════════

def audit_sl_reduction(trades: List[TradeData]) -> Dict:
    """Analyse l'impact de différents SL"""

    print("\n" + "="*80)
    print("AXE 1: RÉDUIRE LES PERTES (SL)")
    print("="*80)

    losing_trades = [t for t in trades if t.pnl < 0]

    if not losing_trades:
        print("Pas de trades perdants à analyser")
        return {}

    # Stats actuelles
    avg_loss = sum(abs(t.pnl) for t in losing_trades) / len(losing_trades)
    avg_mae = sum(t.mae_ticks for t in losing_trades) / len(losing_trades)
    max_mae = max(t.mae_ticks for t in losing_trades)

    print(f"\n📊 STATS PERTES ACTUELLES:")
    print(f"   Nombre de pertes: {len(losing_trades)}")
    print(f"   Perte moyenne: ${avg_loss:.2f}")
    print(f"   MAE moyen: {avg_mae:.1f} ticks")
    print(f"   MAE max: {max_mae:.1f} ticks")

    # Distribution des MAE
    print(f"\n📈 DISTRIBUTION MAE (trades perdants):")
    mae_ranges = [(0, 10), (10, 15), (15, 20), (20, 25), (25, 30), (30, 50)]

    for low, high in mae_ranges:
        count = sum(1 for t in losing_trades if low <= t.mae_ticks < high)
        pct = count / len(losing_trades) * 100
        bar = "█" * int(pct / 5)
        print(f"   {low:>2}-{high:<2}t: {count:>3} trades ({pct:>5.1f}%) {bar}")

    # Simulation différents SL
    print(f"\n🔧 SIMULATION DIFFÉRENTS SL:")
    print(f"   {'SL':>4} | {'Pertes évitées':>15} | {'Économie':>12} | {'Trades stoppés tôt':>20}")
    print(f"   {'-'*60}")

    current_sl = {'ES': 22, 'NQ': 25}
    results = []

    for test_sl in [12, 15, 18, 20, 22, 25]:
        avoided = 0
        economy = 0
        stopped_early = 0

        for t in losing_trades:
            sl_ticks = current_sl.get(t.symbol, 22)
            tick_val = TICK_VALUES.get(t.symbol, 12.5)

            if t.mae_ticks < test_sl:
                # Ce trade n'aurait pas été stoppé plus tôt
                pass
            elif t.mae_ticks >= test_sl and t.mae_ticks >= sl_ticks:
                # Ce trade aurait été stoppé au même niveau ou avant
                if test_sl < sl_ticks:
                    economy += (sl_ticks - test_sl) * tick_val
                    stopped_early += 1

        # Mais attention: un SL plus serré stoppe aussi des trades qui auraient été gagnants!
        winning_trades = [t for t in trades if t.pnl > 0]
        false_stops = sum(1 for t in winning_trades if t.mae_ticks >= test_sl)
        false_stop_cost = sum(test_sl * TICK_VALUES.get(t.symbol, 12.5)
                             for t in winning_trades if t.mae_ticks >= test_sl)

        net = economy - false_stop_cost
        results.append((test_sl, stopped_early, economy, false_stops, false_stop_cost, net))

        print(f"   {test_sl:>4}t | {stopped_early:>15} | ${economy:>10.2f} | {false_stops} faux stops (${false_stop_cost:.0f})")

    # Meilleur SL
    best = max(results, key=lambda x: x[5])
    print(f"\n💡 RECOMMANDATION SL:")
    print(f"   Meilleur SL théorique: {best[0]} ticks")
    print(f"   Économie nette: ${best[5]:.2f}")

    return {'best_sl': best[0], 'net_saving': best[5]}

# ═══════════════════════════════════════════════════════════════════════════════
# AXE 2: AUGMENTER LES GAINS (TRAILING)
# ═══════════════════════════════════════════════════════════════════════════════

def audit_trailing_capture(trades: List[TradeData]) -> Dict:
    """Analyse la capture du MFE"""

    print("\n" + "="*80)
    print("AXE 2: AUGMENTER LES GAINS (TRAILING)")
    print("="*80)

    winning_trades = [t for t in trades if t.pnl > 0]

    if not winning_trades:
        print("Pas de trades gagnants à analyser")
        return {}

    # Stats actuelles
    total_mfe = sum(t.mfe for t in winning_trades)
    total_captured = sum(t.pnl for t in winning_trades)
    capture_rate = total_captured / total_mfe * 100 if total_mfe else 0

    print(f"\n📊 STATS CAPTURE ACTUELLES:")
    print(f"   Trades gagnants: {len(winning_trades)}")
    print(f"   MFE total: ${total_mfe:.2f}")
    print(f"   Capturé: ${total_captured:.2f}")
    print(f"   Taux capture: {capture_rate:.1f}%")
    print(f"   Laissé sur table: ${total_mfe - total_captured:.2f}")

    # Analyse par trade
    print(f"\n📈 ANALYSE PAR TRADE:")
    print(f"   {'MFE':>8} | {'Capturé':>8} | {'Capture%':>8} | {'Potentiel perdu':>15}")
    print(f"   {'-'*50}")

    for t in sorted(winning_trades, key=lambda x: x.mfe, reverse=True)[:10]:
        capture_pct = t.pnl / t.mfe * 100 if t.mfe else 0
        lost = t.mfe - t.pnl
        print(f"   ${t.mfe:>7.2f} | ${t.pnl:>7.2f} | {capture_pct:>7.1f}% | ${lost:>14.2f}")

    # Simulation meilleur trailing
    print(f"\n🔧 SIMULATION TRAILING AMÉLIORÉ:")

    # Si on avait capturé 50% du MFE
    if_50pct = sum(t.mfe * 0.5 for t in winning_trades)
    if_60pct = sum(t.mfe * 0.6 for t in winning_trades)
    if_70pct = sum(t.mfe * 0.7 for t in winning_trades)

    print(f"   Capture actuelle ({capture_rate:.0f}%): ${total_captured:.2f}")
    print(f"   Si capture 50%: ${if_50pct:.2f} (gain: ${if_50pct - total_captured:+.2f})")
    print(f"   Si capture 60%: ${if_60pct:.2f} (gain: ${if_60pct - total_captured:+.2f})")
    print(f"   Si capture 70%: ${if_70pct:.2f} (gain: ${if_70pct - total_captured:+.2f})")

    # Trades où on a laissé beaucoup sur la table
    big_misses = [t for t in winning_trades if t.mfe - t.pnl > 50]
    if big_misses:
        print(f"\n⚠️ GROS MANQUES (>$50 laissé sur table):")
        for t in big_misses:
            print(f"   {t.symbol}: MFE ${t.mfe:.2f}, Capturé ${t.pnl:.2f}, Perdu ${t.mfe - t.pnl:.2f}")

    return {'capture_rate': capture_rate, 'left_on_table': total_mfe - total_captured}

# ═══════════════════════════════════════════════════════════════════════════════
# AXE 3: ÉVITER LES RANGES
# ═══════════════════════════════════════════════════════════════════════════════

def audit_range_detection(trades: List[TradeData]) -> Dict:
    """Analyse les trades en range vs tendance"""

    print("\n" + "="*80)
    print("AXE 3: ÉVITER LES RANGES")
    print("="*80)

    # Un trade en "range" se caractérise par:
    # - MFE et MAE proches (le prix oscille des deux côtés)
    # - Souvent SL hit après avoir été en profit

    range_trades = []
    trend_trades = []

    for t in trades:
        # Ratio MFE/MAE - si proche de 1, c'est un range
        if t.mae_ticks > 0:
            ratio = t.mfe_ticks / t.mae_ticks
        else:
            ratio = float('inf')

        # En range: le prix va des deux côtés de manière similaire
        if 0.5 <= ratio <= 2.0 and t.mfe_ticks > 5 and t.mae_ticks > 5:
            range_trades.append(t)
        else:
            trend_trades.append(t)

    print(f"\n📊 CLASSIFICATION TRADES:")
    print(f"   Trades en RANGE: {len(range_trades)}")
    print(f"   Trades en TREND: {len(trend_trades)}")

    # Performance par type
    if range_trades:
        range_pnl = sum(t.pnl for t in range_trades)
        range_wr = sum(1 for t in range_trades if t.pnl > 0) / len(range_trades) * 100
        print(f"\n📈 PERFORMANCE RANGE:")
        print(f"   P&L: ${range_pnl:.2f}")
        print(f"   Win Rate: {range_wr:.1f}%")
        print(f"   Moyenne: ${range_pnl/len(range_trades):.2f}/trade")

    if trend_trades:
        trend_pnl = sum(t.pnl for t in trend_trades)
        trend_wr = sum(1 for t in trend_trades if t.pnl > 0) / len(trend_trades) * 100
        print(f"\n📈 PERFORMANCE TREND:")
        print(f"   P&L: ${trend_pnl:.2f}")
        print(f"   Win Rate: {trend_wr:.1f}%")
        print(f"   Moyenne: ${trend_pnl/len(trend_trades):.2f}/trade")

    # Recommandation
    print(f"\n💡 ANALYSE:")
    if range_trades and trend_trades:
        range_avg = sum(t.pnl for t in range_trades) / len(range_trades) if range_trades else 0
        trend_avg = sum(t.pnl for t in trend_trades) / len(trend_trades) if trend_trades else 0

        if range_avg < trend_avg:
            impact = len(range_trades) * (trend_avg - range_avg)
            print(f"   ⚠️ Trades en RANGE sous-performent de ${trend_avg - range_avg:.2f}/trade")
            print(f"   Impact estimé si évités: ${impact:.2f}")
        else:
            print(f"   ✅ Trades en range OK")

    return {'range_trades': len(range_trades), 'trend_trades': len(trend_trades)}

# ═══════════════════════════════════════════════════════════════════════════════
# AXE 4: MOINS DE TRADES, MEILLEURE QUALITÉ
# ═══════════════════════════════════════════════════════════════════════════════

def audit_trade_quality(trades: List[TradeData]) -> Dict:
    """Analyse la qualité des trades"""

    print("\n" + "="*80)
    print("AXE 4: MOINS DE TRADES, MEILLEURE QUALITÉ")
    print("="*80)

    if not trades:
        print("Pas de trades à analyser")
        return {}

    # Classer les trades par qualité (basé sur MFE atteint)
    # Bonne qualité = MFE élevé (le trade est allé dans la bonne direction)
    # Mauvaise qualité = MAE élevé et MFE faible

    quality_scores = []
    for t in trades:
        # Score = MFE - MAE (positif = bonne qualité)
        score = t.mfe_ticks - t.mae_ticks
        quality_scores.append((t, score))

    # Trier par score
    quality_scores.sort(key=lambda x: x[1], reverse=True)

    # Top 50% vs Bottom 50%
    mid = len(quality_scores) // 2
    top_half = [t for t, s in quality_scores[:mid]]
    bottom_half = [t for t, s in quality_scores[mid:]]

    print(f"\n📊 ANALYSE QUALITÉ (MFE - MAE):")

    if top_half:
        top_pnl = sum(t.pnl for t in top_half)
        top_wr = sum(1 for t in top_half if t.pnl > 0) / len(top_half) * 100
        print(f"\n   TOP 50% (meilleure qualité):")
        print(f"   ├─ Trades: {len(top_half)}")
        print(f"   ├─ P&L: ${top_pnl:.2f}")
        print(f"   ├─ Win Rate: {top_wr:.1f}%")
        print(f"   └─ Moyenne: ${top_pnl/len(top_half):.2f}/trade")

    if bottom_half:
        bot_pnl = sum(t.pnl for t in bottom_half)
        bot_wr = sum(1 for t in bottom_half if t.pnl > 0) / len(bottom_half) * 100
        print(f"\n   BOTTOM 50% (moins bonne qualité):")
        print(f"   ├─ Trades: {len(bottom_half)}")
        print(f"   ├─ P&L: ${bot_pnl:.2f}")
        print(f"   ├─ Win Rate: {bot_wr:.1f}%")
        print(f"   └─ Moyenne: ${bot_pnl/len(bottom_half):.2f}/trade")

    # Impact si on avait évité les pires trades
    print(f"\n💡 SIMULATION 'MOINS DE TRADES':")

    # Garder seulement les 75% meilleurs
    top_75 = [t for t, s in quality_scores[:int(len(quality_scores)*0.75)]]
    top_75_pnl = sum(t.pnl for t in top_75)

    # Garder seulement les 50% meilleurs
    top_50 = [t for t, s in quality_scores[:int(len(quality_scores)*0.50)]]
    top_50_pnl = sum(t.pnl for t in top_50)

    total_pnl = sum(t.pnl for t in trades)

    print(f"   100% des trades ({len(trades)}): ${total_pnl:.2f}")
    print(f"   Top 75% ({len(top_75)} trades): ${top_75_pnl:.2f} (diff: ${top_75_pnl - total_pnl:+.2f})")
    print(f"   Top 50% ({len(top_50)} trades): ${top_50_pnl:.2f} (diff: ${top_50_pnl - total_pnl:+.2f})")

    # Caractéristiques des mauvais trades
    print(f"\n⚠️ CARACTÉRISTIQUES DES PIRES TRADES:")
    worst_5 = quality_scores[-5:] if len(quality_scores) >= 5 else quality_scores
    for t, score in worst_5:
        print(f"   {t.symbol}: P&L ${t.pnl:.2f}, MFE {t.mfe_ticks:.0f}t, MAE {t.mae_ticks:.0f}t, Score {score:.0f}")

    return {'total_trades': len(trades), 'recommended_reduction': 25}

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n" + "="*80)
    print("AUDIT PROFOND - 4 AXES DE RENTABILITÉ")
    print("="*80)

    # Extraire trades
    print("\n[EXTRACTION] Chargement des trades...")
    trades = extract_trades()
    print(f"   {len(trades)} trades chargés")

    if len(trades) < 5:
        print("\n[WARN] Pas assez de trades pour un audit fiable!")
        exit()

    # Stats globales
    total_pnl = sum(t.pnl for t in trades)
    wins = sum(1 for t in trades if t.pnl > 0)
    losses = len(trades) - wins
    win_rate = wins / len(trades) * 100

    print(f"\n📊 STATS GLOBALES:")
    print(f"   Trades: {len(trades)} | Wins: {wins} | Losses: {losses}")
    print(f"   Win Rate: {win_rate:.1f}%")
    print(f"   P&L Total: ${total_pnl:.2f}")

    # 4 Axes
    r1 = audit_sl_reduction(trades)
    r2 = audit_trailing_capture(trades)
    r3 = audit_range_detection(trades)
    r4 = audit_trade_quality(trades)

    # Synthèse
    print("\n" + "="*80)
    print("SYNTHÈSE FINALE")
    print("="*80)

    print(f"""
    AXE 1 - RÉDUIRE LES PERTES:
    └─ Meilleur SL: {r1.get('best_sl', 'N/A')} ticks
    └─ Économie potentielle: ${r1.get('net_saving', 0):.2f}

    AXE 2 - AUGMENTER LES GAINS:
    └─ Capture actuelle: {r2.get('capture_rate', 0):.1f}%
    └─ Laissé sur table: ${r2.get('left_on_table', 0):.2f}

    AXE 3 - ÉVITER LES RANGES:
    └─ Trades range: {r3.get('range_trades', 0)}
    └─ Trades trend: {r3.get('trend_trades', 0)}

    AXE 4 - MOINS DE TRADES:
    └─ Réduction recommandée: {r4.get('recommended_reduction', 0)}%
    """)

    print("="*80)

