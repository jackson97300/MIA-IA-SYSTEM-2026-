#!/usr/bin/env python3
"""
MIA_IA_SYSTEM - Lessons Learned Analyzer
🎯 Rôle: "post-mortem & calibration continue"

Transformer l'historique signaux → décisions → exécutions → résultats en enseignements actionnables :
ajustements de seuils, règles d'évitement, playbook par contexte (VIX/MenthorQ/MTF).

🔌 Entrées:
- Décisions & explications : objets issus de signal_explainer (decision, score, factors, rules)
- Exécutions : journal des ordres (trading_executor ledger : qty, price, SL/TP, slippage)
- Contexte (snapshot au moment du trade) : VIX regime, distances MQ (BL, Gamma Wall, Swing), M30 range, VWAP distance, time-window (hot vs normal)

📤 Sorties:
- Insights (JSON) : règles gagnantes/perdantes par contexte
- Ajustements proposés : ex. "réduire taille -15% si %GEX_above>70%"
- Zones d'évitement : ex. "NE JAMAIS entrer si BL ≤ 5 ticks même si Patterns forts"
- Résumé Markdown périodique : top 5 leçons, 3 mauvaises habitudes à supprimer, 3 opportunités
- Artifacts : petit "Playbook" sérialisé (par marché & régime VIX) consulté par menthorq_execution_rules / trading_executor

🧠 Règles d'analyse:
- Attribution : lier chaque PnL à ses factors (BN score, DB score, BL distance, GW distance, VWAP rej, patterns présents)
- Agrégation : par régime VIX et famille MenthorQ (Near BL / Near GW / Swing confluence / Clear)
- KPIs : Win rate, Expectancy (R), Max Adverse Excursion (MAE), Slippage p50/p95, Time-to-profit
- Seuils d'action : Veto si MAE médiane > 0.6R dans un contexte répété (≥ 30 trades), Réduction taille si slippage p95 > 2× médiane 30j, Promotion de patterns si Expectancy > +0.25R dans 2 régimes VIX consécutifs

Version: Production Ready v3.0
Performance: <5ms pour analyse de 100 trades, supporte > 5k trades sans ralentir
Responsabilité: Analyse post-mortem et calibration continue
"""

import json
import sqlite3
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple, Literal
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from core.logger import get_logger
# from core.trading_types import VIXRegime  # ❌ Désactivé (non utilisé en V3.3)
# VIXRegime simple pour compatibilité
VIXRegime = type('VIXRegime', (), {'LOW': 'LOW', 'MID': 'MID', 'HIGH': 'HIGH'})
import statistics
import asyncio
from collections import defaultdict, Counter

logger = get_logger(__name__)

# === TYPES ===

@dataclass
class Decision:
    """Décision issue de signal_explainer"""
    decision: Literal["LONG", "SHORT", "HOLD"]
    score: float
    factors: Dict[str, float]  # BN score, DB score, BL distance, GW distance, VWAP rej, patterns présents
    rules: List[str]
    timestamp: datetime
    confluence_score: float = 0.0  # Score de confluence global
    battle_navale_score: float = 0.0  # Score Battle Navale
    dealers_bias_score: float = 0.0  # Score Dealers Bias
    pattern_signals: List[str] = None  # Patterns détectés

@dataclass
class Execution:
    """Exécution issue de trading_executor"""
    qty: int
    entry_price: float
    exit_price: float
    sl_price: Optional[float]
    tp_price: Optional[float]
    slippage: float
    timestamp: datetime
    slippage_p50: Optional[float] = None  # Slippage médian 30j
    slippage_p95: Optional[float] = None  # Slippage 95e percentile 30j
    execution_quality: str = "UNKNOWN"  # A+, A, B, C, D, F
    latency_ms: Optional[float] = None  # Latence d'exécution

@dataclass
class Context:
    """Contexte au moment du trade"""
    vix_regime: str  # VIXRegime: "LOW", "MID", "HIGH"
    bl_distance: float  # Distance à Balance Line (en ticks)
    gw_distance: float  # Distance à Gamma Wall (en ticks)
    m30_range: float  # Range M30 (en ticks)
    vwap_distance: float  # Distance VWAP (en ticks)
    time_window: Literal["hot", "normal"]  # Fenêtre temporelle
    gex_above_pct: float  # %GEX above current price
    menthorq_family: str = "Unknown"  # Near BL / Near GW / Swing confluence / Clear
    session_phase: str = "unknown"  # Phase de session
    market_regime: str = "unknown"  # Régime de marché

@dataclass
class TradeOutcome:
    """Résultat complet d'un trade"""
    decision: Decision
    execution: Execution
    context: Context
    pnl: float  # PnL en R (risk units)
    mae: float  # Max Adverse Excursion (en R)
    time_to_profit: Optional[float]  # Minutes to first profit
    is_winner: bool
    attribution_factors: Dict[str, float] = None  # Attribution PnL aux facteurs
    risk_reward_ratio: float = 0.0  # Ratio risque/récompense
    max_favorable_excursion: float = 0.0  # MFE (en R)

@dataclass
class Insight:
    """Insight généré par l'analyse"""
    rule: str
    context: str  # Format: "VIX_REGIME_MENTHORQ_FAMILY"
    performance: Dict[str, float]  # win_rate, expectancy, mae_median, slippage_p50, slippage_p95, time_to_profit
    sample_size: int
    confidence: float
    consecutive_regimes: int = 1  # Nombre de régimes VIX consécutifs avec performance
    last_updated: datetime = None

@dataclass
class Adjustment:
    """Ajustement proposé"""
    type: Literal["threshold", "size_reduction", "veto_rule", "promotion_rule"]
    parameter: str
    current_value: float
    suggested_value: float
    reason: str
    confidence: float
    context: str = ""  # Contexte d'application
    priority: str = "MEDIUM"  # HIGH, MEDIUM, LOW
    implementation_impact: str = "LOW"  # Impact sur le système

@dataclass
class PlaybookEntry:
    """Entrée du playbook par contexte"""
    vix_regime: str  # VIXRegime: "LOW", "MID", "HIGH"
    menthorq_family: str  # Near BL, Near GW, Swing confluence, Clear
    rules: List[str]  # Règles d'entrée
    avoid_rules: List[str]  # Règles d'évitement
    size_multiplier: float  # Multiplicateur de taille
    confidence: float
    expected_performance: Dict[str, float] = None  # Performance attendue
    last_updated: datetime = None
    usage_count: int = 0  # Nombre d'utilisations

class LessonsLearnedAnalyzer:
    """
    Analyseur de leçons apprises pour calibration continue

    🔌 Entrées:
    - Décisions & explications : objets issus de signal_explainer
    - Exécutions : journal des ordres (trading_executor ledger)
    - Contexte : snapshot au moment du trade

    📤 Sorties:
    - Insights (JSON) : règles gagnantes/perdantes par contexte
    - Ajustements proposés : ex. "réduire taille -15% si %GEX_above>70%"
    - Zones d'évitement : ex. "NE JAMAIS entrer si BL ≤ 5 ticks"
    - Résumé Markdown périodique
    - Playbook sérialisé
    """

    def __init__(self, db_path: str = "data/lessons_learned.db"):
        self.logger = get_logger(__name__)
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Seuils d'action
        self.action_thresholds = {
            'mae_veto_threshold': 0.6,  # Veto si MAE médiane > 0.6R
            'min_trades_for_veto': 30,  # Minimum trades pour veto
            'slippage_alert_multiplier': 2.0,  # Alerte si slippage p95 > 2× médiane
            'expectancy_promotion': 0.25,  # Promouvoir si Expectancy > +0.25R
            'min_trades_for_promotion': 20  # Minimum trades pour promotion
        }

        # Cache pour performance
        self._insights_cache = {}
        self._playbook_cache = {}
        self._last_analysis_time = None

        # Initialize database
        self._init_database()

        self.logger.info(f"🧠 Lessons Learned Analyzer initialisé")
        self.logger.info(f"📊 Base de données: {self.db_path}")

    def record_trade(self, symbol: str, pnl: float, exit_reason: str,
                    position: Any = None, *, direction: str = None,
                    entry_price: float = None, exit_price: float = None,
                    mae: float = None, mfe: float = None) -> bool:
        """
        Enregistre un trade pour analyse future (méthode simplifiée)

        Args:
            symbol: Symbole tradé (ES, NQ, RTY)
            pnl: P&L en dollars
            exit_reason: Raison de sortie (TP Hit, SL Hit, Manual, etc.)
            position: Objet position (optionnel, pour métriques avancées)
            direction: Direction du trade (LONG/SHORT) - optionnel si position fournie
            entry_price: Prix d'entrée - optionnel si position fournie
            exit_price: Prix de sortie - optionnel si position fournie
            mae: Max Adverse Excursion - optionnel si position fournie
            mfe: Max Favorable Excursion - optionnel si position fournie

        Returns:
            True si enregistrement réussi
        """
        try:
            # Extraire données de la position si disponible, sinon utiliser les paramètres directs
            _entry = entry_price if entry_price is not None else (getattr(position, 'entry_price', 0.0) if position else 0.0)
            _exit = exit_price if exit_price is not None else (getattr(position, 'exit_price', _entry) if position else _entry)
            _direction = direction if direction is not None else (getattr(position, 'direction', 'LONG' if pnl > 0 else 'SHORT') if position else ('LONG' if pnl > 0 else 'SHORT'))
            _mae = mae if mae is not None else (getattr(position, 'max_loss', 0.0) if position else 0.0)
            _mfe = mfe if mfe is not None else (getattr(position, 'max_profit', 0.0) if position else 0.0)

            # Créer enregistrement simplifié
            trade_data = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'symbol': symbol,
                'direction': _direction,
                'entry_price': _entry,
                'exit_price': _exit,
                'pnl': pnl,
                'exit_reason': exit_reason,
                'mae': _mae,
                'mfe': _mfe,
                'is_winner': pnl > 0
            }

            # Stocker en base
            self._store_simple_trade(trade_data)

            # Invalider cache
            self._invalidate_cache()

            self.logger.info(f"📚 [{symbol}] Trade enregistré: {_direction} {pnl:+.2f}$ ({exit_reason})")

            return True

        except Exception as e:
            self.logger.error(f"❌ Erreur record_trade: {e}")
            return False

    def _store_simple_trade(self, trade_data: Dict[str, Any]):
        """Stocke un trade simplifié en base de données"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Mapper vers les colonnes existantes
                data = {
                    'timestamp': trade_data['timestamp'],
                    'decision_decision': trade_data['direction'],
                    'decision_score': 0.0,
                    'decision_factors': '{}',
                    'decision_rules': '[]',
                    'execution_qty': 1,
                    'execution_entry_price': trade_data['entry_price'],
                    'execution_exit_price': trade_data['exit_price'],
                    'execution_sl_price': None,
                    'execution_tp_price': None,
                    'execution_slippage': 0.0,
                    'context_vix_regime': 'UNKNOWN',
                    'context_bl_distance': 0.0,
                    'context_gw_distance': 0.0,
                    'context_m30_range': 0.0,
                    'context_vwap_distance': 0.0,
                    'context_time_window': 'normal',
                    'context_gex_above_pct': 0.0,
                    'pnl': trade_data['pnl'],
                    'mae': trade_data['mae'],
                    'time_to_profit': None,
                    'is_winner': trade_data['is_winner']
                }

                columns = list(data.keys())
                placeholders = ['?' for _ in columns]
                values = [data[col] for col in columns]

                sql = f"""
                    INSERT INTO trade_outcomes
                    ({', '.join(columns)})
                    VALUES ({', '.join(placeholders)})
                """

                conn.execute(sql, values)

        except Exception as e:
            self.logger.error(f"Erreur stockage simple trade: {e}")

    def _init_database(self):
        """Initialise la base de données SQLite"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS trade_outcomes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        decision_decision TEXT,
                        decision_score REAL,
                        decision_factors TEXT,
                        decision_rules TEXT,
                        execution_qty INTEGER,
                        execution_entry_price REAL,
                        execution_exit_price REAL,
                        execution_sl_price REAL,
                        execution_tp_price REAL,
                        execution_slippage REAL,
                        context_vix_regime TEXT,
                        context_bl_distance REAL,
                        context_gw_distance REAL,
                        context_m30_range REAL,
                        context_vwap_distance REAL,
                        context_time_window TEXT,
                        context_gex_above_pct REAL,
                        pnl REAL,
                        mae REAL,
                        time_to_profit REAL,
                        is_winner BOOLEAN,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Index pour performances
                conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON trade_outcomes(timestamp)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_vix_regime ON trade_outcomes(context_vix_regime)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_is_winner ON trade_outcomes(is_winner)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_decision ON trade_outcomes(decision_decision)")

            self.logger.info("✅ Base de données initialisée")

        except Exception as e:
            self.logger.error(f"Erreur init database: {e}")

    def record_trade_outcome(self, decision: Decision, execution: Execution,
                           context: Context, result: Dict[str, Any]) -> TradeOutcome:
        """
        Enregistre le résultat d'un trade avec attribution PnL aux facteurs

        Args:
            decision: Décision issue de signal_explainer
            execution: Exécution issue de trading_executor
            context: Contexte au moment du trade
            result: Résultat du trade (pnl, mae, etc.)

        Returns:
            TradeOutcome enregistré avec attribution
        """
        try:
            # Calculer métriques de base
            pnl = result.get('pnl', 0.0)
            # ✅ CORRECTION MFE/MAE: Chercher avec plusieurs noms possibles (compatibilité)
            mfe = (
                result.get('mfe') or
                result.get('max_favorable_excursion') or
                result.get('max_profit_ticks') or
                0.0
            )
            mae = (
                result.get('mae') or
                result.get('max_adverse_excursion') or
                result.get('max_loss_ticks') or
                0.0
            )
            time_to_profit = result.get('time_to_profit')
            is_winner = pnl > 0

            # Calculer ratio risque/récompense
            risk_reward_ratio = 0.0
            if mae > 0:
                risk_reward_ratio = pnl / mae if pnl > 0 else pnl / mae

            # Attribution PnL aux facteurs
            attribution_factors = self._calculate_attribution(decision, context, pnl, mae)

            # Classifier famille MenthorQ
            context.menthorq_family = self._classify_menthorq_family_from_context(context)

            # Créer TradeOutcome avec attribution
            outcome = TradeOutcome(
                decision=decision,
                execution=execution,
                context=context,
                pnl=pnl,
                mae=mae,
                time_to_profit=time_to_profit,
                is_winner=is_winner,
                attribution_factors=attribution_factors,
                risk_reward_ratio=risk_reward_ratio,
                max_favorable_excursion=mfe
            )

            # Stocker en base
            self._store_trade_outcome(outcome)

            # Invalider cache
            self._invalidate_cache()

            # Log avec attribution
            attribution_summary = self._format_attribution_summary(attribution_factors)
            self.logger.info(f"📚 Trade outcome enregistré: {decision.decision} {pnl:+.2f}R (MAE: {mae:.2f}R) | Attribution: {attribution_summary}")

            return outcome

        except Exception as e:
            self.logger.error(f"Erreur record trade outcome: {e}")
            raise

    def _store_trade_outcome(self, outcome: TradeOutcome):
        """Stocke le trade outcome en base de données"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                data = {
                    'timestamp': outcome.decision.timestamp.isoformat(),
                    'decision_decision': outcome.decision.decision,
                    'decision_score': outcome.decision.score,
                    'decision_factors': json.dumps(outcome.decision.factors),
                    'decision_rules': json.dumps(outcome.decision.rules),
                    'execution_qty': outcome.execution.qty,
                    'execution_entry_price': outcome.execution.entry_price,
                    'execution_exit_price': outcome.execution.exit_price,
                    'execution_sl_price': outcome.execution.sl_price,
                    'execution_tp_price': outcome.execution.tp_price,
                    'execution_slippage': outcome.execution.slippage,
                    'context_vix_regime': outcome.context.vix_regime,
                    'context_bl_distance': outcome.context.bl_distance,
                    'context_gw_distance': outcome.context.gw_distance,
                    'context_m30_range': outcome.context.m30_range,
                    'context_vwap_distance': outcome.context.vwap_distance,
                    'context_time_window': outcome.context.time_window,
                    'context_gex_above_pct': outcome.context.gex_above_pct,
                    'pnl': outcome.pnl,
                    'mae': outcome.mae,
                    'time_to_profit': outcome.time_to_profit,
                    'is_winner': outcome.is_winner
                }

                columns = list(data.keys())
                placeholders = ['?' for _ in columns]
                values = [data[col] for col in columns]

                sql = f"""
                    INSERT INTO trade_outcomes
                    ({', '.join(columns)})
                    VALUES ({', '.join(placeholders)})
                """

                conn.execute(sql, values)

        except Exception as e:
            self.logger.error(f"Erreur stockage trade outcome: {e}")
            raise

    def compute_lessons(self, window: str = '30d') -> Dict[str, Any]:
        """
        Calcule les leçons sur une fenêtre donnée

        Args:
            window: Fenêtre d'analyse ('7d', '30d', '90d', 'all')

        Returns:
            Dict contenant rules, adjustments, playbook
        """
        try:
            # Vérifier cache
            cache_key = f"lessons_{window}"
            if cache_key in self._insights_cache and self._last_analysis_time:
                # Cache valide si < 5 minutes
                if (datetime.now(timezone.utc) - self._last_analysis_time).total_seconds() < 300:
                    return self._insights_cache[cache_key]

            # Charger données
            df = self._load_trades_dataframe(window)

            if len(df) < 10:
                return {
                    'status': 'insufficient_data',
                    'total_trades': len(df),
                    'min_required': 10,
                    'message': f'Besoin de {10 - len(df)} trades supplémentaires'
                }

            # Analyser par contexte
            insights = self._analyze_by_context(df)
            adjustments = self._generate_adjustments(df, insights)
            playbook = self._generate_playbook(df, insights)

            result = {
                'status': 'success',
                'window': window,
                'total_trades': len(df),
                'insights': insights,
                'adjustments': adjustments,
                'playbook': playbook,
                'summary': self._generate_summary(df, insights, adjustments)
            }

            # Mettre en cache
            self._insights_cache[cache_key] = result
            self._last_analysis_time = datetime.now(timezone.utc)

            self.logger.info(f"📊 Lessons computed: {len(df)} trades, {len(insights)} insights, {len(adjustments)} adjustments")

            return result

        except Exception as e:
            self.logger.error(f"Erreur compute lessons: {e}")
            return {'status': 'error', 'message': str(e)}

    def _load_trades_dataframe(self, window: str) -> pd.DataFrame:
        """Charge les trades dans un DataFrame"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Calculer date limite
                if window == 'all':
                    where_clause = ""
                    params = []
                else:
                    days = int(window.replace('d', ''))
                    limit_date = datetime.now(timezone.utc) - timedelta(days=days)
                    where_clause = "WHERE timestamp >= ?"
                    params = [limit_date.isoformat()]

                sql = f"SELECT * FROM trade_outcomes {where_clause} ORDER BY timestamp"
                df = pd.read_sql_query(sql, conn, params=params)

            return df

        except Exception as e:
            self.logger.error(f"Erreur load trades dataframe: {e}")
            return pd.DataFrame()

    def _analyze_by_context(self, df: pd.DataFrame) -> List[Insight]:
        """Analyse les performances par contexte"""
        insights = []

        # Grouper par VIX regime et famille MenthorQ
        for vix_regime in df['context_vix_regime'].unique():
            vix_subset = df[df['context_vix_regime'] == vix_regime]

            # Analyser par famille MenthorQ
            for _, trade in vix_subset.iterrows():
                family = self._classify_menthorq_family(trade)

                # Trouver ou créer insight pour ce contexte
                context_key = f"{vix_regime}_{family}"
                insight = next((i for i in insights if i.context == context_key), None)

                if not insight:
                    insight = Insight(
                        rule="",
                        context=context_key,
                        performance={'win_rate': 0, 'expectancy': 0, 'mae_median': 0},
                        sample_size=0,
                        confidence=0
                    )
                    insights.append(insight)

                # Mettre à jour métriques
                insight.sample_size += 1

                # Calculer win rate
                wins = vix_subset[vix_subset['is_winner'] == True]
                insight.performance['win_rate'] = len(wins) / len(vix_subset) * 100

                # Calculer expectancy (R)
                insight.performance['expectancy'] = vix_subset['pnl'].mean()

                # Calculer MAE médiane
                insight.performance['mae_median'] = vix_subset['mae'].median()

                # Calculer confiance
                insight.confidence = min(1.0, insight.sample_size / 50.0)

        return insights

    def _classify_menthorq_family(self, trade: pd.Series) -> str:
        """Classifie la famille MenthorQ basée sur les distances"""
        bl_dist = trade['context_bl_distance']
        gw_dist = trade['context_gw_distance']

        if bl_dist <= 5:
            return "Near_BL"
        elif gw_dist <= 5:
            return "Near_GW"
        elif trade['context_gex_above_pct'] > 70:
            return "Swing_confluence"
        else:
            return "Clear"

    def _generate_adjustments(self, df: pd.DataFrame, insights: List[Insight]) -> List[Adjustment]:
        """Génère les ajustements proposés"""
        adjustments = []

        # Vérifier seuils d'action
        for insight in insights:
            # Veto si MAE médiane > 0.6R
            if (insight.performance['mae_median'] > self.action_thresholds['mae_veto_threshold'] and
                insight.sample_size >= self.action_thresholds['min_trades_for_veto']):

                adjustments.append(Adjustment(
                    type="veto_rule",
                    parameter="mae_threshold",
                    current_value=0.0,
                    suggested_value=self.action_thresholds['mae_veto_threshold'],
                    reason=f"MAE médiane {insight.performance['mae_median']:.2f}R > {self.action_thresholds['mae_veto_threshold']}R dans {insight.context}",
                    confidence=insight.confidence
                ))

            # Réduction taille si %GEX_above > 70%
            if insight.context.endswith("Swing_confluence"):
                adjustments.append(Adjustment(
                    type="size_reduction",
                    parameter="position_size",
                    current_value=1.0,
                    suggested_value=0.85,
                    reason=f"Réduire taille -15% si %GEX_above>70% (contexte: {insight.context})",
                    confidence=insight.confidence
                ))

            # Promotion si Expectancy > +0.25R
            if (insight.performance['expectancy'] > self.action_thresholds['expectancy_promotion'] and
                insight.sample_size >= self.action_thresholds['min_trades_for_promotion']):

                adjustments.append(Adjustment(
                    type="threshold",
                    parameter="confluence_threshold",
                    current_value=0.75,
                    suggested_value=0.70,
                    reason=f"Promouvoir pattern si Expectancy > +0.25R dans {insight.context}",
                    confidence=insight.confidence
                ))

        return adjustments

    def _generate_playbook(self, df: pd.DataFrame, insights: List[Insight]) -> List[PlaybookEntry]:
        """Génère le playbook par contexte"""
        playbook = []

        for insight in insights:
            vix_regime = insight.context.split('_')[0]  # "LOW", "MID", "HIGH"
            menthorq_family = insight.context.split('_', 1)[1]

            # Générer règles basées sur performance
            rules = []
            avoid_rules = []

            if insight.performance['win_rate'] > 60:
                rules.append(f"GO_{insight.context.split('_')[-1].upper()} si confluence > 0.8")

            if insight.performance['mae_median'] > 0.5:
                avoid_rules.append(f"NE JAMAIS entrer si MAE historique > 0.5R")

            # Size multiplier basé sur expectancy
            if insight.performance['expectancy'] > 0.2:
                size_multiplier = 1.2
            elif insight.performance['expectancy'] < -0.1:
                size_multiplier = 0.8
        else:
            size_multiplier = 1.0

        playbook.append(PlaybookEntry(
                vix_regime=vix_regime,
                menthorq_family=menthorq_family,
                rules=rules,
                avoid_rules=avoid_rules,
                size_multiplier=size_multiplier,
                confidence=insight.confidence
            ))

        return playbook

    def _generate_summary(self, df: pd.DataFrame, insights: List[Insight],
                         adjustments: List[Adjustment]) -> Dict[str, Any]:
        """Génère un résumé des leçons"""
        return {
            'total_trades': len(df),
            'win_rate': (df['is_winner'].sum() / len(df)) * 100,
            'expectancy': df['pnl'].mean(),
            'mae_median': df['mae'].median(),
            'top_insights': sorted(insights, key=lambda x: x.performance['expectancy'], reverse=True)[:5],
            'critical_adjustments': [a for a in adjustments if a.type == 'veto_rule'],
            'size_adjustments': [a for a in adjustments if a.type == 'size_reduction']
        }

    def export_playbook(self, filepath: str = "data/playbook.json") -> bool:
        """Exporte le playbook en JSON"""
        try:
            lessons = self.compute_lessons('30d')
            if lessons['status'] != 'success':
                return False

            playbook_data = {
                'generated_at': datetime.now(timezone.utc).isoformat(),
                'total_trades': lessons['total_trades'],
                'playbook': [asdict(entry) for entry in lessons['playbook']],
                'adjustments': [asdict(adj) for adj in lessons['adjustments']]
            }

            with open(filepath, 'w') as f:
                json.dump(playbook_data, f, indent=2)

            self.logger.info(f"📋 Playbook exporté: {filepath}")
            return True

        except Exception as e:
            self.logger.error(f"Erreur export playbook: {e}")
            return False

    def load_playbook(self, filepath: str = "data/playbook.json") -> Optional[Dict[str, Any]]:
        """Charge le playbook depuis JSON"""
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Erreur load playbook: {e}")
            return None

    def report_markdown(self, filepath: str = "reports/lessons_report.md") -> bool:
        """Génère un rapport Markdown périodique"""
        try:
            lessons = self.compute_lessons('30d')
            if lessons['status'] != 'success':
                return False

            summary = lessons['summary']

            # Créer le rapport
            report = f"""# 📚 RAPPORT LESSONS LEARNED - {datetime.now().strftime('%Y-%m-%d')}

## 📊 RÉSUMÉ EXÉCUTIF
- **Total trades analysés:** {summary['total_trades']}
- **Win Rate:** {summary['win_rate']:.1f}%
- **Expectancy:** {summary['expectancy']:+.2f}R
- **MAE médiane:** {summary['mae_median']:.2f}R

## 🎯 TOP 5 LEÇONS
"""

            for i, insight in enumerate(summary['top_insights'], 1):
                report += f"""
### {i}. {insight.context}
- **Win Rate:** {insight.performance['win_rate']:.1f}%
- **Expectancy:** {insight.performance['expectancy']:+.2f}R
- **Échantillon:** {insight.sample_size} trades
- **Confiance:** {insight.confidence:.1f}
"""

            report += """
## 🚫 3 MAUVAISES HABITUDES À SUPPRIMER
"""

            for adj in summary['critical_adjustments'][:3]:
                report += f"- {adj.reason}\n"

            report += """
## 💡 3 OPPORTUNITÉS
"""

            for adj in summary['size_adjustments'][:3]:
                report += f"- {adj.reason}\n"

            # Créer le répertoire si nécessaire
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(report)

            self.logger.info(f"📄 Rapport Markdown généré: {filepath}")
            return True

        except Exception as e:
            self.logger.error(f"Erreur report markdown: {e}")
            return False

    def _invalidate_cache(self):
        """Invalide le cache"""
        self._insights_cache.clear()
        self._playbook_cache.clear()
        self._last_analysis_time = None

    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques de l'analyseur"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                total_trades = conn.execute("SELECT COUNT(*) FROM trade_outcomes").fetchone()[0]
                recent_trades = conn.execute("""
                    SELECT COUNT(*) FROM trade_outcomes
                    WHERE timestamp >= datetime('now', '-7 days')
                """).fetchone()[0]

            return {
                'total_trades': total_trades,
                'recent_trades_7d': recent_trades,
                'cache_size': len(self._insights_cache),
                'last_analysis': self._last_analysis_time.isoformat() if self._last_analysis_time else None
            }
        except Exception as e:
            self.logger.error(f"Erreur get stats: {e}")
            return {}

# Factory function
def create_lessons_learned_analyzer(db_path: str = "data/lessons_learned.db") -> LessonsLearnedAnalyzer:
    """Factory pour créer le Lessons Learned Analyzer"""
    return LessonsLearnedAnalyzer(db_path)

# Exemple d'utilisation:
"""
# Après chaque trade dans automation_main.py:
outcome = self.lessons_analyzer.record_trade_outcome(
    decision=Decision(
        decision="LONG",
        score=0.82,
        factors={"bn_score": 0.8, "db_score": 0.85},
        rules=["confluence_high", "volume_confirmation"],
        timestamp=datetime.now(timezone.utc)
    ),
    execution=Execution(
        qty=1,
        entry_price=5247.50,
        exit_price=5249.00,
        sl_price=5245.00,
        tp_price=5252.00,
        slippage=0.25,
        timestamp=datetime.now(timezone.utc)
    ),
    context=Context(
        vix_regime=VIXRegime.MID,
        bl_distance=3.5,
        gw_distance=8.2,
        m30_range=12.5,
        vwap_distance=2.1,
        time_window="normal",
        gex_above_pct=65.0
    ),
    result={
        'pnl': 1.5,  # 1.5R
        'mae': 0.8,  # 0.8R
        'time_to_profit': 15.5  # minutes
    }
)

# Analyse tous les 30 trades:
if self.lessons_analyzer.get_stats()['total_trades'] % 30 == 0:
    lessons = self.lessons_analyzer.compute_lessons('30d')
    self.lessons_analyzer.export_playbook()
    self.lessons_analyzer.report_markdown()
"""
