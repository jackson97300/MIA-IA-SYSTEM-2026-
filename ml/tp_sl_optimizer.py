"""
TP & SL OPTIMIZER - Trouveur de TP et SL Optimaux
==================================================

Objectif: Tester systématiquement toutes les combinaisons de TP/SL
         pour trouver la combinaison optimale qui maximise P&L/trade.

Méthodologie:
1. Charger les trades historiques (labeled_trades.parquet)
2. Pour chaque combinaison (TP, SL):
   - Re-simuler les trades avec le nouveau TP/SL
   - Calculer P&L/trade, WinRate, Profit Factor, R:R
3. Identifier la combinaison qui maximise P&L net/trade
4. Générer des heatmaps et rapports comparatifs ES vs NQ

Auteur: MIA Trading System
Date: 15 Novembre 2025
"""

import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Tuple
import logging
from dataclasses import dataclass

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class OptimizationResult:
    """Résultat d'une combinaison TP/SL"""
    tp_ticks: int
    sl_ticks: int
    rr_ratio: float
    n_trades: int
    pnl_gross: float
    pnl_net: float
    pnl_per_trade: float
    fees_total: float
    wins: int
    losses: int
    winrate: float
    profit_factor: float
    tp_hits: int
    sl_hits: int
    other_exits: int
    tp_hit_rate: float
    sl_hit_rate: float


class TPSLOptimizer:
    """
    Optimiseur de Take Profit et Stop Loss

    Teste toutes les combinaisons de TP/SL pour trouver l'optimal.
    """

    def __init__(
        self,
        data_path: str = "ml/data/labeled_trades.parquet",
        symbol: str = "ES",  # ES ou NQ
        fees_per_trade: float = None  # Auto selon symbole si None
    ):
        self.data_path = Path(data_path)
        self.symbol = symbol.upper()

        # Fees automatiques selon symbole
        if fees_per_trade is None:
            self.fees_per_trade = 0.12 if symbol == "ES" else 0.28
        else:
            self.fees_per_trade = fees_per_trade

        # Valeur du tick
        self.tick_value = 12.50 if symbol == "ES" else 5.00

        logger.info(f"TPSLOptimizer initialise pour {self.symbol}")
        logger.info(f"  Data: {self.data_path}")
        logger.info(f"  Fees: {self.fees_per_trade} ticks")
        logger.info(f"  Tick value: ${self.tick_value}")

    def load_data(self) -> pd.DataFrame:
        """Charge les données de trades historiques"""
        if not self.data_path.exists():
            raise FileNotFoundError(f"Fichier introuvable: {self.data_path}")

        df = pd.read_parquet(self.data_path)

        # Filtrer par symbole
        if 'symbol' in df.columns:
            df = df[df['symbol'] == self.symbol].copy()
            logger.info(f"Donnees chargees: {len(df)} trades {self.symbol}")
        else:
            logger.warning(f"Colonne 'symbol' absente, utilisation de tous les trades")
            logger.info(f"Donnees chargees: {len(df)} trades")

        return df

    def simulate_trade_with_tp_sl(
        self,
        trade: pd.Series,
        tp_ticks: int,
        sl_ticks: int
    ) -> Tuple[float, str]:
        """
        Simule un trade avec un TP et SL donnés

        Args:
            trade: Série pandas avec les données du trade
            tp_ticks: TP à tester (en ticks)
            sl_ticks: SL à tester (en ticks)

        Returns:
            (pnl_ticks, exit_reason)
        """
        # Données du trade original
        original_pnl = trade['pnl_ticks']
        direction = trade['direction']
        mfe_ticks = trade.get('mfe', 0) * 4  # MFE en ticks (si disponible)
        mae_ticks = abs(trade.get('mae', 0)) * 4  # MAE en ticks

        # Si pas de MFE/MAE, utiliser P&L final
        if mfe_ticks == 0:
            mfe_ticks = max(original_pnl, 0)
        if mae_ticks == 0:
            mae_ticks = abs(min(original_pnl, 0))

        # Simuler avec nouveau TP/SL
        # 1. SL atteint en premier ?
        if mae_ticks >= sl_ticks:
            # Vérifier si TP aussi atteint (prendre le premier)
            if mfe_ticks >= tp_ticks:
                # Les deux sont atteints, on suppose SL en premier (worst case)
                return -sl_ticks, 'SL'
            else:
                return -sl_ticks, 'SL'

        # 2. TP atteint ?
        if mfe_ticks >= tp_ticks:
            return tp_ticks, 'TP'

        # 3. Exit au prix final (ni TP ni SL)
        return original_pnl, 'EXIT'

    def test_tp_sl_combination(
        self,
        df: pd.DataFrame,
        tp_ticks: int,
        sl_ticks: int
    ) -> OptimizationResult:
        """
        Teste une combinaison TP/SL sur tous les trades

        Returns:
            OptimizationResult avec métriques de performance
        """
        results = []

        for idx, row in df.iterrows():
            pnl, exit_reason = self.simulate_trade_with_tp_sl(row, tp_ticks, sl_ticks)
            results.append({
                'pnl_ticks': pnl,
                'exit_reason': exit_reason
            })

        df_results = pd.DataFrame(results)

        # Calculer métriques
        n_trades = len(df_results)
        pnl_gross = df_results['pnl_ticks'].sum()
        fees_total = n_trades * self.fees_per_trade
        pnl_net = pnl_gross - fees_total
        pnl_per_trade = pnl_net / n_trades if n_trades > 0 else 0

        wins = (df_results['pnl_ticks'] > 0).sum()
        losses = (df_results['pnl_ticks'] < 0).sum()
        winrate = wins / n_trades if n_trades > 0 else 0

        gross_profit = df_results[df_results['pnl_ticks'] > 0]['pnl_ticks'].sum()
        gross_loss = abs(df_results[df_results['pnl_ticks'] < 0]['pnl_ticks'].sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else np.inf

        # Compter exit reasons
        tp_count = (df_results['exit_reason'] == 'TP').sum()
        sl_count = (df_results['exit_reason'] == 'SL').sum()
        exit_count = (df_results['exit_reason'] == 'EXIT').sum()

        return OptimizationResult(
            tp_ticks=tp_ticks,
            sl_ticks=sl_ticks,
            rr_ratio=tp_ticks / sl_ticks if sl_ticks > 0 else 0,
            n_trades=n_trades,
            pnl_gross=pnl_gross,
            pnl_net=pnl_net,
            pnl_per_trade=pnl_per_trade,
            fees_total=fees_total,
            wins=wins,
            losses=losses,
            winrate=winrate,
            profit_factor=profit_factor,
            tp_hits=tp_count,
            sl_hits=sl_count,
            other_exits=exit_count,
            tp_hit_rate=tp_count / n_trades if n_trades > 0 else 0,
            sl_hit_rate=sl_count / n_trades if n_trades > 0 else 0
        )

    def optimize_tp_sl(
        self,
        tp_range: Tuple[int, int, int] = (10, 35, 1),  # (min, max, step)
        sl_range: Tuple[int, int, int] = (8, 20, 1)    # (min, max, step)
    ) -> pd.DataFrame:
        """
        Teste toutes les combinaisons de TP/SL

        Returns:
            DataFrame avec résultats pour chaque combinaison
        """
        tp_min, tp_max, tp_step = tp_range
        sl_min, sl_max, sl_step = sl_range

        logger.info(f"Optimisation TP/SL:")
        logger.info(f"  TP: {tp_min}-{tp_max} ticks (step {tp_step})")
        logger.info(f"  SL: {sl_min}-{sl_max} ticks (step {sl_step})")

        # Charger données
        df = self.load_data()

        # Tester chaque combinaison
        results = []
        total_combinations = len(range(tp_min, tp_max + 1, tp_step)) * len(range(sl_min, sl_max + 1, sl_step))
        current = 0

        for sl in range(sl_min, sl_max + 1, sl_step):
            for tp in range(tp_min, tp_max + 1, tp_step):
                current += 1
                if current % 10 == 0:
                    progress = (current / total_combinations) * 100
                    logger.info(f"  Progression: {current}/{total_combinations} ({progress:.1f}%) - TP={tp}, SL={sl}")

                result = self.test_tp_sl_combination(df, tp, sl)
                results.append(result)

        df_results = pd.DataFrame([vars(r) for r in results])

        logger.info("Optimisation terminee")
        logger.info(f"  Total combinaisons testees: {len(df_results)}")

        return df_results

    def find_best_combination(
        self,
        df_results: pd.DataFrame,
        criterion: str = 'pnl_per_trade',
        min_rr: float = 1.0,
        min_winrate: float = 0.35,
        min_profit_factor: float = 1.0
    ) -> Dict:
        """
        Trouve la meilleure combinaison TP/SL selon des critères

        Args:
            criterion: 'pnl_per_trade', 'profit_factor', 'winrate', etc.
            min_rr: R:R minimum requis
            min_winrate: WinRate minimum requis
            min_profit_factor: Profit Factor minimum requis

        Returns:
            Dictionnaire avec la meilleure combinaison
        """
        # Filtrer selon critères minimum
        df_filtered = df_results[
            (df_results['rr_ratio'] >= min_rr) &
            (df_results['winrate'] >= min_winrate) &
            (df_results['profit_factor'] >= min_profit_factor)
        ].copy()

        if len(df_filtered) == 0:
            logger.warning("Aucune combinaison ne respecte les criteres minimums")
            logger.warning("Utilisation de tous les resultats sans filtres")
            df_filtered = df_results.copy()

        best_idx = df_filtered[criterion].idxmax()
        best_row = df_filtered.loc[best_idx]

        logger.info(f"Meilleure combinaison selon {criterion}:")
        logger.info(f"  TP: {int(best_row['tp_ticks'])} ticks")
        logger.info(f"  SL: {int(best_row['sl_ticks'])} ticks")
        logger.info(f"  R:R: {best_row['rr_ratio']:.2f}:1")
        logger.info(f"  P&L/trade: {best_row['pnl_per_trade']:+.3f} ticks")
        logger.info(f"  WinRate: {best_row['winrate']*100:.1f}%")
        logger.info(f"  Profit Factor: {best_row['profit_factor']:.2f}")

        return best_row.to_dict()

    def plot_heatmaps(
        self,
        df_results: pd.DataFrame,
        save_path: str = None
    ):
        """
        Crée des heatmaps pour visualiser les résultats
        """
        # Créer pivot tables pour chaque métrique
        pivot_pnl = df_results.pivot(index='sl_ticks', columns='tp_ticks', values='pnl_per_trade')
        pivot_wr = df_results.pivot(index='sl_ticks', columns='tp_ticks', values='winrate')
        pivot_pf = df_results.pivot(index='sl_ticks', columns='tp_ticks', values='profit_factor')
        pivot_rr = df_results.pivot(index='sl_ticks', columns='tp_ticks', values='rr_ratio')

        # Limiter PF pour lisibilité
        pivot_pf = pivot_pf.clip(upper=3)

        fig, axes = plt.subplots(2, 2, figsize=(18, 14))

        # 1. P&L/trade Heatmap
        ax1 = axes[0, 0]
        sns.heatmap(pivot_pnl, annot=False, fmt='.2f', cmap='RdYlGn', center=0,
                   ax=ax1, cbar_kws={'label': 'P&L/trade (ticks)'})
        ax1.set_title(f'P&L/trade - {self.symbol}', fontsize=14, fontweight='bold')
        ax1.set_xlabel('TP (ticks)', fontsize=12)
        ax1.set_ylabel('SL (ticks)', fontsize=12)
        ax1.invert_yaxis()

        # Marquer le meilleur
        best = self.find_best_combination(df_results, 'pnl_per_trade')
        best_tp_idx = list(pivot_pnl.columns).index(best['tp_ticks'])
        best_sl_idx = list(pivot_pnl.index).index(best['sl_ticks'])
        ax1.add_patch(plt.Rectangle((best_tp_idx, best_sl_idx), 1, 1,
                                   fill=False, edgecolor='blue', lw=3))

        # 2. WinRate Heatmap
        ax2 = axes[0, 1]
        sns.heatmap(pivot_wr * 100, annot=False, fmt='.1f', cmap='YlOrRd',
                   ax=ax2, cbar_kws={'label': 'WinRate (%)'})
        ax2.set_title(f'WinRate - {self.symbol}', fontsize=14, fontweight='bold')
        ax2.set_xlabel('TP (ticks)', fontsize=12)
        ax2.set_ylabel('SL (ticks)', fontsize=12)
        ax2.invert_yaxis()

        # 3. Profit Factor Heatmap
        ax3 = axes[1, 0]
        sns.heatmap(pivot_pf, annot=False, fmt='.2f', cmap='viridis',
                   ax=ax3, cbar_kws={'label': 'Profit Factor'})
        ax3.set_title(f'Profit Factor - {self.symbol}', fontsize=14, fontweight='bold')
        ax3.set_xlabel('TP (ticks)', fontsize=12)
        ax3.set_ylabel('SL (ticks)', fontsize=12)
        ax3.invert_yaxis()

        # 4. R:R Heatmap
        ax4 = axes[1, 1]
        sns.heatmap(pivot_rr, annot=False, fmt='.2f', cmap='coolwarm',
                   ax=ax4, cbar_kws={'label': 'R:R Ratio'})
        ax4.set_title(f'R:R Ratio - {self.symbol}', fontsize=14, fontweight='bold')
        ax4.set_xlabel('TP (ticks)', fontsize=12)
        ax4.set_ylabel('SL (ticks)', fontsize=12)
        ax4.invert_yaxis()

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            logger.info(f"Heatmaps sauvegardees: {save_path}")

        plt.close()

    def plot_3d_surface(
        self,
        df_results: pd.DataFrame,
        save_path: str = None
    ):
        """
        Crée un graphique 3D de P&L/trade en fonction de TP et SL
        """
        from mpl_toolkits.mplot3d import Axes3D

        fig = plt.figure(figsize=(14, 10))
        ax = fig.add_subplot(111, projection='3d')

        # Préparer données
        pivot_pnl = df_results.pivot(index='sl_ticks', columns='tp_ticks', values='pnl_per_trade')

        X = pivot_pnl.columns.values
        Y = pivot_pnl.index.values
        X, Y = np.meshgrid(X, Y)
        Z = pivot_pnl.values

        # Surface plot
        surf = ax.plot_surface(X, Y, Z, cmap='RdYlGn', alpha=0.8, edgecolor='none')

        # Labels
        ax.set_xlabel('TP (ticks)', fontsize=12, labelpad=10)
        ax.set_ylabel('SL (ticks)', fontsize=12, labelpad=10)
        ax.set_zlabel('P&L/trade (ticks)', fontsize=12, labelpad=10)
        ax.set_title(f'Surface P&L/trade - {self.symbol}', fontsize=14, fontweight='bold', pad=20)

        # Colorbar
        fig.colorbar(surf, ax=ax, shrink=0.5, aspect=5)

        # Marquer le meilleur
        best = self.find_best_combination(df_results, 'pnl_per_trade')
        ax.scatter([best['tp_ticks']], [best['sl_ticks']], [best['pnl_per_trade']],
                  color='blue', s=200, marker='*', edgecolors='black', linewidths=2,
                  label=f"Optimal: TP={int(best['tp_ticks'])}, SL={int(best['sl_ticks'])}")

        ax.legend()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            logger.info(f"Graphique 3D sauvegarde: {save_path}")

        plt.close()

    def generate_report(
        self,
        df_results: pd.DataFrame,
        save_path: str = None
    ) -> str:
        """
        Génère un rapport texte avec les résultats
        """
        report = []
        report.append("=" * 80)
        report.append(f"RAPPORT OPTIMISATION TP/SL - {self.symbol}")
        report.append("=" * 80)
        report.append("")

        # Meilleure combinaison
        best = self.find_best_combination(df_results, 'pnl_per_trade')

        report.append("## MEILLEURE COMBINAISON (selon P&L/trade)")
        report.append("")
        report.append(f"TP Optimal:      {int(best['tp_ticks'])} ticks")
        report.append(f"SL Optimal:      {int(best['sl_ticks'])} ticks")
        report.append(f"R:R:             {best['rr_ratio']:.2f}:1")
        report.append(f"P&L/trade:       {best['pnl_per_trade']:+.3f} ticks")
        report.append(f"P&L Net:         {best['pnl_net']:+.2f} ticks")
        report.append(f"WinRate:         {best['winrate']*100:.1f}%")
        report.append(f"Profit Factor:   {best['profit_factor']:.2f}")
        report.append(f"TP Hit Rate:     {best['tp_hit_rate']*100:.1f}%")
        report.append(f"SL Hit Rate:     {best['sl_hit_rate']*100:.1f}%")
        report.append("")

        # Impact financier
        report.append("## IMPACT FINANCIER")
        report.append("")
        report.append("Sur 1,000 trades:")
        pnl_usd = best['pnl_per_trade'] * 1000 * self.tick_value
        report.append(f"  P&L Net: {pnl_usd:+,.2f} USD")
        report.append("")

        # Objectif +1.0t
        gap_to_target = 1.0 - best['pnl_per_trade']

        report.append("## OBJECTIF +1.0 t/trade")
        report.append("")
        if best['pnl_per_trade'] >= 1.0:
            report.append(f"OBJECTIF ATTEINT ! (+{best['pnl_per_trade']-1.0:.3f}t au-dessus)")
        else:
            report.append(f"Gap restant: {gap_to_target:.3f} ticks ({gap_to_target/1.0*100:.1f}%)")
        report.append("")

        # Top 10 combinaisons
        report.append("## TOP 10 MEILLEURES COMBINAISONS")
        report.append("")
        top10 = df_results.nlargest(10, 'pnl_per_trade')

        for i, (idx, row) in enumerate(top10.iterrows(), 1):
            report.append(f"{i:2d}. TP={int(row['tp_ticks']):2d}t, SL={int(row['sl_ticks']):2d}t | "
                        f"R:R={row['rr_ratio']:.2f}:1 | "
                        f"P&L={row['pnl_per_trade']:+.3f}t | "
                        f"WR={row['winrate']*100:.1f}% | "
                        f"PF={row['profit_factor']:.2f}")

        report.append("")

        # Statistiques globales
        report.append("## STATISTIQUES GLOBALES")
        report.append("")
        report.append(f"Total combinaisons testees: {len(df_results)}")
        report.append(f"Combinaisons rentables (P&L > 0): {(df_results['pnl_per_trade'] > 0).sum()}")
        report.append(f"Combinaisons atteignant +1.0t: {(df_results['pnl_per_trade'] >= 1.0).sum()}")
        report.append(f"Meilleur P&L/trade: {df_results['pnl_per_trade'].max():+.3f}t")
        report.append(f"Pire P&L/trade: {df_results['pnl_per_trade'].min():+.3f}t")
        report.append("")

        report.append("=" * 80)

        report_text = "\n".join(report)

        if save_path:
            Path(save_path).write_text(report_text, encoding='utf-8')
            logger.info(f"Rapport sauvegarde: {save_path}")

        return report_text


def main():
    """Point d'entrée principal"""

    logger.info("=" * 80)
    logger.info("TP & SL OPTIMIZER - Recherche de la combinaison optimale ES & NQ")
    logger.info("=" * 80)
    logger.info("")

    output_dir = Path("ml/output")
    output_dir.mkdir(exist_ok=True)

    from datetime import datetime
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Liste pour stocker tous les résultats
    all_results = {}

    # OPTIMISER ES ET NQ
    for symbol in ["ES", "NQ"]:
        logger.info("")
        logger.info("=" * 80)
        logger.info(f"OPTIMISATION {symbol}")
        logger.info("=" * 80)
        logger.info("")

        # Créer l'optimiseur pour ce symbole
        optimizer = TPSLOptimizer(
            data_path="ml/data/labeled_trades.parquet",
            symbol=symbol,
            fees_per_trade=None  # Auto: 0.12 ES, 0.28 NQ
        )

        # Optimiser TP/SL
        df_results = optimizer.optimize_tp_sl(
            tp_range=(10, 35, 1),  # TP: 10-35 ticks
            sl_range=(8, 20, 1)    # SL: 8-20 ticks
        )

        # Sauvegarder résultats CSV
        csv_file = output_dir / f"tp_sl_optimization_{symbol}_{timestamp}.csv"
        df_results.to_csv(csv_file, index=False)
        logger.info(f"Resultats CSV sauvegardes: {csv_file}")

        # Générer heatmaps
        heatmap_file = output_dir / f"tp_sl_heatmaps_{symbol}_{timestamp}.png"
        optimizer.plot_heatmaps(df_results, save_path=heatmap_file)

        # Générer graphique 3D
        plot3d_file = output_dir / f"tp_sl_3d_{symbol}_{timestamp}.png"
        optimizer.plot_3d_surface(df_results, save_path=plot3d_file)

        # Générer rapport
        report_file = output_dir / f"tp_sl_optimization_{symbol}_{timestamp}.txt"
        report = optimizer.generate_report(df_results, save_path=report_file)

        # Stocker résultats
        all_results[symbol] = {
            'optimizer': optimizer,
            'df_results': df_results,
            'report': report
        }

    # RAPPORT COMPARATIF ES vs NQ
    logger.info("")
    logger.info("=" * 80)
    logger.info("GENERATION RAPPORT COMPARATIF ES vs NQ")
    logger.info("=" * 80)
    logger.info("")

    # Extraire les meilleures combinaisons
    best_es = all_results['ES']['optimizer'].find_best_combination(
        all_results['ES']['df_results'], 'pnl_per_trade'
    )
    best_nq = all_results['NQ']['optimizer'].find_best_combination(
        all_results['NQ']['df_results'], 'pnl_per_trade'
    )

    # Créer rapport comparatif
    comp_report = []
    comp_report.append("=" * 80)
    comp_report.append("RAPPORT COMPARATIF: TP/SL OPTIMAL ES vs NQ")
    comp_report.append("=" * 80)
    comp_report.append("")

    comp_report.append("## RESULTATS PAR SYMBOLE")
    comp_report.append("")

    # ES
    comp_report.append("### ES (S&P 500)")
    comp_report.append("")
    comp_report.append(f"TP Optimal:      {int(best_es['tp_ticks'])} ticks")
    comp_report.append(f"SL Optimal:      {int(best_es['sl_ticks'])} ticks")
    comp_report.append(f"R:R:             {best_es['rr_ratio']:.2f}:1")
    comp_report.append(f"P&L/trade:       {best_es['pnl_per_trade']:+.3f} ticks")
    comp_report.append(f"WinRate:         {best_es['winrate']*100:.1f}%")
    comp_report.append(f"Profit Factor:   {best_es['profit_factor']:.2f}")
    comp_report.append(f"Fees:            {all_results['ES']['optimizer'].fees_per_trade} ticks")
    comp_report.append(f"Tick Value:      ${all_results['ES']['optimizer'].tick_value}")
    comp_report.append("")
    comp_report.append(f"Sur 1,000 trades:")
    pnl_usd_es = best_es['pnl_per_trade'] * 1000 * all_results['ES']['optimizer'].tick_value
    comp_report.append(f"  P&L Net: {pnl_usd_es:+,.2f} USD")
    comp_report.append("")

    # NQ
    comp_report.append("### NQ (Nasdaq-100)")
    comp_report.append("")
    comp_report.append(f"TP Optimal:      {int(best_nq['tp_ticks'])} ticks")
    comp_report.append(f"SL Optimal:      {int(best_nq['sl_ticks'])} ticks")
    comp_report.append(f"R:R:             {best_nq['rr_ratio']:.2f}:1")
    comp_report.append(f"P&L/trade:       {best_nq['pnl_per_trade']:+.3f} ticks")
    comp_report.append(f"WinRate:         {best_nq['winrate']*100:.1f}%")
    comp_report.append(f"Profit Factor:   {best_nq['profit_factor']:.2f}")
    comp_report.append(f"Fees:            {all_results['NQ']['optimizer'].fees_per_trade} ticks")
    comp_report.append(f"Tick Value:      ${all_results['NQ']['optimizer'].tick_value}")
    comp_report.append("")
    comp_report.append(f"Sur 1,000 trades:")
    pnl_usd_nq = best_nq['pnl_per_trade'] * 1000 * all_results['NQ']['optimizer'].tick_value
    comp_report.append(f"  P&L Net: {pnl_usd_nq:+,.2f} USD")
    comp_report.append("")

    # Comparaison
    comp_report.append("## COMPARAISON")
    comp_report.append("")

    comp_report.append("| Metrique | ES | NQ | Gagnant |")
    comp_report.append("|----------|----|----|---------|")
    comp_report.append(f"| TP Optimal | {int(best_es['tp_ticks'])}t | {int(best_nq['tp_ticks'])}t | - |")
    comp_report.append(f"| SL Optimal | {int(best_es['sl_ticks'])}t | {int(best_nq['sl_ticks'])}t | - |")
    comp_report.append(f"| R:R | {best_es['rr_ratio']:.2f}:1 | {best_nq['rr_ratio']:.2f}:1 | {'ES' if best_es['rr_ratio'] > best_nq['rr_ratio'] else 'NQ'} |")
    comp_report.append(f"| P&L/trade | {best_es['pnl_per_trade']:+.3f}t | {best_nq['pnl_per_trade']:+.3f}t | {'ES' if best_es['pnl_per_trade'] > best_nq['pnl_per_trade'] else 'NQ'} |")
    comp_report.append(f"| WinRate | {best_es['winrate']*100:.1f}% | {best_nq['winrate']*100:.1f}% | {'ES' if best_es['winrate'] > best_nq['winrate'] else 'NQ'} |")
    comp_report.append(f"| P&L 1000 trades | ${pnl_usd_es:,.0f} | ${pnl_usd_nq:,.0f} | {'ES' if pnl_usd_es > pnl_usd_nq else 'NQ'} |")
    comp_report.append(f"| Objectif +1.0t | {'OUI' if best_es['pnl_per_trade'] >= 1.0 else 'NON'} | {'OUI' if best_nq['pnl_per_trade'] >= 1.0 else 'NON'} | - |")
    comp_report.append("")

    # Recommandation
    comp_report.append("## RECOMMANDATION FINALE")
    comp_report.append("")

    if best_es['pnl_per_trade'] > best_nq['pnl_per_trade']:
        winner = "ES"
        winner_pnl = best_es['pnl_per_trade']
        winner_tp = int(best_es['tp_ticks'])
        winner_sl = int(best_es['sl_ticks'])
        winner_rr = best_es['rr_ratio']
    else:
        winner = "NQ"
        winner_pnl = best_nq['pnl_per_trade']
        winner_tp = int(best_nq['tp_ticks'])
        winner_sl = int(best_nq['sl_ticks'])
        winner_rr = best_nq['rr_ratio']

    comp_report.append(f"**FOCUS PRINCIPAL: {winner}**")
    comp_report.append("")
    comp_report.append(f"- TP Optimal: **{winner_tp} ticks**")
    comp_report.append(f"- SL Optimal: **{winner_sl} ticks**")
    comp_report.append(f"- R:R: **{winner_rr:.2f}:1**")
    comp_report.append(f"- Performance: **{winner_pnl:+.3f} t/trade**")
    comp_report.append("")

    comp_report.append("**Configuration recommandee:**")
    comp_report.append("")
    comp_report.append("```python")
    comp_report.append(f"# ES:")
    comp_report.append(f"tp_ticks_es = {int(best_es['tp_ticks'])}  # R:R {best_es['rr_ratio']:.2f}:1")
    comp_report.append(f"sl_ticks_es = {int(best_es['sl_ticks'])}")
    comp_report.append(f"# Performance attendue: {best_es['pnl_per_trade']:+.3f} t/trade")
    comp_report.append("")
    comp_report.append(f"# NQ:")
    comp_report.append(f"tp_ticks_nq = {int(best_nq['tp_ticks'])}  # R:R {best_nq['rr_ratio']:.2f}:1")
    comp_report.append(f"sl_ticks_nq = {int(best_nq['sl_ticks'])}")
    comp_report.append(f"# Performance attendue: {best_nq['pnl_per_trade']:+.3f} t/trade")
    comp_report.append("```")
    comp_report.append("")
    comp_report.append("=" * 80)

    comp_report_text = "\n".join(comp_report)

    # Sauvegarder rapport comparatif
    comp_file = output_dir / f"tp_sl_optimization_COMPARISON_{timestamp}.txt"
    comp_file.write_text(comp_report_text, encoding='utf-8')
    logger.info(f"Rapport comparatif sauvegarde: {comp_file}")

    # Afficher tous les rapports
    print("")
    print("=" * 80)
    print("RAPPORT ES")
    print("=" * 80)
    print(all_results['ES']['report'])

    print("")
    print("=" * 80)
    print("RAPPORT NQ")
    print("=" * 80)
    print(all_results['NQ']['report'])

    print("")
    print(comp_report_text)

    logger.info("")
    logger.info("OPTIMISATION TERMINEE [OK]")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()







