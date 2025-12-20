#!/usr/bin/env python3
"""
PERFORMANCE PROFILER - Profiler de performance pour optimiser les calculs
=======================================================================

Identifie les goulots d'étranglement dans les calculs des méthodes Elite.
Objectif : réduire les temps de calcul de 1458ms à <100ms.

Version: 1.0.0
Date: Janvier 2025
"""

import time
import functools
import sys
import os
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
import json

@dataclass
class PerformanceMetric:
    """Métrique de performance"""
    function_name: str
    execution_time_ms: float
    call_count: int = 1
    min_time_ms: float = 0.0
    max_time_ms: float = 0.0
    avg_time_ms: float = 0.0
    last_called: float = 0.0

class PerformanceProfiler:
    """
    Profiler de performance pour optimiser les calculs

    Fonctionnalités :
    - Mesure des temps d'exécution
    - Identification des goulots
    - Statistiques détaillées
    - Export des rapports
    """

    def __init__(self, enabled: bool = True):
        """Initialisation du profiler"""
        self.enabled = enabled
        self.metrics: Dict[str, PerformanceMetric] = {}
        self.start_time = time.time()
        self.total_calls = 0
        self.active_timers: Dict[str, float] = {}  # {timer_name: start_time}
        self.timings: Dict[str, List[float]] = {}  # 🔧 FIX 27/11: Ajout attribut manquant

        print("⚡ Performance Profiler initialisé")

    def profile_function(self, func_name: str = None):
        """Décorateur pour profiler une fonction"""
        def decorator(func: Callable) -> Callable:
            name = func_name or f"{func.__module__}.{func.__name__}"

            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                if not self.enabled:
                    return func(*args, **kwargs)

                start_time = time.perf_counter()
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    end_time = time.perf_counter()
                    execution_time_ms = (end_time - start_time) * 1000
                    self._record_metric(name, execution_time_ms)

            return wrapper
        return decorator

    def profile_method(self, method_name: str = None):
        """Décorateur pour profiler une méthode de classe"""
        def decorator(func: Callable) -> Callable:
            name = method_name or f"{func.__self__.__class__.__name__}.{func.__name__}"

            @functools.wraps(func)
            def wrapper(self, *args, **kwargs):
                if not self.enabled:
                    return func(self, *args, **kwargs)

                start_time = time.perf_counter()
                try:
                    result = func(self, *args, **kwargs)
                    return result
                finally:
                    end_time = time.perf_counter()
                    execution_time_ms = (end_time - start_time) * 1000
                    self._record_metric(name, execution_time_ms)

            return wrapper
        return decorator

    def _record_metric(self, function_name: str, execution_time_ms: float):
        """Enregistre une métrique"""
        if function_name not in self.metrics:
            self.metrics[function_name] = PerformanceMetric(
                function_name=function_name,
                execution_time_ms=execution_time_ms,
                min_time_ms=execution_time_ms,
                max_time_ms=execution_time_ms,
                avg_time_ms=execution_time_ms,
                last_called=time.time()
            )
        else:
            metric = self.metrics[function_name]
            metric.call_count += 1
            metric.execution_time_ms += execution_time_ms
            metric.min_time_ms = min(metric.min_time_ms, execution_time_ms)
            metric.max_time_ms = max(metric.max_time_ms, execution_time_ms)
            metric.avg_time_ms = metric.execution_time_ms / metric.call_count
            metric.last_called = time.time()

        self.total_calls += 1

    def get_slowest_functions(self, limit: int = 10) -> List[PerformanceMetric]:
        """Retourne les fonctions les plus lentes"""
        sorted_metrics = sorted(
            self.metrics.values(),
            key=lambda x: x.avg_time_ms,
            reverse=True
        )
        return sorted_metrics[:limit]

    def get_total_time(self) -> float:
        """Retourne le temps total d'exécution"""
        return sum(metric.execution_time_ms for metric in self.metrics.values())

    def get_bottlenecks(self, threshold_ms: float = 50.0) -> List[PerformanceMetric]:
        """Identifie les goulots d'étranglement"""
        return [
            metric for metric in self.metrics.values()
            if metric.avg_time_ms > threshold_ms
        ]

    def print_summary(self):
        """Affiche un résumé des performances"""
        if not self.metrics:
            print("📊 Aucune métrique enregistrée")
            return

        print("\n" + "="*60)
        print("📊 RÉSUMÉ DES PERFORMANCES")
        print("="*60)

        total_time = self.get_total_time()
        print(f"⏱️  Temps total: {total_time:.1f}ms")
        print(f"📞 Appels total: {self.total_calls}")
        print(f"🔄 Fonctions profilées: {len(self.metrics)}")

        # Top 5 des plus lentes
        slowest = self.get_slowest_functions(5)
        print(f"\n🐌 TOP 5 DES PLUS LENTES:")
        for i, metric in enumerate(slowest, 1):
            print(f"   {i}. {metric.function_name}: {metric.avg_time_ms:.1f}ms (avg) | {metric.max_time_ms:.1f}ms (max) | {metric.call_count} appels")

        # Goulots d'étranglement
        bottlenecks = self.get_bottlenecks(50.0)
        if bottlenecks:
            print(f"\n⚠️  GOULOTS D'ÉTRANGLEMENT (>50ms):")
            for metric in bottlenecks:
                print(f"   - {metric.function_name}: {metric.avg_time_ms:.1f}ms (avg)")

        print("="*60)

    def export_report(self, filename: str = None):
        """Exporte un rapport détaillé"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"performance_report_{timestamp}.json"

        report = {
            "timestamp": datetime.now().isoformat(),
            "total_time_ms": self.get_total_time(),
            "total_calls": self.total_calls,
            "functions_count": len(self.metrics),
            "metrics": {
                name: {
                    "execution_time_ms": metric.execution_time_ms,
                    "call_count": metric.call_count,
                    "min_time_ms": metric.min_time_ms,
                    "max_time_ms": metric.max_time_ms,
                    "avg_time_ms": metric.avg_time_ms,
                    "last_called": metric.last_called
                }
                for name, metric in self.metrics.items()
            },
            "slowest_functions": [
                {
                    "function_name": metric.function_name,
                    "avg_time_ms": metric.avg_time_ms,
                    "max_time_ms": metric.max_time_ms,
                    "call_count": metric.call_count
                }
                for metric in self.get_slowest_functions(10)
            ],
            "bottlenecks": [
                {
                    "function_name": metric.function_name,
                    "avg_time_ms": metric.avg_time_ms,
                    "call_count": metric.call_count
                }
                for metric in self.get_bottlenecks(50.0)
            ]
        }

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"📄 Rapport exporté: {filename}")
        return filename

    def start_timer(self, timer_name: str):
        """Démarre un timer manuel"""
        if not self.enabled:
            return
        self.active_timers[timer_name] = time.perf_counter()

    def end_timer(self, timer_name: str):
        """Arrête un timer manuel et enregistre la métrique"""
        if not self.enabled:
            return
        if timer_name not in self.active_timers:
            return

        start_time = self.active_timers.pop(timer_name)
        end_time = time.perf_counter()
        execution_time_ms = (end_time - start_time) * 1000
        self._record_metric(timer_name, execution_time_ms)

        # 🔧 FIX 27/11: Aussi stocker dans timings pour compatibilité
        if timer_name not in self.timings:
            self.timings[timer_name] = []
        self.timings[timer_name].append(execution_time_ms)

    def reset(self):
        """Remet à zéro les métriques"""
        self.metrics.clear()
        self.start_time = time.time()
        self.total_calls = 0
        self.active_timers.clear()
        print("🔄 Profiler remis à zéro")

# Instance globale du profiler
global_profiler = PerformanceProfiler()

def profile_function(func_name: str = None):
    """Décorateur global pour profiler une fonction"""
    return global_profiler.profile_function(func_name)

def profile_method(method_name: str = None):
    """Décorateur global pour profiler une méthode"""
    return global_profiler.profile_method(method_name)

def get_profiler() -> PerformanceProfiler:
    """Retourne l'instance globale du profiler"""
    return global_profiler

if __name__ == "__main__":
    # Test du profiler
    print("🧪 Test Performance Profiler...")

    profiler = PerformanceProfiler()

    # Test avec des fonctions simulées
    @profiler.profile_function("test_fast_function")
    def fast_function():
        time.sleep(0.001)  # 1ms
        return "fast"

    @profiler.profile_function("test_slow_function")
    def slow_function():
        time.sleep(0.1)  # 100ms
        return "slow"

    # Exécuter les fonctions
    for _ in range(5):
        fast_function()
        slow_function()

    # Afficher le résumé
    profiler.print_summary()

    # Exporter le rapport
    profiler.export_report("test_performance_report.json")

    print("✅ Test Performance Profiler terminé")
