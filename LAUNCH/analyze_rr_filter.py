#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')

# Données extraites manuellement des messages Discord avec R:R
# Format: (symbol, WIN/LOSS, r_r_ratio, pnl, confluence, menthorq, orderflow, context)

trades_with_rr = [
    # ES trades avec R:R visible
    ('ES', 'WIN', 1.75, 438.80, 1.06, 0.86, 0.08, 0.12),
    ('ES', 'LOSS', 3.05, -148.70, 1.16, 0.84, 0.20, 0.12),
    ('ES', 'WIN', 2.80, 200.80, 1.21, 0.77, 0.24, 0.20),
    ('ES', 'WIN', 1.79, 188.30, 0.73, 0.51, 0.08, 0.14),
    ('ES', 'LOSS', 1.64, -148.70, 1.04, 0.74, 0.20, 0.10),
    ('ES', 'WIN', 0.16, 50.80, 1.04, 0.64, 0.26, 0.14),
    ('ES', 'WIN', 3.09, 50.80, 0.87, 0.65, 0.08, 0.14),
    ('ES', 'LOSS', 0.43, -261.70, 0.90, 0.64, 0.12, 0.14),
    ('ES', 'WIN', 0.06, 50.80, 1.21, 0.81, 0.24, 0.16),
    ('ES', 'WIN', 0.24, 50.80, 0.87, 0.51, 0.20, 0.16),
    ('ES', 'WIN', 0.41, 38.80, 0.96, 0.78, 0.08, 0.10),
    ('ES', 'WIN', 0.38, 100.80, 1.02, 0.68, 0.20, 0.14),
    ('ES', 'WIN', 0.03, 63.80, 0.87, 0.55, 0.18, 0.14),
    ('ES', 'LOSS', 0.29, -123.70, 0.91, 0.73, 0.08, 0.10),
    ('ES', 'WIN', 0.27, 144.80, 0.87, 0.55, 0.18, 0.14),
    ('ES', 'LOSS', 0.03, -11.20, 0.79, 0.55, 0.10, 0.14),
    ('ES', 'LOSS', 0.06, -19.00, 1.13, 0.73, 0.26, 0.14),  # Très court TP
    ('ES', 'LOSS', 0.38, -130.20, 1.13, 0.73, 0.26, 0.14),
    ('ES', 'WIN', 4.21, 413.30, 1.07, 0.73, 0.20, 0.14),
    ('ES', 'WIN', 3.05, 13.80, 1.20, 0.74, 0.26, 0.20),
    ('ES', 'LOSS', 3.05, -148.70, 1.20, 0.74, 0.26, 0.20),

    # NQ trades avec R:R visible
    ('NQ', 'LOSS', 2.00, -185.20, 0.81, 0.51, 0.08, 0.22),
    ('NQ', 'WIN', 2.00, 347.20, 0.80, 0.52, 0.06, 0.22),
    ('NQ', 'LOSS', 2.00, -180.20, 0.69, 0.35, 0.12, 0.22),
    ('NQ', 'LOSS', 2.00, -180.20, 0.63, 0.35, 0.06, 0.22),
    ('NQ', 'WIN', 2.00, 347.20, 0.76, 0.36, 0.18, 0.22),
    ('NQ', 'LOSS', 2.00, -180.20, 1.26, 0.84, 0.20, 0.22),
    ('NQ', 'LOSS', 1.64, -180.20, 0.89, 0.65, 0.10, 0.14),
    ('NQ', 'WIN', 0.06, 4.80, 0.71, 0.47, 0.08, 0.16),
    ('NQ', 'LOSS', 3.85, -60.20, 0.78, 0.46, 0.18, 0.14),
    ('NQ', 'WIN', 1.25, 217.20, 0.68, 0.46, 0.08, 0.14),
    ('NQ', 'LOSS', 6.55, -82.60, 0.95, 0.55, 0.26, 0.14),
    ('NQ', 'LOSS', 1.29, -180.20, 0.73, 0.55, 0.08, 0.10),
    ('NQ', 'LOSS', 5.99, -65.20, 0.93, 0.55, 0.24, 0.14),
    ('NQ', 'WIN', 2.00, 344.80, 0.97, 0.55, 0.26, 0.16),
    ('NQ', 'LOSS', 6.55, -60.20, 0.85, 0.55, 0.14, 0.16),
    ('NQ', 'LOSS', 2.00, -187.60, 0.93, 0.55, 0.26, 0.12),
    ('NQ', 'LOSS', 5.57, -65.20, 0.97, 0.55, 0.26, 0.16),
    ('NQ', 'LOSS', 5.48, -65.20, 0.91, 0.55, 0.20, 0.16),
    ('NQ', 'LOSS', 5.99, -60.20, 0.79, 0.55, 0.08, 0.16),
    ('NQ', 'WIN', 7.51, 234.80, 0.93, 0.55, 0.26, 0.12),
    ('NQ', 'LOSS', 6.48, -62.60, 0.81, 0.55, 0.14, 0.12),
    ('NQ', 'LOSS', 6.18, -75.20, 0.87, 0.55, 0.20, 0.12),
    ('NQ', 'LOSS', 7.51, -55.20, 0.93, 0.55, 0.26, 0.12),
    ('NQ', 'WIN', 5.83, 482.20, 0.90, 0.48, 0.24, 0.18),
    ('NQ', 'LOSS', 5.99, -60.20, 0.95, 0.55, 0.24, 0.16),
    ('NQ', 'WIN', 2.00, 14.80, 1.01, 0.55, 0.30, 0.16),
    ('NQ', 'WIN', 0.01, -0.20, 0.71, 0.45, 0.14, 0.12),
    ('NQ', 'LOSS', 5.99, -65.20, 1.01, 0.55, 0.30, 0.16),
]

# Séparer par R:R
low_rr = [t for t in trades_with_rr if t[2] < 1.00]
good_rr = [t for t in trades_with_rr if t[2] >= 1.00]

low_rr_wins = [t for t in low_rr if t[1] == 'WIN']
good_rr_wins = [t for t in good_rr if t[1] == 'WIN']

print('='*100)
print('📊 ANALYSE IMPACT FILTRE R:R >= 1.00')
print('='*100)
print()

print('🔍 TRADES AVEC R:R < 1.00 (Mauvais Risk/Reward):')
print(f'   Total: {len(low_rr)} trades')
print(f'   Wins: {len(low_rr_wins)} trades')
print(f'   Loss: {len(low_rr) - len(low_rr_wins)} trades')
print(f'   Win Rate: {len(low_rr_wins)/len(low_rr)*100:.1f}%')
print(f'   P&L Total: ${sum(t[3] for t in low_rr):+,.2f}')
print()

print('✅ TRADES AVEC R:R >= 1.00 (Bon Risk/Reward):')
print(f'   Total: {len(good_rr)} trades')
print(f'   Wins: {len(good_rr_wins)} trades')
print(f'   Loss: {len(good_rr) - len(good_rr_wins)} trades')
print(f'   Win Rate: {len(good_rr_wins)/len(good_rr)*100:.1f}%')
print(f'   P&L Total: ${sum(t[3] for t in good_rr):+,.2f}')
print()

print('='*100)
print('📈 DÉTAIL DES TRADES R:R < 1.00')
print('='*100)
print()

# Grouper par symbole
es_low_rr = [t for t in low_rr if t[0] == 'ES']
nq_low_rr = [t for t in low_rr if t[0] == 'NQ']

print('ES (E-mini S&P 500):')
for t in es_low_rr:
    result = "✅ WIN" if t[1] == 'WIN' else "❌ LOSS"
    print(f'  {result} | R:R {t[2]:.2f} | P&L ${t[3]:+7.2f} | Conf:{t[4]:.2f} MQ:{t[5]:.2f} OF:{t[6]:.2f} CTX:{t[7]:.2f}')

if es_low_rr:
    es_low_rr_wins = [t for t in es_low_rr if t[1] == 'WIN']
    print(f'  → {len(es_low_rr)} trades | WR: {len(es_low_rr_wins)/len(es_low_rr)*100:.1f}% | P&L: ${sum(t[3] for t in es_low_rr):+.2f}')
print()

print('NQ (E-mini Nasdaq 100):')
for t in nq_low_rr:
    result = "✅ WIN" if t[1] == 'WIN' else "❌ LOSS"
    print(f'  {result} | R:R {t[2]:.2f} | P&L ${t[3]:+7.2f} | Conf:{t[4]:.2f} MQ:{t[5]:.2f} OF:{t[6]:.2f} CTX:{t[7]:.2f}')

if nq_low_rr:
    nq_low_rr_wins = [t for t in nq_low_rr if t[1] == 'WIN']
    print(f'  → {len(nq_low_rr)} trades | WR: {len(nq_low_rr_wins)/len(nq_low_rr)*100:.1f}% | P&L: ${sum(t[3] for t in nq_low_rr):+.2f}')
print()

print('='*100)
print('💡 IMPACT SI ON APPLIQUE LE FILTRE R:R >= 1.00')
print('='*100)
print()

print('AVANT FILTRE (Tous les trades):')
all_wins = len([t for t in trades_with_rr if t[1] == 'WIN'])
print(f'  Total: {len(trades_with_rr)} trades')
print(f'  Win Rate: {all_wins/len(trades_with_rr)*100:.1f}%')
print(f'  P&L Total: ${sum(t[3] for t in trades_with_rr):+,.2f}')
print()

print('APRÈS FILTRE (R:R >= 1.00 uniquement):')
print(f'  Total: {len(good_rr)} trades ({len(good_rr)/len(trades_with_rr)*100:.0f}% des trades passent)')
print(f'  Win Rate: {len(good_rr_wins)/len(good_rr)*100:.1f}% ({len(good_rr_wins)/len(good_rr)*100 - all_wins/len(trades_with_rr)*100:+.1f}%)')
print(f'  P&L Total: ${sum(t[3] for t in good_rr):+,.2f} ({sum(t[3] for t in good_rr) - sum(t[3] for t in trades_with_rr):+.2f})')
print()

print('TRADES BLOQUÉS (R:R < 1.00):')
print(f'  Total: {len(low_rr)} trades ({len(low_rr)/len(trades_with_rr)*100:.0f}% des trades)')
print(f'  P&L évité: ${sum(t[3] for t in low_rr):+,.2f}')
print()

print('='*100)
print('🎯 CONCLUSION')
print('='*100)
print()

# Calculer si c'est positif ou négatif
pnl_low_rr = sum(t[3] for t in low_rr)
wr_improvement = len(good_rr_wins)/len(good_rr)*100 - all_wins/len(trades_with_rr)*100

if pnl_low_rr < 0:
    print(f'✅ FILTRE BÉNÉFIQUE: Les trades R:R < 1.00 ont perdu ${abs(pnl_low_rr):.2f}')
    print(f'   → Bloquer ces {len(low_rr)} trades améliore le P&L de ${abs(pnl_low_rr):.2f}')
    print(f'   → Win Rate amélioration: {wr_improvement:+.1f}%')
    print()
    print('💡 RECOMMANDATION: ACTIVER le filtre R:R >= 1.00')
elif pnl_low_rr > 0:
    print(f'⚠️ ATTENTION: Les trades R:R < 1.00 ont GAGNÉ ${pnl_low_rr:.2f}')
    print(f'   → Bloquer ces {len(low_rr)} trades RÉDUIT le P&L de ${pnl_low_rr:.2f}')
    print(f'   → MAIS améliore le Win Rate de {wr_improvement:+.1f}%')
    print()
    print('💡 DÉCISION: Au choix selon priorité (P&L brut vs Win Rate)')
else:
    print('🤷 NEUTRE: Les trades R:R < 1.00 sont à break-even')

print()
print('='*100)
print('📋 PATTERNS OBSERVÉS')
print('='*100)
print()

# Analyser les patterns de trades R:R < 1.00
es_low_wins = [t for t in es_low_rr if t[1] == 'WIN']
print('🔍 Trades R:R < 1.00 qui ont GAGNÉ:')
if es_low_wins or nq_low_rr_wins:
    print('   Ces trades ont fermé AVANT le TP (sortie prématurée ou trailing stop)')
    print('   → Souvent de petits gains (+$50-100)')
    print('   → TP trop loin ou marché n\'a pas suivi')
print()

print('🔍 Trades R:R < 1.00 qui ont PERDU:')
es_low_loss = [t for t in es_low_rr if t[1] == 'LOSS']
nq_low_loss = [t for t in nq_low_rr if t[1] == 'LOSS']
if es_low_loss or nq_low_loss:
    print('   Ces trades avaient TP trop proche ou SL trop large')
    print('   → Setup risqué dès le départ')
    print('   → Souvent des pertes normales ou plus grandes')
print()
