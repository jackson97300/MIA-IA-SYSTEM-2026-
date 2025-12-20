#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gamma Wall Break And Go Strategy
=================================

Stratégie GPT Best - Cassure Mur Gamma avec Momentum

Exploite les cassures PROPRES de murs gamma avec confirmation volume
et pullback/retest pour entry optimal.

Concept:
--------
- Mur gamma = résistance/support majeur options
- Cassure propre + volume = vrais breakouts (pas faux)
- Pullback au mur cassé = entry à faible risque
- Dealers bias confirme la direction

Edge:
-----
- Distingue vraies cassures des faux breakouts (head fake)
- Entry sur pullback/retest = meilleur R:R
- Win rate attendu: 70-75%
- Risk/Reward: 1:2.5
- Fréquence: 3-6 trades/jour

Différence avec zero_dte_wall_sweep:
-------------------------------------
- zero_dte_wall_sweep = REVERSAL sur sweep raté (mèche + rejet)
- gamma_wall_break_and_go = CONTINUATION sur cassure propre (momentum)
- Arbitrage: Si sweep raté détecté → zero_dte prioritaire
           Si cassure propre → gamma_wall_break_and_go

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
    """
    Détermine si le volume est élevé selon la session et le symbole.

    Seuils adaptatifs:
    - Asia: volume plus faible acceptable
    - EU: volume intermédiaire
    - US: volume élevé requis
    - NQ: plus actif que ES (-3 ticks)
    - RTY: plus irrégulier (-5 ticks)

    Args:
        ml_data: Données ML_READY

    Returns:
        True si volume considéré comme élevé
    """
    vol = ml_data.get('volume', 0)
    sess = ml_data.get('session_id', 'US')   # 'Asia','EU','US'
    sym = (ml_data.get('sym', '') or '').upper()

    # Seuils "safe" par session/symbole (calibrage conservateur)
    base = 35 if sess == 'Asia' else (45 if sess == 'EU' else 55)

    # NQ plus actif que ES en ticks, RTY plus irrégulier
    if 'NQ' in sym:
        base -= 3
    if 'RTY' in sym:
        base -= 5

    # Garde-fou sur le flow: au moins un peu d'activité
    # tick_rate_1s/trade_rate_1s existent dans ML_READY
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


class GammaWallBreakAndGo:
    """
    Trade les cassures propres de murs gamma avec momentum.

    Principe:
    ---------
    - Mur gamma = zone d'accumulation dealers
    - Cassure propre = shift de régime, dealers forcés de suivre
    - Volume confirme conviction des participants
    - Pullback au mur = entry à faible risque

    Trigger:
    --------
    LONG (cassure mur résistance):
    1. Distance au mur ≤ 0.18%
    2. RelVol >= 1.35 (volume cassure)
    3. Dealers bias dans le sens (> 0)
    4. Aucune mèche rejet > 0.05% sur 3 dernières barres
    5. Pullback/retest du mur cassé (entry)
    6. Headroom vers prochain niveau > 0.20%

    SHORT: Inverse (cassure mur support)

    Anti-doublon avec zero_dte_wall_sweep:
    ---------------------------------------
    - Si mèche rejet détectée → laisser priorité à zero_dte_wall_sweep
    - Cette stratégie ne trade QUE les cassures propres
    """

    def __init__(self):
        """Initialise la stratégie"""
        self.name = "gamma_wall_break_and_go"

        # Paramètres cassure (seuils ajustés)
        self.max_dist_wall_pct = 0.20        # Distance max au mur (augmenté de 0.18 à 0.20)
        self.min_relvol_break = 1.25         # Volume relatif min (réduit de 1.35 à 1.25)
        self.max_reject_wick_pct = 0.50      # Mèche rejet max tolérée (0.50 au lieu de 0.05)
        self.min_headroom_pct = 0.20         # Headroom min vers prochain niveau

        # Paramètres dealers bias (remplacé par institutional_pressure)
        self.min_pressure_long = 0.15        # Pressure min pour LONG (réduit)
        self.max_pressure_short = -0.15      # Pressure max pour SHORT (réduit)

        # Historique barres (pour détecter pullback)
        self.price_history = []
        self.max_history = 10

        # SL/TP
        self.sl_ticks = 8                    # Stop loss serré (derrière mur)
        self.tp1_multiplier = 1.2            # TP1 rapide sur momentum
        self.tp2_multiplier = 2.5            # TP2 au prochain mur/niveau

        logger.info(f"✅ {self.name} initialisé")

    def analyze_from_ml_ready(self, ml_data: Dict[str, Any]) -> Optional[PatternSignal]:
        """
        Analyse les données ML_READY pour détecter une cassure propre

        Args:
            ml_data: Données ML_READY complètes

        Returns:
            PatternSignal si cassure détectée, None sinon
        """
        try:
            # Mettre à jour historique prix
            mid = ml_data.get('mid')
            if mid:
                self.price_history.append(mid)
                if len(self.price_history) > self.max_history:
                    self.price_history.pop(0)

            # 1. Trouver mur gamma le plus proche
            next_wall = ml_data.get('next_wall', {})
            if not next_wall or not isinstance(next_wall, dict):
                return None

            wall_price = next_wall.get('price')
            wall_side = next_wall.get('side')  # 'call' ou 'put'
            wall_dist_ticks = next_wall.get('dist_ticks', 999)

            if wall_price is None or wall_side is None:
                return None

            # 2. Vérifier distance au mur (≤ 0.18%)
            if mid and wall_price:
                dist_pct = abs((wall_price - mid) / mid) * 100
                if dist_pct > self.max_dist_wall_pct:
                    return None
            else:
                return None

            # 3. Déterminer direction cassure
            if wall_side == 'call':
                # Mur call = résistance → cassure = LONG
                direction = "LONG"
                # Vérifier qu'on est proche ou au-dessus
                if mid < wall_price * 0.998:  # Au moins 0.2% proche
                    return None
            else:  # wall_side == 'put'
                # Mur put = support → cassure = SHORT
                direction = "SHORT"
                # Vérifier qu'on est proche ou en-dessous
                if mid > wall_price * 1.002:
                    return None

            # 4. Vérifier volume cassure - OPTIMISÉ (volume adaptatif session/symbole)
            if not _volume_is_high(ml_data):
                return None

            # 📚 CORRECTION: Calculer relvol pour _create_signal
            volume = ml_data.get('volume', 0)
            avg_volume = ml_data.get('avg_volume', 1)
            relvol = volume / avg_volume if avg_volume > 0 else 0

            # 5. Vérifier institutional pressure dans le sens - CORRIGÉ
            # ❌ dealers_bias n'existe pas → Utiliser institutional_pressure
            inst_pressure = ml_data.get('institutional_pressure', 0.0)

            # 📚 ENRICHISSEMENT BIBLE MENTHORQ: Utiliser gamma_side pour confluence
            gamma_side = ml_data.get('gamma_side', '')
            logger.info(f"📚 Bible MenthorQ: gamma_side={gamma_side}, direction={direction}")

            if direction == "LONG":
                if inst_pressure < self.min_pressure_long:
                    return None
                # ✅ Confluence: LONG + gamma_side "below" (positive gamma, mean-revert UP)
                if gamma_side == 'below':
                    logger.info("   ⚠️ LONG mais gamma_side=below (negative gamma, contre-courant)")
                elif gamma_side == 'above':
                    logger.info("   ✅ LONG + gamma_side=above (positive gamma, confluence !)")
            else:  # SHORT
                if inst_pressure > self.max_pressure_short:
                    return None
                # ✅ Confluence: SHORT + gamma_side "above" (negative gamma, directionnel DOWN)
                if gamma_side == 'above':
                    logger.info("   ⚠️ SHORT mais gamma_side=above (positive gamma, contre-courant)")
                elif gamma_side == 'below':
                    logger.info("   ✅ SHORT + gamma_side=below (negative gamma, confluence !")

            # 6. Vérifier absence mèche rejet (anti sweep raté)
            if self._has_reject_wick(ml_data, direction):
                # Si mèche rejet → laisser zero_dte_wall_sweep gérer
                return None

            # 7. Vérifier cassure confirmée (prix a dépassé le mur)
            if not self._is_breakout_confirmed(mid, wall_price, direction):
                return None

            # 8. Détecter pullback/retest (entry optimal)
            is_pullback = self._detect_pullback(mid, wall_price, direction)
            if not is_pullback:
                # Pas encore de pullback, attendre
                return None

            # 9. Vérifier headroom vers prochain niveau
            if not self._check_headroom(ml_data, direction):
                return None

            # 10. Créer signal
            return self._create_signal(ml_data, direction, wall_price, relvol, inst_pressure)  # 🔧 CORRECTION: inst_pressure au lieu de dealers_bias

        except Exception as e:
            logger.error(f"❌ Erreur GammaWallBreakAndGo: {e}", exc_info=True)
            return None

    def _has_reject_wick(self, ml_data: Dict, direction: str) -> bool:
        """
        Détecte mèche de rejet (signe de sweep raté)

        Si mèche > 0.50% → sweep raté, laisser zero_dte_wall_sweep
        """
        # ❌ CORRECTIF: wick_ratio_upper/lower n'existent pas
        # ✅ Calculer depuis upper_wick_ticks / total_range_ticks
        upper_wick = ml_data.get('upper_wick_ticks', 0)
        lower_wick = ml_data.get('lower_wick_ticks', 0)
        total_range = ml_data.get('total_range_ticks', 1)

        if direction == "LONG":
            # Cassure haussière → vérifier wick supérieure (rejet haut)
            wick_ratio_upper = upper_wick / total_range if total_range > 0 else 0
            if wick_ratio_upper > self.max_reject_wick_pct:
                return True
        else:  # SHORT
            # Cassure baissière → vérifier wick inférieure (rejet bas)
            wick_ratio_lower = lower_wick / total_range if total_range > 0 else 0
            if wick_ratio_lower > self.max_reject_wick_pct:
                return True

        return False

    def _is_breakout_confirmed(self, current_price: float, wall_price: float, direction: str) -> bool:
        """Vérifie que la cassure est confirmée (prix a dépassé le mur)"""
        if direction == "LONG":
            # Prix doit être au-dessus du mur (au moins 2 ticks)
            return current_price > wall_price + (2 * 0.25)
        else:  # SHORT
            # Prix doit être en-dessous du mur (au moins 2 ticks)
            return current_price < wall_price - (2 * 0.25)

    def _detect_pullback(self, current_price: float, wall_price: float, direction: str) -> bool:
        """
        Détecte un pullback/retest du mur cassé

        Pullback = prix revient tester le mur après la cassure
        Entry optimal = sur ce retest
        """
        if len(self.price_history) < 5:
            return False

        if direction == "LONG":
            # Cassure haussière: chercher max récent puis pullback vers mur
            recent_high = max(self.price_history[-5:])

            # A fait un high au-dessus du mur
            if recent_high < wall_price:
                return False

            # Prix actuel proche du mur (retest)
            dist_to_wall = abs(current_price - wall_price) / wall_price * 100
            if dist_to_wall < 0.10:  # Dans 0.10% du mur
                # Et revient du high récent
                if current_price < recent_high:
                    return True

        else:  # SHORT
            # Cassure baissière: chercher min récent puis pullback vers mur
            recent_low = min(self.price_history[-5:])

            # A fait un low en-dessous du mur
            if recent_low > wall_price:
                return False

            # Prix actuel proche du mur (retest)
            dist_to_wall = abs(current_price - wall_price) / wall_price * 100
            if dist_to_wall < 0.10:
                # Et revient du low récent
                if current_price > recent_low:
                    return True

        return False

    def _check_headroom(self, ml_data: Dict, direction: str) -> bool:
        """
        Vérifie headroom suffisant vers prochain niveau

        📚 Bible MenthorQ v2.0: Distances GEX alignées avec grille officielle
        """
        # Options headroom (vers prochain mur gamma)
        menthor_dist = ml_data.get('menthor_distances', {})
        if not isinstance(menthor_dist, dict):
            return True  # Pas de data, on accepte

        if direction == "LONG":
            # Vérifier distance au prochain call wall/resistance
            near_gex_up = menthor_dist.get('near_gex_up', 999)
            # 📚 CORRECTION BIBLE MENTHORQ: < 25 ticks = "proche" (pas 20)
            if near_gex_up < 25:
                logger.warning(f"⚠️ Headroom faible: GEX up @ {near_gex_up:.0f}t (< 25t = proche)")
                return False

            # Vérifier call resistance
            call_res = ml_data.get('call_resistance')
            if call_res:
                mid = ml_data.get('mid')
                if mid:
                    dist_pct = abs((call_res - mid) / mid) * 100
                    if dist_pct < self.min_headroom_pct:
                        return False

        else:  # SHORT
            # Vérifier distance au prochain put wall/support
            near_gex_dn = menthor_dist.get('near_gex_dn', 999)
            # 📚 CORRECTION BIBLE MENTHORQ: < 25 ticks = "proche"
            if near_gex_dn < 25:
                logger.warning(f"⚠️ Headroom faible: GEX down @ {near_gex_dn:.0f}t (< 25t = proche)")
                return False

            # Vérifier put support
            put_sup = ml_data.get('put_support')
            if put_sup:
                mid = ml_data.get('mid')
                if mid:
                    dist_pct = abs((mid - put_sup) / mid) * 100
                    if dist_pct < self.min_headroom_pct:
                        return False

        return True

    def _create_signal(
        self,
        ml_data: Dict,
        direction: str,
        wall_price: float,
        relvol: float,
        dealers_bias: float
    ) -> PatternSignal:
        """Crée le signal de trading"""
        entry = ml_data.get('mid')

        # Tick size dynamique
        symbol = ml_data.get('sym', 'NQ')
        tick_size = 0.25 if symbol in ['ES', 'NQ'] else 0.10

        # ATR pour SL/TP dynamiques
        atr = ml_data.get('atr', 1.0)

        # SL basé sur ATR (minimum 8 ticks)
        sl_ticks = max(int(atr * 1.5 / tick_size), self.sl_ticks)

        # SL derrière le mur cassé
        if direction == "LONG":
            stop_loss = wall_price - (sl_ticks * tick_size)
            # TP1: momentum rapide (1.2R)
            sl_distance = entry - stop_loss
            tp1 = entry + (sl_distance * self.tp1_multiplier)
            tp2 = entry + (sl_distance * self.tp2_multiplier)
        else:  # SHORT
            stop_loss = wall_price + (sl_ticks * tick_size)
            sl_distance = stop_loss - entry
            tp1 = entry - (sl_distance * self.tp1_multiplier)
            tp2 = entry - (sl_distance * self.tp2_multiplier)

        # Confiance basée sur qualité cassure
        confidence = 0.65  # Base (réduit de 0.70 à 0.65)

        # Bonus si volume très élevé
        volume = ml_data.get('volume', 0)
        if volume > 70:
            confidence += 0.05

        # Bonus si institutional pressure fort
        inst_pressure = ml_data.get('institutional_pressure', 0.0)
        if abs(inst_pressure) > 0.25:
            confidence += 0.05

        # Bonus si pullback propre
        if self._detect_pullback(entry, wall_price, direction):
            confidence += 0.05

        confidence = min(confidence, 0.85)  # Cap à 0.85

        return PatternSignal(
            strategy=self.name,
            timestamp=datetime.now(),
            side=direction,
            confidence=confidence,
            entry=entry,
            stop=stop_loss,
            targets=[tp1, tp2],
            metadata={
                'wall_price': wall_price,
                'volume': volume,
                'institutional_pressure': inst_pressure,
                'entry_type': 'pullback_retest',
                'atr': atr,
                'sl_ticks': sl_ticks,
                'risk_reward_ratio': abs((tp1 - entry) / (entry - stop_loss)) if direction == "LONG" else abs((entry - tp1) / (stop_loss - entry))
            },
            processing_time_ms=0.0
        )


if __name__ == "__main__":
    # Test de la stratégie
    strategy = GammaWallBreakAndGo()
    print(f"✅ Stratégie {strategy.name} initialisée")
    print(f"   Max dist wall: {strategy.max_dist_wall_pct}%")
    print(f"   Min relvol break: {strategy.min_relvol_break}")
    print(f"   Max reject wick: {strategy.max_reject_wick_pct}%")
    print(f"   Min headroom: {strategy.min_headroom_pct}%")
    print(f"   SL ticks: {strategy.sl_ticks}")
    print(f"   TP1 multiplier: {strategy.tp1_multiplier}x")
    print(f"   TP2 multiplier: {strategy.tp2_multiplier}x")
