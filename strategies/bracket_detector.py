#!/usr/bin/env python3
"""
MIA_IA_SYSTEM - Bracket Detector
Détecte les brackets (ranges) valides pour le trading
Critères: touches, volume, DOM, confluence, sessions
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime, time
from collections import deque

from core.logger import get_logger
from config.bracket_config import BracketConfig, create_default_bracket_config

logger = get_logger(__name__)


@dataclass
class BracketBound:
    """Une borne de bracket (haut ou bas)"""
    price: float
    touches: int = 0
    last_touch_time: Optional[datetime] = None
    touch_times: List[datetime] = field(default_factory=list)
    volume_at_touches: List[float] = field(default_factory=list)
    dom_imbalance_at_touches: List[float] = field(default_factory=list)
    confluences: List[str] = field(default_factory=list)
    rejection_patterns: List[str] = field(default_factory=list)


@dataclass
class Bracket:
    """Un bracket détecté"""
    upper_bound: BracketBound
    lower_bound: BracketBound

    # Métadonnées
    symbol: str = ""
    detection_time: Optional[datetime] = None
    expiration_time: Optional[datetime] = None

    # Statistiques
    width_ticks: float = 0.0
    width_dollars: float = 0.0
    middle_price: float = 0.0

    # Volume & Liquidité
    avg_volume_bounds: float = 0.0
    avg_volume_middle: float = 0.0
    volume_ratio: float = 0.0  # bounds / middle

    # Qualité
    quality_score: float = 0.0
    session: str = ""
    session_quality: int = 0

    # État
    is_valid: bool = False
    invalidation_reason: str = ""
    trades_taken: int = 0
    last_trade_time: Optional[datetime] = None

    # Fatigue
    is_fatigued: bool = False
    fatigue_reasons: List[str] = field(default_factory=list)


class BracketDetector:
    """Détecteur de brackets pour le trading"""

    def __init__(self, config: Optional[BracketConfig] = None):
        self.config = config or create_default_bracket_config()
        self.logger = logger

        # Historique de prix pour détecter les touches
        self.price_history: deque = deque(maxlen=1000)

        # Brackets actifs
        self.active_brackets: Dict[str, Bracket] = {}

        # Statistiques
        self.brackets_detected_today: int = 0
        self.brackets_invalidated_today: int = 0

        self.logger.info("🎯 BracketDetector initialisé")
        self.logger.info(f"  - Min touches: {self.config.min_touches_per_side}")
        self.logger.info(f"  - Min width ES: {self.config.min_width_ticks.get('ES', 20)} ticks")
        self.logger.info(f"  - TP strategy: {self.config.tp_strategy}")

    def detect_bracket(self, market_data: Dict) -> Optional[Bracket]:
        """
        Détecte un bracket dans les données de marché

        Args:
            market_data: Données complètes du dumper

        Returns:
            Bracket détecté ou None
        """
        try:
            symbol = market_data.get('sym', '').split('_')[0]  # ESZ25 ou NQZ25

            # 1. Vérifier conditions macro
            if not self._check_macro_conditions(market_data):
                return None

            # 2. Identifier les bornes potentielles
            bounds = self._identify_potential_bounds(market_data)
            if not bounds or len(bounds) < 2:
                return None

            # 3. Analyser chaque paire de bornes
            for upper_price, lower_price in self._generate_bound_pairs(bounds):

                # Créer bracket candidat
                bracket = self._create_bracket_candidate(
                    symbol, upper_price, lower_price, market_data
                )

                # Valider le bracket
                if self._validate_bracket(bracket, market_data):
                    self.logger.info(f"✅ Bracket détecté: {bracket.lower_bound.price:.2f} - {bracket.upper_bound.price:.2f}")
                    self.brackets_detected_today += 1
                    return bracket

            return None

        except Exception as e:
            self.logger.error(f"❌ Erreur détection bracket: {e}")
            return None

    def _check_macro_conditions(self, market_data: Dict) -> bool:
        """Vérifie les conditions macro (VIX, trend, divergence)"""
        try:
            # VIX trop élevé
            vix = market_data.get('vix', 0)
            if vix > self.config.no_trade_vix_threshold:
                self.logger.debug(f"⚠️ VIX trop élevé: {vix:.1f}")
                return False

            # TODO: Vérifier trend fort du jour
            # TODO: Vérifier divergence ES/NQ
            # TODO: Vérifier news upcoming

            return True

        except Exception as e:
            self.logger.error(f"❌ Erreur check macro: {e}")
            return False

    def _identify_potential_bounds(self, market_data: Dict) -> List[float]:
        """Identifie les prix potentiels pour les bornes"""
        bounds = []

        try:
            # 1. VWAP bands
            vwap_up1 = market_data.get('vwap_up1')
            vwap_dn1 = market_data.get('vwap_dn1')
            if vwap_up1:
                bounds.append(float(vwap_up1))
            if vwap_dn1:
                bounds.append(float(vwap_dn1))

            # 2. Value Area
            vah = market_data.get('vva', {}).get('vah')
            val = market_data.get('vva', {}).get('val')
            if vah:
                bounds.append(float(vah))
            if val:
                bounds.append(float(val))

            # 3. GEX levels (top 5)
            for i in range(1, 6):
                gex = market_data.get(f'gex_{i}')
                if gex:
                    bounds.append(float(gex))

            # 4. Blind spots (top 5)
            for i in range(5):
                blind_spot = market_data.get(f'blind_spot_{i}')
                if blind_spot:
                    bounds.append(float(blind_spot))

            # 5. PVWAP
            pvwap = market_data.get('pvwap')
            if pvwap:
                bounds.append(float(pvwap))

            # Dédupliquer et trier
            bounds = sorted(list(set(bounds)))

            return bounds

        except Exception as e:
            self.logger.error(f"❌ Erreur identification bornes: {e}")
            return []

    def _generate_bound_pairs(self, bounds: List[float]) -> List[Tuple[float, float]]:
        """Génère des paires de bornes (upper, lower)"""
        pairs = []

        for i in range(len(bounds)):
            for j in range(i+1, len(bounds)):
                upper = bounds[j]
                lower = bounds[i]
                pairs.append((upper, lower))

        return pairs

    def _create_bracket_candidate(self, symbol: str, upper_price: float,
                                   lower_price: float, market_data: Dict) -> Bracket:
        """Crée un bracket candidat"""

        # Bornes
        upper_bound = BracketBound(price=upper_price)
        lower_bound = BracketBound(price=lower_price)

        # Calculer width
        tick_size = 0.25 if 'ES' in symbol else 0.25  # ES et NQ même tick size
        width_dollars = upper_price - lower_price
        width_ticks = width_dollars / tick_size
        middle_price = (upper_price + lower_price) / 2.0

        # Créer bracket
        bracket = Bracket(
            upper_bound=upper_bound,
            lower_bound=lower_bound,
            symbol=symbol,
            detection_time=datetime.now(),
            width_ticks=width_ticks,
            width_dollars=width_dollars,
            middle_price=middle_price
        )

        return bracket

    def _validate_bracket(self, bracket: Bracket, market_data: Dict) -> bool:
        """Valide un bracket selon tous les critères"""

        validation_checks = []

        # 1. Taille minimum
        min_ticks = self.config.min_width_ticks.get(bracket.symbol.split('Z')[0], 20)
        if bracket.width_ticks < min_ticks:
            bracket.invalidation_reason = f"Width trop petit: {bracket.width_ticks:.0f} < {min_ticks}"
            return False
        validation_checks.append("✅ Width")

        # 2. Confluence sur les bornes
        if self.config.require_level_confluence:
            upper_conf = self._count_confluences(bracket.upper_bound.price, market_data)
            lower_conf = self._count_confluences(bracket.lower_bound.price, market_data)

            if upper_conf < self.config.min_confluences or lower_conf < self.config.min_confluences:
                bracket.invalidation_reason = f"Pas assez de confluences (upper={upper_conf}, lower={lower_conf})"
                return False
            validation_checks.append(f"✅ Confluence (U={upper_conf}, L={lower_conf})")

        # 3. Session quality
        session = market_data.get('session_id', 'unknown')
        session_quality = self.config.session_quality.get(session.lower(), 0)

        if session_quality < self.config.min_session_quality:
            bracket.invalidation_reason = f"Session quality insuffisante: {session_quality} < {self.config.min_session_quality}"
            return False
        validation_checks.append(f"✅ Session {session} (quality={session_quality})")

        bracket.session = session
        bracket.session_quality = session_quality

        # 4. TODO: Vérifier touches (nécessite historique)
        # 5. TODO: Vérifier volume ratio
        # 6. TODO: Vérifier DOM imbalance

        # Bracket validé
        bracket.is_valid = True
        bracket.quality_score = self._calculate_quality_score(bracket, market_data)

        self.logger.info(f"🎯 Bracket validé: {' | '.join(validation_checks)}")
        self.logger.info(f"   Quality score: {bracket.quality_score:.2f}")

        return True

    def _count_confluences(self, price: float, market_data: Dict, tolerance_ticks: int = 3) -> int:
        """Compte les confluences à un prix donné"""
        confluences = 0
        tick_size = 0.25

        try:
            # GEX levels
            for i in range(1, 11):
                gex = market_data.get(f'gex_{i}')
                if gex and abs(float(gex) - price) <= (tolerance_ticks * tick_size):
                    confluences += 1

            # VWAP bands
            for band in ['vwap_up1', 'vwap_up2', 'vwap_dn1', 'vwap_dn2']:
                val = market_data.get(band)
                if val and abs(float(val) - price) <= (tolerance_ticks * tick_size):
                    confluences += 1

            # Blind spots
            for i in range(9):
                blind_spot = market_data.get(f'blind_spot_{i}')
                if blind_spot and abs(float(blind_spot) - price) <= (tolerance_ticks * tick_size):
                    confluences += 1

            # Value Area
            vah = market_data.get('vva', {}).get('vah')
            val = market_data.get('vva', {}).get('val')
            if vah and abs(float(vah) - price) <= (tolerance_ticks * tick_size):
                confluences += 1
            if val and abs(float(val) - price) <= (tolerance_ticks * tick_size):
                confluences += 1

            return confluences

        except Exception as e:
            self.logger.error(f"❌ Erreur count confluences: {e}")
            return 0

    def _calculate_quality_score(self, bracket: Bracket, market_data: Dict) -> float:
        """Calcule un score de qualité du bracket (0-1)"""
        score = 0.0

        try:
            # Width (0.2 points)
            optimal_ticks = self.config.optimal_width_ticks.get(bracket.symbol.split('Z')[0], 30)
            if bracket.width_ticks >= optimal_ticks:
                score += 0.2
            else:
                score += 0.1

            # Session (0.3 points)
            session_score = bracket.session_quality / 5.0  # Normalisé 0-1
            score += session_score * 0.3

            # Confluences (0.3 points)
            upper_conf = self._count_confluences(bracket.upper_bound.price, market_data)
            lower_conf = self._count_confluences(bracket.lower_bound.price, market_data)
            avg_conf = (upper_conf + lower_conf) / 2.0
            conf_score = min(avg_conf / 5.0, 1.0)  # Normalisé, cap à 1.0
            score += conf_score * 0.3

            # VIX (0.2 points)
            vix = market_data.get('vix', 20)
            if vix < 15:
                score += 0.2  # Parfait
            elif vix < 25:
                score += 0.1  # Bon
            # Sinon 0

            return min(score, 1.0)

        except Exception as e:
            self.logger.error(f"❌ Erreur calcul quality score: {e}")
            return 0.5

    def check_bracket_fatigue(self, bracket: Bracket, market_data: Dict) -> bool:
        """Vérifie si le bracket est fatigué (stop trading)"""
        fatigue_reasons = []

        try:
            # 1. Nombre de trades
            if bracket.trades_taken >= self.config.max_trades_per_bracket:
                fatigue_reasons.append(f"Max trades atteint ({bracket.trades_taken})")

            # 2. Durée totale
            if bracket.detection_time:
                duration_minutes = (datetime.now() - bracket.detection_time).total_seconds() / 60
                if duration_minutes > self.config.max_duration_minutes:
                    fatigue_reasons.append(f"Durée max atteinte ({duration_minutes:.0f}min)")

            # 3. TODO: Volume décroissant
            # 4. TODO: Touches trop fréquentes
            # 5. TODO: DOM imbalance faible

            if fatigue_reasons:
                bracket.is_fatigued = True
                bracket.fatigue_reasons = fatigue_reasons
                self.logger.info(f"⚠️ Bracket fatigué: {', '.join(fatigue_reasons)}")
                return True

            return False

        except Exception as e:
            self.logger.error(f"❌ Erreur check fatigue: {e}")
            return False

    def check_bracket_invalidation(self, bracket: Bracket, market_data: Dict) -> bool:
        """Vérifie si le bracket est invalidé (cassure)"""
        try:
            current_price = float(market_data.get('close', 0))
            tick_size = 0.25
            breakout_distance = self.config.breakout_threshold_ticks * tick_size

            # Cassure haute
            if current_price > (bracket.upper_bound.price + breakout_distance):
                bracket.invalidation_reason = f"Cassure haute: {current_price:.2f} > {bracket.upper_bound.price:.2f}"
                self.brackets_invalidated_today += 1
                return True

            # Cassure basse
            if current_price < (bracket.lower_bound.price - breakout_distance):
                bracket.invalidation_reason = f"Cassure basse: {current_price:.2f} < {bracket.lower_bound.price:.2f}"
                self.brackets_invalidated_today += 1
                return True

            return False

        except Exception as e:
            self.logger.error(f"❌ Erreur check invalidation: {e}")
            return False
    
    def update_market_data(self, symbol: str, market_data: Dict):
        """
        Met à jour l'historique de marché pour un symbole
        
        Args:
            symbol: Symbole (ES, NQ, etc.)
            market_data: Données de marché
        """
        try:
            # Extraire prix actuel
            price = market_data.get('close', market_data.get('mid', 0))
            
            if price > 0:
                # Ajouter à l'historique
                self.price_history.append({
                    'symbol': symbol,
                    'price': price,
                    'timestamp': market_data.get('timestamp', pd.Timestamp.now()),
                    'volume': market_data.get('volume', 0)
                })
        
        except Exception as e:
            self.logger.debug(f"⚠️ Erreur update market data: {e}")
    
    def get_active_brackets(self, symbol: str) -> List[Bracket]:
        """
        Retourne les brackets actifs pour un symbole
        
        Args:
            symbol: Symbole (ES, NQ, etc.)
            
        Returns:
            Liste des brackets actifs
        """
        return [b for b in self.active_brackets.values() if b.symbol == symbol]


# === FACTORY ===

def create_bracket_detector(config: Optional[BracketConfig] = None) -> BracketDetector:
    """Factory pour créer un BracketDetector"""
    return BracketDetector(config)


# === EXPORTS ===

__all__ = [
    'Bracket',
    'BracketBound',
    'BracketDetector',
    'create_bracket_detector'
]
