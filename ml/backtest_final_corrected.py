"""
BACKTEST CORRIGÉ: TP/SL Optimaux avec MAE/MFE SIGNÉS
=====================================================

CORRECTION: MAE/MFE sont SIGNÉS, pas absolus!
- MAE négatif = mouvement défavorable
- MFE positif = mouvement favorable

On doit prendre abs(MAE) pour comparer avec SL

Date: 15 Novembre 2025
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def backtest_corrected():
    """Backtest CORRIGÉ avec MAE/MFE signés"""
    logger.info("=" * 90)
    logger.info("BACKTEST CORRIGÉ: TP/SL OPTIMAUX")
    logger.info("=" * 90)
    logger.info("")

    # Charger données
    df = pd.read_parquet("ml/data/labeled_trades.parquet")
    df = df[df['symbol'].isin(['ES', 'NQ'])].copy()

    logger.info(f"Données: {len(df)} trades (ES + NQ)")
    logger.info("")

    # Configuration optimale
    config = {
        'ES': {'sl': 12, 'tp': 16, 'fees': 0.12},
        'NQ': {'sl': 12, 'tp': 23, 'fees': 0.28}
    }

    results = {}

    for symbol in ['ES', 'NQ']:
        df_sym = df[df['symbol'] == symbol].copy()
        sl_opt = config[symbol]['sl']
        tp_opt = config[symbol]['tp']
        fees = config[symbol]['fees']

        # Catégoriser trades
        tp_only = 0
        sl_only = 0
        both = 0
        neither = 0

        wins_optimistic = 0
        wins_pessimistic = 0
        wins_realistic = 0

        pnl_optimistic = 0
        pnl_pessimistic = 0
        pnl_realistic = 0

        for idx, row in df_sym.iterrows():
            # ✅ CORRECTION: Utiliser abs() pour MAE car il est SIGNÉ
            mfe = abs(row['mfe'])  # Maximum Favorable (toujours ≥ 0)
            mae = abs(row['mae'])  # Maximum Adverse (prendre valeur absolue!)

            hit_tp = mfe >= tp_opt
            hit_sl = mae >= sl_opt

            if hit_tp and not hit_sl:
                # TP atteint, SL pas touché → WIN certain
                tp_only += 1
                pnl = tp_opt - fees
                wins_optimistic += 1
                wins_pessimistic += 1
                wins_realistic += 1
                pnl_optimistic += pnl
                pnl_pessimistic += pnl
                pnl_realistic += pnl

            elif hit_sl and not hit_tp:
                # SL atteint, TP pas touché → LOSS certain
                sl_only += 1
                pnl = -sl_opt - fees
                pnl_optimistic += pnl
                pnl_pessimistic += pnl
                pnl_realistic += pnl

            elif hit_tp and hit_sl:
                # Les DEUX touchés → INCERTAIN!
                both += 1

                # Optimiste: TP d'abord
                pnl_opt = tp_opt - fees
                wins_optimistic += 1
                pnl_optimistic += pnl_opt

                # Pessimiste: SL d'abord
                pnl_pess = -sl_opt - fees
                pnl_pessimistic += pnl_pess

                # Réaliste: 50/50
                pnl_real = (pnl_opt + pnl_pess) / 2
                wins_realistic += 0.5
                pnl_realistic += pnl_real

            else:
                # Ni TP ni SL → Timeout
                neither += 1
                # Exit à MFE si positif, sinon -MAE
                if mfe > 0:
                    pnl = min(mfe, tp_opt * 0.5) - fees
                    if pnl > 0:
                        wins_optimistic += 1
                        wins_pessimistic += 1
                        wins_realistic += 1
                else:
                    pnl = max(-mae, -sl_opt * 0.5) - fees

                pnl_optimistic += pnl
                pnl_pessimistic += pnl
                pnl_realistic += pnl

        n_trades = len(df_sym)

        results[symbol] = {
            'tp_only': tp_only,
            'sl_only': sl_only,
            'both': both,
            'neither': neither,
            'winrate_opt': wins_optimistic / n_trades,
            'winrate_pess': wins_pessimistic / n_trades,
            'winrate_real': wins_realistic / n_trades,
            'pnl_opt': pnl_optimistic / n_trades,
            'pnl_pess': pnl_pessimistic / n_trades,
            'pnl_real': pnl_realistic / n_trades
        }

        logger.info("=" * 45 + f" {symbol} " + "=" * 45)
        logger.info("")
        logger.info(f"  Total trades: {n_trades}")
        logger.info("")
        logger.info("  CATÉGORIES:")
        logger.info(f"    TP atteint seul (WIN certain):     {tp_only:5d} ({tp_only/n_trades*100:5.1f}%)")
        logger.info(f"    SL atteint seul (LOSS certain):    {sl_only:5d} ({sl_only/n_trades*100:5.1f}%)")
        logger.info(f"    TP ET SL touchés (INCERTAIN):      {both:5d} ({both/n_trades*100:5.1f}%) 🔴")
        logger.info(f"    Ni TP ni SL (Timeout):             {neither:5d} ({neither/n_trades*100:5.1f}%)")
        logger.info("")
        logger.info("  RÉSULTATS:")
        logger.info(f"    Optimiste (TP d'abord):      WR {results[symbol]['winrate_opt']*100:5.1f}%  |  P&L {results[symbol]['pnl_opt']:+.3f} t/trade")
        logger.info(f"    Pessimiste (SL d'abord):     WR {results[symbol]['winrate_pess']*100:5.1f}%  |  P&L {results[symbol]['pnl_pess']:+.3f} t/trade")
        logger.info(f"    Réaliste (50/50):            WR {results[symbol]['winrate_real']*100:5.1f}%  |  P&L {results[symbol]['pnl_real']:+.3f} t/trade")
        logger.info("")

    logger.info("=" * 90)
    logger.info("")
    logger.info("CONCLUSION FINALE:")
    logger.info("")

    # Performance réaliste
    es_real = results['ES']['pnl_real']
    nq_real = results['NQ']['pnl_real']

    logger.info("  PERFORMANCE RÉALISTE (Approche conservatrice 50/50):")
    logger.info(f"    ES: {es_real:+.3f} t/trade (Objectif: +0.397t)")
    logger.info(f"    NQ: {nq_real:+.3f} t/trade (Objectif: +1.528t)")
    logger.info("")

    # Comparaison avec objectifs
    if es_real >= 0.397 and nq_real >= 1.528:
        logger.info("  ✅ OBJECTIFS ATTEINTS!")
        logger.info("  ✅ LANCER EN PRODUCTION")
    elif es_real > 0.2 and nq_real > 1.0:
        logger.info("  ⚠️ PERFORMANCE ACCEPTABLE")
        logger.info("  ⚠️ LANCER AVEC MONITORING SERRÉ")
    else:
        logger.info("  ❌ PERFORMANCE INSUFFISANTE")
        logger.info("  ❌ NE PAS LANCER / REVOIR CONFIG")

    logger.info("")
    logger.info("=" * 90)

    return results


if __name__ == "__main__":
    backtest_corrected()







