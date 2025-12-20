#!/usr/bin/env python3
"""
Analyse Performance - 1er Decembre 2025
"""
import re
from collections import defaultdict

# Lire les trades
with open('logs_advanced/trades/trades_20251201.log', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Parser les trades
trades = []
entries = {}

for line in lines:
    line = line.strip()
    if not line:
        continue

    # Parser timestamp
    time_match = re.match(r'(\d{2}:\d{2}:\d{2})', line)
    if not time_match:
        continue
    time_str = time_match.group(1)

    # Extraire symbole
    symbol_match = re.search(r'\[(\w+)\]', line)
    if not symbol_match:
        continue
    symbol = symbol_match.group(1)

    # Parser le JSON
    json_match = re.search(r'\{.*\}', line)
    if not json_match:
        continue

    try:
        data = eval(json_match.group())
    except:
        continue

    if 'ENTRY' in line:
        key = f'{symbol}_{time_str}'
        entries[key] = {
            'time': time_str,
            'symbol': symbol,
            'direction': data.get('direction'),
            'entry_price': data.get('price'),
            'sl': data.get('sl'),
            'tp': data.get('tp'),
            'confidence': data.get('confidence', 0)
        }

    elif 'EXIT' in line:
        trade = {
            'time': time_str,
            'symbol': symbol,
            'direction': data.get('direction'),
            'entry_price': data.get('entry_price'),
            'exit_price': data.get('exit_price'),
            'pnl_usd': data.get('pnl_usd', 0),
            'exit_reason': data.get('exit_reason', ''),
            'mae': data.get('mae', 0),
            'mfe': data.get('mfe', 0),
            'duration_ms': data.get('duration_ms', 0),
            'confidence': 0
        }

        # Try to find matching entry
        for k, v in entries.items():
            if v['symbol'] == symbol and v['direction'] == trade['direction']:
                trade['confidence'] = v['confidence']
                trade['sl'] = v.get('sl')
                trade['tp'] = v.get('tp')
                break

        trades.append(trade)

# Analyse
print('='*70)
print('  ANALYSE PERFORMANCE - 1er Decembre 2025')
print('='*70)

# Stats globales
total = len(trades)
wins = [t for t in trades if t['pnl_usd'] > 0]
losses = [t for t in trades if t['pnl_usd'] <= 0]
total_pnl = sum(t['pnl_usd'] for t in trades)

print(f'\n GLOBAL: {total} trades | W:{len(wins)} L:{len(losses)} | WR: {len(wins)/total*100:.1f}% | PnL: ${total_pnl:+.2f}')
print(f' Avg Win: ${sum(t["pnl_usd"] for t in wins)/len(wins):.2f}' if wins else '')
print(f' Avg Loss: ${sum(t["pnl_usd"] for t in losses)/len(losses):.2f}' if losses else '')

# Par symbole
print('\n' + '='*70)
print(' PAR INSTRUMENT')
print('='*70)
print(f' {"Symbol":<8} {"Trades":>7} {"W/L":>8} {"WR%":>7} {"PnL":>12} {"AvgW":>10} {"AvgL":>10}')
print('-'*70)
for sym in ['ES', 'NQ', 'RTY']:
    sym_trades = [t for t in trades if t['symbol'] == sym]
    if not sym_trades:
        continue
    sym_wins = [t for t in sym_trades if t['pnl_usd'] > 0]
    sym_losses = [t for t in sym_trades if t['pnl_usd'] <= 0]
    sym_pnl = sum(t['pnl_usd'] for t in sym_trades)
    wr = len(sym_wins)/len(sym_trades)*100 if sym_trades else 0
    avg_win = sum(t['pnl_usd'] for t in sym_wins)/len(sym_wins) if sym_wins else 0
    avg_loss = sum(t['pnl_usd'] for t in sym_losses)/len(sym_losses) if sym_losses else 0
    print(f' {sym:<8} {len(sym_trades):>7} {len(sym_wins):>3}/{len(sym_losses):<4} {wr:>6.1f}% ${sym_pnl:>+10.2f} ${avg_win:>+8.2f} ${avg_loss:>+8.2f}')

# Par direction
print('\n' + '='*70)
print(' PAR DIRECTION')
print('='*70)
print(f' {"Dir":<8} {"Trades":>7} {"W/L":>8} {"WR%":>7} {"PnL":>12} {"AvgW":>10} {"AvgL":>10}')
print('-'*70)
for dir in ['LONG', 'SHORT']:
    dir_trades = [t for t in trades if t['direction'] == dir]
    if not dir_trades:
        continue
    dir_wins = [t for t in dir_trades if t['pnl_usd'] > 0]
    dir_losses = [t for t in dir_trades if t['pnl_usd'] <= 0]
    dir_pnl = sum(t['pnl_usd'] for t in dir_trades)
    wr = len(dir_wins)/len(dir_trades)*100 if dir_trades else 0
    avg_win = sum(t['pnl_usd'] for t in dir_wins)/len(dir_wins) if dir_wins else 0
    avg_loss = sum(t['pnl_usd'] for t in dir_losses)/len(dir_losses) if dir_losses else 0
    print(f' {dir:<8} {len(dir_trades):>7} {len(dir_wins):>3}/{len(dir_losses):<4} {wr:>6.1f}% ${dir_pnl:>+10.2f} ${avg_win:>+8.2f} ${avg_loss:>+8.2f}')

# Par session
print('\n' + '='*70)
print(' PAR SESSION')
print('='*70)
sessions = {
    'London (08-11)': (8, 11),
    'US Morning (15-17)': (15, 17),
    'Power Hour (20-21:30)': (20, 22),
    'Off Hours': None
}

for sess_name, hours in sessions.items():
    if hours:
        sess_trades = [t for t in trades if hours[0] <= int(t['time'][:2]) < hours[1]]
    else:
        # Off hours = tout ce qui n'est pas dans les sessions
        sess_trades = [t for t in trades if not (8 <= int(t['time'][:2]) < 11 or 15 <= int(t['time'][:2]) < 17 or 20 <= int(t['time'][:2]) < 22)]

    if not sess_trades:
        print(f' {sess_name}: 0 trades')
        continue

    sess_wins = [t for t in sess_trades if t['pnl_usd'] > 0]
    sess_pnl = sum(t['pnl_usd'] for t in sess_trades)
    wr = len(sess_wins)/len(sess_trades)*100 if sess_trades else 0
    print(f' {sess_name}: {len(sess_trades)} trades | W:{len(sess_wins)}/L:{len(sess_trades)-len(sess_wins)} | WR: {wr:.1f}% | PnL: ${sess_pnl:+.2f}')

# Par heure
print('\n' + '='*70)
print(' PAR HEURE')
print('='*70)
print(f' {"Heure":>6} {"Trades":>7} {"W/L":>8} {"WR%":>7} {"PnL":>12}')
print('-'*50)
for h in range(9, 22):
    h_trades = [t for t in trades if t['time'].startswith(f'{h:02d}:')]
    if not h_trades:
        continue
    h_wins = [t for t in h_trades if t['pnl_usd'] > 0]
    h_pnl = sum(t['pnl_usd'] for t in h_trades)
    wr = len(h_wins)/len(h_trades)*100 if h_trades else 0
    emoji = '++' if h_pnl > 100 else '+' if h_pnl > 0 else '--' if h_pnl < -100 else '-' if h_pnl < 0 else '='
    print(f' {h:02d}h00 {len(h_trades):>7} {len(h_wins):>3}/{len(h_trades)-len(h_wins):<4} {wr:>6.1f}% ${h_pnl:>+10.2f} {emoji}')

# Analyse stop hunts
print('\n' + '='*70)
print(' STOP HUNTS POTENTIELS (duree moins de 60s + perte)')
print('='*70)
stop_hunts = [t for t in trades if t['pnl_usd'] < 0 and t['duration_ms'] < 60000 and t['duration_ms'] > 0]
total_sh_loss = sum(t['pnl_usd'] for t in stop_hunts)
print(f' Stop hunts detectes: {len(stop_hunts)} trades')
print(f' PnL perdu: ${total_sh_loss:.2f}')
print(f' % des pertes totales: {total_sh_loss / sum(t["pnl_usd"] for t in losses) * 100:.1f}%' if losses else '')

print('\n Details:')
for t in sorted(stop_hunts, key=lambda x: x['pnl_usd'])[:10]:
    print(f'   {t["time"]} {t["symbol"]} {t["direction"]} | Duree: {t["duration_ms"]/1000:.1f}s | PnL: ${t["pnl_usd"]:.2f} | MFE: {t["mfe"]} | MAE: {t["mae"]}')

# Analyse confidence
print('\n' + '='*70)
print(' DISTRIBUTION PAR CONFIDENCE')
print('='*70)
ranges = [(0.0, 0.7), (0.7, 0.8), (0.8, 0.9), (0.9, 1.0), (1.0, 1.5), (1.5, 2.0)]
print(f' {"Range":<12} {"Trades":>7} {"W/L":>8} {"WR%":>7} {"PnL":>12}')
print('-'*55)
for low, high in ranges:
    conf_trades = [t for t in trades if low <= t['confidence'] < high]
    if not conf_trades:
        continue
    conf_wins = [t for t in conf_trades if t['pnl_usd'] > 0]
    conf_pnl = sum(t['pnl_usd'] for t in conf_trades)
    wr = len(conf_wins)/len(conf_trades)*100 if conf_trades else 0
    print(f' {low:.1f}-{high:.1f}     {len(conf_trades):>7} {len(conf_wins):>3}/{len(conf_trades)-len(conf_wins):<4} {wr:>6.1f}% ${conf_pnl:>+10.2f}')

# Seuil optimal
print('\n' + '='*70)
print(' SEUIL OPTIMAL DE CONFIDENCE')
print('='*70)
print(f' {"Seuil":<8} {"Trades":>7} {"W/L":>8} {"WR%":>7} {"PnL":>12} {"Recommandation":>20}')
print('-'*70)
for threshold in [0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 1.00, 1.10]:
    th_trades = [t for t in trades if t['confidence'] >= threshold]
    if not th_trades:
        continue
    th_wins = [t for t in th_trades if t['pnl_usd'] > 0]
    th_pnl = sum(t['pnl_usd'] for t in th_trades)
    wr = len(th_wins)/len(th_trades)*100 if th_trades else 0
    recommendation = 'OPTIMAL' if wr >= 50 and len(th_trades) >= 10 else 'Trop peu' if len(th_trades) < 10 else 'WR faible'
    print(f' >={threshold:.2f}   {len(th_trades):>7} {len(th_wins):>3}/{len(th_trades)-len(th_wins):<4} {wr:>6.1f}% ${th_pnl:>+10.2f} {recommendation:>20}')

# Patterns gagnants
print('\n' + '='*70)
print(' PATTERNS GAGNANTS (WR > 50%, min 3 trades)')
print('='*70)

# Symbol + Direction
for sym in ['ES', 'NQ']:
    for dir in ['LONG', 'SHORT']:
        pattern_trades = [t for t in trades if t['symbol'] == sym and t['direction'] == dir]
        if len(pattern_trades) < 3:
            continue
        wins = [t for t in pattern_trades if t['pnl_usd'] > 0]
        wr = len(wins)/len(pattern_trades)*100
        pnl = sum(t['pnl_usd'] for t in pattern_trades)
        if wr >= 50:
            print(f' ++ {sym} {dir}: {len(pattern_trades)} trades | WR: {wr:.1f}% | PnL: ${pnl:+.2f}')
        else:
            print(f' -- {sym} {dir}: {len(pattern_trades)} trades | WR: {wr:.1f}% | PnL: ${pnl:+.2f}')

# Patterns perdants
print('\n' + '='*70)
print(' PATTERNS PERDANTS (WR < 40%)')
print('='*70)

for sym in ['ES', 'NQ']:
    for dir in ['LONG', 'SHORT']:
        pattern_trades = [t for t in trades if t['symbol'] == sym and t['direction'] == dir]
        if len(pattern_trades) < 3:
            continue
        wins = [t for t in pattern_trades if t['pnl_usd'] > 0]
        wr = len(wins)/len(pattern_trades)*100
        pnl = sum(t['pnl_usd'] for t in pattern_trades)
        if wr < 40:
            print(f' PROBLEME: {sym} {dir}: {len(pattern_trades)} trades | WR: {wr:.1f}% | PnL: ${pnl:+.2f}')

# Points positifs
print('\n' + '='*70)
print(' POINTS POSITIFS')
print('='*70)
# Meilleur trade
best_trade = max(trades, key=lambda t: t['pnl_usd'])
print(f' Meilleur trade: {best_trade["symbol"]} {best_trade["direction"]} @ {best_trade["time"]} = ${best_trade["pnl_usd"]:+.2f}')

# Meilleure serie
current_streak = 0
best_streak = 0
for t in trades:
    if t['pnl_usd'] > 0:
        current_streak += 1
        best_streak = max(best_streak, current_streak)
    else:
        current_streak = 0
print(f' Meilleure serie gagnante: {best_streak} trades consecutifs')

# TP Rate
tp_hits = [t for t in trades if 'TP' in str(t['exit_reason']).upper()]
print(f' TP Hit Rate: {len(tp_hits)/len(trades)*100:.1f}% ({len(tp_hits)}/{len(trades)})')

print('\n' + '='*70)
print(' FIN ANALYSE')
print('='*70)
