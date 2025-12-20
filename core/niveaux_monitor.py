#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📊 MONITEUR NIVEAUX TEMPS RÉEL - MIA Trading Bot
=================================================

Script standalone qui tourne en parallèle du bot et logue:
- Niveaux tradables toutes les 10 secondes
- Alertes quand prix s'approche d'un niveau
- Résumé toutes les minutes

Lancer avec: python core/niveaux_monitor.py

Créé: 10/12/2025
Author: MIA System + Claude Sonnet 4.5
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import time
from datetime import datetime
from typing import Dict, List
from collections import defaultdict
import logging

# Import du data loader dynamique
from core.data_loader import find_latest_snapshot, validate_snapshot

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/niveaux_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════

SYMBOLS_CONFIG = {
    'ES': {
        'tick_size': 0.25,
        'max_distance': 15,
        'icon': '📗'
    },
    'NQ': {
        'tick_size': 0.25,
        'max_distance': 20,
        'icon': '📘'
    },
    'RTY': {
        'tick_size': 0.10,
        'max_distance': 15,
        'icon': '📕'
    }
}

CHECK_INTERVAL = 10  # secondes entre checks
ALERT_THRESHOLD = 5  # Distance en ticks pour alerte

# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

# find_latest_snapshot est maintenant importé de data_loader.py


def extract_all_levels(snapshot: Dict) -> List[tuple]:
    """Extrait tous les niveaux du snapshot"""
    levels = []

    if not snapshot:
        return levels

    # Mapping des niveaux à extraire
    level_mapping = {
        'hvl': 'HVL',
        'hvl_0dte': 'HVL_0DTE',
        'vah': 'VAH',
        'val': 'VAL',
        'poc': 'POC',
        '1d_max': '1D_MAX',
        '1d_min': '1D_MIN',
        'call_resistance_0dte': 'CR_0DTE',
        'put_support_0dte': 'PS_0DTE',
        'gamma_wall_0dte': 'GW_0DTE',
    }

    # Extraire niveaux uniques
    for key, name in level_mapping.items():
        if key in snapshot and snapshot[key]:
            levels.append((name, snapshot[key]))

    # GEX levels
    for i in range(1, 11):
        gex_key = f'gex_{i}'
        if gex_key in snapshot and snapshot[gex_key]:
            levels.append((f'GEX_{i}', snapshot[gex_key]))

    # Blind Spots - Snapshot: blind_spot_0 à blind_spot_8 → Affichage: BL 1 à BL 9
    for i in range(9):  # 0 à 8
        bs_key = f'blind_spot_{i}'
        if bs_key in snapshot and snapshot[bs_key]:
            levels.append((f'BL_{i+1}', snapshot[bs_key]))

    return levels


def calculate_distance(current_price: float, level_price: float, tick_size: float) -> float:
    """Calcule distance en ticks"""
    return abs(level_price - current_price) / tick_size


def analyze_symbol(symbol: str) -> Dict:
    """Analyse un symbole et retourne les niveaux tradables"""
    snapshot = find_latest_snapshot(symbol)

    if not snapshot:
        return {
            'symbol': symbol,
            'status': 'NO_DATA',
            'tradable': [],
            'alerts': []
        }

    current_price = snapshot.get('mid', 0)
    if current_price == 0:
        return {
            'symbol': symbol,
            'status': 'INVALID_PRICE',
            'tradable': [],
            'alerts': []
        }

    config = SYMBOLS_CONFIG[symbol]
    tick_size = config['tick_size']
    max_distance = config['max_distance']

    # Extraire tous les niveaux
    all_levels = extract_all_levels(snapshot)

    # Analyser chaque niveau
    tradable_levels = []
    alert_levels = []

    for level_name, level_price in all_levels:
        dist_ticks = calculate_distance(current_price, level_price, tick_size)

        # Niveau tradable
        if dist_ticks <= max_distance:
            tradable_levels.append({
                'name': level_name,
                'price': level_price,
                'distance': dist_ticks,
                'direction': 'UP' if level_price > current_price else 'DOWN'
            })

        # Alerte proximité
        if dist_ticks <= ALERT_THRESHOLD:
            alert_levels.append({
                'name': level_name,
                'price': level_price,
                'distance': dist_ticks,
                'direction': 'UP' if level_price > current_price else 'DOWN'
            })

    # Trier par distance
    tradable_levels.sort(key=lambda x: x['distance'])
    alert_levels.sort(key=lambda x: x['distance'])

    return {
        'symbol': symbol,
        'status': 'OK',
        'price': current_price,
        'tradable': tradable_levels,
        'alerts': alert_levels,
        'total_levels': len(all_levels)
    }


def log_analysis(analysis: Dict):
    """Logue l'analyse d'un symbole"""
    symbol = analysis['symbol']
    config = SYMBOLS_CONFIG[symbol]
    icon = config['icon']

    if analysis['status'] != 'OK':
        logger.warning(f"{icon} [{symbol}] Status: {analysis['status']}")
        return

    price = analysis['price']
    tradable_count = len(analysis['tradable'])
    alert_count = len(analysis['alerts'])

    # Log résumé
    logger.info(f"\n{'='*60}")
    logger.info(f"{icon} [{symbol}] Prix: {price:.2f}")
    logger.info(f"  Niveaux tradables: {tradable_count} (≤{config['max_distance']}t)")

    # Log niveaux tradables
    if tradable_count > 0:
        logger.info(f"  📍 TOP 5 NIVEAUX TRADABLES:")
        for level in analysis['tradable'][:5]:
            direction = "🔼" if level['direction'] == 'UP' else "🔽"
            logger.info(
                f"     {direction} {level['name']:15s} @ {level['price']:8.2f} "
                f"({level['distance']:5.1f}t)"
            )
    else:
        logger.info(f"  ⚠️  AUCUN niveau tradable actuellement")

    # Alertes proximité
    if alert_count > 0:
        logger.warning(f"  🔔 ALERTES PROXIMITÉ (≤{ALERT_THRESHOLD}t):")
        for level in analysis['alerts']:
            direction = "🔼" if level['direction'] == 'UP' else "🔽"
            logger.warning(
                f"     {direction} {level['name']:15s} @ {level['price']:8.2f} "
                f"({level['distance']:5.1f}t) ⚠️"
            )


def generate_summary(results: Dict):
    """Génère un résumé global"""
    logger.info(f"\n{'='*60}")
    logger.info("📊 RÉSUMÉ GLOBAL")
    logger.info(f"{'='*60}")

    for symbol in ['ES', 'NQ', 'RTY']:
        analysis = results.get(symbol, {})
        if analysis.get('status') == 'OK':
            icon = SYMBOLS_CONFIG[symbol]['icon']
            tradable = len(analysis.get('tradable', []))
            alerts = len(analysis.get('alerts', []))

            status_emoji = "✅" if tradable > 0 else "⚠️"
            logger.info(
                f"{icon} {symbol:3s} | Prix: {analysis['price']:8.2f} | "
                f"Tradables: {tradable:2d} | Alertes: {alerts:2d} {status_emoji}"
            )

    logger.info(f"{'='*60}\n")


# ═══════════════════════════════════════════════════════════════
# MAIN LOOP
# ═══════════════════════════════════════════════════════════════

def main():
    logger.info("="*60)
    logger.info("🚀 MONITEUR NIVEAUX TEMPS RÉEL - DÉMARRAGE")
    logger.info("="*60)
    logger.info(f"Check interval: {CHECK_INTERVAL}s")
    logger.info(f"Alert threshold: {ALERT_THRESHOLD} ticks")
    logger.info(f"Symboles: ES, NQ, RTY")
    logger.info("="*60)

    check_count = 0

    try:
        while True:
            check_count += 1

            # Analyser chaque symbole
            results = {}
            for symbol in ['ES', 'NQ', 'RTY']:
                analysis = analyze_symbol(symbol)
                results[symbol] = analysis
                log_analysis(analysis)

            # Résumé global toutes les 6 checks (1 minute si CHECK_INTERVAL=10)
            if check_count % 6 == 0:
                generate_summary(results)

            # Attendre avant prochain check
            time.sleep(CHECK_INTERVAL)

    except KeyboardInterrupt:
        logger.info("\n🛑 Arrêt du moniteur (Ctrl+C)")
    except Exception as e:
        logger.error(f"❌ Erreur fatale: {e}", exc_info=True)


if __name__ == "__main__":
    main()
