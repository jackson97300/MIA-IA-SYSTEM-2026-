#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
AUDIT CYCLES DE MARCHÉ & HORIZONS DE PRÉDICTION
═══════════════════════════════════════════════════════════════════════════════

Objectif : Déterminer empiriquement sur VOS données :
1. Durée typique des cycles/mouvements de prix
2. Horizon optimal de prédiction (prévisibilité)
3. Corrélation features → labels selon l'horizon
4. Temps de "maturité" d'un setup

Auteur : MIA_IA_SYSTEM
Date : 5 Novembre 2025
═══════════════════════════════════════════════════════════════════════════════
"""

import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats
from scipy.signal import find_peaks

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Style plots
sns.set_style("darkgrid")
plt.rcParams['figure.figsize'] = (16, 10)


class MarketCycleAuditor:
    """
    Auditeur de cycles de marché pour déterminer l'horizon optimal
    """

    def __init__(self, data_path: str, symbol: str, atr_multiplier: float = 0.45):
        """
        Args:
            data_path: Chemin vers ML_READY/*.jsonl
            symbol: ES, NQ, ou RTY
            atr_multiplier: Multiplicateur ATR pour définir un "mouvement significatif"
        """
        self.data_path = Path(data_path)
        self.symbol = symbol
        self.atr_multiplier = atr_multiplier
        self.df = None

        logger.info(f"🔍 MarketCycleAuditor initialisé pour {symbol}")
        logger.info(f"   📂 Data: {data_path}")
        logger.info(f"   📊 ATR multiplier: {atr_multiplier}")

    def load_data(self, max_files: int = 50, additional_paths: list = None) -> pd.DataFrame:
        """Charge les données JSONL (supporte plusieurs dates)"""
        logger.info(f"\n📥 Chargement des données...")

        # Collecter fichiers du chemin principal
        files = sorted(self.data_path.glob("*.jsonl"))[:max_files]

        # Ajouter fichiers des chemins additionnels
        if additional_paths:
            for add_path in additional_paths:
                add_path = Path(add_path)
                if add_path.exists():
                    files.extend(sorted(add_path.glob("*.jsonl"))[:max_files])
                    logger.info(f"   ➕ Ajout: {add_path}")

        if not files:
            raise FileNotFoundError(f"Aucun fichier .jsonl trouvé dans {self.data_path}")

        logger.info(f"   ✅ {len(files)} fichiers trouvés (toutes dates)")

        data_list = []
        for file in files:
            with open(file, 'r') as f:
                for line in f:
                    try:
                        data_list.append(json.loads(line))
                    except:
                        continue

        df = pd.DataFrame(data_list)
        logger.info(f"   ✅ {len(df)} samples chargés")

        # Tri chronologique
        if 't_ms' in df.columns:
            df = df.sort_values('t_ms').reset_index(drop=True)
            df['timestamp'] = pd.to_datetime(df['t_ms'], unit='ms')
        elif 'tsec' in df.columns:
            df = df.sort_values('tsec').reset_index(drop=True)
            df['timestamp'] = pd.to_datetime(df['tsec'], unit='s')

        self.df = df
        return df

    def analyze_price_cycles(self) -> Dict:
        """
        Analyse 1 : Durée des cycles de prix (swing high → swing low)

        Méthode :
        - Détecte les sommets (peaks) et creux (troughs)
        - Mesure la durée entre chaque renversement
        - Statistiques sur les cycles
        """
        logger.info(f"\n{'='*70}")
        logger.info(f"📊 ANALYSE 1 : DURÉE DES CYCLES DE PRIX")
        logger.info(f"{'='*70}")

        price = self.df['mid'].values
        time_diff = self.df['timestamp'].diff().dt.total_seconds().fillna(60)

        # Détection des peaks/troughs (sur 5 barres de chaque côté)
        peaks, _ = find_peaks(price, distance=5, prominence=self.df['atr'].mean() * 0.3)
        troughs, _ = find_peaks(-price, distance=5, prominence=self.df['atr'].mean() * 0.3)

        logger.info(f"   🔺 {len(peaks)} sommets détectés")
        logger.info(f"   🔻 {len(troughs)} creux détectés")

        # Combine et trie peaks/troughs
        turning_points = sorted(list(peaks) + list(troughs))

        # Calcul durées entre renversements
        cycle_durations = []
        for i in range(len(turning_points) - 1):
            idx_start = turning_points[i]
            idx_end = turning_points[i+1]

            # Durée en secondes
            duration = (self.df.iloc[idx_end]['timestamp'] -
                       self.df.iloc[idx_start]['timestamp']).total_seconds()

            cycle_durations.append(duration)

        cycle_durations = np.array(cycle_durations)

        # Statistiques
        stats_dict = {
            'mean': np.mean(cycle_durations),
            'median': np.median(cycle_durations),
            'std': np.std(cycle_durations),
            'min': np.min(cycle_durations),
            'max': np.max(cycle_durations),
            'p25': np.percentile(cycle_durations, 25),
            'p75': np.percentile(cycle_durations, 75),
            'p90': np.percentile(cycle_durations, 90),
        }

        logger.info(f"\n   📈 STATISTIQUES DES CYCLES (secondes) :")
        logger.info(f"      Moyenne    : {stats_dict['mean']:.0f}s ({stats_dict['mean']/60:.1f} min)")
        logger.info(f"      Médiane    : {stats_dict['median']:.0f}s ({stats_dict['median']/60:.1f} min)")
        logger.info(f"      Écart-type : {stats_dict['std']:.0f}s")
        logger.info(f"      Min/Max    : {stats_dict['min']:.0f}s / {stats_dict['max']:.0f}s")
        logger.info(f"      P25/P75    : {stats_dict['p25']:.0f}s / {stats_dict['p75']:.0f}s")
        logger.info(f"      P90        : {stats_dict['p90']:.0f}s ({stats_dict['p90']/60:.1f} min)")

        # Distribution
        logger.info(f"\n   📊 DISTRIBUTION DES CYCLES :")
        logger.info(f"      < 3 min   : {np.sum(cycle_durations < 180) / len(cycle_durations) * 100:.1f}%")
        logger.info(f"      3-5 min   : {np.sum((cycle_durations >= 180) & (cycle_durations < 300)) / len(cycle_durations) * 100:.1f}%")
        logger.info(f"      5-10 min  : {np.sum((cycle_durations >= 300) & (cycle_durations < 600)) / len(cycle_durations) * 100:.1f}%")
        logger.info(f"      10-15 min : {np.sum((cycle_durations >= 600) & (cycle_durations < 900)) / len(cycle_durations) * 100:.1f}%")
        logger.info(f"      > 15 min  : {np.sum(cycle_durations >= 900) / len(cycle_durations) * 100:.1f}%")

        # Interprétation
        logger.info(f"\n   💡 INTERPRÉTATION :")
        if stats_dict['median'] < 240:
            logger.info(f"      ⚡ Cycles COURTS (< 4 min) → Marché rapide, privilégier horizon 3-5 min")
        elif stats_dict['median'] < 420:
            logger.info(f"      ⚖️  Cycles MOYENS (4-7 min) → Équilibre, horizon 5 min optimal")
        else:
            logger.info(f"      🐢 Cycles LONGS (> 7 min) → Marché lent, horizon 10-15 min acceptable")

        return {
            'cycle_durations': cycle_durations,
            'stats': stats_dict,
            'turning_points': turning_points
        }

    def analyze_predictability_by_horizon(self, horizons: List[int] = [60, 120, 180, 300, 600, 900, 1200]) -> Dict:
        """
        Analyse 2 : Prévisibilité selon l'horizon

        Mesure pour chaque horizon :
        - % de mouvements significatifs (> ATR × multiplier)
        - Autocorrélation des returns
        - Stabilité de la direction
        """
        logger.info(f"\n{'='*70}")
        logger.info(f"🔮 ANALYSE 2 : PRÉVISIBILITÉ SELON L'HORIZON")
        logger.info(f"{'='*70}")

        results = {}

        for horizon in horizons:
            logger.info(f"\n   ⏱️  Horizon {horizon}s ({horizon/60:.1f} min) :")

            # Calcul des returns futurs
            future_price = self.df['mid'].shift(-int(horizon / 60))  # Approximation: 1 row = 60s
            current_price = self.df['mid']

            returns = (future_price - current_price).dropna()

            # Seuil de mouvement significatif
            threshold = self.df['atr'].mean() * self.atr_multiplier

            # Stats
            pct_up = (returns > threshold).sum() / len(returns) * 100
            pct_down = (returns < -threshold).sum() / len(returns) * 100
            pct_flat = ((returns >= -threshold) & (returns <= threshold)).sum() / len(returns) * 100

            # Autocorrélation (mesure de prévisibilité)
            autocorr = returns.autocorr()

            # Volatilité des returns
            volatility = returns.std()

            # Ratio signal/noise
            signal_noise_ratio = abs(returns.mean()) / volatility if volatility > 0 else 0

            results[horizon] = {
                'pct_up': pct_up,
                'pct_down': pct_down,
                'pct_flat': pct_flat,
                'autocorr': autocorr,
                'volatility': volatility,
                'signal_noise': signal_noise_ratio,
                'mean_return': returns.mean(),
                'threshold': threshold
            }

            logger.info(f"      UP    : {pct_up:.1f}%")
            logger.info(f"      DOWN  : {pct_down:.1f}%")
            logger.info(f"      FLAT  : {pct_flat:.1f}%")
            logger.info(f"      Autocorr : {autocorr:.3f}")
            logger.info(f"      S/N ratio: {signal_noise_ratio:.3f}")

            # Score de qualité (balance UP/DOWN/FLAT + S/N)
            balance_score = 1 - abs(pct_up - pct_down) / 100  # Proche de 1 = équilibré
            flat_penalty = pct_flat / 100  # Pénalité si trop de FLAT
            quality_score = balance_score * (1 - flat_penalty * 0.5) * signal_noise_ratio

            results[horizon]['quality_score'] = quality_score

            logger.info(f"      📊 Score qualité : {quality_score:.3f}")

        # Trouver l'horizon optimal
        best_horizon = max(results.items(), key=lambda x: x[1]['quality_score'])

        logger.info(f"\n   🏆 HORIZON OPTIMAL : {best_horizon[0]}s ({best_horizon[0]/60:.1f} min)")
        logger.info(f"      Score : {best_horizon[1]['quality_score']:.3f}")
        logger.info(f"      UP/DOWN : {best_horizon[1]['pct_up']:.1f}% / {best_horizon[1]['pct_down']:.1f}%")
        logger.info(f"      FLAT : {best_horizon[1]['pct_flat']:.1f}%")

        return results

    def analyze_feature_correlation_by_horizon(self,
                                               feature_names: List[str] = None,
                                               horizons: List[int] = [180, 300, 600, 900]) -> Dict:
        """
        Analyse 3 : Corrélation features → labels selon l'horizon

        Mesure quelle feature prédit le mieux à quel horizon
        """
        logger.info(f"\n{'='*70}")
        logger.info(f"🔗 ANALYSE 3 : CORRÉLATION FEATURES → LABELS PAR HORIZON")
        logger.info(f"{'='*70}")

        # Features prioritaires pour l'analyse
        if feature_names is None:
            feature_names = [
                'level1_imbalance',
                'depth_imbalance',
                'cum_delta_session',
                'd_vwap_ticks',
                'confluence_proximity',
                'battle_navale_signal_strength',
                'smart_money_flow',
                'institutional_pressure'
            ]

        # Garder seulement les features disponibles
        feature_names = [f for f in feature_names if f in self.df.columns]

        results = {}

        for horizon in horizons:
            logger.info(f"\n   ⏱️  Horizon {horizon}s ({horizon/60:.1f} min) :")

            # Créer les labels
            future_price = self.df['mid'].shift(-int(horizon / 60))
            current_price = self.df['mid']
            returns = future_price - current_price

            threshold = self.df['atr'].mean() * self.atr_multiplier

            labels = np.where(returns > threshold, 1,
                            np.where(returns < -threshold, -1, 0))

            # Corrélations
            correlations = {}
            for feat in feature_names:
                if feat in self.df.columns:
                    corr = np.corrcoef(self.df[feat].fillna(0), labels)[0, 1]
                    correlations[feat] = abs(corr)  # Valeur absolue pour ranking

            # Top 5 features
            top_features = sorted(correlations.items(), key=lambda x: x[1], reverse=True)[:5]

            logger.info(f"      📊 Top 5 features prédictives :")
            for i, (feat, corr) in enumerate(top_features, 1):
                logger.info(f"         {i}. {feat:30s} : {corr:.4f}")

            results[horizon] = {
                'correlations': correlations,
                'top_features': top_features
            }

        return results

    def generate_plots(self,
                      cycle_results: Dict,
                      predictability_results: Dict,
                      output_dir: Path = None):
        """Génère les graphiques d'analyse"""

        if output_dir is None:
            output_dir = Path("ml/audits")
        output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"\n📊 Génération des graphiques...")

        # Plot 1: Distribution des cycles
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))

        cycle_durations = cycle_results['cycle_durations']

        # Histogramme
        axes[0, 0].hist(cycle_durations / 60, bins=50, edgecolor='black', alpha=0.7)
        axes[0, 0].axvline(np.median(cycle_durations) / 60, color='red',
                          linestyle='--', linewidth=2, label=f'Médiane: {np.median(cycle_durations)/60:.1f} min')
        axes[0, 0].set_xlabel('Durée du cycle (minutes)')
        axes[0, 0].set_ylabel('Fréquence')
        axes[0, 0].set_title(f'Distribution des Cycles de Prix - {self.symbol}')
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3)

        # Boxplot
        axes[0, 1].boxplot(cycle_durations / 60, vert=True)
        axes[0, 1].set_ylabel('Durée (minutes)')
        axes[0, 1].set_title('Boxplot des Cycles')
        axes[0, 1].grid(True, alpha=0.3)

        # Plot 2: Qualité par horizon
        horizons = sorted(predictability_results.keys())
        quality_scores = [predictability_results[h]['quality_score'] for h in horizons]
        pct_flat = [predictability_results[h]['pct_flat'] for h in horizons]

        axes[1, 0].plot([h/60 for h in horizons], quality_scores, 'o-', linewidth=2, markersize=8)
        axes[1, 0].set_xlabel('Horizon (minutes)')
        axes[1, 0].set_ylabel('Score Qualité')
        axes[1, 0].set_title('Score de Qualité par Horizon')
        axes[1, 0].grid(True, alpha=0.3)

        # Marquer l'optimal
        best_idx = quality_scores.index(max(quality_scores))
        axes[1, 0].plot(horizons[best_idx]/60, quality_scores[best_idx],
                       'r*', markersize=20, label='Optimal')
        axes[1, 0].legend()

        # Plot 3: Distribution UP/DOWN/FLAT par horizon
        pct_up = [predictability_results[h]['pct_up'] for h in horizons]
        pct_down = [predictability_results[h]['pct_down'] for h in horizons]

        x = np.arange(len(horizons))
        width = 0.25

        axes[1, 1].bar(x - width, pct_up, width, label='UP', color='green', alpha=0.7)
        axes[1, 1].bar(x, pct_down, width, label='DOWN', color='red', alpha=0.7)
        axes[1, 1].bar(x + width, pct_flat, width, label='FLAT', color='gray', alpha=0.7)

        axes[1, 1].set_xlabel('Horizon')
        axes[1, 1].set_ylabel('Pourcentage (%)')
        axes[1, 1].set_title('Distribution UP/DOWN/FLAT par Horizon')
        axes[1, 1].set_xticks(x)
        axes[1, 1].set_xticklabels([f'{h/60:.0f}min' for h in horizons])
        axes[1, 1].legend()
        axes[1, 1].grid(True, alpha=0.3)

        plt.tight_layout()
        output_path = output_dir / f"market_cycles_audit_{self.symbol}.png"
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        logger.info(f"   ✅ Graphique sauvegardé : {output_path}")
        plt.close()

    def generate_report(self,
                       cycle_results: Dict,
                       predictability_results: Dict,
                       feature_results: Dict,
                       output_dir: Path = None) -> str:
        """Génère un rapport textuel complet"""

        if output_dir is None:
            output_dir = Path("ml/audits")
        output_dir.mkdir(parents=True, exist_ok=True)

        report_path = output_dir / f"audit_cycles_{self.symbol}.md"

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(f"# 🔍 AUDIT CYCLES DE MARCHÉ - {self.symbol}\n\n")
            f.write(f"**Date** : {pd.Timestamp.now()}\n")
            f.write(f"**Symbole** : {self.symbol}\n")
            f.write(f"**Samples analysés** : {len(self.df)}\n\n")

            f.write("---\n\n")

            # Résumé cycles
            f.write("## 📊 RÉSUMÉ CYCLES DE PRIX\n\n")
            stats = cycle_results['stats']
            f.write(f"- **Durée moyenne** : {stats['mean']:.0f}s ({stats['mean']/60:.1f} min)\n")
            f.write(f"- **Durée médiane** : {stats['median']:.0f}s ({stats['median']/60:.1f} min)\n")
            f.write(f"- **P25/P75** : {stats['p25']:.0f}s / {stats['p75']:.0f}s\n")
            f.write(f"- **P90** : {stats['p90']:.0f}s ({stats['p90']/60:.1f} min)\n\n")

            # Recommandation horizon
            f.write("## 🎯 HORIZON OPTIMAL RECOMMANDÉ\n\n")

            best_horizon = max(predictability_results.items(),
                             key=lambda x: x[1]['quality_score'])

            f.write(f"### ✅ **{best_horizon[0]}s ({best_horizon[0]/60:.1f} minutes)**\n\n")
            f.write(f"**Justification** :\n")
            f.write(f"- Score qualité : {best_horizon[1]['quality_score']:.3f}\n")
            f.write(f"- Distribution : UP={best_horizon[1]['pct_up']:.1f}% / DOWN={best_horizon[1]['pct_down']:.1f}% / FLAT={best_horizon[1]['pct_flat']:.1f}%\n")
            f.write(f"- Signal/Noise : {best_horizon[1]['signal_noise']:.3f}\n")
            f.write(f"- Autocorrélation : {best_horizon[1]['autocorr']:.3f}\n\n")

            # Comparaison horizons
            f.write("## 📊 COMPARATIF DES HORIZONS\n\n")
            f.write("| Horizon | Score Qualité | UP% | DOWN% | FLAT% | S/N | Autocorr |\n")
            f.write("|---------|---------------|-----|-------|-------|-----|----------|\n")

            for h in sorted(predictability_results.keys()):
                r = predictability_results[h]
                f.write(f"| {h}s ({h/60:.0f}min) | {r['quality_score']:.3f} | "
                       f"{r['pct_up']:.1f}% | {r['pct_down']:.1f}% | {r['pct_flat']:.1f}% | "
                       f"{r['signal_noise']:.3f} | {r['autocorr']:.3f} |\n")

            f.write("\n")

            # Features top par horizon
            f.write("## 🔗 FEATURES LES PLUS PRÉDICTIVES PAR HORIZON\n\n")

            for h in sorted(feature_results.keys()):
                f.write(f"### Horizon {h}s ({h/60:.0f} min)\n\n")
                top = feature_results[h]['top_features']
                for i, (feat, corr) in enumerate(top, 1):
                    f.write(f"{i}. **{feat}** : {corr:.4f}\n")
                f.write("\n")

        logger.info(f"\n   ✅ Rapport sauvegardé : {report_path}")
        return str(report_path)


def main():
    """Fonction principale"""
    import argparse

    parser = argparse.ArgumentParser(description="Audit cycles de marché et horizon optimal")
    parser.add_argument('--symbol', type=str, required=True, choices=['ES', 'NQ', 'RTY'],
                       help='Symbole à analyser')
    parser.add_argument('--data-dir', type=str, required=True,
                       help='Répertoire ML_READY principal')
    parser.add_argument('--additional-dirs', type=str, nargs='+', default=None,
                       help='Répertoires ML_READY additionnels (autres dates)')
    parser.add_argument('--atr-mult', type=float, default=0.45,
                       help='Multiplicateur ATR pour seuil')

    args = parser.parse_args()

    # Créer l'auditeur
    auditor = MarketCycleAuditor(
        data_path=args.data_dir,
        symbol=args.symbol,
        atr_multiplier=args.atr_mult
    )

    # Charger les données (avec chemins additionnels si fournis)
    auditor.load_data(max_files=100, additional_paths=args.additional_dirs)

    # Analyse 1: Cycles de prix
    cycle_results = auditor.analyze_price_cycles()

    # Analyse 2: Prévisibilité par horizon
    predictability_results = auditor.analyze_predictability_by_horizon(
        horizons=[60, 120, 180, 240, 300, 420, 600, 900, 1200, 1800]
    )

    # Analyse 3: Corrélation features
    feature_results = auditor.analyze_feature_correlation_by_horizon()

    # Génération plots
    auditor.generate_plots(cycle_results, predictability_results)

    # Génération rapport
    auditor.generate_report(cycle_results, predictability_results, feature_results)

    logger.info(f"\n{'='*70}")
    logger.info(f"✅ AUDIT TERMINÉ !")
    logger.info(f"{'='*70}")
    logger.info(f"\n📁 Fichiers générés dans ml/audits/")


if __name__ == '__main__':
    main()
