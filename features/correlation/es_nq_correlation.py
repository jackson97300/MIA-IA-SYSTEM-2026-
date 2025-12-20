"""
🔗 MODULE CORRÉLATION ES/NQ
============================

Analyse la corrélation en temps réel entre ES et NQ pour :
1. Confirmer les signaux (même direction = signal fort)
2. Détecter les divergences (directions opposées = danger)
3. Identifier le leader (NQ souvent en avance)

Date: 07/12/2025
"""

import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass, field
from collections import deque
import statistics

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

# Fenêtre de temps pour la corrélation (en millisecondes)
CORRELATION_WINDOW_MS = 60000  # 1 minute
SYNC_TOLERANCE_MS = 2000       # Tolérance de synchronisation (2 secondes)

# Seuils de corrélation
CORRELATION_THRESHOLDS = {
    'strong_positive': 0.80,   # Corrélation forte positive
    'moderate_positive': 0.50, # Corrélation modérée positive
    'neutral': 0.20,           # Zone neutre
    'divergence': -0.20,       # Divergence (attention!)
    'strong_divergence': -0.50 # Divergence forte (danger!)
}

# Seuils de confirmation
CONFIRMATION_THRESHOLDS = {
    'delta_alignment': 0.70,   # 70% du temps même signe de delta
    'direction_match': True,   # Même direction requise
    'min_samples': 10,         # Minimum d'échantillons
}

# ============================================================================
# CLASSES
# ============================================================================

@dataclass
class CorrelationSnapshot:
    """Snapshot synchronisé ES + NQ"""
    timestamp: int
    es_mid: float
    es_delta: float
    es_pressure: float
    nq_mid: float
    nq_delta: float
    nq_pressure: float


@dataclass
class CorrelationResult:
    """Résultat de l'analyse de corrélation"""
    timestamp: int

    # Corrélation calculée
    price_correlation: float      # Corrélation des prix
    delta_correlation: float      # Corrélation des deltas
    pressure_correlation: float   # Corrélation des pressures

    # Analyse
    delta_alignment: float        # % du temps où delta a même signe
    direction_es: str             # LONG, SHORT, NEUTRAL
    direction_nq: str             # LONG, SHORT, NEUTRAL
    directions_match: bool        # ES et NQ même direction ?

    # Signaux
    confirmation_signal: bool     # Signal confirmé ?
    divergence_warning: bool      # Divergence détectée ?
    leader: str                   # "ES", "NQ", ou "SYNC"
    leader_lag_ms: int            # Décalage en ms

    # Score final
    correlation_score: float      # Score 0-100
    recommendation: str           # "CONFIRM", "CAUTION", "AVOID"


@dataclass
class CorrelationStats:
    """Statistiques de corrélation sur une période"""
    samples: int = 0
    avg_price_corr: float = 0.0
    avg_delta_corr: float = 0.0
    confirmations: int = 0
    divergences: int = 0
    es_leads: int = 0
    nq_leads: int = 0
    synced: int = 0


# ============================================================================
# MODULE PRINCIPAL
# ============================================================================

class ESNQCorrelationModule:
    """
    Module de corrélation ES/NQ en temps réel.

    Utilise les snapshots ML pour analyser la corrélation et générer
    des signaux de confirmation ou d'avertissement de divergence.
    """

    def __init__(self, window_size: int = 60):
        """
        Args:
            window_size: Nombre de snapshots à garder en mémoire
        """
        self.window_size = window_size

        # Historique des snapshots synchronisés
        self.history: deque = deque(maxlen=window_size)

        # Dernier résultat
        self.last_result: Optional[CorrelationResult] = None

        # Statistiques
        self.stats = CorrelationStats()

        logger.info(f"🔗 ESNQCorrelationModule initialisé (window={window_size})")

    def update(self, es_snapshot: Dict, nq_snapshot: Dict) -> Optional[CorrelationResult]:
        """
        Met à jour avec de nouveaux snapshots ES et NQ.

        Args:
            es_snapshot: Snapshot ES (format ML_READY)
            nq_snapshot: Snapshot NQ (format ML_READY)

        Returns:
            CorrelationResult ou None si pas assez de données
        """
        # Vérifier synchronisation temporelle
        es_time = es_snapshot.get('t_ms', 0)
        nq_time = nq_snapshot.get('t_ms', 0)

        if abs(es_time - nq_time) > SYNC_TOLERANCE_MS:
            logger.debug(f"⚠️ Snapshots désynchronisés: ES={es_time}, NQ={nq_time}")
            return None

        # Créer snapshot synchronisé
        sync_snap = CorrelationSnapshot(
            timestamp=max(es_time, nq_time),
            es_mid=es_snapshot.get('mid', 0),
            es_delta=es_snapshot.get('delta', 0),
            es_pressure=es_snapshot.get('pressure_strength', 0),
            nq_mid=nq_snapshot.get('mid', 0),
            nq_delta=nq_snapshot.get('delta', 0),
            nq_pressure=nq_snapshot.get('pressure_strength', 0)
        )

        self.history.append(sync_snap)

        # Calculer corrélation si assez de données
        if len(self.history) < CONFIRMATION_THRESHOLDS['min_samples']:
            return None

        result = self._calculate_correlation()
        self.last_result = result
        self._update_stats(result)

        return result

    def _calculate_correlation(self) -> CorrelationResult:
        """Calcule la corrélation sur la fenêtre courante"""
        snaps = list(self.history)
        n = len(snaps)

        # Extraire les séries
        es_prices = [s.es_mid for s in snaps]
        nq_prices = [s.nq_mid for s in snaps]
        es_deltas = [s.es_delta for s in snaps]
        nq_deltas = [s.nq_delta for s in snaps]
        es_pressures = [s.es_pressure for s in snaps]
        nq_pressures = [s.nq_pressure for s in snaps]

        # Calculer les corrélations
        price_corr = self._pearson_correlation(es_prices, nq_prices)
        delta_corr = self._pearson_correlation(es_deltas, nq_deltas)
        pressure_corr = self._pearson_correlation(es_pressures, nq_pressures)

        # Alignement des deltas (même signe)
        same_sign = sum(1 for i in range(n) if (es_deltas[i] > 0) == (nq_deltas[i] > 0) and es_deltas[i] != 0 and nq_deltas[i] != 0)
        delta_alignment = same_sign / max(n, 1)

        # Directions actuelles
        last_es_delta = snaps[-1].es_delta
        last_nq_delta = snaps[-1].nq_delta

        direction_es = "LONG" if last_es_delta > 50 else ("SHORT" if last_es_delta < -50 else "NEUTRAL")
        direction_nq = "LONG" if last_nq_delta > 50 else ("SHORT" if last_nq_delta < -50 else "NEUTRAL")
        directions_match = direction_es == direction_nq and direction_es != "NEUTRAL"

        # Détecter le leader
        leader, lag = self._detect_leader(snaps)

        # Signaux
        confirmation = directions_match and delta_alignment >= CONFIRMATION_THRESHOLDS['delta_alignment']
        divergence = delta_corr < CORRELATION_THRESHOLDS['divergence'] or not directions_match

        # Score de corrélation (0-100)
        score = self._calculate_score(price_corr, delta_corr, delta_alignment, directions_match)

        # Recommandation
        if confirmation and score >= 70:
            recommendation = "CONFIRM"
        elif divergence or score < 40:
            recommendation = "AVOID"
        else:
            recommendation = "CAUTION"

        return CorrelationResult(
            timestamp=snaps[-1].timestamp,
            price_correlation=price_corr,
            delta_correlation=delta_corr,
            pressure_correlation=pressure_corr,
            delta_alignment=delta_alignment,
            direction_es=direction_es,
            direction_nq=direction_nq,
            directions_match=directions_match,
            confirmation_signal=confirmation,
            divergence_warning=divergence,
            leader=leader,
            leader_lag_ms=lag,
            correlation_score=score,
            recommendation=recommendation
        )

    def _pearson_correlation(self, x: List[float], y: List[float]) -> float:
        """Calcule la corrélation de Pearson"""
        n = len(x)
        if n < 2:
            return 0.0

        try:
            mean_x = statistics.mean(x)
            mean_y = statistics.mean(y)

            std_x = statistics.stdev(x)
            std_y = statistics.stdev(y)

            if std_x == 0 or std_y == 0:
                return 0.0

            covariance = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n)) / n
            correlation = covariance / (std_x * std_y)

            return max(-1, min(1, correlation))
        except:
            return 0.0

    def _detect_leader(self, snaps: List[CorrelationSnapshot]) -> Tuple[str, int]:
        """
        Détecte qui est le leader (ES ou NQ).

        Méthode: Cross-corrélation des deltas avec décalage.
        """
        if len(snaps) < 5:
            return "SYNC", 0

        es_deltas = [s.es_delta for s in snaps]
        nq_deltas = [s.nq_delta for s in snaps]

        # Tester différents décalages
        best_corr = 0
        best_lag = 0

        for lag in range(-3, 4):  # -3 à +3 échantillons
            if lag == 0:
                corr = self._pearson_correlation(es_deltas, nq_deltas)
            elif lag > 0:
                # NQ en avance (lag positif = NQ mène)
                corr = self._pearson_correlation(es_deltas[lag:], nq_deltas[:-lag])
            else:
                # ES en avance (lag négatif = ES mène)
                corr = self._pearson_correlation(es_deltas[:lag], nq_deltas[-lag:])

            if abs(corr) > abs(best_corr):
                best_corr = corr
                best_lag = lag

        # Estimer le décalage en ms (environ 1 seconde par échantillon)
        lag_ms = best_lag * 1000

        if best_lag > 0:
            return "NQ", lag_ms  # NQ mène
        elif best_lag < 0:
            return "ES", abs(lag_ms)  # ES mène
        else:
            return "SYNC", 0

    def _calculate_score(self, price_corr: float, delta_corr: float,
                         delta_alignment: float, directions_match: bool) -> float:
        """Calcule un score de corrélation 0-100"""
        score = 0

        # Corrélation prix (0-30 points)
        score += max(0, price_corr * 30)

        # Corrélation delta (0-30 points)
        score += max(0, delta_corr * 30)

        # Alignement delta (0-20 points)
        score += delta_alignment * 20

        # Directions matchent (0-20 points)
        if directions_match:
            score += 20

        return min(100, max(0, score))

    def _update_stats(self, result: CorrelationResult):
        """Met à jour les statistiques"""
        self.stats.samples += 1

        # Moyenne glissante
        alpha = 0.1
        self.stats.avg_price_corr = alpha * result.price_correlation + (1 - alpha) * self.stats.avg_price_corr
        self.stats.avg_delta_corr = alpha * result.delta_correlation + (1 - alpha) * self.stats.avg_delta_corr

        if result.confirmation_signal:
            self.stats.confirmations += 1
        if result.divergence_warning:
            self.stats.divergences += 1

        if result.leader == "ES":
            self.stats.es_leads += 1
        elif result.leader == "NQ":
            self.stats.nq_leads += 1
        else:
            self.stats.synced += 1

    def get_confirmation_for_signal(self, symbol: str, direction: str) -> Dict:
        """
        Vérifie si un signal est confirmé par la corrélation.

        Args:
            symbol: "ES" ou "NQ"
            direction: "LONG" ou "SHORT"

        Returns:
            Dict avec confirmation, score, et recommandation
        """
        if not self.last_result:
            return {
                'confirmed': False,
                'score': 0,
                'recommendation': 'NO_DATA',
                'reason': 'Pas assez de données de corrélation'
            }

        result = self.last_result

        # Vérifier si l'autre symbole est dans la même direction
        if symbol == "ES":
            other_direction = result.direction_nq
        else:
            other_direction = result.direction_es

        same_direction = other_direction == direction

        # Analyse
        if same_direction and result.correlation_score >= 70:
            return {
                'confirmed': True,
                'score': result.correlation_score,
                'recommendation': 'STRONG_CONFIRM',
                'reason': f'{symbol} {direction} confirmé par {"NQ" if symbol == "ES" else "ES"} (score={result.correlation_score:.0f})'
            }
        elif same_direction and result.correlation_score >= 50:
            return {
                'confirmed': True,
                'score': result.correlation_score,
                'recommendation': 'MODERATE_CONFIRM',
                'reason': f'Confirmation modérée (score={result.correlation_score:.0f})'
            }
        elif not same_direction and result.correlation_score < 40:
            return {
                'confirmed': False,
                'score': result.correlation_score,
                'recommendation': 'DIVERGENCE',
                'reason': f'⚠️ DIVERGENCE: {symbol}={direction} mais {"NQ" if symbol == "ES" else "ES"}={other_direction}'
            }
        else:
            return {
                'confirmed': False,
                'score': result.correlation_score,
                'recommendation': 'NEUTRAL',
                'reason': 'Corrélation neutre, pas de confirmation forte'
            }

    def get_stats_summary(self) -> str:
        """Retourne un résumé des statistiques"""
        if self.stats.samples == 0:
            return "Pas de données"

        return (
            f"📊 Corrélation ES/NQ:\n"
            f"   Samples: {self.stats.samples}\n"
            f"   Avg Price Corr: {self.stats.avg_price_corr:.2f}\n"
            f"   Avg Delta Corr: {self.stats.avg_delta_corr:.2f}\n"
            f"   Confirmations: {self.stats.confirmations} ({self.stats.confirmations/self.stats.samples*100:.1f}%)\n"
            f"   Divergences: {self.stats.divergences} ({self.stats.divergences/self.stats.samples*100:.1f}%)\n"
            f"   Leader: ES={self.stats.es_leads}, NQ={self.stats.nq_leads}, SYNC={self.stats.synced}"
        )


# ============================================================================
# FONCTIONS UTILITAIRES
# ============================================================================

def analyze_correlation_from_files(es_file: Path, nq_file: Path, limit: int = 1000) -> CorrelationStats:
    """
    Analyse la corrélation à partir de fichiers de snapshots.

    Args:
        es_file: Chemin vers le fichier ES ML_READY
        nq_file: Chemin vers le fichier NQ ML_READY
        limit: Nombre max de lignes à analyser

    Returns:
        CorrelationStats
    """
    module = ESNQCorrelationModule(window_size=60)

    # Charger les données
    es_snaps = []
    nq_snaps = []

    with open(es_file, 'r') as f:
        for i, line in enumerate(f):
            if i >= limit:
                break
            if line.strip():
                es_snaps.append(json.loads(line))

    with open(nq_file, 'r') as f:
        for i, line in enumerate(f):
            if i >= limit:
                break
            if line.strip():
                nq_snaps.append(json.loads(line))

    # Indexer par timestamp
    nq_by_time = {s.get('t_ms', 0): s for s in nq_snaps}

    # Analyser
    for es_snap in es_snaps:
        es_time = es_snap.get('t_ms', 0)

        # Trouver le NQ le plus proche
        closest_nq = None
        min_diff = float('inf')

        for nq_time, nq_snap in nq_by_time.items():
            diff = abs(es_time - nq_time)
            if diff < min_diff and diff <= SYNC_TOLERANCE_MS:
                min_diff = diff
                closest_nq = nq_snap

        if closest_nq:
            module.update(es_snap, closest_nq)

    return module.stats


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    # Test simple
    module = ESNQCorrelationModule()

    # Simuler des snapshots
    import random

    print("[CORRELATION] Test du module de correlation ES/NQ")
    print("="*60)

    base_time = 1700000000000

    for i in range(30):
        # Simuler une corrélation positive
        base_delta = random.uniform(-200, 200)

        es_snap = {
            't_ms': base_time + i * 1000,
            'mid': 6000 + i * 0.25,
            'delta': base_delta + random.uniform(-20, 20),
            'pressure_strength': random.uniform(0, 0.5)
        }

        nq_snap = {
            't_ms': base_time + i * 1000 + random.randint(-500, 500),
            'mid': 21000 + i * 0.75,
            'delta': base_delta * 1.2 + random.uniform(-30, 30),  # NQ plus volatile
            'pressure_strength': random.uniform(0, 0.5)
        }

        result = module.update(es_snap, nq_snap)

        if result:
            print(f"\n[RESULT] #{i}:")
            print(f"   Score: {result.correlation_score:.0f}")
            print(f"   ES: {result.direction_es} | NQ: {result.direction_nq}")
            print(f"   Match: {result.directions_match}")
            print(f"   Leader: {result.leader} ({result.leader_lag_ms}ms)")
            print(f"   Recommandation: {result.recommendation}")

    print("\n" + "="*60)
    print(module.get_stats_summary())
