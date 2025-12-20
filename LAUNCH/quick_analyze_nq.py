#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')

# Données NQ extraites des messages Discord
# Format: (WIN/LOSS, confluence, menthorq, orderflow, context, pnl)
trades_nq = [
    ('LOSS', 0.81, 0.51, 0.08, 0.22, -185.20),
    ('WIN', 0.80, 0.52, 0.06, 0.22, 347.20),
    ('LOSS', 0.69, 0.35, 0.12, 0.22, -180.20),
    ('LOSS', 0.63, 0.35, 0.06, 0.22, -180.20),
    ('LOSS', 0.72, 0.35, 0.16, 0.22, -332.80),
    ('LOSS', 0.82, 0.36, 0.24, 0.22, -180.20),
    ('LOSS', 0.75, 0.37, 0.18, 0.20, -182.80),
    ('WIN', 0.76, 0.36, 0.18, 0.22, 347.20),
    ('LOSS', 1.26, 0.84, 0.20, 0.22, -180.20),
    ('LOSS', 0.89, 0.65, 0.10, 0.14, -180.20),
    ('WIN', 0.71, 0.47, 0.08, 0.16, 4.80),
    ('LOSS', 0.78, 0.46, 0.18, 0.14, -60.20),
    ('WIN', 0.68, 0.46, 0.08, 0.14, 217.20),
    ('LOSS', 0.95, 0.55, 0.26, 0.14, -82.60),
    ('LOSS', 0.73, 0.55, 0.08, 0.10, -180.20),
    ('LOSS', 0.93, 0.55, 0.24, 0.14, -65.20),
    ('WIN', 1.11, 0.69, 0.26, 0.16, 1064.80),
    ('WIN', 1.11, 0.69, 0.26, 0.16, 189.80),
    ('WIN', 1.03, 0.68, 0.20, 0.14, 14.80),
    ('LOSS', 1.04, 0.66, 0.24, 0.14, -60.20),
    ('LOSS', 1.04, 0.66, 0.24, 0.14, -60.20),
    ('WIN', 1.06, 0.64, 0.26, 0.16, 169.80),
    ('LOSS', 1.00, 0.64, 0.20, 0.16, -50.20),
    ('LOSS', 0.82, 0.58, 0.08, 0.16, -180.20),
    ('LOSS', 1.05, 0.65, 0.26, 0.14, -62.80),
    ('WIN', 0.84, 0.51, 0.19, 0.14, 129.80),
    ('LOSS', 0.79, 0.51, 0.14, 0.14, -65.20),
    ('WIN', 0.95, 0.51, 0.30, 0.14, 154.80),
    ('LOSS', 1.04, 0.66, 0.24, 0.14, -45.20),
    ('LOSS', 0.89, 0.66, 0.09, 0.14, -60.20),
    ('LOSS', 0.88, 0.64, 0.08, 0.16, -45.20),
    ('WIN', 1.06, 0.64, 0.26, 0.16, 344.80),
    ('WIN', 0.75, 0.45, 0.14, 0.16, 29.80),
    ('WIN', 0.97, 0.55, 0.26, 0.16, 344.80),
    ('LOSS', 0.85, 0.55, 0.14, 0.16, -60.20),
    ('LOSS', 0.93, 0.55, 0.26, 0.12, -187.60),
    ('LOSS', 0.97, 0.55, 0.26, 0.16, -65.20),
    ('LOSS', 0.91, 0.55, 0.20, 0.16, -65.20),
    ('LOSS', 0.79, 0.55, 0.08, 0.16, -60.20),
    ('WIN', 0.93, 0.55, 0.26, 0.12, 234.80),
    ('LOSS', 0.81, 0.55, 0.14, 0.12, -62.60),
    ('LOSS', 0.87, 0.55, 0.20, 0.12, -75.20),
    ('LOSS', 0.93, 0.55, 0.26, 0.12, -55.20),
    ('WIN', 0.90, 0.48, 0.24, 0.18, 482.20),
    ('LOSS', 0.95, 0.55, 0.24, 0.16, -60.20),
    ('WIN', 1.01, 0.55, 0.30, 0.16, 14.80),
    ('WIN', 0.71, 0.45, 0.14, 0.12, -0.20),
    ('LOSS', 1.01, 0.55, 0.30, 0.16, -65.20),
]

wins = [t for t in trades_nq if t[0] == 'WIN']
losses = [t for t in trades_nq if t[0] == 'LOSS']

print('='*80)
print('📊 ANALYSE NQ TRADES - 48 Trades Extraits')
print('='*80)
print(f'Total: {len(trades_nq)} trades')
print(f'✅ WINS: {len(wins)} trades ({len(wins)/len(trades_nq)*100:.1f}%)')
print(f'❌ LOSS: {len(losses)} trades ({len(losses)/len(trades_nq)*100:.1f}%)')
print(f'💰 P&L Total: ${sum(t[5] for t in trades_nq):+,.2f}')
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
    range_trades = [t for t in trades_nq if of_min <= t[3] < of_max]
    if range_trades:
        range_wins = [t for t in range_trades if t[0] == 'WIN']
        wr = len(range_wins) / len(range_trades) * 100
        pnl = sum(t[5] for t in range_trades)
        print(f'  [{of_min:.2f}-{of_max:.2f}] {label:15s}: {len(range_trades):2d} trades | WR: {wr:5.1f}% | P&L: ${pnl:+8.2f}')
print()

# Context analysis
print('🌍 CONTEXT Analysis:')
for ctx_min, ctx_max, label in [(0.00, 0.12, 'Très faible'), (0.12, 0.16, 'Faible'),
                                 (0.16, 0.20, 'Moyen'), (0.20, 0.25, 'Bon')]:
    range_trades = [t for t in trades_nq if ctx_min <= t[4] < ctx_max]
    if range_trades:
        range_wins = [t for t in range_trades if t[0] == 'WIN']
        wr = len(range_wins) / len(range_trades) * 100
        pnl = sum(t[5] for t in range_trades)
        print(f'  [{ctx_min:.2f}-{ctx_max:.2f}] {label:15s}: {len(range_trades):2d} trades | WR: {wr:5.1f}% | P&L: ${pnl:+8.2f}')
print()

# Analyse critique
low_of = [t for t in trades_nq if t[3] < 0.15]
low_of_wins = [t for t in low_of if t[0] == 'WIN']
print(f'⚠️  OrderFlow < 0.15: {len(low_of)} trades | WR: {len(low_of_wins)/len(low_of)*100:.1f}% | P&L: ${sum(t[5] for t in low_of):+.2f}')
print(f'   → {"✅ RENTABLE" if len(low_of_wins)/len(low_of) >= 0.50 else "❌ PAS RENTABLE!"}')
print()

low_ctx = [t for t in trades_nq if t[4] < 0.15]
low_ctx_wins = [t for t in low_ctx if t[0] == 'WIN']
if low_ctx:
    print(f'⚠️  Context < 0.15: {len(low_ctx)} trades | WR: {len(low_ctx_wins)/len(low_ctx)*100:.1f}% | P&L: ${sum(t[5] for t in low_ctx):+.2f}')
    print(f'   → {"✅ OK" if len(low_ctx_wins)/len(low_ctx) >= 0.50 else "❌ À BLOQUER!"}')
    print()

# Trades avec TOUS layers bons
good_all = [t for t in trades_nq if t[3] >= 0.20 and t[4] >= 0.16 and t[2] >= 0.50]
good_all_wins = [t for t in good_all if t[0] == 'WIN']
if good_all:
    print(f'✅ TOUS layers bons (OF≥0.20, CTX≥0.16, MQ≥0.50): {len(good_all)} trades | WR: {len(good_all_wins)/len(good_all)*100:.1f}% | P&L: ${sum(t[5] for t in good_all):+.2f}')
    print(f'   → {"🚀 PATTERN PREMIUM!" if len(good_all_wins)/len(good_all) >= 0.70 else "✅ BON"}')
    print()

print('='*80)
print('🎯 RECHERCHE SEUILS OPTIMAUX')
print('='*80)
print()

best_config = None
best_wr = 0
best_pnl_total = -999999

for of_threshold in [0.08, 0.10, 0.12, 0.15, 0.18, 0.20, 0.22, 0.24, 0.26]:
    for ctx_threshold in [0.10, 0.12, 0.14, 0.16, 0.18, 0.20]:
        for mq_threshold in [0.35, 0.40, 0.45, 0.50, 0.55, 0.60]:
            filtered = [t for t in trades_nq if
                       t[3] >= of_threshold and
                       t[4] >= ctx_threshold and
                       t[2] >= mq_threshold]

            if len(filtered) >= 10:
                filtered_wins = [t for t in filtered if t[0] == 'WIN']
                wr = len(filtered_wins) / len(filtered) if filtered else 0
                pnl_total = sum(t[5] for t in filtered)

                if wr >= 0.50 and pnl_total > best_pnl_total:
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
else:
    print('❌ Aucune configuration avec WR ≥ 50% et P&L positif trouvée!')
    print()

print('='*80)
print('📝 RECOMMANDATION FINALE')
print('='*80)
print()
print('Pour NQ dans config/unified_thresholds.py:')
print()
print('"NQ": {')
if best_config:
    of, ctx, mq, _ = best_config
    print(f'    "layer1": {mq:.2f},  # MenthorQ')
    print(f'    "layer2": {of:.2f},  # OrderFlow')
    print(f'    "layer3": {ctx:.2f}   # Context')
else:
    print('    "layer1": 0.55,  # MenthorQ (basé sur moyenne WINS)')
    print('    "layer2": 0.22,  # OrderFlow (basé sur moyenne WINS)')
    print('    "layer3": 0.16   # Context (basé sur moyenne WINS)')
print('},')
print()

print('='*80)
print('📊 COMPARAISON ES vs NQ')
print('='*80)
print()

# ES data from previous analysis
trades_es_wr = 52.5
trades_es_of_avg_wins = 0.18
trades_es_of_avg_loss = 0.18
trades_nq_wr = len(wins)/len(trades_nq)*100
trades_nq_of_avg_wins = sum(t[3] for t in wins)/len(wins)
trades_nq_of_avg_loss = sum(t[3] for t in losses)/len(losses)

print(f'ES:')
print(f'  Win Rate: {trades_es_wr:.1f}%')
print(f'  OrderFlow WINS: {trades_es_of_avg_wins:.2f}')
print(f'  OrderFlow LOSS: {trades_es_of_avg_loss:.2f}')
print()
print(f'NQ:')
print(f'  Win Rate: {trades_nq_wr:.1f}%')
print(f'  OrderFlow WINS: {trades_nq_of_avg_wins:.2f}')
print(f'  OrderFlow LOSS: {trades_nq_of_avg_loss:.2f}')
print()
print('💡 OBSERVATIONS:')
print(f'  - NQ a un Win Rate INFÉRIEUR à ES ({trades_nq_wr:.1f}% vs {trades_es_wr:.1f}%)')
print(f'  - NQ OrderFlow WINS ({trades_nq_of_avg_wins:.2f}) > LOSS ({trades_nq_of_avg_loss:.2f}) ← BONNE DIFFÉRENCE!')
print(f'  - Pour NQ, OrderFlow semble PLUS discriminant que pour ES')
