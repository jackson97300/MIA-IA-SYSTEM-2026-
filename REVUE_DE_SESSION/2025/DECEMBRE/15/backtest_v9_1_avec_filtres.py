#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
            BACKTEST V9.1 - AVEC DUAL-MODE ET OBSTACLE
═══════════════════════════════════════════════════════════════════════════════

🎯 OBJECTIF: Backtest RÉALISTE incluant TOUS les filtres du LIVE

📊 DIFFÉRENCES vs V9:
   V9:   ML + MenthorQ seuls                    → +$11,350 (467 trades)
   V9.1: ML + MenthorQ + DUAL-MODE + OBSTACLE   → ??? (à mesurer)

🔧 FILTRES AJOUTÉS:
   1. DUAL-MODE: Détection RANGE vs TREND
      - Si RANGE et prix en haut (>67%) → pas de LONG
      - Si RANGE et prix en bas (<33%) → pas de SHORT

   2. OBSTACLE: Vérification niveaux bloquants
      - Si niveau MenthorQ entre entry et TP → trade rejeté

📈 QUESTION CLÉ:
   Quel est le P&L RÉALISTE avec tous les filtres live?

Auteur: MIA IA System
Date: 15 Décembre 2025
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict
import sys

# ═══════════════════════════════════════════════════════════════════════════════
#                           CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

DATA_BASE_PATH = Path("D:/MIA_IA_system/DATA_SIERRA_CHART/DATA_2025")

DAYS_TO_TEST = [
    # Novembre
    "20251105", "20251106", "20251107", "20251110", "20251111",
    "20251112", "20251113", "20251114", "20251117", "20251118",
    "20251119", "20251120", "20251121", "20251124", "20251125",
    "20251126", "20251127",
    # Décembre
    "20251201", "20251202", "20251203", "20251204", "20251205",
    "20251208", "20251209", "20251210", "20251211", "20251212",
]

SYMBOLS = {
    "ES": {"chart_id": 3, "tick_size": 0.25, "tick_value": 12.50, "contracts": ["ESZ25", "ESH25"]},
    "NQ": {"chart_id": 9, "tick_size": 0.25, "tick_value": 5.00, "contracts": ["NQZ25", "NQH25"]},
}

SESSIONS = {
    'LONDON': {'start': (8, 0), 'end': (11, 0), 'name': 'London 8h-11h'},
    'US_MORNING': {'start': (15, 50), 'end': (17, 0), 'name': 'US Morning 15:50-17h'},
    'POWER_HOUR': {'start': (20, 0), 'end': (21, 25), 'name': 'Power Hour 20h-21:25'},
}

# ═══════════════════════════════════════════════════════════════════════════════
#              CONFIGS V9 OPTIMALES (avec MenthorQ)
# ═══════════════════════════════════════════════════════════════════════════════

V9_CONFIGS = {
    'LONDON_ES': {
        'tp_ticks': 12, 'sl_ticks': 12, 'cooldown_min': 15,
        'min_confidence': 0.30, 'min_layer2': 0.15, 'mia_threshold': 0.20,
        'max_distance': 12, 'min_confluence': 1, 'min_level_score': 2,
        'enabled': True,
    },
    'LONDON_NQ': {
        'tp_ticks': 25, 'sl_ticks': 20, 'cooldown_min': 20,
        'min_confidence': 0.65, 'min_layer2': 0.15, 'mia_threshold': 0.20,
        'max_distance': 5, 'min_confluence': 3, 'min_level_score': 0,
        'enabled': False,  # Désactivé - pas assez de données
    },
    'US_MORNING_ES': {
        'tp_ticks': 12, 'sl_ticks': 12, 'cooldown_min': 15,
        'min_confidence': 0.60, 'min_layer2': 0.15, 'mia_threshold': 0.20,
        'max_distance': 5, 'min_confluence': 1, 'min_level_score': 3,
        'enabled': True,
    },
    'US_MORNING_NQ': {
        'tp_ticks': 25, 'sl_ticks': 20, 'cooldown_min': 20,
        'min_confidence': 0.30, 'min_layer2': 0.15, 'mia_threshold': 0.25,
        'max_distance': 15, 'min_confluence': 1, 'min_level_score': 0,
        'enabled': True,
    },
    'POWER_HOUR_ES': {
        'tp_ticks': 12, 'sl_ticks': 12, 'cooldown_min': 15,
        'min_confidence': 0.70, 'min_layer2': 0.15, 'mia_threshold': 0.20,
        'max_distance': 10, 'min_confluence': 1, 'min_level_score': 2,
        'enabled': True,
    },
    'POWER_HOUR_NQ': {
        'tp_ticks': 40, 'sl_ticks': 30, 'cooldown_min': 20,
        'min_confidence': 0.70, 'min_layer2': 0.15, 'mia_threshold': 0.20,
        'max_distance': 15, 'min_confluence': 1, 'min_level_score': 2,
        'enabled': True,
    },
}

# ═══════════════════════════════════════════════════════════════════════════════
#              🆕 CONFIG DUAL-MODE (réplique du live)
# ═══════════════════════════════════════════════════════════════════════════════

DUAL_MODE_CONFIG = {
    'ES': {
        'bias_threshold': 0.30,       # Seuil pour détecter tendance
        'bottom_zone_pct': 33,        # 0-33% = BOTTOM (LONG autorisé)
        'top_zone_pct': 67,           # 67-100% = TOP (SHORT autorisé)
        'vol_regime_trend': 1.5,      # Vol > 1.5 = TREND
        'override_threshold': 0.75,   # Override si wall_strength >= 0.75
    },
    'NQ': {
        'bias_threshold': 0.40,
        'bottom_zone_pct': 32,
        'top_zone_pct': 68,
        'vol_regime_trend': 1.5,
        'override_threshold': 0.65,
    },
}

# ═══════════════════════════════════════════════════════════════════════════════
#              NIVEAUX MENTHORQ
# ═══════════════════════════════════════════════════════════════════════════════

STRONG_LEVELS = ['gex_1', 'gex_2', 'hvl', 'gamma_wall_level', 'vwap']
MEDIUM_LEVELS = ['gex_3', 'gex_4', 'gex_5', 'hvl_0dte', 'gamma_wall_0dte',
                 'call_resistance', 'put_support', 'blind_spot_1', 'blind_spot_2']
WEAK_LEVELS = ['call_resistance_0dte', 'put_support_0dte', 'blind_spot_3',
               'vwap_up1', 'vwap_dn1', 'vwap_up2', 'vwap_dn2']
ALL_LEVELS = STRONG_LEVELS + MEDIUM_LEVELS + WEAK_LEVELS

def get_level_score(level_name: str) -> int:
    if level_name in STRONG_LEVELS:
        return 3
    elif level_name in MEDIUM_LEVELS:
        return 2
    elif level_name in WEAK_LEVELS:
        return 1
    return 0

# ═══════════════════════════════════════════════════════════════════════════════
#                           FONCTIONS UTILITAIRES
# ═══════════════════════════════════════════════════════════════════════════════

def progress_bar(current: int, total: int, prefix: str = "", length: int = 30):
    percent = current / total if total > 0 else 0
    filled = int(length * percent)
    bar = "█" * filled + "░" * (length - filled)
    sys.stdout.write(f"\r{prefix} |{bar}| {percent*100:.0f}%")
    sys.stdout.flush()
    if current >= total:
        print()


def get_month_folder(day: str) -> str:
    return "NOVEMBRE" if day[4:6] == "11" else "DECEMBRE"


def find_data_file(day: str, symbol: str) -> Optional[Path]:
    config = SYMBOLS[symbol]
    month_folder = get_month_folder(day)
    for contract in config["contracts"]:
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


def get_session(hour: int, minute: int) -> Optional[str]:
    time_val = hour * 60 + minute
    for session_name, session in SESSIONS.items():
        s = session['start'][0] * 60 + session['start'][1]
        e = session['end'][0] * 60 + session['end'][1]
        if s <= time_val < e:
            return session_name
    return None

# ═══════════════════════════════════════════════════════════════════════════════
#              🆕 DUAL-MODE DETECTION (réplique du live)
# ═══════════════════════════════════════════════════════════════════════════════

def detect_market_mode(snapshot: Dict, symbol: str) -> Tuple[str, float]:
    """
    Détecte si le marché est en RANGE ou TREND.
    Retourne: (mode, position_in_range_pct)
    """
    cfg = DUAL_MODE_CONFIG[symbol]

    # Volatilité
    vol_regime = snapshot.get('vol_regime', 1.0) or 1.0

    # Bias directionnel (MIA bullish score)
    mia_score = snapshot.get('mia_bullish_score', 0) or 0

    # Détecter mode
    if vol_regime >= cfg['vol_regime_trend'] or abs(mia_score) >= cfg['bias_threshold']:
        mode = "TREND"
    else:
        mode = "RANGE"

    # Calculer position dans le range
    # Utiliser IBH/IBL ou high/low du jour
    ibh = snapshot.get('ibh') or snapshot.get('1d_max') or 0
    ibl = snapshot.get('ibl') or snapshot.get('1d_min') or 0
    mid = snapshot.get('mid', 0)

    if ibh > ibl and mid > 0:
        position_pct = ((mid - ibl) / (ibh - ibl)) * 100
        position_pct = max(0, min(100, position_pct))
    else:
        position_pct = 50  # Par défaut au milieu

    return mode, position_pct


def check_dual_mode_block(snapshot: Dict, symbol: str, direction: str) -> Tuple[bool, str]:
    """
    Vérifie si le DUAL-MODE bloque ce trade.
    Retourne: (blocked, reason)
    """
    mode, position_pct = detect_market_mode(snapshot, symbol)
    cfg = DUAL_MODE_CONFIG[symbol]

    # En mode TREND, pas de blocage
    if mode == "TREND":
        return False, ""

    # En mode RANGE, vérifier les zones
    if direction == "LONG":
        if position_pct > cfg['top_zone_pct']:
            return True, f"RANGE TOP ({position_pct:.0f}%): LONG interdit"
    elif direction == "SHORT":
        if position_pct < cfg['bottom_zone_pct']:
            return True, f"RANGE BOTTOM ({position_pct:.0f}%): SHORT interdit"

    # Zone du milieu - bloqué
    if cfg['bottom_zone_pct'] <= position_pct <= cfg['top_zone_pct']:
        return True, f"RANGE MIDDLE ({position_pct:.0f}%): {direction} interdit"

    return False, ""

# ═══════════════════════════════════════════════════════════════════════════════
#              🆕 OBSTACLE DETECTION (réplique du live)
# ═══════════════════════════════════════════════════════════════════════════════

def check_obstacle_before_tp(snapshot: Dict, symbol: str, direction: str,
                              entry_price: float, tp_ticks: int) -> Tuple[bool, str]:
    """
    Vérifie s'il y a un niveau bloquant entre l'entry et le TP.
    Retourne: (has_obstacle, obstacle_info)
    """
    tick_size = SYMBOLS[symbol]['tick_size']

    if direction == "LONG":
        tp_price = entry_price + tp_ticks * tick_size
        # Chercher obstacle entre entry et TP (au-dessus)
        for level_name in ALL_LEVELS:
            level_price = snapshot.get(level_name)
            if not level_price or level_price <= 0:
                continue

            # Obstacle si le niveau est entre entry et TP
            if entry_price < level_price < tp_price:
                distance_to_obstacle = (level_price - entry_price) / tick_size
                distance_to_tp = tp_ticks

                # Obstacle si plus proche que le TP
                if distance_to_obstacle < distance_to_tp * 0.8:  # Marge de 20%
                    return True, f"{level_name} @ {level_price:.2f} (bloque LONG)"

    elif direction == "SHORT":
        tp_price = entry_price - tp_ticks * tick_size
        # Chercher obstacle entre entry et TP (en-dessous)
        for level_name in ALL_LEVELS:
            level_price = snapshot.get(level_name)
            if not level_price or level_price <= 0:
                continue

            # Obstacle si le niveau est entre entry et TP
            if tp_price < level_price < entry_price:
                distance_to_obstacle = (entry_price - level_price) / tick_size
                distance_to_tp = tp_ticks

                # Obstacle si plus proche que le TP
                if distance_to_obstacle < distance_to_tp * 0.8:
                    return True, f"{level_name} @ {level_price:.2f} (bloque SHORT)"

    return False, ""

# ═══════════════════════════════════════════════════════════════════════════════
#              ANALYSE MENTHORQ (identique à V9)
# ═══════════════════════════════════════════════════════════════════════════════

def analyze_menthorq(snapshot: Dict, symbol: str, zone_ticks: int = 15) -> Dict:
    mid = snapshot.get('mid', 0)
    if mid <= 0:
        return {
            'nearest_level': '', 'nearest_distance': float('inf'),
            'nearest_score': 0, 'confluence_count': 0, 'max_score_in_zone': 0
        }

    tick_size = SYMBOLS[symbol]['tick_size']

    levels_in_zone = []
    nearest_level = ""
    nearest_distance = float('inf')
    nearest_score = 0
    max_score = 0

    for level_name in ALL_LEVELS:
        price = snapshot.get(level_name)
        if not price or price <= 0:
            continue

        distance = abs(mid - price) / tick_size
        score = get_level_score(level_name)

        if distance <= zone_ticks:
            levels_in_zone.append({'name': level_name, 'distance': distance, 'score': score})
            max_score = max(max_score, score)

        if distance < nearest_distance:
            nearest_distance = distance
            nearest_level = level_name
            nearest_score = score

    return {
        'nearest_level': nearest_level,
        'nearest_distance': nearest_distance,
        'nearest_score': nearest_score,
        'confluence_count': len(levels_in_zone),
        'max_score_in_zone': max_score,
        'levels_in_zone': levels_in_zone,
    }

# ═══════════════════════════════════════════════════════════════════════════════
#              GÉNÉRATION DE SIGNAL (V9 + DUAL-MODE + OBSTACLE)
# ═══════════════════════════════════════════════════════════════════════════════

def generate_signal_v91(
    snapshot: Dict,
    symbol: str,
    config: Dict
) -> Tuple[bool, str, float, Dict]:
    """
    Génère un signal avec TOUS les filtres (V9 + DUAL-MODE + OBSTACLE).
    """
    mid = snapshot.get('mid', 0)
    if mid <= 0:
        return False, "", 0, {'reject': 'NO_PRICE'}

    # Analyser MenthorQ
    mq = analyze_menthorq(snapshot, symbol)

    # FILTRE V9 1: MAX_DISTANCE
    if mq['nearest_distance'] > config['max_distance']:
        return False, "", 0, {'reject': 'V9_DISTANCE', 'distance': mq['nearest_distance']}

    # FILTRE V9 2: MIN_CONFLUENCE
    if mq['confluence_count'] < config['min_confluence']:
        return False, "", 0, {'reject': 'V9_CONFLUENCE'}

    # FILTRE V9 3: MIN_LEVEL_SCORE
    if mq['max_score_in_zone'] < config['min_level_score']:
        return False, "", 0, {'reject': 'V9_LEVEL_SCORE'}

    # Calcul confidence (identique à V9)
    menthorq_score = max(0, 1 - mq['nearest_distance'] / 25)
    if mq['nearest_level'] in STRONG_LEVELS:
        menthorq_score = min(1.0, menthorq_score * 1.3)
    layer1 = menthorq_score * 0.50

    delta = snapshot.get('delta', 0) or 0
    cum_delta = snapshot.get('cum_delta_session', 0) or 0
    of_score = min(1.0, (abs(delta) / 400 + abs(cum_delta) / 800) / 2) * 0.5 + 0.3
    layer2 = of_score * 0.30

    mia_score = snapshot.get('mia_bullish_score', 0) or 0
    ctx_score = min(1.0, abs(mia_score) * 2.5)
    layer3 = ctx_score * 0.20

    confidence = layer1 + layer2 + layer3

    # Vérifier seuils V9
    if confidence < config['min_confidence']:
        return False, "", confidence, {'reject': 'V9_CONFIDENCE'}

    # Direction
    mia_threshold = config['mia_threshold']
    if mia_score > mia_threshold:
        direction = "LONG"
    elif mia_score < -mia_threshold:
        direction = "SHORT"
    else:
        return False, "", confidence, {'reject': 'NEUTRAL'}

    # 🆕 FILTRE DUAL-MODE
    dm_blocked, dm_reason = check_dual_mode_block(snapshot, symbol, direction)
    if dm_blocked:
        return False, "", confidence, {'reject': 'DUAL_MODE', 'reason': dm_reason}

    # 🆕 FILTRE OBSTACLE
    has_obstacle, obstacle_info = check_obstacle_before_tp(
        snapshot, symbol, direction, mid, config['tp_ticks']
    )
    if has_obstacle:
        return False, "", confidence, {'reject': 'OBSTACLE', 'reason': obstacle_info}

    return True, direction, confidence, mq

# ═══════════════════════════════════════════════════════════════════════════════
#              SIMULATION TRADE (identique)
# ═══════════════════════════════════════════════════════════════════════════════

def simulate_trade(entry_snap: Dict, direction: str, symbol: str,
                   future_snaps: List[Dict], tp_ticks: int, sl_ticks: int) -> Tuple[float, str]:

    tick_size = SYMBOLS[symbol]['tick_size']
    tick_value = SYMBOLS[symbol]['tick_value']

    entry = entry_snap.get('mid')
    entry_time = entry_snap.get('t_ms', 0)

    if direction == "SHORT":
        sl = entry + sl_ticks * tick_size
        tp = entry - tp_ticks * tick_size
    else:
        sl = entry - sl_ticks * tick_size
        tp = entry + tp_ticks * tick_size

    for snap in future_snaps[:300]:
        t_ms = snap.get('t_ms', 0)
        if t_ms - entry_time > 3600_000:
            return 0, "TIMEOUT"

        high = snap.get('high') or snap.get('mid', entry)
        low = snap.get('low') or snap.get('mid', entry)

        if direction == "SHORT":
            if high >= sl:
                return -sl_ticks * tick_value, "LOSS"
            if low <= tp:
                return tp_ticks * tick_value, "WIN"
        else:
            if low <= sl:
                return -sl_ticks * tick_value, "LOSS"
            if high >= tp:
                return tp_ticks * tick_value, "WIN"

    return 0, "TIMEOUT"

# ═══════════════════════════════════════════════════════════════════════════════
#              BACKTEST PAR SESSION × SYMBOLE
# ═══════════════════════════════════════════════════════════════════════════════

def run_backtest_v91(session_name: str, symbol: str, all_data: Dict,
                     config: Dict, track_rejects: bool = True) -> Dict:
    """Backtest V9.1 avec tous les filtres."""

    trades = []
    rejects = defaultdict(int)
    cooldown_ms = config['cooldown_min'] * 60 * 1000
    tp_ticks = config['tp_ticks']
    sl_ticks = config['sl_ticks']

    for day, day_data in all_data.items():
        snapshots = day_data.get(symbol, [])
        if not snapshots:
            continue

        last_trade_time = 0
        session_trades = 0

        for i, snap in enumerate(snapshots):
            if session_trades >= 10:
                break

            t_ms = snap.get('t_ms', 0)
            hour, minute = get_paris_time(t_ms)

            current_session = get_session(hour, minute)
            if current_session != session_name:
                continue

            if t_ms - last_trade_time < cooldown_ms:
                continue

            valid, direction, confidence, info = generate_signal_v91(snap, symbol, config)

            if not valid:
                if track_rejects and 'reject' in info:
                    rejects[info['reject']] += 1
                continue

            future = snapshots[i+1:i+301]
            if len(future) < 10:
                continue

            pnl, result = simulate_trade(snap, direction, symbol, future, tp_ticks, sl_ticks)

            trades.append({
                'pnl': pnl,
                'result': result,
                'direction': direction,
                'confidence': confidence,
            })

            last_trade_time = t_ms
            session_trades += 1

    # Stats
    if not trades:
        return {
            'trades': 0, 'pnl': 0, 'wr': 0, 'pf': 0,
            'rejects': dict(rejects),
        }

    total_pnl = sum(t['pnl'] for t in trades)
    winners = [t for t in trades if t['pnl'] > 0]
    losers = [t for t in trades if t['pnl'] < 0]

    wr = len(winners) / len(trades) * 100 if trades else 0

    gross_profit = sum(t['pnl'] for t in winners) if winners else 0
    gross_loss = abs(sum(t['pnl'] for t in losers)) if losers else 1
    pf = gross_profit / gross_loss if gross_loss > 0 else 0

    return {
        'trades': len(trades),
        'pnl': total_pnl,
        'wr': wr,
        'pf': pf,
        'wins': len(winners),
        'losses': len(losers),
        'rejects': dict(rejects),
    }

# ═══════════════════════════════════════════════════════════════════════════════
#                           MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 100)
    print("     🎯 BACKTEST V9.1 - AVEC DUAL-MODE ET OBSTACLE (FILTRES LIVE)")
    print("=" * 100)
    print("""
┌─────────────────────────────────────────────────────────────────────────────────┐
│  OBJECTIF: Mesurer le P&L RÉALISTE avec tous les filtres du LIVE               │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  V9 (backtest original):  ML + MenthorQ seuls                                   │
│  V9.1 (ce backtest):      ML + MenthorQ + DUAL-MODE + OBSTACLE                  │
│                                                                                 │
│  FILTRES AJOUTÉS:                                                               │
│    • DUAL-MODE: Bloque LONG si prix > 67% du range (RANGE TOP)                  │
│    • DUAL-MODE: Bloque SHORT si prix < 33% du range (RANGE BOTTOM)              │
│    • OBSTACLE: Bloque si niveau MenthorQ entre entry et TP                      │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
""")

    # Charger données
    print("📂 Chargement des données...")
    all_data = {}
    days_loaded = 0

    for i, day in enumerate(DAYS_TO_TEST):
        progress_bar(i + 1, len(DAYS_TO_TEST), "Chargement")
        all_data[day] = {}
        has_data = False

        for symbol in ["ES", "NQ"]:
            file_path = find_data_file(day, symbol)
            if file_path:
                snapshots = load_snapshots(file_path)
                all_data[day][symbol] = snapshots
                if snapshots:
                    has_data = True

        if has_data:
            days_loaded += 1

    print(f"\n   📊 {days_loaded} jours chargés")

    if days_loaded == 0:
        print("❌ Aucune donnée!")
        return

    # Résultats
    results_v91 = {}
    all_rejects = defaultdict(int)

    # ═══════════════════════════════════════════════════════════════
    #                    BOUCLE PAR SESSION × SYMBOLE
    # ═══════════════════════════════════════════════════════════════

    print("\n" + "=" * 100)
    print("                    🔬 EXÉCUTION BACKTEST V9.1")
    print("=" * 100)

    for session_name in SESSIONS.keys():
        for symbol in ["ES", "NQ"]:
            combo_key = f"{session_name}_{symbol}"
            config = V9_CONFIGS.get(combo_key)

            if not config or not config.get('enabled', True):
                print(f"\n⏭️  {combo_key}: DÉSACTIVÉ")
                continue

            print(f"\n🔍 {combo_key}...")

            result = run_backtest_v91(session_name, symbol, all_data, config)
            results_v91[combo_key] = result

            # Accumuler rejets
            for reject_type, count in result.get('rejects', {}).items():
                all_rejects[reject_type] += count

            if result['trades'] > 0:
                print(f"   → {result['trades']} trades | WR: {result['wr']:.1f}% | PnL: ${result['pnl']:+,.0f}")
            else:
                print(f"   → 0 trades (rejets: {dict(result.get('rejects', {}))})")

    # ═══════════════════════════════════════════════════════════════
    #                    RÉSUMÉ FINAL
    # ═══════════════════════════════════════════════════════════════

    print("\n" + "=" * 100)
    print("                    📊 RÉSUMÉ V9.1 - AVEC TOUS LES FILTRES LIVE")
    print("=" * 100)

    # Tableau des résultats
    print(f"\n{'Session':<15} {'Sym':<4} {'Trades':<8} {'Wins':<6} {'Losses':<7} {'WR%':<7} {'PnL':<12}")
    print("-" * 70)

    total_trades = 0
    total_pnl = 0
    total_wins = 0
    total_losses = 0

    for combo_key, result in results_v91.items():
        session = combo_key.rsplit('_', 1)[0]
        symbol = combo_key.rsplit('_', 1)[1]

        trades = result.get('trades', 0)
        wins = result.get('wins', 0)
        losses = result.get('losses', 0)
        wr = result.get('wr', 0)
        pnl = result.get('pnl', 0)

        print(f"{session:<15} {symbol:<4} {trades:<8} {wins:<6} {losses:<7} {wr:<6.1f}% ${pnl:>+10,.0f}")

        total_trades += trades
        total_pnl += pnl
        total_wins += wins
        total_losses += losses

    total_wr = (total_wins / total_trades * 100) if total_trades > 0 else 0

    print("-" * 70)
    print(f"{'TOTAL':<15} {'':<4} {total_trades:<8} {total_wins:<6} {total_losses:<7} {total_wr:<6.1f}% ${total_pnl:>+10,.0f}")

    # ═══════════════════════════════════════════════════════════════
    #                    ANALYSE DES REJETS
    # ═══════════════════════════════════════════════════════════════

    print("\n" + "=" * 100)
    print("                    🚫 ANALYSE DES REJETS")
    print("=" * 100)

    print(f"\n{'Type de rejet':<25} {'Nombre':<10} {'%':<8}")
    print("-" * 50)

    total_rejects = sum(all_rejects.values())
    for reject_type, count in sorted(all_rejects.items(), key=lambda x: -x[1]):
        pct = count / total_rejects * 100 if total_rejects > 0 else 0
        bar = "█" * int(pct / 5)
        print(f"{reject_type:<25} {count:<10} {pct:>5.1f}% {bar}")

    print("-" * 50)
    print(f"{'TOTAL':<25} {total_rejects:<10}")

    # ═══════════════════════════════════════════════════════════════
    #                    COMPARAISON V9 vs V9.1
    # ═══════════════════════════════════════════════════════════════

    print("\n" + "=" * 100)
    print("                    📈 COMPARAISON V9 vs V9.1")
    print("=" * 100)

    # Résultats V9 originaux (approximatifs depuis le backtest)
    v9_results = {
        'trades': 467,
        'pnl': 11350,
    }

    print(f"""
┌────────────────────────────────────────────────────────────────────────────┐
│                                                                            │
│   BACKTEST V9 (sans DUAL-MODE, sans OBSTACLE):                             │
│      Trades: {v9_results['trades']}                                                          │
│      P&L:    ${v9_results['pnl']:+,}                                                     │
│                                                                            │
│   BACKTEST V9.1 (AVEC DUAL-MODE et OBSTACLE):                              │
│      Trades: {total_trades}                                                             │
│      P&L:    ${total_pnl:+,.0f}                                                      │
│                                                                            │
│   DIFFÉRENCE:                                                              │
│      Trades: {total_trades - v9_results['trades']:+} ({(total_trades/v9_results['trades']*100):.0f}% du V9)                                        │
│      P&L:    ${total_pnl - v9_results['pnl']:+,.0f}                                                    │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
""")

    # Verdict
    print("\n" + "=" * 100)
    print("                    🎯 VERDICT")
    print("=" * 100)

    if total_pnl > 7000:
        verdict = "A"
        action = "✅ GARDER les filtres - Résultat excellent!"
    elif total_pnl > 2000:
        verdict = "B"
        action = "✅ GARDER les filtres - Résultat réaliste et positif"
    elif total_pnl > -1000:
        verdict = "C"
        action = "⚠️ ASSOUPLIR les filtres - Trop restrictifs"
    else:
        verdict = "D"
        action = "❌ DÉSACTIVER les filtres - Contreproductifs"

    print(f"""
    SCÉNARIO {verdict}: P&L = ${total_pnl:+,.0f}

    ACTION RECOMMANDÉE: {action}
""")


if __name__ == "__main__":
    main()
