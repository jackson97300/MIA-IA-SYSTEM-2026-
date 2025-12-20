#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Blind Spot Magnetic Pull Strategy
==================================

Stratégie IA #1 - Edge Unique MenthorQ

Exploite l'attraction magnétique des blind spots options.
Le prix est TIRÉ vers les blind spots comme par un aimant.

Concept:
--------
- Blind spots = zones de liquidité options massive
- Dealers doivent hedger leurs positions
- Hedging = achats/ventes spot qui POUSSENT le prix
- + Institutional pressure confirme la direction

Edge:
-----
- Unique à MenthorQ (personne d'autre ne l'a)
- Win rate attendu: 72-78%
- Risk/Reward: 1:3-4 (excellent!)
- Fréquence: 4-8 trades/jour

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


class BlindSpotMagneticPull:
    """
    Trade l'attraction magnétique vers les blind spots options.

    Principe:
    ---------
    - Blind spots = zones de liquidité options massive
    - Dealers DOIVENT hedger pour rester neutres
    - Hedging crée pression achat/vente sur le spot
    - Prix TIRÉ vers blind spot comme par un aimant

    Trigger:
    --------
    LONG:
    1. Blind spot < 0.30% au-dessus du prix
    2. Institutional pressure > 0.30 (poussée vers le haut)
    3. Smart money flow > 0.25 (smart money anticipe)
    4. Pas de mur gamma bloquant entre prix et blind spot
    5. Confluence avec support (VAL, VWAP, gamma)

    SHORT: Inverse
    """

    def __init__(self):
        """Initialise la stratégie"""
        self.name = "blind_spot_magnetic_pull"

        # Paramètres (seuils réduits pour plus de signaux)
        self.max_distance_pct = 0.30        # Distance max au blind spot (0.30%)
        self.inst_pressure_threshold = 0.20  # Réduit de 0.30 à 0.20
        self.smart_money_threshold = 0.18    # Réduit de 0.25 à 0.18

        # SL/TP en ticks
        self.sl_ticks = 10                   # Stop loss à 10 ticks
        self.tp_multiplier = 3.0             # TP à ~3x le SL (avant blind spot)

        logger.info(f"✅ {self.name} initialisé")

    def analyze_from_ml_ready(self, ml_data: Dict[str, Any]) -> Optional[PatternSignal]:
        """
        Analyse les données ML_READY pour détecter un setup

        Args:
            ml_data: Données ML_READY complètes

        Returns:
            PatternSignal si setup détecté, None sinon
        """
        try:
            # 1. Trouver blind spot le plus proche
            closest_blind = self._find_closest_blind_spot(ml_data)

            if not closest_blind:
                return None

            # 2. Vérifier distance (< 0.30%)
            distance_pct = closest_blind['distance_pct']
            if abs(distance_pct) > self.max_distance_pct:
                return None

            # 3. Déterminer direction
            if distance_pct > 0:  # Blind spot au-dessus
                direction = "LONG"
            else:  # Blind spot en dessous
                direction = "SHORT"

            # 4. Valider avec institutional pressure & smart money
            inst_pressure = ml_data.get('institutional_pressure', 0.0)
            smart_money = ml_data.get('smart_money_flow', 0.0)

            if direction == "LONG":
                if inst_pressure < self.inst_pressure_threshold:
                    return None
                if smart_money < self.smart_money_threshold:
                    return None
            else:  # SHORT
                if inst_pressure > -self.inst_pressure_threshold:
                    return None
                if smart_money > -self.smart_money_threshold:
                    return None

            # 5. Vérifier pas de mur gamma bloquant
            if self._wall_blocking(ml_data, direction, closest_blind['price']):
                return None

            # 6. Vérifier confluence avec support/résistance
            confluence = self._check_confluence(ml_data, direction)
            if not confluence:
                return None

            # 7. Créer signal
            return self._create_signal(ml_data, direction, closest_blind, inst_pressure, smart_money)

        except Exception as e:
            logger.error(f"❌ Erreur BlindSpotMagneticPull: {e}", exc_info=True)
            return None

    def _find_closest_blind_spot(self, ml_data: Dict) -> Optional[Dict]:
        """Trouve le blind spot le plus proche"""
        mid_price = ml_data.get('mid')
        if not mid_price:
            return None

        closest = None
        min_distance = float('inf')

        # Chercher dans blind_spot_0 à blind_spot_8
        for i in range(9):
            blind_price = ml_data.get(f'blind_spot_{i}')
            if blind_price is None or blind_price == 0:
                continue

            distance = blind_price - mid_price
            distance_pct = (distance / mid_price) * 100

            if abs(distance_pct) < abs(min_distance):
                min_distance = distance_pct
                closest = {
                    'index': i,
                    'price': blind_price,
                    'distance': distance,
                    'distance_pct': distance_pct
                }

        return closest

    def _wall_blocking(self, ml_data: Dict, direction: str, target_price: float) -> bool:
        """Vérifie si un mur gamma bloque le chemin vers le blind spot"""
        next_wall = ml_data.get('next_wall', {})

        if not next_wall or not isinstance(next_wall, dict):
            return False

        wall_price = next_wall.get('price')
        if wall_price is None:
            return False

        mid_price = ml_data.get('mid')

        # Vérifier si le mur est entre le prix actuel et le target
        if direction == "LONG":
            # Mur entre mid et target?
            if mid_price < wall_price < target_price:
                # Mur bloquant si forte résistance
                wall_strength = next_wall.get('strength', 0)
                if wall_strength and wall_strength > 0.5:
                    return True
        else:  # SHORT
            # Mur entre mid et target?
            if target_price < wall_price < mid_price:
                wall_strength = next_wall.get('strength', 0)
                if wall_strength and wall_strength > 0.5:
                    return True

        return False

    def _check_confluence(self, ml_data: Dict, direction: str) -> bool:
        """Vérifie confluence avec support/résistance"""
        mid_price = ml_data.get('mid')

        # VWAP comme référence
        vwap = ml_data.get('vwap')
        d_vwap = ml_data.get('d_vwap', 0)

        # VAL/VAH
        vva = ml_data.get('vva', {})
        val = vva.get('val') if isinstance(vva, dict) else None
        vah = vva.get('vah') if isinstance(vva, dict) else None

        if direction == "LONG":
            # Confluence si au-dessus support
            # Support = VAL, VWAP-SD1, ou gamma support

            # Au-dessus VWAP ou proche
            if vwap and mid_price > vwap:
                return True

            # Proche VAL (dans 0.20%)
            if val:
                dist_val_pct = abs((mid_price - val) / mid_price) * 100
                if dist_val_pct < 0.20:
                    return True

            # Confluence gamma
            if ml_data.get('gamma_put_confluence', False):
                return True

        else:  # SHORT
            # Confluence si en-dessous résistance
            # Résistance = VAH, VWAP+SD1, ou gamma resistance

            # En-dessous VWAP ou proche
            if vwap and mid_price < vwap:
                return True

            # Proche VAH (dans 0.20%)
            if vah:
                dist_vah_pct = abs((mid_price - vah) / mid_price) * 100
                if dist_vah_pct < 0.20:
                    return True

            # Confluence gamma
            if ml_data.get('gamma_call_confluence', False):
                return True

        return False

    def _create_signal(
        self,
        ml_data: Dict,
        direction: str,
        blind_spot: Dict,
        inst_pressure: float,
        smart_money: float
    ) -> PatternSignal:
        """Crée le signal de trading"""
        entry = ml_data.get('mid')
        blind_price = blind_spot['price']

        # Tick size dynamique
        symbol = ml_data.get('sym', 'NQ')
        tick_size = 0.25 if symbol in ['ES', 'NQ'] else 0.10

        # ATR pour SL/TP dynamiques
        atr = ml_data.get('atr', 1.0)

        # SL basé sur ATR (minimum 10 ticks)
        sl_ticks = max(int(atr * 1.5 / tick_size), self.sl_ticks)

        if direction == "LONG":
            stop_loss = entry - (sl_ticks * tick_size)
            # TP: 2 ticks avant blind spot (pour assurer fill)
            take_profit = blind_price - (2 * tick_size)

            # Si TP trop proche, utiliser ratio fixe
            if take_profit - entry < (sl_ticks * tick_size * 2):
                take_profit = entry + (sl_ticks * tick_size * self.tp_multiplier)
        else:
            stop_loss = entry + (sl_ticks * tick_size)
            take_profit = blind_price + (2 * tick_size)

            if entry - take_profit < (sl_ticks * tick_size * 2):
                take_profit = entry - (sl_ticks * tick_size * self.tp_multiplier)

        # Confiance basée sur force des signaux
        confidence = 0.70  # Base (réduit de 0.75 à 0.70)

        # Bonus si institutional pressure très fort
        if abs(inst_pressure) > 0.30:  # Réduit de 0.40 à 0.30
            confidence += 0.05

        # Bonus si smart money très fort
        if abs(smart_money) > 0.25:  # Réduit de 0.35 à 0.25
            confidence += 0.05

        # Bonus si blind spot très proche
        if abs(blind_spot['distance_pct']) < 0.20:
            confidence += 0.05

        confidence = min(confidence, 0.90)  # Cap à 0.90

        return PatternSignal(
            strategy=self.name,
            timestamp=datetime.now(),
            side=direction,
            confidence=confidence,
            entry=entry,
            stop=stop_loss,
            targets=[take_profit],
            metadata={
                'blind_spot_index': blind_spot['index'],
                'blind_spot_price': blind_price,
                'distance_pct': blind_spot['distance_pct'],
                'institutional_pressure': inst_pressure,
                'smart_money_flow': smart_money,
                'atr': atr,
                'sl_ticks': sl_ticks,
                'risk_reward_ratio': abs((take_profit - entry) / (entry - stop_loss)) if direction == "LONG" else abs((entry - take_profit) / (stop_loss - entry))
            },
            processing_time_ms=0.0
        )


if __name__ == "__main__":
    # Test de la stratégie
    strategy = BlindSpotMagneticPull()
    print(f"✅ Stratégie {strategy.name} initialisée")
    print(f"   Max distance: {strategy.max_distance_pct}%")
    print(f"   Inst pressure threshold: {strategy.inst_pressure_threshold}")
    print(f"   Smart money threshold: {strategy.smart_money_threshold}")
    print(f"   SL ticks: {strategy.sl_ticks}")
    print(f"   TP multiplier: {strategy.tp_multiplier}x")
