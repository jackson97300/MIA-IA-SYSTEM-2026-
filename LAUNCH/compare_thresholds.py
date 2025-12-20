#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')

print('='*100)
print('📊 COMPARAISON SEUILS: ACTUELS vs RECOMMANDÉS (Basés sur analyse 88 trades ES+NQ)')
print('='*100)
print()

# Seuils actuels
actuels = {
    "ES": {
        "total": 0.24,
        "layer1": 0.30,  # MenthorQ
        "layer2": 0.17,  # OrderFlow
        "layer3": 0.20   # Context
    },
    "NQ": {
        "total": 0.24,
        "layer1": 0.30,  # MenthorQ
        "layer2": 0.17,  # OrderFlow
        "layer3": 0.20   # Context
    }
}

# Seuils recommandés
recommandes = {
    "ES": {
        "total": 0.35,  # Basé sur meilleure config
        "layer1": 0.70,  # MenthorQ
        "layer2": 0.08,  # OrderFlow (pas discriminant)
        "layer3": 0.12   # Context
    },
    "NQ": {
        "total": 0.35,  # Estimation
        "layer1": 0.40,  # MenthorQ
        "layer2": 0.22,  # OrderFlow (TRÈS discriminant!)
        "layer3": 0.16   # Context (TRÈS discriminant!)
    }
}

# Résultats observés
resultats = {
    "ES": {
        "trades_total": 40,
        "win_rate_actuel": "52.5%",
        "pnl_actuel": "+$1,041",
        "win_rate_prevu": "52-60%",
        "pnl_prevu": "+$1,400+",
        "trades_prevu": "25/40 (62%)"
    },
    "NQ": {
        "trades_total": 48,
        "win_rate_actuel": "35.4%",
        "pnl_actuel": "+$715",
        "win_rate_prevu": "70%",
        "pnl_prevu": "+$2,420",
        "trades_prevu": "10/48 (21%)"
    }
}

print('┌' + '─'*98 + '┐')
print('│' + ' '*40 + 'ES (E-mini S&P 500)' + ' '*39 + '│')
print('├' + '─'*98 + '┤')
print('│ Seuil            │ ACTUEL │ RECOMMANDÉ │ Δ      │ Impact                                    │')
print('├' + '─'*18 + '┼' + '─'*8 + '┼' + '─'*12 + '┼' + '─'*8 + '┼' + '─'*43 + '┤')

# ES Total Confidence
delta = recommandes["ES"]["total"] - actuels["ES"]["total"]
signe = "⬆️" if delta > 0 else "⬇️"
print(f'│ Total Confidence │  {actuels["ES"]["total"]:.2f}  │    {recommandes["ES"]["total"]:.2f}    │ {delta:+.2f} {signe} │ Plus sélectif                             │')

# ES Layer 1
delta = recommandes["ES"]["layer1"] - actuels["ES"]["layer1"]
signe = "⬆️" if delta > 0 else "⬇️"
print(f'│ Layer1 (MenthorQ)│  {actuels["ES"]["layer1"]:.2f}  │    {recommandes["ES"]["layer1"]:.2f}    │ {delta:+.2f} {signe} │ Gamma walls + GEX doivent être SOLIDES   │')

# ES Layer 2
delta = recommandes["ES"]["layer2"] - actuels["ES"]["layer2"]
signe = "⬆️" if delta > 0 else "⬇️"
print(f'│ Layer2 (OrderFlow│  {actuels["ES"]["layer2"]:.2f}  │    {recommandes["ES"]["layer2"]:.2f}    │ {delta:+.2f} {signe} │ Pas discriminant sur ES, seuil bas OK     │')

# ES Layer 3
delta = recommandes["ES"]["layer3"] - actuels["ES"]["layer3"]
signe = "⬆️" if delta > 0 else "⬇️"
print(f'│ Layer3 (Context) │  {actuels["ES"]["layer3"]:.2f}  │    {recommandes["ES"]["layer3"]:.2f}    │ {delta:+.2f} {signe} │ Un peu plus permissif                     │')

print('├' + '─'*18 + '┼' + '─'*8 + '┼' + '─'*12 + '┼' + '─'*8 + '┼' + '─'*43 + '┤')
print(f'│ Win Rate         │ {resultats["ES"]["win_rate_actuel"]:^6} │  {resultats["ES"]["win_rate_prevu"]:^8}  │        │ Amélioration attendue: +0 à +7.5%         │')
print(f'│ P&L Total        │ {resultats["ES"]["pnl_actuel"]:>6} │ {resultats["ES"]["pnl_prevu"]:>10} │        │ Meilleure qualité des trades             │')
print(f'│ Trades filtrés   │   40   │ {resultats["ES"]["trades_prevu"]:^10} │        │ 38% des trades bloqués (qualité++)       │')
print('└' + '─'*98 + '┘')
print()

print('┌' + '─'*98 + '┐')
print('│' + ' '*39 + 'NQ (E-mini Nasdaq 100)' + ' '*38 + '│')
print('├' + '─'*98 + '┤')
print('│ Seuil            │ ACTUEL │ RECOMMANDÉ │ Δ      │ Impact                                    │')
print('├' + '─'*18 + '┼' + '─'*8 + '┼' + '─'*12 + '┼' + '─'*8 + '┼' + '─'*43 + '┤')

# NQ Total Confidence
delta = recommandes["NQ"]["total"] - actuels["NQ"]["total"]
signe = "⬆️" if delta > 0 else "⬇️"
print(f'│ Total Confidence │  {actuels["NQ"]["total"]:.2f}  │    {recommandes["NQ"]["total"]:.2f}    │ {delta:+.2f} {signe} │ Plus sélectif                             │')

# NQ Layer 1
delta = recommandes["NQ"]["layer1"] - actuels["NQ"]["layer1"]
signe = "⬆️" if delta > 0 else "⬇️"
print(f'│ Layer1 (MenthorQ)│  {actuels["NQ"]["layer1"]:.2f}  │    {recommandes["NQ"]["layer1"]:.2f}    │ {delta:+.2f} {signe} │ Plus permissif (MenthorQ moins important) │')

# NQ Layer 2
delta = recommandes["NQ"]["layer2"] - actuels["NQ"]["layer2"]
signe = "⬆️" if delta > 0 else "⬇️"
print(f'│ Layer2 (OrderFlow│  {actuels["NQ"]["layer2"]:.2f}  │    {recommandes["NQ"]["layer2"]:.2f}    │ {delta:+.2f} {signe} │ 🔥 CRITIQUE! OrderFlow TRÈS discriminant │')

# NQ Layer 3
delta = recommandes["NQ"]["layer3"] - actuels["NQ"]["layer3"]
signe = "⬆️" if delta > 0 else "⬇️"
print(f'│ Layer3 (Context) │  {actuels["NQ"]["layer3"]:.2f}  │    {recommandes["NQ"]["layer3"]:.2f}    │ {delta:+.2f} {signe} │ 🔥 CRITIQUE! Context TRÈS discriminant   │')

print('├' + '─'*18 + '┼' + '─'*8 + '┼' + '─'*12 + '┼' + '─'*8 + '┼' + '─'*43 + '┤')
print(f'│ Win Rate         │ {resultats["NQ"]["win_rate_actuel"]:^6} │   {resultats["NQ"]["win_rate_prevu"]:^6}   │        │ 🚀 ÉNORME amélioration: +34.6%!          │')
print(f'│ P&L Total        │ {resultats["NQ"]["pnl_actuel"]:>6} │ {resultats["NQ"]["pnl_prevu"]:>10} │        │ 🚀 P&L x3.4 avec moins de trades!        │')
print(f'│ Trades filtrés   │   48   │ {resultats["NQ"]["trades_prevu"]:^10} │        │ 79% des trades bloqués (ultra-sélectif)  │')
print('└' + '─'*98 + '┘')
print()

print('='*100)
print('📋 RÉSUMÉ DES CHANGEMENTS')
print('='*100)
print()
print('🎯 ES (E-mini S&P 500):')
print('  ✅ MenthorQ:  0.30 → 0.70  (+133%)  ← Gamma walls doivent être TRÈS clairs')
print('  ✅ OrderFlow: 0.17 → 0.08  (-53%)   ← Pas discriminant, autoriser scores bas')
print('  ✅ Context:   0.20 → 0.12  (-40%)   ← Plus permissif')
print()
print('  💡 Stratégie ES: Focus sur qualité MenthorQ, OrderFlow moins important')
print('  📊 Impact: Win Rate stable (~52%), mais meilleure qualité (moins de faux signaux)')
print()
print('🎯 NQ (E-mini Nasdaq 100):')
print('  ✅ MenthorQ:  0.30 → 0.40  (+33%)   ← Légère hausse')
print('  🔥 OrderFlow: 0.17 → 0.22  (+29%)   ← CRITIQUE! Doit être > 0.22')
print('  🔥 Context:   0.20 → 0.16  (-20%)   ← Légère baisse mais > 0.16 OBLIGATOIRE')
print()
print('  💡 Stratégie NQ: OrderFlow + Context sont discriminants, MenthorQ secondaire')
print('  📊 Impact: Win Rate 35% → 70% (+35 points!) avec filtrage strict')
print()
print('='*100)
print('⚠️  POINTS D\'ATTENTION')
print('='*100)
print()
print('1. 📉 NQ va avoir BEAUCOUP MOINS de trades (48 → 10, soit -79%)')
print('   → C\'est VOULU: on préfère 10 trades à 70% WR que 48 trades à 35% WR')
print()
print('2. 🎯 ES garde un volume correct (40 → 25, soit -38%)')
print('   → Bon équilibre entre volume et qualité')
print()
print('3. 🔄 Les seuils sont DIFFÉRENTS entre ES et NQ')
print('   → C\'est NORMAL: chaque instrument a ses propres caractéristiques')
print()
print('4. 📊 Confluence totale peut rester à 0.24 (le filtrage se fait sur les layers)')
print('   → Les seuils individuels font le travail de sélection')
print()
print('='*100)
