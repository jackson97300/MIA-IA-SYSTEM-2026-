#!/usr/bin/env python3
"""
Alternative à ATR - Analyse Snapshot & Proposition
Identification de métriques plus fiables que ATR pour normalisation

TODO Task 6d - Alternative ATR
Date: 13 Novembre 2025
"""

import logging
import json
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class VolatilityMetric:
    """Métrique de volatilité alternative"""
    name: str
    value: float
    reliability: str  # HIGH/MEDIUM/LOW
    description: str
    use_case: str


class ATRAlternativeAnalyzer:
    """
    Analyse alternatives à ATR pour normalisation distances
    
    Snapshot fourni contient:
    - total_range_ticks (6.0 ES, 12.0 NQ)
    - upper_wick_ticks, lower_wick_ticks
    - 1d_max, 1d_min (range du jour)
    - volatility_regime, volatility_regime_cont
    - spread, spread_ticks
    - day_range_pct
    - position_in_range
    
    💡 HYPOTHÈSE: ATR = 1.14 est peut-être correct pour 1-minute bars
        mais on normalise avec mauvais timeframe!
    """
    
    def __init__(self):
        logger.info("🔍 ATRAlternativeAnalyzer initialisé")
    
    def analyze_snapshot(self, snapshot: Dict) -> Dict:
        """
        Analyse toutes les métriques volatilité disponibles
        
        Args:
            snapshot: Données ML_READY
            
        Returns:
            Analyse complète + recommandations
        """
        # Extraire données
        sym = snapshot.get('sym', 'ES')
        if 'ES' in sym:
            symbol = 'ES'
            tick_size = 0.25
        elif 'NQ' in sym:
            symbol = 'NQ'
            tick_size = 0.25
        elif 'RTY' in sym or '2RTY' in sym:
            symbol = 'RTY'
            tick_size = 0.10
        else:
            symbol = 'UNKNOWN'
            tick_size = 0.25
        
        mid = snapshot.get('mid', 0)
        
        # === MÉTRIQUES DISPONIBLES ===
        
        # 1. ATR (suspect)
        atr = snapshot.get('atr', 0)
        
        # 2. Total Range (bar actuelle)
        total_range_ticks = snapshot.get('total_range_ticks', 0)
        total_range_pts = total_range_ticks * tick_size
        
        # 3. 1D Range (High - Low du jour)
        day_max = snapshot.get('1d_max', 0)
        day_min = snapshot.get('1d_min', 0)
        day_range_pts = day_max - day_min if day_max and day_min else 0
        day_range_pct = snapshot.get('day_range_pct', 0)
        
        # 4. Spread
        spread_pts = snapshot.get('spread', 0)
        spread_ticks = snapshot.get('spread_ticks', 0)
        
        # 5. Volatility Regime
        vol_regime = snapshot.get('volatility_regime', 0)
        vol_regime_cont = snapshot.get('volatility_regime_cont', 0)
        
        # 6. VWAP Bands Width
        vwap = snapshot.get('vwap', 0)
        vwap_up1 = snapshot.get('vwap_up1', 0)
        vwap_dn1 = snapshot.get('vwap_dn1', 0)
        vwap_band_width = (vwap_up1 - vwap_dn1) if vwap_up1 and vwap_dn1 else 0
        
        # 7. Value Area Width
        vah = snapshot.get('vva', {}).get('vah', 0)
        val = snapshot.get('vva', {}).get('val', 0)
        value_area_width = vah - val if vah and val else 0
        
        # 8. Session Progress (pour normalisation temporelle)
        session_progress = snapshot.get('progress01', 0)
        elapsed_s = snapshot.get('elapsed_s', 0)
        
        # === CALCUL ALTERNATIVES ===
        
        metrics = []
        
        # ALT 1: Day Range Percentage (très fiable)
        if day_range_pts > 0:
            day_range_normalized = day_range_pct * 100  # En %
            metrics.append(VolatilityMetric(
                name="day_range_pct",
                value=day_range_normalized,
                reliability="HIGH",
                description=f"Range du jour = {day_range_pts:.2f} pts ({day_range_normalized:.1f}% du prix)",
                use_case="Normalisation VWAP distance en % de jour range"
            ))
        
        # ALT 2: VWAP Band Width (1σ)
        if vwap_band_width > 0:
            vwap_band_atr_equivalent = vwap_band_width / 2  # 1σ ≈ 0.5 * band_width
            metrics.append(VolatilityMetric(
                name="vwap_band_width",
                value=vwap_band_atr_equivalent,
                reliability="HIGH",
                description=f"VWAP ±1σ = {vwap_band_width:.2f} pts (équiv. ATR ~{vwap_band_atr_equivalent:.2f})",
                use_case="Normalisation distances VWAP (déjà basé sur σ)"
            ))
        
        # ALT 3: Value Area Width
        if value_area_width > 0:
            value_area_atr_equiv = value_area_width / 2  # ~68% du range
            metrics.append(VolatilityMetric(
                name="value_area_width",
                value=value_area_atr_equiv,
                reliability="MEDIUM",
                description=f"Value Area = {value_area_width:.2f} pts (équiv. ATR ~{value_area_atr_equiv:.2f})",
                use_case="Normalisation contextuelle (70% temps passé)"
            ))
        
        # ALT 4: Rolling Bar Range Average (simuler ATR avec bars récentes)
        # → Nécessite historique, pas dans snapshot unique
        
        # ALT 5: Volatility Regime Multiplier
        vol_regime_multipliers = {
            0: 0.5,   # LOW
            1: 1.0,   # MEDIUM
            2: 2.0,   # HIGH
            3: 3.0    # EXTREME
        }
        vol_multiplier = vol_regime_multipliers.get(vol_regime, 1.0)
        
        metrics.append(VolatilityMetric(
            name="volatility_regime_multiplier",
            value=vol_multiplier,
            reliability="MEDIUM",
            description=f"Régime volatilité = {vol_regime} → multiplier {vol_multiplier}x",
            use_case="Ajustement seuils selon régime marché"
        ))
        
        # === DIAGNOSTIC ATR ===
        
        # ATR supposé pour ES 5-min bars = 5-10 pts
        # ATR supposé pour ES 1-min bars = 1-3 pts ← CORRESPOND À snapshot fourni!
        
        atr_expected_ranges = {
            'ES': {
                '1min': (0.8, 3.0),
                '5min': (3.0, 10.0),
                '15min': (8.0, 20.0)
            },
            'NQ': {
                '1min': (3.0, 10.0),
                '5min': (10.0, 30.0),
                '15min': (20.0, 60.0)
            },
            'RTY': {
                '1min': (0.5, 2.0),
                '5min': (2.0, 8.0),
                '15min': (5.0, 15.0)
            }
        }
        
        # Détecter timeframe probable
        probable_timeframe = None
        if symbol in atr_expected_ranges:
            for tf, (min_atr, max_atr) in atr_expected_ranges[symbol].items():
                if min_atr <= atr <= max_atr:
                    probable_timeframe = tf
                    break
        
        # === RECOMMANDATION FINALE ===
        
        recommendation = self._generate_recommendation(
            symbol,
            atr,
            day_range_pts,
            vwap_band_width,
            value_area_width,
            probable_timeframe
        )
        
        return {
            'symbol': symbol,
            'snapshot_analysis': {
                'atr_snapshot': atr,
                'probable_timeframe': probable_timeframe,
                'day_range_pts': day_range_pts,
                'vwap_band_width': vwap_band_width,
                'value_area_width': value_area_width,
                'volatility_regime': vol_regime
            },
            'alternative_metrics': [
                {
                    'name': m.name,
                    'value': m.value,
                    'reliability': m.reliability,
                    'description': m.description,
                    'use_case': m.use_case
                }
                for m in metrics
            ],
            'recommendation': recommendation
        }
    
    def _generate_recommendation(
        self,
        symbol: str,
        atr: float,
        day_range: float,
        vwap_band: float,
        va_width: float,
        timeframe: Optional[str]
    ) -> Dict:
        """Génère recommandation finale"""
        
        # === DIAGNOSTIC ===
        
        diagnosis = []
        
        if timeframe == '1min':
            diagnosis.append(
                "✅ ATR = {:.2f} est CORRECT pour bars 1-minute!".format(atr)
            )
            diagnosis.append(
                "⚠️ PROBLÈME: Vous normalisez avec ATR 1-min mais comparez à seuils 5-min!"
            )
        elif timeframe is None:
            diagnosis.append(
                "❌ ATR = {:.2f} n'appartient à aucun timeframe standard".format(atr)
            )
        else:
            diagnosis.append(
                "✅ ATR = {:.2f} correspond à bars {}".format(atr, timeframe)
            )
        
        # === SOLUTION RECOMMANDÉE ===
        
        if vwap_band > 0:
            primary_solution = {
                'metric': 'vwap_band_width',
                'value': vwap_band / 2,
                'reason': "VWAP ±1σ est calculé sur session entière → Cohérent avec timeframe",
                'implementation': "Remplacer ATR par (vwap_up1 - vwap_dn1) / 2 pour normalisation"
            }
        elif day_range > 0:
            primary_solution = {
                'metric': 'day_range_pct',
                'value': day_range,
                'reason': "Day Range capture volatilité réelle du jour",
                'implementation': "Normaliser distances en % de day_range au lieu d'ATR"
            }
        else:
            primary_solution = {
                'metric': 'adaptive_atr_with_timeframe',
                'value': atr * 5 if timeframe == '1min' else atr,
                'reason': "Ajuster ATR selon timeframe détecté",
                'implementation': "Multiplier ATR par ratio timeframe (1min → 5min = x5)"
            }
        
        # === FALLBACK ===
        
        fallback_solution = {
            'metric': 'value_area_width',
            'value': va_width / 2 if va_width else 0,
            'reason': "Value Area = zone où 70% du volume s'échange → Volatilité réelle",
            'implementation': "Utiliser (VAH - VAL) / 2 comme proxy ATR"
        }
        
        return {
            'diagnosis': diagnosis,
            'primary_solution': primary_solution,
            'fallback_solution': fallback_solution,
            'confidence': 'HIGH' if vwap_band > 0 or day_range > 0 else 'MEDIUM'
        }
    
    def print_analysis(self, snapshot: Dict):
        """Affiche analyse formatée"""
        analysis = self.analyze_snapshot(snapshot)
        
        print("\n" + "=" * 80)
        print("🔍 ANALYSE ALTERNATIVES ATR")
        print("=" * 80)
        
        # Snapshot info
        print(f"\nSymbole: {analysis['symbol']}")
        snap = analysis['snapshot_analysis']
        print(f"ATR snapshot: {snap['atr_snapshot']:.2f}")
        print(f"Timeframe probable: {snap['probable_timeframe'] or 'INCONNU'}")
        print(f"Day Range: {snap['day_range_pts']:.2f} pts")
        print(f"VWAP Band Width: {snap['vwap_band_width']:.2f} pts")
        print(f"Value Area Width: {snap['value_area_width']:.2f} pts")
        
        # Métriques alternatives
        print("\n📊 MÉTRIQUES ALTERNATIVES DISPONIBLES:")
        for i, metric in enumerate(analysis['alternative_metrics'], 1):
            print(f"\n{i}. {metric['name'].upper()} [{metric['reliability']}]")
            print(f"   Valeur: {metric['value']:.2f}")
            print(f"   Description: {metric['description']}")
            print(f"   Usage: {metric['use_case']}")
        
        # Recommandation
        print("\n💡 RECOMMANDATION:")
        rec = analysis['recommendation']
        
        print("\nDiagnostic:")
        for diag in rec['diagnosis']:
            print(f"  {diag}")
        
        print("\nSOLUTION PRINCIPALE:")
        sol = rec['primary_solution']
        print(f"  Métrique: {sol['metric']}")
        print(f"  Valeur: {sol['value']:.2f}")
        print(f"  Raison: {sol['reason']}")
        print(f"  Implémentation: {sol['implementation']}")
        
        print("\nSOLUTION FALLBACK:")
        fb = rec['fallback_solution']
        print(f"  Métrique: {fb['metric']}")
        print(f"  Valeur: {fb['value']:.2f}")
        print(f"  Raison: {fb['reason']}")
        
        print(f"\nConfiance: {rec['confidence']}")
        
        print("=" * 80 + "\n")


# === TEST AVEC SNAPSHOTS FOURNIS ===
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Snapshot ES fourni
    snapshot_es = {
        "sym": "ESZ25_FUT_CME",
        "mid": 6870.13,
        "atr": 1.14,
        "vwap": 6885.21,
        "vwap_up1": 6895.28,
        "vwap_dn1": 6865.06,
        "vva": {"vah": 6894.75, "val": 6790.00, "vpoc": 6873.50},
        "1d_max": 6937.08,
        "1d_min": 6814.42,
        "total_range_ticks": 2.0,
        "spread": 0.25,
        "spread_ticks": 1,
        "volatility_regime": 1,
        "volatility_regime_cont": 0.136944,
        "day_range_pct": 0.716051,
        "progress01": 0.497917
    }
    
    # Snapshot NQ similaire (logs précédents)
    snapshot_nq = {
        "sym": "NQZ25_FUT_CME",
        "mid": 25378.0,
        "atr": 8.36,  # Anormal aussi?
        "vwap": 25336.73,
        "vwap_up1": 25380.46,
        "vwap_dn1": 25292.99,
        "vva": {"vah": 25465.00, "val": 25200.00, "vpoc": 25375.00},
        "1d_max": 25506.25,
        "1d_min": 25162.25,
        "total_range_ticks": 12.0,
        "spread": 0.25,
        "spread_ticks": 1,
        "volatility_regime": 2,
        "day_range_pct": 1.354,
        "progress01": 0.497
    }
    
    analyzer = ATRAlternativeAnalyzer()
    
    print("TEST 1: SNAPSHOT ES")
    analyzer.print_analysis(snapshot_es)
    
    print("\n\nTEST 2: SNAPSHOT NQ")
    analyzer.print_analysis(snapshot_nq)
    
    # Export JSON
    print("\n\nEXPORT JSON ES:")
    analysis_es = analyzer.analyze_snapshot(snapshot_es)
    print(json.dumps(analysis_es, indent=2, default=str))

