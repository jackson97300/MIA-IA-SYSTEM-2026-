"""
AUDIT COMPLET - DIAGNOSTIC PERFORMANCE DECEVANTE LIGHTGBM
==========================================================

Analyse systematique de tous les composants du pipeline ML pour identifier
les causes de la performance decevante (R2 negatif, correlation nulle).

Sections:
1. Features Training vs Prediction (mismatch?)
2. Data Quality (NaNs, distributions)
3. Feature Engineering (applique correctement?)
4. Scaling/Normalisation (presente?)
5. Target Quality (distribution quality_score)
6. Model Sanity Check (predictions sensees?)
7. Recommendations
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import joblib
import json
import logging
from typing import Dict, List, Set

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ModelAuditor:
    """Audit complet du pipeline ML."""

    def __init__(self):
        self.model_path = Path("ml/models/lightgbm_quality_v1.pkl")
        self.metadata_path = Path("ml/models/lightgbm_quality_v1_metadata.json")
        self.labeled_trades_path = Path("ml/data/labeled_trades.parquet")
        self.aggregated_path = Path("ml/data/ml_ready_aggregated.parquet")
        self.report_path = Path("ml/backtest_results/AUDIT_COMPLET_MODEL.md")

        self.issues = []
        self.warnings = []
        self.recommendations = []

    def run_audit(self):
        """Execute l'audit complet."""
        logger.info("\n" + "="*80)
        logger.info("AUDIT COMPLET - DIAGNOSTIC PERFORMANCE DECEVANTE")
        logger.info("="*80 + "\n")

        # 1. Charger les artefacts
        logger.info("1. CHARGEMENT ARTEFACTS...")
        model, metadata, df_trades, df_agg = self._load_artifacts()

        # 2. Analyser features training vs prediction
        logger.info("\n" + "="*80)
        logger.info("2. AUDIT FEATURES - TRAINING VS PREDICTION")
        logger.info("="*80)
        self._audit_features(metadata, df_trades, df_agg)

        # 3. Analyser data quality
        logger.info("\n" + "="*80)
        logger.info("3. AUDIT DATA QUALITY")
        logger.info("="*80)
        self._audit_data_quality(df_trades)

        # 4. Analyser feature engineering
        logger.info("\n" + "="*80)
        logger.info("4. AUDIT FEATURE ENGINEERING")
        logger.info("="*80)
        self._audit_feature_engineering(df_trades, metadata)

        # 5. Analyser scaling/normalisation
        logger.info("\n" + "="*80)
        logger.info("5. AUDIT SCALING/NORMALISATION")
        logger.info("="*80)
        self._audit_scaling(model, metadata)

        # 6. Analyser target quality
        logger.info("\n" + "="*80)
        logger.info("6. AUDIT TARGET QUALITY")
        logger.info("="*80)
        self._audit_target_quality(df_trades)

        # 7. Sanity check predictions
        logger.info("\n" + "="*80)
        logger.info("7. SANITY CHECK PREDICTIONS")
        logger.info("="*80)
        self._audit_predictions_sanity(model, df_trades, metadata)

        # 8. Generer rapport
        logger.info("\n" + "="*80)
        logger.info("8. GENERATION RAPPORT AUDIT")
        logger.info("="*80)
        self._generate_report()

        logger.info("\n" + "="*80)
        logger.info("AUDIT TERMINE !")
        logger.info("="*80)
        logger.info(f"Rapport sauvegarde: {self.report_path}\n")

    def _load_artifacts(self):
        """Charge tous les artefacts necessaires."""
        # Modele
        model = joblib.load(self.model_path)
        logger.info(f"   Modele charge: {self.model_path}")

        # Metadata
        with open(self.metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        logger.info(f"   Metadata charge: {self.metadata_path}")

        # Trades labelises
        df_trades = pd.read_parquet(self.labeled_trades_path)
        logger.info(f"   Trades labelises: {len(df_trades):,} trades")

        # Agregation ML_READY
        df_agg = pd.read_parquet(self.aggregated_path)
        logger.info(f"   Snapshots agreges: {len(df_agg):,} snapshots")

        return model, metadata, df_trades, df_agg

    def _audit_features(self, metadata: Dict, df_trades: pd.DataFrame, df_agg: pd.DataFrame):
        """Audit des features: training vs prediction."""

        # Features utilisees pour training (depuis metadata)
        features_training = set(metadata.get('feature_names', []))
        logger.info(f"\n   Features TRAINING: {len(features_training)}")

        # Features disponibles dans labeled_trades (utilisees pour prediction)
        features_prediction = set(df_trades.columns) - {'quality_score', 'outcome', 'pnl_ticks',
                                                          'entry_price', 'stop', 'take_profit',
                                                          'mae', 'mfe', 'duration_minutes',
                                                          'date', 'symbol_base', 'source_file',
                                                          'trade_id', 'entry_time', 'exit_time',
                                                          'exit_price', 'tick_size',
                                                          'initial_sl_ticks', 'initial_tp_ticks',
                                                          'final_sl_ticks', 'final_tp_ticks'}
        logger.info(f"   Features PREDICTION: {len(features_prediction)}")

        # Features manquantes
        missing_in_prediction = features_training - features_prediction
        if missing_in_prediction:
            logger.error(f"\n   PROBLEME CRITIQUE: {len(missing_in_prediction)} features MANQUANTES lors prediction !")
            logger.error(f"   Features manquantes (top 20):")
            for i, feat in enumerate(sorted(list(missing_in_prediction))[:20], 1):
                logger.error(f"      {i:2d}. {feat}")
            self.issues.append({
                'severity': 'CRITICAL',
                'category': 'Features Mismatch',
                'description': f"{len(missing_in_prediction)} features utilisees pour training sont ABSENTES lors prediction",
                'features': list(missing_in_prediction)[:50]  # Limiter pour rapport
            })
        else:
            logger.info(f"   OK - Toutes les features training sont presentes")

        # Features en trop (pas grave mais interessant)
        extra_in_prediction = features_prediction - features_training
        if extra_in_prediction:
            logger.warning(f"\n   {len(extra_in_prediction)} features EXTRA dans prediction (non utilisees):")
            for i, feat in enumerate(sorted(list(extra_in_prediction))[:10], 1):
                logger.warning(f"      {i:2d}. {feat}")
            self.warnings.append({
                'severity': 'LOW',
                'category': 'Features Extra',
                'description': f"{len(extra_in_prediction)} features disponibles mais non utilisees",
                'features': list(extra_in_prediction)[:20]
            })

        # Features communes
        common_features = features_training & features_prediction
        logger.info(f"\n   Features COMMUNES: {len(common_features)}")
        coverage_pct = len(common_features) / len(features_training) * 100 if features_training else 0
        logger.info(f"   Coverage: {coverage_pct:.1f}%")

        if coverage_pct < 50:
            self.issues.append({
                'severity': 'CRITICAL',
                'category': 'Low Feature Coverage',
                'description': f"Seulement {coverage_pct:.1f}% des features training sont disponibles pour prediction",
                'value': coverage_pct
            })

    def _audit_data_quality(self, df_trades: pd.DataFrame):
        """Audit de la qualite des donnees."""

        # NaNs par colonne
        nan_counts = df_trades.isnull().sum()
        nan_cols = nan_counts[nan_counts > 0]

        if len(nan_cols) > 0:
            logger.warning(f"\n   {len(nan_cols)} colonnes contiennent des NaNs:")
            for col, count in nan_cols.head(10).items():
                pct = count / len(df_trades) * 100
                logger.warning(f"      {col}: {count:,} ({pct:.1f}%)")

            self.issues.append({
                'severity': 'HIGH',
                'category': 'Missing Values',
                'description': f"{len(nan_cols)} colonnes avec NaNs",
                'top_columns': {col: int(count) for col, count in nan_cols.head(20).items()}
            })
        else:
            logger.info(f"   OK - Aucun NaN detecte")

        # Colonnes constantes (variance nulle)
        numeric_cols = df_trades.select_dtypes(include=[np.number]).columns
        constant_cols = []
        for col in numeric_cols:
            if df_trades[col].nunique() == 1:
                constant_cols.append(col)

        if constant_cols:
            logger.warning(f"\n   {len(constant_cols)} colonnes CONSTANTES (variance nulle):")
            for col in constant_cols[:10]:
                logger.warning(f"      {col}: {df_trades[col].iloc[0]}")

            self.issues.append({
                'severity': 'MEDIUM',
                'category': 'Constant Features',
                'description': f"{len(constant_cols)} features n'ont aucune variance",
                'columns': constant_cols[:20]
            })
        else:
            logger.info(f"   OK - Aucune colonne constante")

        # Outliers extremes (values > 1e10)
        extreme_cols = []
        for col in numeric_cols:
            if (df_trades[col].abs() > 1e10).any():
                extreme_cols.append(col)

        if extreme_cols:
            logger.warning(f"\n   {len(extreme_cols)} colonnes avec valeurs EXTREMES (>1e10):")
            for col in extreme_cols[:5]:
                logger.warning(f"      {col}: max={df_trades[col].abs().max():.2e}")

            self.warnings.append({
                'severity': 'MEDIUM',
                'category': 'Extreme Values',
                'description': f"{len(extreme_cols)} colonnes avec valeurs potentiellement aberrantes",
                'columns': extreme_cols[:10]
            })

    def _audit_feature_engineering(self, df_trades: pd.DataFrame, metadata: Dict):
        """Audit du feature engineering."""

        # Features engineered attendues (selon feature_engineering_lightgbm.py)
        expected_engineered = [
            'delta_intensity', 'depth_imbalance_ratio', 'vwap_atr_ratio',
            'gamma_position', 'flow_direction', 'gex_proximity_min',
            'range_bias', 'efficiency_ratio', 'dom_slope_ratio',
            'confluence_delta', 'layer1_layer2_interaction', 'next_wall_weighted',
            'blind_gex_confluence', 'vwap_hvl_regime', 'delta_session_ratio',
            'volume_atr_intensity', 'approaching_1d_max', 'approaching_1d_min',
            'range_expansion', 'vix_atr_volatility'
        ]

        # Verifier presence
        missing_engineered = []
        for feat in expected_engineered:
            if feat not in df_trades.columns:
                missing_engineered.append(feat)

        if missing_engineered:
            logger.error(f"\n   PROBLEME CRITIQUE: {len(missing_engineered)}/{len(expected_engineered)} features ENGINEERED MANQUANTES !")
            logger.error(f"   Features manquantes:")
            for feat in missing_engineered:
                logger.error(f"      - {feat}")

            self.issues.append({
                'severity': 'CRITICAL',
                'category': 'Feature Engineering Not Applied',
                'description': f"{len(missing_engineered)} features engineered n'ont PAS ete calculees",
                'features': missing_engineered
            })

            self.recommendations.append({
                'priority': 'HIGH',
                'action': 'Appliquer feature engineering lors du labeling',
                'details': 'Les features engineered doivent etre calculees AVANT de sauvegarder labeled_trades.parquet'
            })
        else:
            logger.info(f"   OK - Toutes les features engineered sont presentes")

    def _audit_scaling(self, model, metadata: Dict):
        """Audit du scaling/normalisation."""

        has_scaler = metadata.get('has_scaler', False)

        if not has_scaler:
            logger.warning(f"\n   ATTENTION: Aucun scaler detecte dans metadata")
            self.warnings.append({
                'severity': 'MEDIUM',
                'category': 'No Scaling',
                'description': 'Pas de StandardScaler ou normalisation appliquee',
                'impact': 'Features avec echelles differentes peuvent biaiser le modele'
            })

            self.recommendations.append({
                'priority': 'MEDIUM',
                'action': 'Ajouter StandardScaler au pipeline',
                'details': 'Normaliser les features avant training pour ameliorer convergence'
            })
        else:
            logger.info(f"   OK - Scaler present")

    def _audit_target_quality(self, df_trades: pd.DataFrame):
        """Audit de la qualite de la target (quality_score)."""

        quality_scores = df_trades['quality_score']

        logger.info(f"\n   Distribution quality_score:")
        logger.info(f"      Min:    {quality_scores.min():.2f}")
        logger.info(f"      Q25:    {quality_scores.quantile(0.25):.2f}")
        logger.info(f"      Median: {quality_scores.median():.2f}")
        logger.info(f"      Q75:    {quality_scores.quantile(0.75):.2f}")
        logger.info(f"      Max:    {quality_scores.max():.2f}")
        logger.info(f"      Mean:   {quality_scores.mean():.2f}")
        logger.info(f"      Std:    {quality_scores.std():.2f}")

        # Verifier variance suffisante
        if quality_scores.std() < 5:
            logger.warning(f"   ATTENTION: Variance tres faible (std={quality_scores.std():.2f})")
            self.warnings.append({
                'severity': 'HIGH',
                'category': 'Low Target Variance',
                'description': f"Quality score a une variance tres faible (std={quality_scores.std():.2f})",
                'impact': 'Difficulte pour le modele a apprendre des patterns'
            })

        # Verifier si target est dans [0, 100]
        out_of_range = ((quality_scores < 0) | (quality_scores > 100)).sum()
        if out_of_range > 0:
            logger.error(f"   PROBLEME: {out_of_range} scores hors range [0, 100]")
            self.issues.append({
                'severity': 'HIGH',
                'category': 'Target Out of Range',
                'description': f"{out_of_range} quality scores hors [0, 100]",
                'count': int(out_of_range)
            })

        # Distribution WIN/LOSS
        if 'outcome' in df_trades.columns:
            outcomes = df_trades['outcome'].value_counts()
            logger.info(f"\n   Distribution outcomes:")
            for outcome, count in outcomes.items():
                pct = count / len(df_trades) * 100
                logger.info(f"      {outcome}: {count:,} ({pct:.1f}%)")
        else:
            logger.warning(f"\n   Colonne 'outcome' manquante - impossible d'analyser WIN/LOSS")

        # Correlation quality_score vs pnl_ticks
        corr = df_trades['quality_score'].corr(df_trades['pnl_ticks'])
        logger.info(f"\n   Correlation quality_score vs pnl_ticks: {corr:.4f}")

        if abs(corr) < 0.3:
            logger.warning(f"   ATTENTION: Correlation faible entre quality_score et pnl_ticks")
            self.warnings.append({
                'severity': 'HIGH',
                'category': 'Low Target Correlation',
                'description': f"Quality score faiblement correle avec pnl_ticks (r={corr:.4f})",
                'impact': 'La target pourrait ne pas capturer correctement la performance reelle'
            })

    def _audit_predictions_sanity(self, model, df_trades: pd.DataFrame, metadata: Dict):
        """Sanity check sur les predictions."""

        # Tester sur un petit echantillon
        sample = df_trades.sample(n=min(100, len(df_trades)), random_state=42)

        # Preparer features (exclure colonnes non-features)
        exclude_cols = [
            'quality_score', 'outcome', 'pnl_ticks', 'entry_price', 'stop',
            'take_profit', 'mae', 'mfe', 'duration_minutes', 'date',
            'symbol_base', 'source_file', 'trade_id', 'entry_time',
            'exit_time', 'exit_price', 'tick_size', 'initial_sl_ticks',
            'initial_tp_ticks', 'final_sl_ticks', 'final_tp_ticks'
        ]

        # Features disponibles
        available_features = [col for col in sample.columns if col not in exclude_cols]

        # Features attendues par le modele
        expected_features = metadata.get('feature_names', [])

        # Intersection
        common_features = [f for f in expected_features if f in available_features]

        logger.info(f"\n   Features communes pour prediction: {len(common_features)}/{len(expected_features)}")

        if len(common_features) < len(expected_features) * 0.5:
            logger.error(f"   PROBLEME CRITIQUE: Moins de 50% des features disponibles pour prediction !")
            self.issues.append({
                'severity': 'CRITICAL',
                'category': 'Insufficient Features',
                'description': f"Seulement {len(common_features)}/{len(expected_features)} features disponibles",
                'available': len(common_features),
                'expected': len(expected_features)
            })
            return

        # Essayer de faire une prediction
        try:
            X_sample = sample[common_features]
            predictions = model.predict(X_sample)

            logger.info(f"\n   Predictions sample (n={len(predictions)}):")
            logger.info(f"      Min:    {predictions.min():.2f}")
            logger.info(f"      Median: {np.median(predictions):.2f}")
            logger.info(f"      Max:    {predictions.max():.2f}")
            logger.info(f"      Mean:   {predictions.mean():.2f}")
            logger.info(f"      Std:    {predictions.std():.2f}")

            # Verifier si predictions sont raisonnables
            if (predictions < -50).any() or (predictions > 150).any():
                logger.warning(f"   ATTENTION: Predictions hors range [-50, 150]")
                self.warnings.append({
                    'severity': 'MEDIUM',
                    'category': 'Unrealistic Predictions',
                    'description': 'Certaines predictions sont hors range attendu',
                    'min': float(predictions.min()),
                    'max': float(predictions.max())
                })

        except Exception as e:
            logger.error(f"   ERREUR lors prediction: {e}")
            self.issues.append({
                'severity': 'CRITICAL',
                'category': 'Prediction Error',
                'description': f"Impossible de faire prediction: {str(e)}"
            })

    def _generate_report(self):
        """Genere le rapport d'audit complet."""

        with open(self.report_path, 'w', encoding='utf-8') as f:
            f.write("# AUDIT COMPLET - DIAGNOSTIC PERFORMANCE DECEVANTE LIGHTGBM\n\n")
            f.write("**Date:** " + pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S') + "\n\n")
            f.write("---\n\n")

            # RESUME
            f.write("## RESUME EXECUTIF\n\n")
            f.write(f"**Issues critiques:** {len([i for i in self.issues if i['severity'] == 'CRITICAL'])}\n")
            f.write(f"**Issues high:** {len([i for i in self.issues if i['severity'] == 'HIGH'])}\n")
            f.write(f"**Issues medium:** {len([i for i in self.issues if i['severity'] == 'MEDIUM'])}\n")
            f.write(f"**Warnings:** {len(self.warnings)}\n\n")

            # ISSUES CRITIQUES
            f.write("---\n\n")
            f.write("## ISSUES CRITIQUES\n\n")
            critical_issues = [i for i in self.issues if i['severity'] == 'CRITICAL']
            if critical_issues:
                for idx, issue in enumerate(critical_issues, 1):
                    f.write(f"### {idx}. {issue['category']}\n\n")
                    f.write(f"**Severite:** {issue['severity']}\n\n")
                    f.write(f"**Description:** {issue['description']}\n\n")

                    # Details supplementaires
                    if 'features' in issue and len(issue['features']) > 0:
                        f.write(f"**Features concernees ({len(issue['features'])}):**\n")
                        for feat in issue['features'][:30]:  # Limiter affichage
                            f.write(f"- `{feat}`\n")
                        if len(issue['features']) > 30:
                            f.write(f"- ... et {len(issue['features']) - 30} autres\n")
                        f.write("\n")

                    if 'value' in issue:
                        f.write(f"**Valeur:** {issue['value']}\n\n")

                    if 'available' in issue and 'expected' in issue:
                        f.write(f"**Disponible:** {issue['available']} / {issue['expected']}\n\n")

                    f.write("---\n\n")
            else:
                f.write("Aucun issue critique detecte.\n\n")

            # AUTRES ISSUES
            f.write("## AUTRES ISSUES\n\n")
            other_issues = [i for i in self.issues if i['severity'] != 'CRITICAL']
            if other_issues:
                for idx, issue in enumerate(other_issues, 1):
                    f.write(f"### {idx}. {issue['category']} ({issue['severity']})\n\n")
                    f.write(f"{issue['description']}\n\n")

                    if 'columns' in issue:
                        f.write(f"**Colonnes ({len(issue['columns'])}):** " + ", ".join([f"`{c}`" for c in issue['columns'][:10]]) + "\n\n")

                    if 'top_columns' in issue:
                        f.write("**Top colonnes:**\n")
                        for col, count in list(issue['top_columns'].items())[:10]:
                            f.write(f"- `{col}`: {count:,}\n")
                        f.write("\n")

                    f.write("---\n\n")

            # WARNINGS
            f.write("## WARNINGS\n\n")
            if self.warnings:
                for idx, warn in enumerate(self.warnings, 1):
                    f.write(f"{idx}. **{warn['category']}** ({warn['severity']}): {warn['description']}\n")
                    if 'impact' in warn:
                        f.write(f"   - Impact: {warn['impact']}\n")
                    f.write("\n")
            else:
                f.write("Aucun warning.\n\n")

            # RECOMMENDATIONS
            f.write("---\n\n")
            f.write("## RECOMMENDATIONS\n\n")
            if self.recommendations:
                # Trier par priorite
                priority_order = {'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
                sorted_recs = sorted(self.recommendations, key=lambda x: priority_order.get(x['priority'], 99))

                for idx, rec in enumerate(sorted_recs, 1):
                    f.write(f"### {idx}. {rec['action']} (Priorite: {rec['priority']})\n\n")
                    f.write(f"{rec['details']}\n\n")
                    f.write("---\n\n")
            else:
                f.write("Aucune recommendation specifique.\n\n")

            f.write("\n---\n\n")
            f.write("*Fin du rapport d'audit*\n")

        logger.info(f"\n   Rapport genere: {self.report_path}")
        logger.info(f"   Issues critiques: {len([i for i in self.issues if i['severity'] == 'CRITICAL'])}")
        logger.info(f"   Total issues: {len(self.issues)}")
        logger.info(f"   Total warnings: {len(self.warnings)}")
        logger.info(f"   Recommendations: {len(self.recommendations)}")


if __name__ == '__main__':
    auditor = ModelAuditor()
    auditor.run_audit()



==========================================================

Analyse systematique de tous les composants du pipeline ML pour identifier
les causes de la performance decevante (R2 negatif, correlation nulle).

Sections:
1. Features Training vs Prediction (mismatch?)
2. Data Quality (NaNs, distributions)
3. Feature Engineering (applique correctement?)
4. Scaling/Normalisation (presente?)
5. Target Quality (distribution quality_score)
6. Model Sanity Check (predictions sensees?)
7. Recommendations
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import joblib
import json
import logging
from typing import Dict, List, Set

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ModelAuditor:
    """Audit complet du pipeline ML."""

    def __init__(self):
        self.model_path = Path("ml/models/lightgbm_quality_v1.pkl")
        self.metadata_path = Path("ml/models/lightgbm_quality_v1_metadata.json")
        self.labeled_trades_path = Path("ml/data/labeled_trades.parquet")
        self.aggregated_path = Path("ml/data/ml_ready_aggregated.parquet")
        self.report_path = Path("ml/backtest_results/AUDIT_COMPLET_MODEL.md")

        self.issues = []
        self.warnings = []
        self.recommendations = []

    def run_audit(self):
        """Execute l'audit complet."""
        logger.info("\n" + "="*80)
        logger.info("AUDIT COMPLET - DIAGNOSTIC PERFORMANCE DECEVANTE")
        logger.info("="*80 + "\n")

        # 1. Charger les artefacts
        logger.info("1. CHARGEMENT ARTEFACTS...")
        model, metadata, df_trades, df_agg = self._load_artifacts()

        # 2. Analyser features training vs prediction
        logger.info("\n" + "="*80)
        logger.info("2. AUDIT FEATURES - TRAINING VS PREDICTION")
        logger.info("="*80)
        self._audit_features(metadata, df_trades, df_agg)

        # 3. Analyser data quality
        logger.info("\n" + "="*80)
        logger.info("3. AUDIT DATA QUALITY")
        logger.info("="*80)
        self._audit_data_quality(df_trades)

        # 4. Analyser feature engineering
        logger.info("\n" + "="*80)
        logger.info("4. AUDIT FEATURE ENGINEERING")
        logger.info("="*80)
        self._audit_feature_engineering(df_trades, metadata)

        # 5. Analyser scaling/normalisation
        logger.info("\n" + "="*80)
        logger.info("5. AUDIT SCALING/NORMALISATION")
        logger.info("="*80)
        self._audit_scaling(model, metadata)

        # 6. Analyser target quality
        logger.info("\n" + "="*80)
        logger.info("6. AUDIT TARGET QUALITY")
        logger.info("="*80)
        self._audit_target_quality(df_trades)

        # 7. Sanity check predictions
        logger.info("\n" + "="*80)
        logger.info("7. SANITY CHECK PREDICTIONS")
        logger.info("="*80)
        self._audit_predictions_sanity(model, df_trades, metadata)

        # 8. Generer rapport
        logger.info("\n" + "="*80)
        logger.info("8. GENERATION RAPPORT AUDIT")
        logger.info("="*80)
        self._generate_report()

        logger.info("\n" + "="*80)
        logger.info("AUDIT TERMINE !")
        logger.info("="*80)
        logger.info(f"Rapport sauvegarde: {self.report_path}\n")

    def _load_artifacts(self):
        """Charge tous les artefacts necessaires."""
        # Modele
        model = joblib.load(self.model_path)
        logger.info(f"   Modele charge: {self.model_path}")

        # Metadata
        with open(self.metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        logger.info(f"   Metadata charge: {self.metadata_path}")

        # Trades labelises
        df_trades = pd.read_parquet(self.labeled_trades_path)
        logger.info(f"   Trades labelises: {len(df_trades):,} trades")

        # Agregation ML_READY
        df_agg = pd.read_parquet(self.aggregated_path)
        logger.info(f"   Snapshots agreges: {len(df_agg):,} snapshots")

        return model, metadata, df_trades, df_agg

    def _audit_features(self, metadata: Dict, df_trades: pd.DataFrame, df_agg: pd.DataFrame):
        """Audit des features: training vs prediction."""

        # Features utilisees pour training (depuis metadata)
        features_training = set(metadata.get('feature_names', []))
        logger.info(f"\n   Features TRAINING: {len(features_training)}")

        # Features disponibles dans labeled_trades (utilisees pour prediction)
        features_prediction = set(df_trades.columns) - {'quality_score', 'outcome', 'pnl_ticks',
                                                          'entry_price', 'stop', 'take_profit',
                                                          'mae', 'mfe', 'duration_minutes',
                                                          'date', 'symbol_base', 'source_file',
                                                          'trade_id', 'entry_time', 'exit_time',
                                                          'exit_price', 'tick_size',
                                                          'initial_sl_ticks', 'initial_tp_ticks',
                                                          'final_sl_ticks', 'final_tp_ticks'}
        logger.info(f"   Features PREDICTION: {len(features_prediction)}")

        # Features manquantes
        missing_in_prediction = features_training - features_prediction
        if missing_in_prediction:
            logger.error(f"\n   PROBLEME CRITIQUE: {len(missing_in_prediction)} features MANQUANTES lors prediction !")
            logger.error(f"   Features manquantes (top 20):")
            for i, feat in enumerate(sorted(list(missing_in_prediction))[:20], 1):
                logger.error(f"      {i:2d}. {feat}")
            self.issues.append({
                'severity': 'CRITICAL',
                'category': 'Features Mismatch',
                'description': f"{len(missing_in_prediction)} features utilisees pour training sont ABSENTES lors prediction",
                'features': list(missing_in_prediction)[:50]  # Limiter pour rapport
            })
        else:
            logger.info(f"   OK - Toutes les features training sont presentes")

        # Features en trop (pas grave mais interessant)
        extra_in_prediction = features_prediction - features_training
        if extra_in_prediction:
            logger.warning(f"\n   {len(extra_in_prediction)} features EXTRA dans prediction (non utilisees):")
            for i, feat in enumerate(sorted(list(extra_in_prediction))[:10], 1):
                logger.warning(f"      {i:2d}. {feat}")
            self.warnings.append({
                'severity': 'LOW',
                'category': 'Features Extra',
                'description': f"{len(extra_in_prediction)} features disponibles mais non utilisees",
                'features': list(extra_in_prediction)[:20]
            })

        # Features communes
        common_features = features_training & features_prediction
        logger.info(f"\n   Features COMMUNES: {len(common_features)}")
        coverage_pct = len(common_features) / len(features_training) * 100 if features_training else 0
        logger.info(f"   Coverage: {coverage_pct:.1f}%")

        if coverage_pct < 50:
            self.issues.append({
                'severity': 'CRITICAL',
                'category': 'Low Feature Coverage',
                'description': f"Seulement {coverage_pct:.1f}% des features training sont disponibles pour prediction",
                'value': coverage_pct
            })

    def _audit_data_quality(self, df_trades: pd.DataFrame):
        """Audit de la qualite des donnees."""

        # NaNs par colonne
        nan_counts = df_trades.isnull().sum()
        nan_cols = nan_counts[nan_counts > 0]

        if len(nan_cols) > 0:
            logger.warning(f"\n   {len(nan_cols)} colonnes contiennent des NaNs:")
            for col, count in nan_cols.head(10).items():
                pct = count / len(df_trades) * 100
                logger.warning(f"      {col}: {count:,} ({pct:.1f}%)")

            self.issues.append({
                'severity': 'HIGH',
                'category': 'Missing Values',
                'description': f"{len(nan_cols)} colonnes avec NaNs",
                'top_columns': {col: int(count) for col, count in nan_cols.head(20).items()}
            })
        else:
            logger.info(f"   OK - Aucun NaN detecte")

        # Colonnes constantes (variance nulle)
        numeric_cols = df_trades.select_dtypes(include=[np.number]).columns
        constant_cols = []
        for col in numeric_cols:
            if df_trades[col].nunique() == 1:
                constant_cols.append(col)

        if constant_cols:
            logger.warning(f"\n   {len(constant_cols)} colonnes CONSTANTES (variance nulle):")
            for col in constant_cols[:10]:
                logger.warning(f"      {col}: {df_trades[col].iloc[0]}")

            self.issues.append({
                'severity': 'MEDIUM',
                'category': 'Constant Features',
                'description': f"{len(constant_cols)} features n'ont aucune variance",
                'columns': constant_cols[:20]
            })
        else:
            logger.info(f"   OK - Aucune colonne constante")

        # Outliers extremes (values > 1e10)
        extreme_cols = []
        for col in numeric_cols:
            if (df_trades[col].abs() > 1e10).any():
                extreme_cols.append(col)

        if extreme_cols:
            logger.warning(f"\n   {len(extreme_cols)} colonnes avec valeurs EXTREMES (>1e10):")
            for col in extreme_cols[:5]:
                logger.warning(f"      {col}: max={df_trades[col].abs().max():.2e}")

            self.warnings.append({
                'severity': 'MEDIUM',
                'category': 'Extreme Values',
                'description': f"{len(extreme_cols)} colonnes avec valeurs potentiellement aberrantes",
                'columns': extreme_cols[:10]
            })

    def _audit_feature_engineering(self, df_trades: pd.DataFrame, metadata: Dict):
        """Audit du feature engineering."""

        # Features engineered attendues (selon feature_engineering_lightgbm.py)
        expected_engineered = [
            'delta_intensity', 'depth_imbalance_ratio', 'vwap_atr_ratio',
            'gamma_position', 'flow_direction', 'gex_proximity_min',
            'range_bias', 'efficiency_ratio', 'dom_slope_ratio',
            'confluence_delta', 'layer1_layer2_interaction', 'next_wall_weighted',
            'blind_gex_confluence', 'vwap_hvl_regime', 'delta_session_ratio',
            'volume_atr_intensity', 'approaching_1d_max', 'approaching_1d_min',
            'range_expansion', 'vix_atr_volatility'
        ]

        # Verifier presence
        missing_engineered = []
        for feat in expected_engineered:
            if feat not in df_trades.columns:
                missing_engineered.append(feat)

        if missing_engineered:
            logger.error(f"\n   PROBLEME CRITIQUE: {len(missing_engineered)}/{len(expected_engineered)} features ENGINEERED MANQUANTES !")
            logger.error(f"   Features manquantes:")
            for feat in missing_engineered:
                logger.error(f"      - {feat}")

            self.issues.append({
                'severity': 'CRITICAL',
                'category': 'Feature Engineering Not Applied',
                'description': f"{len(missing_engineered)} features engineered n'ont PAS ete calculees",
                'features': missing_engineered
            })

            self.recommendations.append({
                'priority': 'HIGH',
                'action': 'Appliquer feature engineering lors du labeling',
                'details': 'Les features engineered doivent etre calculees AVANT de sauvegarder labeled_trades.parquet'
            })
        else:
            logger.info(f"   OK - Toutes les features engineered sont presentes")

    def _audit_scaling(self, model, metadata: Dict):
        """Audit du scaling/normalisation."""

        has_scaler = metadata.get('has_scaler', False)

        if not has_scaler:
            logger.warning(f"\n   ATTENTION: Aucun scaler detecte dans metadata")
            self.warnings.append({
                'severity': 'MEDIUM',
                'category': 'No Scaling',
                'description': 'Pas de StandardScaler ou normalisation appliquee',
                'impact': 'Features avec echelles differentes peuvent biaiser le modele'
            })

            self.recommendations.append({
                'priority': 'MEDIUM',
                'action': 'Ajouter StandardScaler au pipeline',
                'details': 'Normaliser les features avant training pour ameliorer convergence'
            })
        else:
            logger.info(f"   OK - Scaler present")

    def _audit_target_quality(self, df_trades: pd.DataFrame):
        """Audit de la qualite de la target (quality_score)."""

        quality_scores = df_trades['quality_score']

        logger.info(f"\n   Distribution quality_score:")
        logger.info(f"      Min:    {quality_scores.min():.2f}")
        logger.info(f"      Q25:    {quality_scores.quantile(0.25):.2f}")
        logger.info(f"      Median: {quality_scores.median():.2f}")
        logger.info(f"      Q75:    {quality_scores.quantile(0.75):.2f}")
        logger.info(f"      Max:    {quality_scores.max():.2f}")
        logger.info(f"      Mean:   {quality_scores.mean():.2f}")
        logger.info(f"      Std:    {quality_scores.std():.2f}")

        # Verifier variance suffisante
        if quality_scores.std() < 5:
            logger.warning(f"   ATTENTION: Variance tres faible (std={quality_scores.std():.2f})")
            self.warnings.append({
                'severity': 'HIGH',
                'category': 'Low Target Variance',
                'description': f"Quality score a une variance tres faible (std={quality_scores.std():.2f})",
                'impact': 'Difficulte pour le modele a apprendre des patterns'
            })

        # Verifier si target est dans [0, 100]
        out_of_range = ((quality_scores < 0) | (quality_scores > 100)).sum()
        if out_of_range > 0:
            logger.error(f"   PROBLEME: {out_of_range} scores hors range [0, 100]")
            self.issues.append({
                'severity': 'HIGH',
                'category': 'Target Out of Range',
                'description': f"{out_of_range} quality scores hors [0, 100]",
                'count': int(out_of_range)
            })

        # Distribution WIN/LOSS
        if 'outcome' in df_trades.columns:
            outcomes = df_trades['outcome'].value_counts()
            logger.info(f"\n   Distribution outcomes:")
            for outcome, count in outcomes.items():
                pct = count / len(df_trades) * 100
                logger.info(f"      {outcome}: {count:,} ({pct:.1f}%)")
        else:
            logger.warning(f"\n   Colonne 'outcome' manquante - impossible d'analyser WIN/LOSS")

        # Correlation quality_score vs pnl_ticks
        corr = df_trades['quality_score'].corr(df_trades['pnl_ticks'])
        logger.info(f"\n   Correlation quality_score vs pnl_ticks: {corr:.4f}")

        if abs(corr) < 0.3:
            logger.warning(f"   ATTENTION: Correlation faible entre quality_score et pnl_ticks")
            self.warnings.append({
                'severity': 'HIGH',
                'category': 'Low Target Correlation',
                'description': f"Quality score faiblement correle avec pnl_ticks (r={corr:.4f})",
                'impact': 'La target pourrait ne pas capturer correctement la performance reelle'
            })

    def _audit_predictions_sanity(self, model, df_trades: pd.DataFrame, metadata: Dict):
        """Sanity check sur les predictions."""

        # Tester sur un petit echantillon
        sample = df_trades.sample(n=min(100, len(df_trades)), random_state=42)

        # Preparer features (exclure colonnes non-features)
        exclude_cols = [
            'quality_score', 'outcome', 'pnl_ticks', 'entry_price', 'stop',
            'take_profit', 'mae', 'mfe', 'duration_minutes', 'date',
            'symbol_base', 'source_file', 'trade_id', 'entry_time',
            'exit_time', 'exit_price', 'tick_size', 'initial_sl_ticks',
            'initial_tp_ticks', 'final_sl_ticks', 'final_tp_ticks'
        ]

        # Features disponibles
        available_features = [col for col in sample.columns if col not in exclude_cols]

        # Features attendues par le modele
        expected_features = metadata.get('feature_names', [])

        # Intersection
        common_features = [f for f in expected_features if f in available_features]

        logger.info(f"\n   Features communes pour prediction: {len(common_features)}/{len(expected_features)}")

        if len(common_features) < len(expected_features) * 0.5:
            logger.error(f"   PROBLEME CRITIQUE: Moins de 50% des features disponibles pour prediction !")
            self.issues.append({
                'severity': 'CRITICAL',
                'category': 'Insufficient Features',
                'description': f"Seulement {len(common_features)}/{len(expected_features)} features disponibles",
                'available': len(common_features),
                'expected': len(expected_features)
            })
            return

        # Essayer de faire une prediction
        try:
            X_sample = sample[common_features]
            predictions = model.predict(X_sample)

            logger.info(f"\n   Predictions sample (n={len(predictions)}):")
            logger.info(f"      Min:    {predictions.min():.2f}")
            logger.info(f"      Median: {np.median(predictions):.2f}")
            logger.info(f"      Max:    {predictions.max():.2f}")
            logger.info(f"      Mean:   {predictions.mean():.2f}")
            logger.info(f"      Std:    {predictions.std():.2f}")

            # Verifier si predictions sont raisonnables
            if (predictions < -50).any() or (predictions > 150).any():
                logger.warning(f"   ATTENTION: Predictions hors range [-50, 150]")
                self.warnings.append({
                    'severity': 'MEDIUM',
                    'category': 'Unrealistic Predictions',
                    'description': 'Certaines predictions sont hors range attendu',
                    'min': float(predictions.min()),
                    'max': float(predictions.max())
                })

        except Exception as e:
            logger.error(f"   ERREUR lors prediction: {e}")
            self.issues.append({
                'severity': 'CRITICAL',
                'category': 'Prediction Error',
                'description': f"Impossible de faire prediction: {str(e)}"
            })

    def _generate_report(self):
        """Genere le rapport d'audit complet."""

        with open(self.report_path, 'w', encoding='utf-8') as f:
            f.write("# AUDIT COMPLET - DIAGNOSTIC PERFORMANCE DECEVANTE LIGHTGBM\n\n")
            f.write("**Date:** " + pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S') + "\n\n")
            f.write("---\n\n")

            # RESUME
            f.write("## RESUME EXECUTIF\n\n")
            f.write(f"**Issues critiques:** {len([i for i in self.issues if i['severity'] == 'CRITICAL'])}\n")
            f.write(f"**Issues high:** {len([i for i in self.issues if i['severity'] == 'HIGH'])}\n")
            f.write(f"**Issues medium:** {len([i for i in self.issues if i['severity'] == 'MEDIUM'])}\n")
            f.write(f"**Warnings:** {len(self.warnings)}\n\n")

            # ISSUES CRITIQUES
            f.write("---\n\n")
            f.write("## ISSUES CRITIQUES\n\n")
            critical_issues = [i for i in self.issues if i['severity'] == 'CRITICAL']
            if critical_issues:
                for idx, issue in enumerate(critical_issues, 1):
                    f.write(f"### {idx}. {issue['category']}\n\n")
                    f.write(f"**Severite:** {issue['severity']}\n\n")
                    f.write(f"**Description:** {issue['description']}\n\n")

                    # Details supplementaires
                    if 'features' in issue and len(issue['features']) > 0:
                        f.write(f"**Features concernees ({len(issue['features'])}):**\n")
                        for feat in issue['features'][:30]:  # Limiter affichage
                            f.write(f"- `{feat}`\n")
                        if len(issue['features']) > 30:
                            f.write(f"- ... et {len(issue['features']) - 30} autres\n")
                        f.write("\n")

                    if 'value' in issue:
                        f.write(f"**Valeur:** {issue['value']}\n\n")

                    if 'available' in issue and 'expected' in issue:
                        f.write(f"**Disponible:** {issue['available']} / {issue['expected']}\n\n")

                    f.write("---\n\n")
            else:
                f.write("Aucun issue critique detecte.\n\n")

            # AUTRES ISSUES
            f.write("## AUTRES ISSUES\n\n")
            other_issues = [i for i in self.issues if i['severity'] != 'CRITICAL']
            if other_issues:
                for idx, issue in enumerate(other_issues, 1):
                    f.write(f"### {idx}. {issue['category']} ({issue['severity']})\n\n")
                    f.write(f"{issue['description']}\n\n")

                    if 'columns' in issue:
                        f.write(f"**Colonnes ({len(issue['columns'])}):** " + ", ".join([f"`{c}`" for c in issue['columns'][:10]]) + "\n\n")

                    if 'top_columns' in issue:
                        f.write("**Top colonnes:**\n")
                        for col, count in list(issue['top_columns'].items())[:10]:
                            f.write(f"- `{col}`: {count:,}\n")
                        f.write("\n")

                    f.write("---\n\n")

            # WARNINGS
            f.write("## WARNINGS\n\n")
            if self.warnings:
                for idx, warn in enumerate(self.warnings, 1):
                    f.write(f"{idx}. **{warn['category']}** ({warn['severity']}): {warn['description']}\n")
                    if 'impact' in warn:
                        f.write(f"   - Impact: {warn['impact']}\n")
                    f.write("\n")
            else:
                f.write("Aucun warning.\n\n")

            # RECOMMENDATIONS
            f.write("---\n\n")
            f.write("## RECOMMENDATIONS\n\n")
            if self.recommendations:
                # Trier par priorite
                priority_order = {'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
                sorted_recs = sorted(self.recommendations, key=lambda x: priority_order.get(x['priority'], 99))

                for idx, rec in enumerate(sorted_recs, 1):
                    f.write(f"### {idx}. {rec['action']} (Priorite: {rec['priority']})\n\n")
                    f.write(f"{rec['details']}\n\n")
                    f.write("---\n\n")
            else:
                f.write("Aucune recommendation specifique.\n\n")

            f.write("\n---\n\n")
            f.write("*Fin du rapport d'audit*\n")

        logger.info(f"\n   Rapport genere: {self.report_path}")
        logger.info(f"   Issues critiques: {len([i for i in self.issues if i['severity'] == 'CRITICAL'])}")
        logger.info(f"   Total issues: {len(self.issues)}")
        logger.info(f"   Total warnings: {len(self.warnings)}")
        logger.info(f"   Recommendations: {len(self.recommendations)}")


if __name__ == '__main__':
    auditor = ModelAuditor()
    auditor.run_audit()





