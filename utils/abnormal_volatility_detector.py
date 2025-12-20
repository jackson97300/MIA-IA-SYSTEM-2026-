# ==============================================================================
# ABNORMAL VOLATILITY DETECTOR - Détection Breaking News / Événements Imprévus
# ==============================================================================
#
# Ce module détecte les mouvements de marché anormaux qui indiquent souvent
# un événement imprévu (discours surprise président, breaking news, etc.)
#
# SIGNAUX DÉTECTÉS:
# ┌─────────────────────┬─────────────────────────────────────────────────────┐
# │ SIGNAL              │ DESCRIPTION                                         │
# ├─────────────────────┼─────────────────────────────────────────────────────┤
# │ 🚨 PRICE SPIKE      │ Prix bouge de ±X% en Y secondes                     │
# │ 🚨 VIX SPIKE        │ VIX monte de +X% rapidement                         │
# │ 🚨 VOLUME SPIKE     │ Volume 5x+ la moyenne (souvent = breaking news)     │
# │ 🚨 SPREAD EXPANSION │ Spread bid/ask explose (market makers se retirent)  │
# │ 🚨 TICK VELOCITY    │ Nombre de ticks/sec anormal (HFT panic)             │
# └─────────────────────┴─────────────────────────────────────────────────────┘
#
# COMPORTEMENT:
# - Si détecté → STOP TRADING pendant X minutes (cooldown)
# - Log détaillé avec raison
# - Stats pour analyse post-mortem
#
# ==============================================================================

import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass, field
from collections import deque
from enum import Enum

logger = logging.getLogger(__name__)


# ==============================================================================
# CONFIGURATION
# ==============================================================================

class AlertLevel(Enum):
    """Niveau d'alerte de volatilité"""
    NORMAL = 0      # 🟢 Trading normal
    ELEVATED = 1    # 🟡 Prudence - Réduire taille
    HIGH = 2        # 🟠 Danger - Stop temporaire (5 min)
    EXTREME = 3     # 🔴 PANIC - Stop long (15 min)


@dataclass
class VolatilityAlert:
    """Structure d'une alerte de volatilité"""
    level: AlertLevel
    reason: str
    details: Dict
    timestamp: datetime = field(default_factory=datetime.now)
    cooldown_minutes: int = 5
    
    @property
    def emoji(self) -> str:
        return {
            AlertLevel.NORMAL: "🟢",
            AlertLevel.ELEVATED: "🟡", 
            AlertLevel.HIGH: "🟠",
            AlertLevel.EXTREME: "🔴"
        }[self.level]
    
    def __str__(self) -> str:
        return f"{self.emoji} [{self.level.name}] {self.reason}"


# Configuration par symbole (ES/NQ ont des caractéristiques différentes)
VOLATILITY_CONFIG = {
    "ES": {
        # Price spike detection
        "price_spike_threshold_pct": 0.30,    # 0.30% en 60 sec = anormal pour ES
        "price_spike_window_sec": 60,
        
        # VIX spike (ES très corrélé au VIX)
        "vix_spike_threshold_pct": 8.0,       # VIX +8% = danger
        "vix_extreme_threshold_pct": 15.0,    # VIX +15% = PANIC
        
        # Volume spike
        "volume_spike_multiplier": 5.0,       # 5x volume moyen = suspect
        
        # Spread expansion
        "spread_normal_ticks": 1,             # ES = 1 tick spread normal
        "spread_danger_ticks": 4,             # 4+ ticks = market makers partis
        
        # Tick velocity (ticks par seconde)
        "tick_velocity_normal": 50,           # ~50 ticks/sec normal
        "tick_velocity_danger": 200,          # 200+ = HFT panic
        
        # Cooldowns
        "cooldown_elevated_min": 2,
        "cooldown_high_min": 5,
        "cooldown_extreme_min": 15,
    },
    "NQ": {
        # NQ plus volatile que ES
        "price_spike_threshold_pct": 0.50,    # 0.50% en 60 sec
        "price_spike_window_sec": 60,
        
        "vix_spike_threshold_pct": 8.0,
        "vix_extreme_threshold_pct": 15.0,
        
        "volume_spike_multiplier": 5.0,
        
        "spread_normal_ticks": 1,
        "spread_danger_ticks": 6,             # NQ a parfois 2-3 ticks normaux
        
        "tick_velocity_normal": 60,
        "tick_velocity_danger": 250,
        
        "cooldown_elevated_min": 2,
        "cooldown_high_min": 5,
        "cooldown_extreme_min": 15,
    },
    "RTY": {
        # RTY encore plus volatile
        "price_spike_threshold_pct": 0.60,
        "price_spike_window_sec": 60,
        
        "vix_spike_threshold_pct": 10.0,
        "vix_extreme_threshold_pct": 20.0,
        
        "volume_spike_multiplier": 4.0,
        
        "spread_normal_ticks": 1,
        "spread_danger_ticks": 5,
        
        "tick_velocity_normal": 40,
        "tick_velocity_danger": 150,
        
        "cooldown_elevated_min": 2,
        "cooldown_high_min": 5,
        "cooldown_extreme_min": 15,
    }
}

# Config par défaut si symbole inconnu
DEFAULT_CONFIG = VOLATILITY_CONFIG["ES"]


# ==============================================================================
# CLASSE PRINCIPALE
# ==============================================================================

class AbnormalVolatilityDetector:
    """
    Détecteur de volatilité anormale pour identifier les breaking news
    et événements imprévus (discours surprise, tweets, etc.)
    
    Utilisation:
        detector = AbnormalVolatilityDetector()
        
        # Dans run_cycle:
        alert = detector.check_volatility(symbol, tick_data)
        if alert and alert.level >= AlertLevel.HIGH:
            logger.warning(f"🚨 {alert}")
            return None  # Stop trading
    """
    
    def __init__(self, config_override: Dict = None):
        """
        Initialise le détecteur.
        
        Args:
            config_override: Override la config par défaut (optionnel)
        """
        self.config = config_override or VOLATILITY_CONFIG
        
        # Historique des prix par symbole (pour calculer les variations)
        self.price_history: Dict[str, deque] = {}
        self.vix_history: deque = deque(maxlen=120)  # 2 min d'historique VIX
        self.volume_history: Dict[str, deque] = {}
        self.tick_counts: Dict[str, deque] = {}  # Compteur de ticks par seconde
        
        # État des cooldowns actifs
        self.active_cooldowns: Dict[str, datetime] = {}
        
        # Dernier VIX connu
        self.last_vix: Optional[float] = None
        self.last_vix_time: Optional[datetime] = None
        
        # Stats
        self.stats = {
            'checks_total': 0,
            'alerts_triggered': 0,
            'alerts_by_type': {
                'price_spike': 0,
                'vix_spike': 0,
                'volume_spike': 0,
                'spread_expansion': 0,
                'tick_velocity': 0
            },
            'trades_blocked': 0
        }
        
        logger.info("🔍 ══════════════════════════════════════════════════")
        logger.info("🔍 ABNORMAL VOLATILITY DETECTOR INITIALISÉ")
        logger.info("🔍 ══════════════════════════════════════════════════")
        logger.info("📊 Seuils configurés:")
        for symbol, cfg in self.config.items():
            logger.info(f"   {symbol}: Price ±{cfg['price_spike_threshold_pct']}% / "
                       f"VIX +{cfg['vix_spike_threshold_pct']}% / "
                       f"Spread >{cfg['spread_danger_ticks']} ticks")
        logger.info("🔍 ══════════════════════════════════════════════════")
    
    def _get_config(self, symbol: str) -> Dict:
        """Récupère la config pour un symbole"""
        # Normaliser le symbole (MES → ES, MNQ → NQ, etc.)
        base_symbol = symbol.upper().replace("M", "").replace("2", "")
        if base_symbol in ["ES", "SPY", "SPX"]:
            return self.config.get("ES", DEFAULT_CONFIG)
        elif base_symbol in ["NQ", "QQQ", "NDX"]:
            return self.config.get("NQ", DEFAULT_CONFIG)
        elif base_symbol in ["RTY", "RUT", "IWM"]:
            return self.config.get("RTY", DEFAULT_CONFIG)
        return DEFAULT_CONFIG
    
    def _update_price_history(self, symbol: str, price: float, timestamp: datetime):
        """Met à jour l'historique des prix"""
        if symbol not in self.price_history:
            self.price_history[symbol] = deque(maxlen=120)  # 2 min @ 1/sec
        
        self.price_history[symbol].append({
            'price': price,
            'time': timestamp
        })
    
    def _update_vix_history(self, vix: float, timestamp: datetime):
        """Met à jour l'historique VIX"""
        self.vix_history.append({
            'vix': vix,
            'time': timestamp
        })
        self.last_vix = vix
        self.last_vix_time = timestamp
    
    def _update_volume_history(self, symbol: str, volume: float):
        """Met à jour l'historique de volume"""
        if symbol not in self.volume_history:
            self.volume_history[symbol] = deque(maxlen=60)  # 1 min
        
        self.volume_history[symbol].append(volume)
    
    def _update_tick_count(self, symbol: str, timestamp: datetime):
        """Compte les ticks par seconde"""
        if symbol not in self.tick_counts:
            self.tick_counts[symbol] = deque(maxlen=60)
        
        current_second = timestamp.replace(microsecond=0)
        
        if self.tick_counts[symbol] and self.tick_counts[symbol][-1]['second'] == current_second:
            self.tick_counts[symbol][-1]['count'] += 1
        else:
            self.tick_counts[symbol].append({
                'second': current_second,
                'count': 1
            })
    
    # ==========================================================================
    # CHECKS INDIVIDUELS
    # ==========================================================================
    
    def _check_price_spike(self, symbol: str, current_price: float, 
                           timestamp: datetime) -> Optional[VolatilityAlert]:
        """
        Détecte un mouvement de prix anormal (spike).
        
        Ex: ES bouge de 0.30%+ en 60 secondes = probablement breaking news
        """
        config = self._get_config(symbol)
        history = self.price_history.get(symbol, deque())
        
        if len(history) < 10:  # Pas assez d'historique
            return None
        
        # Chercher le prix il y a X secondes
        window_sec = config['price_spike_window_sec']
        cutoff_time = timestamp - timedelta(seconds=window_sec)
        
        old_prices = [h['price'] for h in history if h['time'] <= cutoff_time]
        if not old_prices:
            return None
        
        old_price = old_prices[-1]  # Prix le plus récent avant la fenêtre
        
        # Calculer le changement en %
        price_change_pct = abs((current_price - old_price) / old_price) * 100
        
        threshold = config['price_spike_threshold_pct']
        
        if price_change_pct >= threshold * 2:
            # EXTREME: 2x le seuil
            self.stats['alerts_by_type']['price_spike'] += 1
            return VolatilityAlert(
                level=AlertLevel.EXTREME,
                reason=f"PRICE SPIKE EXTREME: {symbol} a bougé de {price_change_pct:.2f}% en {window_sec}s!",
                details={
                    'old_price': old_price,
                    'new_price': current_price,
                    'change_pct': price_change_pct,
                    'window_sec': window_sec
                },
                cooldown_minutes=config['cooldown_extreme_min']
            )
        
        elif price_change_pct >= threshold:
            # HIGH: Au-dessus du seuil
            self.stats['alerts_by_type']['price_spike'] += 1
            return VolatilityAlert(
                level=AlertLevel.HIGH,
                reason=f"PRICE SPIKE: {symbol} a bougé de {price_change_pct:.2f}% en {window_sec}s",
                details={
                    'old_price': old_price,
                    'new_price': current_price,
                    'change_pct': price_change_pct,
                    'window_sec': window_sec
                },
                cooldown_minutes=config['cooldown_high_min']
            )
        
        return None
    
    def _check_vix_spike(self, symbol: str, current_vix: float) -> Optional[VolatilityAlert]:
        """
        Détecte un spike du VIX.
        
        VIX +8% = Danger
        VIX +15% = PANIC (événement majeur)
        """
        config = self._get_config(symbol)
        
        if len(self.vix_history) < 5:
            return None
        
        # VIX il y a 1-2 minutes
        old_vix_data = list(self.vix_history)[:5]  # Les 5 plus anciens
        old_vix = sum(d['vix'] for d in old_vix_data) / len(old_vix_data)
        
        if old_vix <= 0:
            return None
        
        vix_change_pct = ((current_vix - old_vix) / old_vix) * 100
        
        # Ne détecter que les hausses (pas les baisses)
        if vix_change_pct >= config['vix_extreme_threshold_pct']:
            self.stats['alerts_by_type']['vix_spike'] += 1
            return VolatilityAlert(
                level=AlertLevel.EXTREME,
                reason=f"VIX SPIKE EXTREME: VIX +{vix_change_pct:.1f}% (de {old_vix:.1f} à {current_vix:.1f})",
                details={
                    'old_vix': old_vix,
                    'new_vix': current_vix,
                    'change_pct': vix_change_pct
                },
                cooldown_minutes=config['cooldown_extreme_min']
            )
        
        elif vix_change_pct >= config['vix_spike_threshold_pct']:
            self.stats['alerts_by_type']['vix_spike'] += 1
            return VolatilityAlert(
                level=AlertLevel.HIGH,
                reason=f"VIX SPIKE: VIX +{vix_change_pct:.1f}% (de {old_vix:.1f} à {current_vix:.1f})",
                details={
                    'old_vix': old_vix,
                    'new_vix': current_vix,
                    'change_pct': vix_change_pct
                },
                cooldown_minutes=config['cooldown_high_min']
            )
        
        return None
    
    def _check_volume_spike(self, symbol: str, current_volume: float) -> Optional[VolatilityAlert]:
        """
        Détecte un spike de volume anormal.
        
        Volume 5x+ la moyenne = quelque chose se passe
        """
        config = self._get_config(symbol)
        history = self.volume_history.get(symbol, deque())
        
        if len(history) < 10:
            return None
        
        avg_volume = sum(history) / len(history)
        if avg_volume <= 0:
            return None
        
        volume_multiplier = current_volume / avg_volume
        
        if volume_multiplier >= config['volume_spike_multiplier'] * 2:
            self.stats['alerts_by_type']['volume_spike'] += 1
            return VolatilityAlert(
                level=AlertLevel.HIGH,
                reason=f"VOLUME SPIKE: {symbol} volume {volume_multiplier:.1f}x la moyenne!",
                details={
                    'current_volume': current_volume,
                    'avg_volume': avg_volume,
                    'multiplier': volume_multiplier
                },
                cooldown_minutes=config['cooldown_high_min']
            )
        
        elif volume_multiplier >= config['volume_spike_multiplier']:
            self.stats['alerts_by_type']['volume_spike'] += 1
            return VolatilityAlert(
                level=AlertLevel.ELEVATED,
                reason=f"VOLUME ÉLEVÉ: {symbol} volume {volume_multiplier:.1f}x la moyenne",
                details={
                    'current_volume': current_volume,
                    'avg_volume': avg_volume,
                    'multiplier': volume_multiplier
                },
                cooldown_minutes=config['cooldown_elevated_min']
            )
        
        return None
    
    def _check_spread_expansion(self, symbol: str, bid: float, ask: float, 
                                tick_size: float) -> Optional[VolatilityAlert]:
        """
        Détecte une expansion anormale du spread bid/ask.
        
        Quand les market makers se retirent (breaking news), le spread explose.
        """
        config = self._get_config(symbol)
        
        if bid <= 0 or ask <= 0 or tick_size <= 0:
            return None
        
        spread_ticks = (ask - bid) / tick_size
        
        if spread_ticks >= config['spread_danger_ticks'] * 2:
            self.stats['alerts_by_type']['spread_expansion'] += 1
            return VolatilityAlert(
                level=AlertLevel.EXTREME,
                reason=f"SPREAD EXPLOSION: {symbol} spread = {spread_ticks:.0f} ticks! (normal: {config['spread_normal_ticks']})",
                details={
                    'bid': bid,
                    'ask': ask,
                    'spread_ticks': spread_ticks,
                    'normal_ticks': config['spread_normal_ticks']
                },
                cooldown_minutes=config['cooldown_extreme_min']
            )
        
        elif spread_ticks >= config['spread_danger_ticks']:
            self.stats['alerts_by_type']['spread_expansion'] += 1
            return VolatilityAlert(
                level=AlertLevel.HIGH,
                reason=f"SPREAD LARGE: {symbol} spread = {spread_ticks:.0f} ticks (normal: {config['spread_normal_ticks']})",
                details={
                    'bid': bid,
                    'ask': ask,
                    'spread_ticks': spread_ticks,
                    'normal_ticks': config['spread_normal_ticks']
                },
                cooldown_minutes=config['cooldown_high_min']
            )
        
        return None
    
    def _check_tick_velocity(self, symbol: str) -> Optional[VolatilityAlert]:
        """
        Détecte une vélocité de ticks anormale.
        
        Trop de ticks/seconde = HFT panic, souvent précède un gros mouvement
        """
        config = self._get_config(symbol)
        tick_data = self.tick_counts.get(symbol, deque())
        
        if len(tick_data) < 3:
            return None
        
        # Moyenne des 3 dernières secondes
        recent_counts = [d['count'] for d in list(tick_data)[-3:]]
        avg_velocity = sum(recent_counts) / len(recent_counts)
        
        if avg_velocity >= config['tick_velocity_danger']:
            self.stats['alerts_by_type']['tick_velocity'] += 1
            return VolatilityAlert(
                level=AlertLevel.ELEVATED,
                reason=f"TICK VELOCITY: {symbol} {avg_velocity:.0f} ticks/sec (normal: {config['tick_velocity_normal']})",
                details={
                    'velocity': avg_velocity,
                    'normal': config['tick_velocity_normal']
                },
                cooldown_minutes=config['cooldown_elevated_min']
            )
        
        return None
    
    # ==========================================================================
    # MÉTHODE PRINCIPALE
    # ==========================================================================
    
    def check_volatility(self, symbol: str, tick_data: Dict) -> Optional[VolatilityAlert]:
        """
        Vérifie tous les indicateurs de volatilité anormale.
        
        Args:
            symbol: Symbole (ES, NQ, RTY)
            tick_data: Données du tick avec les champs:
                - price ou last_price
                - bid, ask (optionnel)
                - volume (optionnel)
                - vix (optionnel)
                - tick_size (optionnel, défaut: 0.25 pour ES)
        
        Returns:
            VolatilityAlert si détecté, None sinon
        """
        self.stats['checks_total'] += 1
        timestamp = datetime.now()
        
        # Vérifier si cooldown actif
        if symbol in self.active_cooldowns:
            if timestamp < self.active_cooldowns[symbol]:
                remaining = (self.active_cooldowns[symbol] - timestamp).seconds
                # Ne pas re-logger à chaque tick, juste retourner l'alerte
                return VolatilityAlert(
                    level=AlertLevel.HIGH,
                    reason=f"COOLDOWN ACTIF: {symbol} - reprend dans {remaining}s",
                    details={'remaining_seconds': remaining},
                    cooldown_minutes=0
                )
            else:
                # Cooldown expiré
                del self.active_cooldowns[symbol]
                logger.info(f"✅ [{symbol}] Cooldown volatilité terminé - Trading reprend")
        
        # Extraire les données
        price = tick_data.get('price') or tick_data.get('last_price') or tick_data.get('close', 0)
        bid = tick_data.get('bid', 0)
        ask = tick_data.get('ask', 0)
        volume = tick_data.get('volume', 0)
        vix = tick_data.get('vix', 0)
        tick_size = tick_data.get('tick_size', 0.25)  # ES default
        
        if price <= 0:
            return None
        
        # Mettre à jour les historiques
        self._update_price_history(symbol, price, timestamp)
        self._update_tick_count(symbol, timestamp)
        
        if volume > 0:
            self._update_volume_history(symbol, volume)
        
        if vix > 0:
            self._update_vix_history(vix, timestamp)
        
        # Liste pour collecter toutes les alertes
        alerts: List[VolatilityAlert] = []
        
        # Check 1: Price Spike
        alert = self._check_price_spike(symbol, price, timestamp)
        if alert:
            alerts.append(alert)
        
        # Check 2: VIX Spike (si VIX disponible)
        if vix > 0:
            alert = self._check_vix_spike(symbol, vix)
            if alert:
                alerts.append(alert)
        
        # Check 3: Volume Spike
        if volume > 0:
            alert = self._check_volume_spike(symbol, volume)
            if alert:
                alerts.append(alert)
        
        # Check 4: Spread Expansion
        if bid > 0 and ask > 0:
            alert = self._check_spread_expansion(symbol, bid, ask, tick_size)
            if alert:
                alerts.append(alert)
        
        # Check 5: Tick Velocity
        alert = self._check_tick_velocity(symbol)
        if alert:
            alerts.append(alert)
        
        # Retourner l'alerte la plus grave
        if alerts:
            worst_alert = max(alerts, key=lambda a: a.level.value)
            
            # Activer cooldown si niveau HIGH ou plus
            if worst_alert.level.value >= AlertLevel.HIGH.value:
                self.stats['alerts_triggered'] += 1
                self.stats['trades_blocked'] += 1
                
                cooldown_end = timestamp + timedelta(minutes=worst_alert.cooldown_minutes)
                self.active_cooldowns[symbol] = cooldown_end
                
                logger.warning(f"🚨 VOLATILITÉ ANORMALE DÉTECTÉE!")
                logger.warning(f"   {worst_alert}")
                logger.warning(f"   → Trading {symbol} PAUSÉ pour {worst_alert.cooldown_minutes} min")
                logger.warning(f"   → Reprise à {cooldown_end.strftime('%H:%M:%S')}")
            
            return worst_alert
        
        return None
    
    def is_trading_safe(self, symbol: str, tick_data: Dict) -> Tuple[bool, str]:
        """
        Version simplifiée qui retourne juste True/False + raison.
        
        Usage:
            is_safe, reason = detector.is_trading_safe(symbol, tick)
            if not is_safe:
                logger.warning(f"⚠️ {reason}")
                return None
        """
        alert = self.check_volatility(symbol, tick_data)
        
        if alert is None:
            return True, "OK"
        
        if alert.level.value >= AlertLevel.HIGH.value:
            return False, str(alert)
        
        # ELEVATED = warning mais pas bloquant
        return True, f"⚠️ {alert.reason}"
    
    def get_position_size_multiplier(self, symbol: str, tick_data: Dict) -> float:
        """
        Retourne un multiplicateur de taille basé sur la volatilité.
        
        Returns:
            1.0 = normal
            0.5 = réduire de moitié
            0.0 = ne pas trader
        """
        alert = self.check_volatility(symbol, tick_data)
        
        if alert is None:
            return 1.0
        
        if alert.level == AlertLevel.EXTREME:
            return 0.0
        elif alert.level == AlertLevel.HIGH:
            return 0.0
        elif alert.level == AlertLevel.ELEVATED:
            return 0.5
        
        return 1.0
    
    def get_stats(self) -> Dict:
        """Retourne les statistiques"""
        return {
            **self.stats,
            'active_cooldowns': {
                symbol: end.isoformat() 
                for symbol, end in self.active_cooldowns.items()
            }
        }
    
    def reset_cooldown(self, symbol: str):
        """Force la fin d'un cooldown (pour debug)"""
        if symbol in self.active_cooldowns:
            del self.active_cooldowns[symbol]
            logger.info(f"🔧 Cooldown {symbol} reset manuellement")


# ==============================================================================
# EXEMPLE D'INTÉGRATION
# ==============================================================================

"""
# Dans launch_ml_v3_production.py:

from abnormal_volatility_detector import AbnormalVolatilityDetector

class TradingBot:
    def __init__(self):
        # ... ton code existant ...
        
        # Initialiser le détecteur de volatilité anormale
        self.volatility_detector = AbnormalVolatilityDetector()
    
    async def run_cycle(self, symbol):
        '''Cycle principal'''
        
        # ... calendrier économique check ...
        
        # Lire les données
        tick = await self.get_tick_data(symbol)
        
        # 🚨 CHECK VOLATILITÉ ANORMALE (après lecture tick)
        is_safe, reason = self.volatility_detector.is_trading_safe(symbol, tick)
        
        if not is_safe:
            logger.warning(f"[{symbol}] {reason}")
            return None  # Stop trading
        
        # ... reste du code ...
"""


# ==============================================================================
# TEST LOCAL
# ==============================================================================

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(message)s'
    )
    
    print("=" * 70)
    print("TEST ABNORMAL VOLATILITY DETECTOR")
    print("=" * 70)
    
    detector = AbnormalVolatilityDetector()
    
    # Simuler des ticks normaux
    print("\n📊 Test 1: Ticks normaux")
    for i in range(10):
        tick = {
            'price': 6000 + i * 0.25,  # Mouvement normal
            'bid': 5999.75 + i * 0.25,
            'ask': 6000.25 + i * 0.25,
            'volume': 100,
            'vix': 15.0
        }
        result = detector.check_volatility("ES", tick)
        if result:
            print(f"   Tick {i}: {result}")
        else:
            print(f"   Tick {i}: ✅ Normal")
    
    # Simuler un price spike
    print("\n🚨 Test 2: Price Spike")
    # D'abord établir un historique stable
    for i in range(15):
        tick = {'price': 6000.0, 'bid': 5999.75, 'ask': 6000.25}
        detector.check_volatility("ES", tick)
    
    # Puis un gros mouvement
    tick = {'price': 6025.0, 'bid': 6024.75, 'ask': 6025.25}  # +0.4%
    result = detector.check_volatility("ES", tick)
    if result:
        print(f"   Résultat: {result}")
    
    # Test spread expansion
    print("\n🚨 Test 3: Spread Expansion")
    tick = {
        'price': 6000.0,
        'bid': 5998.0,   # 8 ticks de spread!
        'ask': 6002.0,
        'tick_size': 0.25
    }
    result = detector.check_volatility("NQ", tick)
    if result:
        print(f"   Résultat: {result}")
    
    # Stats
    print(f"\n📈 Stats: {detector.get_stats()}")
    
    print("\n" + "=" * 70)
    print("FIN DU TEST")
    print("=" * 70)
