#!/usr/bin/env python3
"""
Rejection Diagnostic Logger - Module de diagnostic en temps réel
Affiche périodiquement POURQUOI aucun trade n'est pris

**COMPLÉMENTAIRE** à `DecisionMessengerMLReady` :
- DecisionMessenger → Messages détaillés PAR SIGNAL (EXECUTE/WAIT)
- RejectionDiagnosticLogger → Rapport AGRÉGÉ toutes les 5 min (POURQUOI pas de trades)

Author: MIA Trading System
Version: 1.0.0 - Phase 3.5
"""

import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class RejectionStats:
    """Statistiques de rejets sur une période"""
    period_start: datetime
    period_end: datetime
    total_cycles: int = 0
    
    # Catégories de rejet
    no_signal_generated: int = 0  # Aucun signal par stratégies
    ml_filter_low_confidence: int = 0  # ML confiance < threshold
    market_context_rejected: int = 0  # Context filter (VIX, spread, etc)
    risk_limit_hit: int = 0  # Limites de risque atteintes
    safety_kill_switch: int = 0  # Safety Kill Switch actif
    data_quality_issues: int = 0  # Données ML_READY invalides
    time_restrictions: int = 0  # Hors horaires trading
    cooldown_active: int = 0  # Cooldown entre trades
    
    # Détails ML
    ml_avg_confidence: List[float] = field(default_factory=list)
    ml_below_threshold_count: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    
    # Détails Context
    vix_spikes_count: int = 0
    spread_too_wide_count: int = 0
    liquidity_issues_count: int = 0
    
    # Compteurs par symbole
    rejections_by_symbol: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    
    def get_total_rejections(self) -> int:
        """Retourne le nombre total de rejets"""
        return (
            self.no_signal_generated +
            self.ml_filter_low_confidence +
            self.market_context_rejected +
            self.risk_limit_hit +
            self.safety_kill_switch +
            self.data_quality_issues +
            self.time_restrictions +
            self.cooldown_active
        )
    
    def get_top_rejection_reason(self) -> str:
        """Retourne la raison de rejet la plus fréquente"""
        reasons = {
            "Aucun signal généré": self.no_signal_generated,
            "ML confiance insuffisante": self.ml_filter_low_confidence,
            "Contexte marché défavorable": self.market_context_rejected,
            "Limites de risque": self.risk_limit_hit,
            "Safety Kill Switch": self.safety_kill_switch,
            "Qualité données": self.data_quality_issues,
            "Restrictions horaires": self.time_restrictions,
            "Cooldown actif": self.cooldown_active
        }
        
        if not any(reasons.values()):
            return "Aucun rejet enregistré"
        
        return max(reasons.items(), key=lambda x: x[1])[0]


class RejectionDiagnosticLogger:
    """
    Logger de diagnostic pour comprendre pourquoi aucun trade n'est pris
    
    Affiche périodiquement (toutes les 5 minutes) :
    - Nombre de signaux rejetés
    - Raisons principales de rejet
    - Statistiques ML (confiance moyenne)
    - Recommandations pour améliorer le taux d'acceptance
    """
    
    def __init__(self, log_interval_minutes: int = 5):
        """
        Args:
            log_interval_minutes: Intervalle entre chaque rapport (défaut: 5 min)
        """
        self.log_interval_seconds = log_interval_minutes * 60
        self.last_report_time = time.time()
        
        # Stats de la période actuelle
        self.current_stats = RejectionStats(
            period_start=datetime.now(),
            period_end=datetime.now() + timedelta(minutes=log_interval_minutes)
        )
        
        # Historique des périodes (gardé en mémoire pour analyse)
        self.historical_stats: List[RejectionStats] = []
        
        logger.info(f"✅ RejectionDiagnosticLogger initialisé (rapport toutes les {log_interval_minutes} min)")
    
    def record_cycle(self, symbol: str):
        """Enregistre un cycle d'évaluation"""
        self.current_stats.total_cycles += 1
    
    def record_rejection(
        self,
        symbol: str,
        reason: str,
        ml_confidence: Optional[float] = None,
        ml_threshold: Optional[float] = None,
        context_details: Optional[Dict[str, Any]] = None
    ):
        """
        Enregistre un rejet de signal
        
        Args:
            symbol: ES, NQ, RTY
            reason: Raison du rejet (NO_SIGNAL, ML, CONTEXT, RISK, SAFETY, DATA, TIME, COOLDOWN)
            ml_confidence: Confiance ML si rejet ML
            ml_threshold: Seuil ML si rejet ML
            context_details: Détails contextuels (VIX, spread, etc)
        """
        self.current_stats.rejections_by_symbol[symbol] += 1
        
        # Catégoriser le rejet
        if reason == "NO_SIGNAL":
            self.current_stats.no_signal_generated += 1
        elif reason == "ML":
            self.current_stats.ml_filter_low_confidence += 1
            if ml_confidence is not None:
                self.current_stats.ml_avg_confidence.append(ml_confidence)
            if ml_threshold is not None:
                direction = "UP" if ml_confidence else "DOWN"  # Simplification
                self.current_stats.ml_below_threshold_count[f"{symbol}/{direction}"] += 1
        elif reason == "CONTEXT":
            self.current_stats.market_context_rejected += 1
            if context_details:
                if context_details.get('vix_spike'):
                    self.current_stats.vix_spikes_count += 1
                if context_details.get('spread_too_wide'):
                    self.current_stats.spread_too_wide_count += 1
                if context_details.get('liquidity_low'):
                    self.current_stats.liquidity_issues_count += 1
        elif reason == "RISK":
            self.current_stats.risk_limit_hit += 1
        elif reason == "SAFETY":
            self.current_stats.safety_kill_switch += 1
        elif reason == "DATA":
            self.current_stats.data_quality_issues += 1
        elif reason == "TIME":
            self.current_stats.time_restrictions += 1
        elif reason == "COOLDOWN":
            self.current_stats.cooldown_active += 1
    
    def should_log_report(self) -> bool:
        """Vérifie s'il est temps de logger un rapport"""
        return (time.time() - self.last_report_time) >= self.log_interval_seconds
    
    def generate_and_log_report(self) -> str:
        """
        Génère et affiche le rapport de diagnostic
        
        Returns:
            Rapport formaté en string
        """
        stats = self.current_stats
        total_rejections = stats.get_total_rejections()
        
        # Calculer confiance ML moyenne
        avg_ml_conf = sum(stats.ml_avg_confidence) / len(stats.ml_avg_confidence) if stats.ml_avg_confidence else 0.0
        
        # Top raison
        top_reason = stats.get_top_rejection_reason()
        
        # Construire le rapport
        report_lines = [
            "",
            "═" * 80,
            "📊 RAPPORT DIAGNOSTIC - POURQUOI PAS DE TRADES ?",
            "═" * 80,
            f"⏱️  Période : {stats.period_start.strftime('%H:%M')} → {datetime.now().strftime('%H:%M')} " 
            f"({(datetime.now() - stats.period_start).seconds // 60} min)",
            f"🔄 Cycles : {stats.total_cycles}",
            f"🚫 Rejets : {total_rejections}",
            "",
            "📉 RAISONS DE REJET (Top → Bottom) :",
            ""
        ]
        
        # Trier les raisons par fréquence
        reasons_sorted = [
            ("🚫 Aucun signal généré", stats.no_signal_generated),
            ("🤖 ML confiance < seuil", stats.ml_filter_low_confidence),
            ("🌐 Contexte marché", stats.market_context_rejected),
            ("⚠️  Limites de risque", stats.risk_limit_hit),
            ("🚨 Safety Kill Switch", stats.safety_kill_switch),
            ("📊 Qualité données", stats.data_quality_issues),
            ("⏰ Restrictions horaires", stats.time_restrictions),
            ("⏸️  Cooldown actif", stats.cooldown_active)
        ]
        
        for label, count in sorted(reasons_sorted, key=lambda x: x[1], reverse=True):
            if count > 0:
                pct = (count / total_rejections * 100) if total_rejections > 0 else 0
                report_lines.append(f"   {label:30s} : {count:4d} ({pct:5.1f}%)")
        
        report_lines.extend([
            "",
            "🎯 ANALYSE DÉTAILLÉE :",
            ""
        ])
        
        # Détails ML
        if stats.ml_filter_low_confidence > 0:
            report_lines.append(f"   🤖 ML Confiance Moyenne : {avg_ml_conf:.2%}")
            if stats.ml_below_threshold_count:
                report_lines.append("   🎯 Rejets ML par marché/direction :")
                for key, count in sorted(stats.ml_below_threshold_count.items(), key=lambda x: x[1], reverse=True):
                    report_lines.append(f"      - {key} : {count} rejets")
        
        # Détails Context
        if stats.market_context_rejected > 0:
            report_lines.append(f"   🌐 Context - VIX Spikes : {stats.vix_spikes_count}")
            report_lines.append(f"   🌐 Context - Spread trop large : {stats.spread_too_wide_count}")
            report_lines.append(f"   🌐 Context - Liquidité faible : {stats.liquidity_issues_count}")
        
        # Rejets par symbole
        if stats.rejections_by_symbol:
            report_lines.append("")
            report_lines.append("   📈 Rejets par Symbole :")
            for symbol, count in sorted(stats.rejections_by_symbol.items(), key=lambda x: x[1], reverse=True):
                pct_of_total = (count / total_rejections * 100) if total_rejections > 0 else 0
                report_lines.append(f"      - {symbol:3s} : {count:4d} ({pct_of_total:5.1f}%)")
        
        # Recommandations
        report_lines.extend([
            "",
            "💡 RECOMMANDATIONS :",
            ""
        ])
        
        if top_reason == "Aucun signal généré":
            report_lines.append("   ⚠️  Les stratégies ne génèrent aucun signal")
            report_lines.append("   → Vérifier les conditions de marché (volatilité, volume)")
            report_lines.append("   → Vérifier les paramètres des stratégies")
        elif top_reason == "ML confiance insuffisante":
            report_lines.append("   ⚠️  ML rejette la majorité des signaux (confiance < seuil)")
            report_lines.append(f"   → Confiance moyenne : {avg_ml_conf:.2%}")
            report_lines.append("   → Envisager de baisser les thresholds ML (mode ADVISORY)")
            report_lines.append("   → Analyser les features ML (qualité données)")
        elif top_reason == "Contexte marché défavorable":
            report_lines.append("   ⚠️  Conditions de marché défavorables")
            report_lines.append("   → VIX élevé, spread large, ou liquidité faible")
            report_lines.append("   → Attendre des conditions plus favorables")
        elif top_reason == "Safety Kill Switch":
            report_lines.append("   🚨 Safety Kill Switch ACTIF - Trading bloqué")
            report_lines.append("   → Vérifier logs pour la raison (PnL, DTC, VIX)")
        
        report_lines.extend([
            "",
            "═" * 80,
            ""
        ])
        
        # Logger le rapport
        for line in report_lines:
            logger.info(line)
        
        # Sauvegarder dans l'historique
        self.historical_stats.append(self.current_stats)
        
        # Réinitialiser pour la période suivante
        self.current_stats = RejectionStats(
            period_start=datetime.now(),
            period_end=datetime.now() + timedelta(minutes=self.log_interval_seconds // 60)
        )
        self.last_report_time = time.time()
        
        return "\n".join(report_lines)
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Retourne les stats résumées pour la période actuelle"""
        stats = self.current_stats
        total_rejections = stats.get_total_rejections()
        
        return {
            'total_cycles': stats.total_cycles,
            'total_rejections': total_rejections,
            'top_reason': stats.get_top_rejection_reason(),
            'ml_avg_confidence': sum(stats.ml_avg_confidence) / len(stats.ml_avg_confidence) if stats.ml_avg_confidence else 0.0,
            'rejections_by_symbol': dict(stats.rejections_by_symbol),
            'period_start': stats.period_start.isoformat(),
            'period_end': datetime.now().isoformat()
        }


def create_rejection_diagnostic_logger(log_interval_minutes: int = 5) -> RejectionDiagnosticLogger:
    """Factory pour créer un RejectionDiagnosticLogger"""
    return RejectionDiagnosticLogger(log_interval_minutes=log_interval_minutes)

