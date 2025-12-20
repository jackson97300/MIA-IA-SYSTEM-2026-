#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎯 BACKTEST COMPLET STRATÉGIE ML_3LAYER AVEC DONNÉES RÉELLES SIERRA CHART
========================================================================

Objectif:
- Backtester la stratégie ML_3Layer complète avec SL/TP intelligents
- Utiliser les données réelles collectées depuis Sierra Chart (NOVEMBRE 2025)
- Valider les nouvelles optimisations SL/TP basées sur confluence

Structure données:
DATA_SIERRA_CHART/DATA_2025/NOVEMBRE/{DATE}/CHART_{ID}/ML_READY/ml_{SYMBOL}Z25_FUT_CME_{ID}.jsonl

Date: 23 Novembre 2025
"""

import sys
from pathlib import Path
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import logging

# Ajouter racine au path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from strategies.ml_3layer_strategy import ML3LayerStrategy
from ml.ml_3layer_integrated_system import ML3LayerIntegratedSystem
from ml.backtester.jsonl_loader import JSONLSnapshotLoader

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/backtest_complet_reel.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class BacktestCompletStrategieReelle:
    """
    Backtest complet de la stratégie ML_3Layer avec données réelles Sierra Chart
    """

    def __init__(
        self,
        base_path: str = "DATA_SIERRA_CHART/DATA_2025/NOVEMBRE",
        symbols: List[str] = ["ES", "NQ"],
        start_date: str = "20251105",
        end_date: str = "20251121"
    ):
        """
        Initialise le backtester

        Args:
            base_path: Chemin vers dossier NOVEMBRE
            symbols: Liste des symboles à backtester
            start_date: Date de début (YYYYMMDD)
            end_date: Date de fin (YYYYMMDD)
        """
        self.base_path = Path(base_path)
        self.symbols = symbols
        self.start_date = datetime.strptime(start_date, "%Y%m%d")
        self.end_date = datetime.strptime(end_date, "%Y%m%d")

        # Loader JSONL
        self.loader = JSONLSnapshotLoader(str(self.base_path))

        # Système ML
        self.ml_system = ML3LayerIntegratedSystem(
            symbols=symbols,
            use_ml_models=True  # Activer ML pour backtest réaliste
        )

        # Stratégie
        self.strategy = ML3LayerStrategy(ml_3layer_system=self.ml_system)

        # Résultats
        self.all_trades: List[Dict] = []
        self.open_positions: Dict[str, Dict] = {}  # {position_id: trade_dict}

        # Configuration
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

        # Fees (PropFirms)
        self.fees_per_trade = {
            'ES': 0.12,  # ticks
            'NQ': 0.28,  # ticks
            'RTY': 0.30  # ticks
        }

        logger.info("=" * 80)
        logger.info("🎯 BACKTEST COMPLET STRATÉGIE ML_3LAYER - DONNÉES RÉELLES")
        logger.info("=" * 80)
        logger.info(f"Base path: {self.base_path}")
        logger.info(f"Symboles: {self.symbols}")
        logger.info(f"Période: {start_date} → {end_date}")

    def generate_date_list(self) -> List[str]:
        """Génère liste de dates entre start_date et end_date"""
        dates = []
        current = self.start_date
        while current <= self.end_date:
            dates.append(current.strftime("%Y%m%d"))
            current += timedelta(days=1)
        return dates

    def load_all_snapshots(self, symbol: str) -> List[Dict]:
        """Charge tous les snapshots pour un symbole sur la période"""
        dates = self.generate_date_list()
        logger.info(f"\n📂 Chargement snapshots {symbol} ({len(dates)} jours)...")

        all_snapshots = self.loader.load_date_range(symbol, dates)

        if not all_snapshots:
            logger.warning(f"⚠️ Aucun snapshot trouvé pour {symbol}")
            return []

        # Trier par timestamp
        all_snapshots.sort(key=lambda x: x.get('t_ms', 0))

        logger.info(f"✅ {len(all_snapshots):,} snapshots chargés pour {symbol}")
        return all_snapshots

    def extract_price_data(self, snapshot: Dict, symbol: str) -> Dict:
        """
        Extrait données prix depuis snapshot

        Returns:
            dict avec mid, bid, ask, high, low, volume
        """
        # Prix
        mid = snapshot.get('mid', snapshot.get('last', 0))
        bid = snapshot.get('bid', mid - 0.25)
        ask = snapshot.get('ask', mid + 0.25)

        # High/Low (approximation si pas disponible)
        high = snapshot.get('high', mid + snapshot.get('atr', 5) * 0.3)
        low = snapshot.get('low', mid - snapshot.get('atr', 5) * 0.3)

        # Volume
        volume = snapshot.get('volume', snapshot.get('v', 0))

        return {
            'mid': mid,
            'bid': bid,
            'ask': ask,
            'high': high,
            'low': low,
            'volume': volume
        }

    def check_trade_exit(
        self,
        trade: Dict,
        current_price_data: Dict,
        symbol: str
    ) -> Optional[Dict]:
        """
        Vérifie si un trade doit être fermé (TP ou SL)

        Returns:
            dict avec résultat si fermé, None sinon
        """
        entry = trade['entry']
        stop = trade['stop']
        tp1 = trade['targets'][0]
        action = trade['action']
        tick_size = self.tick_sizes[symbol]

        high = current_price_data['high']
        low = current_price_data['low']

        exit_price = None
        exit_reason = None

        if action == "LONG":
            # Vérifier TP
            if high >= tp1:
                exit_price = tp1
                exit_reason = "TP"
            # Vérifier SL
            elif low <= stop:
                exit_price = stop
                exit_reason = "SL"
        else:  # SHORT
            # Vérifier TP
            if low <= tp1:
                exit_price = tp1
                exit_reason = "TP"
            # Vérifier SL
            elif high >= stop:
                exit_price = stop
                exit_reason = "SL"

        if exit_price:
            # Calculer P&L
            if action == "LONG":
                pnl_points = exit_price - entry
            else:
                pnl_points = entry - exit_price

            pnl_ticks = pnl_points / tick_size
            pnl_usd = pnl_ticks * self.tick_values[symbol]

            # Soustraire fees
            pnl_ticks_net = pnl_ticks - self.fees_per_trade[symbol]
            pnl_usd_net = pnl_ticks_net * self.tick_values[symbol]

            return {
                'exit_price': exit_price,
                'exit_reason': exit_reason,
                'pnl_ticks': pnl_ticks_net,
                'pnl_usd': pnl_usd_net,
                'win': exit_reason == "TP"
            }

        return None

    def run_backtest(self) -> pd.DataFrame:
        """Exécute le backtest complet"""
        logger.info("\n" + "=" * 80)
        logger.info("🚀 DÉMARRAGE BACKTEST")
        logger.info("=" * 80)

        # Charger tous les snapshots par symbole
        all_snapshots_by_symbol = {}
        for symbol in self.symbols:
            snapshots = self.load_all_snapshots(symbol)
            if snapshots:
                all_snapshots_by_symbol[symbol] = snapshots

        if not all_snapshots_by_symbol:
            logger.error("❌ Aucune donnée chargée !")
            return pd.DataFrame()

        # Fusionner et trier tous les snapshots par timestamp
        all_snapshots = []
        for symbol, snapshots in all_snapshots_by_symbol.items():
            for snapshot in snapshots:
                snapshot['_symbol'] = symbol  # Ajouter symbole
                all_snapshots.append(snapshot)

        # Trier par timestamp
        all_snapshots.sort(key=lambda x: x.get('t_ms', 0))

        logger.info(f"\n📊 Total snapshots à traiter: {len(all_snapshots):,}")

        # Traiter chaque snapshot chronologiquement
        processed = 0
        for snapshot in all_snapshots:
            symbol = snapshot['_symbol']
            processed += 1

            if processed % 1000 == 0:
                logger.info(f"   Traité: {processed:,}/{len(all_snapshots):,} snapshots")

            # Extraire données prix
            price_data = self.extract_price_data(snapshot, symbol)

            # Vérifier sorties des positions ouvertes
            positions_to_close = []
            for pos_id, trade in self.open_positions.items():
                if trade['symbol'] == symbol:
                    exit_result = self.check_trade_exit(trade, price_data, symbol)
                    if exit_result:
                        # Fermer position
                        final_trade = {
                            **trade,
                            **exit_result,
                            'exit_timestamp': snapshot.get('t_ms', 0),
                            'exit_snapshot': snapshot
                        }
                        self.all_trades.append(final_trade)
                        positions_to_close.append(pos_id)

            # Fermer positions
            for pos_id in positions_to_close:
                del self.open_positions[pos_id]

            # Générer nouveau signal
            try:
                signal = self.strategy.generate_signal(snapshot, symbol)

                if signal and signal.get('action') in ['LONG', 'SHORT']:
                    # Créer nouveau trade
                    position_id = f"{symbol}_{snapshot.get('t_ms', processed)}"

                    trade = {
                        'position_id': position_id,
                        'symbol': symbol,
                        'action': signal['action'],
                        'entry': signal['entry'],
                        'stop': signal['stop'],
                        'targets': signal['targets'],
                        'entry_timestamp': snapshot.get('t_ms', 0),
                        'entry_snapshot': snapshot,
                        'confidence': signal.get('confidence', 0),
                        'metadata': signal.get('metadata', {})
                    }

                    self.open_positions[position_id] = trade

                    logger.debug(
                        f"🔵 {symbol} {signal['action']} @ {signal['entry']:.2f} "
                        f"(conf: {signal.get('confidence', 0):.2f})"
                    )

            except Exception as e:
                logger.warning(f"⚠️ Erreur génération signal {symbol}: {e}")
                continue

        # Fermer positions restantes à la fin
        logger.info("\n📊 Fermeture positions restantes...")
        for pos_id, trade in self.open_positions.items():
            # Utiliser dernier snapshot pour exit
            last_snapshot = all_snapshots[-1] if all_snapshots else None
            if last_snapshot:
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

        logger.info(f"✅ Backtest terminé: {len(self.all_trades)} trades")

        return pd.DataFrame(self.all_trades)

    def analyze_results(self, df: pd.DataFrame) -> Dict:
        """Analyse les résultats du backtest"""
        if df.empty:
            return {}

        logger.info("\n" + "=" * 80)
        logger.info("📊 ANALYSE RÉSULTATS")
        logger.info("=" * 80)

        # Métriques globales
        total_trades = len(df)
        wins = df['win'].sum()
        losses = total_trades - wins
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0

        # P&L
        total_pnl_ticks = df['pnl_ticks'].sum()
        total_pnl_usd = df['pnl_usd'].sum()

        avg_win_ticks = df[df['win']]['pnl_ticks'].mean() if wins > 0 else 0
        avg_loss_ticks = df[~df['win']]['pnl_ticks'].mean() if losses > 0 else 0

        # Par symbole
        results_by_symbol = {}
        for symbol in self.symbols:
            symbol_df = df[df['symbol'] == symbol]
            if len(symbol_df) > 0:
                symbol_wins = symbol_df['win'].sum()
                symbol_total = len(symbol_df)
                symbol_wr = (symbol_wins / symbol_total * 100) if symbol_total > 0 else 0
                symbol_pnl = symbol_df['pnl_ticks'].sum()

                results_by_symbol[symbol] = {
                    'trades': symbol_total,
                    'wins': symbol_wins,
                    'win_rate': symbol_wr,
                    'pnl_ticks': symbol_pnl,
                    'pnl_usd': symbol_pnl * self.tick_values[symbol]
                }

        # SL/TP intelligents
        smart_sl_count = df[df['metadata'].apply(lambda x: x.get('using_smart_sl', False) if isinstance(x, dict) else False)].shape[0]
        smart_sl_pct = (smart_sl_count / total_trades * 100) if total_trades > 0 else 0

        # Résultats
        results = {
            'total_trades': total_trades,
            'wins': wins,
            'losses': losses,
            'win_rate': win_rate,
            'total_pnl_ticks': total_pnl_ticks,
            'total_pnl_usd': total_pnl_usd,
            'avg_win_ticks': avg_win_ticks,
            'avg_loss_ticks': avg_loss_ticks,
            'expectancy': (win_rate / 100 * avg_win_ticks) + ((100 - win_rate) / 100 * avg_loss_ticks),
            'results_by_symbol': results_by_symbol,
            'smart_sl_usage': {
                'count': smart_sl_count,
                'percentage': smart_sl_pct
            }
        }

        # Logs
        logger.info(f"\n📈 MÉTRIQUES GLOBALES:")
        logger.info(f"   Trades: {total_trades}")
        logger.info(f"   Wins: {wins} | Losses: {losses}")
        logger.info(f"   Win Rate: {win_rate:.1f}%")
        logger.info(f"   P&L Total: {total_pnl_ticks:.1f} ticks (${total_pnl_usd:.2f})")
        logger.info(f"   Avg Win: {avg_win_ticks:.1f}t | Avg Loss: {avg_loss_ticks:.1f}t")
        logger.info(f"   Expectancy: {results['expectancy']:.2f} ticks/trade")

        logger.info(f"\n📊 PAR SYMBOLE:")
        for symbol, stats in results_by_symbol.items():
            logger.info(
                f"   {symbol}: {stats['trades']} trades | "
                f"WR: {stats['win_rate']:.1f}% | "
                f"P&L: {stats['pnl_ticks']:.1f}t (${stats['pnl_usd']:.2f})"
            )

        logger.info(f"\n🎯 SL INTELLIGENTS:")
        logger.info(f"   Utilisation: {smart_sl_count}/{total_trades} ({smart_sl_pct:.1f}%)")

        return results

    def save_results(self, df: pd.DataFrame, results: Dict):
        """Sauvegarde les résultats"""
        output_dir = Path("backtests/results")
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # CSV trades
        csv_file = output_dir / f"backtest_trades_{timestamp}.csv"
        df.to_csv(csv_file, index=False)
        logger.info(f"\n💾 Résultats sauvegardés: {csv_file}")

        # JSON résultats
        json_file = output_dir / f"backtest_results_{timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        logger.info(f"💾 Résultats JSON: {json_file}")


def main():
    """Point d'entrée principal"""
    logger.info("\n" + "=" * 80)
    logger.info("🎯 BACKTEST COMPLET STRATÉGIE ML_3LAYER - DONNÉES RÉELLES")
    logger.info("=" * 80)

    # Configuration
    backtester = BacktestCompletStrategieReelle(
        base_path="DATA_SIERRA_CHART/DATA_2025/NOVEMBRE",
        symbols=["ES", "NQ"],
        start_date="20251105",
        end_date="20251121"
    )

    # Exécuter backtest
    df = backtester.run_backtest()

    if df.empty:
        logger.error("❌ Aucun trade généré !")
        return

    # Analyser résultats
    results = backtester.analyze_results(df)

    # Sauvegarder
    backtester.save_results(df, results)

    logger.info("\n✅ BACKTEST TERMINÉ")


if __name__ == "__main__":
    main()
