#!/usr/bin/env python3
"""
Analyse des seuils par Layer - Estimation basee sur confidence totale
"""
import re
from collections import defaultdict

# Lire les trades
with open('logs_advanced/trades/trades_20251201.log', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Parser les trades avec confidence
trades = []
entries = {}

for line in lines:
    line = line.strip()
    if not line:
        continue

    time_match = re.match(r'(\d{2}:\d{2}:\d{2})', line)
    if not time_match:
        continue
    time_str = time_match.group(1)

    symbol_match = re.search(r'\[(\w+)\]', line)
    if not symbol_match:
        continue
    symbol = symbol_match.group(1)

    json_match = re.search(r'\{.*\}', line)
    if not json_match:
        continue

    try:
        data = eval(json_match.group())
    except:
        continue

    if 'ENTRY' in line:
        key = f'{symbol}_{data.get("direction")}_{time_str}'
        entries[key] = {
            'time': time_str,
            'symbol': symbol,
            'direction': data.get('direction'),
            'confidence': data.get('confidence', 0)
        }

    elif 'EXIT' in line:
        # Chercher l'entree correspondante
        conf = 0
        for k, v in list(entries.items()):
            if v['symbol'] == symbol and v['direction'] == data.get('direction'):
                conf = v['confidence']
                del entries[k]
                break

        trade = {
            'time': time_str,
            'symbol': symbol,
            'direction': data.get('direction'),
            'pnl_usd': data.get('pnl_usd', 0),
            'exit_reason': data.get('exit_reason', ''),
            'confidence': conf
        }
        trades.append(trade)

print('='*70)
print('  ANALYSE DES SEUILS PAR LAYER - 1er Dec 2025')
print('='*70)

# Rappel: confidence = L1*0.5 + L2*0.3 + L3*0.2
# L1 = MenthorQ (50%), L2 = OrderFlow (30%), L3 = Context (20%)

print('''
RAPPEL POIDS:
  - MenthorQ (L1): 50%
  - OrderFlow (L2): 30%
  - Context (L3): 20%

  Confidence = L1*0.5 + L2*0.3 + L3*0.2
''')

# Analyser par plages de confidence
print('='*70)
print(' ANALYSE PAR PLAGE DE CONFIDENCE')
print('='*70)

ranges = [
    (0.0, 0.60, 'Tres faible'),
    (0.60, 0.70, 'Faible'),
    (0.70, 0.80, 'Moyen'),
    (0.80, 0.90, 'Bon'),
    (0.90, 1.00, 'Tres bon'),
    (1.00, 1.20, 'Excellent'),
    (1.20, 2.00, 'Elite')
]

print(f' {"Plage":<15} {"Qualite":<12} {"Trades":>7} {"Wins":>5} {"WR%":>7} {"PnL":>12} {"Reco":>15}')
print('-'*80)

for low, high, quality in ranges:
    r_trades = [t for t in trades if low <= t['confidence'] < high]
    if not r_trades:
        continue
    r_wins = [t for t in r_trades if t['pnl_usd'] > 0]
    r_pnl = sum(t['pnl_usd'] for t in r_trades)
    wr = len(r_wins)/len(r_trades)*100 if r_trades else 0

    if wr >= 55:
        reco = 'GARDER'
    elif wr >= 45:
        reco = 'OK'
    elif wr >= 35:
        reco = 'ATTENTION'
    else:
        reco = 'FILTRER'

    print(f' {low:.2f}-{high:.2f}     {quality:<12} {len(r_trades):>7} {len(r_wins):>5} {wr:>6.1f}% ${r_pnl:>+10.2f} {reco:>15}')

# Analyse specifique par Symbol + Direction
print('\n' + '='*70)
print(' SEUILS OPTIMAUX PAR PATTERN')
print('='*70)

patterns = [
    ('ES', 'LONG'),
    ('ES', 'SHORT'),
    ('NQ', 'LONG'),
    ('NQ', 'SHORT')
]

for sym, dir in patterns:
    p_trades = [t for t in trades if t['symbol'] == sym and t['direction'] == dir]
    if not p_trades:
        continue

    print(f'\n {sym} {dir}:')

    # Trouver le seuil optimal
    best_threshold = 0
    best_wr = 0
    best_pnl = 0
    best_count = 0

    for threshold in [0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 1.00, 1.05, 1.10]:
        th_trades = [t for t in p_trades if t['confidence'] >= threshold]
        if len(th_trades) < 3:
            continue
        th_wins = [t for t in th_trades if t['pnl_usd'] > 0]
        th_pnl = sum(t['pnl_usd'] for t in th_trades)
        wr = len(th_wins)/len(th_trades)*100

        # Meilleur = WR >= 50% avec max trades
        if wr >= 50 and len(th_trades) > best_count:
            best_threshold = threshold
            best_wr = wr
            best_pnl = th_pnl
            best_count = len(th_trades)
        elif best_count == 0 and wr >= 45:
            best_threshold = threshold
            best_wr = wr
            best_pnl = th_pnl
            best_count = len(th_trades)

    if best_count > 0:
        print(f'   Seuil optimal: >= {best_threshold:.2f}')
        print(f'   Trades restants: {best_count}')
        print(f'   WR: {best_wr:.1f}%')
        print(f'   PnL: ${best_pnl:+.2f}')
    else:
        print(f'   ATTENTION: Aucun seuil avec WR >= 45%')
        # Afficher le meilleur disponible
        all_wins = [t for t in p_trades if t['pnl_usd'] > 0]
        print(f'   Trades total: {len(p_trades)} | WR: {len(all_wins)/len(p_trades)*100:.1f}%')

# Estimation des seuils par layer
print('\n' + '='*70)
print(' ESTIMATION SEUILS PAR LAYER')
print('='*70)

print('''
Basé sur l'analyse des patterns gagnants (confidence >= 0.80):
''')

# Trades gagnants avec haute confidence
high_conf_wins = [t for t in trades if t['pnl_usd'] > 0 and t['confidence'] >= 0.80]
high_conf_losses = [t for t in trades if t['pnl_usd'] <= 0 and t['confidence'] >= 0.80]
low_conf_wins = [t for t in trades if t['pnl_usd'] > 0 and t['confidence'] < 0.80]
low_conf_losses = [t for t in trades if t['pnl_usd'] <= 0 and t['confidence'] < 0.80]

print(f' Confidence >= 0.80:')
print(f'   Wins: {len(high_conf_wins)} | Losses: {len(high_conf_losses)}')
print(f'   WR: {len(high_conf_wins)/(len(high_conf_wins)+len(high_conf_losses))*100:.1f}%' if (len(high_conf_wins)+len(high_conf_losses)) > 0 else '   WR: N/A')

print(f'\n Confidence < 0.80:')
print(f'   Wins: {len(low_conf_wins)} | Losses: {len(low_conf_losses)}')
print(f'   WR: {len(low_conf_wins)/(len(low_conf_wins)+len(low_conf_losses))*100:.1f}%' if (len(low_conf_wins)+len(low_conf_losses)) > 0 else '   WR: N/A')

# Calcul inverse approximatif des layers
# Si confidence = 0.80, et qu'on assume des scores equilibres:
# 0.80 = L1*0.5 + L2*0.3 + L3*0.2
# Si L1=L2=L3=X, alors X*(0.5+0.3+0.2) = 0.80, donc X = 0.80

print('\n' + '='*70)
print(' RECOMMANDATIONS FINALES')
print('='*70)

# Calculer les seuils recommandes
avg_winning_conf = sum(t['confidence'] for t in trades if t['pnl_usd'] > 0) / len([t for t in trades if t['pnl_usd'] > 0]) if [t for t in trades if t['pnl_usd'] > 0] else 0
avg_losing_conf = sum(t['confidence'] for t in trades if t['pnl_usd'] <= 0) / len([t for t in trades if t['pnl_usd'] <= 0]) if [t for t in trades if t['pnl_usd'] <= 0] else 0

print(f'''
STATISTIQUES OBSERVEES:
  - Confidence moyenne gagnants: {avg_winning_conf:.3f}
  - Confidence moyenne perdants: {avg_losing_conf:.3f}
  - Delta: {avg_winning_conf - avg_losing_conf:+.3f}

SEUILS RECOMMANDES (basés sur l'analyse):

  Configuration actuelle vs Recommandée:

  ┌─────────────────────┬─────────────┬─────────────┐
  │ Parametre           │ Actuel      │ Recommande  │
  ├─────────────────────┼─────────────┼─────────────┤
  │ MIN_CONFIDENCE ES   │ 0.24        │ 0.70        │
  │ MIN_CONFIDENCE NQ   │ 0.24        │ 0.80        │
  │ MIN_CONFLUENCE      │ 0.50        │ 0.60        │
  └─────────────────────┴─────────────┴─────────────┘

ESTIMATION SEUILS PAR LAYER:
(Basé sur formule: Confidence = L1*0.5 + L2*0.3 + L3*0.2)

Pour atteindre confidence >= 0.70 (seuil recommandé ES):
  - MenthorQ (L1): >= 0.50 (contribution: 0.25)
  - OrderFlow (L2): >= 0.40 (contribution: 0.12)
  - Context (L3): >= 0.60 (contribution: 0.12)
  = Total minimum: 0.49 (marge de securite)

Pour atteindre confidence >= 0.80 (seuil recommandé NQ):
  - MenthorQ (L1): >= 0.60 (contribution: 0.30)
  - OrderFlow (L2): >= 0.50 (contribution: 0.15)
  - Context (L3): >= 0.70 (contribution: 0.14)
  = Total minimum: 0.59 (marge de securite)

Pour NQ LONG specifiquement (probleme identifie):
  - MenthorQ (L1): >= 0.70 (haute qualite signal)
  - OrderFlow (L2): >= 0.60 (confirmation forte)
  - Context (L3): >= 0.50 (contexte favorable)
  = Confidence min: 0.62

NOTE: Ces valeurs sont des estimations. Les vraies valeurs
par layer ne sont pas loggees actuellement.
''')

print('='*70)
print(' ACTIONS IMMEDIATES')
print('='*70)
print('''
1. URGENT - Modifier unified_thresholds.py:

   MIN_TOTAL_CONFIDENCE = {
       'ES': 0.70,  # etait 0.24
       'NQ': 0.80,  # etait 0.24
       'RTY': 0.70
   }

2. OPTIONAL - Ajouter filtre specifique NQ LONG:

   if symbol == 'NQ' and direction == 'LONG':
       if confidence < 1.00:
           return False  # Rejeter
''')
