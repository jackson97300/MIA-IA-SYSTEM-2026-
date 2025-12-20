"""
AUDIT CRITIQUE: Vérification des Résultats de Backtest
======================================================

PROBLÈME: Résultats trop beaux pour être vrais
- WinRate 87% ES, 76% NQ → SUSPECT
- P&L +2.5t/trade ES, +4.0t/trade NQ → IRRÉALISTE

HYPOTHÈSES À VÉRIFIER:
1. Biais de Look-Ahead (utilise données futures)
2. Logique de simulation incorrecte
3. Données déjà optimisées (overfitting)
4. MFE/MAE mal interprétés
5. Fees non appliqués correctement

Date: 15 Novembre 2025
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def audit_data_quality(df):
    """Audit 1: Qualité des données"""
    logger.info("=" * 80)
    logger.info("AUDIT 1: QUALITÉ DES DONNÉES")
    logger.info("=" * 80)
    logger.info("")

    # Vérifier colonnes essentielles
    required_cols = ['symbol', 'entry_price', 'stop', 'target', 'mae', 'mfe', 'pnl_ticks', 'win']
    missing = [col for col in required_cols if col not in df.columns]

    if missing:
        logger.error(f"ERREUR: Colonnes manquantes: {missing}")
        return False

    logger.info("✅ Toutes les colonnes requises sont présentes")
    logger.info("")

    # Vérifier cohérence MAE/MFE
    logger.info("Vérification cohérence MAE/MFE:")
    logger.info(f"  MAE min: {df['mae'].min():.2f}, max: {df['mae'].max():.2f}, mean: {df['mae'].mean():.2f}")
    logger.info(f"  MFE min: {df['mfe'].min():.2f}, max: {df['mfe'].max():.2f}, mean: {df['mfe'].mean():.2f}")

    # Valeurs négatives?
    neg_mae = (df['mae'] < 0).sum()
    neg_mfe = (df['mfe'] < 0).sum()

    if neg_mae > 0:
        logger.warning(f"⚠️ {neg_mae} trades avec MAE négatif (suspect!)")
    else:
        logger.info("✅ Pas de MAE négatif")

    if neg_mfe > 0:
        logger.warning(f"⚠️ {neg_mfe} trades avec MFE négatif (suspect!)")
    else:
        logger.info("✅ Pas de MFE négatif")

    logger.info("")

    # Vérifier cohérence WIN vs P&L
    wins_by_flag = df['win'].sum()
    wins_by_pnl = (df['pnl_ticks'] > 0).sum()

    logger.info(f"Cohérence WIN vs P&L:")
    logger.info(f"  Wins selon flag 'win': {wins_by_flag}")
    logger.info(f"  Wins selon pnl_ticks > 0: {wins_by_pnl}")
    logger.info(f"  Différence: {abs(wins_by_flag - wins_by_pnl)}")

    if abs(wins_by_flag - wins_by_pnl) > 10:
        logger.warning("⚠️ Incohérence entre flag 'win' et pnl_ticks!")
    else:
        logger.info("✅ Cohérence acceptable")

    logger.info("")
    return True


def audit_simulation_logic():
    """Audit 2: Logique de simulation"""
    logger.info("=" * 80)
    logger.info("AUDIT 2: LOGIQUE DE SIMULATION")
    logger.info("=" * 80)
    logger.info("")

    logger.info("PROBLÈME IDENTIFIÉ:")
    logger.info("")
    logger.info("  La simulation utilise MAE et MFE comme si c'étaient des")
    logger.info("  'maximum absolus' atteints pendant le trade.")
    logger.info("")
    logger.info("  MAIS: Si MAE = 10t et MFE = 20t, cela signifie:")
    logger.info("  - Le prix a bougé de -10t contre nous (MAE)")
    logger.info("  - Le prix a bougé de +20t en notre faveur (MFE)")
    logger.info("")
    logger.info("  ⚠️ PROBLÈME: On ne sait PAS dans quel ORDRE!")
    logger.info("")
    logger.info("  Scénario A: MFE d'abord, puis MAE")
    logger.info("    → Prix monte à +20t (TP atteint!), puis redescend à -10t")
    logger.info("    → Trade gagnant si TP = 16t")
    logger.info("")
    logger.info("  Scénario B: MAE d'abord, puis MFE")
    logger.info("    → Prix descend à -10t, puis remonte à +20t")
    logger.info("    → Trade gagnant si SL > 10t ET TP < 20t")
    logger.info("")
    logger.info("  🔴 NOTRE SIMULATION ASSUME TOUJOURS LE MEILLEUR SCÉNARIO!")
    logger.info("     → Si MFE >= TP → WIN (même si MAE >= SL atteint avant)")
    logger.info("     → BIAIS OPTIMISTE MASSIF!")
    logger.info("")
    return False


def audit_realistic_simulation(df):
    """Audit 3: Simulation réaliste (pire cas)"""
    logger.info("=" * 80)
    logger.info("AUDIT 3: SIMULATION RÉALISTE (Approche conservatrice)")
    logger.info("=" * 80)
    logger.info("")

    logger.info("HYPOTHÈSE CONSERVATRICE:")
    logger.info("  Si MAE >= SL ET MFE >= TP:")
    logger.info("    → On ne sait pas lequel est touché en premier")
    logger.info("    → Approche prudente: Assumer 50/50 (ou SL d'abord)")
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

        # Catégoriser les trades
        category_counts = {
            'tp_only': 0,      # MFE >= TP et MAE < SL → WIN certain
            'sl_only': 0,      # MAE >= SL et MFE < TP → LOSS certain
            'both': 0,         # MAE >= SL ET MFE >= TP → INCERTAIN
            'neither': 0       # MAE < SL et MFE < TP → Timeout
        }

        wins_optimistic = 0
        wins_pessimistic = 0
        wins_realistic = 0

        pnl_optimistic = 0
        pnl_pessimistic = 0
        pnl_realistic = 0

        for idx, row in df_sym.iterrows():
            mfe = row['mfe']
            mae = row['mae']

            hit_tp = mfe >= tp_opt
            hit_sl = mae >= sl_opt

            if hit_tp and not hit_sl:
                # TP atteint, SL pas touché → WIN certain
                category_counts['tp_only'] += 1
                pnl = tp_opt - fees
                wins_optimistic += 1
                wins_pessimistic += 1
                wins_realistic += 1
                pnl_optimistic += pnl
                pnl_pessimistic += pnl
                pnl_realistic += pnl

            elif hit_sl and not hit_tp:
                # SL atteint, TP pas touché → LOSS certain
                category_counts['sl_only'] += 1
                pnl = -sl_opt - fees
                pnl_optimistic += pnl
                pnl_pessimistic += pnl
                pnl_realistic += pnl

            elif hit_tp and hit_sl:
                # Les DEUX touchés → INCERTAIN!
                category_counts['both'] += 1

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
                category_counts['neither'] += 1
                # Exit à MFE si positif, sinon MAE
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
            'n_trades': n_trades,
            'categories': category_counts,
            'winrate_optimistic': wins_optimistic / n_trades,
            'winrate_pessimistic': wins_pessimistic / n_trades,
            'winrate_realistic': wins_realistic / n_trades,
            'pnl_optimistic': pnl_optimistic / n_trades,
            'pnl_pessimistic': pnl_pessimistic / n_trades,
            'pnl_realistic': pnl_realistic / n_trades
        }

        logger.info(f"{'=' * 35} {symbol} {'=' * 35}")
        logger.info("")
        logger.info(f"  Total trades: {n_trades}")
        logger.info("")
        logger.info("  CATÉGORIES:")
        logger.info(f"    TP atteint seul:     {category_counts['tp_only']:5d} ({category_counts['tp_only']/n_trades*100:5.1f}%) → WIN certain")
        logger.info(f"    SL atteint seul:     {category_counts['sl_only']:5d} ({category_counts['sl_only']/n_trades*100:5.1f}%) → LOSS certain")
        logger.info(f"    TP ET SL touchés:    {category_counts['both']:5d} ({category_counts['both']/n_trades*100:5.1f}%) → INCERTAIN! 🔴")
        logger.info(f"    Ni TP ni SL:         {category_counts['neither']:5d} ({category_counts['neither']/n_trades*100:5.1f}%) → Timeout")
        logger.info("")
        logger.info("  RÉSULTATS:")
        logger.info(f"    Optimiste (TP d'abord):    WR {results[symbol]['winrate_optimistic']*100:5.1f}%  |  P&L {results[symbol]['pnl_optimistic']:+.3f} t/trade")
        logger.info(f"    Pessimiste (SL d'abord):   WR {results[symbol]['winrate_pessimistic']*100:5.1f}%  |  P&L {results[symbol]['pnl_pessimistic']:+.3f} t/trade")
        logger.info(f"    Réaliste (50/50):          WR {results[symbol]['winrate_realistic']*100:5.1f}%  |  P&L {results[symbol]['pnl_realistic']:+.3f} t/trade")
        logger.info("")

    logger.info("=" * 80)
    logger.info("")

    return results


def audit_actual_performance(df):
    """Audit 4: Performance RÉELLE historique"""
    logger.info("=" * 80)
    logger.info("AUDIT 4: PERFORMANCE RÉELLE HISTORIQUE (Baseline)")
    logger.info("=" * 80)
    logger.info("")

    logger.info("Ces trades ont DÉJÀ été exécutés avec TP/SL variables.")
    logger.info("Voyons la performance RÉELLE:")
    logger.info("")

    for symbol in ['ES', 'NQ']:
        df_sym = df[df['symbol'] == symbol]

        n_trades = len(df_sym)
        n_win = df_sym['win'].sum()
        winrate = n_win / n_trades

        pnl_net = df_sym['pnl_ticks'].sum()
        pnl_per_trade = pnl_net / n_trades

        avg_sl = df_sym['sl_ticks_actual'].mean()
        avg_tp = df_sym['tp_ticks_actual'].mean()

        logger.info(f"  {symbol}:")
        logger.info(f"    Trades:       {n_trades}")
        logger.info(f"    WinRate:      {winrate*100:.1f}%")
        logger.info(f"    P&L/trade:    {pnl_per_trade:+.3f} ticks")
        logger.info(f"    Avg SL:       {avg_sl:.1f} ticks")
        logger.info(f"    Avg TP:       {avg_tp:.1f} ticks")
        logger.info("")

    logger.info("=" * 80)
    logger.info("")


def generate_audit_report(df, realistic_results):
    """Génère rapport d'audit final"""
    logger.info("=" * 80)
    logger.info("RAPPORT D'AUDIT FINAL")
    logger.info("=" * 80)
    logger.info("")

    logger.info("CONCLUSION:")
    logger.info("")
    logger.info("1. ❌ SIMULATION INITIALE TROP OPTIMISTE")
    logger.info("   - Assumait toujours TP atteint avant SL")
    logger.info("   - Résultats irréalistes: WR 87% ES, 76% NQ")
    logger.info("")

    logger.info("2. 🔴 PROBLÈME MAJEUR: Trades avec TP ET SL touchés")

    for symbol in ['ES', 'NQ']:
        pct_both = realistic_results[symbol]['categories']['both'] / realistic_results[symbol]['n_trades'] * 100
        logger.info(f"   - {symbol}: {realistic_results[symbol]['categories']['both']} trades ({pct_both:.1f}%) où ordre inconnu")

    logger.info("")
    logger.info("3. ✅ RÉSULTATS RÉALISTES (Approche conservatrice 50/50):")
    logger.info("")

    for symbol in ['ES', 'NQ']:
        r = realistic_results[symbol]
        logger.info(f"   {symbol}:")
        logger.info(f"     WinRate:    {r['winrate_realistic']*100:.1f}%")
        logger.info(f"     P&L/trade:  {r['pnl_realistic']:+.3f} ticks")
        logger.info("")

    # Comparer avec objectifs
    logger.info("4. 📊 VS OBJECTIFS INITIAUX:")
    logger.info("")
    logger.info("   ES:")
    logger.info(f"     Objectif:   +0.397 t/trade")
    logger.info(f"     Réaliste:   {realistic_results['ES']['pnl_realistic']:+.3f} t/trade")
    diff_es = realistic_results['ES']['pnl_realistic'] - 0.397
    logger.info(f"     Différence: {diff_es:+.3f} t/trade")
    logger.info("")

    logger.info("   NQ:")
    logger.info(f"     Objectif:   +1.528 t/trade")
    logger.info(f"     Réaliste:   {realistic_results['NQ']['pnl_realistic']:+.3f} t/trade")
    diff_nq = realistic_results['NQ']['pnl_realistic'] - 1.528
    logger.info(f"     Différence: {diff_nq:+.3f} t/trade")
    logger.info("")

    logger.info("5. 🎯 RECOMMANDATION FINALE:")
    logger.info("")

    if realistic_results['ES']['pnl_realistic'] > 0.3 and realistic_results['NQ']['pnl_realistic'] > 1.0:
        logger.info("   ✅ LANCER EN PRODUCTION")
        logger.info("   - Performance réaliste reste POSITIVE")
        logger.info("   - Même avec approche conservatrice")
    elif realistic_results['ES']['pnl_realistic'] > 0 and realistic_results['NQ']['pnl_realistic'] > 0:
        logger.info("   ⚠️ TESTER AVEC PRUDENCE")
        logger.info("   - Performance positive mais marginale")
        logger.info("   - Monitorer de près les premiers jours")
    else:
        logger.info("   ❌ NE PAS LANCER")
        logger.info("   - Performance réaliste négative ou nulle")
        logger.info("   - Revoir configuration")

    logger.info("")
    logger.info("=" * 80)


def main():
    """Fonction principale d'audit"""
    logger.info("")
    logger.info("=" * 80)
    logger.info("AUDIT CRITIQUE: BACKTEST TP/SL OPTIMAUX")
    logger.info("=" * 80)
    logger.info("")
    logger.info("Objectif: Vérifier si résultats sont réalistes ou biaisés")
    logger.info("")

    # Charger données
    data_path = Path("ml/data/labeled_trades.parquet")
    df = pd.read_parquet(data_path)
    df = df[df['symbol'].isin(['ES', 'NQ'])].copy()

    # Calculer SL/TP actuels
    df['sl_ticks_actual'] = ((df['entry_price'] - df['stop']).abs() / 0.25).astype(int)
    df['tp_ticks_actual'] = ((df['target'] - df['entry_price']).abs() / 0.25).astype(int)

    logger.info(f"Données chargées: {len(df)} trades (ES + NQ)")
    logger.info("")

    # Audits
    audit_data_quality(df)
    audit_simulation_logic()
    realistic_results = audit_realistic_simulation(df)
    audit_actual_performance(df)
    generate_audit_report(df, realistic_results)

    # Sauvegarder rapport
    # (Les logs sont déjà affichés, pas besoin de fichier séparé)


if __name__ == "__main__":
    main()







