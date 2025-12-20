# 🎯 DOM PRESSURE ANALYSIS - VERSION PRO
# ═══════════════════════════════════════════════════════════════
# Analyse avancée de la pression DOM avec:
# - Double vue: Instantané + Lissé
# - Détection des GROSSES MAINS
# - Seuils dynamiques
# - Score pondéré intelligent
#
# Version: 1.0 (10/12/2025)
# Author: MIA System + Claude

"""
PHILOSOPHIE:

1. INSTANTANÉ = Ce qui se passe MAINTENANT (bruit + signal)
2. LISSÉ = La tendance RÉELLE sur les dernières minutes
3. GROSSES MAINS = Les mouvements qui COMPTENT (institutionnels)

Le trader doit voir:
- Qui a la main EN CE MOMENT (instantané)
- Qui a la main SUR LA TENDANCE (lissé)
- Si une GROSSE MAIN vient d'intervenir (alerte)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from collections import deque
from datetime import datetime
import math

# ═══════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════

@dataclass
class DOMPressureConfig:
    """Configuration pour l'analyse DOM"""
    
    # Lissage EMA
    ema_period: int = 10  # Nombre de snapshots pour le lissage
    
    # Seuils de base (seront ajustés dynamiquement)
    base_delta_threshold: float = 0.15  # 15% delta = significatif
    base_imbalance_threshold: float = 0.20  # 20% imbalance = significatif
    base_depth_ratio: float = 1.2  # 20% de différence de depth
    
    # Grosses mains
    delta_burst_threshold: int = 50  # Delta burst > 50 = grosse main
    stacked_imbalance_threshold: int = 2  # 2+ rows stacked = grosse main
    cum_delta_spike_threshold: int = 500  # Spike de 500 sur cum_delta
    
    # Pondérations pour le score
    weights: Dict[str, float] = field(default_factory=lambda: {
        'delta_pct': 0.25,        # OrderFlow delta
        'depth_imbalance': 0.20,  # Profondeur du carnet
        'imbalance_1_3': 0.15,    # Déséquilibre proche
        'smart_money': 0.20,      # Flux smart money
        'stacked': 0.10,          # Imbalances empilées
        'institutional': 0.10,    # Pression institutionnelle
    })


# ═══════════════════════════════════════════════════════════════
# STRUCTURES DE DONNÉES
# ═══════════════════════════════════════════════════════════════

@dataclass
class DOMReading:
    """Une lecture DOM à un instant T"""
    timestamp: int
    
    # Volumes
    ask_pct: float
    bid_pct: float
    delta_pct: float
    
    # Depth
    depth_bid: int
    depth_ask: int
    
    # Imbalances
    imbalance_1_3: float
    imbalance_6_10: float
    
    # Smart Money
    smart_money_flow: float
    institutional_pressure: float
    
    # Grosses mains
    delta_burst: int
    stacked_bid_rows: int
    stacked_ask_rows: int
    cum_delta: int
    
    # Carnet
    ob_center: float
    top_heavy: float


@dataclass
class DOMPressureResult:
    """Résultat de l'analyse DOM"""
    
    # Instantané
    instant_side: str  # 'BUYERS', 'SELLERS', 'NEUTRAL'
    instant_score: float  # -1 (full sellers) à +1 (full buyers)
    instant_strength: int  # 1-5
    
    # Lissé (EMA)
    smoothed_side: str
    smoothed_score: float
    smoothed_strength: int
    
    # Grosses mains
    big_hand_detected: bool
    big_hand_side: Optional[str]  # 'BUY' ou 'SELL'
    big_hand_type: Optional[str]  # 'DELTA_BURST', 'STACKED', 'CUM_SPIKE'
    big_hand_size: Optional[int]
    
    # Divergence
    divergence: bool  # instant ≠ smoothed
    divergence_type: Optional[str]  # 'REVERSAL_UP', 'REVERSAL_DOWN'
    
    # Détails
    factors: Dict[str, Tuple[str, float]]  # facteur -> (side, contribution)
    
    # Conseils
    conseil: str
    

# ═══════════════════════════════════════════════════════════════
# ANALYSEUR DOM
# ═══════════════════════════════════════════════════════════════

class DOMPressureAnalyzer:
    """
    Analyseur de pression DOM avec lissage et détection grosses mains
    """
    
    def __init__(self, config: Optional[DOMPressureConfig] = None):
        self.config = config or DOMPressureConfig()
        
        # Historique pour le lissage (deque = FIFO automatique)
        self.history: deque[DOMReading] = deque(maxlen=self.config.ema_period * 2)
        
        # EMA scores
        self.ema_score: float = 0.0
        self.ema_alpha: float = 2 / (self.config.ema_period + 1)
        
        # Tracking grosses mains
        self.last_cum_delta: int = 0
        self.big_hand_cooldown: int = 0  # Éviter spam d'alertes
    
    def extract_reading(self, snapshot: Dict) -> DOMReading:
        """Extrait une lecture DOM du snapshot"""
        dom_features = snapshot.get('dom_features', {})
        
        return DOMReading(
            timestamp=snapshot.get('t_ms', 0),
            
            # Volumes
            ask_pct=snapshot.get('askPct', 0.5),
            bid_pct=snapshot.get('bidPct', 0.5),
            delta_pct=snapshot.get('deltaPct', 0),
            
            # Depth
            depth_bid=dom_features.get('depth_bid', 0),
            depth_ask=dom_features.get('depth_ask', 0),
            
            # Imbalances
            imbalance_1_3=dom_features.get('imbalance_1_3', 0),
            imbalance_6_10=dom_features.get('imbalance_6_10', 0),
            
            # Smart Money
            smart_money_flow=snapshot.get('smart_money_flow', 0),
            institutional_pressure=snapshot.get('institutional_pressure', 0),
            
            # Grosses mains
            delta_burst=snapshot.get('delta_burst', 0),
            stacked_bid_rows=snapshot.get('stacked_imbalance_bid_rows', 0),
            stacked_ask_rows=snapshot.get('stacked_imbalance_ask_rows', 0),
            cum_delta=snapshot.get('cum_delta_session', 0),
            
            # Carnet
            ob_center=snapshot.get('ob_center', 0),
            top_heavy=snapshot.get('top_heavy', 0),
        )
    
    def calculate_instant_score(self, reading: DOMReading, atr_ratio: float = 1.0) -> Tuple[float, Dict]:
        """
        Calcule le score instantané avec seuils dynamiques
        
        Returns:
            score: -1 (sellers) à +1 (buyers)
            factors: détail de chaque facteur
        """
        factors = {}
        score = 0.0
        
        # Ajuster les seuils selon la volatilité
        vol_mult = max(0.5, min(2.0, 1 / math.sqrt(atr_ratio / 10)))
        
        delta_thresh = self.config.base_delta_threshold * vol_mult
        imb_thresh = self.config.base_imbalance_threshold * vol_mult
        
        # 1. Delta % (25%)
        w = self.config.weights['delta_pct']
        if reading.delta_pct > delta_thresh:
            contribution = min(reading.delta_pct / 0.3, 1.0) * w
            score += contribution
            factors['delta_pct'] = ('BUYERS', contribution)
        elif reading.delta_pct < -delta_thresh:
            contribution = min(abs(reading.delta_pct) / 0.3, 1.0) * w
            score -= contribution
            factors['delta_pct'] = ('SELLERS', -contribution)
        else:
            factors['delta_pct'] = ('NEUTRAL', 0)
        
        # 2. Depth Imbalance (20%)
        w = self.config.weights['depth_imbalance']
        if reading.depth_bid > 0 and reading.depth_ask > 0:
            depth_ratio = reading.depth_bid / reading.depth_ask
            if depth_ratio > self.config.base_depth_ratio:
                contribution = min((depth_ratio - 1) / 0.5, 1.0) * w
                score += contribution
                factors['depth'] = ('BUYERS', contribution)
            elif depth_ratio < 1 / self.config.base_depth_ratio:
                contribution = min((1/depth_ratio - 1) / 0.5, 1.0) * w
                score -= contribution
                factors['depth'] = ('SELLERS', -contribution)
            else:
                factors['depth'] = ('NEUTRAL', 0)
        else:
            factors['depth'] = ('NEUTRAL', 0)
        
        # 3. Imbalance proche 1-3 (15%)
        w = self.config.weights['imbalance_1_3']
        if reading.imbalance_1_3 > imb_thresh:
            contribution = min(reading.imbalance_1_3 / 0.4, 1.0) * w
            score += contribution
            factors['imbalance_1_3'] = ('BUYERS', contribution)
        elif reading.imbalance_1_3 < -imb_thresh:
            contribution = min(abs(reading.imbalance_1_3) / 0.4, 1.0) * w
            score -= contribution
            factors['imbalance_1_3'] = ('SELLERS', -contribution)
        else:
            factors['imbalance_1_3'] = ('NEUTRAL', 0)
        
        # 4. Smart Money (20%)
        w = self.config.weights['smart_money']
        if reading.smart_money_flow > 0.15:
            contribution = min(reading.smart_money_flow / 0.5, 1.0) * w
            score += contribution
            factors['smart_money'] = ('BUYERS', contribution)
        elif reading.smart_money_flow < -0.15:
            contribution = min(abs(reading.smart_money_flow) / 0.5, 1.0) * w
            score -= contribution
            factors['smart_money'] = ('SELLERS', -contribution)
        else:
            factors['smart_money'] = ('NEUTRAL', 0)
        
        # 5. Stacked Imbalances (10%)
        w = self.config.weights['stacked']
        if reading.stacked_bid_rows >= 2:
            contribution = min(reading.stacked_bid_rows / 4, 1.0) * w
            score += contribution
            factors['stacked'] = ('BUYERS', contribution)
        elif reading.stacked_ask_rows >= 2:
            contribution = min(reading.stacked_ask_rows / 4, 1.0) * w
            score -= contribution
            factors['stacked'] = ('SELLERS', -contribution)
        else:
            factors['stacked'] = ('NEUTRAL', 0)
        
        # 6. Institutional Pressure (10%)
        w = self.config.weights['institutional']
        if reading.institutional_pressure > 0.15:
            contribution = min(reading.institutional_pressure / 0.5, 1.0) * w
            score += contribution
            factors['institutional'] = ('BUYERS', contribution)
        elif reading.institutional_pressure < -0.15:
            contribution = min(abs(reading.institutional_pressure) / 0.5, 1.0) * w
            score -= contribution
            factors['institutional'] = ('SELLERS', -contribution)
        else:
            factors['institutional'] = ('NEUTRAL', 0)
        
        return score, factors
    
    def detect_big_hand(self, reading: DOMReading) -> Tuple[bool, Optional[str], Optional[str], Optional[int]]:
        """
        Détecte si une GROSSE MAIN vient d'intervenir
        
        Returns:
            detected: bool
            side: 'BUY' ou 'SELL'
            type: 'DELTA_BURST', 'STACKED', 'CUM_SPIKE'
            size: magnitude
        """
        # Cooldown pour éviter spam
        if self.big_hand_cooldown > 0:
            self.big_hand_cooldown -= 1
            return False, None, None, None
        
        # 1. Delta Burst
        if reading.delta_burst >= self.config.delta_burst_threshold:
            self.big_hand_cooldown = 5  # 5 ticks de cooldown
            # Le signe du delta indique la direction
            side = 'BUY' if reading.delta_pct > 0 else 'SELL'
            return True, side, 'DELTA_BURST', reading.delta_burst
        
        # 2. Stacked Imbalances
        if reading.stacked_bid_rows >= self.config.stacked_imbalance_threshold:
            self.big_hand_cooldown = 5
            return True, 'BUY', 'STACKED_BID', reading.stacked_bid_rows
        
        if reading.stacked_ask_rows >= self.config.stacked_imbalance_threshold:
            self.big_hand_cooldown = 5
            return True, 'SELL', 'STACKED_ASK', reading.stacked_ask_rows
        
        # 3. Cum Delta Spike
        if self.last_cum_delta != 0:
            delta_change = reading.cum_delta - self.last_cum_delta
            if abs(delta_change) >= self.config.cum_delta_spike_threshold:
                self.big_hand_cooldown = 10  # Plus long car plus significatif
                side = 'BUY' if delta_change > 0 else 'SELL'
                return True, side, 'CUM_DELTA_SPIKE', abs(delta_change)
        
        self.last_cum_delta = reading.cum_delta
        return False, None, None, None
    
    def update_ema(self, instant_score: float):
        """Met à jour le score EMA lissé"""
        if self.ema_score == 0:
            self.ema_score = instant_score
        else:
            self.ema_score = self.ema_alpha * instant_score + (1 - self.ema_alpha) * self.ema_score
    
    def score_to_side(self, score: float) -> Tuple[str, int]:
        """Convertit un score en side et strength"""
        if score > 0.15:
            side = 'BUYERS'
            strength = min(5, int(score / 0.15) + 1)
        elif score < -0.15:
            side = 'SELLERS'
            strength = min(5, int(abs(score) / 0.15) + 1)
        else:
            side = 'NEUTRAL'
            strength = 1
        return side, strength
    
    def generate_conseil(self, result: DOMPressureResult) -> str:
        """Génère un conseil basé sur l'analyse"""
        conseils = []
        
        # Grosse main détectée
        if result.big_hand_detected:
            emoji = '🟢' if result.big_hand_side == 'BUY' else '🔴'
            conseils.append(f"🚨 GROSSE MAIN {emoji} {result.big_hand_side} détectée! ({result.big_hand_type}: {result.big_hand_size})")
        
        # Divergence
        if result.divergence:
            if result.divergence_type == 'REVERSAL_UP':
                conseils.append("⚠️ DIVERGENCE: Instantané SELL mais tendance BUY → Possible retournement HAUSSIER")
            else:
                conseils.append("⚠️ DIVERGENCE: Instantané BUY mais tendance SELL → Possible retournement BAISSIER")
        
        # Concordance forte
        if result.instant_side == result.smoothed_side and result.instant_strength >= 3:
            emoji = '🟢' if result.instant_side == 'BUYERS' else '🔴'
            conseils.append(f"✅ CONFIRMATION: {emoji} {result.instant_side} ont la main (Force {result.instant_strength}/5)")
        
        # Neutre
        if result.instant_side == 'NEUTRAL' and result.smoothed_side == 'NEUTRAL':
            conseils.append("⚪ NEUTRE: Pas de pression dominante. Attendre signal clair.")
        
        if not conseils:
            conseils.append(f"📊 {result.instant_side} instantané / {result.smoothed_side} tendance")
        
        return " | ".join(conseils)
    
    def analyze(self, snapshot: Dict) -> DOMPressureResult:
        """
        Analyse complète du DOM
        
        Args:
            snapshot: Snapshot MIA complet
            
        Returns:
            DOMPressureResult avec toutes les infos
        """
        # Extraire la lecture
        reading = self.extract_reading(snapshot)
        self.history.append(reading)
        
        # ATR pour seuils dynamiques
        atr_ratio = snapshot.get('atr_ratio', 1.0)
        
        # Score instantané
        instant_score, factors = self.calculate_instant_score(reading, atr_ratio)
        instant_side, instant_strength = self.score_to_side(instant_score)
        
        # Mettre à jour EMA
        self.update_ema(instant_score)
        smoothed_side, smoothed_strength = self.score_to_side(self.ema_score)
        
        # Détecter grosse main
        big_hand_detected, big_hand_side, big_hand_type, big_hand_size = self.detect_big_hand(reading)
        
        # Détecter divergence
        divergence = False
        divergence_type = None
        if instant_side != smoothed_side and instant_side != 'NEUTRAL' and smoothed_side != 'NEUTRAL':
            divergence = True
            if instant_side == 'SELLERS' and smoothed_side == 'BUYERS':
                divergence_type = 'REVERSAL_DOWN'
            elif instant_side == 'BUYERS' and smoothed_side == 'SELLERS':
                divergence_type = 'REVERSAL_UP'
        
        # Créer le résultat
        result = DOMPressureResult(
            instant_side=instant_side,
            instant_score=instant_score,
            instant_strength=instant_strength,
            
            smoothed_side=smoothed_side,
            smoothed_score=self.ema_score,
            smoothed_strength=smoothed_strength,
            
            big_hand_detected=big_hand_detected,
            big_hand_side=big_hand_side,
            big_hand_type=big_hand_type,
            big_hand_size=big_hand_size,
            
            divergence=divergence,
            divergence_type=divergence_type,
            
            factors=factors,
            conseil=""
        )
        
        # Générer conseil
        result.conseil = self.generate_conseil(result)
        
        return result


# ═══════════════════════════════════════════════════════════════
# FONCTIONS UTILITAIRES POUR LE DASHBOARD
# ═══════════════════════════════════════════════════════════════

def format_dom_pressure_for_display(result: DOMPressureResult, reading: DOMReading) -> Dict:
    """
    Formate le résultat pour l'affichage dans le dashboard
    """
    return {
        # Header
        'title': 'QUI A LA MAIN?',
        
        # Instantané
        'instant': {
            'side': result.instant_side,
            'emoji': '🟢' if result.instant_side == 'BUYERS' else '🔴' if result.instant_side == 'SELLERS' else '⚪',
            'strength': result.instant_strength,
            'score': result.instant_score,
            'color': '#0fbf84' if result.instant_side == 'BUYERS' else '#ef476f' if result.instant_side == 'SELLERS' else '#64748b',
        },
        
        # Lissé
        'smoothed': {
            'side': result.smoothed_side,
            'emoji': '🟢' if result.smoothed_side == 'BUYERS' else '🔴' if result.smoothed_side == 'SELLERS' else '⚪',
            'strength': result.smoothed_strength,
            'score': result.smoothed_score,
            'color': '#0fbf84' if result.smoothed_side == 'BUYERS' else '#ef476f' if result.smoothed_side == 'SELLERS' else '#64748b',
        },
        
        # Données brutes
        'raw': {
            'bid_pct': reading.bid_pct,
            'ask_pct': reading.ask_pct,
            'delta_pct': reading.delta_pct,
            'depth_bid': reading.depth_bid,
            'depth_ask': reading.depth_ask,
            'smart_money': reading.smart_money_flow,
            'cum_delta': reading.cum_delta,
        },
        
        # Grosse main
        'big_hand': {
            'detected': result.big_hand_detected,
            'side': result.big_hand_side,
            'type': result.big_hand_type,
            'size': result.big_hand_size,
        },
        
        # Divergence
        'divergence': {
            'detected': result.divergence,
            'type': result.divergence_type,
        },
        
        # Conseil
        'conseil': result.conseil,
        
        # Facteurs détaillés
        'factors': result.factors,
    }


# ═══════════════════════════════════════════════════════════════
# EXEMPLE D'UTILISATION
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Exemple avec ton snapshot
    example_snapshot = {
        't_ms': 1765373268340,
        'askPct': 0.591241,
        'bidPct': 0.408759,
        'deltaPct': -0.182482,
        'smart_money_flow': 0.182482,
        'institutional_pressure': 0.182482,
        'delta_burst': 25,
        'stacked_imbalance_bid_rows': 1,
        'stacked_imbalance_ask_rows': 0,
        'cum_delta_session': 589,
        'ob_center': 0.176471,
        'top_heavy': -0.411765,
        'atr_ratio': 30.64,
        'dom_features': {
            'depth_bid': 36,
            'depth_ask': 32,
            'imbalance_1_3': 0.230769,
            'imbalance_6_10': 0.024390,
        }
    }
    
    # Créer l'analyseur
    analyzer = DOMPressureAnalyzer()
    
    # Analyser
    result = analyzer.analyze(example_snapshot)
    
    # Afficher
    print("=" * 60)
    print("🎯 ANALYSE DOM PRESSURE")
    print("=" * 60)
    print(f"\n📊 INSTANTANÉ:")
    print(f"   Side: {result.instant_side} ({result.instant_score:+.3f})")
    print(f"   Force: {'█' * result.instant_strength}{'░' * (5-result.instant_strength)} {result.instant_strength}/5")
    
    print(f"\n📈 LISSÉ (EMA):")
    print(f"   Side: {result.smoothed_side} ({result.smoothed_score:+.3f})")
    print(f"   Force: {'█' * result.smoothed_strength}{'░' * (5-result.smoothed_strength)} {result.smoothed_strength}/5")
    
    if result.big_hand_detected:
        print(f"\n🚨 GROSSE MAIN DÉTECTÉE!")
        print(f"   Side: {result.big_hand_side}")
        print(f"   Type: {result.big_hand_type}")
        print(f"   Size: {result.big_hand_size}")
    
    if result.divergence:
        print(f"\n⚠️ DIVERGENCE: {result.divergence_type}")
    
    print(f"\n💡 CONSEIL:")
    print(f"   {result.conseil}")
    
    print(f"\n📋 FACTEURS:")
    for factor, (side, contrib) in result.factors.items():
        bar = '█' * int(abs(contrib) * 20) if contrib != 0 else '░'
        print(f"   {factor:15s}: {side:8s} ({contrib:+.3f}) {bar}")
