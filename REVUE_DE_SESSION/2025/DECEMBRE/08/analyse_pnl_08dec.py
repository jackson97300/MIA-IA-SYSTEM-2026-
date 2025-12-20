#!/usr/bin/env python3
"""
Analyse P&L détaillée - 08/12/2025
"""

import json
import glob
import os

# Charger tous les trades du 08/12
trades = []
for f in glob.glob(r'D:\MIA_IA_system\snapshots_trades\daily\TRADE_20251208*_final_result.json'):
    with open(f, 'r') as fp:
        data = json.load(fp)
    result = data.get('result', {})
    trades.append({
        'time': os.path.basename(f)[15:21],
        'pnl': result.get('pnl', 0),
        'exit': result.get('exit_reason', 'N/A'),
        'ticks': result.get('ticks', 0)
    })

# Trier par heure
trades.sort(key=lambda x: x['time'])

# Afficher
print('TRADES 08/12/2025')
print('='*70)
print(f"{'Heure':<8} {'P&L':>12} {'Ticks':>8} {'Exit':<20}")
print('-'*70)

total_wins = 0
total_losses = 0
sum_wins = 0
sum_losses = 0
biggest_win = 0
biggest_loss = 0
win_pnls = []
loss_pnls = []

for t in trades:
    pnl = t['pnl']
    status = 'WIN' if pnl > 0 else 'LOSS'
    print(f"{t['time']:<8} {pnl:>+12.2f}$ {t['ticks']:>+7.1f}t {t['exit']:<20}")

    if pnl > 0:
        total_wins += 1
        sum_wins += pnl
        win_pnls.append(pnl)
        if pnl > biggest_win:
            biggest_win = pnl
    else:
        total_losses += 1
        sum_losses += abs(pnl)
        loss_pnls.append(abs(pnl))
        if abs(pnl) > biggest_loss:
            biggest_loss = abs(pnl)

print('='*70)
print()
print("STATISTIQUES DETAILLEES:")
print('-'*70)
print(f"WINS:  {total_wins} trades")
print(f"  - Total gains:    +${sum_wins:.2f}")
print(f"  - Gain moyen:     +${sum_wins/total_wins if total_wins else 0:.2f}")
print(f"  - Plus gros gain: +${biggest_win:.2f}")
print()
print(f"LOSS:  {total_losses} trades")
print(f"  - Total pertes:   -${sum_losses:.2f}")
print(f"  - Perte moyenne:  -${sum_losses/total_losses if total_losses else 0:.2f}")
print(f"  - Plus grosse perte: -${biggest_loss:.2f}")
print()
print('-'*70)
print("PROBLEME IDENTIFIE:")
print('-'*70)
avg_win = sum_wins/total_wins if total_wins else 0
avg_loss = sum_losses/total_losses if total_losses else 0

print(f"Gain moyen:  +${avg_win:.2f}")
print(f"Perte moyenne: -${avg_loss:.2f}")
print(f"Ratio Gain/Perte: {avg_win/avg_loss if avg_loss else 0:.2f}:1")
print()

if avg_loss > avg_win * 2:
    print("!! ALERTE: Pertes BEAUCOUP plus grosses que gains !!")
    print(f"   Pour etre rentable avec ce ratio, il faut >66% Win Rate")
    print(f"   Win Rate actuel: {total_wins/(total_wins+total_losses)*100:.1f}%")

print()
print("DETAILS PAR CATEGORIE:")
print('-'*70)

# Catégoriser
small_wins = [p for p in win_pnls if p < 50]
medium_wins = [p for p in win_pnls if 50 <= p < 150]
big_wins = [p for p in win_pnls if p >= 150]

small_losses = [p for p in loss_pnls if p < 150]
big_losses = [p for p in loss_pnls if p >= 150]

print(f"Petits gains (<$50):     {len(small_wins)} trades = +${sum(small_wins):.2f}")
print(f"Gains moyens ($50-150):  {len(medium_wins)} trades = +${sum(medium_wins):.2f}")
print(f"Gros gains (>$150):      {len(big_wins)} trades = +${sum(big_wins):.2f}")
print()
print(f"Petites pertes (<$150):  {len(small_losses)} trades = -${sum(small_losses):.2f}")
print(f"GROSSES PERTES (>$150):  {len(big_losses)} trades = -${sum(big_losses):.2f}")
print()

if big_losses:
    print("!! Les grosses pertes mangent tous les gains !!")
    print(f"   {len(big_losses)} grosses pertes = -${sum(big_losses):.2f}")
    print(f"   vs Total gains = +${sum_wins:.2f}")

print()
print('-'*70)
print(f"P&L NET: ${sum_wins - sum_losses:+.2f}")
print('-'*70)

