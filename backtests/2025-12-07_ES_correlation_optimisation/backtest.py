"""
🔬 AUDIT OPTIMISATION ES AVEC CORRÉLATION NQ
=============================================

Teste plusieurs configurations pour améliorer ES :
1. Sans filtre corrélation (baseline)
2. Avec confirmation NQ obligatoire
3. Avec divergence = skip trade
4. Avec divergence = réduire taille
5. Avec score corrélation minimum

Date: 07/12/2025
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Optional
from dataclasses import dataclass

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

try:
    from tqdm import tqdm
except ImportError:
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "tqdm", "-q"])
    from tqdm import tqdm

import logging
logging.disable(logging.INFO)

# ============================================================================
# CONFIGURATION
# ============================================================================

DATE_RANGE = ["20251202", "20251203", "20251204", "20251205"]
BASE_PATH = Path(r"D:\MIA_IA_system\DATA_SIERRA_CHART\DATA_2025\DECEMBRE")
CHART_ES = 3
CHART_NQ = 9

# Paramètres de trading ES (actuels)
ES_CONFIG = {
    'tick_size': 0.25,
    'tick_value': 12.50,
    'tp_ticks': 20,
    'sl_ticks': 20,
    'min_delta': 100,
    'min_pressure': 0.20,
    'min_layer1': 0.40,
    'max_distance': 15,
}

# Paramètres de corrélation à tester
CORRELATION_CONFIGS = {
    'baseline': {
        'name': 'Sans corrélation (actuel)',
        'require_confirmation': False,
        'skip_divergence': False,
        'reduce_size_divergence': False,
        'min_score': 0,
    },
    'confirm_only': {
        'name': 'Confirmation NQ obligatoire',
        'require_confirmation': True,
        'skip_divergence': True,
        'reduce_size_divergence': False,
        'min_score': 70,
    },
    'skip_divergence': {
        'name': 'Skip si divergence',
        'require_confirmation': False,
        'skip_divergence': True,
        'reduce_size_divergence': False,
        'min_score': 0,
    },
    'reduce_divergence': {
        'name': 'Réduire taille si divergence',
        'require_confirmation': False,
        'skip_divergence': False,
        'reduce_size_divergence': True,
        'min_score': 0,
    },
    'score_50': {
        'name': 'Score corrélation >= 50',
        'require_confirmation': False,
        'skip_divergence': False,
        'reduce_size_divergence': False,
        'min_score': 50,
    },
    'score_60': {
        'name': 'Score corrélation >= 60',
        'require_confirmation': False,
        'skip_divergence': False,
        'reduce_size_divergence': False,
        'min_score': 60,
    },
    'hybrid': {
        'name': 'Hybride (skip divergence + score>=50)',
        'require_confirmation': False,
        'skip_divergence': True,
        'reduce_size_divergence': False,
        'min_score': 50,
    },
}

# Sessions de trading
SESSIONS = {
    'London': {'start': 8, 'end': 11},
    'US_Morning': {'start': 15, 'end': 17},
    'Power_Hour': {'start': 20, 'end': 22},
}

SYNC_TOLERANCE_MS = 5000
COOLDOWN_MS = 300000

# ============================================================================
# CLASSES
# ============================================================================

@dataclass
class Trade:
    timestamp: int
    direction: str
    entry_price: float
    es_delta: float
    nq_delta: float
    correlation_score: float
    nq_direction: str
    is_divergence: bool
    is_confirmed: bool
    size: float  # 1.0 = normal, 0.5 = réduit

    # Résultat simulé
    exit_price: float = 0
    pnl: float = 0
    result: str = ""  # WIN, LOSS


@dataclass
class ConfigResult:
    name: str
    trades: int
    wins: int
    losses: int
    win_rate: float
    total_pnl: float
    avg_pnl: float
    profit_factor: float
    skipped_divergence: int
    skipped_score: int
    reduced_size: int


# ============================================================================
# FONCTIONS
# ============================================================================

def load_snapshots(date_str: str, symbol: str) -> List[Dict]:
    """Charge les snapshots pour une date et symbole"""
    chart_id = CHART_ES if symbol == "ES" else CHART_NQ
    path = BASE_PATH / date_str / f"CHART_{chart_id}" / "ML_READY"

    if not path.exists():
        return []

    files = list(path.glob(f"ml_*{symbol}*.jsonl"))
    if not files:
        return []

    snaps = []
    with open(files[0], 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    snaps.append(json.loads(line))
                except:
                    pass
    return snaps


def get_session(hour: int) -> Optional[str]:
    """Retourne la session pour une heure donnée"""
    for name, times in SESSIONS.items():
        if times['start'] <= hour < times['end']:
            return name
    return None


def get_direction(delta: float, threshold: float = 100) -> str:
    """Retourne la direction basée sur le delta"""
    if delta > threshold:
        return "LONG"
    elif delta < -threshold:
        return "SHORT"
    return "NEUTRAL"


def calculate_correlation_score(es_delta: float, nq_delta: float,
                                 es_pressure: float, nq_pressure: float) -> float:
    """Calcule un score de corrélation simplifié"""
    score = 0

    # Delta dans la même direction (0-40 points)
    if (es_delta > 0 and nq_delta > 0) or (es_delta < 0 and nq_delta < 0):
        # Même signe
        ratio = min(abs(es_delta), abs(nq_delta)) / max(abs(es_delta), abs(nq_delta), 1)
        score += 40 * ratio

    # Force du delta NQ (0-30 points)
    nq_strength = min(abs(nq_delta) / 200, 1)
    score += 30 * nq_strength

    # Pressure strength (0-30 points)
    avg_pressure = (es_pressure + nq_pressure) / 2
    score += 30 * min(avg_pressure * 2, 1)

    return min(100, score)


def simulate_trade_result(trade: Trade, snapshots: List[Dict],
                           tp_ticks: int, sl_ticks: int, tick_size: float) -> Trade:
    """Simule le résultat d'un trade basé sur les prix futurs"""
    entry = trade.entry_price

    if trade.direction == "LONG":
        tp_price = entry + tp_ticks * tick_size
        sl_price = entry - sl_ticks * tick_size
    else:
        tp_price = entry - tp_ticks * tick_size
        sl_price = entry + sl_ticks * tick_size

    # Chercher les prix futurs
    future_snaps = [s for s in snapshots if s.get('t_ms', 0) > trade.timestamp]

    for snap in future_snaps[:500]:  # Max 500 snaps (~8 min)
        price = snap.get('mid', 0)

        if trade.direction == "LONG":
            if price >= tp_price:
                trade.exit_price = tp_price
                trade.pnl = tp_ticks * ES_CONFIG['tick_value'] * trade.size
                trade.result = "WIN"
                return trade
            elif price <= sl_price:
                trade.exit_price = sl_price
                trade.pnl = -sl_ticks * ES_CONFIG['tick_value'] * trade.size
                trade.result = "LOSS"
                return trade
        else:  # SHORT
            if price <= tp_price:
                trade.exit_price = tp_price
                trade.pnl = tp_ticks * ES_CONFIG['tick_value'] * trade.size
                trade.result = "WIN"
                return trade
            elif price >= sl_price:
                trade.exit_price = sl_price
                trade.pnl = -sl_ticks * ES_CONFIG['tick_value'] * trade.size
                trade.result = "LOSS"
                return trade

    # Timeout - considérer comme scratch (0 P&L)
    trade.exit_price = entry
    trade.pnl = 0
    trade.result = "SCRATCH"
    return trade


def run_backtest(config_name: str, config: Dict, all_trades: List[Trade]) -> ConfigResult:
    """Exécute le backtest pour une configuration"""
    trades = 0
    wins = 0
    losses = 0
    total_pnl = 0
    skipped_divergence = 0
    skipped_score = 0
    reduced_size = 0
    gross_profit = 0
    gross_loss = 0

    for trade in all_trades:
        # Appliquer les filtres de la configuration

        # Filtre: Confirmation obligatoire
        if config['require_confirmation'] and not trade.is_confirmed:
            continue

        # Filtre: Skip divergence
        if config['skip_divergence'] and trade.is_divergence:
            skipped_divergence += 1
            continue

        # Filtre: Score minimum
        if config['min_score'] > 0 and trade.correlation_score < config['min_score']:
            skipped_score += 1
            continue

        # Appliquer réduction de taille si divergence
        size = trade.size
        if config['reduce_size_divergence'] and trade.is_divergence:
            size = 0.5
            reduced_size += 1

        # Simuler le trade avec la taille ajustée
        pnl = trade.pnl * (size / trade.size) if trade.size > 0 else trade.pnl

        trades += 1
        total_pnl += pnl

        if trade.result == "WIN":
            wins += 1
            gross_profit += abs(pnl)
        elif trade.result == "LOSS":
            losses += 1
            gross_loss += abs(pnl)

    win_rate = (wins / trades * 100) if trades > 0 else 0
    avg_pnl = total_pnl / trades if trades > 0 else 0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

    return ConfigResult(
        name=config['name'],
        trades=trades,
        wins=wins,
        losses=losses,
        win_rate=win_rate,
        total_pnl=total_pnl,
        avg_pnl=avg_pnl,
        profit_factor=profit_factor,
        skipped_divergence=skipped_divergence,
        skipped_score=skipped_score,
        reduced_size=reduced_size
    )


def main():
    print("="*100)
    print("[AUDIT] OPTIMISATION ES AVEC CORRELATION NQ")
    print("="*100)
    print(f"\nPeriode: {DATE_RANGE[0]} -> {DATE_RANGE[-1]} (4 jours)")
    print(f"Config ES: TP={ES_CONFIG['tp_ticks']}t, SL={ES_CONFIG['sl_ticks']}t, "
          f"Delta>={ES_CONFIG['min_delta']}, Pressure>={ES_CONFIG['min_pressure']}")

    # Charger les données
    print("\n[LOAD] Chargement des donnees...")
    all_es = []
    all_nq = []

    for date in tqdm(DATE_RANGE, desc="[LOAD] Jours"):
        es_snaps = load_snapshots(date, "ES")
        nq_snaps = load_snapshots(date, "NQ")

        for s in es_snaps:
            s['date'] = date
        for s in nq_snaps:
            s['date'] = date

        all_es.extend(es_snaps)
        all_nq.extend(nq_snaps)

    print(f"   TOTAL: ES={len(all_es):,} | NQ={len(all_nq):,}")

    # Indexer NQ
    print("\n[INDEX] Indexation NQ...")
    nq_by_time = {}
    for snap in all_nq:
        t = snap.get('t_ms', 0)
        if t > 0:
            nq_by_time[t] = snap

    # Générer tous les trades potentiels
    print("\n[GENERATE] Generation des trades ES...")
    all_trades = []
    last_trade_time = 0

    for es_snap in tqdm(all_es, desc="[SCAN] Signaux ES"):
        es_time = es_snap.get('t_ms', 0)
        es_delta = es_snap.get('delta', 0)
        es_mid = es_snap.get('mid', 0)
        es_pressure = es_snap.get('pressure_strength', 0)

        # Vérifier session
        dt = datetime.fromtimestamp(es_time / 1000)
        hour = dt.hour
        if get_session(hour) is None:
            continue

        # Vérifier delta minimum
        direction = get_direction(es_delta, ES_CONFIG['min_delta'])
        if direction == "NEUTRAL":
            continue

        # Vérifier pressure minimum
        if es_pressure < ES_CONFIG['min_pressure']:
            continue

        # Cooldown
        if es_time - last_trade_time < COOLDOWN_MS:
            continue

        last_trade_time = es_time

        # Trouver NQ correspondant
        nq_snap = None
        for nq_time in range(es_time - SYNC_TOLERANCE_MS, es_time + SYNC_TOLERANCE_MS, 100):
            if nq_time in nq_by_time:
                nq_snap = nq_by_time[nq_time]
                break

        if not nq_snap:
            # Chercher le plus proche
            closest = None
            min_diff = float('inf')
            for nq_time, snap in nq_by_time.items():
                diff = abs(es_time - nq_time)
                if diff < min_diff and diff <= SYNC_TOLERANCE_MS:
                    min_diff = diff
                    closest = snap
            nq_snap = closest

        nq_delta = nq_snap.get('delta', 0) if nq_snap else 0
        nq_pressure = nq_snap.get('pressure_strength', 0) if nq_snap else 0
        nq_direction = get_direction(nq_delta, 100)

        # Calculer corrélation
        corr_score = calculate_correlation_score(es_delta, nq_delta, es_pressure, nq_pressure)

        # Déterminer si divergence ou confirmation
        is_divergence = (direction == "LONG" and nq_direction == "SHORT") or \
                        (direction == "SHORT" and nq_direction == "LONG")
        is_confirmed = direction == nq_direction and nq_direction != "NEUTRAL"

        # Créer le trade
        trade = Trade(
            timestamp=es_time,
            direction=direction,
            entry_price=es_mid,
            es_delta=es_delta,
            nq_delta=nq_delta,
            correlation_score=corr_score,
            nq_direction=nq_direction,
            is_divergence=is_divergence,
            is_confirmed=is_confirmed,
            size=1.0
        )

        all_trades.append(trade)

    print(f"   Trades potentiels: {len(all_trades)}")

    # Simuler les résultats
    print("\n[SIMULATE] Simulation des resultats...")
    for trade in tqdm(all_trades, desc="[SIM] Trades"):
        # Trouver les snapshots futurs pour ce trade
        future_snaps = [s for s in all_es if s.get('t_ms', 0) > trade.timestamp
                        and s.get('t_ms', 0) < trade.timestamp + 600000]  # 10 min max

        simulate_trade_result(trade, future_snaps,
                             ES_CONFIG['tp_ticks'], ES_CONFIG['sl_ticks'],
                             ES_CONFIG['tick_size'])

    # Stats des trades générés
    wins_total = sum(1 for t in all_trades if t.result == "WIN")
    losses_total = sum(1 for t in all_trades if t.result == "LOSS")
    scratches = sum(1 for t in all_trades if t.result == "SCRATCH")
    pnl_total = sum(t.pnl for t in all_trades)

    print(f"\n   Resultats bruts (avant filtres):")
    print(f"   Wins: {wins_total} | Losses: {losses_total} | Scratch: {scratches}")
    print(f"   P&L total: ${pnl_total:,.2f}")
    print(f"   Win Rate: {wins_total/(wins_total+losses_total)*100:.1f}%" if (wins_total+losses_total) > 0 else "   Win Rate: N/A")

    # Analyser les divergences
    divergences = [t for t in all_trades if t.is_divergence]
    div_wins = sum(1 for t in divergences if t.result == "WIN")
    div_losses = sum(1 for t in divergences if t.result == "LOSS")
    div_pnl = sum(t.pnl for t in divergences)

    print(f"\n   [DIVERGENCES] {len(divergences)} trades:")
    print(f"   Wins: {div_wins} | Losses: {div_losses}")
    print(f"   P&L: ${div_pnl:,.2f}")
    print(f"   Win Rate: {div_wins/(div_wins+div_losses)*100:.1f}%" if (div_wins+div_losses) > 0 else "   Win Rate: N/A")

    # Analyser les confirmations
    confirmed = [t for t in all_trades if t.is_confirmed]
    conf_wins = sum(1 for t in confirmed if t.result == "WIN")
    conf_losses = sum(1 for t in confirmed if t.result == "LOSS")
    conf_pnl = sum(t.pnl for t in confirmed)

    print(f"\n   [CONFIRMES] {len(confirmed)} trades:")
    print(f"   Wins: {conf_wins} | Losses: {conf_losses}")
    print(f"   P&L: ${conf_pnl:,.2f}")
    print(f"   Win Rate: {conf_wins/(conf_wins+conf_losses)*100:.1f}%" if (conf_wins+conf_losses) > 0 else "   Win Rate: N/A")

    # Tester chaque configuration
    print("\n" + "="*100)
    print("[TEST] TEST DES CONFIGURATIONS")
    print("="*100)

    results = []
    for config_name, config in CORRELATION_CONFIGS.items():
        result = run_backtest(config_name, config, all_trades)
        results.append(result)

    # Afficher les résultats
    print("\n" + "-"*100)
    print(f"{'Configuration':<35} {'Trades':>8} {'Wins':>6} {'Loss':>6} {'WR%':>7} {'P&L':>12} {'PF':>6}")
    print("-"*100)

    for r in results:
        print(f"{r.name:<35} {r.trades:>8} {r.wins:>6} {r.losses:>6} "
              f"{r.win_rate:>6.1f}% ${r.total_pnl:>10,.2f} {r.profit_factor:>5.2f}")

    print("-"*100)

    # Trouver le meilleur
    best = max(results, key=lambda x: x.total_pnl)
    baseline = results[0]

    print(f"\n[BEST] Meilleure configuration: {best.name}")
    print(f"   P&L: ${best.total_pnl:,.2f} (vs baseline ${baseline.total_pnl:,.2f})")
    print(f"   Gain: ${best.total_pnl - baseline.total_pnl:,.2f}")
    print(f"   Win Rate: {best.win_rate:.1f}% (vs {baseline.win_rate:.1f}%)")

    # Recommandations
    print("\n" + "="*100)
    print("[RECOMMEND] RECOMMANDATIONS")
    print("="*100)

    # Analyser l'impact de chaque filtre
    print("\n1. IMPACT DE CHAQUE FILTRE:")

    div_impact = baseline.total_pnl - [r for r in results if 'divergence' in r.name.lower() and 'skip' in r.name.lower()][0].total_pnl if len([r for r in results if 'divergence' in r.name.lower() and 'skip' in r.name.lower()]) > 0 else 0

    for r in results[1:]:
        delta_pnl = r.total_pnl - baseline.total_pnl
        delta_wr = r.win_rate - baseline.win_rate
        delta_trades = r.trades - baseline.trades

        status = "[OK]" if delta_pnl > 0 else "[X]"
        print(f"   {status} {r.name}:")
        print(f"       P&L: {'+' if delta_pnl >= 0 else ''}{delta_pnl:,.2f}$ | "
              f"WR: {'+' if delta_wr >= 0 else ''}{delta_wr:.1f}% | "
              f"Trades: {delta_trades:+d}")

    # Solution recommandée
    print("\n2. SOLUTION RECOMMANDEE:")
    if best.total_pnl > baseline.total_pnl:
        print(f"   Implementer: {best.name}")
        print(f"   Gain attendu: +${best.total_pnl - baseline.total_pnl:,.2f}/semaine")
    else:
        print("   Garder la configuration actuelle (baseline)")

    # Sauvegarder
    output = {
        'date': datetime.now().isoformat(),
        'period': DATE_RANGE,
        'es_config': ES_CONFIG,
        'total_trades': len(all_trades),
        'divergences': {
            'count': len(divergences),
            'wins': div_wins,
            'losses': div_losses,
            'pnl': div_pnl
        },
        'confirmed': {
            'count': len(confirmed),
            'wins': conf_wins,
            'losses': conf_losses,
            'pnl': conf_pnl
        },
        'results': [
            {
                'name': r.name,
                'trades': r.trades,
                'wins': r.wins,
                'losses': r.losses,
                'win_rate': r.win_rate,
                'total_pnl': r.total_pnl,
                'profit_factor': r.profit_factor
            }
            for r in results
        ],
        'best_config': best.name,
        'recommendation': f"Gain attendu: +${best.total_pnl - baseline.total_pnl:,.2f}"
    }

    output_path = Path(__file__).parent / "results.json"
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\n[SAVE] Resultats: {output_path}")


if __name__ == "__main__":
    main()
