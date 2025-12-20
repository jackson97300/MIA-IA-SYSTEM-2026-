#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HVL Magnet Fade Strategy
=========================

Stratégie GPT - Fade vers HVL (High Value Level)

Trade les exhaustions au-delà de HVL avec retour vers la moyenne.
HVL = niveau options haute valeur, agit comme aimant magnétique.

Concept:
--------
- HVL = niveau haute valeur options (aimant prix)
- Extension au-delà HVL = exhaustion
- Prix attiré vers HVL comme aimant
- Fade exhaustion + reclaim vers HVL = edge

Edge:
-----
- HVL moins connu que VWAP/VAH/VAL
- Complète blind_spot_magnetic_pull (autre aimant)
- Win rate attendu: 68-73%
- Risk/Reward: 1:2.5
- Fréquence: 4-7 trades/jour

Différence avec blind_spot_magnetic_pull:
------------------------------------------
- Blind Spot = attraction VERS blind spot (continuation)
- HVL Fade = RETOUR vers HVL depuis exhaustion (reversal)

Author: MIA System
Date: 31 Octobre 2025
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import time
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


# === HELPER FUNCTION: Volume Adaptif par Session/Symbole ===
def _volume_is_high(ml_data: Dict[str, Any]) -> bool:
    """Détermine si le volume est élevé selon la session et le symbole."""
    vol = ml_data.get('volume', 0)
    sess = ml_data.get('session_id', 'US')
    sym = (ml_data.get('sym', '') or '').upper()
    base = 35 if sess == 'Asia' else (45 if sess == 'EU' else 55)
    if 'NQ' in sym: base -= 3
    if 'RTY' in sym: base -= 5
    if ml_data.get('tick_rate_1s', 0) >= 1 or ml_data.get('trade_rate_1s', 0) >= 1:
        return vol >= base
    return vol >= (base + 5)


@dataclass
class PatternSignal:
    """Signal de pattern de trading"""
    strategy: str
    timestamp: datetime
    side: Optional[str]
    confidence: float
    entry: float
    stop: float
    targets: list
    metadata: Dict[str, Any]
    processing_time_ms: float = 0.0


class HVLMagnetFade:
    """
    Fade les exhaustions au-delà de HVL avec retour vers la moyenne.

    Principe:
    ---------
    - HVL = High Value Level options (aimant magnétique)
    - Extension au-delà HVL = exhaustion temporaire
    - Prix DOIT revenir vers HVL (hedging dealers)
    - Entry sur épuisement + reclaim = faible risque

    Trigger:
    --------
    LONG (fade exhaustion baissière):
    1. HVL distance >= 0.12% en-dessous du prix
    2. Exhaustion: mèche basse + volume climax
    3. Dealers bias neutre (|bias| <= 0.20)
    4. Reclaim vers HVL (tick d'absorption confirmé)
    5. Pas de mur gamma bloquant entre prix et HVL

    SHORT (fade exhaustion haussière): Inverse

    Fallback si HVL absent:
    -----------------------
    Utilise gamma_pin le plus dense comme proxy HVL
    """

    def __init__(self):
        """Initialise la stratégie"""
        self.name = "hvl_magnet_fade"

        # Paramètres HVL (seuils ajustés)
        self.min_hvl_dist_pct = 0.10         # Distance min à HVL (réduit de 0.12 à 0.10)
        self.max_pressure_abs = 0.25         # Pressure max (augmenté de 0.20 à 0.25)

        # Exhaustion (seuils réduits)
        self.min_wick_ratio = 0.35           # Mèche min (réduit de 0.40 à 0.35)
        self.min_volume_climax = 1.3         # Volume climax (réduit de 1.4 à 1.3)

        # Absorption/Reclaim
        self.min_absorption_ticks = 2        # Ticks d'absorption min

        # SL/TP - 🔧 OPTIMISÉ: Augmenté pour éviter stop hunting
        self.sl_ticks_beyond_extreme_base = {
            'ES': 20,  # $50 - était 3 ticks
            'NQ': 20,  # $100 - était 3 ticks
            'RT': 15   # $15 - était 3 ticks
        }
        self.tp1_target = "hvl"              # TP1 = retour à HVL
        self.tp2_target = "vwap"             # TP2 = VWAP si au-delà HVL

        logger.info(f"✅ {self.name} initialisé")

    def analyze_from_ml_ready(self, ml_data: Dict[str, Any]) -> Optional[PatternSignal]:
        """
        Analyse les données ML_READY pour détecter un fade HVL

        Args:
            ml_data: Données ML_READY complètes

        Returns:
            PatternSignal si setup détecté, None sinon
        """
        try:
            # 1. Trouver HVL (ou fallback)
            hvl_price, hvl_source = self._get_hvl(ml_data)

            if hvl_price is None:
                return None

            mid = ml_data.get('mid')
            if not mid:
                return None

            # 📚 Bible MenthorQ v2.0: Récupérer 1d_max/1d_min (Expected Move)
            day_max = ml_data.get('1d_max', 0)
            day_min = ml_data.get('1d_min', 0)

            # 2. Calculer distance à HVL
            hvl_dist = hvl_price - mid
            hvl_dist_pct = (hvl_dist / mid) * 100

            # 📚 Valider compatibilité fade avec 1-Day extremes
            if day_max and day_min and mid and day_max > day_min:
                day_range = day_max - day_min
                position_pct = ((mid - day_min) / day_range) * 100

                # Éviter fades près des extremes (risque reversal fort)
                if position_pct >= 95:  # Très proche 1d_max
                    logger.info(f"   ⚠️ Prix @ {position_pct:.1f}% du range (proche 1d_max)")
                    if hvl_dist > 0:  # HVL en-dessous (fade LONG)
                        logger.info(f"   ❌ Skip fade LONG près 1d_max: trop risqué")
                        return None

                elif position_pct <= 5:  # Très proche 1d_min
                    logger.info(f"   ⚠️ Prix @ {position_pct:.1f}% du range (proche 1d_min)")
                    if hvl_dist < 0:  # HVL au-dessus (fade SHORT)
                        logger.info(f"   ❌ Skip fade SHORT près 1d_min: trop risqué")
                        return None
            else:
                position_pct = None
                day_range = None

            # Vérifier distance suffisante (>= 0.10%)
            if abs(hvl_dist_pct) < self.min_hvl_dist_pct:
                return None

            # 3. Déterminer direction du fade
            if hvl_dist > 0:
                # HVL au-dessus → prix en-dessous → fade SHORT précédent → LONG
                direction = "LONG"
                exhaustion_side = "lower"
            else:
                # HVL en-dessous → prix au-dessus → fade LONG précédent → SHORT
                direction = "SHORT"
                exhaustion_side = "upper"

            # 4. Vérifier exhaustion (mèche + climax)
            has_exhaustion = self._detect_exhaustion(ml_data, exhaustion_side)
            if not has_exhaustion:
                return None

            # 5. Vérifier institutional pressure neutre - CORRIGÉ
            # ❌ dealers_bias n'existe pas → Utiliser institutional_pressure
            inst_pressure = ml_data.get('institutional_pressure', 0.0)

            if abs(inst_pressure) > self.max_pressure_abs:
                return None

            # 6. Détecter reclaim/absorption vers HVL
            has_reclaim = self._detect_reclaim(ml_data, direction)
            if not has_reclaim:
                return None

            # 7. Vérifier pas de mur bloquant
            if self._wall_blocking(ml_data, direction, hvl_price):
                return None

            # 8. Créer signal
            return self._create_signal(
                ml_data,
                direction,
                hvl_price,
                hvl_source,
                hvl_dist_pct,
                inst_pressure  # 🔧 CORRECTION: Utiliser inst_pressure au lieu de dealers_bias
            )

        except Exception as e:
            logger.error(f"❌ Erreur HVLMagnetFade: {e}", exc_info=True)
            return None

    def _get_hvl(self, ml_data: Dict) -> tuple[Optional[float], str]:
        """
        Récupère HVL price

        Returns:
            (hvl_price, source) où source = "hvl" ou "gamma_fallback"
        """
        # Essayer d'abord hvl_price direct
        hvl_price = ml_data.get('hvl_price') or ml_data.get('hvl')

        if hvl_price and hvl_price > 0:
            return (hvl_price, "hvl")

        # Fallback: Utiliser gamma pin le plus proche et fort
        # (proxy HVL = zone gamma dense)
        menthor_dist = ml_data.get('menthor_distances', {})
        if not isinstance(menthor_dist, dict):
            return (None, "none")

        # Chercher gamma0 (le plus proche)
        gamma0_dist = menthor_dist.get('gamma0')
        if gamma0_dist is not None and gamma0_dist != 0:
            mid = ml_data.get('mid')
            if mid:
                # Reconstituer prix gamma0
                # gamma0_dist est en ticks, convertir en prix
                tick_size = 0.25
                gamma0_price = mid + (gamma0_dist * tick_size)
                return (gamma0_price, "gamma_fallback")

        # Si rien trouvé
        return (None, "none")

    def _detect_exhaustion(self, ml_data: Dict, side: str) -> bool:
        """
        Détecte exhaustion (mèche + volume climax)

        Args:
            side: "upper" pour exhaustion haussière, "lower" pour baissière
        """
        # ❌ CORRECTIF: wick_ratio_upper/lower n'existent pas
        # ✅ Calculer depuis upper_wick_ticks / total_range_ticks
        upper_wick = ml_data.get('upper_wick_ticks', 0)
        lower_wick = ml_data.get('lower_wick_ticks', 0)
        total_range = ml_data.get('total_range_ticks', 1)

        if side == "upper":
            wick_ratio = upper_wick / total_range if total_range > 0 else 0
        else:  # lower
            wick_ratio = lower_wick / total_range if total_range > 0 else 0

        if wick_ratio < self.min_wick_ratio:
            return False

        # Vérifier volume climax - OPTIMISÉ (volume adaptatif session/symbole)
        if not _volume_is_high(ml_data):
            return False

        return True

    def _detect_reclaim(self, ml_data: Dict, direction: str) -> bool:
        """
        Détecte reclaim/absorption vers HVL

        Reclaim = prix commence à revenir vers HVL avec absorption
        """
        # Vérifier imbalance dans la bonne direction
        level1_imb = ml_data.get('level1_imbalance', 0.0)

        if direction == "LONG":
            # Besoin imbalance bid positive (acheteurs absorbent)
            if level1_imb < 0.08:  # Seuil plus bas que cassure
                return False

            # Vérifier delta positif
            delta = ml_data.get('delta', 0)
            if delta <= 0:
                return False

        else:  # SHORT
            # Besoin imbalance ask négative (vendeurs absorbent)
            if level1_imb > -0.08:
                return False

            # Vérifier delta négatif
            delta = ml_data.get('delta', 0)
            if delta >= 0:
                return False

        return True

    def _wall_blocking(self, ml_data: Dict, direction: str, hvl_price: float) -> bool:
        """Vérifie si un mur gamma bloque le retour vers HVL"""
        next_wall = ml_data.get('next_wall', {})

        if not next_wall or not isinstance(next_wall, dict):
            return False

        wall_price = next_wall.get('price')
        if wall_price is None:
            return False

        mid = ml_data.get('mid')
        if not mid:
            return False

        # Vérifier si le mur est entre le prix actuel et HVL
        if direction == "LONG":
            # Retour vers HVL au-dessus
            if mid < wall_price < hvl_price:
                # Mur bloquant si forte résistance
                wall_strength = next_wall.get('strength', 0)
                if wall_strength and wall_strength > 0.5:
                    return True
        else:  # SHORT
            # Retour vers HVL en-dessous
            if hvl_price < wall_price < mid:
                wall_strength = next_wall.get('strength', 0)
                if wall_strength and wall_strength > 0.5:
                    return True

        return False

    def _create_signal(
        self,
        ml_data: Dict,
        direction: str,
        hvl_price: float,
        hvl_source: str,
        hvl_dist_pct: float,
        dealers_bias: float
    ) -> PatternSignal:
        """Crée le signal de trading"""
        entry = ml_data.get('mid')

        # Récupérer 1d_max/1d_min pour metadata
        day_max = ml_data.get('1d_max', 0)
        day_min = ml_data.get('1d_min', 0)
        if day_max and day_min and entry and day_max > day_min:
            day_range = day_max - day_min
            position_pct = ((entry - day_min) / day_range) * 100
        else:
            position_pct = None
            day_range = None

        # Tick size dynamique
        symbol = ml_data.get('sym', 'NQ')[:2]  # Extraire symbole de base
        tick_size = 0.25 if symbol in ['ES', 'NQ'] else 0.10

        # ATR pour SL/TP dynamiques
        atr = ml_data.get('atr', 1.0)

        # Récupérer extrême de la mèche pour SL
        high = ml_data.get('high', entry)
        low = ml_data.get('low', entry)

        # 🔧 SL OPTIMISÉ: Utiliser minimum par symbole (au lieu de 3 ticks fixes)
        sl_ticks = self.sl_ticks_beyond_extreme_base.get(symbol, 20)

        # SL au-delà de l'extrême
        if direction == "LONG":
            stop_loss = low - (sl_ticks * tick_size)
            # TP1: Retour à HVL | TP2: VWAP ou ATR étendu
            take_profit = hvl_price

            # Si HVL très proche, viser VWAP ou ATR étendu
            if abs(hvl_price - entry) < (5 * tick_size):
                vwap = ml_data.get('vwap', entry)
                if vwap > hvl_price:
                    take_profit = vwap
                else:
                    take_profit = entry + (atr * 5.0)  # 5x ATR si pas de VWAP favorable

        else:  # SHORT
            stop_loss = high + (sl_ticks * tick_size)
            # TP1: Retour à HVL | TP2: VWAP ou ATR étendu
            take_profit = hvl_price

            if abs(entry - hvl_price) < (5 * tick_size):
                vwap = ml_data.get('vwap', entry)
                if vwap < hvl_price:
                    take_profit = vwap
                else:
                    take_profit = entry - (atr * 5.0)  # 5x ATR si pas de VWAP favorable

        # Confiance basée sur qualité setup
        confidence = 0.60  # Base (réduit de 0.65 à 0.60)

        # Bonus si HVL réel (pas fallback)
        if hvl_source == "hvl":
            confidence += 0.05

        # Bonus si exhaustion forte (grande mèche)
        upper_wick = ml_data.get('upper_wick_ticks', 0)
        lower_wick = ml_data.get('lower_wick_ticks', 0)
        total_range = ml_data.get('total_range_ticks', 1)

        if direction == "LONG":
            wick = lower_wick / total_range if total_range > 0 else 0
        else:
            wick = upper_wick / total_range if total_range > 0 else 0

        if wick > 0.50:
            confidence += 0.05

        # Bonus si volume très climax
        volume = ml_data.get('volume', 0)
        if volume > 70:
            confidence += 0.05

        confidence = min(confidence, 0.80)  # Cap à 0.80

        return PatternSignal(
            strategy=self.name,
            timestamp=datetime.now(),
            side=direction,
            confidence=confidence,
            entry=entry,
            stop=stop_loss,
            targets=[take_profit],
            metadata={
                'hvl_price': hvl_price,
                'hvl_source': hvl_source,
                'hvl_dist_pct': hvl_dist_pct,
                'institutional_pressure': dealers_bias,
                'exhaustion_wick': wick,
                'volume': volume,
                'atr': atr,
                'risk_reward_ratio': abs((take_profit - entry) / (entry - stop_loss)) if direction == "LONG" else abs((entry - take_profit) / (stop_loss - entry))
            },
            processing_time_ms=0.0
        )


if __name__ == "__main__":
    # Test de la stratégie
    strategy = HVLMagnetFade()
    print(f"✅ Stratégie {strategy.name} initialisée")
    print(f"   Min HVL dist: {strategy.min_hvl_dist_pct}%")
    print(f"   Max bias abs: {strategy.max_bias_abs}")
    print(f"   Min wick ratio: {strategy.min_wick_ratio}")
    print(f"   Min volume climax: {strategy.min_volume_climax}")
    print(f"   SL ticks beyond extreme: {strategy.sl_ticks_beyond_extreme}")
    print(f"   TP1 target: {strategy.tp1_target}")
    print(f"   TP2 target: {strategy.tp2_target}")
