"""
🏷️ TRADE LABELING - ML 3-Layer Strategy
Version: 1.0
Date: 15 novembre 2025

Simule des trades sur données historiques ML_READY et calcule:
- Entry/Exit points basés sur stratégie ML 3-Layer
- MAE (Maximum Adverse Excursion)
- MFE (Maximum Favorable Excursion)
- Durée du trade
- P&L final
- Quality Score (via quality_score_calculator.py)

Input: ml/data/ml_ready_aggregated.parquet
Output: ml/data/labeled_trades.parquet (dataset ML-ready)
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from datetime import datetime

# Ajouter le dossier parent au path pour imports
sys.path.append(str(Path(__file__).parent.parent))

from ml.quality_score_calculator import QualityScoreCalculator
from ml.feature_engineering_lightgbm import FeatureEngineer
from ml.menthorq_zone_transformer import MenthorQZoneTransformer

logger = logging.getLogger(__name__)


class TradeSimulator:
    """
    Simule des trades sur données historiques et calcule métriques.

    Usage:
        simulator = TradeSimulator()
        df_trades = simulator.simulate_trades(df_snapshots)
    """

    def __init__(self):
        """Initialise le simulateur."""

        # Calculateur Quality Score
        self.quality_calculator = QualityScoreCalculator()

        # Feature Engineer (pour ajouter features engineered)
        self.feature_engineer = FeatureEngineer()

        # 🎯 MenthorQ Zone Transformer (niveaux → zones de proximité)
        self.zone_transformer = MenthorQZoneTransformer(
            gex_zone_ticks=5,       # ±5 ticks autour GEX
            blind_zone_ticks=3,     # ±3 ticks autour blind spots
            hvl_zone_ticks=10,      # ±10 ticks autour HVL
            call_put_zone_ticks=20  # ±20 ticks autour call/put
        )

        # Seuils de confluence pour générer signaux (TRÈS assouplis pour ML training)
        self.MIN_CONFLUENCE = 0.05  # Minimum pour considérer un signal (vs 0.30)
        self.MIN_LAYER1 = 0.01      # Minimum Layer 1 (MenthorQ) (vs 0.05)

        # Configuration SL/TP par symbole (en ticks)
        self.SL_CONFIG = {
            'ES': {'min': 10, 'max': 25, 'default': 12},
            'NQ': {'min': 12, 'max': 30, 'default': 15},
            'RTY': {'min': 15, 'max': 35, 'default': 20}
        }

        self.TP_CONFIG = {
            'ES': {'tp1': 15, 'tp2': 30},
            'NQ': {'tp1': 18, 'tp2': 35},
            'RTY': {'tp1': 20, 'tp2': 40}
        }

        # Tick size
        self.TICK_SIZE = {
            'ES': 0.25,
            'NQ': 0.25,
            'RTY': 0.10
        }

        logger.info("✅ TradeSimulator initialisé")


    def _should_take_trade(self, snapshot: Dict) -> Tuple[bool, str, float]:
        """
        Détermine si un trade doit être pris selon les règles de la stratégie.

        Args:
            snapshot: Snapshot ML_READY

        Returns:
            (should_trade, direction, confidence)
        """

        # Extraction features clés
        confluence = snapshot.get('confluence_strength', 0)
        layer1_conf = snapshot.get('menthorq_proximity_strength', 0)
        delta = snapshot.get('delta', 0)
        cum_delta = snapshot.get('cum_delta_day', 0)
        d_vwap_ticks = snapshot.get('d_vwap_ticks', 0)

        # Validation seuils minimums
        if confluence < self.MIN_CONFLUENCE:
            return False, 'NONE', 0.0

        if layer1_conf < self.MIN_LAYER1:
            return False, 'NONE', 0.0

        # Détermination direction (simplifié et assoupli)
        bullish_score = 0
        bearish_score = 0

        # Delta (poids: 1)
        if delta > 100:  # Assouplir seuil
            bullish_score += 1
        elif delta < -100:
            bearish_score += 1

        # Cum Delta (poids: 1)
        if cum_delta > 500:  # Assouplir seuil
            bullish_score += 1
        elif cum_delta < -500:
            bearish_score += 1

        # VWAP (poids: 2)
        if d_vwap_ticks < -20:  # Oversold (assoupli)
            bullish_score += 2
        elif d_vwap_ticks > 20:  # Overbought (assoupli)
            bearish_score += 2

        # Décision (seuil abaissé)
        if bullish_score >= bearish_score and bullish_score >= 1:  # Seuil 1 (vs 2)
            return True, 'LONG', confluence
        elif bearish_score > bullish_score and bearish_score >= 1:  # Seuil 1 (vs 2)
            return True, 'SHORT', confluence
        else:
            return False, 'NONE', 0.0


    def _simulate_trade_outcome(
        self,
        entry_idx: int,
        df_snapshots: pd.DataFrame,
        direction: str,
        entry_price: float,
        sl_ticks: int,
        tp_ticks: int,
        symbol: str
    ) -> Dict:
        """
        Simule l'évolution d'un trade et calcule MAE/MFE/outcome.

        Args:
            entry_idx: Index d'entrée dans df_snapshots
            df_snapshots: DataFrame des snapshots
            direction: 'LONG' ou 'SHORT'
            entry_price: Prix d'entrée
            sl_ticks: Stop Loss en ticks
            tp_ticks: Take Profit en ticks
            symbol: Symbole tradé

        Returns:
            Dict avec résultat du trade
        """

        tick_size = self.TICK_SIZE.get(symbol, 0.25)

        # Calcul niveaux SL/TP
        if direction == 'LONG':
            stop_price = entry_price - (sl_ticks * tick_size)
            target_price = entry_price + (tp_ticks * tick_size)
        else:  # SHORT
            stop_price = entry_price + (sl_ticks * tick_size)
            target_price = entry_price - (tp_ticks * tick_size)

        # Tracking MAE/MFE
        mae = 0.0  # Maximum Adverse Excursion (pire drawdown)
        mfe = 0.0  # Maximum Favorable Excursion (meilleur profit)

        # Simulation bar-by-bar
        max_bars = min(120, len(df_snapshots) - entry_idx)  # Max 2h (1min bars)

        for i in range(1, max_bars):
            current_idx = entry_idx + i
            if current_idx >= len(df_snapshots):
                break

            snapshot = df_snapshots.iloc[current_idx]
            current_price = snapshot.get('mid', entry_price)

            # Calcul P&L actuel
            if direction == 'LONG':
                pnl_current = current_price - entry_price
            else:  # SHORT
                pnl_current = entry_price - current_price

            # Update MAE (pire moment)
            if pnl_current < mae:
                mae = pnl_current

            # Update MFE (meilleur moment)
            if pnl_current > mfe:
                mfe = pnl_current

            # Check SL hit
            if direction == 'LONG' and current_price <= stop_price:
                return {
                    'exit_idx': current_idx,
                    'exit_price': stop_price,
                    'exit_reason': 'SL',
                    'pnl': stop_price - entry_price,
                    'pnl_ticks': (stop_price - entry_price) / tick_size,
                    'mae': mae,
                    'mfe': mfe,
                    'duration_bars': i,
                    'duration_minutes': i  # Assuming 1min bars
                }
            elif direction == 'SHORT' and current_price >= stop_price:
                return {
                    'exit_idx': current_idx,
                    'exit_price': stop_price,
                    'exit_reason': 'SL',
                    'pnl': entry_price - stop_price,
                    'pnl_ticks': (entry_price - stop_price) / tick_size,
                    'mae': mae,
                    'mfe': mfe,
                    'duration_bars': i,
                    'duration_minutes': i
                }

            # Check TP hit
            if direction == 'LONG' and current_price >= target_price:
                return {
                    'exit_idx': current_idx,
                    'exit_price': target_price,
                    'exit_reason': 'TP',
                    'pnl': target_price - entry_price,
                    'pnl_ticks': (target_price - entry_price) / tick_size,
                    'mae': mae,
                    'mfe': mfe,
                    'duration_bars': i,
                    'duration_minutes': i
                }
            elif direction == 'SHORT' and current_price <= target_price:
                return {
                    'exit_idx': current_idx,
                    'exit_price': target_price,
                    'exit_reason': 'TP',
                    'pnl': entry_price - target_price,
                    'pnl_ticks': (entry_price - target_price) / tick_size,
                    'mae': mae,
                    'mfe': mfe,
                    'duration_bars': i,
                    'duration_minutes': i
                }

        # Timeout (pas de SL/TP hit après 2h)
        final_price = df_snapshots.iloc[entry_idx + max_bars - 1].get('mid', entry_price)
        if direction == 'LONG':
            final_pnl = final_price - entry_price
        else:
            final_pnl = entry_price - final_price

        return {
            'exit_idx': entry_idx + max_bars - 1,
            'exit_price': final_price,
            'exit_reason': 'TIMEOUT',
            'pnl': final_pnl,
            'pnl_ticks': final_pnl / tick_size,
            'mae': mae,
            'mfe': mfe,
            'duration_bars': max_bars - 1,
            'duration_minutes': max_bars - 1
        }


    def simulate_trades(
        self,
        df_snapshots: pd.DataFrame,
        max_trades: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Simule des trades sur l'ensemble des snapshots.

        Args:
            df_snapshots: DataFrame des snapshots ML_READY
            max_trades: Nombre maximum de trades à simuler (None = illimité)

        Returns:
            DataFrame des trades simulés avec quality_score
        """

        logger.info(f"\n{'='*70}")
        logger.info(f"🎯 SIMULATION TRADES")
        logger.info(f"{'='*70}")
        logger.info(f"   Snapshots: {len(df_snapshots):,}")
        logger.info(f"   Max trades: {max_trades if max_trades else 'illimité'}")
        logger.info(f"{'='*70}\n")

        trades = []
        in_trade = False
        trade_count = 0

        # Grouper par symbole et date pour simulation séquentielle
        for symbol in df_snapshots['symbol_base'].unique():
            df_symbol = df_snapshots[df_snapshots['symbol_base'] == symbol].copy()
            df_symbol = df_symbol.sort_values('t_ms').reset_index(drop=True)

            logger.info(f"📊 Simulation {symbol}: {len(df_symbol):,} snapshots")

            i = 0
            while i < len(df_symbol):
                if max_trades and trade_count >= max_trades:
                    break

                if in_trade:
                    i += 1
                    continue

                snapshot = df_symbol.iloc[i].to_dict()

                # Vérifier si trade à prendre
                should_trade, direction, confidence = self._should_take_trade(snapshot)

                if should_trade:
                    # Configuration trade
                    entry_price = snapshot.get('mid', 0)
                    sl_config = self.SL_CONFIG.get(symbol, self.SL_CONFIG['ES'])
                    tp_config = self.TP_CONFIG.get(symbol, self.TP_CONFIG['ES'])

                    sl_ticks = sl_config['default']
                    tp_ticks = tp_config['tp1']  # TP1 conservateur

                    # Simulation outcome
                    outcome = self._simulate_trade_outcome(
                        entry_idx=i,
                        df_snapshots=df_symbol,
                        direction=direction,
                        entry_price=entry_price,
                        sl_ticks=sl_ticks,
                        tp_ticks=tp_ticks,
                        symbol=symbol
                    )

                    # Construction trade avec TOUTES les features du snapshot
                    # ⚠️ IMPORTANT: pnl_ticks, mae, mfe, duration_minutes sont des RESULTATS,
                    #    pas des features disponibles AVANT le trade !
                    #    Ils serviront UNIQUEMENT pour calculer quality_score (target)

                    trade = {
                        # === METADATA TRADE (pas des features) ===
                        'trade_id': f"{symbol}_{snapshot.get('date')}_{i}",
                        'symbol': symbol,
                        'date': snapshot.get('date'),
                        'entry_time': snapshot.get('t_ms'),
                        'entry_idx': i,
                        'exit_idx': outcome['exit_idx'],
                        'direction': direction,
                        'entry_price': entry_price,
                        'exit_price': outcome['exit_price'],
                        'stop': entry_price - (sl_ticks * self.TICK_SIZE[symbol]) if direction == 'LONG' else entry_price + (sl_ticks * self.TICK_SIZE[symbol]),
                        'target': entry_price + (tp_ticks * self.TICK_SIZE[symbol]) if direction == 'LONG' else entry_price - (tp_ticks * self.TICK_SIZE[symbol]),
                        'exit_reason': outcome['exit_reason'],

                        # === RESULTATS TRADE (pour quality_score UNIQUEMENT, PAS features) ===
                        'pnl': outcome['pnl'],
                        'pnl_ticks': outcome['pnl_ticks'],
                        'mae': outcome['mae'],
                        'mfe': outcome['mfe'],
                        'duration_minutes': outcome['duration_minutes'],

                        # === FEATURES STRATEGIE (disponibles AVANT le trade) ===
                        'confluence': confidence,
                        'layer1_confidence': snapshot.get('menthorq_proximity_strength', confidence * 0.6),
                        'ml_confidence': confidence,
                    }

                    # === AJOUTER TOUTES LES FEATURES DU SNAPSHOT (disponibles AVANT le trade) ===
                    # On copie toutes les colonnes du snapshot sauf celles déjà ajoutées
                    exclude_cols = ['trade_id', 'symbol', 'date', 'entry_time', 't_ms', 'entry_idx',
                                   'exit_idx', 'direction', 'entry_price', 'exit_price', 'stop',
                                   'target', 'exit_reason', 'pnl', 'pnl_ticks', 'mae', 'mfe',
                                   'duration_minutes', 'confluence', 'layer1_confidence', 'ml_confidence',
                                   'symbol_base', 'source_file']  # Déjà dans trade ou métadonnées

                    for col, value in snapshot.items():
                        if col not in exclude_cols:
                            trade[col] = value

                    # === CALCULER depth_bid et depth_ask si manquantes ===
                    # (nécessaires pour feature engineering mais pas dans tous les snapshots)
                    if 'depth_bid' not in trade:
                        trade['depth_bid'] = snapshot.get('bidvol', 0) * 10  # Estimation
                    if 'depth_ask' not in trade:
                        trade['depth_ask'] = snapshot.get('askvol', 0) * 10  # Estimation

                    trades.append(trade)
                    trade_count += 1

                    # Skip bars jusqu'à exit
                    i = outcome['exit_idx'] + 1
                    in_trade = False

                    if trade_count % 100 == 0:
                        logger.info(f"   ✅ {trade_count} trades simulés...")
                else:
                    i += 1

        logger.info(f"\n✅ Simulation terminée: {len(trades)} trades générés\n")

        if not trades:
            logger.warning("⚠️ Aucun trade généré !")
            return pd.DataFrame()

        df_trades = pd.DataFrame(trades)

        # === SAUVEGARDER les colonnes de RÉSULTATS TRADE avant feature engineering ===
        # (car feature engineering ne retourne que les features ML, pas les résultats)
        trade_result_cols = ['trade_id', 'symbol', 'date', 'entry_time', 'entry_idx',
                            'exit_idx', 'direction', 'entry_price', 'exit_price',
                            'stop', 'target', 'exit_reason',
                            'pnl', 'pnl_ticks', 'mae', 'mfe', 'duration_minutes',
                            'confluence', 'layer1_confidence', 'ml_confidence']
        df_trade_results = df_trades[trade_result_cols].copy()

        # ═══════════════════════════════════════════════════════════
        # APPLICATION FEATURE ENGINEERING (20 features additionnelles)
        # ═══════════════════════════════════════════════════════════

        logger.info("\n⚙️ Application Feature Engineering...")
        logger.info(f"   Features AVANT: {len(df_trades.columns)}")

        try:
            # Appliquer les features engineered (delta_intensity, depth_imbalance_ratio, etc.)
            df_features = self.feature_engineer.engineer_features(df_trades, include_meta=False)
            logger.info(f"   Features APRES: {len(df_features.columns)}")
            logger.info("   ✅ Feature Engineering appliqué avec succès !")

            # === MERGER features ML + résultats trade ===
            # Reset index pour merger proprement
            df_features = df_features.reset_index(drop=True)
            df_trade_results = df_trade_results.reset_index(drop=True)
            df_trades = pd.concat([df_trade_results, df_features], axis=1)
            logger.info(f"   ✅ Colonnes finales: {len(df_trades.columns)}")

        except Exception as e:
            logger.warning(f"   ⚠️ Erreur Feature Engineering: {e}")
            logger.warning("   → Continuons sans features engineered (modèle moins performant)")

        # ═══════════════════════════════════════════════════════════
        # TRANSFORMATION ZONES MENTHORQ (niveaux → zones proximité)
        # ═══════════════════════════════════════════════════════════

        logger.info("🎯 Transformation niveaux MenthorQ → ZONES de proximité...")

        try:
            # Appliquer transformation zones MenthorQ
            df_trades = self.zone_transformer.transform_all(df_trades)

            zone_features = self.zone_transformer.get_zone_features()
            logger.info(f"   ✅ {len(zone_features)} features zones MenthorQ créées:")

            # Log des features créées
            for feat in zone_features:
                if feat in df_trades.columns:
                    non_zero = (df_trades[feat] != 0).sum()
                    logger.info(f"      - {feat:30s} (non-zero: {non_zero:,} / {len(df_trades):,})")

        except Exception as e:
            logger.warning(f"   ⚠️ Erreur transformation zones: {e}")
            logger.warning("   → Continuons sans zones MenthorQ")

        # ═══════════════════════════════════════════════════════════
        # CALCUL TARGET BINAIRE WIN/LOSS (CLASSIFICATION)
        # ═══════════════════════════════════════════════════════════

        logger.info("🎯 Calcul target binaire WIN/LOSS pour classification...")

        # Target simple : WIN = 1 si pnl_ticks > 0, sinon LOSS = 0
        df_trades['win'] = (df_trades['pnl_ticks'] > 0).astype(int)

        # Statistiques
        wins = df_trades[df_trades['win'] == 1]
        losses = df_trades[df_trades['win'] == 0]

        logger.info(f"✅ Target binaire calculée")
        logger.info(f"   WINs:   {len(wins):,} ({len(wins)/len(df_trades)*100:.1f}%)")
        logger.info(f"   LOSSes: {len(losses):,} ({len(losses)/len(df_trades)*100:.1f}%)")
        logger.info(f"   P&L WIN moyen:  {wins['pnl_ticks'].mean():+.2f} ticks")
        logger.info(f"   P&L LOSS moyen: {losses['pnl_ticks'].mean():+.2f} ticks")

        # Statistiques finales
        wins = df_trades[df_trades['pnl_ticks'] > 0]
        losses = df_trades[df_trades['pnl_ticks'] <= 0]

        logger.info(f"\n{'='*70}")
        logger.info(f"📊 STATISTIQUES TRADES SIMULÉS")
        logger.info(f"{'='*70}")
        logger.info(f"   Total trades: {len(df_trades)}")
        logger.info(f"   Wins: {len(wins)} ({len(wins)/len(df_trades)*100:.1f}%)")
        logger.info(f"   Losses: {len(losses)} ({len(losses)/len(df_trades)*100:.1f}%)")
        logger.info(f"   P&L moyen: {df_trades['pnl_ticks'].mean():+.2f} ticks")
        logger.info(f"   P&L total: {df_trades['pnl_ticks'].sum():+.1f} ticks")
        logger.info(f"   Durée moyenne: {df_trades['duration_minutes'].mean():.1f} min")
        logger.info(f"{'='*70}\n")

        return df_trades


# ═══════════════════════════════════════════════════════════════
# SCRIPT PRINCIPAL
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    """Labeling des trades sur données historiques."""

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    # ═══════════════════════════════════════════════════════════
    # CHARGEMENT DONNÉES ML_READY
    # ═══════════════════════════════════════════════════════════

    INPUT_PATH = "ml/data/ml_ready_aggregated.parquet"
    OUTPUT_PATH = "ml/data/labeled_trades.parquet"

    logger.info(f"📂 Chargement données: {INPUT_PATH}")

    if not Path(INPUT_PATH).exists():
        logger.error(f"❌ Fichier non trouvé: {INPUT_PATH}")
        logger.error("   Exécutez d'abord: python ml/extract_ml_ready_data.py")
        exit(1)

    df_snapshots = pd.read_parquet(INPUT_PATH)
    logger.info(f"✅ {len(df_snapshots):,} snapshots chargés\n")

    # ═══════════════════════════════════════════════════════════
    # SIMULATION TRADES
    # ═══════════════════════════════════════════════════════════

    simulator = TradeSimulator()

    df_trades = simulator.simulate_trades(
        df_snapshots=df_snapshots,
        max_trades=None  # Illimité
    )

    if df_trades.empty:
        logger.error("❌ Aucun trade simulé !")
        exit(1)

    # ═══════════════════════════════════════════════════════════
    # SAUVEGARDE
    # ═══════════════════════════════════════════════════════════

    output_file = Path(OUTPUT_PATH)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    df_trades.to_parquet(OUTPUT_PATH, engine='pyarrow', compression='snappy', index=False)

    file_size = output_file.stat().st_size / (1024 * 1024)

    logger.info(f"💾 Trades labeled sauvegardés:")
    logger.info(f"   Fichier: {OUTPUT_PATH}")
    logger.info(f"   Taille: {file_size:.2f} MB")
    logger.info(f"   Trades: {len(df_trades):,}")
    logger.info(f"   Features: {len(df_trades.columns)}")

    logger.info("\n✅ Labeling terminé avec succès !")
