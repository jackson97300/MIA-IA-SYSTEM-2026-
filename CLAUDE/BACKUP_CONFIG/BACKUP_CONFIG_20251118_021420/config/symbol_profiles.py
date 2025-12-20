#!/usr/bin/env python3
"""
MIA_IA_SYSTEM - Configuration Profils Symboles
Phase 4.0: Seuils adaptatifs par symbole + VIX regime
🔥 MODE DATA COLLECTION: Seuils permissifs -5%

Location: D:\\MIA_IA_system\\config\\symbol_profiles.py
"""

from dataclasses import dataclass, field
from typing import Dict, Tuple
import os

# ═══════════════════════════════════════════════════════════════
# 🔥 MODE DATA COLLECTION (Activer pour phase optimisation)
# ═══════════════════════════════════════════════════════════════
DATA_COLLECTION_MODE = os.getenv('DATA_COLLECTION_MODE', 'True').lower() == 'true'
# ⚠️ AJUSTEMENT DÉSACTIVÉ - Les trades manquaient de pertinence avec -5%
CONFIDENCE_ADJUSTMENT = 0.0  # Pas d'ajustement (seuils normaux pour meilleure qualité)

@dataclass
class SymbolProfile:
    """Profil de trading pour un symbole spécifique"""
    # Caractéristiques symbole
    tick_size: float
    tick_value: float

    # Seuils ML 3-Layer (base)
    min_total_conf_base: float  # Confidence totale minimum en conditions normales
    min_layer1_conf: float  # MenthorQ minimum
    min_layer2_conf: float  # OrderFlow minimum
    min_layer3_conf: float  # Context minimum

    # Risk management
    max_size_usd: float  # Risque maximum par trade (USD)
    default_sl_ticks: int  # Stop loss par défaut (en ticks)
    default_tp_ticks: int  # Take profit par défaut (en ticks)

    # VIX regime thresholds
    vix_low: float  # VIX < vix_low = marché calme
    vix_mid: float  # vix_low ≤ VIX < vix_mid = normal
    # VIX ≥ vix_mid = haute volatilité

    # VIX regime adjustments (ajout au min_total_conf_base)
    vix_low_adjustment: float = 0.0  # Marché calme: pas d'ajustement
    vix_mid_adjustment: float = 0.02  # Normal: +2%
    vix_high_adjustment: float = 0.05  # Haute vol: +5% (plus strict)

    def get_min_confidence(self, vix: float = None) -> float:
        """
        Calcule la confidence minimum requise selon le VIX

        Args:
            vix: Valeur VIX actuelle (si None, retourne base)

        Returns:
            Confidence minimum requise
        """
        if vix is None:
            return self.min_total_conf_base

        if vix < self.vix_low:
            return self.min_total_conf_base + self.vix_low_adjustment
        elif vix < self.vix_mid:
            return self.min_total_conf_base + self.vix_mid_adjustment
        else:
            return self.min_total_conf_base + self.vix_high_adjustment

    def get_vix_regime(self, vix: float) -> str:
        """Retourne le régime VIX actuel"""
        if vix < self.vix_low:
            return "LOW"
        elif vix < self.vix_mid:
            return "NORMAL"
        else:
            return "HIGH"


# ════════════════════════════════════════════════════════════════
# 📊 PROFILS PAR SYMBOLE
# ════════════════════════════════════════════════════════════════

SYMBOL_PROFILES = {
    "ES": SymbolProfile(
        # Caractéristiques
        tick_size=0.25,
        tick_value=12.5,

        # Seuils ML 3-Layer
        # ✅ CORRECTION P0: Augmenté de 0.28 à 0.35 (+7%) pour améliorer win rate ES
        min_total_conf_base=0.35 + CONFIDENCE_ADJUSTMENT,  # 0.35 (augmenté de 0.28 pour ES sous-performance)
        min_layer1_conf=0.25,  # MenthorQ
        min_layer2_conf=0.18,  # OrderFlow
        min_layer3_conf=0.12,  # Context

        # Risk
        max_size_usd=500.0,  # $500 risque max par trade
        default_sl_ticks=18,  # ✅ CORRECTION P0: 18 ticks = $225 (augmenté de 12 pour améliorer win rate ES)
        default_tp_ticks=20,  # ✅ AJUSTEMENT: 20 ticks = $250 (R:R 1.11:1 - justifié par confluence >0.70 + confiance 0.35)

        # VIX thresholds (ES suit SPX)
        vix_low=16.0,   # VIX < 16 = calme
        vix_mid=22.0,   # VIX 16-22 = normal
        # VIX ≥ 22 = haute volatilité

        # Adjustments
        vix_low_adjustment=0.0,
        vix_mid_adjustment=0.02,
        vix_high_adjustment=0.05,
    ),

    "NQ": SymbolProfile(
        # Caractéristiques
        tick_size=0.25,
        tick_value=5.0,

        # Seuils ML 3-Layer (NQ plus nerveux)
        # 🔥 OPTIMISATION 2025-11-18: Aligné avec ml_3layer_filter.py (0.28)
        min_total_conf_base=0.28 + CONFIDENCE_ADJUSTMENT,  # 0.28 global (aligné avec filter)
        min_layer1_conf=0.27,  # MenthorQ
        min_layer2_conf=0.20,  # OrderFlow
        min_layer3_conf=0.13,  # Context

        # Risk
        max_size_usd=450.0,  # $450 risque max
        default_sl_ticks=15,  # 15 ticks = $75
        default_tp_ticks=30,  # 2:1 ratio

        # VIX thresholds (NQ plus volatile)
        vix_low=18.0,   # Seuils plus hauts que ES
        vix_mid=25.0,

        # Adjustments (plus agressifs)
        vix_low_adjustment=0.0,
        vix_mid_adjustment=0.03,  # +3% en normal
        vix_high_adjustment=0.07,  # +7% en haute vol
    ),

    "RTY": SymbolProfile(
        # Caractéristiques
        tick_size=0.10,
        tick_value=5.0,

        # Seuils ML 3-Layer (RTY entre ES et NQ)
        # 🔥 OPTIMISATION 2025-11-18: Aligné avec ml_3layer_filter.py (0.28)
        min_total_conf_base=0.28 + CONFIDENCE_ADJUSTMENT,  # 0.28 global (aligné avec filter)
        min_layer1_conf=0.26,  # MenthorQ
        min_layer2_conf=0.19,  # OrderFlow
        min_layer3_conf=0.13,  # Context

        # Risk
        max_size_usd=350.0,  # $350 risque max (small caps plus risqué)
        default_sl_ticks=20,  # 20 ticks = $100
        default_tp_ticks=40,  # 2:1 ratio

        # VIX thresholds (RTY suit RVX mais on utilise VIX)
        vix_low=20.0,   # RTY plus volatile
        vix_mid=28.0,

        # Adjustments
        vix_low_adjustment=0.0,
        vix_mid_adjustment=0.03,
        vix_high_adjustment=0.06,
    ),
}


def get_symbol_profile(symbol: str) -> SymbolProfile:
    """
    Retourne le profil pour un symbole

    Args:
        symbol: Symbol (ES, NQ, RTY)

    Returns:
        SymbolProfile correspondant (ES par défaut si introuvable)
    """
    # Extraire symbole de base (ex: "ESZ25" → "ES")
    base_symbol = symbol[:2].upper()
    return SYMBOL_PROFILES.get(base_symbol, SYMBOL_PROFILES["ES"])


def get_adaptive_threshold(symbol: str, vix: float = None) -> Dict[str, float]:
    """
    Calcule les seuils adaptatifs pour un symbole selon VIX

    Args:
        symbol: Symbol (ES, NQ, RTY)
        vix: Valeur VIX actuelle

    Returns:
        Dict avec tous les seuils calculés
    """
    profile = get_symbol_profile(symbol)

    return {
        "min_total_conf": profile.get_min_confidence(vix),
        "min_layer1_conf": profile.min_layer1_conf,
        "min_layer2_conf": profile.min_layer2_conf,
        "min_layer3_conf": profile.min_layer3_conf,
        "vix": vix,
        "vix_regime": profile.get_vix_regime(vix) if vix else "UNKNOWN",
        "profile": profile,
    }


# ════════════════════════════════════════════════════════════════
# 🧪 TESTS
# ════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 80)
    print("📊 TEST SYMBOL PROFILES")
    print("=" * 80)

    # Test ES
    print("\n🔹 ES Profile:")
    es_profile = get_symbol_profile("ES")
    print(f"   Tick: ${es_profile.tick_value} / {es_profile.tick_size}")
    print(f"   Base confidence: {es_profile.min_total_conf_base:.2%}")
    print(f"   VIX LOW (14): {es_profile.get_min_confidence(14):.2%} ({es_profile.get_vix_regime(14)})")
    print(f"   VIX NORMAL (18): {es_profile.get_min_confidence(18):.2%} ({es_profile.get_vix_regime(18)})")
    print(f"   VIX HIGH (25): {es_profile.get_min_confidence(25):.2%} ({es_profile.get_vix_regime(25)})")

    # Test NQ
    print("\n🔹 NQ Profile:")
    nq_profile = get_symbol_profile("NQ")
    print(f"   Tick: ${nq_profile.tick_value} / {nq_profile.tick_size}")
    print(f"   Base confidence: {nq_profile.min_total_conf_base:.2%}")
    print(f"   VIX LOW (16): {nq_profile.get_min_confidence(16):.2%} ({nq_profile.get_vix_regime(16)})")
    print(f"   VIX NORMAL (20): {nq_profile.get_min_confidence(20):.2%} ({nq_profile.get_vix_regime(20)})")
    print(f"   VIX HIGH (28): {nq_profile.get_min_confidence(28):.2%} ({nq_profile.get_vix_regime(28)})")

    # Test RTY
    print("\n🔹 RTY Profile:")
    rty_profile = get_symbol_profile("RTY")
    print(f"   Tick: ${rty_profile.tick_value} / {rty_profile.tick_size}")
    print(f"   Base confidence: {rty_profile.min_total_conf_base:.2%}")
    print(f"   VIX LOW (18): {rty_profile.get_min_confidence(18):.2%} ({rty_profile.get_vix_regime(18)})")
    print(f"   VIX NORMAL (24): {rty_profile.get_min_confidence(24):.2%} ({rty_profile.get_vix_regime(24)})")
    print(f"   VIX HIGH (30): {rty_profile.get_min_confidence(30):.2%} ({rty_profile.get_vix_regime(30)})")

    print("\n✅ Tests OK")
    print("=" * 80)
