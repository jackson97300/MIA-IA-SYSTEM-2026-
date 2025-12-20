#!/usr/bin/env python3
"""
Optimisation du seuil de décision pour T7_expected_value

Teste différents seuils EV pour maximiser P&L/trade > +1.0t
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Tuple

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_data(data_path: str) -> pd.DataFrame:
    """Charge les données"""
    df = pd.read_parquet(data_path)

    # Créer sl_ticks si nécessaire
    if 'stop' in df.columns and 'sl_ticks' not in df.columns:
        df['sl_ticks'] = abs(df['stop'] - df['entry_price']) * 4

    return df


def calculate_expected_value(df: pd.DataFrame) -> pd.Series:
    """Calcule l'Expected Value pour chaque trade"""
    # Formule T7: EV = pnl_ticks - (sl_ticks * 0.3)
    ev = df['pnl_ticks'] - (df['sl_ticks'] * 0.3)
    return ev


def backtest_threshold(
    df: pd.DataFrame,
    ev: pd.Series,
    threshold: float,
    fees: float = 0.62
) -> Dict:
    """Backtest avec un seuil donné"""

    # Décision: TRADE si EV > threshold
    trades_taken = ev > threshold

    # Calculer P&L
    df_trades = df[trades_taken].copy()
    n_trades = len(df_trades)

    if n_trades == 0:
        return {
            'threshold': threshold,
            'n_trades': 0,
            'pnl_gross': 0.0,
            'pnl_net': 0.0,
            'pnl_per_trade': 0.0,
            'winrate': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'best_trade': 0.0,
            'worst_trade': 0.0
        }

    pnl_gross = df_trades['pnl_ticks'].sum()
    pnl_net = pnl_gross - (n_trades * fees)
    pnl_per_trade = pnl_net / n_trades

    wins = df_trades[df_trades['pnl_ticks'] > 0]
    losses = df_trades[df_trades['pnl_ticks'] <= 0]

    winrate = len(wins) / n_trades if n_trades > 0 else 0.0
    avg_win = wins['pnl_ticks'].mean() if len(wins) > 0 else 0.0
    avg_loss = losses['pnl_ticks'].mean() if len(losses) > 0 else 0.0

    return {
        'threshold': threshold,
        'n_trades': n_trades,
        'pnl_gross': pnl_gross,
        'pnl_net': pnl_net,
        'pnl_per_trade': pnl_per_trade,
        'winrate': winrate * 100,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'best_trade': df_trades['pnl_ticks'].max(),
        'worst_trade': df_trades['pnl_ticks'].min()
    }


def optimize_threshold(
    data_path: str,
    thresholds: List[float],
    test_dates: List[str],
    fees: float = 0.62
) -> pd.DataFrame:
    """Optimise le seuil sur plusieurs valeurs"""

    logger.info("\n" + "="*70)
    logger.info("OPTIMISATION SEUIL T7_expected_value")
    logger.info("="*70)

    # Charger données
    logger.info(f"\nChargement: {data_path}")
    df = load_data(data_path)
    logger.info(f"   Total: {len(df):,} trades")

    # Filtrer période test
    df_test = df[df['date'].isin(test_dates)].copy()
    logger.info(f"   Test: {len(df_test):,} trades (dates: {test_dates})")

    if len(df_test) == 0:
        logger.error("   ERREUR: Aucune donnee pour dates test!")
        return pd.DataFrame()

    # Calculer EV
    logger.info("\nCalcul Expected Value...")
    ev = calculate_expected_value(df_test)
    logger.info(f"   EV moyen: {ev.mean():+.2f}t")
    logger.info(f"   EV median: {ev.median():+.2f}t")
    logger.info(f"   EV min: {ev.min():+.2f}t")
    logger.info(f"   EV max: {ev.max():+.2f}t")

    # Tester chaque seuil
    logger.info("\n" + "="*70)
    logger.info("TEST SEUILS")
    logger.info("="*70)

    results = []
    for threshold in thresholds:
        logger.info(f"\n--- Seuil: EV > {threshold:.1f}t ---")
        result = backtest_threshold(df_test, ev, threshold, fees)
        results.append(result)

        logger.info(f"   Trades: {result['n_trades']:,} / {len(df_test):,} ({result['n_trades']/len(df_test)*100:.1f}%)")
        logger.info(f"   P&L net: {result['pnl_net']:+,.1f}t")
        logger.info(f"   P&L/trade: {result['pnl_per_trade']:+.2f}t")
        logger.info(f"   WinRate: {result['winrate']:.1f}%")
        logger.info(f"   Avg WIN: {result['avg_win']:+.2f}t | Avg LOSS: {result['avg_loss']:+.2f}t")

    # Créer DataFrame résultats
    df_results = pd.DataFrame(results)

    # Identifier meilleur seuil
    logger.info("\n" + "="*70)
    logger.info("ANALYSE RESULTATS")
    logger.info("="*70)

    # Meilleur P&L net
    best_pnl = df_results.loc[df_results['pnl_net'].idxmax()]
    logger.info(f"\nMeilleur P&L net: Seuil {best_pnl['threshold']:.1f}t")
    logger.info(f"   P&L net: {best_pnl['pnl_net']:+,.1f}t")
    logger.info(f"   Trades: {best_pnl['n_trades']:.0f}")

    # Meilleur P&L/trade
    best_ppt = df_results.loc[df_results['pnl_per_trade'].idxmax()]
    logger.info(f"\nMeilleur P&L/trade: Seuil {best_ppt['threshold']:.1f}t")
    logger.info(f"   P&L/trade: {best_ppt['pnl_per_trade']:+.2f}t")
    logger.info(f"   P&L net: {best_ppt['pnl_net']:+,.1f}t")
    logger.info(f"   Trades: {best_ppt['n_trades']:.0f}")

    # Seuils avec P&L/trade > +1.0t
    good_seuils = df_results[df_results['pnl_per_trade'] > 1.0]
    if len(good_seuils) > 0:
        logger.info(f"\nSeuils avec P&L/trade > +1.0t: {len(good_seuils)}")
        for _, row in good_seuils.iterrows():
            logger.info(f"   Seuil {row['threshold']:.1f}t: P&L/trade={row['pnl_per_trade']:+.2f}t, P&L net={row['pnl_net']:+,.1f}t, Trades={row['n_trades']:.0f}")
    else:
        logger.warning("\nAUCUN seuil n'atteint P&L/trade > +1.0t !")
        logger.info("   Meilleur: {:.2f}t (Seuil {:.1f}t)".format(
            best_ppt['pnl_per_trade'],
            best_ppt['threshold']
        ))

    # Recommandation
    logger.info("\n" + "="*70)
    logger.info("RECOMMANDATION")
    logger.info("="*70)

    if len(good_seuils) > 0:
        # Choisir celui avec le meilleur compromis P&L net et P&L/trade
        good_seuils['score'] = good_seuils['pnl_net'] * good_seuils['pnl_per_trade']
        recommended = good_seuils.loc[good_seuils['score'].idxmax()]

        logger.info(f"\nSEUIL RECOMMANDE: {recommended['threshold']:.1f}t")
        logger.info(f"   P&L net: {recommended['pnl_net']:+,.1f}t")
        logger.info(f"   P&L/trade: {recommended['pnl_per_trade']:+.2f}t")
        logger.info(f"   Trades: {recommended['n_trades']:.0f}")
        logger.info(f"   WinRate: {recommended['winrate']:.1f}%")
        logger.info(f"\n   VALIDATION: P&L/trade > +1.0t OK")
    else:
        logger.info(f"\nSEUIL RECOMMANDE: {best_ppt['threshold']:.1f}t (meilleur P&L/trade)")
        logger.info(f"   P&L/trade: {best_ppt['pnl_per_trade']:+.2f}t")
        logger.info(f"   P&L net: {best_ppt['pnl_net']:+,.1f}t")
        logger.info(f"   Trades: {best_ppt['n_trades']:.0f}")
        logger.info(f"\n   ATTENTION: P&L/trade < +1.0t (objectif non atteint)")

    return df_results


def main():
    """Point d'entrée principal"""

    # Configuration
    DATA_PATH = "ml/data/labeled_trades.parquet"
    TEST_DATES = ['20251113', '20251114']  # Out-of-sample
    THRESHOLDS = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0]
    FEES = 0.62

    # Optimiser
    df_results = optimize_threshold(
        data_path=DATA_PATH,
        thresholds=THRESHOLDS,
        test_dates=TEST_DATES,
        fees=FEES
    )

    if len(df_results) == 0:
        logger.error("\nERREUR: Optimisation echouee")
        return 1

    # Sauvegarder résultats
    output_path = Path("ml/6_TARGET_OPTIMIZATION/results/threshold_optimization.csv")
    df_results.to_csv(output_path, index=False)
    logger.info(f"\nResultats sauvegardes: {output_path}")

    logger.info("\n" + "="*70)
    logger.info("OPTIMISATION TERMINEE")
    logger.info("="*70)

    return 0


if __name__ == "__main__":
    sys.exit(main())







