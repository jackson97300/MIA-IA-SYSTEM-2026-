"""
Risk & Sizing Engine v1
=======================

Transforme les recommandations (NO_GO / SCOUT_GO / GO) en cadre d'exécution clair
(taille, stop, TP) avec gestion du risque par mode.

Auteur: MIA Trading System
Version: 1.0
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
from core.logger import get_logger

logger = get_logger(__name__)

# === CONFIGURATION RISK PAR MODE ===

RISK_CFG = {
    "SCOUT": {
        "risk_usd": 150,       # risque max par trade
        "stop_ticks_min": 10,  # min 10 ticks
        "stop_frac_atr": 0.25, # 25% d'ATR en ticks
        "tp_frac_atr": 0.50,   # TP à 50% ATR
        "size_hint": "half"
    },
    "FULL": {
        "risk_usd": 300,
        "stop_ticks_min": 12,
        "stop_frac_atr": 0.30,
        "tp_frac_atr": 0.70,
        "size_hint": "full"
    }
}

# Configuration tick value par symbole (ES, MES, etc.)
TICK_SPECS = {
    'ES':  { 'tick_size': 0.25, 'tick_value': 12.5 },
    'MES': { 'tick_size': 0.25, 'tick_value': 1.25 },
    'NQ':  { 'tick_size': 0.25, 'tick_value': 5.0 },
    'MNQ': { 'tick_size': 0.25, 'tick_value': 0.5 },
    'YM':  { 'tick_size': 1.0,  'tick_value': 5.0 },
    'MYM': { 'tick_size': 1.0,  'tick_value': 0.5 },
    'RTY': { 'tick_size': 0.1,  'tick_value': 5.0 },
    'M2K': { 'tick_size': 0.1,  'tick_value': 0.5 },
    'GC':  { 'tick_size': 0.1,  'tick_value': 0.1 },
    'MGC': { 'tick_size': 0.1,  'tick_value': 0.01 },
    'CL':  { 'tick_size': 0.01, 'tick_value': 10.0 },
    'MCL': { 'tick_size': 0.01, 'tick_value': 1.0 }
}

def _symbol_family(symbol: str) -> str:
    if symbol.startswith('MNQ'): return 'MNQ'
    if symbol.startswith('NQ'):  return 'NQ'
    if symbol.startswith('MES'): return 'MES'
    if symbol.startswith('ES'):  return 'ES'
    if symbol.startswith('MYM'): return 'MYM'
    if symbol.startswith('YM'):  return 'YM'
    if symbol.startswith('M2K'): return 'M2K'
    if symbol.startswith('RTY'): return 'RTY'
    if symbol.startswith('MGC'): return 'MGC'
    if symbol.startswith('GC'):  return 'GC'
    if symbol.startswith('MCL'): return 'MCL'
    if symbol.startswith('CL'):  return 'CL'
    return 'ES'

@dataclass
class RiskBracket:
    """Bracket de risque pour un trade"""
    mode: str                    # 'SCOUT' ou 'FULL'
    symbol: str                  # Symbole (ES, MES, etc.)
    contracts: int               # Nombre de contrats
    stop_ticks: int              # Stop en ticks
    tp_ticks: int                # TP en ticks
    risk_usd: float              # Risque en USD
    tick_value: float            # Valeur du tick
    tick_size: float             # Taille du tick
    size_hint: str               # 'half' ou 'full'
    atr_ticks: float             # ATR en ticks (pour debug)

class RiskSizingEngine:
    """Moteur de calcul du risque et de la taille de position"""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.logger.info("🎯 Risk & Sizing Engine v1 initialisé")

    def build_risk_bracket(self, elite_synthesis: Dict[str, Any],
                          symbol: str = "ES", atr_ticks: float = None,
                          snapshot: Optional[Dict[str, Any]] = None) -> Optional[RiskBracket]:
        """
        Construit un bracket de risque basé sur la recommendation Elite

        Args:
            elite_synthesis: Résultats de l'Elite Unifier
            symbol: Symbole (ES, MES, NQ, etc.)
            atr_ticks: ATR en ticks (optionnel, calculé si non fourni)
            snapshot: ML_READY snapshot (optionnel, pour ajustements MenthorQ)

        Returns:
            RiskBracket ou None si pas de signal
        """
        try:
            mode = elite_synthesis.get("go_live_mode", "NO")
            if mode not in ("SCOUT", "FULL"):
                return None

            cfg = RISK_CFG[mode]
            fam = _symbol_family(symbol)
            tick_value = TICK_SPECS.get(fam, TICK_SPECS['ES'])['tick_value']
            tick_size = TICK_SPECS.get(fam, TICK_SPECS['ES'])['tick_size']

            # ATR en ticks (fallback si non fourni)
            if atr_ticks is None:
                atr_ticks = 20.0  # Fallback conservateur

            # Stop en ticks = max(min, frac*ATR)
            stop_ticks = int(max(cfg["stop_ticks_min"], cfg["stop_frac_atr"] * max(atr_ticks, 1.0)))
            tp_ticks = int(max(stop_ticks, cfg["tp_frac_atr"] * max(atr_ticks, 1.0)))

            # 📚 Bible MenthorQ v2.0: Ajuster sizing selon dangers MenthorQ
            size_multiplier = 1.0
            menthorq_warnings = []

            if snapshot:
                mid = snapshot.get('mid', 0)

                # Check 1: Blind Spots proximity
                blind_spots = snapshot.get('blind_spots', [])
                if blind_spots and mid:
                    min_blind_dist = float('inf')
                    for bs in blind_spots:
                        if isinstance(bs, dict):
                            bs_price = bs.get('price', 0)
                            if bs_price:
                                dist_pct = abs((bs_price - mid) / mid) * 100
                                min_blind_dist = min(min_blind_dist, dist_pct)

                    if min_blind_dist < 0.15:  # < 0.15% du prix
                        size_multiplier *= 0.7  # -30%
                        menthorq_warnings.append(f"blind_spot_proche ({min_blind_dist:.2f}%)")
                        self.logger.warning(f"⚠️ Blind Spot proche ({min_blind_dist:.2f}%) → sizing ×0.7")

                # Check 2: 1-Day extremes proximity
                day_max = snapshot.get('1d_max', 0)
                day_min = snapshot.get('1d_min', 0)

                if day_max and day_min and mid and day_max > day_min:
                    day_range = day_max - day_min
                    position_pct = ((mid - day_min) / day_range) * 100

                    if position_pct >= 95:  # Près 1d_max
                        size_multiplier *= 0.8  # -20%
                        menthorq_warnings.append(f"near_1d_max ({position_pct:.1f}%)")
                        self.logger.warning(f"⚠️ Prix @ {position_pct:.1f}% (près 1d_max) → sizing ×0.8")
                    elif position_pct <= 5:  # Près 1d_min
                        size_multiplier *= 0.8  # -20%
                        menthorq_warnings.append(f"near_1d_min ({position_pct:.1f}%)")
                        self.logger.warning(f"⚠️ Prix @ {position_pct:.1f}% (près 1d_min) → sizing ×0.8")

                # Check 3: Multiple warnings → réduction cumulée
                if len(menthorq_warnings) >= 2:
                    size_multiplier *= 0.9  # -10% additionnel
                    self.logger.warning(f"⚠️ Multiples warnings MenthorQ ({len(menthorq_warnings)}) → sizing ×0.9 additionnel")

            # Position sizing par risque
            # taille = floor(risk_usd / (stop_ticks * tick_value)) × menthorq_multiplier
            raw_size = (cfg["risk_usd"] / max(stop_ticks * tick_value, 1e-9)) * size_multiplier
            contracts = max(int(raw_size), 1)

            # Limiter la taille selon le mode
            if mode == "SCOUT":
                contracts = min(contracts, 2)  # Max 2 contrats en SCOUT
            else:
                contracts = min(contracts, 5)  # Max 5 contrats en FULL

            bracket = RiskBracket(
                mode=mode,
                symbol=symbol,
                contracts=contracts,
                stop_ticks=stop_ticks,
                tp_ticks=tp_ticks,
                risk_usd=cfg["risk_usd"],
                tick_value=tick_value,
                tick_size=tick_size,
                size_hint=cfg["size_hint"],
                atr_ticks=atr_ticks
            )

            log_msg = f"🎯 Risk Bracket: {mode} {symbol} size={contracts} stop={stop_ticks}t tp={tp_ticks}t risk=${cfg['risk_usd']}"
            if size_multiplier < 1.0:
                log_msg += f" (MenthorQ sizing ×{size_multiplier:.2f}: {', '.join(menthorq_warnings)})"
            self.logger.info(log_msg)

            return bracket

        except Exception as e:
            self.logger.error(f"❌ Erreur calcul risk bracket: {e}")
            return None

    def format_risk_summary(self, bracket: RiskBracket) -> str:
        """Formate un résumé du bracket de risque"""
        if not bracket:
            return "Pas de signal"

        return (f"Risk: mode={bracket.mode} {bracket.symbol} size={bracket.contracts} "
                f"stop={bracket.stop_ticks}t tp={bracket.tp_ticks}t (~${bracket.risk_usd})")

    def get_symbol_family(self, symbol: str) -> str:
        return _symbol_family(symbol)

# === FONCTION UTILITAIRE ===

def build_risk_bracket(elite_synthesis: Dict[str, Any],
                      symbol: str = "ES", atr_ticks: float = None) -> Optional[RiskBracket]:
    """
    Fonction utilitaire pour construire un bracket de risque

    Args:
        elite_synthesis: Résultats de l'Elite Unifier
        symbol: Symbole (ES, MES, NQ, etc.)
        atr_ticks: ATR en ticks (optionnel)

    Returns:
        RiskBracket ou None
    """
    engine = RiskSizingEngine()
    return engine.build_risk_bracket(elite_synthesis, symbol, atr_ticks)
