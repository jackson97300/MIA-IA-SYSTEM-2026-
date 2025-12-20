#!/usr/bin/env python3
"""
🎯 BACKTEST MENTHORQ CORRIGÉ - Utilise ML 3-Layer Filter
========================================================================

CORRECTIONS APPLIQUÉES:
- ✅ 1 signal/bar maximum (via ML3LayerStrategy)
- ✅ Filtres ML 3-Layer (Layer 1/2/3)
- ✅ SL/TP confluence-based (via stratégie)
- ✅ Filtres contextuels (VIX, volume, etc.)

Date: 23 Novembre 2025
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json
import logging
import time
from collections import defaultdict

# Ajouter racine au path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from ml.backtester.jsonl_loader import JSONLSnapshotLoader
from ml.ml_3layer_integrated_system import ML3LayerIntegratedSystem
from strategies.ml_3layer_strategy import ML3LayerStrategy

logger = logging.getLogger(__name__)


class MenthorQBacktesterCorrected:
    """
    Backtester corrigé utilisant ML 3-Layer Filter
    Génère 1 signal par bar maximum
    """

    def __init__(self, config: Dict):
        """
        Initialise le backtester corrigé

        Args:
            config: Configuration du backtest
        """
        self.config = config
        self.symbols = config.get('symbols', ['ES', 'NQ'])

        # Support date_range ou start_date/end_date
        date_range = config.get('date_range', {})
        if date_range:
            self.start_date = pd.to_datetime(date_range.get('start', '2025-11-05'))
            self.end_date = pd.to_datetime(date_range.get('end', '2025-11-21'))
        else:
            self.start_date = pd.to_datetime(config.get('start_date', '2025-11-05'))
            self.end_date = pd.to_datetime(config.get('end_date', '2025-11-21'))

        # Convertir chemin data_path en absolu
        data_path = config.get('data_path', 'DATA_SIERRA_CHART/DATA_2025/NOVEMBRE')
        if not Path(data_path).is_absolute():
            self.data_path = str(project_root / data_path)
        else:
            self.data_path = data_path

        # Loader
        self.loader = JSONLSnapshotLoader(self.data_path)

        # Système ML 3-Layer
        # ⚠️ DÉSACTIVER ML TEMPORAIREMENT (modèles mal entraînés)
        # use_ml_models=False → utilise seulement les règles (Layer 1/2/3)
        use_ml = config.get('use_ml_models', False)  # Par défaut False pour backtest

        self.ml_system = ML3LayerIntegratedSystem(
            symbols=self.symbols,
            use_ml_models=use_ml
        )

        # Stratégie ML 3-Layer (génère 1 signal/bar max)
        self.strategy = ML3LayerStrategy(ml_3layer_system=self.ml_system)

        # Résultats
        self.all_trades: List[Dict] = []
        self.open_positions: Dict[str, Dict] = {}

        # Configuration ticks
        self.tick_sizes = {
            'ES': 0.25,
            'NQ': 0.25,
            'RTY': 0.10
        }

        self.tick_values = {
            'ES': 12.50,
            'NQ': 5.00,
            'RTY': 10.00
        }

        self.fees_per_trade = {
            'ES': 0.12,
            'NQ': 0.28,
            'RTY': 0.30
        }

        # Stats
        self.level_stats = defaultdict(lambda: {'wins': 0, 'losses': 0, 'pnl': 0})
        self.time_stats = defaultdict(lambda: {'wins': 0, 'losses': 0, 'pnl': 0})

        logger.info("="*80)
        logger.info("BACKTEST MENTHORQ CORRIGE - ML 3-LAYER FILTER")
        logger.info("="*80)
        logger.info(f"Symboles: {self.symbols}")
        logger.info(f"Periode: {self.start_date.date()} a {self.end_date.date()}")
        logger.info("CORRECTIONS: 1 signal/bar max, Filtres ML 3-Layer actifs")

    def generate_date_list(self) -> List[str]:
        """Génère liste de dates"""
        dates = []
        current = self.start_date
        while current <= self.end_date:
            dates.append(current.strftime('%Y%m%d'))
            current += timedelta(days=1)
        return dates

    def extract_price_data(self, snapshot: Dict, symbol: str) -> Dict:
        """Extrait données prix depuis snapshot"""
        mid = snapshot.get('mid', snapshot.get('last', 0))
        high = snapshot.get('high', mid + snapshot.get('atr', 5) * 0.3)
        low = snapshot.get('low', mid - snapshot.get('atr', 5) * 0.3)

        return {
            'mid': mid,
            'high': high,
            'low': low,
            'last': snapshot.get('last', mid)
        }

    def check_trade_exit(self, trade: Dict, price_data: Dict, symbol: str) -> Optional[Dict]:
        """Vérifie si un trade doit être fermé"""
        entry = trade['entry']
        stop = trade['stop']
        tp1 = trade['targets'][0] if trade.get('targets') else entry + (entry - stop) * 1.5
        action = trade['action']
        tick_size = self.tick_sizes.get(symbol, 0.25)

        high = price_data['high']
        low = price_data['low']

        exit_price = None
        exit_reason = None

        if action == "LONG":
            if high >= tp1:
                exit_price = tp1
                exit_reason = "TP_HIT"
            elif low <= stop:
                exit_price = stop
                exit_reason = "SL_HIT"
        else:  # SHORT
            if low <= tp1:
                exit_price = tp1
                exit_reason = "TP_HIT"
            elif high >= stop:
                exit_price = stop
                exit_reason = "SL_HIT"

        if exit_price:
            if action == "LONG":
                pnl_points = exit_price - entry
            else:
                pnl_points = entry - exit_price

            pnl_ticks = pnl_points / tick_size
            pnl_ticks_net = pnl_ticks - self.fees_per_trade.get(symbol, 0)

            return {
                'outcome': exit_reason,
                'pnl_ticks': pnl_ticks_net,
                'pnl_dollars': pnl_ticks_net * self.tick_values.get(symbol, 0),
                'exit_price': exit_price
            }

        return None

    def run_backtest(self) -> Dict:
        """Execute le backtest corrigé"""
        logger.info("Demarrage backtest MenthorQ CORRIGE")

        # Générer dates
        dates = self.generate_date_list()
        logger.info(f"Periode: {len(dates)} jours")

        # Charger tous les snapshots
        all_snapshots_by_symbol = {}
        for symbol in self.symbols:
            logger.info(f"\n{'='*60}")
            logger.info(f"Chargement {symbol}")
            logger.info(f"{'='*60}")

            snapshots = self.loader.load_date_range(symbol, dates)
            if snapshots:
                snapshots.sort(key=lambda x: x.get('t_ms', 0))
                all_snapshots_by_symbol[symbol] = snapshots
                logger.info(f"OK: {len(snapshots):,} snapshots charges pour {symbol}")

        if not all_snapshots_by_symbol:
            logger.error("ERREUR: Aucune donnee chargee !")
            return {}

        # Fusionner et trier tous les snapshots
        all_snapshots = []
        for symbol, snapshots in all_snapshots_by_symbol.items():
            for snapshot in snapshots:
                snapshot['_symbol'] = symbol
                all_snapshots.append(snapshot)

        all_snapshots.sort(key=lambda x: x.get('t_ms', 0))
        total_snapshots = len(all_snapshots)

        logger.info(f"\n{'='*60}")
        logger.info(f"DEBUT TRAITEMENT: {total_snapshots:,} snapshots")
        logger.info(f"{'='*60}\n")

        start_time = time.time()
        processed = 0
        signals_generated = 0

        # Traiter chaque snapshot chronologiquement
        for snapshot in all_snapshots:
            symbol = snapshot['_symbol']
            processed += 1

            # Progression
            if processed % 5000 == 0:
                elapsed = time.time() - start_time
                progress = (processed / total_snapshots * 100) if total_snapshots > 0 else 0
                rate = processed / elapsed if elapsed > 0 else 0
                remaining = (total_snapshots - processed) / rate if rate > 0 else 0
                logger.info(
                    f"Progression: {processed:,}/{total_snapshots:,} ({progress:.1f}%) | "
                    f"Signals: {signals_generated:,} | Trades: {len(self.all_trades):,} | "
                    f"Temps: {elapsed:.0f}s | Restant: ~{remaining/60:.1f}min"
                )

            # Extraire données prix
            price_data = self.extract_price_data(snapshot, symbol)

            # Vérifier sorties des positions ouvertes
            positions_to_close = []
            for pos_id, trade in self.open_positions.items():
                if trade['symbol'] == symbol:
                    exit_result = self.check_trade_exit(trade, price_data, symbol)
                    if exit_result:
                        final_trade = {
                            **trade,
                            **exit_result,
                            'exit_timestamp': snapshot.get('t_ms', 0)
                        }
                        self.all_trades.append(final_trade)
                        positions_to_close.append(pos_id)

                        # Stats
                        timestamp = trade.get('entry_timestamp', 0)
                        hour = datetime.fromtimestamp(timestamp / 1000).hour if timestamp else 0
                        hour_key = f"{symbol}_{hour}"
                        if exit_result['outcome'] == 'TP_HIT':
                            self.time_stats[hour_key]['wins'] += 1
                        elif exit_result['outcome'] == 'SL_HIT':
                            self.time_stats[hour_key]['losses'] += 1
                        self.time_stats[hour_key]['pnl'] += exit_result['pnl_ticks']

            # Fermer positions
            for pos_id in positions_to_close:
                del self.open_positions[pos_id]

            # Générer nouveau signal (1 par bar max via ML 3-Layer)
            try:
                signal = self.strategy.generate_signal(snapshot, symbol)

                if signal and signal.get('action') in ['LONG', 'SHORT']:
                    signals_generated += 1
                    position_id = f"{symbol}_{snapshot.get('t_ms', processed)}"

                    trade = {
                        'position_id': position_id,
                        'symbol': symbol,
                        'action': signal['action'],
                        'entry': signal['entry'],
                        'stop': signal['stop'],
                        'targets': signal['targets'],
                        'entry_timestamp': snapshot.get('t_ms', 0),
                        'confidence': signal.get('confidence', 0),
                        'metadata': signal.get('metadata', {})
                    }

                    self.open_positions[position_id] = trade

            except Exception as e:
                logger.warning(f"Erreur generation signal {symbol}: {e}")
                continue

        # Fermer positions restantes
        logger.info("\nFermeture positions restantes...")
        for pos_id, trade in self.open_positions.items():
            last_snapshot = all_snapshots[-1] if all_snapshots else None
            if last_snapshot and last_snapshot.get('_symbol') == trade['symbol']:
                price_data = self.extract_price_data(last_snapshot, trade['symbol'])
                exit_result = self.check_trade_exit(trade, price_data, trade['symbol'])
                if exit_result:
                    final_trade = {
                        **trade,
                        **exit_result,
                        'exit_reason': 'END_OF_DATA',
                        'exit_timestamp': last_snapshot.get('t_ms', 0)
                    }
                    self.all_trades.append(final_trade)

        total_elapsed = time.time() - start_time
        logger.info(f"\n{'='*60}")
        logger.info(f"OK: Backtest CORRIGE termine")
        logger.info(f"  Snapshots traites: {processed:,}")
        logger.info(f"  Signals generes: {signals_generated:,}")
        logger.info(f"  Trades simules: {len(self.all_trades):,}")
        logger.info(f"  Temps: {total_elapsed:.0f}s")
        logger.info(f"{'='*60}")

        return self._compile_results()

    def _compile_results(self) -> Dict:
        """Compile les résultats"""
        if not self.all_trades:
            return {}

        df_trades = pd.DataFrame(self.all_trades)

        wins = (df_trades['outcome'] == 'TP_HIT').sum()
        losses = (df_trades['outcome'] == 'SL_HIT').sum()
        total = wins + losses
        win_rate = (wins / total * 100) if total > 0 else 0
        total_pnl_ticks = df_trades['pnl_ticks'].sum()
        total_pnl_dollars = df_trades['pnl_dollars'].sum()

        return {
            'total_trades': len(df_trades),
            'signals_generated': self.strategy.stats.get('signals_generated', 0),
            'wins': int(wins),
            'losses': int(losses),
            'win_rate': float(win_rate),
            'total_pnl_ticks': float(total_pnl_ticks),
            'total_pnl_dollars': float(total_pnl_dollars),
            'avg_pnl_ticks': float(total_pnl_ticks / total) if total > 0 else 0.0,
            'by_time': dict(self.time_stats),
            'summary': {
                'total_trades': len(df_trades),
                'wins': int(wins),
                'losses': int(losses),
                'win_rate': win_rate / 100.0,
                'total_pnl_ticks': float(total_pnl_ticks),
                'total_pnl_dollars': float(total_pnl_dollars),
                'profit_factor': abs(wins * df_trades[df_trades['outcome'] == 'TP_HIT']['pnl_ticks'].mean() /
                                    (losses * abs(df_trades[df_trades['outcome'] == 'SL_HIT']['pnl_ticks'].mean()))) if losses > 0 and wins > 0 else 0.0
            }
        }
