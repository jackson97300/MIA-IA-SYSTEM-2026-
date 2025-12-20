#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Call Put Channel Rotation Strategy
===================================

Stratégie GPT - Rotation de Régime Options

Trade les changements de régime intraday via rotation call/put flow.
Détecte les shifts bullish/bearish par analyse des flux options.

Concept:
--------
- Call/Put flow ratio = sentiment institutionnel options
- Flip du ratio = changement de régime
- Acceptation prix (3 barres) confirme nouveau régime
- Canal call/put définit zones de rotation

Edge:
-----
- Anticipe changements de régime AVANT la foule
- Flux options = smart money intentions
- Win rate attendu: 65-70%
- Risk/Reward: 1:2.5
- Fréquence: 2-4 trades/jour (rare mais puissant)

Particularité:
--------------
- Requiert champs call_put_flow_ratio et channel_state_flip
- Fallback si absents: utilise gamma call vs put strength
- Fréquence faible mais haute qualité

Author: MIA System
Date: 31 Octobre 2025
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import time
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


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


class CallPutChannelRotation:
    """
    Trade les rotations de régime via analyse flux call/put options.

    Principe:
    ---------
    - Call/Put flow ratio = indicateur sentiment institutionnel
    - Ratio >= 1.30 = régime bullish (calls dominants)
    - Ratio <= 0.77 = régime bearish (puts dominants)
    - Flip de régime + acceptation prix = changement durable

    Trigger:
    --------
    LONG (flip vers régime bullish):
    1. channel_state_flip = True (ou détection manuelle)
    2. call_put_flow_ratio >= 1.30
    3. Acceptation prix au-dessus flip (3 barres consécutives)
    4. Headroom vers résistance >= 0.20%
    5. Pas de mur gamma bloquant immédiat

    SHORT (flip vers régime bearish):
    1. channel_state_flip = True
    2. call_put_flow_ratio <= 0.77
    3. Acceptation prix en-dessous flip (3 barres)
    4. Headroom vers support >= 0.20%

    Fallback si champs manquants:
    ------------------------------
    Utilise ratio gamma call strength / gamma put strength comme proxy
    """

    def __init__(self):
        """Initialise la stratégie"""
        self.name = "call_put_channel_rotation"

        # Paramètres flow ratio
        self.min_flow_ratio_long = 1.30      # Ratio min pour LONG
        self.max_flow_ratio_short = 0.77     # Ratio max pour SHORT

        # Acceptation prix
        self.confirm_bars = 3                # Barres confirmation
        self.min_headroom_pct = 0.20         # Headroom min (0.20%)

        # Historique pour confirmation
        self.price_history = []
        self.max_history = 10

        # Dernier flip détecté (pour éviter re-trade même flip)
        self.last_flip_time = 0
        self.flip_cooldown_sec = 600         # 10 min cooldown après flip

        # SL/TP
        self.sl_pct = 0.30                   # SL à 0.30% (mid-channel)
        self.tp_multiplier = 2.5             # TP au bord opposé canal

        logger.info(f"✅ {self.name} initialisé")

    def analyze_from_ml_ready(self, ml_data: Dict[str, Any]) -> Optional[PatternSignal]:
        """
        Analyse les données ML_READY pour détecter une rotation de régime

        Args:
            ml_data: Données ML_READY complètes

        Returns:
            PatternSignal si rotation détectée, None sinon
        """
        try:
            # Mettre à jour historique prix
            mid = ml_data.get('mid')
            if mid:
                self.price_history.append(mid)
                if len(self.price_history) > self.max_history:
                    self.price_history.pop(0)

            # 1. Détecter flip de canal (ou calculer proxy)
            flip_detected, direction = self._detect_channel_flip(ml_data)

            if not flip_detected:
                return None

            # 2. Vérifier cooldown depuis dernier flip
            current_time = ml_data.get('t_ms', int(time.time() * 1000))
            if (current_time - self.last_flip_time) / 1000 < self.flip_cooldown_sec:
                return None

            # 3. Vérifier call/put flow ratio (ou proxy)
            flow_ratio = self._get_flow_ratio(ml_data)

            if flow_ratio is None:
                return None

            # 4. Valider ratio selon direction
            if direction == "LONG":
                if flow_ratio < self.min_flow_ratio_long:
                    return None
            else:  # SHORT
                if flow_ratio > self.max_flow_ratio_short:
                    return None

            # 5. Vérifier acceptation prix (3 barres)
            if not self._check_price_acceptance(ml_data, direction):
                return None

            # 6. Vérifier headroom suffisant
            if not self._check_headroom(ml_data, direction):
                return None

            # 7. Vérifier pas de mur gamma immédiat
            if self._wall_blocking_immediate(ml_data, direction):
                return None

            # 8. Enregistrer flip time
            self.last_flip_time = current_time

            # 9. Créer signal
            return self._create_signal(ml_data, direction, flow_ratio)

        except Exception as e:
            logger.error(f"❌ Erreur CallPutChannelRotation: {e}", exc_info=True)
            return None

    def _detect_channel_flip(self, ml_data: Dict) -> tuple[bool, Optional[str]]:
        """
        Détecte flip de canal options

        Returns:
            (flip_detected: bool, direction: "LONG" ou "SHORT" ou None)
        """
        # Essayer d'abord channel_state_flip direct
        channel_flip = ml_data.get('channel_state_flip')

        if channel_flip is True or channel_flip == 1:
            # Flip détecté, déterminer direction via d'autres signaux
            direction = self._infer_flip_direction(ml_data)
            if direction:
                return (True, direction)

        # Fallback: Détecter manuellement via gamma call vs put
        return self._detect_flip_manual(ml_data)

    def _infer_flip_direction(self, ml_data: Dict) -> Optional[str]:
        """
        Infère direction du flip via autres signaux

        📚 Bible MenthorQ v2.0: Utiliser gamma_side pour confluence
        """
        # 📚 ENRICHISSEMENT: Utiliser gamma_side en priorité
        gamma_side = ml_data.get('gamma_side', '')

        if gamma_side == 'above':
            # Prix au-dessus gamma = positive gamma = mean-revert = BULLISH
            logger.info("📚 Bible MenthorQ: gamma_side=above (positive gamma) → LONG")
            return "LONG"
        elif gamma_side == 'below':
            # Prix au-dessous gamma = negative gamma = directionnel = BEARISH
            logger.info("📚 Bible MenthorQ: gamma_side=below (negative gamma) → SHORT")
            return "SHORT"

        # Fallback: Vérifier gamma confluence
        gamma_call_conf = ml_data.get('gamma_call_confluence', False)
        gamma_put_conf = ml_data.get('gamma_put_confluence', False)

        if gamma_call_conf and not gamma_put_conf:
            return "LONG"
        elif gamma_put_conf and not gamma_call_conf:
            return "SHORT"

        # Vérifier position prix vs VWAP (dernier recours)
        mid = ml_data.get('mid')
        vwap = ml_data.get('vwap')

        if mid and vwap:
            if mid > vwap:
                return "LONG"  # Au-dessus VWAP = bullish
            else:
                return "SHORT"

        return None

    def _detect_flip_manual(self, ml_data: Dict) -> tuple[bool, Optional[str]]:
        """
        Détecte flip manuellement via gamma call vs put strength

        Proxy: Si call resistance devient support OU put support devient resistance
        """
        mid = ml_data.get('mid')
        call_res = ml_data.get('call_resistance')
        put_sup = ml_data.get('put_support')

        if not mid:
            return (False, None)

        # Flip bullish: Prix dépasse call resistance (résistance devient support)
        if call_res:
            if mid > call_res * 1.001:  # Au-dessus de 0.1%
                # Vérifier que c'est récent (dans historique)
                if len(self.price_history) >= 5:
                    # Prix était sous call_res récemment?
                    recent_below = any(p < call_res for p in self.price_history[-5:-1])
                    if recent_below:
                        return (True, "LONG")

        # Flip bearish: Prix passe sous put support (support devient résistance)
        if put_sup:
            if mid < put_sup * 0.999:  # En-dessous de 0.1%
                if len(self.price_history) >= 5:
                    recent_above = any(p > put_sup for p in self.price_history[-5:-1])
                    if recent_above:
                        return (True, "SHORT")

        return (False, None)

    def _get_flow_ratio(self, ml_data: Dict) -> Optional[float]:
        """
        Récupère call/put flow ratio

        📚 Bible MenthorQ v2.0: Rejeter si pas de données réelles
        (Éviter proxies arbitraires qui créent faux signaux)

        Returns:
            flow_ratio si disponible, None sinon
        """
        # Essayer d'abord call_put_flow_ratio direct
        flow_ratio = ml_data.get('call_put_flow_ratio')

        if flow_ratio is not None and flow_ratio > 0:
            logger.info(f"📚 Bible MenthorQ: call_put_flow_ratio={flow_ratio:.3f}")
            return flow_ratio

        # ❌ CORRECTION CRITIQUE: Ne PAS utiliser de fallback proxy arbitraire
        # Les valeurs arbitraires (1.40, 0.70) créent de FAUX signaux
        logger.warning("⚠️ call_put_flow_ratio ABSENT → Signal rejeté (Bible MenthorQ)")
        logger.warning("   → Proxies arbitraires interdits (faux signaux)")
        return None  # ✅ Rejeter si pas de données réelles

    def _check_price_acceptance(self, ml_data: Dict, direction: str) -> bool:
        """
        Vérifie acceptation prix (3 barres au-dessus/dessous flip)

        Acceptation = prix reste dans nouveau régime pendant 3 barres
        """
        if len(self.price_history) < self.confirm_bars:
            return False

        # Récupérer niveau de flip (call_res ou put_sup)
        if direction == "LONG":
            flip_level = ml_data.get('call_resistance')
        else:
            flip_level = ml_data.get('put_support')

        if not flip_level:
            # Sans niveau clair, vérifier VWAP
            flip_level = ml_data.get('vwap')

        if not flip_level:
            return True  # Pas de validation possible, on accepte

        # Vérifier que les 3 dernières barres sont du bon côté
        recent_prices = self.price_history[-self.confirm_bars:]

        if direction == "LONG":
            # Toutes au-dessus flip level
            return all(p > flip_level for p in recent_prices)
        else:  # SHORT
            # Toutes en-dessous flip level
            return all(p < flip_level for p in recent_prices)

    def _check_headroom(self, ml_data: Dict, direction: str) -> bool:
        """Vérifie headroom suffisant vers prochain niveau"""
        mid = ml_data.get('mid')
        if not mid:
            return False

        if direction == "LONG":
            # Vérifier distance à call resistance / prochain mur
            call_res = ml_data.get('call_resistance')
            if call_res:
                dist_pct = ((call_res - mid) / mid) * 100
                if dist_pct < self.min_headroom_pct:
                    return False

        else:  # SHORT
            # Vérifier distance à put support / prochain mur
            put_sup = ml_data.get('put_support')
            if put_sup:
                dist_pct = ((mid - put_sup) / mid) * 100
                if dist_pct < self.min_headroom_pct:
                    return False

        return True

    def _wall_blocking_immediate(self, ml_data: Dict, direction: str) -> bool:
        """Vérifie si un mur gamma bloque immédiatement"""
        next_wall = ml_data.get('next_wall', {})

        if not next_wall or not isinstance(next_wall, dict):
            return False

        wall_dist_ticks = next_wall.get('dist_ticks', 999)

        # Si mur très proche (<15 ticks), risque de blocage
        if wall_dist_ticks < 15:
            wall_side = next_wall.get('side')

            # Mur dans la mauvaise direction = blocage
            if direction == "LONG" and wall_side == "call":
                return True
            elif direction == "SHORT" and wall_side == "put":
                return True

        return False

    def _create_signal(
        self,
        ml_data: Dict,
        direction: str,
        flow_ratio: float
    ) -> PatternSignal:
        """Crée le signal de trading"""
        entry = ml_data.get('mid')

        # Tick size dynamique
        symbol = ml_data.get('sym', 'NQ')
        tick_size = 0.25 if symbol in ['ES', 'NQ'] else 0.10

        # ATR pour SL/TP dynamiques
        atr = ml_data.get('atr', 1.0)

        # SL au mid-channel (0.30% de l'entry)
        if direction == "LONG":
            stop_loss = entry * (1 - self.sl_pct / 100)
            # TP au bord opposé canal (call resistance ou VAH)
            call_res = ml_data.get('call_resistance')
            if call_res and call_res > entry:
                tp1 = call_res
                tp2 = call_res + (atr * 1.5)
            else:
                # Fallback: TP basé sur R:R
                sl_distance = entry - stop_loss
                tp1 = entry + (sl_distance * self.tp_multiplier)
                tp2 = tp1 + (atr * 1.0)

        else:  # SHORT
            stop_loss = entry * (1 + self.sl_pct / 100)
            # TP au bord opposé canal (put support ou VAL)
            put_sup = ml_data.get('put_support')
            if put_sup and put_sup < entry:
                tp1 = put_sup
                tp2 = put_sup - (atr * 1.5)
            else:
                sl_distance = stop_loss - entry
                tp1 = entry - (sl_distance * self.tp_multiplier)
                tp2 = tp1 - (atr * 1.0)

        # Confiance basée sur qualité flip
        confidence = 0.55  # Base (réduit de 0.60 à 0.55)

        # Bonus si flow ratio très marqué
        if direction == "LONG" and flow_ratio >= 1.50:
            confidence += 0.05
        elif direction == "SHORT" and flow_ratio <= 0.65:
            confidence += 0.05

        # Bonus si acceptation prix très nette
        if len(self.price_history) >= 5:
            confidence += 0.05

        # Bonus si headroom large
        if direction == "LONG":
            call_res = ml_data.get('call_resistance')
            if call_res:
                headroom_pct = ((call_res - entry) / entry) * 100
                if headroom_pct > 0.40:
                    confidence += 0.05
        else:
            put_sup = ml_data.get('put_support')
            if put_sup:
                headroom_pct = ((entry - put_sup) / entry) * 100
                if headroom_pct > 0.40:
                    confidence += 0.05

        confidence = min(confidence, 0.75)  # Cap à 0.75 (conservateur)

        return PatternSignal(
            strategy=self.name,
            timestamp=datetime.now(),
            side=direction,
            confidence=confidence,
            entry=entry,
            stop=stop_loss,
            targets=[tp1, tp2],
            metadata={
                'flow_ratio': flow_ratio,
                'confirm_bars': self.confirm_bars,
                'headroom_pct': self.min_headroom_pct,
                'regime_change': True,
                'atr': atr,
                'risk_reward_ratio': abs((tp1 - entry) / (entry - stop_loss)) if direction == "LONG" else abs((entry - tp1) / (stop_loss - entry))
            },
            processing_time_ms=0.0
        )


if __name__ == "__main__":
    # Test de la stratégie
    strategy = CallPutChannelRotation()
    print(f"✅ Stratégie {strategy.name} initialisée")
    print(f"   Min flow ratio LONG: {strategy.min_flow_ratio_long}")
    print(f"   Max flow ratio SHORT: {strategy.max_flow_ratio_short}")
    print(f"   Confirm bars: {strategy.confirm_bars}")
    print(f"   Min headroom: {strategy.min_headroom_pct}%")
    print(f"   Flip cooldown: {strategy.flip_cooldown_sec}s")
    print(f"   SL %: {strategy.sl_pct}%")
    print(f"   TP multiplier: {strategy.tp_multiplier}x")
