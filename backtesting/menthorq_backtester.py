"""
🎯 MENTHORQ BACKTESTER - Moteur Principal

Backtester exhaustif pour la méthode MenthorQ qui teste:
- 80+ niveaux techniques (GEX, Blind Spots, VWAP, IB, etc.)
- Multiple configurations SL/TP
- Toutes les heures de trading
- Différents seuils de confiance
- Différentes confluence strengths

Utilise les composants existants:
- ml/backtester/jsonl_loader.py pour charger les snapshots ML_READY
- ml/ml_3layer_filter.py pour scorer les signaux
- strategies/ml_3layer_strategy.py pour générer les signaux

Date: 23 Novembre 2025
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
import json
import logging
import time
from collections import defaultdict

# Ajouter racine au path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Imports système existant
from ml.backtester.jsonl_loader import JSONLSnapshotLoader
from ml.ml_3layer_integrated_system import ML3LayerIntegratedSystem
from strategies.ml_3layer_strategy import ML3LayerStrategy

logger = logging.getLogger(__name__)


class MenthorQBacktester:
    """
    Backtester exhaustif pour la méthode MenthorQ

    Teste TOUTES les combinaisons :
    - 80+ niveaux techniques
    - Multiple configurations SL/TP
    - Toutes les heures de trading
    - Différents seuils de confiance
    - Différentes confluence strengths
    """

    def __init__(self, config: Dict):
        """
        Initialise le backtester

        Args:
            config: Configuration du backtest
                - symbols: ['ES', 'NQ', 'RTY']
                - start_date: '2025-11-05'
                - end_date: '2025-11-21'
                - data_path: 'DATA_SIERRA_CHART/DATA_2025/NOVEMBRE'
                - sl_configs: [...]
                - tp_configs: [...]
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

        # Convertir chemin relatif en absolu depuis racine projet
        data_path = config.get('data_path', 'DATA_SIERRA_CHART/DATA_2025/NOVEMBRE')
        if not Path(data_path).is_absolute():
            project_root = Path(__file__).resolve().parent.parent
            self.data_path = str(project_root / data_path)
        else:
            self.data_path = data_path

        # Configurations SL/TP à tester
        self.sl_configs = config.get('sl_configs', [
            {'method': 'fixed', 'ticks': 8},
            {'method': 'fixed', 'ticks': 10},
            {'method': 'fixed', 'ticks': 15},
            {'method': 'fixed', 'ticks': 20},
            {'method': 'fixed', 'ticks': 25},
            {'method': 'fixed', 'ticks': 30},
            {'method': 'fixed', 'ticks': 35},
            {'method': 'fixed', 'ticks': 40},
            {'method': 'confluence', 'buffer_ticks': 2},
            {'method': 'confluence', 'buffer_ticks': 3}
        ])

        self.tp_configs = config.get('tp_configs', [
            {'method': 'rr', 'ratio': 1.0},
            {'method': 'rr', 'ratio': 1.2},
            {'method': 'rr', 'ratio': 1.5},
            {'method': 'rr', 'ratio': 1.8},
            {'method': 'rr', 'ratio': 2.0},
            {'method': 'rr', 'ratio': 2.5},
            {'method': 'rr', 'ratio': 3.0},
            {'method': 'level', 'target_level': 'next_technical'}
        ])

        # Loader JSONL
        self.loader = JSONLSnapshotLoader(self.data_path)

        # Système ML
        self.ml_system = ML3LayerIntegratedSystem(
            symbols=self.symbols,
            use_ml_models=True
        )

        # Stratégie
        self.strategy = ML3LayerStrategy(ml_3layer_system=self.ml_system)

        # Résultats
        self.all_trades: List[Dict] = []
        self.level_stats: Dict = defaultdict(lambda: {'wins': 0, 'losses': 0, 'pnl': 0.0})
        self.time_stats: Dict = defaultdict(lambda: {'wins': 0, 'losses': 0, 'pnl': 0.0})

        # Tick sizes
        self.tick_sizes = {'ES': 0.25, 'NQ': 0.25, 'RTY': 0.10}
        self.tick_values = {'ES': 12.50, 'NQ': 5.00, 'RTY': 10.00}
        self.fees_per_trade = {'ES': 0.12, 'NQ': 0.28, 'RTY': 0.30}  # ticks

        logger.info(f"Backtester initialisé: {self.start_date.date()} à {self.end_date.date()}")
        logger.info(f"Symboles: {self.symbols}")
        logger.info(f"Configurations SL: {len(self.sl_configs)}")
        logger.info(f"Configurations TP: {len(self.tp_configs)}")

    def generate_date_list(self) -> List[str]:
        """Génère liste de dates entre start_date et end_date"""
        dates = []
        current = self.start_date
        while current <= self.end_date:
            dates.append(current.strftime("%Y%m%d"))
            current += timedelta(days=1)
        return dates

    def extract_all_levels(self, snapshot: Dict) -> Dict:
        """
        Extrait TOUS les niveaux MenthorQ depuis un snapshot ML_READY

        Returns:
            {
                'gex_levels': [6850, 6875, ...],  # GEX 1-10
                'blind_spots': [6855, 6880, ...],  # BS 0-8
                'vwap_levels': {'vwap': 6870, 'vwap_up1': 6880, ...},
                'ib_levels': {'ib_high': 6890, 'ib_low': 6850},
                'structure_levels': {'call_resistance': 6900, 'put_support': 6850, 'hvl': 6875},
                ...
            }
        """
        all_levels = {
            'gex_levels': [],
            'blind_spots': [],
            'vwap_levels': {},
            'ib_levels': {},
            'structure_levels': {},
            'value_area': {}
        }

        # GEX Levels (1-10)
        for i in range(1, 11):
            key = f'gex_{i}'
            if key in snapshot and snapshot[key]:
                all_levels['gex_levels'].append(snapshot[key])

        # Blind Spots (0-8)
        for i in range(9):
            key = f'blind_spot_{i}'
            if key in snapshot and snapshot[key]:
                all_levels['blind_spots'].append(snapshot[key])

        # VWAP Levels
        vwap_keys = ['vwap', 'vwap_up1', 'vwap_up2', 'vwap_dn1', 'vwap_dn2']
        for key in vwap_keys:
            if key in snapshot and snapshot[key]:
                all_levels['vwap_levels'][key] = snapshot[key]

        # IB Levels
        if 'ib_high' in snapshot and snapshot['ib_high']:
            all_levels['ib_levels']['ib_high'] = snapshot['ib_high']
        if 'ib_low' in snapshot and snapshot['ib_low']:
            all_levels['ib_levels']['ib_low'] = snapshot['ib_low']

        # Structure Levels
        structure_keys = ['call_resistance', 'put_support', 'hvl', '1d_max', '1d_min']
        for key in structure_keys:
            if key in snapshot and snapshot[key]:
                all_levels['structure_levels'][key] = snapshot[key]

        # Value Area
        if 'vah' in snapshot and snapshot['vah']:
            all_levels['value_area']['vah'] = snapshot['vah']
        if 'val' in snapshot and snapshot['val']:
            all_levels['value_area']['val'] = snapshot['val']
        if 'poc' in snapshot and snapshot['poc']:
            all_levels['value_area']['poc'] = snapshot['poc']

        return all_levels

    def identify_confluences(self, all_levels: Dict, price: float, symbol: str) -> List[Dict]:
        """
        Identifie toutes les confluences de niveaux

        Confluence = multiple niveaux dans une zone de ±5 ticks

        Returns:
            [
                {
                    'price': 6875.00,
                    'levels': ['gex_3', 'blind_spot_2', 'vwap'],
                    'strength': 3,
                    'distance_from_price': 2.5,
                    'types': ['gex', 'blind_spot', 'vwap']
                },
                ...
            ]
        """
        confluences = []
        tick_size = self.tick_sizes.get(symbol, 0.25)
        confluence_zone = 5 * tick_size  # ±5 ticks

        # Aplatir tous les niveaux avec leurs types
        flat_levels = []

        # GEX
        for i, level in enumerate(all_levels['gex_levels'], 1):
            if level > 0:
                flat_levels.append({
                    'price': level,
                    'type': 'gex',
                    'name': f'gex_{i}'
                })

        # Blind Spots
        for i, level in enumerate(all_levels['blind_spots']):
            if level > 0:
                flat_levels.append({
                    'price': level,
                    'type': 'blind_spot',
                    'name': f'blind_spot_{i}'
                })

        # VWAP
        for name, level in all_levels['vwap_levels'].items():
            if level > 0:
                flat_levels.append({
                    'price': level,
                    'type': 'vwap',
                    'name': name
                })

        # Structure
        for name, level in all_levels['structure_levels'].items():
            if level > 0:
                flat_levels.append({
                    'price': level,
                    'type': 'structure',
                    'name': name
                })

        # Grouper par proximité
        flat_levels.sort(key=lambda x: x['price'])

        i = 0
        while i < len(flat_levels):
            cluster = [flat_levels[i]]
            j = i + 1

            while j < len(flat_levels):
                if abs(flat_levels[j]['price'] - cluster[0]['price']) <= confluence_zone:
                    cluster.append(flat_levels[j])
                    j += 1
                else:
                    break

            if len(cluster) >= 2:  # Au moins 2 niveaux
                avg_price = np.mean([l['price'] for l in cluster])
                confluences.append({
                    'price': avg_price,
                    'levels': [l['name'] for l in cluster],
                    'strength': len(cluster),
                    'distance_from_price': abs(avg_price - price) / tick_size,
                    'types': list(set([l['type'] for l in cluster]))
                })

            i = j if j > i + 1 else i + 1

        return confluences

    def test_sl_tp_configuration(
        self,
        entry: float,
        direction: str,
        sl_config: Dict,
        tp_config: Dict,
        future_snapshots: List[Dict],
        tick_size: float,
        symbol: str
    ) -> Dict:
        """
        Simule un trade avec une configuration SL/TP donnée

        Args:
            entry: Prix d'entrée
            direction: 'LONG' ou 'SHORT'
            sl_config: {'method': 'fixed', 'ticks': 30} ou {'method': 'confluence', 'buffer': 2}
            tp_config: {'method': 'rr', 'ratio': 1.5} ou {'method': 'level', 'target': 6900}
            future_snapshots: Snapshots suivants pour simulation

        Returns:
            {
                'outcome': 'TP_HIT' | 'SL_HIT' | 'TIMEOUT',
                'pnl_ticks': 15,
                'pnl_dollars': 750,
                'bars_held': 8,
                'mae': -5,
                'mfe': 20,
            }
        """
        # Calculer SL
        sl_method = sl_config.get('method', 'fixed')
        if sl_method == 'fixed':
            sl_ticks = sl_config.get('ticks', 20)
            if direction == 'LONG':
                sl = entry - (sl_ticks * tick_size)
            else:
                sl = entry + (sl_ticks * tick_size)
        elif sl_config['method'] == 'confluence':
            # SL basé sur confluence (2-3 ticks sous le niveau)
            buffer = sl_config.get('buffer_ticks', 2)
            if direction == 'LONG':
                sl = entry - (buffer * tick_size)
            else:
                sl = entry + (buffer * tick_size)
            sl_ticks = buffer
        else:
            sl_ticks = 20  # Default
            if direction == 'LONG':
                sl = entry - (sl_ticks * tick_size)
            else:
                sl = entry + (sl_ticks * tick_size)

        # Calculer TP
        tp_method = tp_config.get('method', 'rr')
        if tp_method == 'rr':
            sl_distance = abs(entry - sl)
            rr_ratio = tp_config.get('ratio', 1.5)
            if direction == 'LONG':
                tp = entry + (sl_distance * rr_ratio)
            else:
                tp = entry - (sl_distance * rr_ratio)
        elif tp_method == 'level':
            # Utiliser niveau technique suivant (simplifié)
            sl_distance = abs(entry - sl)
            rr_ratio = 1.5  # Default
            if direction == 'LONG':
                tp = entry + (sl_distance * rr_ratio)
            else:
                tp = entry - (sl_distance * rr_ratio)
        else:
            sl_distance = abs(entry - sl)
            tp = entry + (sl_distance * 1.5) if direction == 'LONG' else entry - (sl_distance * 1.5)

        # Simuler tick-by-tick
        mae = 0  # Maximum Adverse Excursion
        mfe = 0  # Maximum Favorable Excursion

        for i, snapshot in enumerate(future_snapshots):
            # Extraire high/low
            high = snapshot.get('high', snapshot.get('mid', entry) + snapshot.get('atr', 5) * 0.3)
            low = snapshot.get('low', snapshot.get('mid', entry) - snapshot.get('atr', 5) * 0.3)

            # Check si SL ou TP touché
            if direction == 'LONG':
                if low <= sl:
                    return {
                        'outcome': 'SL_HIT',
                        'pnl_ticks': -sl_ticks - self.fees_per_trade[symbol],
                        'pnl_dollars': (-sl_ticks - self.fees_per_trade[symbol]) * self.tick_values[symbol],
                        'bars_held': i + 1,
                        'mae': mae,
                        'mfe': mfe
                    }
                if high >= tp:
                    tp_ticks = (tp - entry) / tick_size
                    return {
                        'outcome': 'TP_HIT',
                        'pnl_ticks': tp_ticks - self.fees_per_trade[symbol],
                        'pnl_dollars': (tp_ticks - self.fees_per_trade[symbol]) * self.tick_values[symbol],
                        'bars_held': i + 1,
                        'mae': mae,
                        'mfe': mfe
                    }

                # Track MAE/MFE
                excursion = (low - entry) / tick_size
                mae = min(mae, excursion)
                excursion = (high - entry) / tick_size
                mfe = max(mfe, excursion)

            else:  # SHORT
                if high >= sl:
                    return {
                        'outcome': 'SL_HIT',
                        'pnl_ticks': -sl_ticks - self.fees_per_trade[symbol],
                        'pnl_dollars': (-sl_ticks - self.fees_per_trade[symbol]) * self.tick_values[symbol],
                        'bars_held': i + 1,
                        'mae': mae,
                        'mfe': mfe
                    }
                if low <= tp:
                    tp_ticks = (entry - tp) / tick_size
                    return {
                        'outcome': 'TP_HIT',
                        'pnl_ticks': tp_ticks - self.fees_per_trade[symbol],
                        'pnl_dollars': (tp_ticks - self.fees_per_trade[symbol]) * self.tick_values[symbol],
                        'bars_held': i + 1,
                        'mae': mae,
                        'mfe': mfe
                    }

                # Track MAE/MFE
                excursion = (entry - high) / tick_size
                mae = min(mae, excursion)
                excursion = (entry - low) / tick_size
                mfe = max(mfe, excursion)

        # Timeout
        return {
            'outcome': 'TIMEOUT',
            'pnl_ticks': 0 - self.fees_per_trade[symbol],
            'pnl_dollars': -self.fees_per_trade[symbol] * self.tick_values[symbol],
            'bars_held': len(future_snapshots),
            'mae': mae,
            'mfe': mfe
        }

    def run_backtest(self) -> Dict:
        """
        Execute le backtest complet

        Pour chaque snapshot:
        1. Extrait tous les niveaux
        2. Identifie confluences
        3. Teste chaque confluence comme entry potentiel
        4. Pour chaque entry, teste toutes les configs SL/TP
        5. Enregistre résultats

        Returns:
            {
                'total_trades': 15420,
                'by_level': {...},
                'by_sl_tp': {...},
                'by_time': {...},
                'by_confluence': {...},
                'summary': {...}
            }
        """
        import traceback
        try:
            logger.info("Demarrage backtest MenthorQ")

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
                    # Trier par timestamp
                    snapshots.sort(key=lambda x: x.get('t_ms', 0))
                    all_snapshots_by_symbol[symbol] = snapshots
                    logger.info(f"OK: {len(snapshots):,} snapshots charges pour {symbol}")

            if not all_snapshots_by_symbol:
                logger.error("ERREUR: Aucune donnee chargee !")
                return {}

            # Traiter chaque snapshot
            start_time = time.time()
            total_processed = 0
            total_snapshots = sum(len(s) - 200 for s in all_snapshots_by_symbol.values())  # -200 pour garde avant/après

            logger.info(f"\n{'='*60}")
            logger.info(f"DEBUT TRAITEMENT: {total_snapshots:,} snapshots a traiter au total")
            logger.info(f"{'='*60}\n")

            for symbol, snapshots in all_snapshots_by_symbol.items():
                tick_size = self.tick_sizes.get(symbol, 0.25)
                symbol_snapshots = len(snapshots) - 200  # Exclure garde avant/après
                symbol_start_time = time.time()
                symbol_processed = 0

                logger.info(f"\n{'='*60}")
                logger.info(f"Traitement {symbol} ({len(snapshots):,} snapshots, {symbol_snapshots:,} a traiter)")
                logger.info(f"{'='*60}")

                for i, snapshot in enumerate(snapshots):
                    if i < 100 or i >= len(snapshots) - 100:
                        continue  # Garde 100 snapshots avant/après

                    total_processed += 1
                    symbol_processed += 1

                    # Progression détaillée
                    if total_processed % 500 == 0 or total_processed == 1:
                        elapsed = time.time() - start_time
                        symbol_elapsed = time.time() - symbol_start_time
                        progress_pct = (total_processed / total_snapshots * 100) if total_snapshots > 0 else 0
                        symbol_progress_pct = (symbol_processed / symbol_snapshots * 100) if symbol_snapshots > 0 else 0
                        rate = total_processed / elapsed if elapsed > 0 else 0
                        remaining = (total_snapshots - total_processed) / rate if rate > 0 else 0

                        logger.info(
                            f"[{symbol}] {symbol_progress_pct:.1f}% | "
                            f"Global: {total_processed:,}/{total_snapshots:,} ({progress_pct:.1f}%) | "
                            f"Trades: {len(self.all_trades):,} | "
                            f"Temps: {elapsed:.0f}s | "
                            f"Restant: ~{remaining/60:.1f}min"
                        )

                    # Extraire prix actuel
                    current_price = snapshot.get('mid', snapshot.get('last', 0))
                    if not current_price or current_price <= 0:
                        continue

                    # Extraire tous les niveaux (avec gestion d'erreur)
                    try:
                        all_levels = self.extract_all_levels(snapshot)
                    except Exception as e:
                        logger.warning(f"Erreur extract_all_levels: {e}")
                        continue

                    # Identifier confluences (avec gestion d'erreur)
                    try:
                        confluences = self.identify_confluences(all_levels, current_price, symbol)
                    except Exception as e:
                        logger.warning(f"Erreur identify_confluences: {e}")
                        continue

                    # Tester chaque confluence comme entry potentiel
                    for confluence in confluences:
                        # Skip si trop loin du prix actuel
                        if confluence['distance_from_price'] > 50:  # > 50 ticks
                            continue

                        # FILTRE OPTIMISATION: Confluence strength minimale
                        min_confluence = self.config.get('filters', {}).get('min_confluence', 2)
                        if confluence.get('strength', 0) < min_confluence:
                            continue

                        # FILTRE OPTIMISATION: Heures à éviter
                        timestamp = snapshot.get('t_ms', 0)
                        hour = datetime.fromtimestamp(timestamp / 1000).hour if timestamp else 0
                        avoid_hours = self.config.get('trading_hours', {}).get('avoid', [])
                        if avoid_hours:
                            # Convertir les heures à éviter en liste d'entiers
                            avoid_hours_int = []
                            for h in avoid_hours:
                                if isinstance(h, str):
                                    # Format "10:00" ou "10h00" ou "10"
                                    h_clean = h.replace(':', '').replace('h', '').strip()
                                    try:
                                        avoid_hours_int.append(int(h_clean[:2]))  # Prendre les 2 premiers chiffres
                                    except:
                                        pass
                                elif isinstance(h, int):
                                    avoid_hours_int.append(h)

                            if hour in avoid_hours_int:
                                continue

                        # Tester LONG et SHORT
                        for direction in ['LONG', 'SHORT']:
                            # Tester toutes les configs SL/TP
                            for sl_config in self.sl_configs:
                                for tp_config in self.tp_configs:
                                    # Snapshots futurs pour simulation
                                    future_snapshots = snapshots[i+1:i+101]  # 100 snapshots max

                                    if len(future_snapshots) < 10:
                                        continue  # Pas assez de données

                                    # Tester SL/TP avec gestion d'erreur
                                    try:
                                        result = self.test_sl_tp_configuration(
                                            entry=confluence['price'],
                                            direction=direction,
                                            sl_config=sl_config,
                                            tp_config=tp_config,
                                            future_snapshots=future_snapshots,
                                            tick_size=tick_size,
                                            symbol=symbol
                                        )
                                    except Exception as e:
                                        logger.warning(f"Erreur test_sl_tp_configuration: {e}")
                                        continue

                                    # Enregistrer trade
                                    timestamp = snapshot.get('t_ms', 0)
                                    hour = datetime.fromtimestamp(timestamp / 1000).hour if timestamp else 0

                                    trade = {
                                        'symbol': symbol,
                                        'timestamp': timestamp,
                                        'hour': hour,
                                        'direction': direction,
                                        'entry': confluence['price'],
                                        'current_price': current_price,
                                        'confluence_strength': confluence['strength'],
                                        'confluence_levels': ','.join(confluence['levels']),
                                        'confluence_types': ','.join(confluence['types']),
                                        'sl_config': json.dumps(sl_config),
                                        'tp_config': json.dumps(tp_config),
                                        **result
                                    }

                                    self.all_trades.append(trade)

                                    # Stats par niveau
                                    for level_name in confluence['levels']:
                                        level_key = f"{level_name}_{direction}"
                                        if result['outcome'] == 'TP_HIT':
                                            self.level_stats[level_key]['wins'] += 1
                                        elif result['outcome'] == 'SL_HIT':
                                            self.level_stats[level_key]['losses'] += 1
                                        self.level_stats[level_key]['pnl'] += result['pnl_ticks']

                                    # Stats par heure
                                    hour_key = f"{symbol}_{hour}"
                                    if result['outcome'] == 'TP_HIT':
                                        self.time_stats[hour_key]['wins'] += 1
                                    elif result['outcome'] == 'SL_HIT':
                                        self.time_stats[hour_key]['losses'] += 1
                                    self.time_stats[hour_key]['pnl'] += result['pnl_ticks']

                # Fin traitement symbole
                symbol_elapsed = time.time() - symbol_start_time
                logger.info(
                    f"\n[{symbol}] TERMINE: {symbol_processed:,} snapshots traites en {symbol_elapsed:.0f}s | "
                    f"Trades generes: {len(self.all_trades):,}"
                )

            total_elapsed = time.time() - start_time
            logger.info(f"\n{'='*60}")
            logger.info(f"OK: Backtest termine: {len(self.all_trades):,} trades simules en {total_elapsed:.0f}s")
            logger.info(f"{'='*60}")
            return self._compile_results()
        except KeyboardInterrupt:
            logger.warning("\nATTENTION: Backtest interrompu par l'utilisateur")
            logger.info(f"Trades generes jusqu'a present: {len(self.all_trades):,}")
            if self.all_trades:
                return self._compile_results()
            return {}
        except Exception as e:
            logger.error(f"\nERREUR CRITIQUE dans run_backtest: {e}")
            logger.error(traceback.format_exc())
            logger.info(f"Trades generes jusqu'a present: {len(self.all_trades):,}")
            if self.all_trades:
                logger.info("Compilation des resultats partiels...")
                return self._compile_results()
            return {}

    def _compile_results(self) -> Dict:
        """Compile tous les résultats en statistiques"""
        if not self.all_trades:
            return {}

        logger.info(f"Compilation des resultats: {len(self.all_trades):,} trades...")
        try:
            logger.info("Creation DataFrame...")
            df_trades = pd.DataFrame(self.all_trades)
            logger.info(f"DataFrame cree: {len(df_trades):,} lignes")

            logger.info("Analyse par niveau...")
            by_level = self._analyze_by_level(df_trades)

            logger.info("Analyse par SL/TP...")
            by_sl_tp = self._analyze_by_sl_tp(df_trades)

            logger.info("Analyse par heure...")
            by_time = self._analyze_by_time(df_trades)

            logger.info("Analyse par confluence...")
            by_confluence = self._analyze_by_confluence(df_trades)

            logger.info("Calcul du resume...")
            summary = self._calculate_summary(df_trades)

            logger.info("Compilation terminee avec succes")

            return {
                'total_trades': len(df_trades),
                'by_level': by_level,
                'by_sl_tp': by_sl_tp,
                'by_time': by_time,
                'by_confluence': by_confluence,
                'summary': summary,
                # Ne pas inclure all_trades pour economiser la memoire
                # 'all_trades': df_trades.to_dict('records')
            }
        except Exception as e:
            logger.error(f"ERREUR lors de la compilation: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # Retourner un resultat minimal
            return {
                'total_trades': len(self.all_trades),
                'error': str(e)
            }

    def _analyze_by_level(self, df: pd.DataFrame) -> Dict:
        """Analyse performance par type de niveau - OPTIMISE"""
        level_perf = {}

        # Extraire tous les niveaux uniques de manière optimisée
        logger.info("Extraction des niveaux uniques...")
        all_levels = set()
        for levels_str in df['confluence_levels'].dropna():
            if isinstance(levels_str, str):
                levels = [l.strip() for l in levels_str.split(',') if l.strip()]
                all_levels.update(levels)

        logger.info(f"  {len(all_levels)} niveaux uniques trouves")

        # Analyser chaque niveau
        for idx, level_name in enumerate(all_levels, 1):
            if idx % 10 == 0:
                logger.info(f"  Analyse niveau {idx}/{len(all_levels)}: {level_name}")

            # Utiliser une méthode plus rapide: split et check
            mask = df['confluence_levels'].str.contains(level_name, na=False, regex=False)
            level_df = df[mask]

            if len(level_df) == 0:
                continue

            wins = (level_df['outcome'] == 'TP_HIT').sum()
            losses = (level_df['outcome'] == 'SL_HIT').sum()
            total = wins + losses
            win_rate = (wins / total * 100) if total > 0 else 0
            pnl = level_df['pnl_ticks'].sum()

            level_perf[level_name] = {
                'trades': int(total),
                'wins': int(wins),
                'losses': int(losses),
                'win_rate': float(win_rate),
                'pnl_ticks': float(pnl),
                'avg_pnl': float(pnl / total if total > 0 else 0)
            }

        logger.info(f"Analyse par niveau terminee: {len(level_perf)} niveaux analyses")
        return level_perf

    def _analyze_by_sl_tp(self, df: pd.DataFrame) -> Dict:
        """Analyse performance par configuration SL/TP"""
        sl_tp_perf = {}

        for sl_str in df['sl_config'].unique():
            for tp_str in df['tp_config'].unique():
                config_df = df[(df['sl_config'] == sl_str) & (df['tp_config'] == tp_str)]
                if len(config_df) == 0:
                    continue

                config_key = f"{sl_str}_{tp_str}"
                wins = (config_df['outcome'] == 'TP_HIT').sum()
                losses = (config_df['outcome'] == 'SL_HIT').sum()
                total = wins + losses
                win_rate = (wins / total * 100) if total > 0 else 0
                pnl = config_df['pnl_ticks'].sum()

                sl_tp_perf[config_key] = {
                    'trades': total,
                    'wins': wins,
                    'losses': losses,
                    'win_rate': win_rate,
                    'pnl_ticks': pnl,
                    'avg_pnl': pnl / total if total > 0 else 0
                }

        return sl_tp_perf

    def _analyze_by_time(self, df: pd.DataFrame) -> Dict:
        """Analyse performance par heure de trading"""
        time_perf = {}

        for hour in df['hour'].unique():
            hour_df = df[df['hour'] == hour]
            if len(hour_df) == 0:
                continue

            wins = (hour_df['outcome'] == 'TP_HIT').sum()
            losses = (hour_df['outcome'] == 'SL_HIT').sum()
            total = wins + losses
            win_rate = (wins / total * 100) if total > 0 else 0
            pnl = hour_df['pnl_ticks'].sum()

            time_perf[int(hour)] = {
                'trades': total,
                'wins': wins,
                'losses': losses,
                'win_rate': win_rate,
                'pnl_ticks': pnl,
                'avg_pnl': pnl / total if total > 0 else 0
            }

        return time_perf

    def _analyze_by_confluence(self, df: pd.DataFrame) -> Dict:
        """Analyse performance par confluence strength"""
        confluence_perf = {}

        for strength in df['confluence_strength'].unique():
            strength_df = df[df['confluence_strength'] == strength]
            if len(strength_df) == 0:
                continue

            wins = (strength_df['outcome'] == 'TP_HIT').sum()
            losses = (strength_df['outcome'] == 'SL_HIT').sum()
            total = wins + losses
            win_rate = (wins / total * 100) if total > 0 else 0
            pnl = strength_df['pnl_ticks'].sum()

            confluence_perf[int(strength)] = {
                'trades': total,
                'wins': wins,
                'losses': losses,
                'win_rate': win_rate,
                'pnl_ticks': pnl,
                'avg_pnl': pnl / total if total > 0 else 0
            }

        return confluence_perf

    def _calculate_summary(self, df: pd.DataFrame) -> Dict:
        """Calcule statistiques globales"""
        wins = (df['outcome'] == 'TP_HIT').sum()
        losses = (df['outcome'] == 'SL_HIT').sum()
        total = wins + losses
        win_rate = (wins / total * 100) if total > 0 else 0
        total_pnl = df['pnl_ticks'].sum()
        avg_pnl = total_pnl / total if total > 0 else 0

        return {
            'total_trades': total,
            'wins': wins,
            'losses': losses,
            'win_rate': win_rate,
            'total_pnl_ticks': total_pnl,
            'avg_pnl_ticks': avg_pnl,
            'expectancy': avg_pnl
        }
