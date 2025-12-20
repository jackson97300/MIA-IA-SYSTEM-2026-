"""
🎯 BACKTEST COMPLET: PARAMÈTRE PRESSURE_STRENGTH
================================================

Rejoue toutes les journées de Novembre + Décembre 2025
Teste différents seuils de pressure_strength
Compare les résultats pour trouver le seuil optimal

Données: ~24 jours de trading (Nov 05 - Dec 06)
Symboles: ES (CHART_3) et NQ (CHART_9)
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from collections import defaultdict
from dataclasses import dataclass
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_PATH = Path(r"D:\MIA_IA_system\DATA_SIERRA_CHART\DATA_2025")

# Mapping symbole -> Chart ID
CHART_MAPPING = {
    "ES": 3,
    "NQ": 9,
    "RTY": 1
}

# Symboles à analyser
SYMBOLS = ["ES", "NQ"]

# Mois à analyser
MONTHS = ["NOVEMBRE", "DECEMBRE"]

# Tick values pour calcul P&L
TICK_VALUES = {
    "ES": 12.50,
    "NQ": 5.00,
    "RTY": 5.00
}

# Seuils de pressure_strength à tester
PRESSURE_THRESHOLDS = [0.00, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40]

# Configuration de simulation de trades
SIM_CONFIG = {
    "ES": {
        "min_confidence": 0.30,
        "tp_ticks": 40,
        "sl_ticks": 20,
    },
    "NQ": {
        "min_confidence": 0.30,
        "tp_ticks": 50,
        "sl_ticks": 25,
    }
}

# Sessions de trading (heure Paris)
TRADING_SESSIONS = {
    "LONDON": (8, 0, 11, 0),      # 08:00 - 11:00
    "US_MORNING": (15, 50, 17, 0), # 15:50 - 17:00
    "POWER_HOUR": (20, 0, 21, 30)  # 20:00 - 21:30
}

# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class SimulatedSignal:
    """Signal de trading simulé"""
    timestamp: int
    symbol: str
    direction: str  # LONG ou SHORT
    entry_price: float
    confidence: float
    pressure_strength: float
    delta: float
    vol: float
    menthorq_score: float = 0.0
    orderflow_score: float = 0.0
    context_score: float = 0.0

@dataclass
class SimulatedTrade:
    """Résultat de trade simulé"""
    signal: SimulatedSignal
    result: str  # WIN, LOSS, BE
    pnl_ticks: float
    pnl_usd: float
    exit_reason: str

# ============================================================================
# FONCTIONS DE CHARGEMENT DES DONNÉES
# ============================================================================

def get_all_dates(base_path: Path, months: List[str]) -> List[Tuple[str, str, Path]]:
    """Récupère toutes les dates disponibles pour les mois donnés"""
    dates = []

    for month in months:
        month_path = base_path / month
        if not month_path.exists():
            continue

        for date_dir in month_path.iterdir():
            if date_dir.is_dir() and date_dir.name.isdigit() and len(date_dir.name) == 8:
                dates.append((month, date_dir.name, date_dir))

    # Trier par date
    dates.sort(key=lambda x: x[1])
    return dates


def load_ml_ready_file(date_path: Path, symbol: str) -> List[Dict]:
    """Charge un fichier ML_READY pour un symbole donné"""
    chart_id = CHART_MAPPING.get(symbol)
    if not chart_id:
        return []

    # Construire le chemin du fichier
    # Format: ml_{SYMBOL}Z25_FUT_CME_{ID}.jsonl
    ml_ready_path = date_path / f"CHART_{chart_id}" / "ML_READY"

    if not ml_ready_path.exists():
        return []

    # Trouver le fichier JSONL
    jsonl_files = list(ml_ready_path.glob(f"ml_*{symbol}*.jsonl"))
    if not jsonl_files:
        return []

    file_path = jsonl_files[0]

    snapshots = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    try:
                        snapshot = json.loads(line)
                        snapshots.append(snapshot)
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        print(f"   ⚠️ Erreur lecture {file_path}: {e}")

    return snapshots


def is_in_trading_session(timestamp_ms: int) -> Tuple[bool, str]:
    """Vérifie si le timestamp est dans une session de trading"""
    # Convertir timestamp en heure Paris (UTC+1)
    dt = datetime.utcfromtimestamp(timestamp_ms / 1000)
    dt_paris = dt + timedelta(hours=1)  # Approximation UTC+1

    hour = dt_paris.hour
    minute = dt_paris.minute
    time_decimal = hour + minute / 60

    for session_name, (start_h, start_m, end_h, end_m) in TRADING_SESSIONS.items():
        start_decimal = start_h + start_m / 60
        end_decimal = end_h + end_m / 60

        if start_decimal <= time_decimal <= end_decimal:
            return True, session_name

    return False, "CLOSED"

# ============================================================================
# SIMULATION DES SIGNAUX
# ============================================================================

def extract_signal_from_snapshot(snapshot: Dict, symbol: str) -> Optional[SimulatedSignal]:
    """
    Extrait un signal potentiel d'un snapshot
    Simule la logique de génération de signaux du bot
    """
    # Vérifier les champs essentiels
    required_fields = ['t_ms', 'mid', 'delta', 'pressure_strength']
    for field in required_fields:
        if field not in snapshot:
            return None

    t_ms = snapshot.get('t_ms', 0)
    mid = snapshot.get('mid', 0)
    delta = snapshot.get('delta', 0)
    pressure = snapshot.get('pressure_strength', 0)
    vol = snapshot.get('vol', 0) or snapshot.get('volume', 0) or 0

    # Vérifier session de trading
    in_session, session_name = is_in_trading_session(t_ms)
    if not in_session:
        return None

    # Simuler la logique de direction basée sur delta et autres indicateurs
    # Delta positif fort = pression acheteuse = LONG
    # Delta négatif fort = pression vendeuse = SHORT

    # Seuil pour générer un signal (simplifié)
    DELTA_THRESHOLD = 50  # Ajuster selon les données réelles

    if abs(delta) < DELTA_THRESHOLD:
        return None  # Pas assez de conviction

    direction = "LONG" if delta > 0 else "SHORT"

    # Calculer une confidence simulée basée sur les scores disponibles
    menthorq = snapshot.get('menthorq_score', 0) or snapshot.get('layer1_score', 0) or 0.5
    orderflow = snapshot.get('orderflow_score', 0) or snapshot.get('layer2_score', 0) or 0.5
    context = snapshot.get('context_score', 0) or snapshot.get('layer3_score', 0) or 0.5

    # Confidence = moyenne pondérée (comme le ML 3-Layer)
    confidence = menthorq * 0.5 + orderflow * 0.3 + context * 0.2

    # Si pas de scores ML, utiliser pressure_strength comme proxy
    if confidence == 0:
        confidence = min(1.0, pressure + 0.3)  # Proxy basé sur pressure

    config = SIM_CONFIG.get(symbol, SIM_CONFIG["ES"])
    if confidence < config["min_confidence"]:
        return None

    return SimulatedSignal(
        timestamp=t_ms,
        symbol=symbol,
        direction=direction,
        entry_price=mid,
        confidence=confidence,
        pressure_strength=pressure,
        delta=delta,
        vol=vol,
        menthorq_score=menthorq,
        orderflow_score=orderflow,
        context_score=context
    )


def simulate_trade_outcome(signal: SimulatedSignal, subsequent_snapshots: List[Dict]) -> SimulatedTrade:
    """
    Simule le résultat d'un trade basé sur les snapshots suivants
    Regarde si TP ou SL aurait été touché
    """
    config = SIM_CONFIG.get(signal.symbol, SIM_CONFIG["ES"])
    tick_value = TICK_VALUES.get(signal.symbol, 12.50)

    # Calculer TP et SL en prix
    if signal.symbol == "ES":
        tick_size = 0.25
    elif signal.symbol == "NQ":
        tick_size = 0.25
    else:
        tick_size = 0.10

    if signal.direction == "LONG":
        tp_price = signal.entry_price + (config["tp_ticks"] * tick_size)
        sl_price = signal.entry_price - (config["sl_ticks"] * tick_size)
    else:  # SHORT
        tp_price = signal.entry_price - (config["tp_ticks"] * tick_size)
        sl_price = signal.entry_price + (config["sl_ticks"] * tick_size)

    # Parcourir les snapshots suivants (max 30 min = ~1800 snapshots à 1/sec)
    max_duration_ms = 30 * 60 * 1000  # 30 minutes

    for snap in subsequent_snapshots[:1800]:
        snap_time = snap.get('t_ms', 0)
        if snap_time - signal.timestamp > max_duration_ms:
            break  # Timeout

        snap_mid = snap.get('mid', 0)
        snap_high = snap.get('high', snap_mid)
        snap_low = snap.get('low', snap_mid)

        # Vérifier TP
        if signal.direction == "LONG":
            if snap_high >= tp_price:
                return SimulatedTrade(
                    signal=signal,
                    result="WIN",
                    pnl_ticks=config["tp_ticks"],
                    pnl_usd=config["tp_ticks"] * tick_value,
                    exit_reason="TP_HIT"
                )
            if snap_low <= sl_price:
                return SimulatedTrade(
                    signal=signal,
                    result="LOSS",
                    pnl_ticks=-config["sl_ticks"],
                    pnl_usd=-config["sl_ticks"] * tick_value,
                    exit_reason="SL_HIT"
                )
        else:  # SHORT
            if snap_low <= tp_price:
                return SimulatedTrade(
                    signal=signal,
                    result="WIN",
                    pnl_ticks=config["tp_ticks"],
                    pnl_usd=config["tp_ticks"] * tick_value,
                    exit_reason="TP_HIT"
                )
            if snap_high >= sl_price:
                return SimulatedTrade(
                    signal=signal,
                    result="LOSS",
                    pnl_ticks=-config["sl_ticks"],
                    pnl_usd=-config["sl_ticks"] * tick_value,
                    exit_reason="SL_HIT"
                )

    # Timeout - considérer comme BE
    return SimulatedTrade(
        signal=signal,
        result="BE",
        pnl_ticks=0,
        pnl_usd=0,
        exit_reason="TIMEOUT"
    )

# ============================================================================
# BACKTEST PRINCIPAL
# ============================================================================

def run_backtest_for_threshold(
    all_data: Dict[str, List[Tuple[str, List[Dict]]]],
    pressure_threshold: float,
    min_signal_interval_ms: int = 300000  # 5 minutes entre signaux
) -> Dict[str, Any]:
    """
    Exécute le backtest pour un seuil de pressure_strength donné
    """
    results = {
        "threshold": pressure_threshold,
        "total_signals": 0,
        "signals_accepted": 0,
        "signals_rejected": 0,
        "trades": [],
        "by_symbol": {},
        "by_session": defaultdict(lambda: {"trades": 0, "wins": 0, "pnl": 0}),
        "by_date": defaultdict(lambda: {"trades": 0, "wins": 0, "pnl": 0})
    }

    for symbol in SYMBOLS:
        results["by_symbol"][symbol] = {
            "signals": 0,
            "accepted": 0,
            "rejected": 0,
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "be": 0,
            "pnl_total": 0,
            "win_rate": 0
        }

    # Traiter chaque symbole
    for symbol in SYMBOLS:
        if symbol not in all_data:
            continue

        last_signal_time = 0

        for date_str, snapshots in all_data[symbol]:
            if not snapshots:
                continue

            # Parcourir les snapshots
            for i, snapshot in enumerate(snapshots):
                # Extraire signal potentiel
                signal = extract_signal_from_snapshot(snapshot, symbol)
                if not signal:
                    continue

                results["total_signals"] += 1
                results["by_symbol"][symbol]["signals"] += 1

                # Vérifier cooldown
                if signal.timestamp - last_signal_time < min_signal_interval_ms:
                    continue

                # 🎯 FILTRE PRESSURE_STRENGTH
                if signal.pressure_strength < pressure_threshold:
                    results["signals_rejected"] += 1
                    results["by_symbol"][symbol]["rejected"] += 1
                    continue

                results["signals_accepted"] += 1
                results["by_symbol"][symbol]["accepted"] += 1
                last_signal_time = signal.timestamp

                # Simuler le trade
                subsequent = snapshots[i+1:i+1801] if i+1 < len(snapshots) else []
                trade = simulate_trade_outcome(signal, subsequent)

                results["trades"].append(trade)
                results["by_symbol"][symbol]["trades"] += 1
                results["by_symbol"][symbol]["pnl_total"] += trade.pnl_usd

                if trade.result == "WIN":
                    results["by_symbol"][symbol]["wins"] += 1
                elif trade.result == "LOSS":
                    results["by_symbol"][symbol]["losses"] += 1
                else:
                    results["by_symbol"][symbol]["be"] += 1

                # Stats par session
                _, session = is_in_trading_session(signal.timestamp)
                results["by_session"][session]["trades"] += 1
                results["by_session"][session]["pnl"] += trade.pnl_usd
                if trade.result == "WIN":
                    results["by_session"][session]["wins"] += 1

                # Stats par date
                results["by_date"][date_str]["trades"] += 1
                results["by_date"][date_str]["pnl"] += trade.pnl_usd
                if trade.result == "WIN":
                    results["by_date"][date_str]["wins"] += 1

    # Calculer win rates
    for symbol in SYMBOLS:
        stats = results["by_symbol"][symbol]
        if stats["trades"] > 0:
            stats["win_rate"] = (stats["wins"] / stats["trades"]) * 100

    return results


def print_results_comparison(all_results: List[Dict]):
    """Affiche la comparaison des résultats pour tous les seuils"""

    print("\n" + "="*120)
    print("📊 RÉSULTATS DU BACKTEST PRESSURE_STRENGTH")
    print("="*120)

    print(f"\n{'Seuil':<10} {'Signaux':<10} {'Acceptés':<10} {'Rejetés':<10} {'Trades':<10} {'Wins':<8} {'Losses':<8} {'Win Rate':<10} {'P&L Total':<12}")
    print("-"*120)

    for result in all_results:
        threshold = result["threshold"]
        total_signals = result["total_signals"]
        accepted = result["signals_accepted"]
        rejected = result["signals_rejected"]
        trades = len(result["trades"])
        wins = sum(1 for t in result["trades"] if t.result == "WIN")
        losses = sum(1 for t in result["trades"] if t.result == "LOSS")
        win_rate = (wins / trades * 100) if trades > 0 else 0
        pnl = sum(t.pnl_usd for t in result["trades"])

        pnl_str = f"${pnl:+,.2f}"
        if pnl > 0:
            pnl_str = f"✅ {pnl_str}"
        elif pnl < 0:
            pnl_str = f"❌ {pnl_str}"

        print(f"{threshold:<10.2f} {total_signals:<10} {accepted:<10} {rejected:<10} {trades:<10} {wins:<8} {losses:<8} {win_rate:<10.1f}% {pnl_str:<12}")

    # Trouver le meilleur seuil
    print("\n" + "="*120)
    print("🎯 ANALYSE DU MEILLEUR SEUIL")
    print("="*120)

    # Meilleur par P&L
    best_pnl = max(all_results, key=lambda x: sum(t.pnl_usd for t in x["trades"]))
    best_pnl_value = sum(t.pnl_usd for t in best_pnl["trades"])

    # Meilleur par Win Rate (min 10 trades)
    valid_for_wr = [r for r in all_results if len(r["trades"]) >= 10]
    if valid_for_wr:
        best_wr = max(valid_for_wr, key=lambda x: sum(1 for t in x["trades"] if t.result == "WIN") / max(1, len(x["trades"])))
        best_wr_value = sum(1 for t in best_wr["trades"] if t.result == "WIN") / max(1, len(best_wr["trades"])) * 100
    else:
        best_wr = all_results[0]
        best_wr_value = 0

    # Meilleur compromis (P&L * Win Rate)
    def score(r):
        trades = r["trades"]
        if len(trades) < 5:
            return 0
        pnl = sum(t.pnl_usd for t in trades)
        wr = sum(1 for t in trades if t.result == "WIN") / len(trades)
        return pnl * wr

    best_compromise = max(all_results, key=score)

    print(f"\n📈 MEILLEUR P&L:")
    print(f"   Seuil: {best_pnl['threshold']:.2f}")
    print(f"   P&L: ${best_pnl_value:+,.2f}")
    print(f"   Trades: {len(best_pnl['trades'])}")

    print(f"\n🎯 MEILLEUR WIN RATE (min 10 trades):")
    print(f"   Seuil: {best_wr['threshold']:.2f}")
    print(f"   Win Rate: {best_wr_value:.1f}%")
    print(f"   Trades: {len(best_wr['trades'])}")

    print(f"\n⚖️ MEILLEUR COMPROMIS (P&L × Win Rate):")
    print(f"   Seuil: {best_compromise['threshold']:.2f}")
    trades = best_compromise["trades"]
    pnl = sum(t.pnl_usd for t in trades)
    wr = sum(1 for t in trades if t.result == "WIN") / max(1, len(trades)) * 100
    print(f"   P&L: ${pnl:+,.2f}")
    print(f"   Win Rate: {wr:.1f}%")
    print(f"   Trades: {len(trades)}")


def print_detailed_analysis(result: Dict, threshold: float):
    """Affiche l'analyse détaillée pour un seuil donné"""

    print(f"\n{'='*100}")
    print(f"📊 ANALYSE DÉTAILLÉE - SEUIL {threshold:.2f}")
    print(f"{'='*100}")

    # Par symbole
    print(f"\n📈 PAR SYMBOLE:")
    print(f"{'Symbole':<10} {'Signals':<10} {'Accepted':<10} {'Trades':<10} {'Wins':<8} {'Losses':<8} {'WR%':<10} {'P&L':<12}")
    print("-"*80)

    for symbol, stats in result["by_symbol"].items():
        pnl_str = f"${stats['pnl_total']:+,.2f}"
        print(f"{symbol:<10} {stats['signals']:<10} {stats['accepted']:<10} {stats['trades']:<10} {stats['wins']:<8} {stats['losses']:<8} {stats['win_rate']:<10.1f} {pnl_str:<12}")

    # Par session
    print(f"\n⏰ PAR SESSION:")
    print(f"{'Session':<15} {'Trades':<10} {'Wins':<10} {'WR%':<10} {'P&L':<12}")
    print("-"*60)

    for session, stats in result["by_session"].items():
        if stats["trades"] > 0:
            wr = (stats["wins"] / stats["trades"]) * 100
            pnl_str = f"${stats['pnl']:+,.2f}"
            print(f"{session:<15} {stats['trades']:<10} {stats['wins']:<10} {wr:<10.1f} {pnl_str:<12}")

    # Top 5 meilleurs et pires jours
    print(f"\n📅 TOP 5 MEILLEURS JOURS:")
    sorted_dates = sorted(result["by_date"].items(), key=lambda x: x[1]["pnl"], reverse=True)
    for date, stats in sorted_dates[:5]:
        if stats["trades"] > 0:
            wr = (stats["wins"] / stats["trades"]) * 100
            print(f"   {date}: {stats['trades']} trades, {wr:.0f}% WR, ${stats['pnl']:+,.2f}")

    print(f"\n📅 TOP 5 PIRES JOURS:")
    for date, stats in sorted_dates[-5:]:
        if stats["trades"] > 0:
            wr = (stats["wins"] / stats["trades"]) * 100
            print(f"   {date}: {stats['trades']} trades, {wr:.0f}% WR, ${stats['pnl']:+,.2f}")


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("="*100)
    print("🚀 BACKTEST COMPLET - PARAMÈTRE PRESSURE_STRENGTH")
    print("="*100)
    print(f"\n📅 Période: Novembre - Décembre 2025")
    print(f"📊 Symboles: {', '.join(SYMBOLS)}")
    print(f"🎯 Seuils testés: {PRESSURE_THRESHOLDS}")

    # Récupérer toutes les dates disponibles
    print(f"\n📂 Chargement des données...")
    all_dates = get_all_dates(BASE_PATH, MONTHS)
    print(f"   ✅ {len(all_dates)} jours de données trouvés")

    # Charger toutes les données ML_READY
    print(f"\n📥 Chargement des snapshots ML_READY...")
    all_data: Dict[str, List[Tuple[str, List[Dict]]]] = {symbol: [] for symbol in SYMBOLS}

    total_snapshots = 0
    snapshots_with_pressure = 0

    for month, date_str, date_path in all_dates:
        for symbol in SYMBOLS:
            snapshots = load_ml_ready_file(date_path, symbol)
            if snapshots:
                all_data[symbol].append((date_str, snapshots))
                total_snapshots += len(snapshots)

                # Compter ceux avec pressure_strength
                for s in snapshots:
                    if 'pressure_strength' in s:
                        snapshots_with_pressure += 1

                print(f"   ✅ {date_str} {symbol}: {len(snapshots):,} snapshots")

    print(f"\n📊 STATISTIQUES DES DONNÉES:")
    print(f"   Total snapshots: {total_snapshots:,}")
    print(f"   Avec pressure_strength: {snapshots_with_pressure:,} ({100*snapshots_with_pressure/max(1,total_snapshots):.1f}%)")

    if snapshots_with_pressure == 0:
        print("\n⚠️ ATTENTION: Aucun snapshot avec pressure_strength trouvé!")
        print("   Le champ pressure_strength n'existe peut-être pas dans les données ML_READY.")
        print("   Vérifions les champs disponibles...")

        # Afficher les champs d'un snapshot exemple
        for symbol in SYMBOLS:
            if all_data[symbol]:
                date_str, snaps = all_data[symbol][0]
                if snaps:
                    print(f"\n   Champs disponibles dans {symbol} ({date_str}):")
                    for key in sorted(snaps[0].keys()):
                        print(f"      - {key}: {type(snaps[0][key]).__name__} = {snaps[0][key]}")
                    break
        return

    # Exécuter le backtest pour chaque seuil
    print(f"\n🔄 Exécution du backtest pour {len(PRESSURE_THRESHOLDS)} seuils...")

    all_results = []
    for threshold in PRESSURE_THRESHOLDS:
        print(f"   Testing threshold {threshold:.2f}...", end=" ")
        start_time = time.time()

        result = run_backtest_for_threshold(all_data, threshold)
        all_results.append(result)

        elapsed = time.time() - start_time
        trades = len(result["trades"])
        pnl = sum(t.pnl_usd for t in result["trades"])
        print(f"✅ {trades} trades, ${pnl:+,.2f} ({elapsed:.1f}s)")

    # Afficher les résultats
    print_results_comparison(all_results)

    # Analyse détaillée du meilleur seuil
    best = max(all_results, key=lambda x: sum(t.pnl_usd for t in x["trades"]))
    print_detailed_analysis(best, best["threshold"])

    # Recommandation finale
    print("\n" + "="*100)
    print("💡 RECOMMANDATION FINALE")
    print("="*100)

    # Trouver le sweet spot
    for result in all_results:
        trades = result["trades"]
        if len(trades) >= 10:
            pnl = sum(t.pnl_usd for t in trades)
            wr = sum(1 for t in trades if t.result == "WIN") / len(trades) * 100
            if pnl > 0 and wr >= 50:
                print(f"\n✅ SEUIL RECOMMANDÉ: {result['threshold']:.2f}")
                print(f"   - P&L: ${pnl:+,.2f}")
                print(f"   - Win Rate: {wr:.1f}%")
                print(f"   - Trades: {len(trades)}")
                print(f"\n   Ce seuil offre un bon compromis entre:")
                print(f"   - Nombre de trades (pas trop restrictif)")
                print(f"   - Win Rate > 50%")
                print(f"   - P&L positif")
                break

    print("\n" + "="*100)
    print("✅ BACKTEST TERMINÉ")
    print("="*100)


if __name__ == "__main__":
    main()
