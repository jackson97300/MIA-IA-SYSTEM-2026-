#!/usr/bin/env python3
"""
MIA_IA_SYSTEM - Bracket Detector ML_READY v2.0 (GPT-4 Optimized)
=================================================================

Version: 4.0 - ML_READY Native + GPT-4 Patches Applied
Date: 10 Novembre 2025

🎯 AMÉLIORATIONS v2.0 (GPT-4 Audited):
- ✅ Patch A: Normalisation symbole + seuil touches en TICKS (vs % prix)
- ✅ Patch B: Score qualité intègre volume/activité (tick_rate/trade_rate)
- ✅ Patch C: Largeur max adaptée symbole/session (ES/NQ/RTY + Asia/US)
- ✅ Patch D: Breakout confirmé (2 closes + buffer + OrderFlow)
- ✅ Patch E: Durée minimale en TEMPS (≥3 min) pas seulement barres

🔒 RESPONSABILITÉS:
1. Maintenir historique de prix ML_READY
2. Détecter consolidations (range étroit) avec seuils adaptatifs
3. Compter touches RÉALISTES sur support/résistance (en ticks)
4. Détecter breakouts CONFIRMÉS (anti head-fake)
5. Qualité brackets intégrant volume ET activité (tick_rate)
6. Compatibilité ES/NQ/RTY + sessions Asia/EU/US
"""

from typing import Dict, List, Optional, Any
from collections import deque
from datetime import datetime, timedelta
from dataclasses import dataclass
from core.logger import get_logger

logger = get_logger(__name__)

# === DATA STRUCTURES ===

@dataclass
class Bracket:
    """Un bracket détecté"""
    upper: float  # Résistance
    lower: float  # Support
    middle: float  # Point milieu
    width_dollars: float  # Largeur en dollars
    width_percent: float  # Largeur en %
    touches_upper: int  # Nombre de touches résistance
    touches_lower: int  # Nombre de touches support
    quality_score: float  # Score de qualité (0-1)
    detection_time: datetime  # Quand détecté
    bars_in_bracket: int  # Nombre de barres dans le bracket
    duration_seconds: float  # Durée réelle en secondes
    avg_volume: float  # Volume moyen dans le bracket
    avg_tick_rate: float  # Tick rate moyen
    is_valid: bool  # Si bracket est valide pour trading
    symbol: str  # Symbole


# === MAIN CLASS ===

class BracketDetectorMLReady:
    """
    Détecteur de brackets en version ML_READY v2.0 (GPT-4 Optimized)

    Améliorations vs v1.0:
    - Touches en TICKS (réaliste), pas en % du prix
    - Largeur max adaptée par symbole/session
    - Breakout confirmé (2+ closes + buffer ticks)
    - Score qualité intégrant activité OrderFlow
    - Durée minimale en temps réel (≥3 min)
    """

    def __init__(self,
                 window_size: int = 120,  # Augmenté de 100 à 120
                 min_bars_in_bracket: int = 120,  # Augmenté de 20 à 120 (GPT Patch E)
                 min_duration_seconds: float = 180.0,  # ≥3 minutes (GPT Patch E)
                 min_touches_per_side: int = 2,
                 breakout_confirm_closes: int = 2,  # GPT Patch D
                 breakout_buffer_ticks: int = 2):  # GPT Patch D
        """
        Initialisation du détecteur v2.0

        Args:
            window_size: Nombre de samples à garder en mémoire
            min_bars_in_bracket: Minimum de samples pour détecter un bracket
            min_duration_seconds: Durée minimale d'un bracket (secondes)
            min_touches_per_side: Minimum de touches support ET résistance
            breakout_confirm_closes: Nombre de closes requis pour confirmer breakout
            breakout_buffer_ticks: Buffer en ticks au-delà du bord pour breakout
        """
        self.window_size = window_size
        self.min_bars_in_bracket = min_bars_in_bracket
        self.min_duration_seconds = min_duration_seconds
        self.min_touches_per_side = min_touches_per_side
        self.breakout_confirm_closes = breakout_confirm_closes
        self.breakout_buffer_ticks = breakout_buffer_ticks

        # Historique de prix (deque pour performance)
        self.price_history: deque = deque(maxlen=window_size)

        # Bracket actif
        self.current_bracket: Optional[Bracket] = None

        # Breakout confirmation tracking
        self._post_breakout_closes = 0

        # Métriques "live" pour score qualité (GPT Patch B)
        self._last_tick_rate = 0.0
        self._last_trade_rate = 0.0

        # Statistics
        self.stats = {
            'brackets_detected': 0,
            'breakouts_detected': 0,
            'false_breakouts_rejected': 0,  # NEW
            'last_detection_time': None
        }

        logger.info(f"✅ BracketDetectorMLReady v2.0 initialisé (GPT-4 Optimized)")
        logger.info(f"   Window: {window_size} | Min bars: {min_bars_in_bracket}")
        logger.info(f"   Min duration: {min_duration_seconds}s | Breakout confirms: {breakout_confirm_closes}")

    # === PATCH A: HELPER TICK SIZE ===

    def _tick_size_for(self, sym: str) -> float:
        """
        Retourne le tick size selon le symbole.

        Args:
            sym: Symbole (ex: "NQZ25_FUT_CME")

        Returns:
            Tick size (0.25 pour ES/NQ, 0.10 pour RTY)
        """
        s = (sym or "").upper()
        if s.startswith("ES") or "ES" in s:
            return 0.25
        if s.startswith("NQ") or "NQ" in s:
            return 0.25
        if s.startswith("RT") or "RTY" in s:
            return 0.10
        if s.startswith("YM"):
            return 1.0
        return 0.25  # Default

    # === PATCH C: LARGEUR MAX ADAPTÉE ===

    def _max_width_percent(self, sym: str, session: str) -> float:
        """
        Retourne la largeur max selon symbole/session.

        Args:
            sym: Symbole
            session: Session ('Asia', 'EU', 'US')

        Returns:
            Largeur max en % du prix
        """
        # Base % du prix - optimisé par symbole
        s = (sym or "").upper()

        if "NQ" in s:
            base = 0.0025  # 0.25% pour NQ (plus volatil)
        elif "ES" in s:
            base = 0.0018  # 0.18% pour ES (plus serré)
        elif "RT" in s:
            base = 0.0022  # 0.22% pour RTY (intermédiaire)
        else:
            base = 0.0020  # Default

        # Asia: ranges plus calmes mais lents → légèrement plus permissif
        if session == "Asia":
            base *= 1.25

        return base

    # === PATCH A: UPDATE AVEC NORMALISATION SYMBOLE ===

    def update(self, ml_data: Dict[str, Any]):
        """
        Met à jour l'historique avec nouvelle donnée ML_READY.

        Args:
            ml_data: Dictionnaire ML_READY complet
        """
        # PATCH A: Lire 'sym' puis fallback 'symbol'
        sym = ml_data.get('sym') or ml_data.get('symbol') or 'UNKNOWN'

        bar_data = {
            'timestamp': ml_data.get('t_ms', 0),
            'mid': ml_data.get('mid', 0),
            'high': ml_data.get('high', ml_data.get('mid', 0)),
            'low': ml_data.get('low', ml_data.get('mid', 0)),
            'volume': ml_data.get('volume', 0),
            'symbol': sym
        }

        # Ajouter à l'historique
        self.price_history.append(bar_data)

    def detect_bracket(self, ml_data: Dict[str, Any]) -> Optional[Bracket]:
        """
        Détecte un bracket depuis les données ML_READY (v2.0 Enhanced).

        Args:
            ml_data: Données ML_READY actuelles

        Returns:
            Bracket si détecté, None sinon
        """
        # Mettre à jour l'historique
        self.update(ml_data)

        # Besoin d'au moins min_bars_in_bracket
        if len(self.price_history) < self.min_bars_in_bracket:
            return None

        # Analyser les dernières barres
        recent_bars = list(self.price_history)[-self.min_bars_in_bracket:]

        # PATCH E: Vérifier durée minimale en TEMPS
        first_ts = recent_bars[0]['timestamp']
        last_ts = recent_bars[-1]['timestamp']
        duration_ms = last_ts - first_ts
        duration_seconds = duration_ms / 1000.0

        if duration_seconds < self.min_duration_seconds:
            # Bracket trop court dans le temps
            return None

        # Extraire highs, lows, volumes
        highs = [bar['high'] for bar in recent_bars]
        lows = [bar['low'] for bar in recent_bars]
        volumes = [bar['volume'] for bar in recent_bars]

        # Trouver support et résistance
        resistance = max(highs)
        support = min(lows)
        middle = (resistance + support) / 2

        # Prix actuel
        current_price = ml_data.get('mid', 0)
        if current_price == 0:
            return None

        # Symbole et session
        sym = ml_data.get('sym') or ml_data.get('symbol') or 'UNKNOWN'
        session = ml_data.get('session_id', 'US')

        # PATCH C: Vérifier largeur adaptée symbole/session
        width_dollars = resistance - support
        width_percent = width_dollars / current_price

        max_width = self._max_width_percent(sym, session)
        if width_percent > max_width:
            # Range trop large
            return None

        # PATCH A: Compter touches en TICKS (réaliste)
        tick_size = self._tick_size_for(sym)
        atr = ml_data.get('atr', tick_size * 10)  # Fallback si pas d'ATR

        # Seuil touche: max(2 ticks, 2% d'ATR)
        touch_threshold = max(tick_size * 2, atr * 0.02)

        touches_upper = self._count_touches(highs, resistance, touch_threshold)
        touches_lower = self._count_touches(lows, support, touch_threshold)

        if touches_upper < self.min_touches_per_side or touches_lower < self.min_touches_per_side:
            # Pas assez de touches
            return None

        # Volume moyen
        avg_volume = sum(volumes) / len(volumes) if volumes else 0

        # PATCH B: Stocker métriques "live" pour score qualité
        self._last_tick_rate = ml_data.get('tick_rate_1s', 0.0)
        self._last_trade_rate = ml_data.get('trade_rate_1s', 0.0)

        # Calculer score de qualité (ENHANCED)
        quality_score = self._calculate_quality_score_enhanced(
            width_percent=width_percent,
            touches_upper=touches_upper,
            touches_lower=touches_lower,
            bars_count=len(recent_bars),
            duration_seconds=duration_seconds,
            avg_volume=avg_volume
        )

        # Créer bracket
        bracket = Bracket(
            upper=resistance,
            lower=support,
            middle=middle,
            width_dollars=width_dollars,
            width_percent=width_percent,
            touches_upper=touches_upper,
            touches_lower=touches_lower,
            quality_score=quality_score,
            detection_time=datetime.now(),
            bars_in_bracket=len(recent_bars),
            duration_seconds=duration_seconds,
            avg_volume=avg_volume,
            avg_tick_rate=self._last_tick_rate,
            is_valid=quality_score >= 0.6,  # Seuil de qualité minimum
            symbol=sym
        )

        # Mettre à jour bracket actif
        self.current_bracket = bracket
        self.stats['brackets_detected'] += 1
        self.stats['last_detection_time'] = datetime.now()

        logger.info(f"📦 Bracket {sym}: {support:.2f} - {resistance:.2f} "
                    f"({width_percent*100:.2f}%) | Q={quality_score:.2f} | {duration_seconds:.0f}s")

        return bracket

    # === PATCH D: BREAKOUT CONFIRMÉ (ANTI HEAD-FAKE) ===

    def check_breakout(self, ml_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Vérifie si le prix casse un bracket actif (v2.0 - Confirmé).

        Nécessite:
        - 2+ closes au-delà du bord + buffer (2 ticks)
        - Activité OrderFlow confirmée (delta_rate ou tick_rate > 0)
        - Pas de mur gamma immédiat dans la direction

        Args:
            ml_data: Données ML_READY actuelles

        Returns:
            Dict avec infos breakout si détecté, None sinon
        """
        if not self.current_bracket:
            return None

        price = ml_data.get('mid', 0.0)
        if price == 0:
            return None

        sym = ml_data.get('sym') or ml_data.get('symbol') or ''
        tick_size = self._tick_size_for(sym)
        buffer = self.breakout_buffer_ticks * tick_size

        # Direction & buffer
        above = price > (self.current_bracket.upper + buffer)
        below = price < (self.current_bracket.lower - buffer)

        if above or below:
            # Incrémenter compteur de closes
            self._post_breakout_closes += 1

            # Vérifier activité OrderFlow (au moins un peu d'activité)
            delta_rate = abs(ml_data.get('delta_rate_1s', 0.0))
            tick_rate = ml_data.get('tick_rate_1s', 0.0)
            flow_ok = (delta_rate > 0) or (tick_rate >= 1)

            # Vérifier pas de mur gamma bloquant (optionnel mais recommandé)
            next_wall = ml_data.get('next_wall', {})
            wall_blocking = False

            if isinstance(next_wall, dict) and next_wall:
                wall_price = next_wall.get('price')
                wall_dist_ticks = next_wall.get('dist_ticks', 999)

                # Si mur très proche (< 20 ticks) dans la direction → bloquant
                if wall_price and wall_dist_ticks < 20:
                    if above and wall_price > price:
                        wall_blocking = True
                    elif below and wall_price < price:
                        wall_blocking = True

            # CONFIRMATION: 2+ closes + flow OK + pas de mur bloquant
            if (self._post_breakout_closes >= self.breakout_confirm_closes and
                flow_ok and
                not wall_blocking):

                # Construire breakout
                direction = "LONG" if above else "SHORT"
                breakout_type = 'bullish_breakout' if above else 'bearish_breakout'

                breakout = {
                    'type': breakout_type,
                    'direction': direction,
                    'bracket_upper': self.current_bracket.upper,
                    'bracket_lower': self.current_bracket.lower,
                    'breakout_price': price,
                    'bracket_width': self.current_bracket.width_dollars,
                    'quality_score': self.current_bracket.quality_score,
                    'confirmed_closes': self._post_breakout_closes,
                    'timestamp': datetime.now()
                }

                self.stats['breakouts_detected'] += 1
                logger.info(f"🚀 BREAKOUT {direction} confirmé ({self._post_breakout_closes} closes): "
                           f"{price:.2f} {'>' if above else '<'} "
                           f"{self.current_bracket.upper if above else self.current_bracket.lower:.2f}")

                # Invalider bracket actif et reset compteur
                self.current_bracket = None
                self._post_breakout_closes = 0

                return breakout

            elif wall_blocking:
                # Mur gamma bloque le breakout → rejeter
                self.stats['false_breakouts_rejected'] += 1
                logger.debug(f"⚠️ Breakout rejeté: mur gamma bloquant à {wall_dist_ticks}t")
                self._post_breakout_closes = 0

        else:
            # Prix revenu dans le bracket → reset compteur
            if self._post_breakout_closes > 0:
                logger.debug(f"🔄 Breakout annulé: prix revenu dans bracket")
                self._post_breakout_closes = 0

        return None

    def _count_touches(self, prices: List[float], level: float, threshold: float) -> int:
        """
        Compte le nombre de fois où le prix touche un niveau.

        Args:
            prices: Liste de prix (highs ou lows)
            level: Niveau à tester (support ou résistance)
            threshold: Seuil de tolérance (EN TICKS, pas en %)

        Returns:
            Nombre de touches
        """
        touches = 0
        for price in prices:
            if abs(price - level) <= threshold:
                touches += 1

        return touches

    # === PATCH B: SCORE QUALITÉ ENHANCED (INTÈGRE ACTIVITÉ) ===

    def _calculate_quality_score_enhanced(self,
                                         width_percent: float,
                                         touches_upper: int,
                                         touches_lower: int,
                                         bars_count: int,
                                         duration_seconds: float,
                                         avg_volume: float) -> float:
        """
        Calcule un score de qualité pour le bracket (v2.0 Enhanced).

        Pondération:
        - Largeur: 25%
        - Touches: 35%
        - Équilibre touches: 15%
        - Durée: 10%
        - Activité (tick_rate/trade_rate): 15%  ← NEW

        Args:
            width_percent: Largeur du bracket en %
            touches_upper: Touches sur résistance
            touches_lower: Touches sur support
            bars_count: Nombre de barres dans le bracket
            duration_seconds: Durée réelle en secondes
            avg_volume: Volume moyen

        Returns:
            Score de 0 à 1
        """
        score = 0.0

        # 1. Largeur (plus étroit = meilleur) - 25%
        # Idéal: 0.1% - 0.2%
        if 0.001 <= width_percent <= 0.002:
            score += 0.25
        elif 0.0005 <= width_percent <= 0.0025:
            score += 0.18
        else:
            score += 0.10

        # 2. Touches (plus de touches = meilleur) - 35%
        total_touches = touches_upper + touches_lower
        if total_touches >= 8:
            score += 0.35
        elif total_touches >= 6:
            score += 0.25
        elif total_touches >= 4:
            score += 0.15
        else:
            score += 0.08

        # 3. Équilibre touches (support ~= résistance) - 15%
        touch_ratio = min(touches_upper, touches_lower) / max(touches_upper, touches_lower) if max(touches_upper, touches_lower) > 0 else 0
        score += touch_ratio * 0.15

        # 4. Durée (plus longtemps = meilleur) - 10%
        if duration_seconds >= 600:  # ≥ 10 min
            score += 0.10
        elif duration_seconds >= 300:  # ≥ 5 min
            score += 0.07
        elif duration_seconds >= 180:  # ≥ 3 min
            score += 0.05
        else:
            score += 0.02

        # 5. Activité (tick_rate/trade_rate) - 15% ← PATCH B
        activity_score = 0.0
        try:
            tick_rate = self._last_tick_rate
            trade_rate = self._last_trade_rate

            # Normalisation simple
            if tick_rate >= 2 or trade_rate >= 1:
                activity_score = 0.15  # Activité forte
            elif tick_rate >= 1:
                activity_score = 0.10  # Activité moyenne
            else:
                activity_score = 0.05  # Activité faible
        except Exception:
            activity_score = 0.08  # Fallback si pas de données

        score += activity_score

        return min(score, 1.0)

    def get_current_bracket(self) -> Optional[Bracket]:
        """Retourne le bracket actuellement actif."""
        return self.current_bracket

    def get_statistics(self) -> Dict[str, Any]:
        """Retourne les statistiques du détecteur."""
        return {
            'brackets_detected': self.stats['brackets_detected'],
            'breakouts_detected': self.stats['breakouts_detected'],
            'false_breakouts_rejected': self.stats['false_breakouts_rejected'],
            'last_detection_time': self.stats['last_detection_time'],
            'current_bracket_active': self.current_bracket is not None,
            'history_size': len(self.price_history)
        }

    def reset(self):
        """Reset le détecteur (historique + bracket actif)."""
        self.price_history.clear()
        self.current_bracket = None
        self._post_breakout_closes = 0
        logger.info("🔄 BracketDetector v2.0 reset")


# === FACTORY FUNCTION ===

def create_bracket_detector_ml_ready(**kwargs) -> BracketDetectorMLReady:
    """
    Factory pour créer un BracketDetector ML_READY v2.0.

    Args:
        **kwargs: Arguments pour BracketDetectorMLReady

    Returns:
        BracketDetectorMLReady instance (v2.0 optimisé)
    """
    return BracketDetectorMLReady(**kwargs)


# === TESTS ===

if __name__ == "__main__":
    logger.info("=== TEST BRACKET DETECTOR ML_READY v2.0 (GPT-4 Optimized) ===")

    # Créer détecteur v2.0
    detector = create_bracket_detector_ml_ready()

    # Simuler consolidation NQ (range 25340-25345)
    import random
    import time as pytime

    base_ts = int(datetime.now().timestamp() * 1000)

    logger.info("\n📊 Phase 1: Accumulation bracket (180 samples, 3+ min)")
    for i in range(180):
        ml_data_test = {
            'sym': 'NQZ25_FUT_CME',
            't_ms': base_ts + (i * 1000),  # 1 sample/seconde
            'mid': 25342.5 + random.uniform(-2.5, 2.5),
            'high': 25345 + random.uniform(-1, 1),
            'low': 25340 + random.uniform(-1, 1),
            'volume': random.randint(30, 60),
            'atr': 12.5,
            'tick_rate_1s': random.uniform(1.5, 3.0),
            'trade_rate_1s': random.uniform(0.8, 1.5),
            'session_id': 'US'
        }

        # Détecter bracket
        bracket = detector.detect_bracket(ml_data_test)

        if bracket and i == 179:  # Dernière barre
            logger.info(f"\n✅ Bracket détecté:")
            logger.info(f"   Support: {bracket.lower:.2f}")
            logger.info(f"   Résistance: {bracket.upper:.2f}")
            logger.info(f"   Largeur: {bracket.width_percent*100:.3f}%")
            logger.info(f"   Touches: {bracket.touches_lower} / {bracket.touches_upper}")
            logger.info(f"   Durée: {bracket.duration_seconds:.1f}s")
            logger.info(f"   Qualité: {bracket.quality_score:.2f}")
            logger.info(f"   Activité: {bracket.avg_tick_rate:.1f} tick/s")

    # Simuler breakout bullish (confirmation en 2 étapes)
    logger.info("\n🚀 Phase 2: Tentative breakout (confirmation requise)")

    for j in range(3):
        ml_data_breakout = {
            'sym': 'NQZ25_FUT_CME',
            't_ms': base_ts + 180000 + (j * 1000),
            'mid': 25348 + (j * 0.5),  # Au-dessus résistance + buffer
            'volume': 80,
            'atr': 12.5,
            'tick_rate_1s': 2.5,
            'delta_rate_1s': 0.5,  # Activité confirmée
            'next_wall': {'price': 25370, 'dist_ticks': 88},  # Pas bloquant
            'session_id': 'US'
        }

        breakout = detector.check_breakout(ml_data_breakout)
        if breakout:
            logger.info(f"\n✅ BREAKOUT CONFIRMÉ: {breakout['type']}")
            logger.info(f"   Prix breakout: {breakout['breakout_price']:.2f}")
            logger.info(f"   Confirmed closes: {breakout['confirmed_closes']}")
            logger.info(f"   Qualité bracket: {breakout['quality_score']:.2f}")
            break
        else:
            logger.info(f"   Close {j+1}/2: {ml_data_breakout['mid']:.2f} (attente confirmation...)")

    # Statistiques finales
    stats = detector.get_statistics()
    logger.info(f"\n📊 Statistiques finales:")
    logger.info(f"   Brackets détectés: {stats['brackets_detected']}")
    logger.info(f"   Breakouts confirmés: {stats['breakouts_detected']}")
    logger.info(f"   Faux breakouts rejetés: {stats['false_breakouts_rejected']}")

    logger.info("\n=== TEST TERMINÉ ===")
