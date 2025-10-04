"""
MIA_IA_SYSTEM - MenthorQ Elite Implementation
Version: 1.0 Elite - Production Ready

Implémentation réelle de la méthode MenthorQ Elite avec :
- 5 composants essentiels (Gamma, Blind Spots, Dealers Bias, VWAP, VIX)
- Kernel lisse calibré (pas de paliers)
- Tick size généralisé par symbole
- Gates de fraîcheur et QC
- Directional scoring

Performance: <50ms, intégration temps réel
"""

import math
import numpy as np
from typing import Dict, Any, Tuple, Optional
from dataclasses import dataclass
from core.performance_profiler import profile_function, profile_method
from datetime import datetime
from core.logger import get_logger

logger = get_logger(__name__)

# === CONFIGURATION MENTHORQ ELITE ===

# Configuration tick_size par symbole (cohérent avec Battle Navale)
TICK_SIZE_CONFIG = {
    'ES': 0.25,    # E-mini S&P 500
    'NQ': 0.25,    # E-mini NASDAQ
    'YM': 1.0,     # E-mini Dow
    'RTY': 0.1,    # E-mini Russell
    'GC': 0.1,     # Gold
    'CL': 0.01     # Crude Oil
}

# Configuration des paramètres λ calibrés pour MenthorQ (AMÉLIORÉS)
MENTHORQ_LAMBDA_CONFIG = {
    'ES_gamma': 8.0,    # Plus large pour scores plus élevés
    'ES_blind': 6.0,    # Plus large pour scores plus élevés
    'NQ_gamma': 8.0,    # Plus large pour scores plus élevés
    'NQ_blind': 6.0,    # Plus large pour scores plus élevés
    'YM_gamma': 8.0,    # Plus large pour scores plus élevés
    'YM_blind': 6.0     # Plus large pour scores plus élevés
}

# === DATACLASSES ===

@dataclass
class MenthorQEliteResult:
    """Résultat MenthorQ Elite complet"""
    menthorq_score: float
    raw_score: float
    vix_multiplier: float
    gamma_levels: Dict[str, Any]
    blind_spots: Dict[str, Any]
    dealers_bias: Dict[str, Any]
    vwap_confluence: Dict[str, Any]
    vix_regime: Dict[str, Any]
    is_signal: bool
    signal_strength: str
    risk_multiplier: float
    patience_minutes: int
    calculation_time_ms: float
    timestamp: datetime

# === UTILITAIRES ===

def proximity_kernel(price: float, level: float, tick_size: float, lambda_ticks: float) -> float:
    """
    Fonction utilitaire : kernel de proximité lisse
    """
    if level <= 0:
        return 0.0
    
    distance_ticks = abs(price - level) / tick_size
    return math.exp(-distance_ticks / lambda_ticks)

def clamp(x: float, lo: float, hi: float) -> float:
    """Clamp une valeur entre lo et hi"""
    return max(lo, min(hi, x))

def bucketize(value: float) -> float:
    """Fonction utilitaire de bucketisation"""
    return min(1.0, max(0.0, value))

# === CLASSE PRINCIPALE MENTHORQ ELITE ===

class MenthorQElite:
    """
    MenthorQ Elite - Implémentation réelle
    
    Composants essentiels :
    1. Gamma Levels (35%) - Kernel lisse calibré
    2. Blind Spots (25%) - Avec direction
    3. Dealers Bias (15%) - Pondéré
    4. VWAP Confluence (15%) - QC-aware
    5. VIX Regime (10%) - Adaptatif
    """
    
    def __init__(self):
        """Initialisation MenthorQ Elite"""
        self.tick_size_config = TICK_SIZE_CONFIG
        # Charger λ calibrés si disponibles (loader robuste JSON + JSONL)
        try:
            import json, re
            from pathlib import Path
            cfg_path = Path('config/lambda_calibrated.json')
            if cfg_path.exists():
                raw = cfg_path.read_text(encoding='utf-8-sig', errors='ignore')
                
                # Nettoyer le JSON (commentaires, trailing commas)
                raw = re.sub(r'//.*', '', raw)  # Supprimer commentaires //
                raw = re.sub(r'/\*.*?\*/', '', raw, flags=re.S)  # Supprimer commentaires /* */
                raw = re.sub(r',(\s*[}\]])', r'\1', raw)  # Supprimer trailing commas
                
                calibrated = {}
                try:
                    # Essayer JSON standard
                    calibrated = json.loads(raw)
                except json.JSONDecodeError:
                    # Fallback JSONL: lire ligne par ligne
                    logger.info("🔄 MenthorQ: Fallback JSONL parsing...")
                    for line in raw.split('\n'):
                        line = line.strip()
                        if line and not line.startswith('//'):
                            try:
                                line_data = json.loads(line)
                                calibrated.update(line_data)
                            except json.JSONDecodeError:
                                continue
                
                # Valider et appliquer les defaults
                calibrated = self._validate_lambda_config(calibrated)
                self.lambda_config = {**MENTHORQ_LAMBDA_CONFIG, **calibrated}
                
                esg = self.lambda_config.get('ES_gamma'); esb = self.lambda_config.get('ES_blind')
                nqg = self.lambda_config.get('NQ_gamma'); nqb = self.lambda_config.get('NQ_blind')
                logger.info(f"🧠 MenthorQ Elite: λ chargés ES(g={esg}, b={esb}) NQ(g={nqg}, b={nqb})")
            else:
                self.lambda_config = MENTHORQ_LAMBDA_CONFIG
        except Exception as e:
            logger.warning(f"⚠️ MenthorQ Elite: échec chargement λ calibrés: {e}")
            self.lambda_config = MENTHORQ_LAMBDA_CONFIG
        logger.info("🧠 MenthorQ Elite initialisé - 5 composants essentiels")
    
    def _validate_lambda_config(self, config: dict) -> dict:
        """Valide et nettoie la configuration λ"""
        validated = {}
        for key, value in config.items():
            if isinstance(value, (int, float)) and 0.1 <= value <= 20.0:
                validated[key] = float(value)
            else:
                logger.warning(f"⚠️ MenthorQ: λ invalide {key}={value} → ignoré")
        return validated
    
    def calculate_menthorq_elite(self, menthorq_data: Dict[str, Any], current_price: float, 
                                symbol: str, intended_direction: int, qc: Dict[str, Any]) -> MenthorQEliteResult:
        """
        MenthorQ ELITE - Score final avec gates de fraîcheur
        
        Args:
            menthorq_data: Données MenthorQ (gamma, blind_spots, dealers_bias, vwap, vix)
            current_price: Prix actuel
            symbol: Symbole (ES, NQ, YM, etc.)
            intended_direction: Direction voulue (1=Long, -1=Short)
            qc: Contexte qualité (options_snapshot_age_min, vwap_qc_p95, etc.)
        
        Returns:
            MenthorQEliteResult complet
        """
        start_time = datetime.now()
        
        try:
            # === GATE FRAÎCHEUR OPTIONS ===
            if qc.get('options_snapshot_age_min', 999) > 5:
                logger.warning(f"🚫 Gate options stale: {qc.get('options_snapshot_age_min', 999)}min")
                return MenthorQEliteResult(
                    menthorq_score=0.0, raw_score=0.0, vix_multiplier=1.0,
                    gamma_levels={}, blind_spots={}, dealers_bias={}, 
                    vwap_confluence={}, vix_regime={}, is_signal=False,
                    signal_strength='STALE', risk_multiplier=1.0, patience_minutes=0,
                    calculation_time_ms=0.0, timestamp=start_time
                )
            
            # === COMPOSANTS INDIVIDUELS ===
            gamma_levels = self._calculate_gamma_levels_score(
                menthorq_data.get('gamma', {}), current_price, symbol
            )
            blind_spots = self._calculate_blind_spots_score(
                menthorq_data.get('blind_spots', {}), current_price, symbol, intended_direction
            )
            dealers_bias = self._calculate_dealers_bias_score(
                menthorq_data.get('dealers_bias', {}), intended_direction
            )
            vwap_confluence = self._calculate_vwap_confluence_score(
                menthorq_data.get('vwap', {}), current_price, symbol, qc
            )
            vix_regime = self._calculate_vix_regime_score(
                menthorq_data.get('vix', {})
            )
            
            # === SCORE FINAL PONDÉRÉ (VIX = multiplicateur uniquement) ===
            menthorq_score = (
                gamma_levels['gamma_score'] * 0.35 +
                blind_spots['blind_score'] * 0.25 +
                dealers_bias['dealers_score'] * 0.15 +
                vwap_confluence['vwap_score'] * 0.25  # Monté à 25% pour compenser VIX
            )
            
            # ✅ BONUS FLIP ZONE - quand price s'approche des murs avec VWAP slope favorable
            flip_bonus = self._calculate_flip_zone_bonus(
                menthorq_data.get('gamma', {}), 
                menthorq_data.get('vwap', {}), 
                current_price, symbol
            )
            menthorq_score = min(1.0, menthorq_score + flip_bonus)
            
            # === APPLICATION DU MULTIPLICATEUR VIX ===
            vix_multiplier = vix_regime['regime_analysis']['multiplier']
            final_score = menthorq_score * vix_multiplier
            
            # === CALCUL TEMPS ===
            calc_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return MenthorQEliteResult(
                menthorq_score=final_score,
                raw_score=menthorq_score,
                vix_multiplier=vix_multiplier,
                gamma_levels=gamma_levels,
                blind_spots=blind_spots,
                dealers_bias=dealers_bias,
                vwap_confluence=vwap_confluence,
                vix_regime=vix_regime,
                is_signal=final_score >= 0.70,
                signal_strength='STRONG' if final_score >= 0.85 else 'MEDIUM' if final_score >= 0.70 else 'WEAK',
                risk_multiplier=vix_regime['regime_analysis']['risk_multiplier'],
                patience_minutes=vix_regime['regime_analysis']['patience_minutes'],
                calculation_time_ms=calc_time,
                timestamp=start_time
            )
            
        except Exception as e:
            logger.error(f"❌ Erreur MenthorQ Elite: {e}")
            return MenthorQEliteResult(
                menthorq_score=0.0, raw_score=0.0, vix_multiplier=1.0,
                gamma_levels={}, blind_spots={}, dealers_bias={}, 
                vwap_confluence={}, vix_regime={}, is_signal=False,
                signal_strength='ERROR', risk_multiplier=1.0, patience_minutes=0,
                calculation_time_ms=0.0, timestamp=start_time
            )
    
    # === COMPOSANT 1 : GAMMA LEVELS (35%) ===
    
    def _calculate_gamma_levels_score(self, gamma_data: Dict[str, Any], current_price: float, symbol: str) -> Dict[str, Any]:
        """Score des niveaux gamma avec kernel lisse calibré"""
        gamma_scores = {
            'gamma_max': self._analyze_gamma_maximum(gamma_data, current_price, symbol),
            'call_wall': self._analyze_call_wall(gamma_data, current_price, symbol),
            'put_wall': self._analyze_put_wall(gamma_data, current_price, symbol),
            'zero_gamma': self._analyze_zero_gamma(gamma_data, current_price, symbol),
            'gamma_flip': self._analyze_gamma_flip(gamma_data, current_price, symbol)
        }
        
        # Score pondéré
        gamma_score = (
            gamma_scores['gamma_max'] * 0.30 +
            gamma_scores['call_wall'] * 0.25 +
            gamma_scores['put_wall'] * 0.25 +
            gamma_scores['zero_gamma'] * 0.15 +
            gamma_scores['gamma_flip'] * 0.05
        )
        
        # Exploitation des champs retournés
        strongest_level = max(gamma_scores.items(), key=lambda x: x[1])
        level_count = sum(1 for score in gamma_scores.values() if score > 0.5)
        
        # Bonus confluence si ≥2 niveaux >0.7
        confluence_bonus = 0.0
        if level_count >= 2:
            confluence_bonus = min(0.05, level_count * 0.02)
        
        gamma_score = min(1.0, gamma_score + confluence_bonus)
        
        return {
            'gamma_score': gamma_score,
            'gamma_scores': gamma_scores,
            'strongest_level': strongest_level,
            'level_count': level_count,
            'confluence_bonus': confluence_bonus
        }
    
    def _calculate_flip_zone_bonus(self, gamma_data: Dict[str, Any], vwap_data: Dict[str, Any], 
                                  current_price: float, symbol: str) -> float:
        """
        Bonus flip zone - quand price s'approche des murs avec VWAP slope favorable
        
        Args:
            gamma_data: Données gamma (zero_gamma, call_wall, put_wall)
            vwap_data: Données VWAP (slope)
            current_price: Prix actuel
            symbol: Symbole
            
        Returns:
            Bonus score (0.0 à 0.3)
        """
        try:
            zero_gamma = gamma_data.get('zero_gamma', 0)
            call_wall = gamma_data.get('call_wall', 0)
            put_wall = gamma_data.get('put_wall', 0)
            vwap_slope = vwap_data.get('slope', 0)
            
            if not all([zero_gamma, call_wall, put_wall]):
                return 0.0
            
            # Normalisation simple autour de ZG et murs
            rng = max(call_wall - put_wall, 1e-6)
            pos = (current_price - zero_gamma) / rng  # -0.5..+0.5 environ
            
            # Bonus si on s'éloigne de ZG vers les murs
            distance_bonus = min(1.0, abs(pos) * 2.0)  # 0 à 1 selon distance de ZG
            
            # Bonus VWAP slope favorable (positif = bullish)
            slope_bonus = 1.0 if vwap_slope >= 0 else 0.5
            
            # Bonus final (max 0.3)
            flip_bonus = distance_bonus * slope_bonus * 0.3
            
            logger.debug(f"🎯 Flip bonus: pos={pos:.3f}, distance={distance_bonus:.3f}, slope={slope_bonus:.3f}, bonus={flip_bonus:.3f}")
            
            return flip_bonus
            
        except Exception as e:
            logger.error(f"❌ Erreur calcul flip bonus: {e}")
            return 0.0
    
    def _analyze_gamma_maximum(self, gamma_data: Dict[str, Any], current_price: float, symbol: str) -> float:
        """Analyse du niveau de gamma maximum avec kernel lisse"""
        gamma_max = gamma_data.get('gamma_max', 0)
        if gamma_max > 0:
            tick_size = self.tick_size_config.get(symbol, 0.25)
            lambda_gamma = self.lambda_config.get(f'{symbol}_gamma', 6.0)
            return proximity_kernel(current_price, gamma_max, tick_size, lambda_gamma)
        return 0.0
    
    def _analyze_call_wall(self, gamma_data: Dict[str, Any], current_price: float, symbol: str) -> float:
        """Analyse du mur de calls (résistance) avec kernel lisse et direction"""
        call_wall = gamma_data.get('call_wall', 0)
        if call_wall > 0:
            tick_size = self.tick_size_config.get(symbol, 0.25)
            lambda_gamma = self.lambda_config.get(f'{symbol}_gamma', 6.0)
            
            # Kernel lisse de base
            base_score = proximity_kernel(current_price, call_wall, tick_size, lambda_gamma)
            
            # Bonus directionnel si le prix est en-dessous du call wall (résistance)
            if current_price < call_wall:
                direction_bonus = 0.2  # Bonus pour résistance au-dessus
            else:
                direction_bonus = 0.0
            
            return min(1.0, base_score + direction_bonus)
        return 0.0
    
    def _analyze_put_wall(self, gamma_data: Dict[str, Any], current_price: float, symbol: str) -> float:
        """Analyse du mur de puts (support) avec kernel lisse et direction"""
        put_wall = gamma_data.get('put_wall', 0)
        if put_wall > 0:
            tick_size = self.tick_size_config.get(symbol, 0.25)
            lambda_gamma = self.lambda_config.get(f'{symbol}_gamma', 6.0)
            
            # Kernel lisse de base
            base_score = proximity_kernel(current_price, put_wall, tick_size, lambda_gamma)
            
            # Bonus directionnel si le prix est au-dessus du put wall (support)
            if current_price > put_wall:
                direction_bonus = 0.2  # Bonus pour support en-dessous
            else:
                direction_bonus = 0.0
            
            return min(1.0, base_score + direction_bonus)
        return 0.0
    
    def _analyze_zero_gamma(self, gamma_data: Dict[str, Any], current_price: float, symbol: str) -> float:
        """Analyse de la zone de gamma zéro avec kernel lisse"""
        zero_gamma = gamma_data.get('zero_gamma', 0)
        if zero_gamma > 0:
            tick_size = self.tick_size_config.get(symbol, 0.25)
            lambda_gamma = self.lambda_config.get(f'{symbol}_gamma', 6.0)
            
            # Kernel lisse : zone de gamma zéro = zone de forte volatilité
            volatility_score = proximity_kernel(current_price, zero_gamma, tick_size, lambda_gamma)
            return volatility_score
        return 0.0
    
    def _analyze_gamma_flip(self, gamma_data: Dict[str, Any], current_price: float, symbol: str) -> float:
        """Analyse de l'inversion gamma avec temporalité (âge du flip + TTL)"""
        gamma_flip = gamma_data.get('gamma_flip', False)
        flip_price = gamma_data.get('flip_price', 0)
        flip_age_min = gamma_data.get('flip_age_minutes', 999)  # Âge en minutes
        
        if gamma_flip and flip_price > 0 and flip_age_min <= 5:  # TTL de 5 minutes
            tick_size = self.tick_size_config.get(symbol, 0.25)
            lambda_gamma = self.lambda_config.get(f'{symbol}_gamma', 6.0)
            
            # Kernel lisse avec λ plus serré pour flip
            flip_score = proximity_kernel(current_price, flip_price, tick_size, lambda_gamma * 0.5)
            
            # Limite le boost flip à 0.15-0.20 du sous-score Gamma
            return min(0.20, flip_score)
        else:
            return 0.0  # Flip trop vieux ou inexistant
    
    # === COMPOSANT 2 : BLIND SPOTS (25%) ===
    
    def _calculate_blind_spots_score(self, blind_spots_data: Dict[str, Any], current_price: float, 
                                   symbol: str, intended_direction: int) -> Dict[str, Any]:
        """Score des blind spots avec kernel lisse, direction et cap"""
        blind_scores = {
            'blind_spot_1': self._analyze_blind_spot_principal(blind_spots_data, current_price, symbol, intended_direction),
            'blind_spot_2': self._analyze_blind_spot_secondaire(blind_spots_data, current_price, symbol, intended_direction),
            'liquidity_gap': self._analyze_liquidity_gap(blind_spots_data, current_price, symbol),
            'dead_zone': self._analyze_dead_zone(blind_spots_data, current_price, symbol)
        }
        
        # CAP : prendre la meilleure zone active (éviter sur-signal)
        blind_score = max(blind_scores.values())
        
        return {
            'blind_score': blind_score,
            'blind_scores': blind_scores,
            'strongest_blind_spot': max(blind_scores.items(), key=lambda x: x[1]),
            'blind_spot_count': sum(1 for score in blind_scores.values() if score > 0.3)
        }
    
    def _analyze_blind_spot_principal(self, blind_spots_data: Dict[str, Any], current_price: float, 
                                    symbol: str, intended_direction: int) -> float:
        """Analyse du blind spot principal avec kernel lisse et direction"""
        blind_spot_1 = blind_spots_data.get('blind_spot_1', 0)
        if blind_spot_1 > 0:
            tick_size = self.tick_size_config.get(symbol, 0.25)
            lambda_blind = self.lambda_config.get(f'{symbol}_blind', 3.5)
            
            # Kernel lisse de base
            base_score = proximity_kernel(current_price, blind_spot_1, tick_size, lambda_blind)
            
            # Bonus directionnel selon la direction voulue
            if intended_direction == 1:  # Long
                # Bonus si le prix est en-dessous du blind spot (breakout potentiel vers le haut)
                if current_price < blind_spot_1:
                    direction_bonus = 0.3
                else:
                    direction_bonus = 0.0
            else:  # Short
                # Bonus si le prix est au-dessus du blind spot (breakout potentiel vers le bas)
                if current_price > blind_spot_1:
                    direction_bonus = 0.3
                else:
                    direction_bonus = 0.0
            
            return min(1.0, base_score + direction_bonus)
        return 0.0
    
    def _analyze_blind_spot_secondaire(self, blind_spots_data: Dict[str, Any], current_price: float, 
                                     symbol: str, intended_direction: int) -> float:
        """Analyse du blind spot secondaire avec kernel lisse et direction"""
        blind_spot_2 = blind_spots_data.get('blind_spot_2', 0)
        if blind_spot_2 > 0:
            tick_size = self.tick_size_config.get(symbol, 0.25)
            lambda_blind = self.lambda_config.get(f'{symbol}_blind', 3.5)
            
            # Kernel lisse de base (légèrement plus large)
            base_score = proximity_kernel(current_price, blind_spot_2, tick_size, lambda_blind * 1.2)
            
            # Bonus directionnel (plus faible que le principal)
            if intended_direction == 1:  # Long
                if current_price < blind_spot_2:
                    direction_bonus = 0.2
                else:
                    direction_bonus = 0.0
            else:  # Short
                if current_price > blind_spot_2:
                    direction_bonus = 0.2
                else:
                    direction_bonus = 0.0
            
            return min(1.0, base_score + direction_bonus)
        return 0.0
    
    def _analyze_liquidity_gap(self, blind_spots_data: Dict[str, Any], current_price: float, symbol: str) -> float:
        """Analyse du gap de liquidité avec tick size généralisé"""
        liquidity_gap = blind_spots_data.get('liquidity_gap', 0)
        if liquidity_gap > 0:
            tick_size = self.tick_size_config.get(symbol, 0.25)
            distance_ticks = abs(current_price - liquidity_gap) / tick_size
            
            # Gap de liquidité = zone de forte volatilité
            if distance_ticks <= 1:
                return 1.0  # Dans le gap
            elif distance_ticks <= 3:
                return 0.7  # Proche du gap
            elif distance_ticks <= 8:
                return 0.4  # Moyennement proche
            else:
                return 0.0
        return 0.0
    
    def _analyze_dead_zone(self, blind_spots_data: Dict[str, Any], current_price: float, symbol: str) -> float:
        """Analyse de la zone morte avec tick size généralisé"""
        dead_zone = blind_spots_data.get('dead_zone', 0)
        if dead_zone > 0:
            tick_size = self.tick_size_config.get(symbol, 0.25)
            distance_ticks = abs(current_price - dead_zone) / tick_size
            
            # Zone morte = zone de faible activité
            if distance_ticks <= 2:
                return 0.6  # Dans la zone morte
            elif distance_ticks <= 5:
                return 0.3  # Proche de la zone morte
            else:
                return 0.0
        return 0.0
    
    # === COMPOSANT 3 : DEALERS BIAS (15%) ===
    
    def _calculate_dealers_bias_score(self, dealers_data: Dict[str, Any], intended_direction: int) -> Dict[str, Any]:
        """Score final du biais des dealers avec gate dur sur alignement"""
        dir_sc = self._analyze_directional_bias(dealers_data, intended_direction)  # 0–1
        str_sc = self._analyze_bias_strength(dealers_data)                         # 0–1
        conf_sc = self._analyze_bias_confidence(dealers_data)                      # 0–1
        aligned = 1.0 if dir_sc > 0 else 0.0
        
        # Gate dur : ≈0 si pas aligné
        base = 0.5 * dir_sc + 0.3 * str_sc + 0.2 * conf_sc
        dealers_score = base * (0.25 + 0.75 * aligned)
        
        return {
            'dealers_score': dealers_score,
            'bias_scores': {
                'directional_bias': dir_sc,
                'bias_strength': str_sc,
                'bias_confidence': conf_sc
            },
            'bias_direction': 'BULLISH' if dealers_data.get('bias_score', 0) > 0 else 'BEARISH' if dealers_data.get('bias_score', 0) < 0 else 'NEUTRAL',
            'aligned': bool(aligned)  # Indique si aligné avec direction
        }
    
    def _analyze_directional_bias(self, dealers_data: Dict[str, Any], intended_direction: int) -> float:
        """Analyse du biais directionnel des dealers avec alignement"""
        bias_score = dealers_data.get('bias_score', 0)  # -1.0 à +1.0
        
        # Vérification alignement avec direction voulue
        if intended_direction == 1:  # Long
            # Bonus seulement si biais bullish
            if bias_score > 0:
                return min(1.0, bias_score)
            else:
                return 0.0  # Pas de bonus si biais opposé
        else:  # Short
            # Bonus seulement si biais bearish
            if bias_score < 0:
                return min(1.0, abs(bias_score))
            else:
                return 0.0  # Pas de bonus si biais opposé
    
    def _analyze_bias_strength(self, dealers_data: Dict[str, Any]) -> float:
        """Analyse de la force du biais (bucketizé)"""
        bias_strength = dealers_data.get('bias_strength', 0)
        
        # Bucketisation simple
        if bias_strength >= 0.8:
            return 1.0  # Biais très fort
        elif bias_strength >= 0.6:
            return 0.8  # Biais fort
        elif bias_strength >= 0.4:
            return 0.6  # Biais moyen
        elif bias_strength >= 0.2:
            return 0.4  # Biais faible
        else:
            return 0.0
    
    def _analyze_bias_confidence(self, dealers_data: Dict[str, Any]) -> float:
        """Analyse de la confiance du biais (bucketizé)"""
        bias_confidence = dealers_data.get('bias_confidence', 0)
        
        # Bucketisation simple
        if bias_confidence >= 0.9:
            return 1.0  # Très confiant
        elif bias_confidence >= 0.7:
            return 0.8  # Confiant
        elif bias_confidence >= 0.5:
            return 0.6  # Moyennement confiant
        elif bias_confidence >= 0.3:
            return 0.4  # Peu confiant
        else:
            return 0.0
    
    # === COMPOSANT 4 : VWAP CONFLUENCE (15%) ===
    
    def _calculate_vwap_confluence_score(self, vwap_data: Dict[str, Any], current_price: float, 
                                       symbol: str, qc: Dict[str, Any]) -> Dict[str, Any]:
        """Score final de confluence VWAP avec QC penalty"""
        vwap_scores = {
            'vwap_distance': self._analyze_vwap_distance(vwap_data, current_price, symbol),
            'vwap_bands': self._analyze_vwap_bands(vwap_data, current_price),
            'vwap_slope': self._analyze_vwap_slope(vwap_data, qc.get('atr_per_bar', 1.0), symbol)
        }
        
        # Score pondéré
        vwap_score = (
            vwap_scores['vwap_distance'] * 0.50 +
            vwap_scores['vwap_bands'] * 0.30 +
            vwap_scores['vwap_slope'] * 0.20
        )
        
        # QC penalty si VWAP study vs derived diverge
        if qc.get('vwap_qc_p95', 0.0) > 0.20:
            vwap_score *= 0.8
        
        return {
            'vwap_score': vwap_score,
            'vwap_scores': vwap_scores,
            'vwap_position': 'ABOVE' if current_price > vwap_data.get('vwap', 0) else 'BELOW' if current_price < vwap_data.get('vwap', 0) else 'AT'
        }
    
    def _analyze_vwap_distance(self, vwap_data: Dict[str, Any], current_price: float, symbol: str) -> float:
        """Analyse de la distance au VWAP avec kernel lisse"""
        vwap_price = vwap_data.get('vwap', 0)
        if vwap_price > 0:
            tick_size = self.tick_size_config.get(symbol, 0.25)
            distance_ticks = abs(current_price - vwap_price) / tick_size
            
            # Kernel lisse plutôt que paliers
            lambda_vwap = 3.0
            return math.exp(-distance_ticks / lambda_vwap)
        return 0.0
    
    def _analyze_vwap_bands(self, vwap_data: Dict[str, Any], current_price: float) -> float:
        """Analyse des bandes VWAP"""
        vwap_up1 = vwap_data.get('up1', 0)
        vwap_dn1 = vwap_data.get('dn1', 0)
        
        if vwap_up1 > 0 and vwap_dn1 > 0:
            # Position par rapport aux bandes
            if vwap_dn1 <= current_price <= vwap_up1:
                return 1.0  # Entre les bandes
            elif abs(current_price - vwap_up1) <= 2 or abs(current_price - vwap_dn1) <= 2:
                return 0.7  # Proche des bandes
            else:
                return 0.3  # Loin des bandes
        return 0.0
    
    def _analyze_vwap_slope(self, vwap_data: Dict[str, Any], atr_per_bar: float, symbol: str) -> float:
        """Analyse de la pente VWAP normalisée par ATR"""
        vwap_slope = vwap_data.get('slope', 0.0)
        tick_size = self.tick_size_config.get(symbol, 0.25)
        
        # Normalisation : pente / (ATR_par_bar / tick)
        denom = max(1e-6, atr_per_bar / tick_size)
        normalized_slope = min(1.0, abs(vwap_slope) / denom)
        
        return normalized_slope
    
    # === COMPOSANT 5 : VIX REGIME (10%) ===
    
    def _calculate_vix_regime_score(self, vix_data: Dict[str, Any]) -> Dict[str, Any]:
        """Score final du régime VIX"""
        vix_value = vix_data.get('vix', 20)
        
        # Déterminer le régime
        if vix_value < 15:
            regime_analysis = self._analyze_vix_low_regime(vix_data)
        elif vix_value <= 25:
            regime_analysis = self._analyze_vix_normal_regime(vix_data)
        elif vix_value <= 35:
            regime_analysis = self._analyze_vix_high_regime(vix_data)
        else:
            regime_analysis = self._analyze_vix_extreme_regime(vix_data)
        
        # Score basé sur l'optimalité du régime
        if regime_analysis['regime'] == 'NORMAL':
            vix_score = 1.0  # Régime optimal
        elif regime_analysis['regime'] == 'LOW':
            vix_score = 0.8  # Régime bon
        elif regime_analysis['regime'] == 'HIGH':
            vix_score = 0.6  # Régime difficile
        else:  # EXTREME
            vix_score = 0.3  # Régime très difficile
        
        return {
            'vix_score': vix_score,
            'vix_value': vix_value,
            'regime_analysis': regime_analysis,
            'regime': regime_analysis['regime']
        }
    
    def _analyze_vix_low_regime(self, vix_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyse du régime VIX bas"""
        vix_value = vix_data.get('vix', 20)
        if vix_value < 15:
            return {
                'regime': 'LOW',
                'multiplier': 1.2,  # Bonus pour les signaux
                'risk_multiplier': 0.8,  # Réduction du risque
                'patience_minutes': 15  # Patience réduite
            }
        return {}
    
    def _analyze_vix_normal_regime(self, vix_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyse du régime VIX normal"""
        vix_value = vix_data.get('vix', 20)
        if 15 <= vix_value <= 25:
            return {
                'regime': 'NORMAL',
                'multiplier': 1.0,  # Multiplicateur neutre
                'risk_multiplier': 1.0,  # Risque normal
                'patience_minutes': 20  # Patience normale
            }
        return {}
    
    def _analyze_vix_high_regime(self, vix_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyse du régime VIX élevé"""
        vix_value = vix_data.get('vix', 20)
        if 25 < vix_value <= 35:
            return {
                'regime': 'HIGH',
                'multiplier': 0.8,  # Réduction des signaux
                'risk_multiplier': 1.2,  # Augmentation du risque
                'patience_minutes': 25  # Patience accrue
            }
        return {}
    
    def _analyze_vix_extreme_regime(self, vix_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyse du régime VIX extrême"""
        vix_value = vix_data.get('vix', 20)
        if vix_value > 35:
            return {
                'regime': 'EXTREME',
                'multiplier': 0.6,  # Forte réduction des signaux
                'risk_multiplier': 1.5,  # Forte augmentation du risque
                'patience_minutes': 30  # Patience maximale
            }
        return {}
