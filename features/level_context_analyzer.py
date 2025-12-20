"""
LEVEL CONTEXT ANALYZER
======================
Analyse le contexte des niveaux MenthorQ:
- Nombre de touches
- Type de réaction (rejet/rebond)
- Direction d'approche
- Support vs Résistance dynamique

Créé: 09 Décembre 2025
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from collections import deque
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class LevelTouch:
    """Représente une touche sur un niveau"""
    timestamp: datetime
    price_at_touch: float
    level_price: float
    approach_direction: str  # "FROM_ABOVE" ou "FROM_BELOW"
    reaction: str  # "REJECTED", "BOUNCED", "BROKE_THROUGH", "FAKEOUT", "PENDING"
    price_after_10bars: float = 0.0  # Prix 10 barres après (pour valider réaction)
    broke_through: bool = False  # A-t-il cassé le niveau?
    came_back: bool = False  # Est-il revenu après cassure? (= FAKEOUT)


@dataclass
class LevelContext:
    """Contexte complet d'un niveau"""
    level_price: float
    level_type: str  # "GEX", "HVL", "PUT_SUPPORT", "CALL_RESIST", etc.

    # Statistiques
    total_touches: int = 0
    touches_from_above: int = 0
    touches_from_below: int = 0
    rejections: int = 0
    bounces: int = 0
    breakthroughs: int = 0
    fakeouts: int = 0  # 🔥 NOUVEAU: Cassure + Rejet = FAKEOUT

    # Dernières touches
    last_touch_time: Optional[datetime] = None
    last_reaction: str = "NONE"

    # 🔥 NOUVEAU: Tracking de la position actuelle par rapport au niveau
    currently_above: bool = True
    last_cross_time: Optional[datetime] = None
    last_cross_direction: str = "NONE"  # "UP" (cassure haussière) ou "DOWN" (cassure baissière)

    # Classification dynamique
    acting_as: str = "UNKNOWN"  # "SUPPORT", "RESISTANCE", "MAGNET", "WEAK"
    strength_score: float = 0.0  # 0.0 à 1.0

    # Historique des touches
    touch_history: List[LevelTouch] = field(default_factory=list)


class LevelContextAnalyzer:
    """
    Analyse le contexte des niveaux pour déterminer s'ils agissent
    comme Support ou Résistance.
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}

        # Paramètres
        self.touch_threshold_ticks = self.config.get('touch_threshold_ticks', 5)  # Distance pour considérer une touche
        self.min_touches_for_classification = self.config.get('min_touches', 2)
        self.reaction_bars = self.config.get('reaction_bars', 10)  # Barres pour évaluer réaction
        self.level_expiry_hours = self.config.get('level_expiry_hours', 24)

        # Stockage des niveaux par symbole
        self.levels: Dict[str, Dict[float, LevelContext]] = {}  # {symbol: {price: LevelContext}}

        # Historique des prix pour analyse
        self.price_history: Dict[str, deque] = {}  # {symbol: deque of (timestamp, price)}
        self.max_history = 500  # Garder 500 dernières barres

        logger.info("🔍 LevelContextAnalyzer initialisé")
        logger.info(f"   Touch threshold: {self.touch_threshold_ticks} ticks")
        logger.info(f"   Min touches pour classification: {self.min_touches_for_classification}")

    def update_price(self, symbol: str, price: float, timestamp: datetime = None):
        """Met à jour l'historique des prix"""
        if timestamp is None:
            timestamp = datetime.now()

        if symbol not in self.price_history:
            self.price_history[symbol] = deque(maxlen=self.max_history)

        self.price_history[symbol].append((timestamp, price))

    def register_level(self, symbol: str, level_price: float, level_type: str):
        """Enregistre un nouveau niveau à tracker"""
        if symbol not in self.levels:
            self.levels[symbol] = {}

        # Arrondir le prix pour éviter les doublons
        rounded_price = round(level_price, 2)

        if rounded_price not in self.levels[symbol]:
            self.levels[symbol][rounded_price] = LevelContext(
                level_price=rounded_price,
                level_type=level_type
            )
            logger.debug(f"[{symbol}] Niveau enregistré: {level_type} @ {rounded_price}")

    def analyze_touch(self, symbol: str, current_price: float,
                      tick_size: float = 0.25) -> List[Tuple[LevelContext, str]]:
        """
        Analyse si le prix actuel touche un niveau et retourne le contexte.

        🔥 NOUVEAU: Détecte aussi les FAKEOUTS (cassure + rejet)

        Returns:
            Liste de tuples (LevelContext, recommendation) où recommendation est:
            - "LONG" si le niveau agit comme SUPPORT
            - "SHORT" si le niveau agit comme RÉSISTANCE
            - "AVOID" si le niveau est faible ou incertain
        """
        if symbol not in self.levels:
            return []

        results = []
        touch_distance = self.touch_threshold_ticks * tick_size

        for level_price, context in self.levels[symbol].items():
            distance = abs(current_price - level_price)

            # 🔥 NOUVEAU: Détecter les FAKEOUTS (cassure puis retour)
            self._detect_fakeout(context, current_price, level_price, tick_size)

            # Vérifier si on touche ce niveau
            if distance <= touch_distance:
                # Déterminer la direction d'approche
                approach = self._get_approach_direction(symbol, level_price, current_price)

                # Enregistrer la touche
                self._record_touch(context, current_price, approach)

                # Classifier le niveau
                self._classify_level(context)

                # Générer recommandation
                recommendation = self._get_recommendation(context, approach)

                results.append((context, recommendation))

                logger.info(f"🎯 [{symbol}] TOUCHE NIVEAU: {context.level_type} @ {level_price:.2f}")
                logger.info(f"   Approche: {approach}")
                logger.info(f"   Total touches: {context.total_touches}")
                logger.info(f"   Rejets: {context.rejections} | Rebonds: {context.bounces}")
                logger.info(f"   Agit comme: {context.acting_as} (force: {context.strength_score:.0%})")
                logger.info(f"   → Recommandation: {recommendation}")

        return results

    def _get_approach_direction(self, symbol: str, level_price: float,
                                current_price: float) -> str:
        """Détermine si le prix approche d'en haut ou d'en bas"""
        if symbol not in self.price_history or len(self.price_history[symbol]) < 5:
            # Pas assez d'historique, utiliser position relative
            return "FROM_BELOW" if current_price < level_price else "FROM_ABOVE"

        # Regarder les 10 dernières barres
        recent_prices = [p for _, p in list(self.price_history[symbol])[-10:]]
        avg_recent = sum(recent_prices) / len(recent_prices)

        # Si le prix moyen récent est sous le niveau, on approche d'en bas
        if avg_recent < level_price - 2:  # 2 points de marge
            return "FROM_BELOW"
        elif avg_recent > level_price + 2:
            return "FROM_ABOVE"
        else:
            # Prix oscille autour du niveau
            return "OSCILLATING"

    def _detect_fakeout(self, context: LevelContext, current_price: float,
                        level_price: float, tick_size: float):
        """
        🔥 NOUVEAU 09/12: Détecte les FAKEOUTS (cassure + rejet)

        Pattern FAKEOUT:
        1. Prix CASSE le niveau (traverse de l'autre côté)
        2. Prix REVIENT du côté original dans les 5-10 minutes
        = Le niveau est ENCORE PLUS FORT car il a "piégé" les breakout traders
        """
        now = datetime.now()
        is_above = current_price > level_price
        margin = 3 * tick_size  # 3 ticks de marge pour confirmer cassure

        # Vérifier si le prix a traversé le niveau
        if context.last_cross_time is None:
            # Première observation, initialiser et continuer
            context.currently_above = is_above
            context.last_cross_time = now  # Initialiser le temps
            # Ne pas retourner - continuer pour détecter les cassures

        # 🔥 ÉTAPE 1: Détecter un FAKEOUT AVANT de mettre à jour la direction
        # Un fakeout = le prix était de l'autre côté du niveau et revient
        if context.last_cross_time:
            time_since_cross = (now - context.last_cross_time).total_seconds()

            # Fakeout = retour dans les 10 minutes après cassure
            if time_since_cross < 600:  # 10 minutes

                # Fakeout DOWN: était sous le niveau (DOWN), revenu au-dessus
                if context.last_cross_direction == "DOWN" and is_above and current_price > (level_price + margin):
                    context.fakeouts += 1
                    context.last_cross_direction = "FAKEOUT_DOWN"  # Reset pour éviter double comptage
                    logger.info(f"FAKEOUT DOWN detecte sur {context.level_type} @ {level_price:.2f}!")
                    logger.info(f"   -> Cassure vers le bas puis retour au-dessus = SUPPORT FORT!")
                    logger.info(f"   -> Total fakeouts: {context.fakeouts}")

                # Fakeout UP: était au-dessus (UP), revenu en-dessous
                elif context.last_cross_direction == "UP" and not is_above and current_price < (level_price - margin):
                    context.fakeouts += 1
                    context.last_cross_direction = "FAKEOUT_UP"  # Reset pour éviter double comptage
                    logger.info(f"FAKEOUT UP detecte sur {context.level_type} @ {level_price:.2f}!")
                    logger.info(f"   -> Cassure vers le haut puis retour en-dessous = RESISTANCE FORTE!")
                    logger.info(f"   -> Total fakeouts: {context.fakeouts}")

        # 🔥 ÉTAPE 2: Détecter une nouvelle CASSURE (prix traverse le niveau avec marge)
        # Seulement si ce n'est pas un fakeout qu'on vient de détecter
        if context.last_cross_direction not in ["FAKEOUT_DOWN", "FAKEOUT_UP"]:
            if context.currently_above and current_price < (level_price - margin):
                # Cassure vers le BAS (breakdown)
                if context.last_cross_direction != "DOWN":
                    context.last_cross_direction = "DOWN"
                    context.last_cross_time = now
                    logger.debug(f"CASSURE DOWN detectee: prix {current_price:.2f} sous niveau {level_price:.2f}")

            elif not context.currently_above and current_price > (level_price + margin):
                # Cassure vers le HAUT (breakout)
                if context.last_cross_direction != "UP":
                    context.last_cross_direction = "UP"
                    context.last_cross_time = now
                    logger.debug(f"CASSURE UP detectee: prix {current_price:.2f} au-dessus niveau {level_price:.2f}")

        # 🔥 ÉTAPE 3: Mettre à jour la position actuelle
        context.currently_above = is_above

    def _record_touch(self, context: LevelContext, price: float, approach: str):
        """Enregistre une touche sur le niveau"""
        now = datetime.now()

        # Éviter les doublons (même touche en quelques secondes)
        if context.last_touch_time:
            time_since_last = (now - context.last_touch_time).total_seconds()
            if time_since_last < 60:  # Minimum 1 minute entre les touches
                return

        touch = LevelTouch(
            timestamp=now,
            price_at_touch=price,
            level_price=context.level_price,
            approach_direction=approach,
            reaction="PENDING"
        )

        context.touch_history.append(touch)
        context.total_touches += 1
        context.last_touch_time = now

        if approach == "FROM_ABOVE":
            context.touches_from_above += 1
        elif approach == "FROM_BELOW":
            context.touches_from_below += 1

        # Évaluer la réaction de la touche précédente (si existe)
        if len(context.touch_history) >= 2:
            prev_touch = context.touch_history[-2]
            self._evaluate_reaction(context, prev_touch, price)

    def _evaluate_reaction(self, context: LevelContext, touch: LevelTouch,
                          current_price: float):
        """Évalue la réaction après une touche"""
        if touch.reaction != "PENDING":
            return

        level = context.level_price
        price_at_touch = touch.price_at_touch

        # Déterminer la réaction basée sur le mouvement
        if touch.approach_direction == "FROM_BELOW":
            # Prix venait d'en bas
            if current_price < price_at_touch - 5:
                # Prix a été REJETÉ (redescend)
                touch.reaction = "REJECTED"
                context.rejections += 1
            elif current_price > level + 5:
                # Prix a CASSÉ le niveau
                touch.reaction = "BROKE_THROUGH"
                context.breakthroughs += 1
            else:
                touch.reaction = "BOUNCED"
                context.bounces += 1

        elif touch.approach_direction == "FROM_ABOVE":
            # Prix venait d'en haut
            if current_price > price_at_touch + 5:
                # Prix a été REJETÉ (remonte)
                touch.reaction = "REJECTED"
                context.rejections += 1
            elif current_price < level - 5:
                # Prix a CASSÉ le niveau
                touch.reaction = "BROKE_THROUGH"
                context.breakthroughs += 1
            else:
                touch.reaction = "BOUNCED"
                context.bounces += 1

        context.last_reaction = touch.reaction
        touch.price_after_10bars = current_price

    def _classify_level(self, context: LevelContext):
        """
        Classifie le niveau comme Support, Résistance, ou autre

        🔥 NOUVEAU 09/12: Les FAKEOUTS comptent DOUBLE!
        Un fakeout = le niveau a piégé les breakout traders = TRÈS FORT
        """

        # 🔥 PRIORITÉ #1: Si fakeout détecté, le niveau est TRÈS FORT
        if context.fakeouts > 0:
            # Déterminer la direction basée sur le dernier fakeout
            if context.last_cross_direction == "FAKEOUT_UP":
                # Cassé vers le haut puis rejeté = RÉSISTANCE FORTE
                context.acting_as = "RESISTANCE"
                context.strength_score = min(1.0, 0.8 + (context.fakeouts * 0.1))
                logger.info(f"🔥 Niveau classé RÉSISTANCE FORTE (fakeout UP x{context.fakeouts})")
                return
            elif context.last_cross_direction == "FAKEOUT_DOWN":
                # Cassé vers le bas puis rejeté = SUPPORT FORT
                context.acting_as = "SUPPORT"
                context.strength_score = min(1.0, 0.8 + (context.fakeouts * 0.1))
                logger.info(f"🔥 Niveau classé SUPPORT FORT (fakeout DOWN x{context.fakeouts})")
                return

        if context.total_touches < self.min_touches_for_classification:
            context.acting_as = "UNKNOWN"
            context.strength_score = 0.0
            return

        # Calculer les ratios
        total_reactions = context.rejections + context.bounces + context.breakthroughs
        if total_reactions == 0:
            context.acting_as = "UNKNOWN"
            context.strength_score = 0.0
            return

        rejection_ratio = context.rejections / total_reactions
        bounce_ratio = context.bounces / total_reactions
        breakthrough_ratio = context.breakthroughs / total_reactions

        # Analyser la direction dominante des approches
        from_above_ratio = context.touches_from_above / context.total_touches if context.total_touches > 0 else 0
        from_below_ratio = context.touches_from_below / context.total_touches if context.total_touches > 0 else 0

        # Classification
        if breakthrough_ratio > 0.5 and context.fakeouts == 0:
            # Le niveau est souvent cassé ET pas de fakeout → FAIBLE
            context.acting_as = "WEAK"
            context.strength_score = 0.2

        elif from_below_ratio > 0.7 and rejection_ratio > 0.5:
            # Prix vient souvent d'en bas et est rejeté → RÉSISTANCE
            context.acting_as = "RESISTANCE"
            # 🔥 Bonus pour fakeouts
            fakeout_bonus = context.fakeouts * 0.15
            context.strength_score = min(1.0, rejection_ratio + (context.rejections * 0.1) + fakeout_bonus)

        elif from_above_ratio > 0.7 and rejection_ratio > 0.5:
            # Prix vient souvent d'en haut et est rejeté → SUPPORT
            context.acting_as = "SUPPORT"
            # 🔥 Bonus pour fakeouts
            fakeout_bonus = context.fakeouts * 0.15
            context.strength_score = min(1.0, rejection_ratio + (context.rejections * 0.1) + fakeout_bonus)

        elif bounce_ratio > 0.6:
            # Le prix rebondit souvent → SUPPORT/RÉSISTANCE selon contexte récent
            if context.touch_history and len(context.touch_history) > 0:
                last_approach = context.touch_history[-1].approach_direction
                if last_approach == "FROM_ABOVE":
                    context.acting_as = "SUPPORT"
                else:
                    context.acting_as = "RESISTANCE"
                context.strength_score = bounce_ratio
            else:
                context.acting_as = "MAGNET"
                context.strength_score = 0.5

        else:
            # Comportement mixte
            context.acting_as = "MAGNET"
            context.strength_score = 0.4

    def _get_recommendation(self, context: LevelContext, current_approach: str) -> str:
        """Génère une recommandation de trading basée sur le contexte"""

        # Niveau faible ou inconnu → ÉVITER
        if context.acting_as in ["WEAK", "UNKNOWN"]:
            return "AVOID"

        # Pas assez de données
        if context.strength_score < 0.3:
            return "AVOID"

        # RÉSISTANCE confirmée
        if context.acting_as == "RESISTANCE":
            if current_approach == "FROM_BELOW":
                # Prix approche d'en bas vers résistance → SHORT
                return "SHORT"
            else:
                # Prix approche d'en haut vers résistance → AVOID (déjà au-dessus)
                return "AVOID"

        # SUPPORT confirmé
        if context.acting_as == "SUPPORT":
            if current_approach == "FROM_ABOVE":
                # Prix approche d'en haut vers support → LONG
                return "LONG"
            else:
                # Prix approche d'en bas vers support → AVOID (déjà en-dessous)
                return "AVOID"

        # MAGNET (niveau qui attire) → AVOID
        if context.acting_as == "MAGNET":
            return "AVOID"

        return "AVOID"

    def get_level_summary(self, symbol: str) -> Dict[str, LevelContext]:
        """Retourne le résumé de tous les niveaux pour un symbole"""
        return self.levels.get(symbol, {})

    def should_trade(self, symbol: str, direction: str,
                     entry_price: float, trigger_level: float,
                     tick_size: float = 0.25) -> Tuple[bool, str]:
        """
        Vérifie si un trade est cohérent avec le contexte du niveau.

        Args:
            symbol: Symbole (ES, NQ)
            direction: "LONG" ou "SHORT"
            entry_price: Prix d'entrée proposé
            trigger_level: Niveau MenthorQ qui a déclenché le signal

        Returns:
            Tuple (allowed: bool, reason: str)
        """
        # Enregistrer le niveau s'il n'existe pas
        self.register_level(symbol, trigger_level, "MENTHORQ")

        # Mettre à jour le prix
        self.update_price(symbol, entry_price)

        # Analyser le contexte
        results = self.analyze_touch(symbol, entry_price, tick_size)

        if not results:
            # Pas de niveau proche, laisser passer
            return True, "Pas de niveau proche"

        for context, recommendation in results:
            # Vérifier cohérence direction / recommandation
            if direction == "LONG" and recommendation == "SHORT":
                return False, f"❌ LONG interdit: {context.level_type} @ {context.level_price:.2f} agit comme RÉSISTANCE ({context.rejections} rejets)"

            if direction == "SHORT" and recommendation == "LONG":
                return False, f"❌ SHORT interdit: {context.level_type} @ {context.level_price:.2f} agit comme SUPPORT ({context.rejections} rebonds)"

            if recommendation == "AVOID":
                return False, f"⚠️ AVOID: {context.level_type} @ {context.level_price:.2f} est {context.acting_as} (force: {context.strength_score:.0%})"

        return True, "✅ Direction cohérente avec contexte niveau"


# === SINGLETON INSTANCE ===
_analyzer_instance: Optional[LevelContextAnalyzer] = None

def get_level_analyzer() -> LevelContextAnalyzer:
    """Retourne l'instance singleton de l'analyseur"""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = LevelContextAnalyzer()
    return _analyzer_instance


# === TEST ===
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("=" * 60)
    print("TEST LEVEL CONTEXT ANALYZER")
    print("=" * 60)

    # Creer analyseur avec temps minimum = 0 pour test
    analyzer = LevelContextAnalyzer({'min_touch_interval': 0})

    # Simuler le scenario GEX 3 @ 25725
    symbol = "NQ"
    gex_level = 25725.0

    # Enregistrer le niveau
    analyzer.register_level(symbol, gex_level, "GEX_3")

    print("\n1) SIMULATION: Prix monte vers GEX 3 et rejete plusieurs fois")
    print("-" * 40)

    # Simuler manuellement les touches et rejets
    context = analyzer.levels[symbol][gex_level]

    # Forcer les stats pour test
    context.total_touches = 5
    context.touches_from_below = 5
    context.touches_from_above = 0
    context.rejections = 4
    context.bounces = 0
    context.breakthroughs = 1

    # Classifier manuellement
    analyzer._classify_level(context)

    print("\n2) CLASSIFICATION DU NIVEAU")
    print("-" * 40)
    print(f"GEX 3 @ {gex_level}:")
    print(f"  Total touches: {context.total_touches}")
    print(f"  Touches from below: {context.touches_from_below}")
    print(f"  Rejections: {context.rejections}")
    print(f"  Agit comme: {context.acting_as}")
    print(f"  Force: {context.strength_score:.0%}")

    # Test should_trade
    print("\n3) TEST SHOULD_TRADE")
    print("-" * 40)

    # Mettre a jour prix pour contexte
    for p in [25700, 25710, 25720, 25723]:
        analyzer.update_price(symbol, p)

    # Test LONG (devrait etre bloque car resistance)
    allowed, reason = analyzer.should_trade(
        symbol="NQ",
        direction="LONG",
        entry_price=25724.0,
        trigger_level=gex_level
    )
    # Enlever emojis pour Windows
    reason_clean = reason.replace('\u274c', 'X').replace('\u2705', 'OK').replace('\u26a0\ufe0f', '!')
    print(f"LONG @ 25724 pres de GEX 3: {allowed}")
    print(f"  Raison: {reason_clean}")

    # Test SHORT (devrait etre autorise)
    allowed, reason = analyzer.should_trade(
        symbol="NQ",
        direction="SHORT",
        entry_price=25724.0,
        trigger_level=gex_level
    )
    reason_clean = reason.replace('\u274c', 'X').replace('\u2705', 'OK').replace('\u26a0\ufe0f', '!')
    print(f"SHORT @ 25724 pres de GEX 3: {allowed}")
    print(f"  Raison: {reason_clean}")

    # =========================================
    # TEST FAKEOUT
    # =========================================
    print("\n" + "=" * 60)
    print("TEST FAKEOUT (Cassure + Rejet)")
    print("=" * 60)

    # Nouveau niveau HVL
    hvl_level = 25676.0
    analyzer.register_level(symbol, hvl_level, "HVL_0DTE")
    hvl_context = analyzer.levels[symbol][hvl_level]

    print(f"\nScenario: HVL 0DTE @ {hvl_level}")
    print("1. Prix au-dessus du HVL (25680)")

    # Initialiser: prix au-dessus avec premier appel
    analyzer._detect_fakeout(hvl_context, 25680.0, hvl_level, 0.25)
    hvl_context.last_cross_time = datetime.now()  # Forcer le time pour le test
    print(f"   Currently above: {hvl_context.currently_above}")

    # Prix descend et casse le niveau
    print("2. Prix CASSE vers le bas (25670) - Breakdown!")
    analyzer._detect_fakeout(hvl_context, 25670.0, hvl_level, 0.25)
    print(f"   Cross direction: {hvl_context.last_cross_direction}")
    print(f"   Currently above: {hvl_context.currently_above}")

    # Prix revient au-dessus = FAKEOUT!
    print("3. Prix REVIENT au-dessus (25680) - FAKEOUT!")
    analyzer._detect_fakeout(hvl_context, 25680.0, hvl_level, 0.25)
    print(f"   Fakeouts detectes: {hvl_context.fakeouts}")
    print(f"   Cross direction: {hvl_context.last_cross_direction}")

    # Classifier apres fakeout
    analyzer._classify_level(hvl_context)
    print(f"\n4. CLASSIFICATION apres FAKEOUT:")
    print(f"   Agit comme: {hvl_context.acting_as}")
    print(f"   Force: {hvl_context.strength_score:.0%}")

    # Test trading apres fakeout
    print("\n5. TEST TRADING apres FAKEOUT:")

    # LONG devrait etre autorise (support fort)
    allowed, reason = analyzer.should_trade(
        symbol="NQ",
        direction="LONG",
        entry_price=25678.0,
        trigger_level=hvl_level
    )
    reason_clean = reason.replace('\u274c', 'X').replace('\u2705', 'OK').replace('\u26a0\ufe0f', '!').replace('\u00c9', 'E')
    print(f"   LONG @ 25678 pres HVL (apres fakeout): {allowed}")
    print(f"   Raison: {reason_clean}")

    print("\n" + "=" * 60)
    print("TEST TERMINE")
    print("=" * 60)
