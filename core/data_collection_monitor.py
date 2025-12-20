#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MODULE MONITORING COLLECTE DE DONNÉES
=====================================
Affiche la progression de collecte des données pour les marchés en pré-production
Utilisé dans le dashboard pendant les phases où on ne trade pas encore un marché
"""

import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json

class DataCollectionMonitor:
    """Moniteur de collecte de données pour marchés en pré-production"""

    # Objectifs minimums pour training ML
    MIN_SAMPLES_TRAINING = 20000  # Samples minimum pour training
    RECOMMENDED_SAMPLES = 40000   # Samples recommandés
    MIN_DAYS_COLLECTION = 30      # Jours minimum de collecte

    # Configuration marchés
    MARKETS_CONFIG = {
        "ES": {
            "name": "E-mini S&P 500",
            "chart_id": 3,
            "status": "active_trading",
            "phase": "Phase 0 - Validation"
        },
        "NQ": {
            "name": "E-mini Nasdaq 100",
            "chart_id": 9,
            "status": "active_trading",
            "phase": "Phase 0 - Validation"
        },
        "GC": {
            "name": "Gold Futures",
            "chart_id": 11,
            "status": "collecting",
            "phase": "Phase 1 - Collecte"
        },
        "CL": {
            "name": "WTI Crude Oil",
            "chart_id": 13,
            "status": "collecting",
            "phase": "Phase 1 - Collecte"
        },
        "RTY": {
            "name": "E-mini Russell 2000",
            "chart_id": 1,
            "status": "collecting",
            "phase": "Phase 1 - Collecte Active"
        }
    }

    def __init__(self, base_path: str = "D:/MIA_IA_system/DATA_SIERRA_CHART"):
        self.base_path = Path(base_path)

    def get_collection_status(self, symbol: str, days_back: int = 30) -> Dict:
        """
        Récupère le statut de collecte pour un marché

        Returns:
            Dict avec:
            - total_samples: nombre total de samples collectés
            - days_collected: nombre de jours avec données
            - files_count: nombre de fichiers ML_READY
            - total_size_mb: taille totale en MB
            - avg_samples_per_day: moyenne samples/jour
            - completion_pct: % vers objectif training
            - status: "ready", "collecting", "insufficient"
            - next_milestone: prochain objectif
        """
        chart_id = self.MARKETS_CONFIG.get(symbol, {}).get("chart_id")
        if not chart_id:
            return self._empty_status(symbol)

        # Chercher les données des N derniers jours
        total_samples = 0
        days_with_data = 0
        files_found = []
        total_size_bytes = 0

        today = datetime.now()

        for days_ago in range(days_back):
            date = today - timedelta(days=days_ago)
            date_str = date.strftime("%Y%m%d")
            month_str = self._get_month_name(date.month)

            # Chemin ML_READY
            ml_ready_path = (
                self.base_path /
                f"DATA_{date.year}" /
                month_str /
                date_str /
                f"CHART_{chart_id}" /
                "ML_READY"
            )

            if ml_ready_path.exists():
                # Compter les fichiers .scid
                files = list(ml_ready_path.glob("*.scid"))
                if files:
                    days_with_data += 1
                    for f in files:
                        files_found.append(str(f))
                        total_size_bytes += f.stat().st_size
                        # Estimer samples (très approximatif: 1 sample ~= 500 bytes)
                        total_samples += f.stat().st_size // 500

        # Calculer métriques
        total_size_mb = total_size_bytes / (1024 * 1024)
        avg_samples_per_day = total_samples / days_with_data if days_with_data > 0 else 0
        completion_pct = (total_samples / self.MIN_SAMPLES_TRAINING) * 100

        # Déterminer statut
        if total_samples >= self.RECOMMENDED_SAMPLES and days_with_data >= self.MIN_DAYS_COLLECTION:
            status = "ready"
            next_milestone = "Training ML possible"
        elif total_samples >= self.MIN_SAMPLES_TRAINING:
            status = "minimum_reached"
            remaining = self.RECOMMENDED_SAMPLES - total_samples
            next_milestone = f"{remaining:,} samples pour niveau recommandé"
        else:
            status = "collecting"
            remaining = self.MIN_SAMPLES_TRAINING - total_samples
            next_milestone = f"{remaining:,} samples pour minimum training"

        # Estimer jours restants
        if avg_samples_per_day > 0 and status == "collecting":
            days_remaining = remaining / avg_samples_per_day
            eta_date = datetime.now() + timedelta(days=days_remaining)
            eta = eta_date.strftime("%Y-%m-%d")
        else:
            eta = "N/A"

        return {
            "symbol": symbol,
            "name": self.MARKETS_CONFIG[symbol]["name"],
            "chart_id": chart_id,
            "phase": self.MARKETS_CONFIG[symbol]["phase"],
            "total_samples": int(total_samples),
            "days_collected": days_with_data,
            "files_count": len(files_found),
            "total_size_mb": round(total_size_mb, 2),
            "avg_samples_per_day": int(avg_samples_per_day),
            "completion_pct": round(completion_pct, 1),
            "status": status,
            "next_milestone": next_milestone,
            "eta_ready": eta,
            "min_samples_target": self.MIN_SAMPLES_TRAINING,
            "recommended_target": self.RECOMMENDED_SAMPLES
        }

    def get_all_collecting_markets(self) -> List[Dict]:
        """Récupère le statut de tous les marchés en collecte"""
        results = []
        for symbol, config in self.MARKETS_CONFIG.items():
            if config["status"] == "collecting":
                status = self.get_collection_status(symbol)
                results.append(status)
        return results

    def get_summary(self) -> Dict:
        """Résumé global de la collecte"""
        collecting = self.get_all_collecting_markets()

        total_samples = sum(m["total_samples"] for m in collecting)
        total_size_mb = sum(m["total_size_mb"] for m in collecting)
        markets_ready = sum(1 for m in collecting if m["status"] == "ready")
        markets_collecting = len(collecting)

        return {
            "markets_collecting": markets_collecting,
            "markets_ready": markets_ready,
            "total_samples_collected": total_samples,
            "total_size_mb": round(total_size_mb, 2),
            "collection_active": markets_collecting > 0
        }

    def check_data_quality(self, symbol: str, date: datetime = None) -> Dict:
        """
        Vérifie la qualité des données collectées pour un jour donné

        Returns:
            - nan_count: nombre de NaN
            - gaps_detected: trous dans les données
            - duplicate_timestamps: timestamps dupliqués
            - quality_score: score qualité 0-100
        """
        if date is None:
            date = datetime.now()

        chart_id = self.MARKETS_CONFIG.get(symbol, {}).get("chart_id")
        if not chart_id:
            return {}

        date_str = date.strftime("%Y%m%d")
        month_str = self._get_month_name(date.month)

        ml_ready_path = (
            self.base_path /
            f"DATA_{date.year}" /
            month_str /
            date_str /
            f"CHART_{chart_id}" /
            "ML_READY"
        )

        if not ml_ready_path.exists():
            return {
                "date": date_str,
                "status": "no_data",
                "quality_score": 0
            }

        # Pour l'instant, score basique
        # TODO: Implémenter analyse détaillée des fichiers .scid
        files = list(ml_ready_path.glob("*.scid"))

        if not files:
            quality_score = 0
        else:
            # Score simplifié basé sur présence fichiers
            quality_score = 85  # Assume good quality if files exist

        return {
            "date": date_str,
            "files_found": len(files),
            "status": "ok" if files else "empty",
            "quality_score": quality_score,
            "note": "Analyse détaillée à implémenter"
        }

    def _empty_status(self, symbol: str) -> Dict:
        """Retourne un statut vide pour marché non configuré"""
        return {
            "symbol": symbol,
            "name": f"Unknown ({symbol})",
            "chart_id": None,
            "phase": "Unknown",
            "total_samples": 0,
            "days_collected": 0,
            "files_count": 0,
            "total_size_mb": 0.0,
            "avg_samples_per_day": 0,
            "completion_pct": 0.0,
            "status": "not_configured",
            "next_milestone": "Configuration requise",
            "eta_ready": "N/A"
        }

    def _get_month_name(self, month: int) -> str:
        """Retourne le nom du mois en français (uppercase)"""
        months = {
            1: "JANVIER", 2: "FEVRIER", 3: "MARS", 4: "AVRIL",
            5: "MAI", 6: "JUIN", 7: "JUILLET", 8: "AOUT",
            9: "SEPTEMBRE", 10: "OCTOBRE", 11: "NOVEMBRE", 12: "DECEMBRE"
        }
        return months.get(month, "JANVIER")


def create_collection_monitor(base_path: str = None) -> DataCollectionMonitor:
    """Factory function pour créer un moniteur de collecte"""
    if base_path is None:
        base_path = "D:/MIA_IA_system/DATA_SIERRA_CHART"
    return DataCollectionMonitor(base_path)


# Test standalone
if __name__ == "__main__":
    import sys
    import io

    # Force UTF-8 on Windows
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    monitor = create_collection_monitor()

    print("=" * 80)
    print("MONITORING COLLECTE DE DONNEES - MIA IA SYSTEM")
    print("=" * 80)

    # Résumé global
    summary = monitor.get_summary()
    print(f"\n[RESUME GLOBAL]")
    print(f"   Marches en collecte : {summary['markets_collecting']}")
    print(f"   Marches prets      : {summary['markets_ready']}")
    print(f"   Total samples      : {summary['total_samples_collected']:,}")
    print(f"   Taille totale      : {summary['total_size_mb']:.2f} MB")

    # Détail par marché
    print(f"\n[DETAIL PAR MARCHE]")
    for market_status in monitor.get_all_collecting_markets():
        print(f"\n   {market_status['symbol']} - {market_status['name']}")
        print(f"   |- Samples      : {market_status['total_samples']:,} / {market_status['min_samples_target']:,}")
        print(f"   |- Progression  : {market_status['completion_pct']:.1f}%")
        print(f"   |- Jours        : {market_status['days_collected']} jours")
        print(f"   |- Avg/jour     : {market_status['avg_samples_per_day']:,} samples")
        print(f"   |- Statut       : {market_status['status'].upper()}")
        print(f"   |- Prochain     : {market_status['next_milestone']}")
        print(f"   `- ETA Ready    : {market_status['eta_ready']}")

    print(f"\n" + "=" * 80)
