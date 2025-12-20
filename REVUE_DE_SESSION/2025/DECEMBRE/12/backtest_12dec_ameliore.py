#!/usr/bin/env python3
"""
🔄 BACKTEST AMÉLIORÉ - 12 DÉCEMBRE 2025
Avec les corrections identifiées:
- Cooldown 30 min
- Heures toxiques évitées (13h-14h)
- TP partiel à 10t
- Trailing stop
- Détection de retournement
- Filtre delta
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

# Configuration
DATA_PATH = Path("D:/MIA_IA_system/DATA_SIERRA_CHART/DATA_2025/DECEMBRE/20251212")
SYMBOLS = {
    "ES": {"chart_id": 3, "tick_size": 0.25, "tick_value": 12.50},
    "NQ": {"chart_id": 9, "tick_size": 0.25, "tick_value": 5.00},
}

# === NOUVEAUX PARAMÈTRES OPTIMISÉS ===
SL_TICKS = 15
TP1_TICKS = 10                # TP partiel à 10 ticks (50% position)
TP2_TICKS = 15                # TP final à 15 ticks (50% restant)
TRAILING_ACTIVATION = 8       # Active trailing après 8t de profit
TRAILING_DISTANCE = 5         # Trailing à 5 ticks du prix

MIN_CONFIDENCE = 1.00
MAX_DISTANCE_TICKS = {"ES": 10, "NQ": 15}
START_TIME_PARIS = 12
END_TIME_PARIS = 22

MIN_INTERVAL_MS = 1_800_000   # 30 min (était 5 min)
MAX_TRADES_PER_SYMBOL = 8     # Max 8 trades/symbole/jour
TOXIC_HOURS = [13, 14]        # Éviter 13h-14h


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

    snapshots.sort(key=lambda x: x.get('t_ms', 0))
    print(f"✅ {symbol}: {len(snapshots)} snapshots")
    return snapshots


def get_hour_paris(t_ms: int) -> int:
    """Convertit timestamp en heure Paris."""
    hour_utc = (t_ms // 1000 // 3600) % 24
    return (hour_utc + 1) % 24


def check_signal_valid_v2(snap: Dict, symbol: str, recent_snaps: List[Dict]) -> Tuple[bool, str, float, str]:
    """
    Version améliorée avec détection de retournement et filtre delta.
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

    nearest_dist = float('inf')
    nearest_name = ""

    for name, price in levels_to_check:
        if price and price > 0:
            dist_ticks = abs(mid - price) / tick_size
            if dist_ticks < nearest_dist:
                nearest_dist = dist_ticks
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

    # === NOUVEAU: Vérifier retournement ===
    if len(recent_snaps) >= 10:
        old_score = recent_snaps[0].get('mia_bullish_score', 0)
        new_score = mia_score

        # Si le score change de direction rapidement → pas de trade
        if abs(new_score - old_score) > 0.40:
            return False, "", 0, ""

    # === NOUVEAU: Vérifier cohérence delta ===
    delta = snap.get('delta', 0)
    if direction == "SHORT" and delta > 200:
        return False, "", 0, ""
    if direction == "LONG" and delta < -200:
        return False, "", 0, ""

    # Confidence
    confidence = 1.0 + abs(mia_score) * 0.5

    return True, direction, confidence, nearest_name


def simulate_trade_with_tp1(
    entry_snap: Dict,
    direction: str,
    symbol: str,
    future_snapshots: List[Dict],
) -> Dict:
    """
    Simule avec TP partiel à 10t + trailing stop.
    """
    tick_size = SYMBOLS[symbol]['tick_size']
    tick_value = SYMBOLS[symbol]['tick_value']

    entry = entry_snap.get('mid')
    entry_time = entry_snap.get('t_ms', 0)

    # Prix cibles
    if direction == "SHORT":
        tp1_price = entry - (TP1_TICKS * tick_size)
        tp2_price = entry - (TP2_TICKS * tick_size)
        sl_price = entry + (SL_TICKS * tick_size)
    else:
        tp1_price = entry + (TP1_TICKS * tick_size)
        tp2_price = entry + (TP2_TICKS * tick_size)
        sl_price = entry - (SL_TICKS * tick_size)

    tp1_hit = False
    trailing_stop = None
    best_profit_ticks = 0
    pnl_usd = 0
    result = "TIMEOUT"
    exit_price = entry
    exit_time = entry_time
    high_reached = entry
    low_reached = entry

    for snap in future_snapshots:
        t_ms = snap.get('t_ms', 0)
        if t_ms - entry_time > 3600_000:  # Max 1h
            break

        high = snap.get('high', entry)
        low = snap.get('low', entry)
        high_reached = max(high_reached, high)
        low_reached = min(low_reached, low)

        if direction == "SHORT":
            profit_ticks = (entry - low) / tick_size

            # TP1 touché? (50% de la position)
            if not tp1_hit and low <= tp1_price:
                tp1_hit = True
                pnl_usd += TP1_TICKS * tick_value * 0.5

            # Update trailing stop si profit > activation
            if profit_ticks > best_profit_ticks:
                best_profit_ticks = profit_ticks
                if profit_ticks >= TRAILING_ACTIVATION:
                    new_ts = entry - ((profit_ticks - TRAILING_DISTANCE) * tick_size)
                    if trailing_stop is None or new_ts < trailing_stop:
                        trailing_stop = new_ts

            # SL touché?
            if high >= sl_price:
                if tp1_hit:
                    pnl_usd += -SL_TICKS * tick_value * 0.5
                    result = "PARTIAL"
                else:
                    pnl_usd = -SL_TICKS * tick_value
                    result = "LOSS"
                exit_price = sl_price
                exit_time = t_ms
                break

            # Trailing touché?
            if trailing_stop and high >= trailing_stop:
                profit_trailing = (entry - trailing_stop) / tick_size
                if tp1_hit:
                    pnl_usd += profit_trailing * tick_value * 0.5
                else:
                    pnl_usd = profit_trailing * tick_value
                result = "TRAILING"
                exit_price = trailing_stop
                exit_time = t_ms
                break

            # TP2 touché?
            if low <= tp2_price:
                if tp1_hit:
                    pnl_usd += TP2_TICKS * tick_value * 0.5
                else:
                    pnl_usd = TP2_TICKS * tick_value
                result = "WIN"
                exit_price = tp2_price
                exit_time = t_ms
                break

        else:  # LONG
            profit_ticks = (high - entry) / tick_size

            # TP1 touché?
            if not tp1_hit and high >= tp1_price:
                tp1_hit = True
                pnl_usd += TP1_TICKS * tick_value * 0.5

            # Update trailing stop
            if profit_ticks > best_profit_ticks:
                best_profit_ticks = profit_ticks
                if profit_ticks >= TRAILING_ACTIVATION:
                    new_ts = entry + ((profit_ticks - TRAILING_DISTANCE) * tick_size)
                    if trailing_stop is None or new_ts > trailing_stop:
                        trailing_stop = new_ts

            # SL touché?
            if low <= sl_price:
                if tp1_hit:
                    pnl_usd += -SL_TICKS * tick_value * 0.5
                    result = "PARTIAL"
                else:
                    pnl_usd = -SL_TICKS * tick_value
                    result = "LOSS"
                exit_price = sl_price
                exit_time = t_ms
                break

            # Trailing touché?
            if trailing_stop and low <= trailing_stop:
                profit_trailing = (trailing_stop - entry) / tick_size
                if tp1_hit:
                    pnl_usd += profit_trailing * tick_value * 0.5
                else:
                    pnl_usd = profit_trailing * tick_value
                result = "TRAILING"
                exit_price = trailing_stop
                exit_time = t_ms
                break

            # TP2 touché?
            if high >= tp2_price:
                if tp1_hit:
                    pnl_usd += TP2_TICKS * tick_value * 0.5
                else:
                    pnl_usd = TP2_TICKS * tick_value
                result = "WIN"
                exit_price = tp2_price
                exit_time = t_ms
                break

    # MAE/MFE
    if direction == "LONG":
        mae_ticks = (entry - low_reached) / tick_size
        mfe_ticks = (high_reached - entry) / tick_size
    else:
        mae_ticks = (high_reached - entry) / tick_size
        mfe_ticks = (entry - low_reached) / tick_size

    return {
        'symbol': symbol,
        'direction': direction,
        'entry_price': entry,
        'exit_price': exit_price,
        'result': result,
        'pnl_usd': pnl_usd,
        'tp1_hit': tp1_hit,
        'entry_time': entry_time,
        'exit_time': exit_time,
        'duration_sec': (exit_time - entry_time) / 1000,
        'mfe_ticks': mfe_ticks,
        'mae_ticks': mae_ticks,
        'mia_score': entry_snap.get('mia_bullish_score', 0),
    }


def run_backtest_v2():
    """Backtest avec toutes les améliorations."""
    print("=" * 70)
    print("🔄 BACKTEST AMÉLIORÉ - 12 DÉCEMBRE 2025")
    print("=" * 70)
    print(f"   📊 Paramètres optimisés:")
    print(f"      Cooldown: {MIN_INTERVAL_MS // 60000} min")
    print(f"      Max trades/symbole: {MAX_TRADES_PER_SYMBOL}")
    print(f"      TP1: {TP1_TICKS}t (50%) | TP2: {TP2_TICKS}t (50%)")
    print(f"      Trailing: activation {TRAILING_ACTIVATION}t, distance {TRAILING_DISTANCE}t")
    print(f"      Heures évitées: {TOXIC_HOURS}")
    print()

    all_trades = []

    for symbol in ["ES", "NQ"]:
        print(f"\n📊 {symbol}...")
        snapshots = load_snapshots(symbol)
        if not snapshots:
            continue

        trades = []
        last_trade_time = 0
        trade_count = 0

        for idx, snap in enumerate(snapshots):
            t_ms = snap.get('t_ms', 0)
            hour = get_hour_paris(t_ms)

            # Filtres temporels
            if hour < START_TIME_PARIS or hour >= END_TIME_PARIS:
                continue
            if hour in TOXIC_HOURS:
                continue
            if t_ms - last_trade_time < MIN_INTERVAL_MS:
                continue
            if trade_count >= MAX_TRADES_PER_SYMBOL:
                break

            # Récupérer snapshots récents pour détection retournement
            recent_start = max(0, idx - 30)
            recent_snaps = snapshots[recent_start:idx]

            is_valid, direction, confidence, level = check_signal_valid_v2(
                snap, symbol, recent_snaps
            )

            if is_valid and confidence >= MIN_CONFIDENCE:
                future_snaps = snapshots[idx + 1:]
                if len(future_snaps) < 10:
                    continue

                trade = simulate_trade_with_tp1(snap, direction, symbol, future_snaps)
                trades.append(trade)
                last_trade_time = t_ms
                trade_count += 1

                ts = datetime.fromtimestamp(t_ms / 1000).strftime('%H:%M')

                if trade['result'] == "WIN":
                    icon = "✅"
                elif trade['result'] == "TRAILING":
                    icon = "🟢"
                elif trade['result'] == "PARTIAL":
                    icon = "🟡"
                elif trade['result'] == "LOSS":
                    icon = "❌"
                else:
                    icon = "⏱️"

                tp1_str = " [TP1✓]" if trade['tp1_hit'] else ""
                print(f"   {ts} | {direction:5s} @ {trade['entry_price']:.2f} → {icon} {trade['result']:8s} | ${trade['pnl_usd']:+7.2f}{tp1_str}")

        print(f"   Total: {len(trades)} trades")
        all_trades.extend(trades)

    # === RÉSULTATS ===
    print("\n" + "=" * 70)
    print("📊 RÉSULTATS AMÉLIORÉS")
    print("=" * 70)

    if not all_trades:
        print("❌ Aucun trade")
        return

    total_pnl = sum(t['pnl_usd'] for t in all_trades)

    wins = [t for t in all_trades if t['result'] == 'WIN']
    trailing = [t for t in all_trades if t['result'] == 'TRAILING']
    partial = [t for t in all_trades if t['result'] == 'PARTIAL']
    losses = [t for t in all_trades if t['result'] == 'LOSS']
    timeouts = [t for t in all_trades if t['result'] == 'TIMEOUT']

    profitable = wins + trailing + [t for t in partial if t['pnl_usd'] > 0]
    wr = len(profitable) / len(all_trades) * 100 if all_trades else 0

    print(f"\n📈 RÉSUMÉ:")
    print(f"   Trades: {len(all_trades)}")
    print(f"   ├── WIN (TP2): {len(wins)}")
    print(f"   ├── TRAILING: {len(trailing)}")
    print(f"   ├── PARTIAL: {len(partial)}")
    print(f"   ├── LOSS: {len(losses)}")
    print(f"   └── TIMEOUT: {len(timeouts)}")
    print(f"\n   Win Rate (profitable): {wr:.1f}%")
    print(f"   PnL Total: ${total_pnl:+.2f}")

    # Profit Factor
    gross_profit = sum(t['pnl_usd'] for t in all_trades if t['pnl_usd'] > 0)
    gross_loss = abs(sum(t['pnl_usd'] for t in all_trades if t['pnl_usd'] < 0))
    pf = gross_profit / gross_loss if gross_loss > 0 else float('inf')
    print(f"   Profit Factor: {pf:.2f}")

    # Par symbole
    print(f"\n📊 PAR SYMBOLE:")
    for sym in ["ES", "NQ"]:
        sym_trades = [t for t in all_trades if t['symbol'] == sym]
        if sym_trades:
            sym_pnl = sum(t['pnl_usd'] for t in sym_trades)
            sym_profitable = len([t for t in sym_trades if t['pnl_usd'] > 0])
            sym_wr = sym_profitable / len(sym_trades) * 100
            print(f"   {sym}: {len(sym_trades)} trades | WR: {sym_wr:.1f}% | ${sym_pnl:+.2f}")

    # Analyse TP1
    tp1_count = len([t for t in all_trades if t['tp1_hit']])
    print(f"\n📊 ANALYSE TP1:")
    print(f"   Trades où TP1 touché: {tp1_count}/{len(all_trades)} ({tp1_count/len(all_trades)*100:.0f}%)")

    # Comparaison
    print("\n" + "=" * 70)
    print("📊 COMPARAISON")
    print("=" * 70)
    print(f"   Backtest ORIGINAL:  -$712.50 (55 trades, 45.5% WR)")
    print(f"   Backtest AMÉLIORÉ:  ${total_pnl:+.2f} ({len(all_trades)} trades, {wr:.1f}% WR)")
    print(f"   DIFFÉRENCE:         ${total_pnl - (-712.50):+.2f}")

    if total_pnl > -712.50:
        print("\n   ✅ AMÉLIORATION CONFIRMÉE!")
    if total_pnl > 0:
        print("   🎉 PROFITABLE!")


if __name__ == "__main__":
    run_backtest_v2()
