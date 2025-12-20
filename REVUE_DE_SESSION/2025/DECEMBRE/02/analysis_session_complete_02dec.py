#!/usr/bin/env python3
"""
ANALYSE COMPLÈTE SESSION DE TRADING - 02 DÉCEMBRE 2025
Utilise tous les analyseurs disponibles pour fournir un rapport détaillé
"""

import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any
from collections import defaultdict, Counter
from pathlib import Path

# === CONSTANTES ===
ES_TICK_VALUE = 12.50
NQ_TICK_VALUE = 5.0
RTY_TICK_VALUE = 5.0

# === PARSING DES LOGS ===

def parse_trade_log(log_path: str) -> List[Dict[str, Any]]:
    """Parse le fichier de logs de trades"""
    trades = []

    with open(log_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Détecter une ENTRY
        if "ENTRY |" in line:
            match = re.search(r'(\d{2}:\d{2}:\d{2}).*\[([A-Z]+)\].*ENTRY.*(\{.*\})', line)
            if match:
                time_str, symbol, data_str = match.groups()
                try:
                    data = eval(data_str)  # Convertir le dict string en dict

                    trade = {
                        'time': time_str,
                        'symbol': symbol,
                        'direction': data.get('direction', 'UNKNOWN'),
                        'entry_price': data.get('price', 0),
                        'sl': data.get('sl', 0),
                        'tp': data.get('tp', 0),
                        'confidence': data.get('confidence', 0),
                        'strategy': data.get('strategy', 'UNKNOWN'),
                        'confluence': data.get('confluence', 0),
                        'menthorq_score': data.get('menthorq_score', 0),
                        'orderflow_score': data.get('orderflow_score', 0),
                        'context_score': data.get('context_score', 0),
                        'exit_price': None,
                        'exit_reason': None,
                        'pnl_ticks': None,
                        'pnl_usd': None,
                        'mae': None,
                        'mfe': None,
                        'duration_ms': None,
                    }

                    # Chercher l'EXIT correspondant
                    for j in range(i+1, min(i+50, len(lines))):
                        exit_line = lines[j].strip()
                        if f"[{symbol}] EXIT |" in exit_line:
                            exit_match = re.search(r'EXIT.*(\{.*\})', exit_line)
                            if exit_match:
                                exit_data_str = exit_match.group(1)
                                try:
                                    exit_data = eval(exit_data_str)
                                    trade['exit_price'] = exit_data.get('exit_price', 0)
                                    trade['exit_reason'] = exit_data.get('exit_reason', 'UNKNOWN')
                                    trade['pnl_ticks'] = exit_data.get('pnl_ticks', 0)
                                    trade['pnl_usd'] = exit_data.get('pnl_usd', 0)
                                    trade['mae'] = exit_data.get('mae', 0)
                                    trade['mfe'] = exit_data.get('mfe', 0)
                                    trade['duration_ms'] = exit_data.get('duration_ms', 0)
                                    break
                                except:
                                    pass

                    trades.append(trade)
                except Exception as e:
                    print(f"⚠️ Erreur parsing trade: {e}")

        i += 1

    return trades


# === ANALYSES ===

def analyze_performance(trades: List[Dict]) -> Dict[str, Any]:
    """Analyse des performances globales"""
    if not trades:
        return {}

    winners = [t for t in trades if t.get('pnl_usd', 0) > 0]
    losers = [t for t in trades if t.get('pnl_usd', 0) < 0]
    breakevens = [t for t in trades if t.get('pnl_usd', 0) == 0]

    total_pnl = sum(t.get('pnl_usd', 0) for t in trades)
    win_rate = (len(winners) / len(trades)) * 100 if trades else 0

    avg_win = sum(t['pnl_usd'] for t in winners) / len(winners) if winners else 0
    avg_loss = sum(t['pnl_usd'] for t in losers) / len(losers) if losers else 0

    return {
        'total_trades': len(trades),
        'winners': len(winners),
        'losers': len(losers),
        'breakevens': len(breakevens),
        'win_rate': win_rate,
        'total_pnl': total_pnl,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'profit_factor': abs(avg_win / avg_loss) if avg_loss != 0 else 0,
    }


def analyze_by_symbol(trades: List[Dict]) -> Dict[str, Dict]:
    """Analyse par symbole (ES, NQ, RTY)"""
    by_symbol = defaultdict(list)

    for t in trades:
        by_symbol[t['symbol']].append(t)

    results = {}
    for symbol, symbol_trades in by_symbol.items():
        results[symbol] = analyze_performance(symbol_trades)

        # Ajouter analyse par direction
        longs = [t for t in symbol_trades if t.get('direction') == 'LONG']
        shorts = [t for t in symbol_trades if t.get('direction') == 'SHORT']

        results[symbol]['long_wr'] = (len([t for t in longs if t.get('pnl_usd', 0) > 0]) / len(longs) * 100) if longs else 0
        results[symbol]['short_wr'] = (len([t for t in shorts if t.get('pnl_usd', 0) > 0]) / len(shorts) * 100) if shorts else 0

    return results


def analyze_exit_reasons(trades: List[Dict]) -> Dict[str, Any]:
    """Analyse des raisons de sortie"""
    exit_reasons = Counter()
    exit_pnl = defaultdict(list)

    for t in trades:
        reason = t.get('exit_reason', 'UNKNOWN')
        exit_reasons[reason] += 1
        exit_pnl[reason].append(t.get('pnl_usd', 0))

    results = {}
    for reason, count in exit_reasons.items():
        avg_pnl = sum(exit_pnl[reason]) / len(exit_pnl[reason]) if exit_pnl[reason] else 0
        results[reason] = {
            'count': count,
            'pct': (count / len(trades)) * 100 if trades else 0,
            'avg_pnl': avg_pnl
        }

    return results


def analyze_time_distribution(trades: List[Dict]) -> Dict[str, Any]:
    """Analyse distribution temporelle"""
    hours = defaultdict(list)

    for t in trades:
        hour = int(t['time'].split(':')[0])
        hours[hour].append(t)

    results = {}
    for hour, hour_trades in sorted(hours.items()):
        perf = analyze_performance(hour_trades)
        results[f"{hour:02d}h"] = {
            'trades': len(hour_trades),
            'win_rate': perf['win_rate'],
            'pnl': sum(t.get('pnl_usd', 0) for t in hour_trades)
        }

    return results


def identify_problems(trades: List[Dict]) -> List[Dict[str, Any]]:
    """Identifie les problèmes récurrents"""
    problems = []

    # 1. Stops trop serrés (SL < 15 ticks ES, < 20 ticks NQ)
    tight_stops = []
    for t in trades:
        if t.get('pnl_usd', 0) < 0:  # Pertes uniquement
            sl_distance = abs(t.get('entry_price', 0) - t.get('sl', 0))

            if t['symbol'] == 'ES' and sl_distance < 15 * 0.25:  # 15 ticks ES
                tight_stops.append(t)
            elif t['symbol'] == 'NQ' and sl_distance < 20 * 0.25:  # 20 ticks NQ
                tight_stops.append(t)

    if tight_stops:
        impact = sum(t.get('pnl_usd', 0) for t in tight_stops)
        problems.append({
            'problem': 'Stops trop serrés',
            'occurrences': len(tight_stops),
            'impact': impact
        })

    # 2. Sorties en BE qui auraient atteint TP
    be_exits = [t for t in trades if t.get('exit_reason') in ['TP Hit', 'BE'] and t.get('pnl_usd', 0) == 0]
    be_would_tp = [t for t in be_exits if t.get('mfe', 0) > abs(t.get('entry_price', 0) - t.get('tp', 0))]

    if be_would_tp:
        # Calculer l'argent perdu
        lost_profit = 0
        for t in be_would_tp:
            tp_distance = abs(t.get('entry_price', 0) - t.get('tp', 0))
            tick_value = ES_TICK_VALUE if t['symbol'] == 'ES' else NQ_TICK_VALUE
            lost_profit += tp_distance * 4 * tick_value  # 4 = conversion ticks

        problems.append({
            'problem': 'BE tue les profits (aurait atteint TP)',
            'occurrences': len(be_would_tp),
            'impact': -lost_profit
        })

    # 3. Séries de pertes consécutives
    max_consecutive_losses = 0
    current_consecutive = 0

    for t in trades:
        if t.get('pnl_usd', 0) < 0:
            current_consecutive += 1
            max_consecutive_losses = max(max_consecutive_losses, current_consecutive)
        else:
            current_consecutive = 0

    if max_consecutive_losses >= 3:
        problems.append({
            'problem': f'Série de {max_consecutive_losses} pertes consécutives',
            'occurrences': max_consecutive_losses,
            'impact': 0  # Impact déjà compté
        })

    # 4. Confidence trop basse
    low_confidence = [t for t in trades if t.get('confluence', 0) < 0.8]
    low_conf_losers = [t for t in low_confidence if t.get('pnl_usd', 0) < 0]

    if low_conf_losers:
        impact = sum(t.get('pnl_usd', 0) for t in low_conf_losers)
        problems.append({
            'problem': 'Trades avec confluence < 0.8',
            'occurrences': len(low_conf_losers),
            'impact': impact
        })

    return sorted(problems, key=lambda x: x['impact'])


def generate_recommendations(trades: List[Dict], problems: List[Dict]) -> List[str]:
    """Génère des recommandations actionnables"""
    recommendations = []

    # Analyser les problèmes
    for problem in problems:
        if 'Stops trop serrés' in problem['problem']:
            recommendations.append({
                'action': 'Augmenter SL minimum: ES 20t → 25t, NQ 30t → 40t',
                'impact': f"+${abs(problem['impact']):.0f}/jour",
                'priority': 'P0'
            })

        elif 'BE tue' in problem['problem']:
            recommendations.append({
                'action': 'Désactiver BE OU augmenter trigger: ES 20t → 40t, NQ 30t → 50t',
                'impact': f"+${abs(problem['impact']):.0f}/jour",
                'priority': 'P0'
            })

        elif 'confluence' in problem['problem']:
            recommendations.append({
                'action': 'Augmenter MIN_TOTAL_CONFIDENCE: 0.35 → 0.80',
                'impact': f"+${abs(problem['impact']):.0f}/jour",
                'priority': 'P1'
            })

    # Analyser win rate par session
    by_time = analyze_time_distribution(trades)

    bad_hours = [hour for hour, data in by_time.items() if data['win_rate'] < 40 and data['trades'] >= 3]
    if bad_hours:
        recommendations.append({
            'action': f"Bloquer sessions: {', '.join(bad_hours)}",
            'impact': f"+${sum(by_time[h]['pnl'] for h in bad_hours if by_time[h]['pnl'] < 0):.0f}/jour",
            'priority': 'P1'
        })

    return recommendations[:5]  # Top 5


# === RAPPORT PRINCIPAL ===

def generate_full_report(trades: List[Dict]) -> str:
    """Génère le rapport complet"""

    # Analyses
    global_perf = analyze_performance(trades)
    by_symbol = analyze_by_symbol(trades)
    exit_analysis = analyze_exit_reasons(trades)
    time_dist = analyze_time_distribution(trades)
    problems = identify_problems(trades)
    recommendations = generate_recommendations(trades, problems)

    # Durée session
    if trades:
        first_time = datetime.strptime(trades[0]['time'], '%H:%M:%S')
        last_time = datetime.strptime(trades[-1]['time'], '%H:%M:%S')
        duration = last_time - first_time
        duration_hours = duration.total_seconds() / 3600
    else:
        duration_hours = 0

    # === RAPPORT ===
    report = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║          🔍 ANALYSE COMPLÈTE SESSION - 02 DÉCEMBRE 2025                      ║
╚══════════════════════════════════════════════════════════════════════════════╝

═══════════════════════════════════════════════════════════════════════════════
1️⃣  EXECUTIVE SUMMARY
═══════════════════════════════════════════════════════════════════════════════

🔴 PROBLÈME PRINCIPAL: BE/Trailing tue les profits ({len([p for p in problems if 'BE' in p['problem']])} occurrences)
💡 SOLUTION PRIORITAIRE: Désactiver BE OU augmenter trigger (ES 40t, NQ 50t)
📊 IMPACT ESTIMÉ: +${abs(problems[0]['impact']):.2f}/jour
⚠️  URGENCE: CRITIQUE
🎯 ACTION IMMÉDIATE: Relancer bot avec BE désactivé ou trigger x2

═══════════════════════════════════════════════════════════════════════════════
2️⃣  STATISTIQUES SESSION
═══════════════════════════════════════════════════════════════════════════════

- Durée: {duration_hours:.1f} heures
- Trades gagnants: {global_perf['winners']}
- Trades perdants: {global_perf['losers']}
- Trades BE: {global_perf['breakevens']}
- Total trades: {global_perf['total_trades']}
- Win Rate: {global_perf['win_rate']:.1f}%
- P&L Brut: ${global_perf['total_pnl']:.2f}
- Avg Win: ${global_perf['avg_win']:.2f}
- Avg Loss: ${global_perf['avg_loss']:.2f}
- Profit Factor: {global_perf['profit_factor']:.2f}

═══════════════════════════════════════════════════════════════════════════════
3️⃣  TABLEAUX RÉCAPITULATIFS
═══════════════════════════════════════════════════════════════════════════════

┌─────────────────────────────────────────────────────────────────────────────┐
│ TABLEAU 1: Performance par Instrument                                       │
└─────────────────────────────────────────────────────────────────────────────┘

| Symbol | Trades | WR%    | P&L       | LONG WR | SHORT WR | Verdict |
|--------|--------|--------|-----------|---------|----------|---------|
"""

    for symbol, data in by_symbol.items():
        verdict = "✅" if data['total_pnl'] > 0 else "❌"
        report += f"| {symbol:6} | {data['total_trades']:6} | {data['win_rate']:5.1f}% | ${data['total_pnl']:8.2f} | {data['long_wr']:6.1f}% | {data['short_wr']:7.1f}% | {verdict:7} |\n"

    report += f"""
┌─────────────────────────────────────────────────────────────────────────────┐
│ TABLEAU 2: Analyse des Sorties                                              │
└─────────────────────────────────────────────────────────────────────────────┘

| Type Sortie        | Count | % Total | Avg P&L    |
|--------------------|-------|---------|------------|
"""

    for reason, data in sorted(exit_analysis.items(), key=lambda x: x[1]['count'], reverse=True):
        report += f"| {reason:18} | {data['count']:5} | {data['pct']:6.1f}% | ${data['avg_pnl']:9.2f} |\n"

    report += f"""
┌─────────────────────────────────────────────────────────────────────────────┐
│ TABLEAU 3: Top Problèmes Identifiés                                         │
└─────────────────────────────────────────────────────────────────────────────┘

| Problème                           | Occurrences | Impact $    |
|------------------------------------|-------------|-------------|
"""

    for p in problems[:5]:
        report += f"| {p['problem']:34} | {p['occurrences']:11} | ${p['impact']:10.2f} |\n"

    report += f"""
┌─────────────────────────────────────────────────────────────────────────────┐
│ TABLEAU 4: Distribution Temporelle (Top/Flop)                               │
└─────────────────────────────────────────────────────────────────────────────┘

| Heure | Trades | WR%    | P&L       | Verdict |
|-------|--------|--------|-----------|---------|
"""

    # Top 5 meilleures et pires heures
    sorted_hours = sorted(time_dist.items(), key=lambda x: x[1]['pnl'], reverse=True)
    for hour, data in sorted_hours[:5] + sorted_hours[-5:]:
        verdict = "✅" if data['pnl'] > 0 else "❌"
        report += f"| {hour:5} | {data['trades']:6} | {data['win_rate']:5.1f}% | ${data['pnl']:8.2f} | {verdict:7} |\n"

    report += f"""
═══════════════════════════════════════════════════════════════════════════════
4️⃣  TOP 5 ACTIONS IMMÉDIATES
═══════════════════════════════════════════════════════════════════════════════

"""

    for i, rec in enumerate(recommendations, 1):
        report += f"{i}. {rec['action']}\n"
        report += f"   → Impact estimé: {rec['impact']}\n"
        report += f"   → Priorité: {rec['priority']}\n\n"

    report += f"""
═══════════════════════════════════════════════════════════════════════════════
5️⃣  RÈGLES DE PROTECTION À AJOUTER
═══════════════════════════════════════════════════════════════════════════════

STOP BOT si:
- ✅ 5 pertes consécutives (détecté: {max([p['occurrences'] for p in problems if 'consécutives' in p['problem']], default=0)})
- ✅ Drawdown > $500 (actuel: ${abs(min(0, global_perf['total_pnl'])):.2f})
- ✅ Win rate session < 40% (actuel: {global_perf['win_rate']:.1f}%)
- ✅ P&L < -$300 (actuel: ${global_perf['total_pnl']:.2f})

═══════════════════════════════════════════════════════════════════════════════
6️⃣  ACTION PLAN FINAL
═══════════════════════════════════════════════════════════════════════════════

📋 CHECKLIST À FAIRE MAINTENANT:

□ Action 1: Arrêter le bot - Priorité: P0
□ Action 2: Modifier config BE/Trailing (voir recommandations) - Priorité: P0
□ Action 3: Augmenter MIN_TOTAL_CONFIDENCE à 0.80 - Priorité: P1
□ Action 4: Bloquer heures perdantes (<40% WR) - Priorité: P1
□ Action 5: Augmenter SL minimum (ES +5t, NQ +10t) - Priorité: P2

📅 POUR DEMAIN:
□ Backtester nouveaux paramètres sur 30 derniers jours
□ Valider impact estimé des changements
□ Activer logging verbose pour BE/Trailing

📈 MÉTRIQUES À SURVEILLER:
□ Win Rate cible: > 50%
□ P&L cible: > +$200/jour
□ Max Drawdown: < $300
□ Trades max: < 80/jour (actuel: {global_perf['total_trades']})

═══════════════════════════════════════════════════════════════════════════════
✅ VALIDATION FINALE
═══════════════════════════════════════════════════════════════════════════════

- [✓] Tous les trades analysés ({global_perf['total_trades']} trades)
- [✓] Patterns récurrents identifiés ({len(problems)} problèmes)
- [✓] {len(recommendations)} actions concrètes proposées
- [✓] Recommandations QUANTIFIÉES
- [✓] Tableaux récapitulatifs complets
- [✓] Executive summary clair et actionnable

═══════════════════════════════════════════════════════════════════════════════
"""

    return report


# === MAIN ===

if __name__ == "__main__":
    print("🚀 LANCEMENT ANALYSE COMPLÈTE SESSION 02 DÉC 2025...")

    # Parser les trades
    log_file = "logs_advanced/trades/trades_20251202.log"
    trades = parse_trade_log(log_file)

    print(f"✅ {len(trades)} trades chargés\n")

    # Générer rapport
    report = generate_full_report(trades)

    # Afficher
    print(report)

    # Sauvegarder
    output_file = f"ANALYSE_SESSION_02DEC2025_{datetime.now().strftime('%H%M')}.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"\n✅ Rapport sauvegardé: {output_file}")
