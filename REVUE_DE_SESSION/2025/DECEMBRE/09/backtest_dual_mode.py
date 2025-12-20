#!/usr/bin/env python3
"""
BACKTEST DUAL-MODE STRATEGY
============================
Test sur vraies donnees collectees (JSONL)

Compare:
- MODE TREND: SL/TP fixes (20t/40t ES, 25t/50t NQ)
- MODE RANGE: SL/TP adaptatifs (hors bracket, TP 60%)

Version: 1.0.0 - 09/12/2025
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict

# Ajouter le chemin du projet
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

print("=" * 70)
print("BACKTEST DUAL-MODE STRATEGY")
print("=" * 70)

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DATA_PATH = Path("D:/MIA_IA_system/DATA_SIERRA_CHART/DATA_2025/DECEMBRE")

CHART_MAPPING = {
    "ES": 3,
    "NQ": 9,
    "RTY": 1
}

SYMBOL_CONFIG = {
    'ES': {
        'tick_size': 0.25,
        'tick_value': 12.50,
        # MODE TREND
        'trend_sl_ticks': 20,
        'trend_tp_ticks': 40,
        # MODE RANGE
        'range_sl_buffer_ticks': 6,
        'range_tp_pct': 0.60,
        # Seuils
        'vol_regime_trend': 1.5,
        'bias_threshold': 0.25,
        'bottom_zone_pct': 30,
        'top_zone_pct': 70,
        'min_range_ticks': 12,
        'max_range_ticks': 50,
    },
    'NQ': {
        'tick_size': 0.25,
        'tick_value': 5.00,
        'trend_sl_ticks': 25,
        'trend_tp_ticks': 50,
        'range_sl_buffer_ticks': 8,
        'range_tp_pct': 0.60,
        'vol_regime_trend': 1.5,
        'bias_threshold': 0.25,
        'bottom_zone_pct': 30,
        'top_zone_pct': 70,
        'min_range_ticks': 15,
        'max_range_ticks': 60,
    }
}


# ============================================================================
# DATACLASSES
# ============================================================================

@dataclass
class SimulatedTrade:
    symbol: str
    direction: str
    entry_price: float
    entry_time: datetime
    sl_price: float
    tp_price: float
    mode: str  # "TREND" ou "RANGE"
    zone: str  # "BOTTOM", "MIDDLE", "TOP", "N/A"
    # Resultats
    exit_price: float = 0.0
    exit_time: Optional[datetime] = None
    pnl_ticks: float = 0.0
    pnl_usd: float = 0.0
    exit_reason: str = ""  # "TP", "SL", "TIMEOUT"
    mfe_ticks: float = 0.0  # Max Favorable Excursion
    mae_ticks: float = 0.0  # Max Adverse Excursion


# ============================================================================
# FONCTIONS UTILITAIRES
# ============================================================================

def load_snapshots_for_date(date_str: str, symbol: str) -> List[Dict]:
    """Charge les snapshots pour une date et un symbole"""
    chart_id = CHART_MAPPING.get(symbol)
    if not chart_id:
        print(f"  [!] Symbole inconnu: {symbol}")
        return []

    file_path = BASE_DATA_PATH / date_str / f"CHART_{chart_id}" / "ML_READY" / f"ml_{symbol}Z25_FUT_CME_{chart_id}.jsonl"

    if not file_path.exists():
        print(f"  [!] Fichier non trouve: {file_path}")
        return []

    snapshots = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    snapshot = json.loads(line)
                    snapshots.append(snapshot)
                except json.JSONDecodeError:
                    continue

    print(f"  [OK] {len(snapshots)} snapshots charges pour {symbol} le {date_str}")
    return snapshots


def detect_market_mode(snapshot: Dict, symbol: str) -> Tuple[str, str]:
    """Detecte le mode TREND ou RANGE"""
    cfg = SYMBOL_CONFIG.get(symbol, SYMBOL_CONFIG['ES'])

    vol_regime = snapshot.get('volatility_regime', 2.0)
    mia_score = snapshot.get('mia_bullish_score', 0)

    # Protection contre None
    if vol_regime is None:
        vol_regime = 2.0
    if mia_score is None:
        mia_score = 0

    is_high_vol = vol_regime > cfg['vol_regime_trend']
    is_directional = abs(mia_score) > cfg['bias_threshold']

    if is_high_vol:
        return "TREND", f"Vol haute ({vol_regime:.1f})"
    elif is_directional:
        bias = "BULLISH" if mia_score > 0 else "BEARISH"
        return "TREND", f"Bias {bias} ({mia_score:.2f})"
    else:
        return "RANGE", f"Vol basse + Bias neutre"


def detect_range_zone(snapshot: Dict, symbol: str) -> Tuple[bool, str, Dict]:
    """Detecte la zone dans le range"""
    cfg = SYMBOL_CONFIG.get(symbol, SYMBOL_CONFIG['ES'])
    tick_size = cfg['tick_size']

    mid = snapshot.get('mid', 0)
    if not mid:
        return False, "OUTSIDE", {}

    # IBH/IBL depuis structure
    structure = snapshot.get('structure', {})
    ibh = structure.get('ibh', 0)
    ibl = structure.get('ibl', 0)

    # Fallback sur high/low
    if not ibh or not ibl or ibh <= ibl:
        ibh = snapshot.get('high', 0)
        ibl = snapshot.get('low', 0)

    if not ibh or not ibl or ibh <= ibl:
        return False, "OUTSIDE", {}

    range_ticks = (ibh - ibl) / tick_size

    # Verifier taille valide
    if range_ticks < cfg['min_range_ticks'] or range_ticks > cfg['max_range_ticks']:
        return False, "OUTSIDE", {'reason': f"Range invalide ({range_ticks:.0f}t)"}

    # Position dans le range
    position_pct = ((mid - ibl) / (ibh - ibl)) * 100
    position_pct = max(0, min(100, position_pct))

    if position_pct < cfg['bottom_zone_pct']:
        zone = "BOTTOM"
    elif position_pct > cfg['top_zone_pct']:
        zone = "TOP"
    else:
        zone = "MIDDLE"

    return True, zone, {
        'ibh': ibh,
        'ibl': ibl,
        'range_ticks': range_ticks,
        'position_pct': position_pct,
    }


def should_generate_signal(snapshot: Dict, symbol: str) -> Tuple[bool, str]:
    """Determine si un signal doit etre genere (simplifie)"""
    # Utiliser mia_bullish_score pour la direction
    mia_score = snapshot.get('mia_bullish_score', 0)
    if mia_score is None:
        return False, ""

    # Verifier qu'on a une direction claire
    if abs(mia_score) < 0.05:
        return False, ""

    direction = "LONG" if mia_score > 0 else "SHORT"
    return True, direction


def simulate_trade_outcome(trade: SimulatedTrade, future_snapshots: List[Dict],
                           symbol: str, max_bars: int = 60) -> SimulatedTrade:
    """Simule le resultat d'un trade sur les snapshots futurs"""
    cfg = SYMBOL_CONFIG.get(symbol, SYMBOL_CONFIG['ES'])
    tick_size = cfg['tick_size']
    tick_value = cfg['tick_value']

    mfe = 0.0
    mae = 0.0

    for i, snap in enumerate(future_snapshots[:max_bars]):
        high = snap.get('high', snap.get('mid', 0))
        low = snap.get('low', snap.get('mid', 0))
        mid = snap.get('mid', 0)

        if not mid:
            continue

        # Calculer MFE/MAE
        if trade.direction == "LONG":
            favorable = (high - trade.entry_price) / tick_size
            adverse = (trade.entry_price - low) / tick_size
        else:  # SHORT
            favorable = (trade.entry_price - low) / tick_size
            adverse = (high - trade.entry_price) / tick_size

        mfe = max(mfe, favorable)
        mae = max(mae, adverse)

        # Verifier SL touche
        if trade.direction == "LONG":
            if low <= trade.sl_price:
                trade.exit_price = trade.sl_price
                trade.exit_reason = "SL"
                trade.pnl_ticks = -abs(trade.entry_price - trade.sl_price) / tick_size
                break
        else:  # SHORT
            if high >= trade.sl_price:
                trade.exit_price = trade.sl_price
                trade.exit_reason = "SL"
                trade.pnl_ticks = -abs(trade.sl_price - trade.entry_price) / tick_size
                break

        # Verifier TP touche
        if trade.direction == "LONG":
            if high >= trade.tp_price:
                trade.exit_price = trade.tp_price
                trade.exit_reason = "TP"
                trade.pnl_ticks = abs(trade.tp_price - trade.entry_price) / tick_size
                break
        else:  # SHORT
            if low <= trade.tp_price:
                trade.exit_price = trade.tp_price
                trade.exit_reason = "TP"
                trade.pnl_ticks = abs(trade.entry_price - trade.tp_price) / tick_size
                break
    else:
        # Timeout - sortie au dernier prix
        if future_snapshots:
            trade.exit_price = future_snapshots[-1].get('mid', trade.entry_price)
            trade.exit_reason = "TIMEOUT"
            if trade.direction == "LONG":
                trade.pnl_ticks = (trade.exit_price - trade.entry_price) / tick_size
            else:
                trade.pnl_ticks = (trade.entry_price - trade.exit_price) / tick_size

    trade.mfe_ticks = mfe
    trade.mae_ticks = mae
    trade.pnl_usd = trade.pnl_ticks * tick_value

    return trade


# ============================================================================
# BACKTEST PRINCIPAL
# ============================================================================

def run_backtest(dates: List[str], symbol: str, sample_every: int = 300):
    """
    Execute le backtest sur plusieurs dates

    Args:
        dates: Liste des dates (format YYYYMMDD)
        symbol: ES ou NQ
        sample_every: Prendre un snapshot tous les N (pour eviter trop de trades)
    """
    cfg = SYMBOL_CONFIG.get(symbol, SYMBOL_CONFIG['ES'])
    tick_size = cfg['tick_size']
    tick_value = cfg['tick_value']

    # Resultats par mode
    results = {
        'TREND': {'trades': [], 'wins': 0, 'losses': 0, 'pnl': 0},
        'RANGE': {'trades': [], 'wins': 0, 'losses': 0, 'pnl': 0},
        'BLOCKED_MIDDLE': 0,
        'BLOCKED_COUNTER': 0,
    }

    print(f"\n{'='*70}")
    print(f"BACKTEST {symbol} - DUAL MODE STRATEGY")
    print(f"{'='*70}")

    for date_str in dates:
        print(f"\n[DATE] {date_str}")

        snapshots = load_snapshots_for_date(date_str, symbol)
        if not snapshots:
            continue

        # Parcourir les snapshots (echantillonnes)
        i = 0
        while i < len(snapshots) - 60:  # Garder 60 barres pour simulation
            snapshot = snapshots[i]

            # Detecter mode
            mode, mode_reason = detect_market_mode(snapshot, symbol)

            # Generer signal
            has_signal, direction = should_generate_signal(snapshot, symbol)

            if not has_signal:
                i += sample_every
                continue

            mid = snapshot.get('mid', 0)
            if not mid:
                i += sample_every
                continue

            # ====== MODE RANGE ======
            if mode == "RANGE":
                is_range, zone, range_info = detect_range_zone(snapshot, symbol)

                if is_range:
                    # BLOQUER MIDDLE
                    if zone == "MIDDLE":
                        results['BLOCKED_MIDDLE'] += 1
                        i += sample_every
                        continue

                    # BLOQUER direction contraire
                    if zone == "BOTTOM" and direction == "SHORT":
                        results['BLOCKED_COUNTER'] += 1
                        i += sample_every
                        continue
                    if zone == "TOP" and direction == "LONG":
                        results['BLOCKED_COUNTER'] += 1
                        i += sample_every
                        continue

                    # Calculer SL/TP RANGE
                    ibh = range_info['ibh']
                    ibl = range_info['ibl']
                    range_size = ibh - ibl

                    if zone == "BOTTOM":
                        sl = ibl - (cfg['range_sl_buffer_ticks'] * tick_size)
                        tp = ibl + (range_size * cfg['range_tp_pct'])
                    else:  # TOP
                        sl = ibh + (cfg['range_sl_buffer_ticks'] * tick_size)
                        tp = ibh - (range_size * cfg['range_tp_pct'])

                    trade = SimulatedTrade(
                        symbol=symbol,
                        direction=direction,
                        entry_price=mid,
                        entry_time=datetime.fromtimestamp(snapshot.get('t_ms', 0) / 1000),
                        sl_price=sl,
                        tp_price=tp,
                        mode="RANGE",
                        zone=zone
                    )
                else:
                    # Pas de range valide, fallback sur TREND
                    mode = "TREND"

            # ====== MODE TREND ======
            if mode == "TREND":
                mia_score = snapshot.get('mia_bullish_score', 0) or 0

                # Verifier direction alignee
                if direction == "LONG" and mia_score < -cfg['bias_threshold']:
                    results['BLOCKED_COUNTER'] += 1
                    i += sample_every
                    continue
                if direction == "SHORT" and mia_score > cfg['bias_threshold']:
                    results['BLOCKED_COUNTER'] += 1
                    i += sample_every
                    continue

                # Calculer SL/TP TREND (fixes)
                if direction == "LONG":
                    sl = mid - (cfg['trend_sl_ticks'] * tick_size)
                    tp = mid + (cfg['trend_tp_ticks'] * tick_size)
                else:
                    sl = mid + (cfg['trend_sl_ticks'] * tick_size)
                    tp = mid - (cfg['trend_tp_ticks'] * tick_size)

                trade = SimulatedTrade(
                    symbol=symbol,
                    direction=direction,
                    entry_price=mid,
                    entry_time=datetime.fromtimestamp(snapshot.get('t_ms', 0) / 1000),
                    sl_price=sl,
                    tp_price=tp,
                    mode="TREND",
                    zone="N/A"
                )

            # Simuler le trade
            future_snaps = snapshots[i+1:i+61]
            trade = simulate_trade_outcome(trade, future_snaps, symbol)

            # Enregistrer resultat
            results[trade.mode]['trades'].append(trade)
            if trade.pnl_usd > 0:
                results[trade.mode]['wins'] += 1
            else:
                results[trade.mode]['losses'] += 1
            results[trade.mode]['pnl'] += trade.pnl_usd

            # Sauter apres un trade (cooldown)
            i += sample_every * 2

    return results


def print_results(results: Dict, symbol: str):
    """Affiche les resultats du backtest"""
    cfg = SYMBOL_CONFIG.get(symbol, SYMBOL_CONFIG['ES'])

    print(f"\n{'='*70}")
    print(f"RESULTATS BACKTEST {symbol}")
    print(f"{'='*70}")

    print(f"\n[BLOCAGES]")
    print(f"  Bloques MIDDLE:        {results['BLOCKED_MIDDLE']}")
    print(f"  Bloques COUNTER-TREND: {results['BLOCKED_COUNTER']}")

    for mode in ['TREND', 'RANGE']:
        data = results[mode]
        trades = data['trades']
        wins = data['wins']
        losses = data['losses']
        total = wins + losses
        pnl = data['pnl']

        print(f"\n[MODE {mode}]")
        print(f"  Trades: {total}")

        if total > 0:
            win_rate = (wins / total) * 100
            avg_pnl = pnl / total

            # Calculer stats
            win_trades = [t for t in trades if t.pnl_usd > 0]
            loss_trades = [t for t in trades if t.pnl_usd <= 0]

            avg_win = sum(t.pnl_usd for t in win_trades) / len(win_trades) if win_trades else 0
            avg_loss = sum(t.pnl_usd for t in loss_trades) / len(loss_trades) if loss_trades else 0

            avg_mfe = sum(t.mfe_ticks for t in trades) / len(trades)
            avg_mae = sum(t.mae_ticks for t in trades) / len(trades)

            tp_count = len([t for t in trades if t.exit_reason == "TP"])
            sl_count = len([t for t in trades if t.exit_reason == "SL"])

            print(f"  Wins: {wins} | Losses: {losses}")
            print(f"  Win Rate: {win_rate:.1f}%")
            print(f"  Total P&L: ${pnl:+.2f}")
            print(f"  Avg P&L/trade: ${avg_pnl:+.2f}")
            print(f"  Avg Win: ${avg_win:+.2f} | Avg Loss: ${avg_loss:+.2f}")
            print(f"  Avg MFE: {avg_mfe:.1f}t | Avg MAE: {avg_mae:.1f}t")
            print(f"  TP hits: {tp_count} | SL hits: {sl_count}")
        else:
            print(f"  Aucun trade")

    # Total
    total_pnl = results['TREND']['pnl'] + results['RANGE']['pnl']
    total_trades = len(results['TREND']['trades']) + len(results['RANGE']['trades'])

    print(f"\n[TOTAL]")
    print(f"  Trades: {total_trades}")
    print(f"  P&L Total: ${total_pnl:+.2f}")
    if total_trades > 0:
        print(f"  Avg P&L/trade: ${total_pnl/total_trades:+.2f}")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    # Dates a tester (decembre 2025)
    # Ajuster selon les donnees disponibles
    test_dates = []

    # Chercher les dates disponibles
    for d in range(1, 10):  # 1er au 9 decembre
        date_str = f"2025120{d}"
        if (BASE_DATA_PATH / date_str).exists():
            test_dates.append(date_str)

    print(f"\nDates disponibles: {test_dates}")

    if not test_dates:
        print("\n[!] Aucune donnee trouvee dans le dossier DECEMBRE")
        print(f"    Chemin verifie: {BASE_DATA_PATH}")

        # Essayer NOVEMBRE
        BASE_DATA_PATH_NOV = Path("D:/MIA_IA_system/DATA_SIERRA_CHART/DATA_2025/NOVEMBRE")
        for d in range(20, 30):
            date_str = f"202511{d}"
            if (BASE_DATA_PATH_NOV / date_str).exists():
                test_dates.append(date_str)

        if test_dates:
            print(f"\n[OK] Dates trouvees en NOVEMBRE: {test_dates}")
            BASE_DATA_PATH = BASE_DATA_PATH_NOV

    if test_dates:
        # Backtest ES
        print("\n" + "="*70)
        print("BACKTEST ES")
        print("="*70)
        results_es = run_backtest(test_dates, "ES", sample_every=200)
        print_results(results_es, "ES")

        # Backtest NQ
        print("\n" + "="*70)
        print("BACKTEST NQ")
        print("="*70)
        results_nq = run_backtest(test_dates, "NQ", sample_every=200)
        print_results(results_nq, "NQ")

        # Resume final
        print("\n" + "="*70)
        print("RESUME FINAL")
        print("="*70)

        total_es = results_es['TREND']['pnl'] + results_es['RANGE']['pnl']
        total_nq = results_nq['TREND']['pnl'] + results_nq['RANGE']['pnl']

        print(f"\nES Total P&L: ${total_es:+.2f}")
        print(f"NQ Total P&L: ${total_nq:+.2f}")
        print(f"COMBINED P&L: ${total_es + total_nq:+.2f}")

        blocked_total = (results_es['BLOCKED_MIDDLE'] + results_es['BLOCKED_COUNTER'] +
                        results_nq['BLOCKED_MIDDLE'] + results_nq['BLOCKED_COUNTER'])
        print(f"\nTrades bloques (protection): {blocked_total}")
    else:
        print("\n[ERREUR] Aucune donnee disponible pour le backtest")

