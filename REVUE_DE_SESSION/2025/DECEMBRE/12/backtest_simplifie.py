#!/usr/bin/env python3
"""
BACKTEST SIMPLIFIÉ - Version réaliste MIA IA SYSTEM
====================================================

Ce backtest compare 3 configurations:
1. CURRENT: Configuration actuelle (trop stricte)
2. SIMPLIFIED: Configuration simplifiée proposée
3. MINIMAL: Configuration minimale (référence)

Objectif: Prouver que la simplification améliore les performances.

Auteur: MIA IA System
Date: 13 Décembre 2025
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import pytz

# Setup path
project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATIONS À COMPARER
# ═══════════════════════════════════════════════════════════════════════════════

CONFIGS = {
    # Configuration ACTUELLE (trop stricte - le problème!)
    'CURRENT': {
        'name': 'Configuration Actuelle (Trop Stricte)',
        'min_confidence': {'ES': 1.00, 'NQ': 1.00},        # 🔴 100% requis!
        'max_distance_ticks': {'ES': 8, 'NQ': 10},          # 🔴 Très serré
        'min_pressure_strength': {'ES': 0.20, 'NQ': 0.03},  # 🔴 ES strict
        'tp_ticks': {'ES': 15, 'NQ': 31},
        'sl_ticks': {'ES': 15, 'NQ': 25},
        'enable_trend_filter': True,                         # 🔴 Actif
        'enable_pressure_filter': True,                      # 🔴 Actif
        'sessions_enabled': ['London', 'US Morning', 'Power Hour'],
    },

    # Configuration SIMPLIFIÉE (proposée)
    'SIMPLIFIED': {
        'name': 'Configuration Simplifiée (Proposée)',
        'min_confidence': {'ES': 0.50, 'NQ': 0.50},          # ✅ 50% suffit
        'max_distance_ticks': {'ES': 15, 'NQ': 20},           # ✅ Plus large
        'min_pressure_strength': {'ES': 0.0, 'NQ': 0.0},      # ✅ Désactivé
        'tp_ticks': {'ES': 15, 'NQ': 31},
        'sl_ticks': {'ES': 15, 'NQ': 25},
        'enable_trend_filter': False,                         # ✅ Désactivé
        'enable_pressure_filter': False,                      # ✅ Désactivé
        'sessions_enabled': ['London', 'US Morning', 'Power Hour'],
    },

    # Configuration MINIMALE (référence - tout passe)
    'MINIMAL': {
        'name': 'Configuration Minimale (Référence)',
        'min_confidence': {'ES': 0.30, 'NQ': 0.30},          # Très permissif
        'max_distance_ticks': {'ES': 50, 'NQ': 60},           # Large
        'min_pressure_strength': {'ES': 0.0, 'NQ': 0.0},
        'tp_ticks': {'ES': 15, 'NQ': 31},
        'sl_ticks': {'ES': 15, 'NQ': 25},
        'enable_trend_filter': False,
        'enable_pressure_filter': False,
        'sessions_enabled': ['London', 'US Morning', 'Power Hour'],
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# STRUCTURES DE DONNÉES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class TradeResult:
    """Résultat d'un trade simulé"""
    symbol: str
    direction: str  # LONG ou SHORT
    entry_price: float
    entry_time: datetime
    exit_price: float
    exit_time: datetime
    pnl_ticks: float
    pnl_usd: float
    exit_reason: str  # TP, SL, TIMEOUT
    confidence: float
    distance_to_level: float


@dataclass
class BacktestResult:
    """Résultats complets d'un backtest"""
    config_name: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    avg_pnl_per_trade: float
    profit_factor: float
    max_drawdown: float
    trades_per_day: float
    signals_generated: int
    signals_rejected: int
    rejection_rate: float
    rejection_reasons: Dict[str, int]
    trades: List[TradeResult] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════════
# CHARGEMENT DES DONNÉES
# ═══════════════════════════════════════════════════════════════════════════════

def load_snapshots(data_path: Path, date_str: str, symbol: str) -> List[Dict]:
    """Charge les snapshots ML_READY pour une date et un symbole."""

    snapshots = []

    # Chercher dans DATA_SIERRA_CHART/DATA_2025/
    sierra_path = project_root / "DATA_SIERRA_CHART" / "DATA_2025"

    # Chercher le fichier du jour
    pattern = f"*{date_str}*.jsonl"
    files = list(sierra_path.glob(pattern))

    if not files:
        # Essayer format alternatif
        pattern2 = f"*{symbol}*{date_str}*.jsonl"
        files = list(sierra_path.glob(pattern2))

    if not files:
        return snapshots

    for file_path in files:
        try:
            with open(file_path, 'r') as f:
                for line in f:
                    if line.strip():
                        snap = json.loads(line)
                        # Filtrer par symbole
                        snap_symbol = snap.get('sym', snap.get('symbol', ''))
                        if symbol in snap_symbol:
                            snapshots.append(snap)
        except Exception as e:
            print(f"Erreur lecture {file_path}: {e}")

    return snapshots


def load_snapshots_from_calibrage(symbol: str, max_files: int = 1000) -> List[Dict]:
    """Charge les snapshots depuis le dossier CALIBRAGE_PHASE (données récentes)."""

    snapshots = []
    calibrage_path = project_root / "CALIBRAGE_PHASE" / "SNAPSHOTS"

    if not calibrage_path.exists():
        print(f"⚠️ Dossier CALIBRAGE_PHASE/SNAPSHOTS non trouvé")
        return snapshots

    # Charger les fichiers JSON
    files = list(calibrage_path.glob(f"{symbol}*.json"))[:max_files]

    for file_path in files:
        try:
            with open(file_path, 'r') as f:
                snap = json.load(f)
                snapshots.append(snap)
        except:
            pass

    print(f"📊 {len(snapshots)} snapshots chargés pour {symbol}")
    return snapshots


# ═══════════════════════════════════════════════════════════════════════════════
# SIMULATION
# ═══════════════════════════════════════════════════════════════════════════════

def get_closest_menthorq_level(snapshot: Dict, symbol: str) -> float:
    """Calcule la distance au niveau MenthorQ le plus proche en ticks."""

    mid = snapshot.get('mid', snapshot.get('price', 0))
    if mid <= 0:
        return 999

    tick_size = 0.25 if symbol in ['ES', 'NQ'] else 0.10
    closest_distance = 999

    # Vérifier les niveaux GEX
    for i in range(1, 11):
        gex = snapshot.get(f'gex_{i}')
        if gex and gex > 0:
            dist = abs(gex - mid) / tick_size
            if dist < closest_distance:
                closest_distance = dist

    # Vérifier HVL
    hvl = snapshot.get('hvl')
    if hvl and hvl > 0:
        dist = abs(hvl - mid) / tick_size
        if dist < closest_distance:
            closest_distance = dist

    # Vérifier Blind Spots
    for i in range(9):
        blind = snapshot.get(f'blind_spot_{i}')
        if blind and blind > 0:
            dist = abs(blind - mid) / tick_size
            if dist < closest_distance:
                closest_distance = dist

    # Vérifier menthor_distances
    menthor_distances = snapshot.get('menthor_distances', {})
    for key in ['near_gex_up', 'near_gex_dn', 'hvl0', 'near_blind']:
        dist = menthor_distances.get(key)
        if dist is not None:
            if abs(dist) < closest_distance:
                closest_distance = abs(dist)

    return closest_distance


def get_session_name(hour: int, minute: int) -> Optional[str]:
    """Retourne le nom de la session basé sur l'heure Paris."""

    # London: 08:00-11:00
    if 8 <= hour < 11:
        return 'London'

    # US Morning: 15:50-17:00
    if (hour == 15 and minute >= 50) or hour == 16:
        return 'US Morning'

    # Power Hour: 20:00-21:25
    if hour == 20 or (hour == 21 and minute < 25):
        return 'Power Hour'

    return None


def simulate_signal_generation(snapshot: Dict, symbol: str, config: Dict) -> Tuple[bool, str, float, str]:
    """
    Simule la génération d'un signal avec la config donnée.

    Returns:
        (signal_valid, direction, confidence, rejection_reason)
    """

    # 1. Vérifier session
    try:
        ts = snapshot.get('timestamp', snapshot.get('ts', ''))
        if isinstance(ts, str) and ts:
            dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
            paris = pytz.timezone('Europe/Paris')
            dt_paris = dt.astimezone(paris)
            session = get_session_name(dt_paris.hour, dt_paris.minute)

            if session not in config['sessions_enabled']:
                return False, None, 0, f"Hors session ({session})"
        else:
            # Pas de timestamp, on accepte
            pass
    except:
        pass

    # 2. Vérifier distance au niveau
    distance = get_closest_menthorq_level(snapshot, symbol)
    max_dist = config['max_distance_ticks'].get(symbol, 15)

    if distance > max_dist:
        return False, None, 0, f"Distance trop grande ({distance:.0f}t > {max_dist}t)"

    # 3. Calculer confidence (simulée depuis les données disponibles)
    # Utiliser les scores ML si disponibles, sinon estimer
    l1 = snapshot.get('layer1_confidence', snapshot.get('menthorq_score', 0.5))
    l2 = snapshot.get('layer2_confidence', snapshot.get('orderflow_score', 0.3))
    l3 = snapshot.get('layer3_confidence', snapshot.get('context_score', 0.2))

    # Pondération 50% / 30% / 20%
    confidence = l1 * 0.50 + l2 * 0.30 + l3 * 0.20

    # Si pas de scores, utiliser le bullish_score
    if confidence == 0:
        bullish = snapshot.get('mia_bullish_score', snapshot.get('bullish_score', 0))
        confidence = 0.5 + abs(bullish) * 0.5  # Convertir en 0-1

    min_conf = config['min_confidence'].get(symbol, 0.50)
    if confidence < min_conf:
        return False, None, confidence, f"Confidence insuffisante ({confidence:.2f} < {min_conf})"

    # 4. Vérifier pressure strength (si activé)
    if config.get('enable_pressure_filter', False):
        pressure = snapshot.get('pressure_strength', 0.5)
        min_pressure = config['min_pressure_strength'].get(symbol, 0.0)

        if pressure < min_pressure:
            return False, None, confidence, f"Pressure trop faible ({pressure:.3f} < {min_pressure})"

    # 5. Déterminer direction
    bullish = snapshot.get('mia_bullish_score', 0)
    delta = snapshot.get('delta', 0)

    if bullish > 0.1 or delta > 0:
        direction = 'LONG'
    elif bullish < -0.1 or delta < 0:
        direction = 'SHORT'
    else:
        # Neutre - pas de signal
        return False, None, confidence, "Direction neutre"

    # 6. Vérifier trend filter (si activé)
    if config.get('enable_trend_filter', False):
        hvl = snapshot.get('hvl', 0)
        mid = snapshot.get('mid', 0)
        vwap = snapshot.get('vwap', 0)

        if mid > 0 and hvl > 0:
            above_hvl = mid > hvl
            above_vwap = mid > vwap if vwap > 0 else True

            # Bloquer contre-tendance forte
            if direction == 'LONG' and not above_hvl and not above_vwap:
                return False, None, confidence, "LONG bloqué (tendance baissière)"

            if direction == 'SHORT' and above_hvl and above_vwap:
                return False, None, confidence, "SHORT bloqué (tendance haussière)"

    # Signal valide!
    return True, direction, confidence, "OK"


def simulate_trade(snapshot: Dict, direction: str, symbol: str,
                   future_snapshots: List[Dict], config: Dict) -> Optional[TradeResult]:
    """
    Simule un trade avec les données futures.

    Returns:
        TradeResult ou None si impossible de simuler
    """

    entry_price = snapshot.get('mid', snapshot.get('price', 0))
    if entry_price <= 0:
        return None

    tick_size = 0.25 if symbol in ['ES', 'NQ'] else 0.10
    tick_value = 12.50 if symbol == 'ES' else 5.0

    tp_ticks = config['tp_ticks'].get(symbol, 15)
    sl_ticks = config['sl_ticks'].get(symbol, 15)

    # Calculer prix TP et SL
    if direction == 'LONG':
        tp_price = entry_price + (tp_ticks * tick_size)
        sl_price = entry_price - (sl_ticks * tick_size)
    else:  # SHORT
        tp_price = entry_price - (tp_ticks * tick_size)
        sl_price = entry_price + (sl_ticks * tick_size)

    # Simuler avec les snapshots futurs
    entry_ts = snapshot.get('timestamp', snapshot.get('ts', ''))

    for future_snap in future_snapshots:
        high = future_snap.get('high', future_snap.get('mid', 0))
        low = future_snap.get('low', future_snap.get('mid', 0))
        mid = future_snap.get('mid', 0)

        if high <= 0 or low <= 0:
            continue

        exit_ts = future_snap.get('timestamp', future_snap.get('ts', ''))

        if direction == 'LONG':
            # Check TP
            if high >= tp_price:
                return TradeResult(
                    symbol=symbol,
                    direction=direction,
                    entry_price=entry_price,
                    entry_time=entry_ts,
                    exit_price=tp_price,
                    exit_time=exit_ts,
                    pnl_ticks=tp_ticks,
                    pnl_usd=tp_ticks * tick_value,
                    exit_reason='TP',
                    confidence=snapshot.get('confidence', 0.5),
                    distance_to_level=get_closest_menthorq_level(snapshot, symbol)
                )

            # Check SL
            if low <= sl_price:
                return TradeResult(
                    symbol=symbol,
                    direction=direction,
                    entry_price=entry_price,
                    entry_time=entry_ts,
                    exit_price=sl_price,
                    exit_time=exit_ts,
                    pnl_ticks=-sl_ticks,
                    pnl_usd=-sl_ticks * tick_value,
                    exit_reason='SL',
                    confidence=snapshot.get('confidence', 0.5),
                    distance_to_level=get_closest_menthorq_level(snapshot, symbol)
                )

        else:  # SHORT
            # Check TP
            if low <= tp_price:
                return TradeResult(
                    symbol=symbol,
                    direction=direction,
                    entry_price=entry_price,
                    entry_time=entry_ts,
                    exit_price=tp_price,
                    exit_time=exit_ts,
                    pnl_ticks=tp_ticks,
                    pnl_usd=tp_ticks * tick_value,
                    exit_reason='TP',
                    confidence=snapshot.get('confidence', 0.5),
                    distance_to_level=get_closest_menthorq_level(snapshot, symbol)
                )

            # Check SL
            if high >= sl_price:
                return TradeResult(
                    symbol=symbol,
                    direction=direction,
                    entry_price=entry_price,
                    entry_time=entry_ts,
                    exit_price=sl_price,
                    exit_time=exit_ts,
                    pnl_ticks=-sl_ticks,
                    pnl_usd=-sl_ticks * tick_value,
                    exit_reason='SL',
                    confidence=snapshot.get('confidence', 0.5),
                    distance_to_level=get_closest_menthorq_level(snapshot, symbol)
                )

    # Timeout - pas de sortie trouvée
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# BACKTEST PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

def run_backtest(snapshots: List[Dict], symbol: str, config: Dict) -> BacktestResult:
    """
    Exécute le backtest avec une configuration donnée.
    """

    trades = []
    rejection_reasons = defaultdict(int)
    signals_generated = 0
    signals_rejected = 0

    # Cooldown entre trades (en nombre de snapshots)
    cooldown = 0
    cooldown_period = 60  # ~60 snapshots = ~1-2 minutes selon fréquence

    for i, snapshot in enumerate(snapshots):
        # Respecter cooldown
        if cooldown > 0:
            cooldown -= 1
            continue

        # Générer signal
        signal_valid, direction, confidence, reason = simulate_signal_generation(
            snapshot, symbol, config
        )

        signals_generated += 1

        if not signal_valid:
            signals_rejected += 1
            rejection_reasons[reason] += 1
            continue

        # Simuler trade avec les 100 snapshots suivants
        future_snaps = snapshots[i+1:i+101]

        if len(future_snaps) < 10:
            continue

        trade = simulate_trade(snapshot, direction, symbol, future_snaps, config)

        if trade:
            trades.append(trade)
            cooldown = cooldown_period  # Reset cooldown

    # Calculer métriques
    total_trades = len(trades)

    if total_trades == 0:
        return BacktestResult(
            config_name=config['name'],
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=0.0,
            total_pnl=0.0,
            avg_pnl_per_trade=0.0,
            profit_factor=0.0,
            max_drawdown=0.0,
            trades_per_day=0.0,
            signals_generated=signals_generated,
            signals_rejected=signals_rejected,
            rejection_rate=100.0,
            rejection_reasons=dict(rejection_reasons),
            trades=trades
        )

    winning_trades = len([t for t in trades if t.pnl_usd > 0])
    losing_trades = len([t for t in trades if t.pnl_usd < 0])

    total_pnl = sum(t.pnl_usd for t in trades)
    avg_pnl = total_pnl / total_trades

    gross_profit = sum(t.pnl_usd for t in trades if t.pnl_usd > 0)
    gross_loss = abs(sum(t.pnl_usd for t in trades if t.pnl_usd < 0))

    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 999

    # Max drawdown
    running_pnl = 0
    peak = 0
    max_dd = 0
    for t in trades:
        running_pnl += t.pnl_usd
        if running_pnl > peak:
            peak = running_pnl
        dd = peak - running_pnl
        if dd > max_dd:
            max_dd = dd

    # Trades par jour (approximation)
    trades_per_day = total_trades  # Sera ajusté selon période

    rejection_rate = (signals_rejected / signals_generated * 100) if signals_generated > 0 else 0

    return BacktestResult(
        config_name=config['name'],
        total_trades=total_trades,
        winning_trades=winning_trades,
        losing_trades=losing_trades,
        win_rate=(winning_trades / total_trades * 100),
        total_pnl=total_pnl,
        avg_pnl_per_trade=avg_pnl,
        profit_factor=profit_factor,
        max_drawdown=max_dd,
        trades_per_day=trades_per_day,
        signals_generated=signals_generated,
        signals_rejected=signals_rejected,
        rejection_rate=rejection_rate,
        rejection_reasons=dict(rejection_reasons),
        trades=trades
    )


def print_results(results: Dict[str, BacktestResult], symbol: str):
    """Affiche les résultats comparatifs."""

    print("\n" + "=" * 100)
    print(f"                    RÉSULTATS BACKTEST COMPARATIF - {symbol}")
    print("=" * 100)

    print(f"\n{'Config':<35} {'Trades':>8} {'WR%':>8} {'P&L':>12} {'PF':>8} {'Rej%':>8}")
    print("-" * 100)

    for config_name, result in results.items():
        print(f"{result.config_name:<35} {result.total_trades:>8} "
              f"{result.win_rate:>7.1f}% ${result.total_pnl:>10,.0f} "
              f"{result.profit_factor:>7.2f} {result.rejection_rate:>7.1f}%")

    print("-" * 100)

    # Détails des rejections par config
    print("\n📊 RAISONS DE REJET PAR CONFIGURATION:\n")

    for config_name, result in results.items():
        print(f"\n{result.config_name}:")
        if result.rejection_reasons:
            for reason, count in sorted(result.rejection_reasons.items(),
                                        key=lambda x: -x[1])[:5]:
                pct = count / result.signals_generated * 100 if result.signals_generated > 0 else 0
                print(f"  • {reason}: {count} ({pct:.1f}%)")
        else:
            print("  • Aucun rejet")

    print("\n" + "=" * 100)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """Point d'entrée principal."""

    print("\n" + "=" * 80)
    print("     BACKTEST COMPARATIF - MIA IA SYSTEM")
    print("     Compare CURRENT vs SIMPLIFIED vs MINIMAL")
    print("=" * 80)

    symbols = ['ES', 'NQ']

    for symbol in symbols:
        print(f"\n🔄 Chargement des données {symbol}...")

        # Charger les snapshots
        snapshots = load_snapshots_from_calibrage(symbol, max_files=2000)

        if len(snapshots) < 100:
            print(f"⚠️ Pas assez de données pour {symbol} ({len(snapshots)} snapshots)")
            continue

        print(f"✅ {len(snapshots)} snapshots chargés")

        # Exécuter backtest pour chaque config
        results = {}

        for config_name, config in CONFIGS.items():
            print(f"   ▶ Backtest {config_name}...")
            result = run_backtest(snapshots, symbol, config)
            results[config_name] = result

        # Afficher résultats
        print_results(results, symbol)

    print("\n✅ BACKTEST TERMINÉ")
    print("\n💡 CONCLUSION:")
    print("   • Si SIMPLIFIED a plus de trades et WR similaire → ADOPTER")
    print("   • Si SIMPLIFIED a WR < 45% → Ajuster les seuils")
    print("   • Si MINIMAL a WR > 50% → Preuve que système filtre trop")


if __name__ == "__main__":
    main()









