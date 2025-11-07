#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AUDIT DISCORD INTEGRATION - Phase 3.5
Vérifie que toutes les fonctions Discord sont bien appelées
"""

import sys
import io

# Fix encoding pour Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("=" * 80)
print("🔍 AUDIT DISCORD INTEGRATION - LAUNCH/launch_ml_v3_production.py")
print("=" * 80)
print()

# Lire le fichier
with open('LAUNCH/launch_ml_v3_production.py', 'r', encoding='utf-8') as f:
    content = f.read()

# ═══════════════════════════════════════════════════════════════
# 1️⃣ VÉRIFIER L'IMPORT
# ═══════════════════════════════════════════════════════════════
print("1️⃣ IMPORT DISCORD NOTIFIER")
if 'from monitoring.discord_notifier import create_discord_notifier' in content:
    print("   ✅ Import présent")
else:
    print("   ❌ Import MANQUANT")

print()

# ═══════════════════════════════════════════════════════════════
# 2️⃣ VÉRIFIER L'INITIALISATION
# ═══════════════════════════════════════════════════════════════
print("2️⃣ INITIALISATION DISCORD")
if 'self.discord = create_discord_notifier()' in content:
    print("   ✅ Initialisation présente")
else:
    print("   ❌ Initialisation MANQUANTE")

if 'PostMortemAnalyzer(discord_notifier=self.discord)' in content:
    print("   ✅ PostMortem avec Discord")
else:
    print("   ❌ PostMortem SANS Discord")

print()

# ═══════════════════════════════════════════════════════════════
# 3️⃣ VÉRIFIER MESSAGE DÉMARRAGE
# ═══════════════════════════════════════════════════════════════
print("3️⃣ MESSAGE DÉMARRAGE")
if '🚀 MIA BOT DÉMARRÉ - Phase 3.5' in content:
    print("   ✅ Message démarrage présent")
else:
    print("   ❌ Message démarrage MANQUANT")

print()

# ═══════════════════════════════════════════════════════════════
# 4️⃣ VÉRIFIER HEARTBEAT LOOP
# ═══════════════════════════════════════════════════════════════
print("4️⃣ HEARTBEAT DISCORD LOOP")
if 'async def _heartbeat_discord_loop' in content:
    print("   ✅ Fonction _heartbeat_discord_loop présente")
else:
    print("   ❌ Fonction MANQUANTE")

if 'heartbeat_task = asyncio.create_task(self._heartbeat_discord_loop())' in content:
    print("   ✅ Loop lancé dans run()")
else:
    print("   ❌ Loop NON lancé")

print()

# ═══════════════════════════════════════════════════════════════
# 5️⃣ VÉRIFIER NOTIFICATIONS TRADES
# ═══════════════════════════════════════════════════════════════
print("5️⃣ NOTIFICATIONS TRADES")

# Trade exécuté
if 'await self.discord.send_trade_executed(trade_data)' in content:
    print("   ✅ send_trade_executed() appelé")
else:
    print("   ❌ send_trade_executed() MANQUANT")

# Trade fermé
if 'await self.discord.send_trade_closed(trade_data)' in content:
    print("   ✅ send_trade_closed() appelé")
else:
    print("   ❌ send_trade_closed() MANQUANT")

print()

# ═══════════════════════════════════════════════════════════════
# 6️⃣ FONCTIONS DISCORD DISPONIBLES (dans discord_notifier.py)
# ═══════════════════════════════════════════════════════════════
print("6️⃣ FONCTIONS DISPONIBLES (discord_notifier.py)")
with open('monitoring/discord_notifier.py', 'r', encoding='utf-8') as f:
    discord_content = f.read()

fonctions_disponibles = [
    'send_trade_executed',
    'send_trade_closed',
    'send_daily_report',
    'send_custom_message',
    'send_error_log',
    'send_warning_log',
    'send_config_change_log',
    'send_audit_log',
    'send_backtest_result',
    'send_strategy_optimization',
    'send_ab_test_result',
    'send_trading_opportunity',
    'send_position_management_alert',
    'send_market_insight',
    'send_setup_confirmation',
    'send_live_dashboard'
]

for func in fonctions_disponibles:
    if f'async def {func}' in discord_content:
        print(f"   ✅ {func}")
    else:
        print(f"   ❌ {func} MANQUANT")

print()

# ═══════════════════════════════════════════════════════════════
# 7️⃣ RESTE À IMPLÉMENTER
# ═══════════════════════════════════════════════════════════════
print("7️⃣ RESTE À IMPLÉMENTER")
print()

reste = {
    'send_daily_report': {
        'status': '❌ NON APPELÉ',
        'description': 'Rapport quotidien (P&L, Win Rate, Profit Factor)',
        'priorite': '🟡 DISCORD 3',
        'localisation': 'Créer une fonction daily_summary() appelée à 23h59 EST'
    },
    'send_error_log / send_warning_log': {
        'status': '❌ NON APPELÉ',
        'description': 'Logs d\'erreurs/warnings critiques',
        'priorite': '🟡 DISCORD 2',
        'localisation': 'Exception handlers critiques, Safety Kill Switch'
    },
    'send_custom_message (Signals)': {
        'status': '❌ NON APPELÉ',
        'description': 'Alertes signaux acceptés/rejetés',
        'priorite': '🟡 DISCORD 2',
        'localisation': 'Après ML filter, après market context filter'
    },
    'send_custom_message (Kill Switch)': {
        'status': '❌ NON APPELÉ',
        'description': 'Alerte URGENTE Safety Kill Switch activé',
        'priorite': '🔴 CRITIQUE',
        'localisation': 'Ligne 1269 (kill_switch_state_changed)'
    }
}

for nom, info in reste.items():
    print(f"   {info['priorite']} {nom}")
    print(f"      Status: {info['status']}")
    print(f"      Description: {info['description']}")
    print(f"      Localisation: {info['localisation']}")
    print()

# ═══════════════════════════════════════════════════════════════
# 8️⃣ RÉSUMÉ
# ═══════════════════════════════════════════════════════════════
print("=" * 80)
print("📊 RÉSUMÉ AUDIT")
print("=" * 80)
print()

completions = {
    '✅ URGENT 5': 'Import + Init + Message démarrage + PostMortem Discord',
    '✅ URGENT 6': 'Heartbeat loop (5 min) avec uptime, positions, P&L, Kill Switch',
    '✅ DISCORD 1 (PARTIEL)': 'send_trade_executed() + send_trade_closed() implémentés',
    '❌ DISCORD 2': 'Alerts (Kill Switch, signals, errors) NON implémentés',
    '❌ DISCORD 3': 'Daily Summary NON implémenté',
    '⏸️ DISCORD 4': 'Améliorations (anti-spam, filtrage) à faire plus tard'
}

for statut, description in completions.items():
    print(f"   {statut}: {description}")

print()
print("=" * 80)
print("🎯 PROCHAINES ACTIONS")
print("=" * 80)
print()
print("1. 🔴 CRITIQUE: Ajouter alerte Kill Switch (ligne 1269)")
print("2. 🟡 IMPORTANT: Ajouter alerts signaux acceptés/rejetés")
print("3. 🟡 IMPORTANT: Créer fonction daily_summary() pour rapport 23h59")
print("4. 🟢 OPTIONNEL: Intégrer error_log/warning_log dans exceptions critiques")
print()
print("✅ ESTIMATION: 30-45 min pour compléter DISCORD 2-3")
print()
