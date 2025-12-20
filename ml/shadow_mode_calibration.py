#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
SHADOW MODE - CALIBRAGE SEUILS EN PRODUCTION
═══════════════════════════════════════════════════════════════════════════════

Teste TOUS les seuils en parallèle pendant 1 semaine
SANS bloquer les trades (shadow mode)

Permet comparaison directe sur mêmes conditions marché
4× plus rapide que A/B testing séquentiel

Usage:
    # Intégrer dans votre système de trading
    from ml.shadow_mode_calibration import ShadowModeCalibrator

    calibrator = ShadowModeCalibrator(
        thresholds_es=[0.56, 0.59, 0.62, 0.65],
        thresholds_nq=[0.62, 0.65, 0.68, 0.71]
    )

    # Pour chaque signal (SANS bloquer)
    ml_pred = ml_filter.predict(ml_ready_data)
    calibrator.log_all_thresholds(ml_pred, signal)

    # Exécuter trade normalement
    trade = execute_trade(signal)

    # Update avec résultat
    calibrator.update_trade_result(trade.id, trade.result)

    # Après 1 semaine
    calibrator.analyze_results()
    calibrator.export_report('ml/calibration/shadow_mode_report.md')

Auteur : MIA_IA_SYSTEM
Date : 2 Novembre 2025
═══════════════════════════════════════════════════════════════════════════════
"""

import json
import logging
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class ShadowDecision:
    """Décision shadow pour un seuil"""
    timestamp: float
    trade_id: str
    symbol: str
    strategy: str
    side: str
    threshold: float
    ml_direction: str
    ml_confidence: float
    accepted: bool
    trade_result: Optional[str] = None  # 'TP1', 'TP2', 'SL', etc.
    pnl_ticks: Optional[float] = None


class ShadowModeCalibrator:
    """
    Calibrateur en mode shadow

    Teste tous les seuils en parallèle SANS bloquer les trades

    Usage:
        calibrator = ShadowModeCalibrator(
            thresholds_es=[0.56, 0.59, 0.62, 0.65],
            thresholds_nq=[0.62, 0.65, 0.68, 0.71]
        )

        # Pour chaque signal
        calibrator.log_all_thresholds(ml_prediction, signal)

        # Exécuter trade normalement
        trade = execute_trade(signal)

        # Update résultat
        calibrator.update_trade_result(trade.id, trade.result, trade.pnl_ticks)

        # Après 1 semaine
        results = calibrator.analyze_results()
    """

    def __init__(
        self,
        thresholds_es: List[float],
        thresholds_nq: List[float],
        auto_save: bool = True,
        save_path: str = "ml/calibration/shadow_logs.jsonl"
    ):
        """
        Initialise le calibrateur shadow

        Args:
            thresholds_es: Liste seuils à tester pour ES
            thresholds_nq: Liste seuils à tester pour NQ
            auto_save: Sauvegarder automatiquement chaque log
            save_path: Chemin fichier sauvegarde
        """
        self.thresholds_es = sorted(thresholds_es)
        self.thresholds_nq = sorted(thresholds_nq)
        self.auto_save = auto_save
        self.save_path = Path(save_path)

        # Créer répertoire si nécessaire
        self.save_path.parent.mkdir(parents=True, exist_ok=True)

        # Logs shadow
        self.shadow_decisions: List[ShadowDecision] = []

        # Index pour retrouver trades
        self.trade_index: Dict[str, List[int]] = {}

        logger.info(f"\n{'='*70}")
        logger.info(f"🔍 SHADOW MODE CALIBRATOR INITIALISÉ")
        logger.info(f"{'='*70}")
        logger.info(f"   ES seuils : {self.thresholds_es}")
        logger.info(f"   NQ seuils : {self.thresholds_nq}")
        logger.info(f"   Auto-save : {'✅' if auto_save else '❌'}")
        logger.info(f"   Fichier   : {self.save_path}")
        logger.info(f"{'='*70}")

    def log_all_thresholds(
        self,
        ml_prediction,
        signal: dict,
        trade_id: Optional[str] = None
    ):
        """
        Log décision pour TOUS les seuils (ES ou NQ selon symbole)

        Args:
            ml_prediction: MLPrediction du modèle
            signal: Dict signal {'strategy', 'side', 'symbol', ...}
            trade_id: ID unique du trade (auto-généré si None)
        """
        if trade_id is None:
            trade_id = f"{signal['symbol']}_{int(time.time()*1000)}"

        # Déterminer symbole et seuils
        sym = signal.get('symbol', 'ES')
        thresholds = self.thresholds_nq if 'NQ' in sym.upper() else self.thresholds_es

        # Logger pour chaque seuil
        for threshold in thresholds:
            # Déterminer si accepté
            accepted = (
                ml_prediction.confidence >= threshold and
                ml_prediction.direction != 'FLAT' and
                (
                    (signal['side'] == 'LONG' and ml_prediction.direction == 'UP') or
                    (signal['side'] == 'SHORT' and ml_prediction.direction == 'DOWN')
                )
            )

            decision = ShadowDecision(
                timestamp=time.time(),
                trade_id=trade_id,
                symbol=sym,
                strategy=signal['strategy'],
                side=signal['side'],
                threshold=threshold,
                ml_direction=ml_prediction.direction,
                ml_confidence=ml_prediction.confidence,
                accepted=accepted,
                trade_result=None,
                pnl_ticks=None
            )

            self.shadow_decisions.append(decision)

            # Index
            if trade_id not in self.trade_index:
                self.trade_index[trade_id] = []
            self.trade_index[trade_id].append(len(self.shadow_decisions) - 1)

            # Auto-save
            if self.auto_save:
                self._save_decision(decision)

    def update_trade_result(
        self,
        trade_id: str,
        result: str,
        pnl_ticks: float
    ):
        """
        Met à jour le résultat d'un trade dans TOUS les logs de seuils

        Args:
            trade_id: ID du trade
            result: 'TP1', 'TP2', 'SL', etc.
            pnl_ticks: P&L en ticks
        """
        if trade_id not in self.trade_index:
            logger.warning(f"⚠️ Trade ID introuvable : {trade_id}")
            return

        # Update tous les logs de ce trade
        for idx in self.trade_index[trade_id]:
            self.shadow_decisions[idx].trade_result = result
            self.shadow_decisions[idx].pnl_ticks = pnl_ticks

    def _save_decision(self, decision: ShadowDecision):
        """Sauvegarde une décision dans le fichier JSONL"""
        with open(self.save_path, 'a') as f:
            f.write(json.dumps(asdict(decision)) + '\n')

    def load_from_file(self, file_path: Optional[str] = None):
        """
        Charge les logs depuis un fichier

        Args:
            file_path: Chemin fichier (utilise self.save_path si None)
        """
        path = Path(file_path) if file_path else self.save_path

        if not path.exists():
            logger.warning(f"⚠️ Fichier introuvable : {path}")
            return

        logger.info(f"📂 Chargement logs : {path}")

        self.shadow_decisions = []
        self.trade_index = {}

        with open(path, 'r') as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    decision = ShadowDecision(**data)
                    self.shadow_decisions.append(decision)

                    # Rebuild index
                    if decision.trade_id not in self.trade_index:
                        self.trade_index[decision.trade_id] = []
                    self.trade_index[decision.trade_id].append(len(self.shadow_decisions) - 1)

        logger.info(f"✅ {len(self.shadow_decisions)} décisions chargées")
        logger.info(f"✅ {len(self.trade_index)} trades uniques")

    def analyze_results(self) -> pd.DataFrame:
        """
        Analyse les résultats par seuil

        Returns:
            DataFrame avec métriques par seuil et symbole
        """
        logger.info(f"\n{'='*70}")
        logger.info(f"📊 ANALYSE RÉSULTATS SHADOW MODE")
        logger.info(f"{'='*70}")

        # Convertir en DataFrame
        df = pd.DataFrame([asdict(d) for d in self.shadow_decisions])

        # Filtrer seulement les décisions avec résultat
        df_completed = df[df['trade_result'].notna()].copy()

        logger.info(f"📈 Trades complétés : {len(df_completed)} / {len(df)}")

        if len(df_completed) == 0:
            logger.warning("⚠️ Aucun trade complété. Attendre résultats.")
            return pd.DataFrame()

        # Grouper par symbole et seuil
        results = []

        for sym in df_completed['symbol'].unique():
            df_sym = df_completed[df_completed['symbol'] == sym]

            for threshold in df_sym['threshold'].unique():
                df_th = df_sym[df_sym['threshold'] == threshold]

                # Filtrer trades acceptés
                df_accepted = df_th[df_th['accepted'] == True]

                if len(df_accepted) == 0:
                    continue

                # Métriques
                n_trades = len(df_accepted)
                n_wins = len(df_accepted[df_accepted['trade_result'].str.contains('TP', na=False)])
                n_losses = len(df_accepted[df_accepted['trade_result'].str.contains('SL', na=False)])

                win_rate = n_wins / n_trades if n_trades > 0 else 0

                # P&L
                total_pnl = df_accepted['pnl_ticks'].sum()
                avg_pnl = df_accepted['pnl_ticks'].mean()

                # Profit Factor
                wins_pnl = df_accepted[df_accepted['pnl_ticks'] > 0]['pnl_ticks'].sum()
                losses_pnl = abs(df_accepted[df_accepted['pnl_ticks'] < 0]['pnl_ticks'].sum())
                profit_factor = wins_pnl / losses_pnl if losses_pnl > 0 else float('inf')

                results.append({
                    'symbol': sym,
                    'threshold': threshold,
                    'n_trades': n_trades,
                    'n_wins': n_wins,
                    'n_losses': n_losses,
                    'win_rate': win_rate,
                    'total_pnl_ticks': total_pnl,
                    'avg_pnl_ticks': avg_pnl,
                    'profit_factor': profit_factor
                })

        df_results = pd.DataFrame(results)

        # Afficher résultats
        self._print_results(df_results)

        return df_results

    def _print_results(self, df_results: pd.DataFrame):
        """Affiche résultats formatés"""

        for sym in df_results['symbol'].unique():
            df_sym = df_results[df_results['symbol'] == sym].sort_values('threshold')

            logger.info(f"\n{'='*70}")
            logger.info(f"{'🔵 ES' if sym == 'ES' else '🟢 NQ'} - RÉSULTATS PAR SEUIL")
            logger.info(f"{'='*70}")

            # Trouver optimal
            best_pf = df_sym.loc[df_sym['profit_factor'].idxmax()]
            best_wr = df_sym.loc[df_sym['win_rate'].idxmax()]

            for _, row in df_sym.iterrows():
                is_best_pf = row['threshold'] == best_pf['threshold']
                is_best_wr = row['threshold'] == best_wr['threshold']

                marker = ''
                if is_best_pf and is_best_wr:
                    marker = ' ⭐⭐ OPTIMAL (PF + WR)'
                elif is_best_pf:
                    marker = ' ⭐ Meilleur PF'
                elif is_best_wr:
                    marker = ' 🎯 Meilleur WR'

                logger.info(f"\n🎯 Seuil {row['threshold']:.2f}{marker}")
                logger.info(f"   Trades       : {row['n_trades']:.0f}")
                logger.info(f"   Win Rate     : {row['win_rate']:.1%}")
                logger.info(f"   Profit Factor: {row['profit_factor']:.2f}")
                logger.info(f"   Total P&L    : {row['total_pnl_ticks']:+.0f} ticks")
                logger.info(f"   Avg P&L      : {row['avg_pnl_ticks']:+.1f} ticks/trade")

    def export_report(self, output_path: str = "ml/calibration/shadow_mode_report.md"):
        """
        Exporte rapport complet en Markdown

        Args:
            output_path: Chemin fichier sortie
        """
        df_results = self.analyze_results()

        if df_results.empty:
            logger.warning("⚠️ Pas de résultats à exporter")
            return

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# 📊 RAPPORT SHADOW MODE - CALIBRAGE SEUILS\n\n")
            f.write(f"**Date :** {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("---\n\n")

            for sym in df_results['symbol'].unique():
                df_sym = df_results[df_results['symbol'] == sym].sort_values('threshold')

                f.write(f"## {'🔵 ES (E-mini S&P 500)' if sym == 'ES' else '🟢 NQ (E-mini Nasdaq)'}\n\n")

                # Trouver optimal
                best_pf = df_sym.loc[df_sym['profit_factor'].idxmax()]
                best_wr = df_sym.loc[df_sym['win_rate'].idxmax()]

                f.write(f"**Seuil optimal :** {best_pf['threshold']:.2f} (Profit Factor max)\n\n")

                # Tableau
                f.write("| Seuil | Trades | Win Rate | PF | P&L Total | P&L Moyen |\n")
                f.write("|-------|--------|----------|----|-----------|-----------|\n")

                for _, row in df_sym.iterrows():
                    marker = ''
                    if row['threshold'] == best_pf['threshold']:
                        marker = ' ⭐'

                    f.write(
                        f"| {row['threshold']:.2f}{marker} | "
                        f"{row['n_trades']:.0f} | "
                        f"{row['win_rate']:.1%} | "
                        f"{row['profit_factor']:.2f} | "
                        f"{row['total_pnl_ticks']:+.0f} | "
                        f"{row['avg_pnl_ticks']:+.1f} |\n"
                    )

                f.write("\n")

            f.write("---\n\n")
            f.write("## 💡 RECOMMANDATIONS\n\n")

            # Recommandations par symbole
            for sym in df_results['symbol'].unique():
                df_sym = df_results[df_results['symbol'] == sym]
                best = df_sym.loc[df_sym['profit_factor'].idxmax()]

                f.write(f"**{sym} :**\n")
                f.write(f"- Seuil optimal : `{best['threshold']:.2f}`\n")
                f.write(f"- Profit Factor : `{best['profit_factor']:.2f}`\n")
                f.write(f"- Win Rate : `{best['win_rate']:.1%}`\n")
                f.write(f"- Trades/semaine : `{best['n_trades']:.0f}`\n")
                f.write("\n")

        logger.info(f"\n💾 Rapport exporté : {output_path}")

    def get_stats(self) -> Dict:
        """Retourne statistiques générales"""
        return {
            'n_decisions': len(self.shadow_decisions),
            'n_trades': len(self.trade_index),
            'n_completed': len([d for d in self.shadow_decisions if d.trade_result is not None]),
            'thresholds_es': self.thresholds_es,
            'thresholds_nq': self.thresholds_nq,
        }


# ═══════════════════════════════════════════════════════════════════════════
# EXEMPLE D'UTILISATION
# ═══════════════════════════════════════════════════════════════════════════

def example_usage():
    """Exemple d'intégration dans système de trading"""

    logger.info("\n🧪 EXEMPLE D'UTILISATION SHADOW MODE CALIBRATOR")

    # 1. Initialiser
    calibrator = ShadowModeCalibrator(
        thresholds_es=[0.56, 0.59, 0.62, 0.65],
        thresholds_nq=[0.62, 0.65, 0.68, 0.71],
        auto_save=True
    )

    # 2. Simuler quelques signaux
    from ml.ml_direction_filter import MLPrediction

    for i in range(10):
        # Prédiction ML
        ml_pred = MLPrediction(
            direction='UP',
            confidence=0.60 + i * 0.02,
            probabilities={'DOWN': 0.1, 'FLAT': 0.2, 'UP': 0.7},
            timestamp=time.time(),
            latency_ms=5.0
        )

        # Signal stratégie
        signal = {
            'strategy': 'hybrid_strategy',
            'side': 'LONG',
            'symbol': 'ES' if i % 2 == 0 else 'NQ'
        }

        trade_id = f"trade_{i}"

        # Log TOUS les seuils (shadow)
        calibrator.log_all_thresholds(ml_pred, signal, trade_id)

        # Simuler résultat trade
        result = 'TP1' if i % 3 != 0 else 'SL'
        pnl = 10.0 if result == 'TP1' else -5.0

        calibrator.update_trade_result(trade_id, result, pnl)

    # 3. Analyser
    logger.info("\n" + "="*70)
    results = calibrator.analyze_results()

    # 4. Exporter rapport
    calibrator.export_report('ml/calibration/shadow_mode_example_report.md')

    logger.info("\n✅ Exemple terminé")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    example_usage()



