"""
unifier/unify_chart9_day.py
Unifie les fichiers du CHART 9 (NQ) pour une journée donnée.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, List
import numpy as np
import sys

# Réutiliser la logique existante depuis unify_chart2_day.py
from .unify_chart2_day import unify_chart2_day as unify_chart9_day_main


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="Dossier racine de la journée (…/YYYYMMDD)")
    ap.add_argument("--date", required=True, help="YYYYMMDD")
    ap.add_argument("--symbol", required=False, help="Symbole strict à garder (ex: ESZ25-CME ou NQZ25-CME)")
    ap.add_argument("--vwap_p95", type=float, required=False, help="Seuil p95 VWAP en % (defaut 0.10)")
    ap.add_argument("--vwap_p99", type=float, required=False, help="Seuil p99 VWAP en % (defaut 0.15)")
    ap.add_argument("--session_reset", type=float, required=False, help="Seuil reset session cum_delta (defaut 100.0)")
    args = ap.parse_args()
    return unify_chart9_day_main(Path(args.root), args.date, symbol=args.symbol)


if __name__ == "__main__":
    raise SystemExit(main())



