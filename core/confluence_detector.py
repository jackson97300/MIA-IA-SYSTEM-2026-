"""
core/confluence_detector.py

🎯 DÉTECTION CONFLUENCE AUTOMATIQUE - PHASE 2 OPTIMISATION MAJEURE

Détecte automatiquement les confluences entre niveaux MenthorQ:
- next_wall + GEX level @ même prix = CONFLUENCE DOUBLE
- HVL + Gamma wall + VWAP = CONFLUENCE TRIPLE
- Etc.

Confluence = 2+ niveaux importants dans tolérance (15 ticks par défaut)
→ Bonus confidence +10% par niveau additionnel (max +25%)

Version: 1.0
Date: 18 Novembre 2025
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Import unified config si disponible
try:
    from config.unified_thresholds import CONFLUENCE_CONFIG
    UNIFIED_CONFIG_AVAILABLE = True
except ImportError:
    UNIFIED_CONFIG_AVAILABLE = False
    # Fallback config
    CONFLUENCE_CONFIG = {
        'enabled': True,
        'tolerance_ticks': 15,
        'min_levels': 2,
        'bonus_per_level': 0.10,
        'max_bonus': 0.25,
        'level_importance': {
            'next_wall': 1.0,
            'gamma_wall': 0.9,
            'hvl': 0.9,
            'gex_level': 0.8,
            'blind_spot': 0.7,
            'vwap': 0.7,
            'value_area': 0.6
        }
    }


@dataclass
class PriceLevel:
    """Représente un niveau de prix détecté"""
    price: float
    type: str  # 'next_wall', 'gex_level', 'hvl', etc.
    subtype: Optional[str] = None  # Pour GEX: 'gex_1', 'gex_2', etc.
    strength: float = 0.5  # Force du niveau (0.0-1.0)
    importance: float = 0.8  # Importance relative (0.0-1.0)
    metadata: Dict[str, Any] = None  # Données additionnelles

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class Confluence:
    """Représente une confluence détectée"""
    price: float  # Prix moyen de la confluence
    levels: List[PriceLevel]  # Niveaux en confluence
    count: int  # Nombre de niveaux
    strength: float  # Force totale (0.0-1.0+)
    distance_ticks: float  # Distance au prix actuel
    bonus_confidence: float  # Bonus confidence à appliquer
    description: str  # Description textuelle

    def get_level_types(self) -> List[str]:
        """Retourne les types de niveaux"""
        return [level.type for level in self.levels]

    def has_type(self, level_type: str) -> bool:
        """Vérifie si un type est présent"""
        return level_type in self.get_level_types()

    def get_highest_importance(self) -> float:
        """Retourne la plus haute importance"""
        return max([level.importance for level in self.levels])


@dataclass
class ConfluenceAnalysis:
    """Résultat complet de l'analyse de confluence"""
    confluences: List[Confluence]
    total_count: int
    strongest_confluence: Optional[Confluence]
    nearest_confluence: Optional[Confluence]
    max_strength: float
    max_bonus: float
    all_levels: List[PriceLevel]  # Tous les niveaux détectés


class ConfluenceDetector:
    """
    Détecteur de confluence automatique

    Workflow:
    1. Extraire tous les niveaux de ML_READY
    2. Grouper niveaux proches (tolérance)
    3. Calculer force de chaque confluence
    4. Calculer bonus confidence
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialise le détecteur

        Args:
            config: Configuration optionnelle (override CONFLUENCE_CONFIG)
        """
        if config:
            self.config = config
        elif UNIFIED_CONFIG_AVAILABLE:
            self.config = CONFLUENCE_CONFIG
        else:
            self.config = CONFLUENCE_CONFIG  # Fallback

        self.enabled = self.config.get('enabled', True)
        self.tolerance_ticks = self.config.get('tolerance_ticks', 15)
        self.min_levels = self.config.get('min_levels', 2)
        self.bonus_per_level = self.config.get('bonus_per_level', 0.10)
        self.max_bonus = self.config.get('max_bonus', 0.25)
        self.level_importance = self.config.get('level_importance', {})

        logger.info("✅ ConfluenceDetector initialisé")
        logger.info(f"   Tolérance: {self.tolerance_ticks} ticks")
        logger.info(f"   Min niveaux: {self.min_levels}")
        logger.info(f"   Bonus par niveau: {self.bonus_per_level:.2f}")

    def detect(self, data: Dict, symbol: str = 'ES') -> ConfluenceAnalysis:
        """
        Détecte toutes les confluences dans les données ML_READY

        Args:
            data: Données ML_READY
            symbol: Symbole (ES/NQ/RTY)

        Returns:
            ConfluenceAnalysis complète
        """
        if not self.enabled:
            return self._empty_analysis()

        try:
            # 1. Extraire tous les niveaux
            all_levels = self._extract_all_levels(data, symbol)

            if len(all_levels) < self.min_levels:
                logger.debug(f"Trop peu de niveaux détectés ({len(all_levels)})")
                return self._empty_analysis()

            # 2. Détecter confluences
            confluences = self._detect_confluences(all_levels, data.get('mid', 0), symbol)

            if not confluences:
                logger.debug("Aucune confluence détectée")
                return ConfluenceAnalysis(
                    confluences=[],
                    total_count=0,
                    strongest_confluence=None,
                    nearest_confluence=None,
                    max_strength=0.0,
                    max_bonus=0.0,
                    all_levels=all_levels
                )

            # 3. Analyser confluences
            strongest = max(confluences, key=lambda c: c.strength)
            nearest = min(confluences, key=lambda c: abs(c.distance_ticks))
            max_strength = strongest.strength
            max_bonus = max([c.bonus_confidence for c in confluences])

            logger.info(f"🎯 {len(confluences)} confluence(s) détectée(s)")
            logger.info(f"   Plus forte: {strongest.count} niveaux @ {strongest.price:.2f} (force={strongest.strength:.2f})")
            logger.info(f"   Plus proche: {nearest.count} niveaux @ {nearest.distance_ticks:.0f}t")
            logger.info(f"   Bonus max: {max_bonus:.2f}")

            return ConfluenceAnalysis(
                confluences=confluences,
                total_count=len(confluences),
                strongest_confluence=strongest,
                nearest_confluence=nearest,
                max_strength=max_strength,
                max_bonus=max_bonus,
                all_levels=all_levels
            )

        except Exception as e:
            logger.error(f"❌ Erreur détection confluence: {e}", exc_info=True)
            return self._empty_analysis()

    def _extract_all_levels(self, data: Dict, symbol: str) -> List[PriceLevel]:
        """
        Extrait tous les niveaux de prix depuis ML_READY

        Args:
            data: Données ML_READY
            symbol: Symbole

        Returns:
            Liste de PriceLevel
        """
        levels = []

        # ═══════════════════════════════════════════════════════════════
        # 1. next_wall (PRIORITÉ MAXIMALE)
        # ═══════════════════════════════════════════════════════════════
        next_wall = data.get('next_wall', {})
        if isinstance(next_wall, dict) and next_wall.get('price', 0) > 0:
            levels.append(PriceLevel(
                price=next_wall['price'],
                type='next_wall',
                subtype=next_wall.get('side', 'unknown'),  # 'put' ou 'call'
                strength=next_wall.get('strength', 0.3),
                importance=self.level_importance.get('next_wall', 1.0),
                metadata={
                    'dist_ticks': next_wall.get('dist_ticks', 0),
                    'age_min': next_wall.get('age_min', 0),
                    'side': next_wall.get('side', '')
                }
            ))
            logger.debug(f"   next_wall @ {next_wall['price']:.2f} (strength={next_wall.get('strength', 0.3):.2f})")

        # ═══════════════════════════════════════════════════════════════
        # 2. GEX Levels (10 niveaux)
        # ═══════════════════════════════════════════════════════════════
        for i in range(1, 11):
            gex = data.get(f'gex_{i}', 0)
            if gex > 0:
                # Top 3 GEX plus importants
                strength = 0.6 if i <= 3 else 0.4
                importance = self.level_importance.get('gex_level', 0.8)
                if i <= 3:
                    importance *= 1.1  # Bonus top 3

                levels.append(PriceLevel(
                    price=gex,
                    type='gex_level',
                    subtype=f'gex_{i}',
                    strength=strength,
                    importance=min(importance, 1.0),
                    metadata={'rank': i}
                ))

                if i <= 3:
                    logger.debug(f"   gex_{i} @ {gex:.2f} (top 3)")

        # ═══════════════════════════════════════════════════════════════
        # 3. Gamma Walls (call_resistance, put_support)
        # ═══════════════════════════════════════════════════════════════
        call_resistance = data.get('call_resistance', 0)
        put_support = data.get('put_support', 0)

        if call_resistance > 0:
            levels.append(PriceLevel(
                price=call_resistance,
                type='gamma_wall',
                subtype='call_resistance',
                strength=0.7,
                importance=self.level_importance.get('gamma_wall', 0.9),
                metadata={'wall_type': 'call'}
            ))
            logger.debug(f"   call_resistance @ {call_resistance:.2f}")

        if put_support > 0:
            levels.append(PriceLevel(
                price=put_support,
                type='gamma_wall',
                subtype='put_support',
                strength=0.7,
                importance=self.level_importance.get('gamma_wall', 0.9),
                metadata={'wall_type': 'put'}
            ))
            logger.debug(f"   put_support @ {put_support:.2f}")

        # ═══════════════════════════════════════════════════════════════
        # 4. HVL (High Volume Level)
        # ═══════════════════════════════════════════════════════════════
        hvl = data.get('hvl', 0)
        if hvl > 0:
            levels.append(PriceLevel(
                price=hvl,
                type='hvl',
                strength=0.6,
                importance=self.level_importance.get('hvl', 0.9),
                metadata={}
            ))
            logger.debug(f"   hvl @ {hvl:.2f}")

        # ═══════════════════════════════════════════════════════════════
        # 5. Blind Spots (9 niveaux max)
        # ═══════════════════════════════════════════════════════════════
        for i in range(9):
            blind_spot = data.get(f'blind_spot_{i}', 0)
            if blind_spot > 0:
                levels.append(PriceLevel(
                    price=blind_spot,
                    type='blind_spot',
                    subtype=f'blind_spot_{i}',
                    strength=0.5,
                    importance=self.level_importance.get('blind_spot', 0.7),
                    metadata={'index': i}
                ))

                if i < 3:
                    logger.debug(f"   blind_spot_{i} @ {blind_spot:.2f}")

        # ═══════════════════════════════════════════════════════════════
        # 6. VWAP (mean)
        # ═══════════════════════════════════════════════════════════════
        vwap = data.get('vwap', 0)
        if vwap > 0:
            levels.append(PriceLevel(
                price=vwap,
                type='vwap',
                subtype='mean',
                strength=0.5,
                importance=self.level_importance.get('vwap', 0.7),
                metadata={}
            ))
            logger.debug(f"   vwap @ {vwap:.2f}")

        # VWAP bands
        vwap_up1 = data.get('vwap_up1', 0)
        vwap_dn1 = data.get('vwap_dn1', 0)

        if vwap_up1 > 0:
            levels.append(PriceLevel(
                price=vwap_up1,
                type='vwap',
                subtype='up1',
                strength=0.4,
                importance=self.level_importance.get('vwap', 0.7) * 0.8,
                metadata={'band': 'up1'}
            ))

        if vwap_dn1 > 0:
            levels.append(PriceLevel(
                price=vwap_dn1,
                type='vwap',
                subtype='dn1',
                strength=0.4,
                importance=self.level_importance.get('vwap', 0.7) * 0.8,
                metadata={'band': 'dn1'}
            ))

        # ═══════════════════════════════════════════════════════════════
        # 7. Value Area (VAH, VAL, VPOC)
        # ═══════════════════════════════════════════════════════════════
        vva = data.get('vva', {})
        if isinstance(vva, dict):
            vah = vva.get('vah', 0)
            val = vva.get('val', 0)
            vpoc = vva.get('vpoc', 0)

            if vah > 0:
                levels.append(PriceLevel(
                    price=vah,
                    type='value_area',
                    subtype='vah',
                    strength=0.5,
                    importance=self.level_importance.get('value_area', 0.6),
                    metadata={'level': 'high'}
                ))
                logger.debug(f"   vah @ {vah:.2f}")

            if val > 0:
                levels.append(PriceLevel(
                    price=val,
                    type='value_area',
                    subtype='val',
                    strength=0.5,
                    importance=self.level_importance.get('value_area', 0.6),
                    metadata={'level': 'low'}
                ))
                logger.debug(f"   val @ {val:.2f}")

            if vpoc > 0:
                levels.append(PriceLevel(
                    price=vpoc,
                    type='value_area',
                    subtype='vpoc',
                    strength=0.6,
                    importance=self.level_importance.get('value_area', 0.6) * 1.1,
                    metadata={'level': 'poc'}
                ))
                logger.debug(f"   vpoc @ {vpoc:.2f}")

        # Trier par prix
        levels.sort(key=lambda l: l.price)

        logger.debug(f"Total niveaux extraits: {len(levels)}")

        return levels

    def _detect_confluences(self, levels: List[PriceLevel], mid_price: float,
                           symbol: str) -> List[Confluence]:
        """
        Détecte les confluences dans une liste de niveaux

        Args:
            levels: Liste de niveaux triés par prix
            mid_price: Prix actuel
            symbol: Symbole

        Returns:
            Liste de Confluence détectées
        """
        confluences = []
        tick_size = 0.25 if symbol in ['ES', 'NQ'] else 0.10

        i = 0
        while i < len(levels):
            # Commencer un groupe avec le niveau courant
            group = [levels[i]]
            j = i + 1

            # Ajouter tous les niveaux dans la tolérance
            while j < len(levels):
                dist_ticks = abs(levels[j].price - levels[i].price) / tick_size

                if dist_ticks <= self.tolerance_ticks:
                    group.append(levels[j])
                    j += 1
                else:
                    break  # Trop loin, arrêter

            # Si 2+ niveaux = confluence
            if len(group) >= self.min_levels:
                confluence = self._create_confluence(group, mid_price, tick_size)
                confluences.append(confluence)

                logger.debug(f"   Confluence @ {confluence.price:.2f}: {confluence.count} niveaux")

            # Passer au prochain groupe (éviter doublons)
            i = j if j > i + 1 else i + 1

        return confluences

    def _create_confluence(self, levels: List[PriceLevel], mid_price: float,
                          tick_size: float) -> Confluence:
        """
        Crée un objet Confluence depuis un groupe de niveaux

        Args:
            levels: Niveaux en confluence
            mid_price: Prix actuel
            tick_size: Taille du tick

        Returns:
            Confluence
        """
        # Prix moyen de la confluence
        avg_price = sum(level.price for level in levels) / len(levels)

        # Force totale (somme pondérée)
        total_strength = sum(level.strength * level.importance for level in levels)
        total_strength = min(total_strength, 1.5)  # Cap à 1.5

        # Distance au prix actuel
        distance_ticks = abs(mid_price - avg_price) / tick_size

        # Bonus confidence
        # Base: bonus_per_level × (count - 1)
        # Max: max_bonus
        bonus = self.bonus_per_level * (len(levels) - 1)
        bonus = min(bonus, self.max_bonus)

        # Bonus extra si next_wall présent
        has_next_wall = any(level.type == 'next_wall' for level in levels)
        if has_next_wall:
            bonus += 0.05  # +5% bonus
            bonus = min(bonus, self.max_bonus)

        # Description
        level_types = [level.type for level in levels]
        type_counts = {}
        for lt in level_types:
            type_counts[lt] = type_counts.get(lt, 0) + 1

        desc_parts = []
        for lt, count in sorted(type_counts.items(), key=lambda x: -x[1]):
            if count > 1:
                desc_parts.append(f"{count}× {lt}")
            else:
                desc_parts.append(lt)

        description = " + ".join(desc_parts[:3])  # Max 3 types dans description
        if len(desc_parts) > 3:
            description += f" + {len(desc_parts) - 3} autres"

        return Confluence(
            price=avg_price,
            levels=levels,
            count=len(levels),
            strength=total_strength,
            distance_ticks=distance_ticks,
            bonus_confidence=bonus,
            description=description
        )

    def _empty_analysis(self) -> ConfluenceAnalysis:
        """Retourne analyse vide"""
        return ConfluenceAnalysis(
            confluences=[],
            total_count=0,
            strongest_confluence=None,
            nearest_confluence=None,
            max_strength=0.0,
            max_bonus=0.0,
            all_levels=[]
        )

    def get_nearest_confluence_to_price(self, analysis: ConfluenceAnalysis,
                                        target_price: float) -> Optional[Confluence]:
        """
        Trouve la confluence la plus proche d'un prix cible

        Args:
            analysis: ConfluenceAnalysis
            target_price: Prix cible

        Returns:
            Confluence la plus proche ou None
        """
        if not analysis.confluences:
            return None

        return min(analysis.confluences,
                  key=lambda c: abs(c.price - target_price))

    def get_confluences_within_distance(self, analysis: ConfluenceAnalysis,
                                       max_distance_ticks: float) -> List[Confluence]:
        """
        Retourne les confluences dans une distance max

        Args:
            analysis: ConfluenceAnalysis
            max_distance_ticks: Distance max en ticks

        Returns:
            Liste de Confluence
        """
        return [c for c in analysis.confluences
                if abs(c.distance_ticks) <= max_distance_ticks]


# ═══════════════════════════════════════════════════════════════════════
# INSTANCE GLOBALE (Singleton)
# ═══════════════════════════════════════════════════════════════════════

_global_detector: Optional[ConfluenceDetector] = None

def get_confluence_detector() -> ConfluenceDetector:
    """
    Retourne l'instance globale du détecteur (singleton)

    Returns:
        ConfluenceDetector
    """
    global _global_detector
    if _global_detector is None:
        _global_detector = ConfluenceDetector()
    return _global_detector


# ═══════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════

def detect_confluences(data: Dict, symbol: str = 'ES') -> ConfluenceAnalysis:
    """
    Function helper pour détecter confluences

    Args:
        data: ML_READY data
        symbol: Symbole

    Returns:
        ConfluenceAnalysis
    """
    detector = get_confluence_detector()
    return detector.detect(data, symbol)


def get_confluence_bonus(data: Dict, symbol: str = 'ES') -> float:
    """
    Retourne le bonus de confidence maximal des confluences

    Args:
        data: ML_READY data
        symbol: Symbole

    Returns:
        Bonus confidence (0.0-0.25)
    """
    analysis = detect_confluences(data, symbol)
    return analysis.max_bonus


# ═══════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════

__all__ = [
    'PriceLevel',
    'Confluence',
    'ConfluenceAnalysis',
    'ConfluenceDetector',
    'get_confluence_detector',
    'detect_confluences',
    'get_confluence_bonus'
]
