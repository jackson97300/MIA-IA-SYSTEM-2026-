"""
🎯 ES PURE MENTHORQ STRATEGY V2.3 - ORDERFLOW STRICT
=====================================================
Stratégie ES distincte - Approche institutionnelle pure

Version: 2.3 (ORDERFLOW = VALIDATEUR STRICT!)
Date: 27 Novembre 2025

🔥 FIX CRITIQUE V2.3:
✅ OrderFlow REJETTE les trades si non confirmé (était ignoré!)
✅ Seuil OrderFlow: 0.55 → 0.60 (plus strict)
✅ SL: 16t (compromis)
✅ BE trigger: 7t
✅ Trail: 10t
✅ Near level: 8t
❌ hvl_magnet DÉSACTIVÉ

EDGE FONDAMENTAL (CORRIGÉ):
- OPTIONS (MenthorQ) = LEADER (direction, niveaux)  
- ORDERFLOW = VALIDATEUR STRICT (confirme ou REJETTE!)
  ↳ Si orderflow non confirmé → PAS DE TRADE

PRINCIPES CLÉS V2:
1. JAMAIS trader au milieu de nulle part
2. VWAP + Déviations comme niveaux clés
3. Breakouts quand niveaux cassent
4. Pullbacks AVEC MARGE uniquement (pas les sales)
5. Trailing Stop + Breakeven systématiques
6. 🔥 OrderFlow VALIDE ou REJETTE chaque setup

SETUPS ACTIFS V2.3:
1. GAMMA_WALL_DEFENSE - Fade aux walls (70%)
2. ❌ HVL_MAGNET - DÉSACTIVÉ (0% WR)
3. VWAP_REVERSION - Retour au VWAP/déviations (10%)
4. BREAKOUT - Quand niveau casse avec volume (10%)
5. PULLBACK_CLEAN - Pullback avec marge de sécurité (10%)
"""

import logging
from typing import Dict, List, Optional, Tuple, NamedTuple
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION ES V2
# ============================================================================

ES_CONFIG_V2 = {
    # Identification
    'symbol': 'ES',
    'tick_size': 0.25,
    'point_value': 50.00,
    'tick_value': 12.50,
    
    # Stop Loss - OPTIMISÉ V2.2 (compromis 16t)
    'sl_base_ticks': 16,      # ⬆️ 15→18→16 (compromis)
    'sl_max_ticks': 20,       # Retour à 20
    'sl_min_ticks': 12,       # Gardé
    'sl_buffer_ticks': 3,
    
    # Take Profit
    'tp1_ticks': 12,      # TP1 rapide (50% position)
    'tp2_ticks': 20,      # TP2 (30% position)
    'tp3_ticks': 30,      # TP3 runner (20% position)
    
    # Trailing Stop - OPTIMISÉ V2.2
    'trail_activation_ticks': 10,  # ⬇️ 12→10 (capture plus tôt)
    'trail_distance_ticks': 5,     # Trail à 5t du prix
    'breakeven_trigger_ticks': 7,  # ⬇️ 8→7 (sauve trade MaxFav=7t)
    'breakeven_buffer_ticks': 2,   # BE = entry + 2t
    
    # Risk Management
    'max_trades_day': 8,
    'max_loss_day_usd': 500,
    'position_size': 1,
    
    # Distances CRITIQUES - OPTIMISÉ V2.2
    'near_level_ticks': 8,         # ⬇️ 10→8 (plus proche = meilleur)
    'far_level_ticks': 25,         # Niveau "loin" - pas de trade
    'danger_zone_ticks': 5,        # SL interdit à ±5t d'un niveau
    'pullback_margin_ticks': 8,    # Marge minimum pour pullback
    
    # Breakout config
    'breakout_confirm_ticks': 3,   # Break confirmé après 3t au-delà
    'breakout_volume_mult': 1.5,   # Volume 1.5x pour confirmer
    
    # VWAP config
    'vwap_stddev_1': 0.65,         # 1 StdDev - niveau moyen
    'vwap_stddev_2': 0.80,         # 2 StdDev - niveau fort
    'vwap_reversion_trigger': 15,  # Entry si >15t du VWAP
}

# Sessions ES - US uniquement
ES_SESSIONS_V2 = {
    'LONDON_OVERLAP': {
        'hours': (12, 14),
        'enabled': True,
        'min_confluence': 0.70,
        'description': 'Overlap EU/US - Volatilité modérée'
    },
    'US_OPEN': {
        'hours': (14.5, 16),
        'enabled': True,
        'min_confluence': 0.55,
        'description': 'US Open - PRIME TIME'
    },
    'US_MID': {
        'hours': (16, 19.5),
        'enabled': True,
        'min_confluence': 0.60,
        'description': 'Mid-session - Flux institutionnels'
    },
    'US_POWER_HOUR': {
        'hours': (19.5, 21),
        'enabled': True,
        'min_confluence': 0.55,
        'description': 'Power Hour - PREMIUM'
    },
    # DÉSACTIVÉES
    'AFTER_HOURS': {'hours': (21, 24), 'enabled': False},
    'ASIA': {'hours': (0, 6), 'enabled': False},
    'LONDON_EARLY': {'hours': (6, 12), 'enabled': False},
}

# R:R adaptatifs par obstacle
ES_MIN_RR_V2 = {
    # OBSTACLES CRITIQUES - Défendus par institutions
    'CALL_RESISTANCE': 0.8, 'PUT_SUPPORT': 0.8,
    'CALL_RESISTANCE_0DTE': 0.8, 'PUT_SUPPORT_0DTE': 0.8,
    'GAMMA_WALL': 0.8, 'GAMMA_WALL_0DTE': 0.8,
    'HVL': 0.7, 'HVL_0DTE': 0.7,
    'SWING_HIGH': 0.8, 'SWING_LOW': 0.8,
    
    # GEX 1-10 (classés par force décroissante)
    # GEX_1 = le plus de gamma, GEX_10 = le moins
    'GEX_1': 0.75, 'GEX_2': 0.70, 'GEX_3': 0.65,
    'GEX_4': 0.60, 'GEX_5': 0.55, 'GEX_6': 0.50,
    'GEX_7': 0.50, 'GEX_8': 0.45, 'GEX_9': 0.45, 'GEX_10': 0.45,
    
    # VWAP - Niveaux statistiques
    'VWAP': 0.6,
    'VWAP_UP1': 0.6, 'VWAP_DN1': 0.6,
    'VWAP_UP2': 0.7, 'VWAP_DN2': 0.7,   # Plus fort = plus strict
    'VWAP_UP3': 0.75, 'VWAP_DN3': 0.75,
    'VWAP_WEEKLY': 0.7,
    'PVWAP': 0.55,
    
    # OBSTACLES MOYENS
    'IBH': 0.6, 'IBL': 0.6,
    'VAH': 0.6, 'VAL': 0.6, 'VPOC': 0.6,
    
    # OBSTACLES FAIBLES - Zones de réaction
    'BLIND_SPOT': 0.45,  # Générique
    'BLIND_SPOT_1': 0.5, 'BLIND_SPOT_2': 0.5, 'BLIND_SPOT_3': 0.5,
    'BLIND_SPOT_4': 0.4, 'BLIND_SPOT_5': 0.4,
    'ONH': 0.5, 'ONL': 0.5,
    'ROUND_NUMBER': 0.4,
    '1D_MAX': 0.6, '1D_MIN': 0.6,
    
    # Défaut
    'DEFAULT': 0.55,
}


# ============================================================================
# ENUMS & DATACLASSES
# ============================================================================

class ESSetupType(Enum):
    """Types de setups ES V2"""
    GAMMA_WALL_DEFENSE = "gamma_wall_defense"   # Fade aux walls
    HVL_MAGNET = "hvl_magnet"                   # Mean reversion HVL
    VWAP_REVERSION = "vwap_reversion"           # Retour au VWAP
    BREAKOUT = "breakout"                       # Break niveau avec volume
    PULLBACK_CLEAN = "pullback_clean"           # Pullback avec marge
    ONE_DAY_BOUNDARY = "1d_boundary"            # Expected move
    
class GammaRegime(Enum):
    """Régime gamma ES"""
    POSITIVE = "positive"       # Au-dessus HVL - Mean Reversion
    NEGATIVE = "negative"       # Sous HVL - Momentum
    TRANSITION = "transition"   # Zone neutre - PAS DE TRADE


@dataclass
class ESLevel:
    """Niveau ES avec métadonnées complètes"""
    price: float
    type: str
    strength: float           # 0-1
    distance_ticks: float
    side: str                 # support/resistance/magnet
    is_vwap: bool = False     # Flag VWAP
    is_breakable: bool = True # Peut être cassé
    
    def __repr__(self):
        marker = "🔵" if self.is_vwap else "🟢" if self.side == 'support' else "🔴"
        return f"{marker} {self.type}@{self.price:.2f} ({self.distance_ticks:.1f}t)"


@dataclass
class ESSetup:
    """Setup ES identifié avec gestion complète"""
    setup_type: ESSetupType
    direction: str              # LONG/SHORT
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    take_profit_3: float
    
    # Métadonnées
    confluence_score: float     # 0-1
    risk_reward: float
    key_level: ESLevel          # Niveau principal du setup
    conditions: List[str] = field(default_factory=list)
    
    # Gestion dynamique
    trail_active: bool = False
    breakeven_active: bool = False
    
    def __repr__(self):
        return (f"ES {self.setup_type.value} {self.direction} "
                f"@ {self.entry_price:.2f} | SL: {self.stop_loss:.2f} | "
                f"TP: {self.take_profit_1:.2f}/{self.take_profit_2:.2f}/{self.take_profit_3:.2f} | "
                f"R:R {self.risk_reward:.2f}")


# ============================================================================
# CLASSE PRINCIPALE V2
# ============================================================================

class ESPureMenthorQV2:
    """
    🎯 ES Pure MenthorQ Strategy V2
    
    EDGE: Options (Leader) + OrderFlow (Validateur)
    
    Principes:
    1. JAMAIS au milieu de nulle part
    2. VWAP + déviations comme niveaux clés
    3. Breakouts quand niveaux cassent
    4. Pullbacks PROPRES avec marge
    5. Trailing + BE systématiques
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or ES_CONFIG_V2
        self.sessions = ES_SESSIONS_V2
        self.min_rr = ES_MIN_RR_V2
        self.tick_size = self.config['tick_size']
        
        # Stats journalières
        self.daily_stats = {
            'trades': 0,
            'wins': 0,
            'losses': 0,
            'pnl': 0.0,
            'date': None,
        }
        
        # Historique niveaux cassés (pour pullbacks)
        self.broken_levels: List[Dict] = []
        
        logger.info("=" * 60)
        logger.info("🎯 ES PURE MENTHORQ V2 INITIALIZED")
        logger.info("=" * 60)
        logger.info(f"   EDGE: Options (Leader) + OrderFlow (Validateur)")
        logger.info(f"   Max trades/jour: {self.config['max_trades_day']}")
        logger.info(f"   SL: {self.config['sl_min_ticks']}-{self.config['sl_max_ticks']} ticks")
        logger.info(f"   Trail après: +{self.config['trail_activation_ticks']}t")
        logger.info(f"   BE après: +{self.config['breakeven_trigger_ticks']}t")
        logger.info("=" * 60)
    
    # ========================================================================
    # SESSION MANAGEMENT
    # ========================================================================
    
    def _reset_daily_stats_if_needed(self):
        """Reset stats si nouveau jour."""
        today = datetime.now(timezone.utc).date()
        if self.daily_stats['date'] != today:
            self.daily_stats = {
                'trades': 0, 'wins': 0, 'losses': 0,
                'pnl': 0.0, 'date': today,
            }
            self.broken_levels = []  # Reset niveaux cassés
            logger.info("📅 ES Daily stats + broken levels reset")
    
    def _get_current_session(self, tick: Optional[Dict] = None) -> Tuple[str, Dict]:
        """
        Retourne session actuelle.
        
        En mode backtest (tick fourni), utilise le timestamp du tick.
        En mode live, utilise l'heure actuelle.
        """
        # Mode backtest: utiliser le timestamp du tick
        if tick and 't_ms' in tick:
            ts = datetime.fromtimestamp(tick['t_ms'] / 1000, tz=timezone.utc)
            current_hour = ts.hour + ts.minute / 60
        else:
            # Mode live
            now = datetime.now(timezone.utc)
            current_hour = now.hour + now.minute / 60
        
        for name, cfg in self.sessions.items():
            if 'hours' in cfg:
                start, end = cfg['hours']
                if start <= current_hour < end:
                    return name, cfg
        
        return 'OUTSIDE', {'enabled': False}
    
    def _is_trading_allowed(self, tick: Optional[Dict] = None) -> Tuple[bool, str]:
        """Vérifie si on peut trader."""
        self._reset_daily_stats_if_needed()
        
        # Check session
        session_name, session_cfg = self._get_current_session(tick)
        if not session_cfg.get('enabled', False):
            return False, f"Session {session_name} désactivée"
        
        # Check max trades
        if self.daily_stats['trades'] >= self.config['max_trades_day']:
            return False, f"Max trades atteint ({self.config['max_trades_day']})"
        
        # Check max loss
        if self.daily_stats['pnl'] <= -self.config['max_loss_day_usd']:
            return False, f"Max loss atteint (${self.config['max_loss_day_usd']})"
        
        return True, f"Session {session_name} OK"
    
    # ========================================================================
    # GAMMA REGIME
    # ========================================================================
    
    def _get_gamma_regime(self, tick: Dict) -> GammaRegime:
        """
        Détermine régime gamma ES.
        
        ES: 1 point = 4 ticks = $50
        
        Zones:
        - > 20 ticks au-dessus HVL = POSITIVE (mean reversion)
        - < 20 ticks sous HVL = NEGATIVE (momentum)  
        - ±20 ticks du HVL = TRANSITION (attention)
        """
        mid = tick.get('mid', 0)
        hvl = tick.get('hvl', 0)
        ts = self.tick_size
        
        if not hvl or hvl <= 0:
            return GammaRegime.TRANSITION
        
        distance_ticks = (mid - hvl) / ts
        
        # Zones ES en TICKS (plus précis)
        if distance_ticks > 20:  # +5 points au-dessus HVL
            return GammaRegime.POSITIVE
        elif distance_ticks < -20:  # -5 points sous HVL
            return GammaRegime.NEGATIVE
        else:
            # Zone TRANSITION = PEUT trader mais avec prudence
            # On ne bloque plus, on laisse les autres setups décider
            if abs(distance_ticks) <= 8:  # Très proche (±2 points)
                return GammaRegime.TRANSITION
            elif distance_ticks > 0:
                return GammaRegime.POSITIVE  # Légèrement au-dessus
            else:
                return GammaRegime.NEGATIVE  # Légèrement en-dessous
    
    # ========================================================================
    # EXTRACTION DES NIVEAUX - INCLUANT VWAP COMPLET
    # ========================================================================
    
    def _extract_levels(self, tick: Dict) -> List[ESLevel]:
        """
        Extrait TOUS les niveaux ES incluant VWAP et déviations.
        """
        levels = []
        mid = tick.get('mid', 0)
        ts = self.tick_size
        
        if mid <= 0:
            return levels
        
        # -----------------------------------------------------------------
        # 1. NIVEAUX OPTIONS INSTITUTIONNELS (LEADER)
        # -----------------------------------------------------------------
        
        # HVL - Niveau principal
        if tick.get('hvl', 0) > 0:
            levels.append(ESLevel(
                price=tick['hvl'],
                type='HVL',
                strength=0.95,
                distance_ticks=abs(mid - tick['hvl']) / ts,
                side='magnet'
            ))
        
        # Call Resistance / Put Support
        if tick.get('call_resistance', 0) > 0:
            levels.append(ESLevel(
                price=tick['call_resistance'],
                type='CALL_RESISTANCE',
                strength=0.90,
                distance_ticks=abs(mid - tick['call_resistance']) / ts,
                side='resistance',
                is_breakable=False  # Rarement cassé
            ))
        
        if tick.get('put_support', 0) > 0:
            levels.append(ESLevel(
                price=tick['put_support'],
                type='PUT_SUPPORT',
                strength=0.90,
                distance_ticks=abs(mid - tick['put_support']) / ts,
                side='support',
                is_breakable=False
            ))
        
        # GEX Levels (1-10)
        for i in range(1, 11):
            gex_key = f'gex_{i}'
            if tick.get(gex_key, 0) > 0:
                gex_price = tick[gex_key]
                strength = max(0.5, 1.0 - (i * 0.05))  # GEX1=0.95, GEX10=0.50
                levels.append(ESLevel(
                    price=gex_price,
                    type=f'GEX_{i}',
                    strength=strength,
                    distance_ticks=abs(mid - gex_price) / ts,
                    side='resistance' if gex_price > mid else 'support',
                    is_breakable=(i > 3)  # GEX 1-3 plus solides
                ))
        
        # Gamma Wall
        if tick.get('gamma_wall_level', 0) > 0:
            levels.append(ESLevel(
                price=tick['gamma_wall_level'],
                type='GAMMA_WALL',
                strength=0.95,
                distance_ticks=abs(mid - tick['gamma_wall_level']) / ts,
                side='resistance' if tick['gamma_wall_level'] > mid else 'support',
                is_breakable=False
            ))
        
        # -----------------------------------------------------------------
        # 2. VWAP ET DÉVIATIONS (CLÉS POUR ES)
        # -----------------------------------------------------------------
        
        vwap_levels = [
            # Daily VWAP
            ('vwap', 'VWAP', 0.85, 'magnet'),
            ('vwap_up1', 'VWAP_UP1', 0.70, 'resistance'),
            ('vwap_dn1', 'VWAP_DN1', 0.70, 'support'),
            ('vwap_up2', 'VWAP_UP2', 0.80, 'resistance'),
            ('vwap_dn2', 'VWAP_DN2', 0.80, 'support'),
            ('vwap_up3', 'VWAP_UP3', 0.75, 'resistance'),
            ('vwap_dn3', 'VWAP_DN3', 0.75, 'support'),
            
            # Weekly VWAP
            ('vwap_weekly', 'VWAP_WEEKLY', 0.80, 'magnet'),
            ('vwap_weekly_up1', 'VWAP_W_UP1', 0.65, 'resistance'),
            ('vwap_weekly_dn1', 'VWAP_W_DN1', 0.65, 'support'),
            
            # Prior VWAP
            ('pvwap', 'PVWAP', 0.70, 'magnet'),
            ('pvwap_up1', 'PVWAP_UP1', 0.60, 'resistance'),
            ('pvwap_dn1', 'PVWAP_DN1', 0.60, 'support'),
        ]
        
        for key, name, strength, side in vwap_levels:
            price = tick.get(key, 0)
            if price > 0:
                levels.append(ESLevel(
                    price=price,
                    type=name,
                    strength=strength,
                    distance_ticks=abs(mid - price) / ts,
                    side=side,
                    is_vwap=True,
                    is_breakable=True  # VWAP peuvent être cassés
                ))
        
        # -----------------------------------------------------------------
        # 3. NIVEAUX TECHNIQUES (SESSION)
        # -----------------------------------------------------------------
        
        # Value Area
        vva = tick.get('vva', {})
        if vva.get('vah', 0) > 0:
            levels.append(ESLevel(
                price=vva['vah'],
                type='VAH',
                strength=0.75,
                distance_ticks=abs(mid - vva['vah']) / ts,
                side='resistance'
            ))
        if vva.get('val', 0) > 0:
            levels.append(ESLevel(
                price=vva['val'],
                type='VAL',
                strength=0.75,
                distance_ticks=abs(mid - vva['val']) / ts,
                side='support'
            ))
        if vva.get('vpoc', 0) > 0:
            levels.append(ESLevel(
                price=vva['vpoc'],
                type='VPOC',
                strength=0.80,
                distance_ticks=abs(mid - vva['vpoc']) / ts,
                side='magnet'
            ))
        
        # Initial Balance & Overnight - DEPUIS STRUCTURE si disponible
        structure = tick.get('structure', {})
        
        # IBH/IBL
        ibh = structure.get('ibh') or tick.get('ibh', 0)
        ibl = structure.get('ibl') or tick.get('ibl', 0)
        
        if ibh and ibh > 0:
            levels.append(ESLevel(
                price=ibh,
                type='IBH',
                strength=0.70,
                distance_ticks=abs(mid - ibh) / ts,
                side='resistance'
            ))
        if ibl and ibl > 0:
            levels.append(ESLevel(
                price=ibl,
                type='IBL',
                strength=0.70,
                distance_ticks=abs(mid - ibl) / ts,
                side='support'
            ))
        
        # ONH/ONL
        onh = structure.get('onh') or tick.get('onh', 0)
        onl = structure.get('onl') or tick.get('onl', 0)
        
        if onh and onh > 0:
            levels.append(ESLevel(
                price=onh,
                type='ONH',
                strength=0.65,
                distance_ticks=abs(mid - onh) / ts,
                side='resistance'
            ))
        if onl and onl > 0:
            levels.append(ESLevel(
                price=onl,
                type='ONL',
                strength=0.65,
                distance_ticks=abs(mid - onl) / ts,
                side='support'
            ))
        
        # -----------------------------------------------------------------
        # 4. 1D EXPECTED MOVE
        # -----------------------------------------------------------------
        
        if tick.get('1d_max', 0) > 0:
            levels.append(ESLevel(
                price=tick['1d_max'],
                type='1D_MAX',
                strength=0.75,
                distance_ticks=abs(mid - tick['1d_max']) / ts,
                side='resistance'
            ))
        if tick.get('1d_min', 0) > 0:
            levels.append(ESLevel(
                price=tick['1d_min'],
                type='1D_MIN',
                strength=0.75,
                distance_ticks=abs(mid - tick['1d_min']) / ts,
                side='support'
            ))
        
        # -----------------------------------------------------------------
        # 5. NEXT_WALL (Niveau dynamique MenthorQ)
        # -----------------------------------------------------------------
        
        next_wall = tick.get('next_wall', {})
        if next_wall and next_wall.get('price', 0) > 0:
            nw_price = next_wall['price']
            nw_side = next_wall.get('side', 'neutral')
            nw_strength = next_wall.get('strength', 0.5)
            
            levels.append(ESLevel(
                price=nw_price,
                type='NEXT_WALL',
                strength=max(0.6, nw_strength),  # Min 0.6
                distance_ticks=abs(mid - nw_price) / ts,
                side='support' if nw_side == 'put' else 'resistance'
            ))
        
        # -----------------------------------------------------------------
        # 6. BLIND SPOTS
        # -----------------------------------------------------------------
        
        for i in range(10):
            bs_key = f'blind_spot_{i}'
            if tick.get(bs_key, 0) > 0:
                bs_price = tick[bs_key]
                strength = max(0.4, 0.65 - (i * 0.05))
                levels.append(ESLevel(
                    price=bs_price,
                    type=f'BLIND_SPOT_{i+1}',
                    strength=strength,
                    distance_ticks=abs(mid - bs_price) / ts,
                    side='resistance' if bs_price > mid else 'support'
                ))
        
        # Trier par distance
        levels.sort(key=lambda x: x.distance_ticks)
        
        return levels
    
    # ========================================================================
    # VALIDATION "PAS AU MILIEU DE NULLE PART"
    # ========================================================================
    
    def _is_near_level(self, tick: Dict, levels: List[ESLevel]) -> Tuple[bool, Optional[ESLevel]]:
        """
        Vérifie que le prix est PRÈS d'un niveau significatif.
        PRINCIPE: JAMAIS trader au milieu de nulle part!
        
        Accepte aussi les niveaux VWAP (magnets) même s'ils sont plus loin
        car ils peuvent servir de targets.
        """
        near_threshold = self.config['near_level_ticks']
        
        # Chercher niveau proche significatif
        for level in levels:
            # Pour niveaux VWAP magnets, on accepte jusqu'à 15 ticks
            if level.is_vwap and level.side == 'magnet':
                threshold = 15
            else:
                threshold = near_threshold
            
            if level.distance_ticks <= threshold and level.strength >= 0.6:
                return True, level
        
        return False, None
    
    # ========================================================================
    # DÉTECTION BREAKOUT
    # ========================================================================
    
    def _detect_breakout(self, tick: Dict, levels: List[ESLevel]) -> Optional[Dict]:
        """
        Détecte un breakout confirmé d'un niveau.
        Conditions:
        1. Prix a traversé le niveau de plus de X ticks
        2. Volume élevé (si disponible)
        3. Niveau était "breakable"
        """
        mid = tick.get('mid', 0)
        confirm_ticks = self.config['breakout_confirm_ticks']
        ts = self.tick_size
        
        for level in levels:
            if not level.is_breakable:
                continue
            
            # Breakout vers le haut (niveau était résistance)
            if level.side == 'resistance' and mid > level.price:
                distance_above = (mid - level.price) / ts
                if confirm_ticks <= distance_above <= 15:  # Pas trop loin
                    # Marquer comme cassé pour pullback
                    self._register_broken_level(level, 'UP', tick['t_ms'])
                    return {
                        'type': 'BREAKOUT_UP',
                        'level': level,
                        'distance': distance_above,
                        'direction': 'LONG'
                    }
            
            # Breakout vers le bas (niveau était support)
            elif level.side == 'support' and mid < level.price:
                distance_below = (level.price - mid) / ts
                if confirm_ticks <= distance_below <= 15:
                    self._register_broken_level(level, 'DOWN', tick['t_ms'])
                    return {
                        'type': 'BREAKOUT_DOWN',
                        'level': level,
                        'distance': distance_below,
                        'direction': 'SHORT'
                    }
        
        return None
    
    def _register_broken_level(self, level: ESLevel, direction: str, timestamp: int):
        """Enregistre niveau cassé pour pullback."""
        # Éviter doublons
        for bl in self.broken_levels:
            if abs(bl['price'] - level.price) < 2 * self.tick_size:
                return
        
        self.broken_levels.append({
            'price': level.price,
            'type': level.type,
            'break_direction': direction,
            'timestamp': timestamp,
            'tested_count': 0
        })
        
        # Garder max 10 niveaux
        if len(self.broken_levels) > 10:
            self.broken_levels = self.broken_levels[-10:]
    
    # ========================================================================
    # DÉTECTION PULLBACK PROPRE (AVEC MARGE)
    # ========================================================================
    
    def _detect_clean_pullback(self, tick: Dict) -> Optional[Dict]:
        """
        Détecte un pullback PROPRE vers un niveau cassé.
        
        RÈGLE: Le pullback doit avoir une MARGE de sécurité!
        - Prix doit être revenu PRÈS du niveau cassé
        - Mais pas trop profond (sinon c'est un failed breakout)
        """
        mid = tick.get('mid', 0)
        ts = self.tick_size
        margin = self.config['pullback_margin_ticks']
        
        for bl in self.broken_levels:
            level_price = bl['price']
            distance = abs(mid - level_price) / ts
            
            # Pullback zone: entre 2 et margin ticks du niveau
            if 2 <= distance <= margin:
                
                # Breakout UP -> Pullback vers niveau (maintenant support)
                if bl['break_direction'] == 'UP' and mid >= level_price:
                    return {
                        'type': 'PULLBACK_CLEAN',
                        'level_price': level_price,
                        'level_type': bl['type'],
                        'direction': 'LONG',
                        'distance': distance,
                        'margin_ok': True
                    }
                
                # Breakout DOWN -> Pullback vers niveau (maintenant résistance)
                elif bl['break_direction'] == 'DOWN' and mid <= level_price:
                    return {
                        'type': 'PULLBACK_CLEAN',
                        'level_price': level_price,
                        'level_type': bl['type'],
                        'direction': 'SHORT',
                        'distance': distance,
                        'margin_ok': True
                    }
        
        return None
    
    # ========================================================================
    # DÉTECTION VWAP REVERSION
    # ========================================================================
    
    def _detect_vwap_reversion(self, tick: Dict, levels: List[ESLevel]) -> Optional[Dict]:
        """
        Détecte opportunité de retour au VWAP depuis déviation.
        
        Condition: Prix à +2 StdDev, reversion vers VWAP central
        """
        mid = tick.get('mid', 0)
        vwap = tick.get('vwap', 0)
        ts = self.tick_size
        
        if not vwap or vwap <= 0:
            return None
        
        distance_vwap = abs(mid - vwap) / ts
        
        # Trigger reversion si > 15 ticks du VWAP
        if distance_vwap >= self.config['vwap_reversion_trigger']:
            
            # Chercher si on est à une déviation
            vwap_up2 = tick.get('vwap_up2', 0)
            vwap_dn2 = tick.get('vwap_dn2', 0)
            
            # À VWAP+2 StdDev -> SHORT vers VWAP
            if vwap_up2 and mid >= vwap_up2 - 5 * ts:  # Tolérance 5 ticks
                return {
                    'type': 'VWAP_REVERSION',
                    'from_level': 'VWAP_UP2',
                    'target': vwap,
                    'direction': 'SHORT',
                    'distance_to_target': distance_vwap
                }
            
            # À VWAP-2 StdDev -> LONG vers VWAP
            elif vwap_dn2 and mid <= vwap_dn2 + 5 * ts:  # Tolérance 5 ticks
                return {
                    'type': 'VWAP_REVERSION',
                    'from_level': 'VWAP_DN2',
                    'target': vwap,
                    'direction': 'LONG',
                    'distance_to_target': distance_vwap
                }
        
        return None
    
    # ========================================================================
    # ORDERFLOW VALIDATION (VALIDATEUR)
    # ========================================================================
    
    def _validate_orderflow(self, tick: Dict, direction: str) -> Tuple[bool, float, str]:
        """
        Valide l'orderflow COMME CONFIRMATEUR (pas leader).
        
        Utilise:
        - delta, deltaPct
        - depth_imbalance
        - smart_money_flow
        - mia_bullish_score (nouveau!)
        - institutional_pressure (nouveau!)
        
        Retourne: (is_valid, score, reason)
        """
        delta = tick.get('delta', 0)
        delta_pct = tick.get('deltaPct', 0)
        depth_imb = tick.get('depth_imbalance', 0)
        smart_money = tick.get('smart_money_flow', 0)
        mia_score = tick.get('mia_bullish_score', 0)  # -1 à +1
        inst_pressure = tick.get('institutional_pressure', 0)
        
        score = 0.5  # Neutre par défaut
        reasons = []
        
        # Delta direction
        if direction == 'LONG':
            if delta > 0:
                score += 0.12
                reasons.append("Delta+")
            if delta_pct > 0.3:
                score += 0.08
            if depth_imb > 0.1:
                score += 0.08
                reasons.append("DOM+")
            if smart_money > 0:
                score += 0.08
                reasons.append("SMF+")
            # MIA Score (puissant!)
            if mia_score > 0.3:
                score += 0.12
                reasons.append(f"MIA+{mia_score:.1f}")
            elif mia_score < -0.3:
                score -= 0.10  # Pénalité si contre
            # Institutional pressure
            if inst_pressure > 0.1:
                score += 0.05
                
        else:  # SHORT
            if delta < 0:
                score += 0.12
                reasons.append("Delta-")
            if delta_pct < -0.3:
                score += 0.08
            if depth_imb < -0.1:
                score += 0.08
                reasons.append("DOM-")
            if smart_money < 0:
                score += 0.08
                reasons.append("SMF-")
            # MIA Score
            if mia_score < -0.3:
                score += 0.12
                reasons.append(f"MIA{mia_score:.1f}")
            elif mia_score > 0.3:
                score -= 0.10  # Pénalité si contre
            # Institutional pressure
            if inst_pressure < -0.1:
                score += 0.05
        
        # Seuil minimum 0.60 pour valider (STRICT!)
        is_valid = score >= 0.60
        reason = " | ".join(reasons) if reasons else "Neutre"
        
        return is_valid, score, reason
    
    # ========================================================================
    # CALCUL SL PROTÉGÉ
    # ========================================================================
    
    def _calculate_protected_sl(
        self, 
        entry: float, 
        direction: str, 
        tick: Dict,
        levels: List[ESLevel]
    ) -> Tuple[float, str]:
        """
        Calcule SL PROTÉGÉ par un niveau technique.
        
        RÈGLE: SL jamais "au milieu de nulle part"!
        """
        ts = self.tick_size
        buffer = self.config['sl_buffer_ticks']
        sl_min = self.config['sl_min_ticks']
        sl_max = self.config['sl_max_ticks']
        
        # Trouver niveaux de protection
        protection_levels = []
        
        if direction == 'LONG':
            # Pour LONG, chercher supports SOUS entry
            for lvl in levels:
                if lvl.side in ['support', 'magnet'] and lvl.price < entry:
                    dist = (entry - lvl.price) / ts
                    if sl_min - 3 <= dist <= sl_max + 5:  # Dans zone acceptable
                        protection_levels.append((lvl, dist))
        else:
            # Pour SHORT, chercher résistances AU-DESSUS entry
            for lvl in levels:
                if lvl.side in ['resistance', 'magnet'] and lvl.price > entry:
                    dist = (lvl.price - entry) / ts
                    if sl_min - 3 <= dist <= sl_max + 5:
                        protection_levels.append((lvl, dist))
        
        # Trier par distance croissante et force
        protection_levels.sort(key=lambda x: (x[1], -x[0].strength))
        
        if protection_levels:
            best_level, best_dist = protection_levels[0]
            
            if direction == 'LONG':
                sl = best_level.price - buffer * ts
                reason = f"SL sous {best_level.type}@{best_level.price:.2f}"
            else:
                sl = best_level.price + buffer * ts
                reason = f"SL sur {best_level.type}@{best_level.price:.2f}"
            
            return sl, reason
        
        # Fallback: SL par défaut
        default_sl_ticks = self.config['sl_base_ticks']
        if direction == 'LONG':
            sl = entry - default_sl_ticks * ts
        else:
            sl = entry + default_sl_ticks * ts
        
        return sl, "SL défaut (AUCUN NIVEAU PROTECTION!)"
    
    # ========================================================================
    # VALIDATION SL (PAS EN ZONE DANGER)
    # ========================================================================
    
    def _validate_sl_position(
        self, 
        sl: float, 
        levels: List[ESLevel],
        direction: str,
        key_level: ESLevel = None  # Niveau qu'on trade (à exclure)
    ) -> Tuple[bool, str]:
        """
        Vérifie que SL n'est PAS dans une zone de "stop hunt".
        
        Zone danger: ±5 ticks d'un niveau connu
        EXCEPTION: Le niveau qu'on trade (key_level) est OK car c'est normal
        que le SL soit juste après ce niveau.
        """
        danger_zone = self.config['danger_zone_ticks']
        ts = self.tick_size
        
        for lvl in levels:
            # Exclure le niveau qu'on trade - c'est normal que SL soit juste après
            if key_level and abs(lvl.price - key_level.price) < 2 * ts:
                continue
            
            dist = abs(sl - lvl.price) / ts
            
            if dist < danger_zone:
                return False, f"⚠️ SL à {dist:.0f}t de {lvl.type}@{lvl.price:.2f} - STOP HUNT RISK!"
        
        return True, "SL OK"
    
    # ========================================================================
    # CALCUL R:R ADAPTATIF
    # ========================================================================
    
    def _get_min_rr_for_obstacle(self, obstacle_type: str) -> float:
        """Retourne R:R minimum selon type d'obstacle."""
        # Chercher exact match
        if obstacle_type in self.min_rr:
            return self.min_rr[obstacle_type]
        
        # Chercher match partiel
        for key, value in self.min_rr.items():
            if key in obstacle_type:
                return value
        
        return self.min_rr['DEFAULT']
    
    def _calculate_rr(
        self, 
        entry: float, 
        sl: float, 
        tp: float, 
        direction: str
    ) -> float:
        """Calcule ratio Risk:Reward."""
        if direction == 'LONG':
            risk = entry - sl
            reward = tp - entry
        else:
            risk = sl - entry
            reward = entry - tp
        
        if risk <= 0:
            return 0.0
        
        return reward / risk
    
    # ========================================================================
    # GÉNÉRATION DE SETUP
    # ========================================================================
    
    def _generate_setup(
        self,
        tick: Dict,
        setup_type: ESSetupType,
        direction: str,
        entry: float,
        key_level: ESLevel,
        levels: List[ESLevel],
        target_override: float = None
    ) -> Optional[ESSetup]:
        """
        Génère un setup complet avec SL protégé et TP.
        """
        ts = self.tick_size
        
        logger.debug(f"📝 Génération setup {setup_type.value} {direction}...")
        
        # 1. Calculer SL protégé
        sl, sl_reason = self._calculate_protected_sl(entry, direction, tick, levels)
        logger.debug(f"   SL: {sl:.2f} ({sl_reason})")
        
        # 2. Valider SL (exclure le niveau qu'on trade)
        sl_valid, sl_msg = self._validate_sl_position(sl, levels, direction, key_level)
        if not sl_valid:
            logger.warning(f"❌ {sl_msg}")
            return None
        
        # 3. Calculer TPs
        if target_override:
            tp1 = target_override
            tp2 = target_override + (8 * ts if direction == 'LONG' else -8 * ts)
            tp3 = target_override + (15 * ts if direction == 'LONG' else -15 * ts)
        else:
            if direction == 'LONG':
                tp1 = entry + self.config['tp1_ticks'] * ts
                tp2 = entry + self.config['tp2_ticks'] * ts
                tp3 = entry + self.config['tp3_ticks'] * ts
            else:
                tp1 = entry - self.config['tp1_ticks'] * ts
                tp2 = entry - self.config['tp2_ticks'] * ts
                tp3 = entry - self.config['tp3_ticks'] * ts
        
        # 4. Calculer R:R
        rr = self._calculate_rr(entry, sl, tp1, direction)
        min_rr = self._get_min_rr_for_obstacle(key_level.type)
        
        if rr < min_rr:
            logger.info(f"❌ R:R insuffisant: {rr:.2f} < {min_rr:.2f} (obstacle: {key_level.type})")
            return None
        
        # 5. Valider orderflow - ✅ VALIDATEUR STRICT !
        of_valid, of_score, of_reason = self._validate_orderflow(tick, direction)
        if not of_valid:
            logger.info(f"❌ REJET: OrderFlow non confirmé ({of_score:.2f}): {of_reason}")
            return None  # ← REJETER le trade !
        
        # 6. Score confluence
        confluence = 0.5
        confluence += key_level.strength * 0.3  # Force du niveau
        confluence += of_score * 0.2            # OrderFlow
        if sl_reason != "SL défaut (AUCUN NIVEAU PROTECTION!)":
            confluence += 0.1  # Bonus SL protégé
        
        # 7. Créer setup
        setup = ESSetup(
            setup_type=setup_type,
            direction=direction,
            entry_price=entry,
            stop_loss=sl,
            take_profit_1=tp1,
            take_profit_2=tp2,
            take_profit_3=tp3,
            confluence_score=min(1.0, confluence),
            risk_reward=rr,
            key_level=key_level,
            conditions=[
                f"Niveau: {key_level}",
                sl_reason,
                f"R:R: {rr:.2f} (min: {min_rr:.2f})",
                f"OrderFlow: {of_reason} ({of_score:.2f})"
            ]
        )
        
        return setup
    
    # ========================================================================
    # IDENTIFICATION DES SETUPS
    # ========================================================================
    
    def _identify_setups(self, tick: Dict, levels: List[ESLevel]) -> List[ESSetup]:
        """
        Identifie tous les setups possibles.
        """
        setups = []
        mid = tick.get('mid', 0)
        gamma = self._get_gamma_regime(tick)
        
        # Skip si TRANSITION STRICT (vraiment collé au HVL)
        if gamma == GammaRegime.TRANSITION:
            logger.info("⚠️ Régime TRANSITION - Setups limités aux Gamma Walls uniquement")
            # En transition, on n'accepte QUE les Gamma Wall Defense
            # Car ce sont des niveaux défendus peu importe le régime
        
        # -----------------------------------------------------------------
        # SETUP 1: GAMMA WALL DEFENSE (Fade les walls)
        # -----------------------------------------------------------------
        # TOUS les GEX 1-10 sont tradables (classés par force: GEX_1 > GEX_2 > ... > GEX_10)
        # MenthorQ: "GEX Level 0 = highest Net GEX, GEX Level 1 = second highest, etc."
        
        all_tradable_walls = [
            # Niveaux primaires (les plus défendus)
            'CALL_RESISTANCE', 'PUT_SUPPORT', 'GAMMA_WALL',
            'CALL_RESISTANCE_0DTE', 'PUT_SUPPORT_0DTE', 'GAMMA_WALL_0DTE',
            # GEX secondaires (TOUS tradables, classés par force)
            'GEX_1', 'GEX_2', 'GEX_3', 'GEX_4', 'GEX_5',
            'GEX_6', 'GEX_7', 'GEX_8', 'GEX_9', 'GEX_10',
        ]
        
        for lvl in levels[:12]:  # Top 12 niveaux proches (augmenté de 8)
            if lvl.type in all_tradable_walls:
                if lvl.distance_ticks <= 8:  # ⬇️ 12→8 (plus proche = meilleur)
                    
                    # Fade direction opposée
                    direction = 'SHORT' if lvl.side == 'resistance' else 'LONG'
                    
                    setup = self._generate_setup(
                        tick=tick,
                        setup_type=ESSetupType.GAMMA_WALL_DEFENSE,
                        direction=direction,
                        entry=mid,
                        key_level=lvl,
                        levels=levels
                    )
                    
                    if setup:
                        setups.append(setup)
        
        # -----------------------------------------------------------------
        # SETUP 2: HVL MAGNET - ❌ DÉSACTIVÉ (0% WR, -$375 loss)
        # -----------------------------------------------------------------
        
        # ⚠️ DÉSACTIVÉ SUITE BACKTEST 24NOV:
        # - 0% Win Rate (2 trades, 2 losses)
        # - Perte de $375 (65% du drawdown total)
        # - MaxFav très faible (2-7 ticks) = mauvais timing
        
        # if gamma == GammaRegime.POSITIVE:
        #     hvl_level = next((l for l in levels if l.type == 'HVL'), None)
        #     
        #     if hvl_level and 8 <= hvl_level.distance_ticks <= 40:
        #         direction = 'SHORT' if mid > hvl_level.price else 'LONG'
        #         
        #         logger.info(f"🧲 HVL Magnet détecté: {direction} vers HVL @ {hvl_level.price}")
        #         
        #         setup = self._generate_setup(
        #             tick=tick,
        #             setup_type=ESSetupType.HVL_MAGNET,
        #             direction=direction,
        #             entry=mid,
        #             key_level=hvl_level,
        #             levels=levels,
        #             target_override=hvl_level.price
        #         )
        #         
        #         if setup:
        #             setups.append(setup)
        
        # -----------------------------------------------------------------
        # SETUP 3: VWAP REVERSION
        # -----------------------------------------------------------------
        
        vwap_signal = self._detect_vwap_reversion(tick, levels)
        if vwap_signal:
            vwap_level = next((l for l in levels if l.type == vwap_signal['from_level']), None)
            
            if vwap_level:
                setup = self._generate_setup(
                    tick=tick,
                    setup_type=ESSetupType.VWAP_REVERSION,
                    direction=vwap_signal['direction'],
                    entry=mid,
                    key_level=vwap_level,
                    levels=levels,
                    target_override=vwap_signal['target']
                )
                
                if setup:
                    setups.append(setup)
        
        # -----------------------------------------------------------------
        # SETUP 4: BREAKOUT
        # -----------------------------------------------------------------
        
        breakout = self._detect_breakout(tick, levels)
        if breakout:
            setup = self._generate_setup(
                tick=tick,
                setup_type=ESSetupType.BREAKOUT,
                direction=breakout['direction'],
                entry=mid,
                key_level=breakout['level'],
                levels=levels
            )
            
            if setup:
                setups.append(setup)
        
        # -----------------------------------------------------------------
        # SETUP 5: PULLBACK CLEAN
        # -----------------------------------------------------------------
        
        pullback = self._detect_clean_pullback(tick)
        if pullback:
            # Créer un ESLevel temporaire pour le niveau cassé
            pb_level = ESLevel(
                price=pullback['level_price'],
                type=pullback['level_type'],
                strength=0.70,
                distance_ticks=pullback['distance'],
                side='support' if pullback['direction'] == 'LONG' else 'resistance'
            )
            
            setup = self._generate_setup(
                tick=tick,
                setup_type=ESSetupType.PULLBACK_CLEAN,
                direction=pullback['direction'],
                entry=mid,
                key_level=pb_level,
                levels=levels
            )
            
            if setup:
                setups.append(setup)
        
        return setups
    
    # ========================================================================
    # GÉNÉRATION DU SIGNAL PRINCIPAL
    # ========================================================================
    
    def generate_signal(self, tick: Dict) -> Optional[Dict]:
        """
        Point d'entrée principal - Génère signal ES si conditions remplies.
        """
        # 1. Vérifier si trading autorisé
        allowed, reason = self._is_trading_allowed(tick)
        if not allowed:
            logger.debug(f"Trading non autorisé: {reason}")
            return None
        
        mid = tick.get('mid', 0)
        if mid <= 0:
            return None
        
        # 2. Extraire niveaux
        levels = self._extract_levels(tick)
        
        if not levels:
            logger.warning("Aucun niveau extrait")
            return None
        
        # 3. VÉRIFIER: PAS AU MILIEU DE NULLE PART
        is_near, nearest_level = self._is_near_level(tick, levels)
        if not is_near:
            logger.debug(f"❌ Prix au milieu de nulle part - Niveau proche le plus fort: {levels[0] if levels else 'AUCUN'}")
            return None
        
        logger.info(f"✅ Prix près de: {nearest_level}")
        
        # 4. Identifier setups
        setups = self._identify_setups(tick, levels)
        
        if not setups:
            logger.debug("Aucun setup identifié")
            return None
        
        # 5. Sélectionner meilleur setup
        best_setup = max(setups, key=lambda s: (s.confluence_score, s.risk_reward))
        
        # 6. Log et retourne signal
        logger.info("=" * 60)
        logger.info(f"🎯 ES SIGNAL: {best_setup}")
        logger.info("=" * 60)
        for cond in best_setup.conditions:
            logger.info(f"   • {cond}")
        logger.info("=" * 60)
        
        # Formater signal pour exécution
        return {
            'symbol': 'ES',
            'action': best_setup.direction,
            'entry_price': best_setup.entry_price,
            'stop_loss': best_setup.stop_loss,
            'take_profit_1': best_setup.take_profit_1,
            'take_profit_2': best_setup.take_profit_2,
            'take_profit_3': best_setup.take_profit_3,
            'confidence': best_setup.confluence_score,
            'risk_reward': best_setup.risk_reward,
            'setup_type': best_setup.setup_type.value,
            'key_level': str(best_setup.key_level),
            'strategy': 'es_pure_menthorq_v2',
            'timestamp': tick.get('t_ms', 0),
            # Trade management
            'trail_config': {
                'activation_ticks': self.config['trail_activation_ticks'],
                'distance_ticks': self.config['trail_distance_ticks'],
            },
            'breakeven_config': {
                'trigger_ticks': self.config['breakeven_trigger_ticks'],
                'buffer_ticks': self.config['breakeven_buffer_ticks'],
            }
        }
    
    # ========================================================================
    # GESTION DES TRADES
    # ========================================================================
    
    def register_trade_result(self, result: str, pnl: float):
        """Enregistre résultat d'un trade."""
        self.daily_stats['trades'] += 1
        self.daily_stats['pnl'] += pnl
        
        if result == 'WIN':
            self.daily_stats['wins'] += 1
        elif result == 'LOSS':
            self.daily_stats['losses'] += 1
        
        win_rate = self.daily_stats['wins'] / self.daily_stats['trades'] * 100 if self.daily_stats['trades'] > 0 else 0
        
        logger.info(f"📊 ES Stats: {self.daily_stats['trades']} trades | "
                   f"WR: {win_rate:.0f}% | P&L: ${self.daily_stats['pnl']:.0f}")
    
    def get_daily_summary(self) -> Dict:
        """Retourne résumé journalier."""
        trades = self.daily_stats['trades']
        return {
            'date': str(self.daily_stats['date']),
            'trades': trades,
            'wins': self.daily_stats['wins'],
            'losses': self.daily_stats['losses'],
            'win_rate': self.daily_stats['wins'] / trades * 100 if trades > 0 else 0,
            'pnl': self.daily_stats['pnl'],
            'broken_levels_tracked': len(self.broken_levels)
        }


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(message)s'
    )
    
    # Snapshot ES de test
    test_tick = {
        "t_ms": 1763609127106,
        "sym": "ESZ25_FUT_CME",
        "mid": 6047.50,
        "spread": 0.25,
        "best_bid": 6047.25,
        "best_ask": 6047.75,
        
        # Options (LEADER)
        "hvl": 6045.00,
        "call_resistance": 6100.00,
        "put_support": 6000.00,
        "gex_1": 6050.00,
        "gex_2": 6025.00,
        "gex_3": 6075.00,
        
        # VWAP + Deviations
        "vwap": 6040.00,
        "vwap_up1": 6055.00,
        "vwap_dn1": 6025.00,
        "vwap_up2": 6070.00,
        "vwap_dn2": 6010.00,
        "vwap_weekly": 6030.00,
        "pvwap": 6035.00,
        
        # Session levels
        "vva": {"vah": 6060.00, "val": 6020.00, "vpoc": 6045.00},
        "ibh": 6055.00,
        "ibl": 6030.00,
        "onh": 6050.00,
        "onl": 6025.00,
        
        # 1D Expected Move
        "1d_max": 6080.00,
        "1d_min": 6010.00,
        
        # Blind spots
        "blind_spot_0": 6042.00,
        "blind_spot_1": 6058.00,
        
        # OrderFlow (VALIDATEUR)
        "delta": 150,
        "deltaPct": 0.25,
        "depth_imbalance": 0.15,
        "smart_money_flow": 0.08,
        
        # Context
        "atr": 1.20,
        "vix": 16.50,
    }
    
    print("\n" + "="*80)
    print("🧪 TEST ES PURE MENTHORQ V2")
    print("="*80)
    
    strategy = ESPureMenthorQV2()
    
    # Extraire niveaux
    levels = strategy._extract_levels(test_tick)
    print(f"\n📊 {len(levels)} niveaux extraits:")
    for i, lvl in enumerate(levels[:10]):
        print(f"   {i+1}. {lvl}")
    
    # Vérifier proximité niveau
    is_near, nearest = strategy._is_near_level(test_tick, levels)
    print(f"\n📍 Près d'un niveau? {is_near}")
    if nearest:
        print(f"   Niveau proche: {nearest}")
    
    # Régime gamma
    gamma = strategy._get_gamma_regime(test_tick)
    print(f"\n🔮 Régime Gamma: {gamma.value}")
    
    # Générer signal
    print("\n" + "-"*40)
    signal = strategy.generate_signal(test_tick)
    
    if signal:
        print(f"\n✅ SIGNAL GÉNÉRÉ:")
        for k, v in signal.items():
            print(f"   {k}: {v}")
    else:
        print("\n❌ Aucun signal généré")
    
    print("\n" + "="*80)
