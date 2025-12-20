#!/usr/bin/env python3
"""
ATR Anomaly Audit - Diagnostic Complet
Analyse le problème ATR = 1.14 au lieu de 5-10 pour ES

Sprint 5 - TODO Tasks 6a, 6b, 6c, 6d
Date: 13 Novembre 2025
"""

import logging
import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import deque, defaultdict
import numpy as np

logger = logging.getLogger(__name__)


class ATRAnomalyAuditor:
    """
    Audit ATR Anormal
    
    Objectif: Comprendre pourquoi ATR ES = 1.14 au lieu de 5-10
    
    Hypothèses:
    1. Sierra Chart envoie mauvaise valeur
    2. Calcul Python incorrect
    3. Unités différentes (points vs ticks?)
    4. Timeframe incorrect (1min au lieu de 5min?)
    5. Bug dans pipeline de données
    """
    
    def __init__(self):
        # Historique ATR par symbole
        self.atr_history = defaultdict(lambda: deque(maxlen=500))
        
        # Historique prix (pour calcul ATR manuel)
        self.price_history = defaultdict(lambda: deque(maxlen=100))
        
        # Statistiques ATR
        self.atr_stats = defaultdict(lambda: {
            'count': 0,
            'min': float('inf'),
            'max': float('-inf'),
            'mean': 0.0,
            'std': 0.0,
            'median': 0.0,
            'last_update': None
        })
        
        # Alertes ATR anormal
        self.anomalies = []
        
        # ATR attendu par symbole (référence)
        self.EXPECTED_ATR_RANGE = {
            'ES': (3.0, 15.0),   # Normal: 5-10 pts
            'NQ': (10.0, 50.0),  # Normal: 15-30 pts
            'RTY': (2.0, 10.0)   # Normal: 3-6 pts
        }
        
        logger.info("🔍 ATRAnomalyAuditor initialisé")
    
    def analyze_snapshot(self, snapshot: Dict) -> Dict:
        """
        Analyse snapshot pour anomalies ATR
        
        Args:
            snapshot: Données ML_READY
            
        Returns:
            Rapport d'analyse
        """
        # Extraire données
        sym = snapshot.get('sym', 'ES')
        if 'ES' in sym:
            symbol = 'ES'
        elif 'NQ' in sym:
            symbol = 'NQ'
        elif 'RTY' in sym or '2RTY' in sym:
            symbol = 'RTY'
        else:
            symbol = 'UNKNOWN'
        
        atr = snapshot.get('atr', 0)
        mid = snapshot.get('mid', 0)
        high = snapshot.get('high', 0)
        low = snapshot.get('low', 0)
        close = snapshot.get('close', 0)
        open_price = snapshot.get('open', 0)
        
        timestamp = datetime.now()
        
        # Ajouter à historique
        self.atr_history[symbol].append({
            'timestamp': timestamp,
            'atr': atr,
            'mid': mid,
            'high': high,
            'low': low,
            'close': close,
            'open': open_price
        })
        
        # Ajouter prix pour calcul manuel
        self.price_history[symbol].append({
            'timestamp': timestamp,
            'high': high,
            'low': low,
            'close': close
        })
        
        # Mise à jour stats
        self._update_stats(symbol, atr)
        
        # Détecter anomalie
        is_anomaly, reason = self._detect_anomaly(symbol, atr)
        
        # Calculer ATR manuel
        atr_manual = self._calculate_atr_manual(symbol)
        
        # Rapport
        report = {
            'symbol': symbol,
            'timestamp': timestamp.isoformat(),
            'atr_snapshot': atr,
            'atr_manual': atr_manual,
            'atr_expected_range': self.EXPECTED_ATR_RANGE.get(symbol, (0, 0)),
            'is_anomaly': is_anomaly,
            'anomaly_reason': reason,
            'atr_stats': self.atr_stats[symbol].copy(),
            'snapshot_data': {
                'mid': mid,
                'high': high,
                'low': low,
                'close': close,
                'open': open_price,
                'bar_range': high - low if high and low else 0
            }
        }
        
        # Logger si anomalie
        if is_anomaly:
            logger.warning(
                "🚨 ATR ANORMAL: %s ATR=%.2f (attendu: %.0f-%.0f) - %s",
                symbol,
                atr,
                self.EXPECTED_ATR_RANGE[symbol][0],
                self.EXPECTED_ATR_RANGE[symbol][1],
                reason
            )
            
            self.anomalies.append(report)
        
        return report
    
    def _update_stats(self, symbol: str, atr: float):
        """Update statistiques ATR"""
        stats = self.atr_stats[symbol]
        
        stats['count'] += 1
        stats['min'] = min(stats['min'], atr)
        stats['max'] = max(stats['max'], atr)
        stats['last_update'] = datetime.now()
        
        # Recalculer mean/std/median si assez de données
        if len(self.atr_history[symbol]) >= 10:
            atr_values = [d['atr'] for d in self.atr_history[symbol]]
            stats['mean'] = np.mean(atr_values)
            stats['std'] = np.std(atr_values)
            stats['median'] = np.median(atr_values)
    
    def _detect_anomaly(self, symbol: str, atr: float) -> tuple:
        """
        Détecte si ATR est anormal
        
        Returns:
            (is_anomaly, reason)
        """
        expected_min, expected_max = self.EXPECTED_ATR_RANGE.get(symbol, (0, 999))
        
        # Check range attendu
        if atr < expected_min:
            return True, f"ATR trop bas ({atr:.2f} < {expected_min})"
        
        if atr > expected_max:
            return True, f"ATR trop haut ({atr:.2f} > {expected_max})"
        
        # Check spike soudain (si assez d'historique)
        if len(self.atr_history[symbol]) >= 20:
            recent_median = np.median([d['atr'] for d in list(self.atr_history[symbol])[-20:]])
            
            if recent_median > 0:
                ratio = atr / recent_median
                
                if ratio > 3.0:
                    return True, f"Spike soudain ({ratio:.1f}x median récent)"
                elif ratio < 0.3:
                    return True, f"Chute soudaine ({ratio:.1f}x median récent)"
        
        return False, "OK"
    
    def _calculate_atr_manual(self, symbol: str, period: int = 14) -> Optional[float]:
        """
        Calcule ATR manuellement (14-period True Range)
        
        True Range = max(
            high - low,
            abs(high - previous_close),
            abs(low - previous_close)
        )
        
        ATR = Average(True Range, 14 periods)
        
        Args:
            symbol: ES/NQ/RTY
            period: Période ATR (default 14)
            
        Returns:
            ATR calculé ou None si pas assez de données
        """
        if len(self.price_history[symbol]) < period + 1:
            return None
        
        # Calculer True Range pour chaque barre
        true_ranges = []
        
        price_data = list(self.price_history[symbol])
        
        for i in range(1, len(price_data)):
            current = price_data[i]
            previous = price_data[i - 1]
            
            high = current['high']
            low = current['low']
            prev_close = previous['close']
            
            if not all([high, low, prev_close]):
                continue
            
            # True Range
            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            
            true_ranges.append(tr)
        
        # ATR = Moyenne des N derniers TR
        if len(true_ranges) >= period:
            atr_manual = np.mean(true_ranges[-period:])
            return atr_manual
        
        return None
    
    def get_diagnostic_report(self, symbol: str) -> Dict:
        """
        Génère rapport diagnostic complet
        
        Args:
            symbol: ES/NQ/RTY
            
        Returns:
            Rapport complet
        """
        if symbol not in self.atr_stats:
            return {'error': f'Pas de données pour {symbol}'}
        
        stats = self.atr_stats[symbol]
        
        # Anomalies récentes
        recent_anomalies = [
            a for a in self.anomalies
            if a['symbol'] == symbol
            and datetime.fromisoformat(a['timestamp']) > datetime.now() - timedelta(hours=1)
        ]
        
        # ATR manuel actuel
        atr_manual = self._calculate_atr_manual(symbol)
        
        # Dernière valeur snapshot
        last_snapshot_atr = None
        if self.atr_history[symbol]:
            last_snapshot_atr = self.atr_history[symbol][-1]['atr']
        
        report = {
            'symbol': symbol,
            'generated_at': datetime.now().isoformat(),
            'data_points_collected': stats['count'],
            
            # ATR Snapshot (Sierra Chart)
            'atr_from_snapshot': {
                'current': last_snapshot_atr,
                'min': stats['min'],
                'max': stats['max'],
                'mean': stats['mean'],
                'std': stats['std'],
                'median': stats['median']
            },
            
            # ATR Manuel (calculé Python)
            'atr_calculated_python': atr_manual,
            
            # Comparaison
            'comparison': {
                'expected_range': self.EXPECTED_ATR_RANGE.get(symbol, (0, 0)),
                'snapshot_vs_expected': 'ANOMALY' if last_snapshot_atr and (
                    last_snapshot_atr < self.EXPECTED_ATR_RANGE[symbol][0] or
                    last_snapshot_atr > self.EXPECTED_ATR_RANGE[symbol][1]
                ) else 'OK',
                'manual_vs_expected': 'ANOMALY' if atr_manual and (
                    atr_manual < self.EXPECTED_ATR_RANGE[symbol][0] or
                    atr_manual > self.EXPECTED_ATR_RANGE[symbol][1]
                ) else 'OK',
                'snapshot_vs_manual_diff': abs(last_snapshot_atr - atr_manual) if last_snapshot_atr and atr_manual else None
            },
            
            # Anomalies
            'anomalies_last_hour': len(recent_anomalies),
            'total_anomalies': len([a for a in self.anomalies if a['symbol'] == symbol]),
            
            # Conclusion
            'diagnosis': self._generate_diagnosis(symbol, last_snapshot_atr, atr_manual)
        }
        
        return report
    
    def _generate_diagnosis(
        self,
        symbol: str,
        atr_snapshot: Optional[float],
        atr_manual: Optional[float]
    ) -> Dict:
        """Génère diagnostic basé sur comparaison"""
        diagnosis = {
            'source_issue': None,
            'recommended_fix': None,
            'confidence': 'LOW'
        }
        
        if not atr_snapshot or not atr_manual:
            diagnosis['source_issue'] = "Données insuffisantes"
            diagnosis['confidence'] = 'LOW'
            return diagnosis
        
        expected_min, expected_max = self.EXPECTED_ATR_RANGE[symbol]
        
        # Cas 1: Snapshot ET Manual anormaux → Problème de données source (Sierra Chart)
        if atr_snapshot < expected_min and atr_manual < expected_min:
            diagnosis['source_issue'] = "Sierra Chart envoie ATR anormalement bas"
            diagnosis['recommended_fix'] = "Vérifier configuration Sierra Chart (timeframe, symbole, calcul ATR)"
            diagnosis['confidence'] = 'HIGH'
        
        # Cas 2: Snapshot anormal MAIS Manual OK → Problème de transmission
        elif atr_snapshot < expected_min and expected_min <= atr_manual <= expected_max:
            diagnosis['source_issue'] = "ATR snapshot incorrect mais calcul manuel OK"
            diagnosis['recommended_fix'] = "Utiliser ATR calculé Python au lieu de snapshot"
            diagnosis['confidence'] = 'HIGH'
        
        # Cas 3: Snapshot OK MAIS Manual anormal → Problème de calcul Python
        elif expected_min <= atr_snapshot <= expected_max and atr_manual < expected_min:
            diagnosis['source_issue'] = "Calcul ATR Python incorrect"
            diagnosis['recommended_fix'] = "Corriger algorithme calcul ATR Python"
            diagnosis['confidence'] = 'MEDIUM'
        
        # Cas 4: Tous deux OK
        elif expected_min <= atr_snapshot <= expected_max and expected_min <= atr_manual <= expected_max:
            diagnosis['source_issue'] = None
            diagnosis['recommended_fix'] = "Aucune action nécessaire"
            diagnosis['confidence'] = 'HIGH'
        
        else:
            diagnosis['source_issue'] = "Pattern non identifié"
            diagnosis['recommended_fix'] = "Analyse manuelle requise"
            diagnosis['confidence'] = 'LOW'
        
        return diagnosis
    
    def print_diagnostic_report(self, symbol: str):
        """Affiche rapport diagnostic formaté"""
        report = self.get_diagnostic_report(symbol)
        
        if 'error' in report:
            print(f"\n❌ {report['error']}")
            return
        
        print("\n" + "=" * 80)
        print(f"🔍 DIAGNOSTIC ATR ANOMALIE - {symbol}")
        print("=" * 80)
        
        print(f"\nDonnées collectées: {report['data_points_collected']}")
        print(f"Généré à: {report['generated_at']}")
        
        # ATR Snapshot
        print("\n📊 ATR DEPUIS SNAPSHOT (Sierra Chart):")
        snap = report['atr_from_snapshot']
        print(f"  Actuel: {snap['current']:.2f}")
        print(f"  Min: {snap['min']:.2f}, Max: {snap['max']:.2f}")
        print(f"  Mean: {snap['mean']:.2f}, Median: {snap['median']:.2f}, Std: {snap['std']:.2f}")
        
        # ATR Manuel
        print("\n🧮 ATR CALCULÉ PYTHON (14-period True Range):")
        if report['atr_calculated_python']:
            print(f"  {report['atr_calculated_python']:.2f}")
        else:
            print("  Données insuffisantes")
        
        # Comparaison
        print("\n⚖️ COMPARAISON:")
        comp = report['comparison']
        print(f"  Range attendu: {comp['expected_range'][0]:.0f} - {comp['expected_range'][1]:.0f}")
        print(f"  Snapshot vs Attendu: {comp['snapshot_vs_expected']}")
        print(f"  Manuel vs Attendu: {comp['manual_vs_expected']}")
        if comp['snapshot_vs_manual_diff']:
            print(f"  Diff Snapshot-Manuel: {comp['snapshot_vs_manual_diff']:.2f}")
        
        # Anomalies
        print(f"\n🚨 ANOMALIES:")
        print(f"  Dernière heure: {report['anomalies_last_hour']}")
        print(f"  Total: {report['total_anomalies']}")
        
        # Diagnostic
        print("\n💡 DIAGNOSTIC:")
        diag = report['diagnosis']
        print(f"  Problème: {diag['source_issue'] or 'Aucun'}")
        print(f"  Fix recommandé: {diag['recommended_fix']}")
        print(f"  Confiance: {diag['confidence']}")
        
        print("=" * 80 + "\n")


# === TEST AVEC SNAPSHOT FOURNI ===
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Snapshot fourni par l'utilisateur
    snapshot_user = {
        "t_ms": 1763031555432,
        "sym": "ESZ25_FUT_CME",
        "mid": 6870.13,
        "atr": 1.14,  # ❌ ANORMAL
        "high": 6870.50,
        "low": 6870.00,
        "close": 6870.50,
        "open": 6870.00,
        "vwap": 6885.21,
        "d_vwap_atr": -13.198913
    }
    
    # Créer auditor
    auditor = ATRAnomalyAuditor()
    
    print("📊 ANALYSE SNAPSHOT FOURNI...\n")
    
    # Simuler historique (ATR anormal persistant)
    for i in range(30):
        fake_snapshot = snapshot_user.copy()
        fake_snapshot['atr'] = 1.14 + np.random.randn() * 0.2  # ATR autour de 1.14
        fake_snapshot['high'] = 6870 + np.random.randn() * 3
        fake_snapshot['low'] = 6870 + np.random.randn() * 3 - 2
        fake_snapshot['close'] = 6870 + np.random.randn() * 2
        
        auditor.analyze_snapshot(fake_snapshot)
    
    # Diagnostic
    auditor.print_diagnostic_report('ES')
    
    # Export JSON
    report = auditor.get_diagnostic_report('ES')
    print("\nRAPPORT JSON:")
    print(json.dumps(report, indent=2, default=str))

