"""
T4 vNext Strategy - Backtest
=============================

Objectif: Optimiser le bot T4 Baseline avec 3 modifications ciblées:
1. R:R minimum 2:1 (SL 10-12t / TP 20-25t)
2. Confluence minimum 0.50 (au lieu de 0.60)
3. Sizing adaptatif par paliers (0x / 0.5x / 1.0x / 1.5x)

Comparaison avec T4 Baseline (+0.30 t/trade) et MenthorQ Pure (-0.357 t/trade).

Auteur: MIA Trading System
Date: 15 Novembre 2025
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import logging

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class T4vNextConfig:
    """Configuration pour T4 vNext"""
    # R:R minimum
    min_rr_ratio: float = 2.0
    sl_min_ticks: int = 10
    sl_max_ticks: int = 12
    tp_min_ticks: int = 20
    tp_max_ticks: int = 25

    # Confluence
    min_confluence: float = 0.50

    # Sizing paliers
    size_skip_threshold: float = 0.50
    size_reduced_threshold: float = 0.60
    size_normal_threshold: float = 0.70
    size_reduced: float = 0.5
    size_normal: float = 1.0
    size_boosted: float = 1.5

    # Fees
    fees_per_trade: float = 0.62

    # ATR pour SL adaptatif
    use_atr_adaptive_sl: bool = True
    atr_threshold_ticks: int = 50


class T4vNextStrategy:
    """
    Stratégie T4 vNext - Version optimisée du bot actuel

    Améliorations:
    1. R:R minimum 2:1 strictement appliqué
    2. Confluence assouplie (0.50 au lieu de 0.60)
    3. Sizing adaptatif selon confluence
    """

    def __init__(self, config: T4vNextConfig = None):
        self.config = config or T4vNextConfig()

        logger.info("T4vNextStrategy initialisee")
        logger.info(f"  R:R min: {self.config.min_rr_ratio}:1")
        logger.info(f"  SL: {self.config.sl_min_ticks}-{self.config.sl_max_ticks}t")
        logger.info(f"  TP: {self.config.tp_min_ticks}-{self.config.tp_max_ticks}t")
        logger.info(f"  Confluence min: {self.config.min_confluence}")
        logger.info(f"  Sizing: 0x / {self.config.size_reduced}x / {self.config.size_normal}x / {self.config.size_boosted}x")

    def _calculate_sl(self, entry_price: float, direction: str, atr_ticks: float = None) -> Tuple[float, int]:
        """
        Calcule le SL optimal selon:
        - Direction
        - ATR si disponible (pour volatilité)
        - Contraintes min/max
        """
        sl_ticks = self.config.sl_min_ticks

        # Adapter selon ATR si haute volatilité
        if self.config.use_atr_adaptive_sl and atr_ticks and atr_ticks > self.config.atr_threshold_ticks:
            sl_ticks = self.config.sl_max_ticks

        # Conversion ticks → prix (1 tick ES = 0.25)
        tick_value = 0.25

        if direction == 'LONG':
            sl = entry_price - (sl_ticks * tick_value)
        else:  # SHORT
            sl = entry_price + (sl_ticks * tick_value)

        return sl, sl_ticks

    def _calculate_tp(self, entry_price: float, direction: str, sl_ticks: int) -> Tuple[float, int]:
        """
        Calcule le TP avec R:R minimum 2:1

        TP minimum = SL × 2 (R:R 2:1)
        TP maximum = tp_max_ticks si structure le permet
        """
        # R:R 2:1 minimum
        tp_ticks_min = int(sl_ticks * self.config.min_rr_ratio)

        # Limiter au maximum configuré
        tp_ticks = min(tp_ticks_min, self.config.tp_max_ticks)

        # Mais toujours respecter le minimum absolu
        tp_ticks = max(tp_ticks, self.config.tp_min_ticks)

        # Conversion ticks → prix
        tick_value = 0.25

        if direction == 'LONG':
            tp = entry_price + (tp_ticks * tick_value)
        else:  # SHORT
            tp = entry_price - (tp_ticks * tick_value)

        return tp, tp_ticks

    def _calculate_size(self, confluence: float) -> float:
        """
        Calcule la taille du trade selon la confluence

        < 0.50: SKIP (0x)
        < 0.60: Réduit (0.5x)
        < 0.70: Normal (1.0x)
        >= 0.70: Boosté (1.5x)
        """
        if confluence < self.config.size_skip_threshold:
            return 0.0
        elif confluence < self.config.size_reduced_threshold:
            return self.config.size_reduced
        elif confluence < self.config.size_normal_threshold:
            return self.config.size_normal
        else:
            return self.config.size_boosted

    def should_take_trade(self, trade_data: Dict) -> Optional[Dict]:
        """
        Décide si on doit prendre ce trade selon T4 vNext

        Critères:
        1. Confluence >= 0.50
        2. R:R >= 2:1 après calcul SL/TP
        3. Size > 0

        Returns:
            Dict avec détails du trade validé, ou None si rejeté
        """
        # Extraire données
        confluence = trade_data.get('confluence', 0)
        entry_price = trade_data.get('entry_price', 0)
        direction = trade_data.get('direction', 'LONG')

        # Critère 1: Confluence minimum
        if confluence < self.config.min_confluence:
            return None

        # Calculer size
        size = self._calculate_size(confluence)

        if size == 0:
            return None

        # Calculer SL
        atr_ticks = trade_data.get('atr_ticks', None)
        sl, sl_ticks = self._calculate_sl(entry_price, direction, atr_ticks)

        # Calculer TP avec R:R 2:1
        tp, tp_ticks = self._calculate_tp(entry_price, direction, sl_ticks)

        # Vérifier R:R effectif
        actual_rr = tp_ticks / sl_ticks if sl_ticks > 0 else 0

        if actual_rr < self.config.min_rr_ratio:
            return None

        return {
            'entry_price': entry_price,
            'direction': direction,
            'sl': sl,
            'tp': tp,
            'sl_ticks': sl_ticks,
            'tp_ticks': tp_ticks,
            'rr_ratio': actual_rr,
            'size': size,
            'confluence': confluence
        }


class T4vNextBacktester:
    """
    Backtester pour T4 vNext
    """

    def __init__(
        self,
        strategy: T4vNextStrategy,
        data_path: str = "ml/data/labeled_trades.parquet"
    ):
        self.strategy = strategy
        self.data_path = Path(data_path)

        logger.info("T4vNextBacktester initialise")
        logger.info(f"  Data path: {self.data_path}")

    def load_data(self) -> pd.DataFrame:
        """Charge les données de trades"""
        if not self.data_path.exists():
            raise FileNotFoundError(f"Fichier introuvable: {self.data_path}")

        df = pd.read_parquet(self.data_path)
        logger.info(f"Donnees chargees: {len(df)} trades")

        return df

    def run_backtest(self) -> pd.DataFrame:
        """
        Lance le backtest T4 vNext

        Logique:
        - Charge les trades déjà exécutés
        - Pour chaque trade, vérifie s'il aurait été pris par T4 vNext
        - Recalcule le P&L selon les nouveaux SL/TP et sizing

        Returns:
            DataFrame avec tous les trades validés et leur P&L ajusté
        """
        logger.info("Demarrage backtest T4 vNext...")

        # Charger données
        df = self.load_data()

        # Pour chaque trade, vérifier si T4 vNext l'aurait pris
        trades_taken = 0
        trades_skipped = 0

        validated_trades = []

        for idx in range(len(df)):
            row = df.iloc[idx]
            trade_data = row.to_dict()

            # Vérifier si on prend ce trade
            setup = self.strategy.should_take_trade(trade_data)

            if setup is None:
                trades_skipped += 1
                continue

            # Trade validé → simuler le résultat avec nouveaux SL/TP et sizing
            # Note: ici on utilise le P&L réel du trade comme proxy
            # Dans un vrai backtest, on re-simulerait avec les nouveaux SL/TP

            original_pnl = row['pnl_ticks']
            original_sl = abs(row['stop'] - row['entry_price']) * 4  # Conversion prix → ticks
            original_tp = abs(row['target'] - row['entry_price']) * 4

            # Estimer le nouveau P&L selon les nouveaux SL/TP
            # Si le trade original était gagnant, on applique le nouveau TP
            # Si perdant, on applique le nouveau SL

            if original_pnl > 0:
                # Gagnant → vérifier si nouveau TP aurait été atteint
                if original_pnl >= setup['tp_ticks']:
                    # TP atteint
                    adjusted_pnl = setup['tp_ticks']
                else:
                    # TP pas atteint → exit au prix réel
                    adjusted_pnl = original_pnl
            else:
                # Perdant → vérifier si nouveau SL aurait été touché
                if abs(original_pnl) >= setup['sl_ticks']:
                    # SL touché
                    adjusted_pnl = -setup['sl_ticks']
                else:
                    # SL pas touché → exit au prix réel
                    adjusted_pnl = original_pnl

            # Appliquer le sizing
            adjusted_pnl_sized = adjusted_pnl * setup['size']

            validated_trades.append({
                'entry_time': pd.to_datetime(row.get('entry_time'), unit='ms') if 'entry_time' in row else None,
                'entry_price': row['entry_price'],
                'direction': row['direction'],
                'confluence': setup['confluence'],
                'size': setup['size'],
                'sl_ticks': setup['sl_ticks'],
                'tp_ticks': setup['tp_ticks'],
                'rr_ratio': setup['rr_ratio'],
                'original_pnl': original_pnl,
                'adjusted_pnl': adjusted_pnl,
                'pnl_ticks': adjusted_pnl_sized,
                'exit_reason': row.get('exit_reason', 'UNKNOWN')
            })

            trades_taken += 1

            if trades_taken % 100 == 0:
                logger.info(f"  Trades valides: {trades_taken}")

        logger.info(f"Backtest termine: {trades_taken} trades valides, {trades_skipped} rejetes")
        logger.info(f"  Taux selection: {trades_taken/(trades_taken+trades_skipped)*100:.1f}%")

        # Convertir en DataFrame
        if not validated_trades:
            logger.warning("Aucun trade valide!")
            return pd.DataFrame()

        df_trades = pd.DataFrame(validated_trades)

        return df_trades

    def calculate_metrics(self, df_trades: pd.DataFrame) -> Dict:
        """
        Calcule les métriques de performance
        """
        if df_trades.empty:
            return {}

        # P&L brut (avant fees)
        pnl_gross = df_trades['pnl_ticks'].sum()

        # Nombre de trades (pondéré par size)
        n_trades = len(df_trades)

        # Fees (par trade, même si size différente)
        fees_total = n_trades * self.strategy.config.fees_per_trade

        # P&L net
        pnl_net = pnl_gross - fees_total

        # P&L par trade
        pnl_per_trade = pnl_net / n_trades if n_trades > 0 else 0

        # WinRate
        wins = (df_trades['pnl_ticks'] > 0).sum()
        losses = (df_trades['pnl_ticks'] < 0).sum()
        winrate = wins / n_trades if n_trades > 0 else 0

        # Profit Factor
        gross_profit = df_trades[df_trades['pnl_ticks'] > 0]['pnl_ticks'].sum()
        gross_loss = abs(df_trades[df_trades['pnl_ticks'] < 0]['pnl_ticks'].sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else np.inf

        # R:R moyen
        avg_rr = df_trades['rr_ratio'].mean()

        # Size moyen
        avg_size = df_trades['size'].mean()

        # Distribution sizing
        size_distribution = df_trades['size'].value_counts().to_dict()

        # Sharpe Ratio (simplifié)
        if 'entry_time' in df_trades.columns and df_trades['entry_time'].notna().any():
            daily_pnl = df_trades.set_index('entry_time')['pnl_ticks'].resample('D').sum()
            sharpe = (daily_pnl.mean() / daily_pnl.std() * np.sqrt(252)) if daily_pnl.std() > 0 else 0
        else:
            sharpe = 0

        # Max Drawdown
        cumulative_pnl = df_trades['pnl_ticks'].cumsum()
        running_max = cumulative_pnl.cummax()
        drawdown = running_max - cumulative_pnl
        max_dd = drawdown.max()

        return {
            'pnl_gross': pnl_gross,
            'pnl_net': pnl_net,
            'pnl_per_trade': pnl_per_trade,
            'n_trades': n_trades,
            'n_wins': wins,
            'n_losses': losses,
            'winrate': winrate,
            'profit_factor': profit_factor,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_dd,
            'fees_total': fees_total,
            'avg_rr': avg_rr,
            'avg_size': avg_size,
            'size_distribution': size_distribution
        }

    def generate_comparison_report(
        self,
        df_trades: pd.DataFrame,
        metrics: Dict,
        baseline_metrics: Dict = None,
        menthorq_metrics: Dict = None
    ) -> str:
        """
        Génère un rapport comparatif avec T4 Baseline et MenthorQ Pure
        """
        report = []
        report.append("=" * 80)
        report.append("RAPPORT COMPARATIF: T4 vNext vs BASELINE vs MENTHORQ PURE")
        report.append("=" * 80)
        report.append("")

        # Métriques T4 vNext
        report.append("## T4 vNext (OPTIMISE)")
        report.append("")
        report.append(f"P&L Brut:        {metrics['pnl_gross']:+.2f} ticks")
        report.append(f"Fees:            -{metrics['fees_total']:.2f} ticks")
        report.append(f"P&L Net:         {metrics['pnl_net']:+.2f} ticks")
        report.append(f"P&L/trade:       {metrics['pnl_per_trade']:+.3f} ticks")
        report.append("")
        report.append(f"Trades:          {metrics['n_trades']}")
        report.append(f"Wins:            {metrics['n_wins']} ({metrics['winrate']*100:.1f}%)")
        report.append(f"Losses:          {metrics['n_losses']}")
        report.append(f"Profit Factor:   {metrics['profit_factor']:.2f}")
        report.append(f"R:R moyen:       {metrics['avg_rr']:.2f}:1")
        report.append(f"Size moyen:      {metrics['avg_size']:.2f}x")
        report.append(f"Sharpe Ratio:    {metrics['sharpe_ratio']:.2f}")
        report.append(f"Max Drawdown:    {metrics['max_drawdown']:.2f} ticks")
        report.append("")
        report.append(f"Distribution sizing:")
        for size, count in sorted(metrics['size_distribution'].items()):
            pct = count / metrics['n_trades'] * 100
            report.append(f"  {size}x: {count} trades ({pct:.1f}%)")
        report.append("")

        # Baseline (si fournie)
        if baseline_metrics:
            report.append("## T4 BASELINE (Reference)")
            report.append("")
            report.append(f"P&L Net:         {baseline_metrics.get('pnl_net', 0):+.2f} ticks")
            report.append(f"P&L/trade:       {baseline_metrics.get('pnl_per_trade', 0):+.3f} ticks")
            report.append(f"Trades:          {baseline_metrics.get('n_trades', 0)}")
            report.append(f"WinRate:         {baseline_metrics.get('winrate', 0)*100:.1f}%")
            report.append("")

        # MenthorQ Pure (si fournie)
        if menthorq_metrics:
            report.append("## MENTHORQ PURE")
            report.append("")
            report.append(f"P&L Net:         {menthorq_metrics.get('pnl_net', 0):+.2f} ticks")
            report.append(f"P&L/trade:       {menthorq_metrics.get('pnl_per_trade', 0):+.3f} ticks")
            report.append(f"Trades:          {menthorq_metrics.get('n_trades', 0)}")
            report.append(f"WinRate:         {menthorq_metrics.get('winrate', 0)*100:.1f}%")
            report.append("")

        # Comparaison
        report.append("## COMPARAISON")
        report.append("")

        if baseline_metrics:
            delta_vs_baseline = metrics['pnl_per_trade'] - baseline_metrics.get('pnl_per_trade', 0)
            delta_pct_baseline = (delta_vs_baseline / baseline_metrics.get('pnl_per_trade', 1)) * 100 if baseline_metrics.get('pnl_per_trade', 0) != 0 else 0

            symbol = "+" if delta_vs_baseline > 0 else ""
            report.append(f"vs T4 Baseline:")
            report.append(f"  Delta P&L/trade: {symbol}{delta_vs_baseline:.3f} ticks ({symbol}{delta_pct_baseline:.1f}%)")

            if delta_vs_baseline > 0.20:
                report.append("  VERDICT: T4 vNext >> BASELINE [EXCELLENT]")
            elif delta_vs_baseline > 0.10:
                report.append("  VERDICT: T4 vNext > BASELINE [BON]")
            elif delta_vs_baseline > 0:
                report.append("  VERDICT: T4 vNext > BASELINE [LEGER]")
            else:
                report.append("  VERDICT: T4 vNext = BASELINE [PAS D'AMELIORATION]")
            report.append("")

        if menthorq_metrics:
            delta_vs_menthorq = metrics['pnl_per_trade'] - menthorq_metrics.get('pnl_per_trade', 0)
            symbol = "+" if delta_vs_menthorq > 0 else ""
            report.append(f"vs MenthorQ Pure:")
            report.append(f"  Delta P&L/trade: {symbol}{delta_vs_menthorq:.3f} ticks")
            report.append("")

        # Objectif
        report.append("## OBJECTIF +1.0 t/trade")
        report.append("")
        gap = 1.0 - metrics['pnl_per_trade']
        if gap <= 0:
            report.append(f"OBJECTIF ATTEINT ! [OK]")
        else:
            report.append(f"Gap restant: {gap:.3f} ticks ({gap/1.0*100:.1f}%)")

            if gap < 0.20:
                report.append("Tres proche de l'objectif ! [EXCELLENT]")
            elif gap < 0.40:
                report.append("Bon progres, quelques optimisations supplementaires necessaires")
            else:
                report.append("Progres significatif, mais plus de travail requis")

        report.append("")
        report.append("=" * 80)

        return "\n".join(report)


def main():
    """Point d'entrée principal"""

    logger.info("=" * 80)
    logger.info("T4 vNext BACKTEST")
    logger.info("=" * 80)
    logger.info("")

    # Configuration
    config = T4vNextConfig(
        min_rr_ratio=2.0,
        sl_min_ticks=10,
        sl_max_ticks=12,
        tp_min_ticks=20,
        tp_max_ticks=25,
        min_confluence=0.40,  # Assoupli de 0.50 à 0.40 pour plus de trades
        size_skip_threshold=0.40,  # Assoupli aussi
        size_reduced_threshold=0.50,
        size_normal_threshold=0.60,
        size_reduced=0.5,
        size_normal=1.0,
        size_boosted=1.5,
        fees_per_trade=0.12,  # OPTION A: PropFirms Moyennes (Apex/TopStep/Elite) - 0.12t pour ES
        use_atr_adaptive_sl=True,
        atr_threshold_ticks=50
    )

    # Créer la stratégie
    strategy = T4vNextStrategy(config)

    # Créer le backtester
    backtester = T4vNextBacktester(
        strategy=strategy,
        data_path="ml/data/labeled_trades.parquet"
    )

    # Lancer le backtest
    df_trades = backtester.run_backtest()

    if df_trades.empty:
        logger.error("Aucun trade genere! Verifiez les parametres.")
        return

    # Calculer métriques
    metrics = backtester.calculate_metrics(df_trades)

    # Métriques baseline (T4) - Avec fees correctes (0.12t)
    baseline_metrics = {
        'pnl_net': 800.0,  # Recalculé: +920t brut - 120t fees (0.12t × 1000)
        'pnl_per_trade': 0.80,  # Au lieu de 0.30t avec fees incorrectes 0.62t
        'n_trades': 1000,
        'winrate': 0.48
    }

    # Métriques MenthorQ Pure - Avec fees correctes (0.12t)
    menthorq_metrics = {
        'pnl_net': -303.42,  # Recalculé: +313t brut - 142.92t fees (0.12t × 1191)
        'pnl_per_trade': -0.255,  # Au lieu de -0.357t avec fees incorrectes
        'n_trades': 1191,
        'winrate': 0.462
    }

    # Générer rapport
    report = backtester.generate_comparison_report(
        df_trades,
        metrics,
        baseline_metrics,
        menthorq_metrics
    )

    print("")
    print(report)

    # Sauvegarder résultats
    output_dir = Path("ml/output")
    output_dir.mkdir(exist_ok=True)

    # Sauvegarder trades
    from datetime import datetime
    trades_file = output_dir / f"t4_vnext_trades_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df_trades.to_csv(trades_file, index=False)
    logger.info(f"Trades sauvegardes: {trades_file}")

    # Sauvegarder rapport
    report_file = output_dir / f"t4_vnext_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    report_file.write_text(report, encoding='utf-8')
    logger.info(f"Rapport sauvegarde: {report_file}")

    logger.info("")
    logger.info("BACKTEST TERMINE [OK]")

    # Afficher résumé final
    logger.info("")
    logger.info("=" * 80)
    logger.info("RESUME FINAL")
    logger.info("=" * 80)
    logger.info(f"T4 vNext P&L/trade:   {metrics['pnl_per_trade']:+.3f} ticks")
    logger.info(f"T4 Baseline:          +0.300 ticks")
    logger.info(f"MenthorQ Pure:        -0.357 ticks")
    logger.info("")

    delta = metrics['pnl_per_trade'] - 0.30
    improvement_pct = (delta / 0.30) * 100 if delta > 0 else 0
    logger.info(f"Amelioration vs Baseline: {delta:+.3f} ticks ({improvement_pct:+.1f}%)")

    gap_to_target = 1.0 - metrics['pnl_per_trade']
    if gap_to_target <= 0:
        logger.info("OBJECTIF +1.0 t/trade ATTEINT ! [VICTOIRE]")
    else:
        logger.info(f"Gap vers objectif +1.0t: {gap_to_target:.3f} ticks")

    logger.info("=" * 80)


if __name__ == "__main__":
    main()
