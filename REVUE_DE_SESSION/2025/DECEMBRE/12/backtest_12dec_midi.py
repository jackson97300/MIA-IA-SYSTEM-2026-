#!/usr/bin/env python3
"""
🔄 BACKTEST RÉEL - 12 DÉCEMBRE 2025
Simule avec les VRAIS mouvements de prix.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional

# Configuration
DATA_PATH = Path("D:/MIA_IA_system/DATA_SIERRA_CHART/DATA_2025/DECEMBRE/20251212")
SYMBOLS = {
    "ES": {"chart_id": 3, "tick_size": 0.25, "tick_value": 12.50},
    "NQ": {"chart_id": 9, "tick_size": 0.25, "tick_value": 5.00},
}

# Paramètres
SL_TICKS = 15
TP_TICKS = 15
MIN_CONFIDENCE = 1.00
MAX_DISTANCE_TICKS = {"ES": 10, "NQ": 15}
START_TIME_PARIS = 12
END_TIME_PARIS = 22
MIN_INTERVAL_MS = 300_000  # 5 min cooldown


def load_snapshots(symbol: str) -> List[Dict]:
    """Charge les snapshots pour un symbole."""
    config = SYMBOLS[symbol]
    file_path = DATA_PATH / f"CHART_{config['chart_id']}" / "ML_READY" / f"ml_{symbol}Z25_FUT_CME_{config['chart_id']}.jsonl"

    if not file_path.exists():
        print(f"❌ Fichier non trouvé: {file_path}")
        return []

    snapshots = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    snap = json.loads(line)
                    snapshots.append(snap)
                except json.JSONDecodeError:
                    continue

    # IMPORTANT: Trier par timestamp
    snapshots.sort(key=lambda x: x.get('t_ms', 0))
    print(f"✅ {symbol}: {len(snapshots)} snapshots chargés")
    return snapshots


def get_hour_paris(t_ms: int) -> int:
    """Convertit timestamp en heure Paris."""
    hour_utc = (t_ms // 1000 // 3600) % 24
    return (hour_utc + 1) % 24  # UTC+1 pour décembre


def check_signal_valid(snap: Dict, symbol: str) -> Tuple[bool, str, float, str]:
    """
    Vérifie si un snapshot génère un signal valide.
    Retourne: (is_valid, direction, confidence, nearest_level_name)
    """
    mid = snap.get('mid', 0)
    if mid <= 0:
        return False, "", 0, ""

    tick_size = SYMBOLS[symbol]['tick_size']
    max_dist = MAX_DISTANCE_TICKS[symbol]

    # Vérifier proximité des niveaux
    levels_to_check = [
        ('gex_1', snap.get('gex_1')),
        ('gex_2', snap.get('gex_2')),
        ('gex_3', snap.get('gex_3')),
        ('hvl', snap.get('hvl')),
        ('blind_spot_7', snap.get('blind_spot_7')),
        ('blind_spot_8', snap.get('blind_spot_8')),
    ]

    nearest_level = None
    nearest_dist = float('inf')
    nearest_name = ""

    for name, price in levels_to_check:
        if price and price > 0:
            dist_ticks = abs(mid - price) / tick_size
            if dist_ticks < nearest_dist:
                nearest_dist = dist_ticks
                nearest_level = price
                nearest_name = name

    if nearest_dist > max_dist:
        return False, "", 0, ""

    # Direction basée sur mia_score
    mia_score = snap.get('mia_bullish_score', 0)

    if mia_score < -0.30:
        direction = "SHORT"
    elif mia_score > 0.30:
        direction = "LONG"
    else:
        return False, "", 0, ""

    # Confidence
    confidence = 1.0 + abs(mia_score) * 0.5

    return True, direction, confidence, nearest_name


def simulate_trade_real(
    entry_snap: Dict,
    direction: str,
    symbol: str,
    future_snapshots: List[Dict],
    nearest_level: str,
    max_duration_ms: int = 3600_000  # Max 1h pour le trade
) -> Dict:
    """
    Simule un trade avec les VRAIS prix futurs.
    """
    tick_size = SYMBOLS[symbol]['tick_size']
    tick_value = SYMBOLS[symbol]['tick_value']

    entry_price = entry_snap.get('mid')
    entry_time = entry_snap.get('t_ms', 0)

    # Calculer SL et TP
    if direction == "SHORT":
        tp_price = entry_price - (TP_TICKS * tick_size)
        sl_price = entry_price + (SL_TICKS * tick_size)
    else:  # LONG
        tp_price = entry_price + (TP_TICKS * tick_size)
        sl_price = entry_price - (SL_TICKS * tick_size)

    # Parcourir les snapshots futurs
    result = "TIMEOUT"
    exit_price = entry_price
    exit_time = entry_time
    high_reached = entry_price
    low_reached = entry_price

    for snap in future_snapshots:
        t_ms = snap.get('t_ms', 0)

        # Vérifier timeout
        if t_ms - entry_time > max_duration_ms:
            break

        # Prix high/low de la barre
        high = snap.get('high', snap.get('mid', entry_price))
        low = snap.get('low', snap.get('mid', entry_price))

        # Tracker extremes
        high_reached = max(high_reached, high)
        low_reached = min(low_reached, low)

        # Vérifier si SL ou TP touché
        if direction == "LONG":
            # SL touché?
            if low <= sl_price:
                result = "LOSS"
                exit_price = sl_price
                exit_time = t_ms
                break
            # TP touché?
            if high >= tp_price:
                result = "WIN"
                exit_price = tp_price
                exit_time = t_ms
                break

        else:  # SHORT
            # SL touché?
            if high >= sl_price:
                result = "LOSS"
                exit_price = sl_price
                exit_time = t_ms
                break
            # TP touché?
            if low <= tp_price:
                result = "WIN"
                exit_price = tp_price
                exit_time = t_ms
                break

    # Calculer P&L
    if direction == "LONG":
        pnl_ticks = (exit_price - entry_price) / tick_size
    else:
        pnl_ticks = (entry_price - exit_price) / tick_size

    pnl_usd = pnl_ticks * tick_value

    # MAE/MFE (Max Adverse/Favorable Excursion)
    if direction == "LONG":
        mae_ticks = (entry_price - low_reached) / tick_size
        mfe_ticks = (high_reached - entry_price) / tick_size
    else:
        mae_ticks = (high_reached - entry_price) / tick_size
        mfe_ticks = (entry_price - low_reached) / tick_size

    return {
        'symbol': symbol,
        'direction': direction,
        'entry_price': entry_price,
        'exit_price': exit_price,
        'tp_price': tp_price,
        'sl_price': sl_price,
        'result': result,
        'pnl_ticks': pnl_ticks,
        'pnl_usd': pnl_usd,
        'entry_time': entry_time,
        'exit_time': exit_time,
        'duration_sec': (exit_time - entry_time) / 1000,
        'mae_ticks': mae_ticks,
        'mfe_ticks': mfe_ticks,
        'mia_score': entry_snap.get('mia_bullish_score', 0),
        'nearest_level': nearest_level,
    }


def run_backtest():
    """Exécute le backtest RÉEL."""
    print("=" * 70)
    print("🔄 BACKTEST RÉEL - 12 DÉCEMBRE 2025 (VRAIS PRIX)")
    print("=" * 70)

    all_trades = []

    for symbol in ["ES", "NQ"]:
        print(f"\n📊 {symbol}...")
        snapshots = load_snapshots(symbol)

        if not snapshots:
            continue

        # Filtrer par heure
        valid_indices = []
        for i, snap in enumerate(snapshots):
            hour = get_hour_paris(snap.get('t_ms', 0))
            if START_TIME_PARIS <= hour < END_TIME_PARIS:
                valid_indices.append(i)

        print(f"   {len(valid_indices)} snapshots entre 12h et 22h")

        # Chercher signaux et simuler
        last_trade_time = 0
        trades = []

        for idx in valid_indices:
            snap = snapshots[idx]
            t_ms = snap.get('t_ms', 0)

            # Cooldown
            if t_ms - last_trade_time < MIN_INTERVAL_MS:
                continue

            is_valid, direction, confidence, nearest_level = check_signal_valid(snap, symbol)

            if is_valid and confidence >= MIN_CONFIDENCE:
                # Obtenir les snapshots FUTURS
                future_snaps = snapshots[idx + 1:]

                if len(future_snaps) < 10:
                    continue  # Pas assez de données futures

                # Simuler avec les VRAIS prix
                trade = simulate_trade_real(snap, direction, symbol, future_snaps, nearest_level)
                trades.append(trade)
                last_trade_time = t_ms

                # Log
                ts = datetime.fromtimestamp(t_ms / 1000).strftime('%H:%M')
                icon = "✅" if trade['result'] == 'WIN' else "❌" if trade['result'] == 'LOSS' else "⏱️"
                print(f"   {ts} | {direction:5s} @ {trade['entry_price']:.2f} → {icon} {trade['result']} | ${trade['pnl_usd']:+.2f} | MFE:{trade['mfe_ticks']:.0f}t MAE:{trade['mae_ticks']:.0f}t")

        print(f"   Total: {len(trades)} trades")
        all_trades.extend(trades)

    # === RÉSULTATS ===
    print("\n" + "=" * 70)
    print("📊 RÉSULTATS RÉELS")
    print("=" * 70)

    if not all_trades:
        print("❌ Aucun trade")
        return

    wins = [t for t in all_trades if t['result'] == 'WIN']
    losses = [t for t in all_trades if t['result'] == 'LOSS']
    timeouts = [t for t in all_trades if t['result'] == 'TIMEOUT']

    total_pnl = sum(t['pnl_usd'] for t in all_trades)
    win_rate = len(wins) / len(all_trades) * 100 if all_trades else 0

    print(f"\n📈 GLOBAL:")
    print(f"   Trades: {len(all_trades)} (W:{len(wins)} L:{len(losses)} T:{len(timeouts)})")
    print(f"   Win Rate: {win_rate:.1f}%")
    print(f"   PnL: ${total_pnl:+.2f}")

    if wins:
        avg_win = sum(t['pnl_usd'] for t in wins) / len(wins)
        print(f"   Avg Win: ${avg_win:+.2f}")
    if losses:
        avg_loss = sum(t['pnl_usd'] for t in losses) / len(losses)
        print(f"   Avg Loss: ${avg_loss:.2f}")

    # Profit Factor
    gross_profit = sum(t['pnl_usd'] for t in wins) if wins else 0
    gross_loss = abs(sum(t['pnl_usd'] for t in losses)) if losses else 1
    pf = gross_profit / gross_loss if gross_loss > 0 else 0
    print(f"   Profit Factor: {pf:.2f}")

    # Par symbole
    print(f"\n📊 PAR SYMBOLE:")
    for sym in ["ES", "NQ"]:
        sym_trades = [t for t in all_trades if t['symbol'] == sym]
        if sym_trades:
            sym_pnl = sum(t['pnl_usd'] for t in sym_trades)
            sym_wr = len([t for t in sym_trades if t['result'] == 'WIN']) / len(sym_trades) * 100
            print(f"   {sym}: {len(sym_trades)} trades | WR: {sym_wr:.1f}% | ${sym_pnl:+.2f}")

    # Par direction
    print(f"\n📊 PAR DIRECTION:")
    for dir_name in ["LONG", "SHORT"]:
        dir_trades = [t for t in all_trades if t['direction'] == dir_name]
        if dir_trades:
            dir_pnl = sum(t['pnl_usd'] for t in dir_trades)
            dir_wr = len([t for t in dir_trades if t['result'] == 'WIN']) / len(dir_trades) * 100
            print(f"   {dir_name}: {len(dir_trades)} trades | WR: {dir_wr:.1f}% | ${dir_pnl:+.2f}")

    # Stop Hunt Analysis
    print(f"\n🔍 STOP HUNT ANALYSIS (trades où MFE > 10t avant LOSS):")
    stop_hunts = 0
    for t in all_trades:
        if t['result'] == 'LOSS' and t['mfe_ticks'] > 10:
            stop_hunts += 1
            ts = datetime.fromtimestamp(t['entry_time'] / 1000).strftime('%H:%M')
            print(f"   ⚠️ {ts} {t['symbol']} {t['direction']} @ {t['entry_price']:.2f}")
            print(f"      MFE={t['mfe_ticks']:.0f}t (allé en faveur) puis SL touché (MAE={t['mae_ticks']:.0f}t)")

    if stop_hunts == 0:
        print("   ✅ Aucun stop hunt détecté")
    else:
        print(f"\n   📊 {stop_hunts} stop hunts sur {len(losses)} pertes = {stop_hunts/len(losses)*100:.0f}%")

    # Comparaison
    print("\n" + "=" * 70)
    print("📊 COMPARAISON VS RÉSULTAT RÉEL DU 12 DÉC")
    print("=" * 70)
    print(f"   RÉEL (12h-22h):   -$580.50 (3 trades, 0% WR)")
    print(f"   BACKTEST:         ${total_pnl:+.2f} ({len(all_trades)} trades, {win_rate:.1f}% WR)")
    print(f"   DIFFÉRENCE:       ${total_pnl - (-580.50):+.2f}")

    if total_pnl > -580.50:
        print("\n   ✅ Le code corrigé aurait fait MIEUX!")
    elif total_pnl > 0:
        print("\n   ✅ Le code corrigé aurait été PROFITABLE!")
    else:
        print("\n   ⚠️ Le marché était difficile ce jour-là")


if __name__ == "__main__":
    run_backtest()
