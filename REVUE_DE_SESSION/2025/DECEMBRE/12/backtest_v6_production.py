#!/usr/bin/env python3

"""

═══════════════════════════════════════════════════════════════════════════════

                    BACKTEST V6 - CONFIG PRODUCTION OPTIMISÉE

═══════════════════════════════════════════════════════════════════════════════



📊 CONFIG ACTUELLE (Production):

   ES:  TP=15, SL=15, R:R 1:1    → WR breakeven 50%

   NQ:  TP=31, SL=25, R:R 1.24:1 → WR breakeven 44.6%

   RTY: TP=40, SL=30, R:R 1.33:1 → WR breakeven 42.9%



🎯 OBJECTIF: Garder les SL réalistes, tester différents TP pour améliorer R:R



📋 TESTS:

   - Config actuelle (baseline)

   - TP augmentés (R:R 1.5:1, 2:1)

   - TP réduits (scalper rapide)

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

#              CONFIGS À TESTER - SL RÉALISTES + VARIATIONS TP

# ═══════════════════════════════════════════════════════════════════════════════



# Format: (name, symbol, tp, sl, cooldown, max_dist, mia_threshold, confidence)



CONFIGS_TO_TEST = [

    # ═══════════════════════════════════════════════════════════════

    # ES - SL FIXE 15 ticks ($187.50)

    # ═══════════════════════════════════════════════════════════════



    # Config actuelle

    ("ES_CURRENT_15_15", "ES", 15, 15, 20, 17, 0.22, 0.46),      # R:R 1:1



    # TP augmentés (meilleur R:R)

    ("ES_TP20_SL15", "ES", 20, 15, 20, 17, 0.22, 0.46),          # R:R 1.33:1

    ("ES_TP22_SL15", "ES", 22, 15, 20, 17, 0.22, 0.46),          # R:R 1.5:1

    ("ES_TP25_SL15", "ES", 25, 15, 20, 17, 0.22, 0.46),          # R:R 1.67:1

    ("ES_TP30_SL15", "ES", 30, 15, 20, 17, 0.22, 0.46),          # R:R 2:1



    # TP réduit (scalper)

    ("ES_TP12_SL15", "ES", 12, 15, 20, 17, 0.22, 0.46),          # R:R 0.8:1

    ("ES_TP10_SL15", "ES", 10, 15, 20, 17, 0.22, 0.46),          # R:R 0.67:1



    # SL plus large

    ("ES_TP20_SL20", "ES", 20, 20, 20, 17, 0.22, 0.46),          # R:R 1:1

    ("ES_TP30_SL20", "ES", 30, 20, 20, 17, 0.22, 0.46),          # R:R 1.5:1



    # ═══════════════════════════════════════════════════════════════

    # NQ - SL FIXE 25 ticks ($125)

    # ═══════════════════════════════════════════════════════════════



    # Config actuelle

    ("NQ_CURRENT_31_25", "NQ", 31, 25, 20, 22, 0.22, 0.46),      # R:R 1.24:1



    # TP augmentés (meilleur R:R)

    ("NQ_TP38_SL25", "NQ", 38, 25, 20, 22, 0.22, 0.46),          # R:R 1.5:1

    ("NQ_TP40_SL25", "NQ", 40, 25, 20, 22, 0.22, 0.46),          # R:R 1.6:1

    ("NQ_TP45_SL25", "NQ", 45, 25, 20, 22, 0.22, 0.46),          # R:R 1.8:1

    ("NQ_TP50_SL25", "NQ", 50, 25, 20, 22, 0.22, 0.46),          # R:R 2:1



    # TP réduit (scalper)

    ("NQ_TP25_SL25", "NQ", 25, 25, 20, 22, 0.22, 0.46),          # R:R 1:1

    ("NQ_TP20_SL25", "NQ", 20, 25, 20, 22, 0.22, 0.46),          # R:R 0.8:1



    # SL différents

    ("NQ_TP30_SL20", "NQ", 30, 20, 20, 22, 0.22, 0.46),          # R:R 1.5:1

    ("NQ_TP40_SL20", "NQ", 40, 20, 20, 22, 0.22, 0.46),          # R:R 2:1

    ("NQ_TP45_SL30", "NQ", 45, 30, 20, 22, 0.22, 0.46),          # R:R 1.5:1

    ("NQ_TP60_SL30", "NQ", 60, 30, 20, 22, 0.22, 0.46),          # R:R 2:1



    # ═══════════════════════════════════════════════════════════════

    # VARIATIONS AUTRES PARAMÈTRES (NQ SL25 comme base)

    # ═══════════════════════════════════════════════════════════════



    # Cooldown

    ("NQ_TP38_CD15", "NQ", 38, 25, 15, 22, 0.22, 0.46),          # Cooldown 15min

    ("NQ_TP38_CD30", "NQ", 38, 25, 30, 22, 0.22, 0.46),          # Cooldown 30min



    # Distance

    ("NQ_TP38_DIST15", "NQ", 38, 25, 20, 15, 0.22, 0.46),        # Distance stricte

    ("NQ_TP38_DIST30", "NQ", 38, 25, 20, 30, 0.22, 0.46),        # Distance large



    # MIA threshold

    ("NQ_TP38_MIA15", "NQ", 38, 25, 20, 22, 0.15, 0.46),         # MIA sensible

    ("NQ_TP38_MIA30", "NQ", 38, 25, 20, 22, 0.30, 0.46),         # MIA strict



    # Confidence

    ("NQ_TP38_CONF40", "NQ", 38, 25, 20, 22, 0.22, 0.40),        # Conf basse

    ("NQ_TP38_CONF50", "NQ", 38, 25, 20, 22, 0.22, 0.50),        # Conf haute

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

            return False, "BLOCKED"



    for name, session in TRADING_SESSIONS.items():

        s = time_to_minutes(session['start'][0], session['start'][1])

        e = time_to_minutes(session['end'][0], session['end'][1])

        if s <= time_val < e:

            return True, name



    return False, "OFF_HOURS"





def find_nearest_level(snapshot: Dict, symbol: str) -> Tuple[str, float]:

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

#                           BACKTEST

# ═══════════════════════════════════════════════════════════════════════════════



@dataclass

class ConfigResult:

    name: str

    symbol: str

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

    tp_dollars: float

    sl_dollars: float





def run_backtest(config_name: str, symbol: str, tp: int, sl: int, cooldown: int,

                 max_dist: int, mia_threshold: float, min_confidence: float,

                 all_data: Dict) -> ConfigResult:

    """Backtest avec TP unique."""



    trades = []

    cooldown_ms = cooldown * 60 * 1000

    tick_size = SYMBOLS[symbol]['tick_size']

    tick_value = SYMBOLS[symbol]['tick_value']



    for day, day_data in all_data.items():

        snapshots = day_data.get(symbol, [])

        if not snapshots:

            continue



        last_trade_time = 0



        for i, snap in enumerate(snapshots):

            t_ms = snap.get('t_ms', 0)



            if t_ms - last_trade_time < cooldown_ms:

                continue



            hour, minute = get_paris_time(t_ms)

            in_session, session = is_in_trading_session(hour, minute)

            if not in_session:

                continue



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



            # Simuler trade

            mid = snap.get('mid', 0)

            future = snapshots[i+1:i+901]  # 15 minutes

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

                trades.append({'result': result[0], 'pnl': result[1]})

                last_trade_time = t_ms



    # Stats

    if not trades:

        return ConfigResult(

            name=config_name, symbol=symbol, tp=tp, sl=sl,

            trades=0, wins=0, losses=0, pnl=0,

            win_rate=0, profit_factor=0, avg_win=0, avg_loss=0,

            tp_dollars=tp * tick_value, sl_dollars=sl * tick_value

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



    return ConfigResult(

        name=config_name, symbol=symbol, tp=tp, sl=sl,

        trades=len(trades), wins=len(wins), losses=len(losses),

        pnl=total_pnl, win_rate=win_rate, profit_factor=pf,

        avg_win=avg_win, avg_loss=avg_loss,

        tp_dollars=tp * tick_value, sl_dollars=sl * tick_value

    )



# ═══════════════════════════════════════════════════════════════════════════════

#                           MAIN

# ═══════════════════════════════════════════════════════════════════════════════



def main():

    print("=" * 95)

    print("          🎯 BACKTEST V6 - CONFIG PRODUCTION OPTIMISÉE")

    print("=" * 95)

    print(f"""

📊 CONFIG ACTUELLE (Production):

   ┌─────────┬────────┬────────┬─────────┬───────────┬───────────┐

   │ Symbole │ TP     │ SL     │ R:R     │ TP $      │ SL $      │

   ├─────────┼────────┼────────┼─────────┼───────────┼───────────┤

   │ ES      │ 15     │ 15     │ 1:1     │ $187.50   │ $187.50   │

   │ NQ      │ 31     │ 25     │ 1.24:1  │ $155.00   │ $125.00   │

   └─────────┴────────┴────────┴─────────┴───────────┴───────────┘



🎯 OBJECTIF: Tester différents TP avec les SL réalistes actuels

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



    # Backtests

    print("\n" + "=" * 95)

    print("                    🧪 EXÉCUTION DES BACKTESTS")

    print("=" * 95)



    results = []

    total_configs = len(CONFIGS_TO_TEST)



    for i, (name, symbol, tp, sl, cooldown, dist, mia_th, conf) in enumerate(CONFIGS_TO_TEST):

        progress_bar(i + 1, total_configs, "Backtest", f"{name}")



        result = run_backtest(name, symbol, tp, sl, cooldown, dist, mia_th, conf, all_data)

        results.append(result)



        if (i + 1) % 10 == 0:

            gc.collect()



    # Résultats par symbole

    for sym in ["ES", "NQ"]:

        sym_results = [r for r in results if r.symbol == sym]

        if not sym_results:

            continue



        sym_results_sorted = sorted(sym_results, key=lambda x: x.pnl, reverse=True)



        print(f"\n{'=' * 95}")

        print(f"                    📊 RÉSULTATS {sym}")

        print(f"{'=' * 95}")



        print(f"\n{'Config':<22} {'TP':>4} {'SL':>4} {'R:R':>5} {'Trades':>7} {'WR%':>6} {'PnL':>12} {'PF':>6} {'TP$':>8} {'SL$':>8}")

        print("-" * 100)



        for r in sym_results_sorted:

            rr = r.tp / r.sl if r.sl > 0 else 0

            wr_be = 100 / (1 + rr) if rr > 0 else 50



            if r.pnl > 0:

                marker = "🏆" if r.pnl == sym_results_sorted[0].pnl else "✅"

            else:

                marker = "❌"



            current = "📍" if "CURRENT" in r.name else "  "



            print(f"{marker}{current}{r.name:<19} {r.tp:>4} {r.sl:>4} {rr:>4.1f}:1 {r.trades:>7} {r.win_rate:>5.1f}% ${r.pnl:>+10,.0f} {r.profit_factor:>5.2f} ${r.tp_dollars:>6.0f} ${r.sl_dollars:>6.0f}")



        print("-" * 100)



        # Meilleure config pour ce symbole

        best = sym_results_sorted[0]

        if best.pnl > 0:

            rr = best.tp / best.sl

            wr_be = 100 / (1 + rr)



            print(f"""

   🏆 MEILLEUR {sym}: {best.name}

      TP={best.tp} (${best.tp_dollars:.0f}) | SL={best.sl} (${best.sl_dollars:.0f}) | R:R={rr:.2f}:1

      Trades={best.trades} | WR={best.win_rate:.1f}% (BE={wr_be:.1f}%) | PnL=${best.pnl:+,.0f}

""")



    # Comparaison config actuelle vs meilleure

    print("\n" + "=" * 95)

    print("                    📈 COMPARAISON ACTUEL vs OPTIMAL")

    print("=" * 95)



    for sym in ["ES", "NQ"]:

        sym_results = [r for r in results if r.symbol == sym]

        current = next((r for r in sym_results if "CURRENT" in r.name), None)

        best = max(sym_results, key=lambda x: x.pnl) if sym_results else None



        if current and best:

            improvement = best.pnl - current.pnl

            print(f"""

   {sym}:

   ├── ACTUEL:  TP={current.tp}, SL={current.sl} → PnL=${current.pnl:+,.0f} | WR={current.win_rate:.1f}%

   ├── OPTIMAL: TP={best.tp}, SL={best.sl} → PnL=${best.pnl:+,.0f} | WR={best.win_rate:.1f}%

   └── GAIN:    ${improvement:+,.0f} ({'+' if improvement > 0 else ''}{improvement/abs(current.pnl)*100 if current.pnl != 0 else 0:.0f}%)

""")



    # CSV

    csv_path = Path("backtest_v6_production_results.csv")

    with open(csv_path, 'w') as f:

        f.write("Config,Symbol,TP,SL,RR,Trades,WR,PnL,PF,TP_USD,SL_USD\n")

        for r in results:

            rr = r.tp / r.sl if r.sl > 0 else 0

            f.write(f"{r.name},{r.symbol},{r.tp},{r.sl},{rr:.2f},{r.trades},{r.win_rate:.1f},{r.pnl:.2f},{r.profit_factor:.2f},{r.tp_dollars:.2f},{r.sl_dollars:.2f}\n")



    print(f"\n✅ Résultats: {csv_path}")

    print("\n✅ BACKTEST TERMINÉ!")





if __name__ == "__main__":

    main()









