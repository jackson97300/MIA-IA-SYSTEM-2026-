#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analyse des trades ES depuis les messages Discord
"""
import sys
import re
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

def parse_discord_messages(text):
    """Parse les messages Discord et extrait les trades"""
    trades = []

    # Pattern pour TRADE OUVERT
    entry_pattern = r'TRADE OUVERT.*?📊\s+Scores Qualité\s+.*?Confluence:\s+([\d.]+).*?MenthorQ:\s+([\d.]+).*?OrderFlow:\s+([\d.]+).*?Context:\s+([\d.]+).*?Trade ID\s+(ES_\d+)'

    # Pattern pour TRADE FERMÉ
    exit_pattern = r'(💰|🩸)\s+TRADE FERMÉ — (WIN|LOSS).*?Trade:\s+\$([+-][\d.]+)\s+\(([+-][\d.]+)t\).*?Trade ID\s+N/A\s+.*?Confluence:\s+([\d.]+).*?MenthorQ:\s+([\d.]+).*?OrderFlow:\s+([\d.]+).*?Context:\s+([\d.]+)'

    # Extraire les entrées
    entries = {}
    for match in re.finditer(entry_pattern, text, re.DOTALL):
        confluence = float(match.group(1))
        menthorq = float(match.group(2))
        orderflow = float(match.group(3))
        context = float(match.group(4))
        trade_id = match.group(5)

        entries[trade_id] = {
            'confluence': confluence,
            'menthorq': menthorq,
            'orderflow': orderflow,
            'context': context
        }

    # Extraire les sorties
    for match in re.finditer(exit_pattern, text, re.DOTALL):
        result = match.group(2)  # WIN or LOSS
        pnl = float(match.group(3))
        ticks = float(match.group(4))
        confluence = float(match.group(5))
        menthorq = float(match.group(6))
        orderflow = float(match.group(7))
        context = float(match.group(8))

        trades.append({
            'result': result,
            'pnl': pnl,
            'ticks': ticks,
            'confluence': confluence,
            'menthorq': menthorq,
            'orderflow': orderflow,
            'context': context
        })

    return trades

def analyze_trades(trades):
    """Analyse statistique des trades"""

    wins = [t for t in trades if t['result'] == 'WIN']
    losses = [t for t in trades if t['result'] == 'LOSS']

    print("=" * 80)
    print("📊 ANALYSE TRADES ES - Session du 01/12/2025")
    print("=" * 80)
    print()

    # Stats globales
    print(f"✅ WINS: {len(wins)} trades")
    print(f"❌ LOSS: {len(losses)} trades")
    print(f"📈 Win Rate: {len(wins)/(len(wins)+len(losses))*100:.1f}%")
    print(f"💰 P&L Total: ${sum(t['pnl'] for t in trades):+,.2f}")
    print()

    # Moyennes par catégorie
    print("=" * 80)
    print("📊 MOYENNES DES SCORES")
    print("=" * 80)
    print()

    print("✅ TRADES GAGNANTS:")
    print(f"  🧩 Confluence:  {sum(t['confluence'] for t in wins)/len(wins):.2f}")
    print(f"  🎯 MenthorQ:    {sum(t['menthorq'] for t in wins)/len(wins):.2f}")
    print(f"  📊 OrderFlow:   {sum(t['orderflow'] for t in wins)/len(wins):.2f}")
    print(f"  🌍 Context:     {sum(t['context'] for t in wins)/len(wins):.2f}")
    print()

    print("❌ TRADES PERDANTS:")
    print(f"  🧩 Confluence:  {sum(t['confluence'] for t in losses)/len(losses):.2f}")
    print(f"  🎯 MenthorQ:    {sum(t['menthorq'] for t in losses)/len(losses):.2f}")
    print(f"  📊 OrderFlow:   {sum(t['orderflow'] for t in losses)/len(losses):.2f}")
    print(f"  🌍 Context:     {sum(t['context'] for t in losses)/len(losses):.2f}")
    print()

    # Analyse par ranges de scores
    print("=" * 80)
    print("🔍 ANALYSE PAR RANGES DE SCORES")
    print("=" * 80)
    print()

    # OrderFlow analysis (le plus critique!)
    print("📊 ORDERFLOW Analysis:")
    orderflow_ranges = [
        (0.00, 0.10, "Catastrophique"),
        (0.10, 0.15, "Très faible"),
        (0.15, 0.20, "Faible"),
        (0.20, 0.25, "Moyen"),
        (0.25, 0.30, "Bon"),
        (0.30, 1.00, "Excellent")
    ]

    for min_val, max_val, label in orderflow_ranges:
        range_trades = [t for t in trades if min_val <= t['orderflow'] < max_val]
        if range_trades:
            range_wins = [t for t in range_trades if t['result'] == 'WIN']
            wr = len(range_wins) / len(range_trades) * 100 if range_trades else 0
            avg_pnl = sum(t['pnl'] for t in range_trades) / len(range_trades)
            print(f"  [{min_val:.2f}-{max_val:.2f}] {label:15s}: {len(range_trades):2d} trades | WR: {wr:5.1f}% | Avg P&L: ${avg_pnl:+7.2f}")
    print()

    # MenthorQ analysis
    print("🎯 MENTHORQ Analysis:")
    menthorq_ranges = [
        (0.00, 0.50, "Faible"),
        (0.50, 0.60, "Moyen-Faible"),
        (0.60, 0.70, "Moyen"),
        (0.70, 0.80, "Bon"),
        (0.80, 0.90, "Excellent"),
        (0.90, 1.50, "Exceptionnel")
    ]

    for min_val, max_val, label in menthorq_ranges:
        range_trades = [t for t in trades if min_val <= t['menthorq'] < max_val]
        if range_trades:
            range_wins = [t for t in range_trades if t['result'] == 'WIN']
            wr = len(range_wins) / len(range_trades) * 100 if range_trades else 0
            avg_pnl = sum(t['pnl'] for t in range_trades) / len(range_trades)
            print(f"  [{min_val:.2f}-{max_val:.2f}] {label:15s}: {len(range_trades):2d} trades | WR: {wr:5.1f}% | Avg P&L: ${avg_pnl:+7.2f}")
    print()

    # Context analysis
    print("🌍 CONTEXT Analysis:")
    context_ranges = [
        (0.00, 0.12, "Très faible"),
        (0.12, 0.16, "Faible"),
        (0.16, 0.20, "Moyen"),
        (0.20, 0.25, "Bon"),
        (0.25, 1.00, "Excellent")
    ]

    for min_val, max_val, label in context_ranges:
        range_trades = [t for t in trades if min_val <= t['context'] < max_val]
        if range_trades:
            range_wins = [t for t in range_trades if t['result'] == 'WIN']
            wr = len(range_wins) / len(range_trades) * 100 if range_trades else 0
            avg_pnl = sum(t['pnl'] for t in range_trades) / len(range_trades)
            print(f"  [{min_val:.2f}-{max_val:.2f}] {label:15s}: {len(range_trades):2d} trades | WR: {wr:5.1f}% | Avg P&L: ${avg_pnl:+7.2f}")
    print()

    # Confluence analysis
    print("🧩 CONFLUENCE Analysis:")
    confluence_ranges = [
        (0.00, 0.80, "Faible"),
        (0.80, 0.95, "Moyen"),
        (0.95, 1.10, "Bon"),
        (1.10, 1.25, "Excellent"),
        (1.25, 2.00, "Exceptionnel")
    ]

    for min_val, max_val, label in confluence_ranges:
        range_trades = [t for t in trades if min_val <= t['confluence'] < max_val]
        if range_trades:
            range_wins = [t for t in range_trades if t['result'] == 'WIN']
            wr = len(range_wins) / len(range_trades) * 100 if range_trades else 0
            avg_pnl = sum(t['pnl'] for t in range_trades) / len(range_trades)
            print(f"  [{min_val:.2f}-{max_val:.2f}] {label:15s}: {len(range_trades):2d} trades | WR: {wr:5.1f}% | Avg P&L: ${avg_pnl:+7.2f}")
    print()

    # Pattern analysis: Combinaisons gagnantes vs perdantes
    print("=" * 80)
    print("🎯 PATTERNS GAGNANTS vs PERDANTS")
    print("=" * 80)
    print()

    # Trades avec OrderFlow < 0.15
    low_of = [t for t in trades if t['orderflow'] < 0.15]
    low_of_wins = [t for t in low_of if t['result'] == 'WIN']
    print(f"⚠️  OrderFlow < 0.15: {len(low_of)} trades | WR: {len(low_of_wins)/len(low_of)*100:.1f}% | P&L: ${sum(t['pnl'] for t in low_of):+.2f}")
    print(f"   → CE PATTERN EST-IL RENTABLE ? {'✅ OUI' if len(low_of_wins)/len(low_of) > 0.50 else '❌ NON'}")
    print()

    # Trades avec Context < 0.15
    low_ctx = [t for t in trades if t['context'] < 0.15]
    low_ctx_wins = [t for t in low_ctx if t['result'] == 'WIN']
    print(f"⚠️  Context < 0.15: {len(low_ctx)} trades | WR: {len(low_ctx_wins)/len(low_ctx)*100:.1f}% | P&L: ${sum(t['pnl'] for t in low_ctx):+.2f}")
    print(f"   → CE PATTERN EST-IL RENTABLE ? {'✅ OUI' if len(low_ctx_wins)/len(low_ctx) > 0.50 else '❌ NON'}")
    print()

    # Trades avec OrderFlow < 0.15 ET Context < 0.15
    low_both = [t for t in trades if t['orderflow'] < 0.15 and t['context'] < 0.15]
    low_both_wins = [t for t in low_both if t['result'] == 'WIN']
    if low_both:
        print(f"🔴 OrderFlow < 0.15 ET Context < 0.15: {len(low_both)} trades | WR: {len(low_both_wins)/len(low_both)*100:.1f}% | P&L: ${sum(t['pnl'] for t in low_both):+.2f}")
        print(f"   → CE PATTERN EST-IL RENTABLE ? {'✅ OUI' if len(low_both_wins)/len(low_both) > 0.50 else '❌ NON - À ÉVITER!'}")
        print()

    # Trades avec TOUS les layers bons
    good_all = [t for t in trades if t['orderflow'] >= 0.20 and t['context'] >= 0.16 and t['menthorq'] >= 0.65]
    good_all_wins = [t for t in good_all if t['result'] == 'WIN']
    if good_all:
        print(f"✅ TOUS layers bons (OF≥0.20, CTX≥0.16, MQ≥0.65): {len(good_all)} trades | WR: {len(good_all_wins)/len(good_all)*100:.1f}% | P&L: ${sum(t['pnl'] for t in good_all):+.2f}")
        print(f"   → PATTERN PREMIUM ! {'🚀' if len(good_all_wins)/len(good_all) > 0.70 else '✅'}")
        print()

    # Recommandations de seuils
    print("=" * 80)
    print("🎯 RECOMMANDATIONS DE SEUILS OPTIMAUX")
    print("=" * 80)
    print()

    # Calcul des seuils optimaux basés sur les données
    print("Analyse des seuils pour maximiser Win Rate ET P&L:")
    print()

    # Test différents seuils OrderFlow
    best_of_threshold = 0.0
    best_of_wr = 0.0
    best_of_pnl = 0.0

    for of_threshold in [0.08, 0.10, 0.12, 0.15, 0.18, 0.20, 0.22, 0.25]:
        filtered = [t for t in trades if t['orderflow'] >= of_threshold]
        if len(filtered) >= 10:  # Au moins 10 trades
            wins_filtered = [t for t in filtered if t['result'] == 'WIN']
            wr = len(wins_filtered) / len(filtered)
            pnl = sum(t['pnl'] for t in filtered)

            if wr > best_of_wr and pnl > 0:
                best_of_threshold = of_threshold
                best_of_wr = wr
                best_of_pnl = pnl

    print(f"📊 OrderFlow optimal: ≥ {best_of_threshold:.2f}")
    print(f"   → WR: {best_of_wr*100:.1f}% | P&L: ${best_of_pnl:+.2f} | Trades: {len([t for t in trades if t['orderflow'] >= best_of_threshold])}")
    print()

    # Test différents seuils Context
    best_ctx_threshold = 0.0
    best_ctx_wr = 0.0
    best_ctx_pnl = 0.0

    for ctx_threshold in [0.10, 0.12, 0.14, 0.16, 0.18, 0.20, 0.22]:
        filtered = [t for t in trades if t['context'] >= ctx_threshold]
        if len(filtered) >= 10:
            wins_filtered = [t for t in filtered if t['result'] == 'WIN']
            wr = len(wins_filtered) / len(filtered)
            pnl = sum(t['pnl'] for t in filtered)

            if wr > best_ctx_wr and pnl > 0:
                best_ctx_threshold = ctx_threshold
                best_ctx_wr = wr
                best_ctx_pnl = pnl

    print(f"🌍 Context optimal: ≥ {best_ctx_threshold:.2f}")
    print(f"   → WR: {best_ctx_wr*100:.1f}% | P&L: ${best_ctx_pnl:+.2f} | Trades: {len([t for t in trades if t['context'] >= best_ctx_threshold])}")
    print()

    # Test différents seuils MenthorQ
    best_mq_threshold = 0.0
    best_mq_wr = 0.0
    best_mq_pnl = 0.0

    for mq_threshold in [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80]:
        filtered = [t for t in trades if t['menthorq'] >= mq_threshold]
        if len(filtered) >= 10:
            wins_filtered = [t for t in filtered if t['result'] == 'WIN']
            wr = len(wins_filtered) / len(filtered)
            pnl = sum(t['pnl'] for t in filtered)

            if wr > best_mq_wr and pnl > 0:
                best_mq_threshold = mq_threshold
                best_mq_wr = wr
                best_mq_pnl = pnl

    print(f"🎯 MenthorQ optimal: ≥ {best_mq_threshold:.2f}")
    print(f"   → WR: {best_mq_wr*100:.1f}% | P&L: ${best_mq_pnl:+.2f} | Trades: {len([t for t in trades if t['menthorq'] >= best_mq_threshold])}")
    print()

    # Test avec TOUS les seuils optimaux combinés
    optimal_filtered = [t for t in trades if
                       t['orderflow'] >= best_of_threshold and
                       t['context'] >= best_ctx_threshold and
                       t['menthorq'] >= best_mq_threshold]

    if optimal_filtered:
        optimal_wins = [t for t in optimal_filtered if t['result'] == 'WIN']
        print("=" * 80)
        print("🚀 RÉSULTATS AVEC SEUILS OPTIMAUX COMBINÉS")
        print("=" * 80)
        print(f"Trades: {len(optimal_filtered)}")
        print(f"Win Rate: {len(optimal_wins)/len(optimal_filtered)*100:.1f}%")
        print(f"P&L Total: ${sum(t['pnl'] for t in optimal_filtered):+,.2f}")
        print(f"P&L Moyen: ${sum(t['pnl'] for t in optimal_filtered)/len(optimal_filtered):+.2f}")
        print()

    print("=" * 80)
    print("📝 CONFIGURATION RECOMMANDÉE pour config/unified_thresholds.py")
    print("=" * 80)
    print()
    print('"ES": {')
    print(f'    "layer1": {best_mq_threshold:.2f},  # MenthorQ')
    print(f'    "layer2": {best_of_threshold:.2f},  # OrderFlow')
    print(f'    "layer3": {best_ctx_threshold:.2f}   # Context')
    print('},')
    print()

if __name__ == "__main__":
    # Lire le contenu depuis stdin ou fichier
    import sys

    # Le texte Discord sera fourni en argument
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r', encoding='utf-8') as f:
            discord_text = f.read()
    else:
        print("Usage: python analyze_es_trades.py <discord_messages.txt>")
        print("Ou collez le texte Discord ci-dessous (Ctrl+D pour terminer):")
        discord_text = sys.stdin.read()

    trades = parse_discord_messages(discord_text)

    if not trades:
        print("❌ Aucun trade trouvé dans le texte fourni!")
        sys.exit(1)

    analyze_trades(trades)
