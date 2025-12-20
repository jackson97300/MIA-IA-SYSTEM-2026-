"""
🔬 BACKTEST ES MENTHORQ MAGNET V4.0 OPTIMIZED - 17 JOURS
========================================================
Version optimisée avec:
- TP: 18t (vs 12t)
- SL: 12t (vs 16t)
- Filtrage GEX_1/GEX_3
- Priorisation HVL/GEX_5
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import logging
import io

from backtester_es_pure_v2 import ESPureV2Backtester, BacktestResult, print_results

logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_PATH = Path(r"D:\MIA_IA_system\DATA_SIERRA_CHART\DATA_2025\NOVEMBRE")

DATES = [
    "20251105", "20251106", "20251107",
    "20251110", "20251111", "20251112", "20251113", "20251114",
    "20251117", "20251118", "20251119", "20251120", "20251121",
    "20251124", "20251125", "20251126", "20251127"
]

SYMBOL = "ES"
CHART_ID = 3

def find_data_file(date: str) -> Path:
    file_path = (
        BASE_PATH / date / f"CHART_{CHART_ID}" / "ML_READY" /
        f"ml_{SYMBOL}Z25_FUT_CME_{CHART_ID}.jsonl"
    )
    return file_path if file_path.exists() else None

def load_snapshots(file_path: Path) -> list:
    snapshots = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    snapshots.append(json.loads(line))
                except:
                    continue
    return snapshots

def merge_results(all_results: list) -> BacktestResult:
    merged = BacktestResult()

    for result in all_results:
        merged.trades.extend(result.trades)

    merged.total_trades = len(merged.trades)

    if not merged.trades:
        return merged

    winners = [t for t in merged.trades if t.pnl_usd > 0]
    losers = [t for t in merged.trades if t.pnl_usd <= 0]

    merged.winning_trades = len(winners)
    merged.losing_trades = len(losers)
    merged.win_rate = len(winners) / len(merged.trades) * 100
    merged.total_pnl_usd = sum(t.pnl_usd for t in merged.trades)
    merged.total_pnl_ticks = sum(t.pnl_ticks for t in merged.trades)
    merged.avg_win_usd = sum(t.pnl_usd for t in winners) / len(winners) if winners else 0
    merged.avg_loss_usd = sum(t.pnl_usd for t in losers) / len(losers) if losers else 0

    gross_profit = sum(t.pnl_usd for t in winners)
    gross_loss = abs(sum(t.pnl_usd for t in losers))
    merged.profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

    equity = 10000
    peak = 10000
    max_dd = 0

    for trade in merged.trades:
        equity += trade.pnl_usd
        if equity > peak:
            peak = equity
        dd = peak - equity
        max_dd = max(max_dd, dd)

    merged.max_drawdown_usd = max_dd

    for setup in set(t.setup_type for t in merged.trades):
        setup_trades = [t for t in merged.trades if t.setup_type == setup]
        setup_winners = [t for t in setup_trades if t.pnl_usd > 0]
        merged.by_setup[setup] = {
            'trades': len(setup_trades),
            'wins': len(setup_winners),
            'win_rate': len(setup_winners) / len(setup_trades) * 100,
            'pnl_usd': sum(t.pnl_usd for t in setup_trades),
            'avg_pnl': sum(t.pnl_usd for t in setup_trades) / len(setup_trades)
        }

    for trade in merged.trades:
        level_type = 'UNKNOWN'
        if 'HVL' in trade.level_type:
            level_type = 'HVL'
        elif 'GEX_5' in trade.level_type:
            level_type = 'GEX_5'
        elif 'GEX_2' in trade.level_type:
            level_type = 'GEX_2'
        elif 'CALL_RESISTANCE' in trade.level_type:
            level_type = 'CALL_RESISTANCE'
        elif 'PUT_SUPPORT' in trade.level_type:
            level_type = 'PUT_SUPPORT'

        if level_type not in merged.by_level:
            merged.by_level[level_type] = {'trades': 0, 'wins': 0, 'pnl_usd': 0}
        merged.by_level[level_type]['trades'] += 1
        if trade.pnl_usd > 0:
            merged.by_level[level_type]['wins'] += 1
        merged.by_level[level_type]['pnl_usd'] += trade.pnl_usd

    for level in merged.by_level:
        l = merged.by_level[level]
        l['win_rate'] = l['wins'] / l['trades'] * 100 if l['trades'] > 0 else 0

    for session in set(t.session for t in merged.trades):
        sess_trades = [t for t in merged.trades if t.session == session]
        sess_winners = [t for t in sess_trades if t.pnl_usd > 0]
        merged.by_session[session] = {
            'trades': len(sess_trades),
            'wins': len(sess_winners),
            'win_rate': len(sess_winners) / len(sess_trades) * 100,
            'pnl_usd': sum(t.pnl_usd for t in sess_trades)
        }

    for reason in set(t.exit_reason for t in merged.trades):
        merged.by_exit_reason[reason] = len([t for t in merged.trades if t.exit_reason == reason])

    return merged

def generate_html_report(result: BacktestResult, daily_results: dict) -> str:
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Backtest ES MenthorQ Magnet V4.0 OPTIMIZED - 17 Jours</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 20px; background: #0d1117; color: #c9d1d9; }}
        h1 {{ color: #58a6ff; border-bottom: 3px solid #58a6ff; padding-bottom: 10px; }}
        h2 {{ color: #79c0ff; margin-top: 30px; border-bottom: 2px solid #30363d; padding-bottom: 8px; }}
        .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; margin: 20px 0; }}
        .metric-card {{ background: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 15px; }}
        .metric-card h3 {{ margin: 0 0 10px 0; color: #58a6ff; font-size: 14px; }}
        .metric-card .value {{ font-size: 28px; font-weight: bold; color: #fff; }}
        .metric-card .label {{ font-size: 12px; color: #8b949e; margin-top: 5px; }}
        .positive {{ color: #3fb950 !important; }}
        .negative {{ color: #f85149 !important; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; background: #161b22; }}
        th {{ background: #21262d; color: #58a6ff; padding: 12px; text-align: left; border-bottom: 2px solid #30363d; }}
        td {{ padding: 10px 12px; border-bottom: 1px solid #30363d; }}
        tr:hover {{ background: #1c2128; }}
        .optimization {{ background: #1c2128; border-left: 4px solid #58a6ff; padding: 15px; margin: 20px 0; }}
    </style>
</head>
<body>
    <h1>📊 Backtest ES MenthorQ Magnet V4.0 OPTIMIZED - 17 Jours</h1>
    <div class="optimization">
        <h3 style="color: #58a6ff; margin-top: 0;">🔧 Optimisations Appliquées:</h3>
        <ul>
            <li>TP: 18t (vs 12t) → R:R 1.5:1</li>
            <li>SL: 12t (vs 16t) → Limiter pertes</li>
            <li>Filtrage GEX_1/GEX_3 (sous-performants)</li>
            <li>Priorisation HVL/GEX_5 (meilleurs résultats)</li>
            <li>Trailing stop plus agressif (8t activation)</li>
        </ul>
    </div>
    <p style="color: #8b949e;">Période: 5-27 Novembre 2025 | Total: {result.total_trades} trades</p>

    <div class="metrics">
        <div class="metric-card">
            <h3>Win Rate</h3>
            <div class="value {'positive' if result.win_rate >= 60 else 'negative'}">{result.win_rate:.1f}%</div>
            <div class="label">{result.winning_trades}W / {result.losing_trades}L</div>
        </div>
        <div class="metric-card">
            <h3>P&L Total</h3>
            <div class="value {'positive' if result.total_pnl_usd >= 0 else 'negative'}">${result.total_pnl_usd:.2f}</div>
            <div class="label">{result.total_pnl_ticks:.1f} ticks</div>
        </div>
        <div class="metric-card">
            <h3>Profit Factor</h3>
            <div class="value {'positive' if result.profit_factor >= 1 else 'negative'}">{result.profit_factor:.2f}</div>
            <div class="label">Gross P/L ratio</div>
        </div>
        <div class="metric-card">
            <h3>Max Drawdown</h3>
            <div class="value negative">${result.max_drawdown_usd:.2f}</div>
            <div class="label">Peak-to-trough</div>
        </div>
        <div class="metric-card">
            <h3>Avg Win</h3>
            <div class="value positive">${result.avg_win_usd:.2f}</div>
            <div class="label">Per winning trade</div>
        </div>
        <div class="metric-card">
            <h3>Avg Loss</h3>
            <div class="value negative">${result.avg_loss_usd:.2f}</div>
            <div class="label">Per losing trade</div>
        </div>
    </div>

    <h2>🎯 Par Niveau Magnet</h2>
    <table>
        <thead>
            <tr>
                <th>Niveau</th>
                <th>Trades</th>
                <th>Win Rate</th>
                <th>P&L</th>
            </tr>
        </thead>
        <tbody>
"""

    for level, stats in sorted(result.by_level.items(), key=lambda x: -x[1]['trades']):
        html += f"""
            <tr>
                <td>{level}</td>
                <td>{stats['trades']}</td>
                <td {'class="positive"' if stats['win_rate'] >= 60 else 'class="negative"' if stats['win_rate'] < 50 else ''}>{stats['win_rate']:.1f}%</td>
                <td {'class="positive"' if stats['pnl_usd'] >= 0 else 'class="negative"'}>${stats['pnl_usd']:.2f}</td>
            </tr>
"""

    html += """
        </tbody>
    </table>

    <p style="margin-top: 50px; color: #8b949e; text-align: center;">
        Généré le """ + datetime.now().strftime("%d/%m/%Y %H:%M:%S") + """<br>
        ES MenthorQ Magnet V4.0 OPTIMIZED
    </p>
</body>
</html>
"""

    return html

def main():
    if sys.stdout.encoding != 'utf-8':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

    print("\n" + "="*70)
    print("BACKTEST ES MENTHORQ MAGNET V4.0 OPTIMIZED - 17 JOURS")
    print("="*70 + "\n")

    if not BASE_PATH.exists():
        print(f"❌ ERREUR: Le chemin {BASE_PATH} n'existe pas!")
        return

    from es_menthorq_magnet_v4_optimized import ESMenthorQMagnetV4Optimized

    all_results = []
    daily_results = {}
    total_snapshots = 0

    for date in DATES:
        file_path = find_data_file(date)

        if not file_path:
            logger.warning(f"⚠️ Fichier non trouvé pour {date}")
            continue

        logger.info(f"📅 Processing {date}...")

        snapshots = load_snapshots(file_path)
        total_snapshots += len(snapshots)
        logger.info(f"   Loaded {len(snapshots):,} snapshots")

        temp_file = Path(f"temp_{date}.jsonl")
        with open(temp_file, 'w') as f:
            for snap in snapshots:
                f.write(json.dumps(snap) + '\n')

        try:
            strategy = ESMenthorQMagnetV4Optimized()
            backtester = ESPureV2Backtester(str(temp_file))
            backtester.strategy = strategy

            result = backtester.run()

            all_results.append(result)
            daily_results[date] = result

            logger.info(f"   ✅ {result.total_trades} trades | WR: {result.win_rate:.1f}% | P&L: ${result.total_pnl_usd:.2f}")

        except Exception as e:
            logger.error(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if temp_file.exists():
                temp_file.unlink()

    logger.info(f"\n📊 Merging results from {len(all_results)} days...")
    merged = merge_results(all_results)

    print("\n" + "="*70)
    print("📊 RÉSULTATS GLOBAUX - 17 JOURS (OPTIMIZED)")
    print("="*70 + "\n")
    print_results(merged)

    html = generate_html_report(merged, daily_results)

    report_path = Path("BACKTEST_REPORT_17_DAYS_ES_MAGNET_V4_OPTIMIZED.html")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"\n✅ Rapport HTML généré: {report_path.absolute()}")
    print(f"   Total snapshots traités: {total_snapshots:,}")
    print(f"   Total trades: {merged.total_trades}")
    print(f"   Win Rate: {merged.win_rate:.1f}%")
    print(f"   P&L: ${merged.total_pnl_usd:.2f}")
    print("\n" + "="*70 + "\n")

if __name__ == "__main__":
    main()




