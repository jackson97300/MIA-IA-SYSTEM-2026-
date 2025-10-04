"""
Quality package: calculs dérivés, nettoyages et validateurs pour la donnée Sierra/MentorQ.

Sous-modules:
- computations: VWAP, Cumulative Delta (recalculés depuis les trades)
- cleaners: dédoublonnage et filtres (quotes lock, etc.)
- validators: règles de qualité (gates) avant ingestion
"""

__all__ = [
    "computations",
    "cleaners",
    "validators",
]





