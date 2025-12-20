"""
TP OPTIMIZER - Trouveur de TP Optimal
======================================

Objectif: Tester systématiquement différentes valeurs de TP pour trouver
         le TP optimal qui maximise P&L/trade sur ES.

Méthodologie:
1. Charger les trades historiques (labeled_trades.parquet)
2. Pour chaque valeur de TP (de 10t à 35t):
   - Re-simuler les trades avec le nouveau TP
   - Calculer P&L/trade, WinRate, Profit Factor
3. Identifier le TP qui maximise P&L net/trade

Auteur: MIA Trading System
Date: 15 Novembre 2025
"""

import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple
import logging

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TPOptimizer:
    """
    Optimiseur de Take Profit

    Teste différentes valeurs de TP pour trouver l'optimal.
    """

    def __init__(
        self,
        data_path: str = "ml/data/labeled_trades.parquet",
        symbol: str = "ES",  # ES ou NQ
        sl_fixed: int = 12,  # SL fixe à 12 ticks
        fees_per_trade: float = None  # Auto selon symbole si None
    ):
        self.data_path = Path(data_path)
        self.symbol = symbol.upper()
        self.sl_fixed = sl_fixed

        # Fees automatiques selon symbole
        if fees_per_trade is None:
            self.fees_per_trade = 0.12 if symbol == "ES" else 0.28
        else:
            self.fees_per_trade = fees_per_trade

        # Valeur du tick
        self.tick_value = 12.50 if symbol == "ES" else 5.00

        logger.info(f"TPOptimizer initialise pour {self.symbol}")
        logger.info(f"  Data: {self.data_path}")
        logger.info(f"  SL fixe: {sl_fixed} ticks")
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

    def simulate_trade_with_tp(
        self,
        trade: pd.Series,
        tp_ticks: int
    ) -> Tuple[float, str]:
        """
        Simule un trade avec un TP donné

        Args:
            trade: Série pandas avec les données du trade
            tp_ticks: TP à tester (en ticks)

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

        # Simuler avec nouveau TP
        # 1. TP atteint ?
        if mfe_ticks >= tp_ticks:
            return tp_ticks, 'TP'

        # 2. SL atteint ?
        if mae_ticks >= self.sl_fixed:
            return -self.sl_fixed, 'SL'

        # 3. Exit au prix final (ni TP ni SL)
        return original_pnl, 'EXIT'

    def test_tp_value(
        self,
        df: pd.DataFrame,
        tp_ticks: int
    ) -> Dict:
        """
        Teste une valeur de TP sur tous les trades

        Returns:
            Dictionnaire avec métriques de performance
        """
        results = []

        for idx, row in df.iterrows():
            pnl, exit_reason = self.simulate_trade_with_tp(row, tp_ticks)
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

        return {
            'tp_ticks': tp_ticks,
            'rr_ratio': tp_ticks / self.sl_fixed,
            'n_trades': n_trades,
            'pnl_gross': pnl_gross,
            'pnl_net': pnl_net,
            'pnl_per_trade': pnl_per_trade,
            'fees_total': fees_total,
            'wins': wins,
            'losses': losses,
            'winrate': winrate,
            'profit_factor': profit_factor,
            'tp_hits': tp_count,
            'sl_hits': sl_count,
            'other_exits': exit_count,
            'tp_hit_rate': tp_count / n_trades if n_trades > 0 else 0
        }

    def optimize_tp(
        self,
        tp_min: int = 10,
        tp_max: int = 35,
        tp_step: int = 1
    ) -> pd.DataFrame:
        """
        Teste toutes les valeurs de TP entre min et max

        Returns:
            DataFrame avec résultats pour chaque TP
        """
        logger.info(f"Optimisation TP: {tp_min}-{tp_max} ticks (step {tp_step})")

        # Charger données
        df = self.load_data()

        # Tester chaque valeur de TP
        results = []

        for tp in range(tp_min, tp_max + 1, tp_step):
            logger.info(f"  Test TP = {tp} ticks...")
            metrics = self.test_tp_value(df, tp)
            results.append(metrics)

        df_results = pd.DataFrame(results)

        logger.info("Optimisation terminee")

        return df_results

    def find_best_tp(
        self,
        df_results: pd.DataFrame,
        criterion: str = 'pnl_per_trade'
    ) -> Dict:
        """
        Trouve le meilleur TP selon un critère

        Args:
            criterion: 'pnl_per_trade', 'profit_factor', 'winrate', etc.

        Returns:
            Ligne du DataFrame avec le meilleur TP
        """
        best_idx = df_results[criterion].idxmax()
        best_row = df_results.loc[best_idx]

        logger.info(f"Meilleur TP selon {criterion}: {best_row['tp_ticks']} ticks")
        logger.info(f"  P&L/trade: {best_row['pnl_per_trade']:.3f} ticks")
        logger.info(f"  WinRate: {best_row['winrate']*100:.1f}%")
        logger.info(f"  Profit Factor: {best_row['profit_factor']:.2f}")

        return best_row.to_dict()

    def plot_results(
        self,
        df_results: pd.DataFrame,
        save_path: str = None
    ):
        """
        Crée des graphiques pour visualiser les résultats
        """
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))

        # 1. P&L/trade vs TP
        ax1 = axes[0, 0]
        ax1.plot(df_results['tp_ticks'], df_results['pnl_per_trade'],
                'b-o', linewidth=2, markersize=4)
        ax1.axhline(y=0, color='r', linestyle='--', alpha=0.5)
        ax1.axhline(y=1.0, color='g', linestyle='--', alpha=0.5, label='Objectif +1.0t')
        ax1.set_xlabel('TP (ticks)', fontsize=12)
        ax1.set_ylabel('P&L/trade (ticks)', fontsize=12)
        ax1.set_title('P&L/trade vs TP', fontsize=14, fontweight='bold')
        ax1.grid(True, alpha=0.3)
        ax1.legend()

        # Marquer le meilleur
        best_idx = df_results['pnl_per_trade'].idxmax()
        best_tp = df_results.loc[best_idx, 'tp_ticks']
        best_pnl = df_results.loc[best_idx, 'pnl_per_trade']
        ax1.plot(best_tp, best_pnl, 'r*', markersize=20,
                label=f'Best: TP={best_tp}t, P&L={best_pnl:.3f}t')
        ax1.legend()

        # 2. WinRate vs TP
        ax2 = axes[0, 1]
        ax2.plot(df_results['tp_ticks'], df_results['winrate'] * 100,
                'g-o', linewidth=2, markersize=4)
        ax2.set_xlabel('TP (ticks)', fontsize=12)
        ax2.set_ylabel('WinRate (%)', fontsize=12)
        ax2.set_title('WinRate vs TP', fontsize=14, fontweight='bold')
        ax2.grid(True, alpha=0.3)

        # 3. Profit Factor vs TP
        ax3 = axes[1, 0]
        # Limiter PF pour lisibilité
        pf_capped = df_results['profit_factor'].clip(upper=5)
        ax3.plot(df_results['tp_ticks'], pf_capped,
                'orange', linewidth=2, marker='o', markersize=4)
        ax3.axhline(y=2.0, color='g', linestyle='--', alpha=0.5, label='PF 2.0')
        ax3.set_xlabel('TP (ticks)', fontsize=12)
        ax3.set_ylabel('Profit Factor', fontsize=12)
        ax3.set_title('Profit Factor vs TP', fontsize=14, fontweight='bold')
        ax3.grid(True, alpha=0.3)
        ax3.legend()

        # 4. R:R vs P&L/trade
        ax4 = axes[1, 1]
        scatter = ax4.scatter(df_results['rr_ratio'], df_results['pnl_per_trade'],
                            c=df_results['winrate'], cmap='RdYlGn',
                            s=100, alpha=0.6, edgecolors='black')
        ax4.axhline(y=0, color='r', linestyle='--', alpha=0.5)
        ax4.axhline(y=1.0, color='g', linestyle='--', alpha=0.5, label='Objectif +1.0t')
        ax4.set_xlabel('R:R Ratio', fontsize=12)
        ax4.set_ylabel('P&L/trade (ticks)', fontsize=12)
        ax4.set_title('R:R vs P&L/trade (coloré par WinRate)', fontsize=14, fontweight='bold')
        ax4.grid(True, alpha=0.3)
        ax4.legend()

        # Colorbar
        cbar = plt.colorbar(scatter, ax=ax4)
        cbar.set_label('WinRate', fontsize=10)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            logger.info(f"Graphiques sauvegardes: {save_path}")

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
        report.append(f"RAPPORT OPTIMISATION TP - {self.symbol}")
        report.append("=" * 80)
        report.append("")

        # Meilleur TP
        best = self.find_best_tp(df_results, 'pnl_per_trade')

        report.append("## MEILLEUR TP (selon P&L/trade)")
        report.append("")
        report.append(f"TP Optimal:      {best['tp_ticks']} ticks")
        report.append(f"R:R:             {best['rr_ratio']:.2f}:1")
        report.append(f"P&L/trade:       {best['pnl_per_trade']:+.3f} ticks")
        report.append(f"P&L Net:         {best['pnl_net']:+.2f} ticks")
        report.append(f"WinRate:         {best['winrate']*100:.1f}%")
        report.append(f"Profit Factor:   {best['profit_factor']:.2f}")
        report.append(f"TP Hit Rate:     {best['tp_hit_rate']*100:.1f}%")
        report.append("")

        # Comparaison avec baseline
        baseline_pnl = 0.80  # P&L actuel
        improvement = best['pnl_per_trade'] - baseline_pnl
        improvement_pct = (improvement / baseline_pnl) * 100

        report.append("## COMPARAISON vs BASELINE")
        report.append("")
        report.append(f"Baseline (TP actuel):  +{baseline_pnl:.2f} t/trade")
        report.append(f"TP Optimise:           +{best['pnl_per_trade']:.3f} t/trade")
        report.append(f"Amelioration:          +{improvement:.3f} ticks ({improvement_pct:+.1f}%)")
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

        # Top 5 TP
        report.append("## TOP 5 MEILLEURS TP")
        report.append("")
        top5 = df_results.nlargest(5, 'pnl_per_trade')

        for i, (idx, row) in enumerate(top5.iterrows(), 1):
            report.append(f"{i}. TP={int(row['tp_ticks']):2d}t | "
                        f"P&L={row['pnl_per_trade']:+.3f}t | "
                        f"WR={row['winrate']*100:.1f}% | "
                        f"PF={row['profit_factor']:.2f} | "
                        f"R:R={row['rr_ratio']:.2f}:1")

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
    logger.info("TP OPTIMIZER - Recherche du TP Optimal ES & NQ")
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
        optimizer = TPOptimizer(
            data_path="ml/data/labeled_trades.parquet",
            symbol=symbol,
            sl_fixed=12,
            fees_per_trade=None  # Auto: 0.12 ES, 0.28 NQ
        )

        # Optimiser TP
        df_results = optimizer.optimize_tp(
            tp_min=10,
            tp_max=35,
            tp_step=1
        )

        # Sauvegarder résultats CSV
        csv_file = output_dir / f"tp_optimization_{symbol}_{timestamp}.csv"
        df_results.to_csv(csv_file, index=False)
        logger.info(f"Resultats CSV sauvegardes: {csv_file}")

        # Générer graphiques
        plot_file = output_dir / f"tp_optimization_{symbol}_{timestamp}.png"
        optimizer.plot_results(df_results, save_path=plot_file)

        # Générer rapport
        report_file = output_dir / f"tp_optimization_{symbol}_{timestamp}.txt"
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
    logger.info("GÉNÉRATION RAPPORT COMPARATIF ES vs NQ")
    logger.info("=" * 80)
    logger.info("")

    # Extraire les meilleurs TP
    best_es = all_results['ES']['optimizer'].find_best_tp(
        all_results['ES']['df_results'], 'pnl_per_trade'
    )
    best_nq = all_results['NQ']['optimizer'].find_best_tp(
        all_results['NQ']['df_results'], 'pnl_per_trade'
    )

    # Créer rapport comparatif
    comp_report = []
    comp_report.append("=" * 80)
    comp_report.append("RAPPORT COMPARATIF: TP OPTIMAL ES vs NQ")
    comp_report.append("=" * 80)
    comp_report.append("")

    comp_report.append("## RÉSULTATS PAR SYMBOLE")
    comp_report.append("")

    # ES
    comp_report.append("### ES (S&P 500)")
    comp_report.append("")
    comp_report.append(f"TP Optimal:      {int(best_es['tp_ticks'])} ticks")
    comp_report.append(f"R:R:             {best_es['rr_ratio']:.2f}:1")
    comp_report.append(f"P&L/trade:       {best_es['pnl_per_trade']:+.3f} ticks")
    comp_report.append(f"WinRate:         {best_es['winrate']*100:.1f}%")
    comp_report.append(f"Profit Factor:   {best_es['profit_factor']:.2f}")
    comp_report.append(f"Fees:            {all_results['ES']['optimizer'].fees_per_trade} ticks")
    comp_report.append(f"Tick Value:      ${all_results['ES']['optimizer'].tick_value}")
    comp_report.append("")
    comp_report.append(f"Sur 1,000 trades:")
    pnl_usd_es = best_es['pnl_per_trade'] * 1000 * all_results['ES']['optimizer'].tick_value
    comp_report.append(f"  P&L Net: +{pnl_usd_es:,.2f} USD")
    comp_report.append("")

    # NQ
    comp_report.append("### NQ (Nasdaq-100)")
    comp_report.append("")
    comp_report.append(f"TP Optimal:      {int(best_nq['tp_ticks'])} ticks")
    comp_report.append(f"R:R:             {best_nq['rr_ratio']:.2f}:1")
    comp_report.append(f"P&L/trade:       {best_nq['pnl_per_trade']:+.3f} ticks")
    comp_report.append(f"WinRate:         {best_nq['winrate']*100:.1f}%")
    comp_report.append(f"Profit Factor:   {best_nq['profit_factor']:.2f}")
    comp_report.append(f"Fees:            {all_results['NQ']['optimizer'].fees_per_trade} ticks")
    comp_report.append(f"Tick Value:      ${all_results['NQ']['optimizer'].tick_value}")
    comp_report.append("")
    comp_report.append(f"Sur 1,000 trades:")
    pnl_usd_nq = best_nq['pnl_per_trade'] * 1000 * all_results['NQ']['optimizer'].tick_value
    comp_report.append(f"  P&L Net: +{pnl_usd_nq:,.2f} USD")
    comp_report.append("")

    # Comparaison
    comp_report.append("## COMPARAISON")
    comp_report.append("")

    comp_report.append("| Métrique | ES | NQ | Gagnant |")
    comp_report.append("|----------|----|----|---------|")
    comp_report.append(f"| TP Optimal | {int(best_es['tp_ticks'])}t | {int(best_nq['tp_ticks'])}t | - |")
    comp_report.append(f"| P&L/trade | {best_es['pnl_per_trade']:+.3f}t | {best_nq['pnl_per_trade']:+.3f}t | {'ES' if best_es['pnl_per_trade'] > best_nq['pnl_per_trade'] else 'NQ'} |")
    comp_report.append(f"| WinRate | {best_es['winrate']*100:.1f}% | {best_nq['winrate']*100:.1f}% | {'ES' if best_es['winrate'] > best_nq['winrate'] else 'NQ'} |")
    comp_report.append(f"| P&L 1000 trades | ${pnl_usd_es:,.0f} | ${pnl_usd_nq:,.0f} | {'ES' if pnl_usd_es > pnl_usd_nq else 'NQ'} |")
    comp_report.append(f"| Fees (ticks) | 0.12t | 0.28t | ES |")
    comp_report.append(f"| Objectif +1.0t | {'✅ ATTEINT' if best_es['pnl_per_trade'] >= 1.0 else '❌ Non'} | {'✅ ATTEINT' if best_nq['pnl_per_trade'] >= 1.0 else '❌ Non'} | - |")
    comp_report.append("")

    # Recommandation
    comp_report.append("## RECOMMANDATION FINALE")
    comp_report.append("")

    if best_es['pnl_per_trade'] > best_nq['pnl_per_trade']:
        winner = "ES"
        winner_pnl = best_es['pnl_per_trade']
        winner_tp = int(best_es['tp_ticks'])
    else:
        winner = "NQ"
        winner_pnl = best_nq['pnl_per_trade']
        winner_tp = int(best_nq['tp_ticks'])

    comp_report.append(f"**FOCUS PRINCIPAL: {winner}**")
    comp_report.append("")
    comp_report.append(f"- TP Optimal: **{winner_tp} ticks**")
    comp_report.append(f"- Performance: **{winner_pnl:+.3f} t/trade**")
    comp_report.append(f"- Meilleur P&L net/trade")
    comp_report.append("")

    comp_report.append("**Configuration recommandée:**")
    comp_report.append("")
    comp_report.append("```python")
    comp_report.append(f"# ES:")
    comp_report.append(f"tp_ticks_es = {int(best_es['tp_ticks'])}  # R:R {best_es['rr_ratio']:.2f}:1")
    comp_report.append(f"# Performance attendue: {best_es['pnl_per_trade']:+.3f} t/trade")
    comp_report.append("")
    comp_report.append(f"# NQ:")
    comp_report.append(f"tp_ticks_nq = {int(best_nq['tp_ticks'])}  # R:R {best_nq['rr_ratio']:.2f}:1")
    comp_report.append(f"# Performance attendue: {best_nq['pnl_per_trade']:+.3f} t/trade")
    comp_report.append("```")
    comp_report.append("")
    comp_report.append("=" * 80)

    comp_report_text = "\n".join(comp_report)

    # Sauvegarder rapport comparatif
    comp_file = output_dir / f"tp_optimization_COMPARISON_{timestamp}.txt"
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
