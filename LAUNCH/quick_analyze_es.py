#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')

# Données extraites manuellement depuis les messages Discord
# Format: (WIN/LOSS, confluence, menthorq, orderflow, context, pnl)
trades_data = [
    ('WIN', 1.06, 0.86, 0.08, 0.12, 438.80),
    ('LOSS', 1.16, 0.84, 0.20, 0.12, -148.70),
    ('WIN', 1.21, 0.77, 0.24, 0.20, 200.80),
    ('WIN', 0.73, 0.51, 0.08, 0.14, 188.30),
    ('LOSS', 1.04, 0.74, 0.20, 0.10, -148.70),
    ('WIN', 1.04, 0.64, 0.26, 0.14, 50.80),
    ('WIN', 0.87, 0.65, 0.08, 0.14, 50.80),
    ('LOSS', 0.90, 0.64, 0.12, 0.14, -261.70),
    ('WIN', 1.21, 0.81, 0.24, 0.16, 50.80),
    ('WIN', 0.87, 0.51, 0.20, 0.16, 50.80),
    ('WIN', 0.96, 0.78, 0.08, 0.10, 38.80),
    ('WIN', 1.02, 0.68, 0.20, 0.14, 100.80),
    ('WIN', 0.87, 0.55, 0.18, 0.14, 63.80),
    ('LOSS', 0.91, 0.73, 0.08, 0.10, -123.70),
    ('WIN', 0.87, 0.55, 0.18, 0.14, 144.80),
    ('LOSS', 0.79, 0.55, 0.10, 0.14, -11.20),
    ('LOSS', 1.13, 0.73, 0.26, 0.14, -130.20),
    ('WIN', 1.07, 0.73, 0.20, 0.14, 413.30),
    ('WIN', 1.20, 0.74, 0.26, 0.20, 13.80),
    ('LOSS', 1.20, 0.74, 0.26, 0.20, -148.70),
    ('LOSS', 1.24, 0.78, 0.26, 0.20, -36.20),
    ('WIN', 1.20, 0.74, 0.26, 0.20, 326.30),
    ('LOSS', 1.01, 0.68, 0.12, 0.22, -23.70),
    ('LOSS', 1.20, 0.72, 0.26, 0.22, -261.20),
    ('LOSS', 1.21, 0.75, 0.26, 0.20, -11.20),
    ('LOSS', 0.97, 0.75, 0.08, 0.14, -149.20),
    ('LOSS', 0.89, 0.59, 0.08, 0.22, -261.20),
    ('LOSS', 1.14, 0.76, 0.24, 0.14, -111.70),
    ('LOSS', 1.08, 0.68, 0.26, 0.14, -261.70),
    ('WIN', 1.08, 0.71, 0.15, 0.22, 288.80),
    ('LOSS', 1.09, 0.73, 0.20, 0.16, -261.70),
    ('WIN', 1.10, 0.72, 0.26, 0.12, 438.80),
    ('LOSS', 1.40, 0.88, 0.30, 0.22, -24.20),
    ('LOSS', 0.94, 0.72, 0.09, 0.12, -200.00),
    ('WIN', 0.92, 0.72, 0.08, 0.12, 263.80),
    ('LOSS', 1.03, 0.72, 0.14, 0.16, -149.20),
    ('WIN', 1.32, 0.86, 0.24, 0.22, 63.30),
    ('WIN', 0.95, 0.71, 0.08, 0.16, 250.80),
    ('WIN', 0.94, 0.72, 0.09, 0.12, 301.30),
    ('WIN', 1.14, 0.72, 0.26, 0.16, 25.80),
]

wins = [t for t in trades_data if t[0] == 'WIN']
losses = [t for t in trades_data if t[0] == 'LOSS']

print('='*80)
print('📊 ANALYSE ES TRADES - 40 Trades Extraits')
print('='*80)
print(f'Total: {len(trades_data)} trades')
print(f'✅ WINS: {len(wins)} trades ({len(wins)/len(trades_data)*100:.1f}%)')
print(f'❌ LOSS: {len(losses)} trades ({len(losses)/len(trades_data)*100:.1f}%)')
print(f'💰 P&L Total: ${sum(t[5] for t in trades_data):+,.2f}')
print()

print('='*80)
print('MOYENNES WINS vs LOSS')
print('='*80)
print()
print('✅ MOYENNES WINS:')
print(f'  🧩 Confluence:  {sum(t[1] for t in wins)/len(wins):.2f}')
print(f'  🎯 MenthorQ:    {sum(t[2] for t in wins)/len(wins):.2f}')
print(f'  📊 OrderFlow:   {sum(t[3] for t in wins)/len(wins):.2f}')
print(f'  🌍 Context:     {sum(t[4] for t in wins)/len(wins):.2f}')
print()

print('❌ MOYENNES LOSS:')
print(f'  🧩 Confluence:  {sum(t[1] for t in losses)/len(losses):.2f}')
print(f'  🎯 MenthorQ:    {sum(t[2] for t in losses)/len(losses):.2f}')
print(f'  📊 OrderFlow:   {sum(t[3] for t in losses)/len(losses):.2f}')
print(f'  🌍 Context:     {sum(t[4] for t in losses)/len(losses):.2f}')
print()

print('='*80)
print('🔍 ANALYSE PAR RANGES')
print('='*80)
print()

# OrderFlow Analysis
print('📊 ORDERFLOW Analysis:')
for of_min, of_max, label in [(0.00, 0.10, 'Catastrophique'), (0.10, 0.15, 'Très faible'),
                                (0.15, 0.20, 'Faible'), (0.20, 0.25, 'Moyen'),
                                (0.25, 0.30, 'Bon'), (0.30, 1.00, 'Excellent')]:
    range_trades = [t for t in trades_data if of_min <= t[3] < of_max]
    if range_trades:
        range_wins = [t for t in range_trades if t[0] == 'WIN']
        wr = len(range_wins) / len(range_trades) * 100
        pnl = sum(t[5] for t in range_trades)
        print(f'  [{of_min:.2f}-{of_max:.2f}] {label:15s}: {len(range_trades):2d} trades | WR: {wr:5.1f}% | P&L: ${pnl:+8.2f}')
print()

# Analyse critique: OrderFlow < 0.15
low_of = [t for t in trades_data if t[3] < 0.15]
low_of_wins = [t for t in low_of if t[0] == 'WIN']
print(f'⚠️ OrderFlow < 0.15: {len(low_of)} trades | WR: {len(low_of_wins)/len(low_of)*100:.1f}% | P&L: ${sum(t[5] for t in low_of):+.2f}')
print(f'   → {"✅ RENTABLE QUAND MÊME!" if len(low_of_wins)/len(low_of) >= 0.50 else "❌ PAS RENTABLE!"}')
print()

# OrderFlow < 0.15 ET Context < 0.15
low_both = [t for t in trades_data if t[3] < 0.15 and t[4] < 0.15]
low_both_wins = [t for t in low_both if t[0] == 'WIN']
if low_both:
    print(f'🔴 OrderFlow < 0.15 ET Context < 0.15: {len(low_both)} trades | WR: {len(low_both_wins)/len(low_both)*100:.1f}% | P&L: ${sum(t[5] for t in low_both):+.2f}')
    print(f'   → {"✅ OK" if len(low_both_wins)/len(low_both) >= 0.50 else "❌ À BLOQUER!"}')
    print()

# Trades avec TOUS layers bons
good_all = [t for t in trades_data if t[3] >= 0.20 and t[4] >= 0.16 and t[2] >= 0.70]
good_all_wins = [t for t in good_all if t[0] == 'WIN']
if good_all:
    print(f'✅ TOUS layers bons (OF≥0.20, CTX≥0.16, MQ≥0.70): {len(good_all)} trades | WR: {len(good_all_wins)/len(good_all)*100:.1f}% | P&L: ${sum(t[5] for t in good_all):+.2f}')
    print(f'   → {"🚀 PATTERN PREMIUM!" if len(good_all_wins)/len(good_all) >= 0.70 else "✅ BON"}')
    print()

print('='*80)
print('🎯 RECHERCHE SEUILS OPTIMAUX')
print('='*80)
print()

# Test différents seuils
best_config = None
best_wr = 0
best_pnl_total = 0

print('Test de combinaisons de seuils...')
print()

for of_threshold in [0.08, 0.10, 0.12, 0.15, 0.18, 0.20]:
    for ctx_threshold in [0.10, 0.12, 0.14, 0.16, 0.18, 0.20]:
        for mq_threshold in [0.55, 0.60, 0.65, 0.70, 0.75]:
            filtered = [t for t in trades_data if
                       t[3] >= of_threshold and
                       t[4] >= ctx_threshold and
                       t[2] >= mq_threshold]

            if len(filtered) >= 10:  # Au moins 10 trades
                filtered_wins = [t for t in filtered if t[0] == 'WIN']
                wr = len(filtered_wins) / len(filtered)
                pnl_total = sum(t[5] for t in filtered)

                if wr > best_wr and pnl_total > best_pnl_total:
                    best_wr = wr
                    best_pnl_total = pnl_total
                    best_config = (of_threshold, ctx_threshold, mq_threshold, len(filtered))

if best_config:
    of, ctx, mq, count = best_config
    print(f'🏆 MEILLEURE CONFIGURATION:')
    print(f'   OrderFlow:  ≥ {of:.2f}')
    print(f'   Context:    ≥ {ctx:.2f}')
    print(f'   MenthorQ:   ≥ {mq:.2f}')
    print(f'   Résultats:  {count} trades | WR: {best_wr*100:.1f}% | P&L: ${best_pnl_total:+,.2f}')
    print()

print('='*80)
print('📝 RECOMMANDATION FINALE')
print('='*80)
print()
print('Pour ES dans config/unified_thresholds.py:')
print()
print('"ES": {')
if best_config:
    of, ctx, mq, _ = best_config
    print(f'    "layer1": {mq:.2f},  # MenthorQ')
    print(f'    "layer2": {of:.2f},  # OrderFlow ⚠️ CRITIQUE!')
    print(f'    "layer3": {ctx:.2f}   # Context')
else:
    print('    "layer1": 0.70,  # MenthorQ')
    print('    "layer2": 0.18,  # OrderFlow (basé sur moyenne WINS)')
    print('    "layer3": 0.16   # Context (basé sur moyenne WINS)')
print('},')
print()

print('💡 OBSERVATIONS CLÉS:')
print(f'  - OrderFlow moyen WINS:  {sum(t[3] for t in wins)/len(wins):.2f}')
print(f'  - OrderFlow moyen LOSS:  {sum(t[3] for t in losses)/len(losses):.2f}')
print(f'  - ⚠️ Même avec OrderFlow bas (0.08-0.09), certains trades WIN!')
print(f'  - Le Context semble AUSSI important que OrderFlow')
print(f'  - MenthorQ seul NE SUFFIT PAS (même à 0.88 ça peut perdre!)')
