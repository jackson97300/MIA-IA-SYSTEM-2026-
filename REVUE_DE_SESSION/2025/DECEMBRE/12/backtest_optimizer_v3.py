#!/usr/bin/env python3

"""

🚀 BACKTEST OPTIMIZER V3 - VERSION LÉGÈRE

Ne fait PAS planter le PC!



OPTIMISATIONS:

1. Seulement ~50-100 combinaisons (pas 41,000!)

2. Barre de progression

3. Limite mémoire

4. Focus sur les paramètres IMPORTANTS seulement

"""



import json

from pathlib import Path

from typing import Dict, List, Tuple, Optional

from dataclasses import dataclass

from collections import defaultdict

import sys

import gc



# ═══════════════════════════════════════════════════════════════════════════════

#                           CONFIGURATION

# ═══════════════════════════════════════════════════════════════════════════════



DATA_BASE_PATH = Path("D:/MIA_IA_system/DATA_SIERRA_CHART/DATA_2025")



NOVEMBER_DAYS = [

    "20251105", "20251106", "20251107", "20251110", "20251111",

    "20251112", "20251113", "20251114", "20251117", "20251118",

    "20251119", "20251120", "20251121", "20251124", "20251125",

    "20251126", "20251127", "20251130",

]



DECEMBER_DAYS = [

    "20251201", "20251202", "20251203", "20251204", "20251205",

    "20251206", "20251207", "20251208", "20251209", "20251210",

    "20251211", "20251212", "20251213",

]



DAYS_TO_TEST = NOVEMBER_DAYS + DECEMBER_DAYS



SYMBOLS = {

    "ES": {"chart_id": 3, "tick_size": 0.25, "tick_value": 12.50},

    "NQ": {"chart_id": 9, "tick_size": 0.25, "tick_value": 5.00},

}



# Sessions

TRADING_SESSIONS = {

    'london': {'start': (8, 0), 'end': (11, 0)},

    'us_morning': {'start': (15, 50), 'end': (17, 0)},

    'power_hour': {'start': (20, 0), 'end': (21, 25)},

}



BLOCKED_PERIODS = {

    'overnight': ((0, 0), (8, 0)),

    'pre_market': ((11, 0), (15, 50)),

    'lunch': ((17, 0), (20, 0)),

    'hard_stop': ((21, 25), (24, 0)),

}



# 21 niveaux MenthorQ

MENTHORQ_LEVELS = [

    'gex_1', 'gex_2', 'gex_3', 'gex_4', 'gex_5',

    'gamma_wall_0dte', 'gamma_wall_level',

    'hvl', 'hvl_0dte',

    'blind_spot_1', 'blind_spot_2', 'blind_spot_3',

    'call_resistance', 'put_support',

    'call_resistance_0dte', 'put_support_0dte',

    'vwap', 'vwap_up1', 'vwap_dn1', 'vwap_up2', 'vwap_dn2',

]



# ═══════════════════════════════════════════════════════════════════════════════

#              GRILLE RÉDUITE - SEULEMENT ~20 COMBINAISONS!

# ═══════════════════════════════════════════════════════════════════════════════



# On teste SEULEMENT les paramètres les plus importants

CONFIGS_TO_TEST = [

    # Format: (name, tp, sl, cooldown, max_dist_es, max_dist_nq, mia_threshold, confidence)



    # === TP UNIQUE (pas de partial) ===

    ("TP_1:1_SL10", 10, 10, 20, 17, 22, 0.22, 0.46),

    ("TP_1.5:1_SL8", 12, 8, 20, 17, 22, 0.22, 0.46),

    ("TP_2:1_SL8", 16, 8, 20, 17, 22, 0.22, 0.46),

    ("TP_2:1_SL10", 20, 10, 20, 17, 22, 0.22, 0.46),

    ("TP_2.5:1_SL6", 15, 6, 20, 17, 22, 0.22, 0.46),

    ("TP_3:1_SL5", 15, 5, 20, 17, 22, 0.22, 0.46),



    # === Variations de cooldown ===

    ("TP_2:1_CD15", 16, 8, 15, 17, 22, 0.22, 0.46),

    ("TP_2:1_CD25", 16, 8, 25, 17, 22, 0.22, 0.46),

    ("TP_2:1_CD30", 16, 8, 30, 17, 22, 0.22, 0.46),



    # === Variations de distance ===

    ("TP_2:1_DIST12", 16, 8, 20, 12, 15, 0.22, 0.46),

    ("TP_2:1_DIST20", 16, 8, 20, 20, 25, 0.22, 0.46),



    # === Variations de MIA threshold ===

    ("TP_2:1_MIA20", 16, 8, 20, 17, 22, 0.20, 0.46),

    ("TP_2:1_MIA25", 16, 8, 20, 17, 22, 0.25, 0.46),

    ("TP_2:1_MIA30", 16, 8, 20, 17, 22, 0.30, 0.46),



    # === Variations de confidence ===

    ("TP_2:1_CONF40", 16, 8, 20, 17, 22, 0.22, 0.40),

    ("TP_2:1_CONF50", 16, 8, 20, 17, 22, 0.22, 0.50),



    # === SCALPER ===

    ("SCALPER_8_5", 8, 5, 15, 17, 22, 0.20, 0.45),

    ("SCALPER_10_6", 10, 6, 15, 17, 22, 0.20, 0.45),



    # === CONSERVATIVE ===

    ("CONSERV_14_7", 14, 7, 25, 12, 15, 0.25, 0.50),

    ("CONSERV_12_6", 12, 6, 25, 12, 15, 0.25, 0.50),

]



# ═══════════════════════════════════════════════════════════════════════════════

#                           FONCTIONS UTILITAIRES

# ═══════════════════════════════════════════════════════════════════════════════



def progress_bar(current: int, total: int, prefix: str = "", suffix: str = "", length: int = 40):

    percent = current / total if total > 0 else 0

    filled = int(length * percent)

    bar = "█" * filled + "░" * (length - filled)

    sys.stdout.write(f"\r{prefix} |{bar}| {percent*100:.1f}% {suffix}")

    sys.stdout.flush()

    if current >= total:

        print()





def get_month_folder(day: str) -> str:

    return "NOVEMBRE" if day[4:6] == "11" else "DECEMBRE"





def find_data_file(day: str, symbol: str) -> Optional[Path]:

    config = SYMBOLS[symbol]

    month_folder = get_month_folder(day)

    for contract in [f"{symbol}Z25", f"{symbol}H25"]:

        path = DATA_BASE_PATH / month_folder / day / f"CHART_{config['chart_id']}" / "ML_READY" / f"ml_{contract}_FUT_CME_{config['chart_id']}.jsonl"

        if path.exists():

            return path

    return None





def load_snapshots(file_path: Path) -> List[Dict]:

    snapshots = []

    try:

        with open(file_path, 'r', encoding='utf-8') as f:

            for line in f:

                if line.strip():

                    try:

                        snapshots.append(json.loads(line))

                    except:

                        continue

    except:

        return []

    snapshots.sort(key=lambda x: x.get('t_ms', 0))

    return snapshots





def get_paris_time(t_ms: int) -> Tuple[int, int]:

    total_sec = t_ms // 1000

    total_min = total_sec // 60

    hour_utc = (total_min // 60) % 24

    minute = total_min % 60

    hour_paris = (hour_utc + 1) % 24

    return hour_paris, minute





def time_to_minutes(h: int, m: int) -> int:

    return h * 60 + m





def is_in_trading_session(hour: int, minute: int) -> Tuple[bool, str]:

    time_val = time_to_minutes(hour, minute)



    for name, (start, end) in BLOCKED_PERIODS.items():

        s = time_to_minutes(start[0], start[1])

        e = time_to_minutes(end[0], end[1])

        if s <= time_val < e:

            return False, f"BLOCKED"



    for name, session in TRADING_SESSIONS.items():

        s = time_to_minutes(session['start'][0], session['start'][1])

        e = time_to_minutes(session['end'][0], session['end'][1])

        if s <= time_val < e:

            return True, name



    return False, "OFF_HOURS"





def find_nearest_level(snapshot: Dict, symbol: str) -> Tuple[str, float, float]:

    mid = snapshot.get('mid', 0)

    tick_size = SYMBOLS[symbol]['tick_size']



    nearest_name = ""

    nearest_dist = float('inf')



    for level_name in MENTHORQ_LEVELS:

        price = snapshot.get(level_name)

        if price and price > 0:

            dist = abs(mid - price) / tick_size

            if dist < nearest_dist:

                nearest_dist = dist

                nearest_name = level_name



    return nearest_name, nearest_dist



# ═══════════════════════════════════════════════════════════════════════════════

#                           BACKTEST SIMPLE

# ═══════════════════════════════════════════════════════════════════════════════



@dataclass

class ConfigResult:

    name: str

    tp: int

    sl: int

    trades: int

    wins: int

    losses: int

    pnl: float

    win_rate: float

    profit_factor: float

    avg_win: float

    avg_loss: float

    es_trades: int

    es_pnl: float

    nq_trades: int

    nq_pnl: float





def run_backtest(config_name: str, tp: int, sl: int, cooldown: int,

                 max_dist_es: int, max_dist_nq: int, mia_threshold: float,

                 min_confidence: float, all_data: Dict) -> ConfigResult:

    """Backtest simple et rapide."""



    trades = []

    cooldown_ms = cooldown * 60 * 1000



    for day, day_data in all_data.items():

        for symbol in ["ES", "NQ"]:

            snapshots = day_data.get(symbol, [])

            if not snapshots:

                continue



            tick_size = SYMBOLS[symbol]['tick_size']

            tick_value = SYMBOLS[symbol]['tick_value']

            max_dist = max_dist_es if symbol == "ES" else max_dist_nq



            last_trade_time = 0



            for i, snap in enumerate(snapshots):

                t_ms = snap.get('t_ms', 0)



                # Cooldown

                if t_ms - last_trade_time < cooldown_ms:

                    continue



                # Session

                hour, minute = get_paris_time(t_ms)

                in_session, session = is_in_trading_session(hour, minute)

                if not in_session:

                    continue



                # Distance

                level_name, distance = find_nearest_level(snap, symbol)

                if distance > max_dist:

                    continue



                # Confidence

                menthorq_score = max(0, 1 - distance / 25)

                if level_name in ['gex_1', 'gex_2', 'hvl', 'vwap']:

                    menthorq_score = min(1.0, menthorq_score * 1.25)



                delta = snap.get('delta', 0) or 0

                orderflow_score = min(1.0, abs(delta) / 500) * 0.5 + 0.25



                mia_score = snap.get('mia_bullish_score', 0) or 0

                context_score = min(1.0, abs(mia_score) * 2)



                confidence = menthorq_score * 0.50 + orderflow_score * 0.30 + context_score * 0.20



                if confidence < min_confidence:

                    continue



                # Direction

                if mia_score > mia_threshold:

                    direction = "LONG"

                elif mia_score < -mia_threshold:

                    direction = "SHORT"

                else:

                    continue



                # Simuler trade (simple: TP ou SL)

                mid = snap.get('mid', 0)

                future = snapshots[i+1:i+301]

                if len(future) < 10:

                    continue



                if direction == "LONG":

                    tp_price = mid + tp * tick_size

                    sl_price = mid - sl * tick_size

                else:

                    tp_price = mid - tp * tick_size

                    sl_price = mid + sl * tick_size



                result = None

                for future_snap in future:

                    high = future_snap.get('high') or future_snap.get('mid', mid)

                    low = future_snap.get('low') or future_snap.get('mid', mid)



                    if direction == "LONG":

                        if high >= tp_price:

                            result = ("WIN", tp * tick_value)

                            break

                        if low <= sl_price:

                            result = ("LOSS", -sl * tick_value)

                            break

                    else:

                        if low <= tp_price:

                            result = ("WIN", tp * tick_value)

                            break

                        if high >= sl_price:

                            result = ("LOSS", -sl * tick_value)

                            break



                if result:

                    trades.append({

                        'symbol': symbol,

                        'result': result[0],

                        'pnl': result[1],

                    })

                    last_trade_time = t_ms



    # Calculer stats

    if not trades:

        return ConfigResult(

            name=config_name, tp=tp, sl=sl,

            trades=0, wins=0, losses=0, pnl=0,

            win_rate=0, profit_factor=0, avg_win=0, avg_loss=0,

            es_trades=0, es_pnl=0, nq_trades=0, nq_pnl=0

        )



    wins = [t for t in trades if t['result'] == "WIN"]

    losses = [t for t in trades if t['result'] == "LOSS"]



    total_pnl = sum(t['pnl'] for t in trades)

    win_rate = len(wins) / len(trades) * 100 if trades else 0



    gross_profit = sum(t['pnl'] for t in wins)

    gross_loss = abs(sum(t['pnl'] for t in losses))

    pf = gross_profit / gross_loss if gross_loss > 0 else 999



    avg_win = gross_profit / len(wins) if wins else 0

    avg_loss = gross_loss / len(losses) if losses else 0



    es_trades = [t for t in trades if t['symbol'] == "ES"]

    nq_trades = [t for t in trades if t['symbol'] == "NQ"]



    return ConfigResult(

        name=config_name, tp=tp, sl=sl,

        trades=len(trades),

        wins=len(wins),

        losses=len(losses),

        pnl=total_pnl,

        win_rate=win_rate,

        profit_factor=pf,

        avg_win=avg_win,

        avg_loss=avg_loss,

        es_trades=len(es_trades),

        es_pnl=sum(t['pnl'] for t in es_trades),

        nq_trades=len(nq_trades),

        nq_pnl=sum(t['pnl'] for t in nq_trades),

    )



# ═══════════════════════════════════════════════════════════════════════════════

#                           MAIN

# ═══════════════════════════════════════════════════════════════════════════════



def main():

    print("=" * 90)

    print("          🚀 BACKTEST OPTIMIZER V3 - VERSION LÉGÈRE")

    print("          Ne fait PAS planter le PC!")

    print("=" * 90)

    print(f"""

📊 Seulement {len(CONFIGS_TO_TEST)} configurations à tester (pas 41,000!)



⏰ SESSIONS:

   - London:     08:00 - 11:00

   - US Morning: 15:50 - 17:00

   - Power Hour: 20:00 - 21:25



💰 1 contrat MINI: ES=$12.50/tick, NQ=$5.00/tick

""")



    # Charger données

    print("📂 Chargement des données...")

    all_data = {}

    days_loaded = 0

    total_snapshots = 0



    for i, day in enumerate(DAYS_TO_TEST):

        progress_bar(i + 1, len(DAYS_TO_TEST), "Chargement", f"{day}")

        all_data[day] = {}

        has_data = False



        for symbol in ["ES", "NQ"]:

            file_path = find_data_file(day, symbol)

            if file_path:

                snapshots = load_snapshots(file_path)

                all_data[day][symbol] = snapshots

                total_snapshots += len(snapshots)

                if snapshots:

                    has_data = True



        if has_data:

            days_loaded += 1



    print(f"\n   📊 {days_loaded} jours | {total_snapshots:,} snapshots")



    if days_loaded == 0:

        print("\n❌ Aucune donnée!")

        return



    # Backtests

    print("\n" + "=" * 90)

    print("                    🧪 EXÉCUTION DES BACKTESTS")

    print("=" * 90)



    results = []

    total_configs = len(CONFIGS_TO_TEST)



    for i, (name, tp, sl, cooldown, dist_es, dist_nq, mia_th, conf) in enumerate(CONFIGS_TO_TEST):

        progress_bar(i + 1, total_configs, "Backtest", f"{name}")



        result = run_backtest(

            name, tp, sl, cooldown, dist_es, dist_nq, mia_th, conf, all_data

        )

        results.append(result)



        # Libérer mémoire périodiquement

        if (i + 1) % 10 == 0:

            gc.collect()



    # Résultats

    print("\n" + "=" * 90)

    print("                    📊 RÉSULTATS")

    print("=" * 90)



    # Trier par PnL

    results_sorted = sorted(results, key=lambda x: x.pnl, reverse=True)



    print(f"\n{'Config':<20} {'TP':>4} {'SL':>4} {'R:R':>5} {'Trades':>7} {'WR%':>6} {'PnL':>12} {'PF':>6} {'AvgWin':>8} {'AvgLoss':>9}")

    print("-" * 100)



    for r in results_sorted:

        rr = r.tp / r.sl if r.sl > 0 else 0

        marker = "🏆" if r.pnl > 0 and r.pnl == results_sorted[0].pnl else "  "

        profitable = "✅" if r.pnl > 0 else "❌"

        print(f"{marker}{r.name:<18} {r.tp:>4} {r.sl:>4} {rr:>4.1f}:1 {r.trades:>7} {r.win_rate:>5.1f}% ${r.pnl:>+10,.0f} {r.profit_factor:>5.2f} ${r.avg_win:>+6.0f} ${r.avg_loss:>+7.0f} {profitable}")



    print("-" * 100)



    # Meilleure config

    best = results_sorted[0] if results_sorted else None



    if best and best.pnl > 0:

        rr = best.tp / best.sl if best.sl > 0 else 0

        breakeven_wr = 100 / (1 + rr)



        print(f"""

╔══════════════════════════════════════════════════════════════════════════════════╗

║  🏆 MEILLEURE CONFIG: {best.name:<55} ║

╠══════════════════════════════════════════════════════════════════════════════════╣

║  TP: {best.tp} ticks | SL: {best.sl} ticks | R:R: {rr:.1f}:1                                       ║

║  WR Breakeven: {breakeven_wr:.1f}% | WR Actuel: {best.win_rate:.1f}% | Marge: {best.win_rate - breakeven_wr:+.1f}%                      ║

╠══════════════════════════════════════════════════════════════════════════════════╣

║  Trades:        {best.trades:<10}                                                       ║

║  P&L Total:     ${best.pnl:<+10,.0f}                                                    ║

║  Profit Factor: {best.profit_factor:<10.2f}                                                    ║

║  Avg Win:       ${best.avg_win:<+10.0f}                                                    ║

║  Avg Loss:      ${best.avg_loss:<+10.0f}                                                    ║

╠══════════════════════════════════════════════════════════════════════════════════╣

║  ES: {best.es_trades} trades, ${best.es_pnl:+,.0f}                                                     ║

║  NQ: {best.nq_trades} trades, ${best.nq_pnl:+,.0f}                                                     ║

╚══════════════════════════════════════════════════════════════════════════════════╝



🚀 PARAMÈTRES POUR PRODUCTION:

────────────────────────────────

TP_TICKS = {best.tp}

SL_TICKS = {best.sl}

# Pas de TP partiel, pas de trailing - SIMPLE!

""")

    else:

        print("\n⚠️ Aucune config rentable trouvée. Ajuster les paramètres de signal.")



    # Analyse R:R

    print("\n" + "=" * 90)

    print("                    📈 ANALYSE PAR R:R")

    print("=" * 90)



    rr_groups = defaultdict(list)

    for r in results:

        rr = round(r.tp / r.sl, 1) if r.sl > 0 else 0

        rr_groups[rr].append(r)



    print(f"\n{'R:R':>6} {'Configs':>8} {'Avg WR%':>8} {'Avg PnL':>12} {'Best PnL':>12} {'Rentables':>10}")

    print("-" * 70)



    for rr in sorted(rr_groups.keys()):

        group = rr_groups[rr]

        avg_wr = sum(r.win_rate for r in group) / len(group)

        avg_pnl = sum(r.pnl for r in group) / len(group)

        best_pnl = max(r.pnl for r in group)

        rentables = len([r for r in group if r.pnl > 0])



        print(f"{rr:>5.1f}:1 {len(group):>8} {avg_wr:>7.1f}% ${avg_pnl:>+10,.0f} ${best_pnl:>+10,.0f} {rentables}/{len(group):>8}")



    # CSV

    csv_path = Path("backtest_optimizer_v3_results.csv")

    with open(csv_path, 'w') as f:

        f.write("Config,TP,SL,RR,Trades,WR,PnL,PF,AvgWin,AvgLoss,ES_Trades,ES_PnL,NQ_Trades,NQ_PnL\n")

        for r in results_sorted:

            rr = r.tp / r.sl if r.sl > 0 else 0

            f.write(f"{r.name},{r.tp},{r.sl},{rr:.2f},{r.trades},{r.win_rate:.1f},{r.pnl:.2f},{r.profit_factor:.2f},{r.avg_win:.2f},{r.avg_loss:.2f},{r.es_trades},{r.es_pnl:.2f},{r.nq_trades},{r.nq_pnl:.2f}\n")



    print(f"\n✅ Résultats: {csv_path}")

    print("\n✅ BACKTEST TERMINÉ!")





if __name__ == "__main__":

    main()









