"""
📊 DASHBOARD PnL COMPARATIF ES vs NQ
====================================

Génère un dashboard visuel comparant les performances ES et NQ:
- Courbes de P&L cumulé
- Distribution des trades
- Hit rate par type d'exit
- Heatmap horaire
- Métriques clés côte à côte

Date: 15 Novembre 2025
"""

import pandas as pd
import numpy as np
from datetime import datetime
import json
from pathlib import Path


class PnLDashboard:
    """Générateur de dashboard PnL ES vs NQ"""

    def __init__(self, trades_file: str = "LAUNCH/daily_trades.json"):
        self.trades_file = trades_file
        self.tick_values = {'ES': 12.50, 'NQ': 5.00}

    def load_trades(self):
        """Charge les trades"""
        try:
            df = pd.read_json(self.trades_file)
            df['entry_time'] = pd.to_datetime(df['entry_time'])
            df['hour'] = df['entry_time'].dt.hour
            df['date'] = df['entry_time'].dt.date
            return df
        except Exception as e:
            print(f"Erreur chargement: {e}")
            return pd.DataFrame()

    def generate_ascii_chart(self, data, width=70, height=15, title=""):
        """Génère un graphique ASCII simple"""
        if len(data) == 0:
            return ""

        min_val = min(data)
        max_val = max(data)

        # Normaliser
        if max_val == min_val:
            normalized = [height // 2] * len(data)
        else:
            normalized = [int((v - min_val) / (max_val - min_val) * (height - 1)) for v in data]

        # Créer grille
        chart = []
        chart.append(f"\n{title}")
        chart.append("┌" + "─" * width + "┐")

        for row in range(height - 1, -1, -1):
            line = "│"
            for i, norm_val in enumerate(normalized):
                if int(i * width / len(data)) >= len(line) - 1:
                    if norm_val == row:
                        line += "●"
                    elif norm_val > row:
                        line += "│"
                    else:
                        line += " "

            # Remplir le reste
            while len(line) < width + 1:
                line += " "
            line += "│"

            # Ajouter valeur Y
            if row == height - 1:
                line += f" {max_val:+.1f}"
            elif row == 0:
                line += f" {min_val:+.1f}"
            elif row == height // 2:
                line += f" {(max_val + min_val) / 2:+.1f}"

            chart.append(line)

        chart.append("└" + "─" * width + "┘")
        return "\n".join(chart)

    def generate_dashboard(self):
        """Génère le dashboard complet"""

        df = self.load_trades()

        if df.empty:
            return "❌ Aucune donnée disponible"

        output = []

        # En-tête
        output.append("\n" + "=" * 90)
        output.append("📊 DASHBOARD PnL COMPARATIF - ES vs NQ")
        output.append("=" * 90)
        output.append(f"Période: {df['date'].min()} → {df['date'].max()}")
        output.append("")

        # Métriques clés côte à côte
        output.append("┌─────────────────────────────────────┬─────────────────────────────────────┐")
        output.append("│             ES (S&P 500)            │          NQ (Nasdaq-100)            │")
        output.append("├─────────────────────────────────────┼─────────────────────────────────────┤")

        for symbol in ['ES', 'NQ']:
            df_sym = df[df['symbol'] == symbol]

            if not df_sym.empty:
                n_trades = len(df_sym)
                n_win = (df_sym['pnl_ticks'] > 0).sum()
                winrate = n_win / n_trades * 100

                pnl_total = df_sym['pnl_ticks'].sum()
                pnl_per_trade = pnl_total / n_trades
                pnl_usd = pnl_total * self.tick_values[symbol]

                gross_profit = df_sym[df_sym['pnl_ticks'] > 0]['pnl_ticks'].sum()
                gross_loss = abs(df_sym[df_sym['pnl_ticks'] < 0]['pnl_ticks'].sum())
                profit_factor = gross_profit / gross_loss if gross_loss > 0 else 999.99

                if symbol == 'ES':
                    output.append(f"│  Trades:        {n_trades:4d}               │", end="")
                else:
                    output[-1] = output[-1].rstrip('│') + f"  Trades:        {n_trades:4d}               │"
                    output.append("")

                if symbol == 'ES':
                    output.append(f"│  Wins:          {n_win:4d} ({winrate:5.1f}%)       │", end="")
                else:
                    output[-1] = output[-1].rstrip('│') + f"  Wins:          {n_win:4d} ({winrate:5.1f}%)       │"
                    output.append("")

                if symbol == 'ES':
                    output.append(f"│  P&L Total:     {pnl_total:+7.1f} ticks       │", end="")
                else:
                    output[-1] = output[-1].rstrip('│') + f"  P&L Total:     {pnl_total:+7.1f} ticks       │"
                    output.append("")

                if symbol == 'ES':
                    output.append(f"│  P&L/trade:     {pnl_per_trade:+7.3f} ticks      │", end="")
                else:
                    output[-1] = output[-1].rstrip('│') + f"  P&L/trade:     {pnl_per_trade:+7.3f} ticks      │"
                    output.append("")

                if symbol == 'ES':
                    output.append(f"│  P&L USD:       ${pnl_usd:+9,.2f}        │", end="")
                else:
                    output[-1] = output[-1].rstrip('│') + f"  P&L USD:       ${pnl_usd:+9,.2f}        │"
                    output.append("")

                if symbol == 'ES':
                    output.append(f"│  Profit Factor: {profit_factor:6.2f}              │", end="")
                else:
                    output[-1] = output[-1].rstrip('│') + f"  Profit Factor: {profit_factor:6.2f}              │"
                    output.append("")

        output.append("└─────────────────────────────────────┴─────────────────────────────────────┘")
        output.append("")

        # Courbes P&L cumulé
        for symbol in ['ES', 'NQ']:
            df_sym = df[df['symbol'] == symbol].copy()
            df_sym = df_sym.sort_values('entry_time')

            if not df_sym.empty:
                cumulative_pnl = df_sym['pnl_ticks'].cumsum().tolist()
                chart = self.generate_ascii_chart(
                    cumulative_pnl,
                    width=70,
                    height=12,
                    title=f"📈 P&L Cumulé {symbol} (ticks)"
                )
                output.append(chart)
                output.append("")

        # Distribution des trades par heure
        output.append("=" * 90)
        output.append("🕐 DISTRIBUTION HORAIRE DES TRADES")
        output.append("=" * 90)
        output.append("")

        for symbol in ['ES', 'NQ']:
            df_sym = df[df['symbol'] == symbol]

            if not df_sym.empty:
                hourly = df_sym.groupby('hour').size()

                output.append(f"{symbol}:")
                output.append("")

                max_count = hourly.max() if len(hourly) > 0 else 1

                for hour in range(0, 24):
                    count = hourly.get(hour, 0)
                    bar_len = int(count / max_count * 40) if max_count > 0 else 0
                    bar = "█" * bar_len
                    output.append(f"  {hour:02d}h: {bar} {count}")

                output.append("")

        # Exit Breakdown
        output.append("=" * 90)
        output.append("🚪 EXIT BREAKDOWN")
        output.append("=" * 90)
        output.append("")

        if 'exit_reason' in df.columns:
            for symbol in ['ES', 'NQ']:
                df_sym = df[df['symbol'] == symbol]

                if not df_sym.empty:
                    exit_counts = df_sym['exit_reason'].value_counts()

                    output.append(f"{symbol}:")
                    for reason, count in exit_counts.items():
                        pct = count / len(df_sym) * 100
                        bar_len = int(pct / 2)
                        bar = "█" * bar_len
                        output.append(f"  {reason:15s}: {bar} {count:4d} ({pct:5.1f}%)")

                    output.append("")

        # Recommandation finale
        output.append("=" * 90)
        output.append("🎯 VERDICT")
        output.append("=" * 90)
        output.append("")

        es_pnl = df[df['symbol'] == 'ES']['pnl_ticks'].sum() if 'ES' in df['symbol'].values else 0
        nq_pnl = df[df['symbol'] == 'NQ']['pnl_ticks'].sum() if 'NQ' in df['symbol'].values else 0

        es_trades = len(df[df['symbol'] == 'ES']) if 'ES' in df['symbol'].values else 0
        nq_trades = len(df[df['symbol'] == 'NQ']) if 'NQ' in df['symbol'].values else 0

        es_ppt = es_pnl / es_trades if es_trades > 0 else 0
        nq_ppt = nq_pnl / nq_trades if nq_trades > 0 else 0

        if nq_ppt > es_ppt * 1.2:
            output.append("  ✅ FOCUS NQ RECOMMANDÉ")
            output.append(f"     NQ surperforme ES de {(nq_ppt/es_ppt - 1)*100:.0f}%")
        elif es_ppt > nq_ppt * 1.2:
            output.append("  ✅ FOCUS ES RECOMMANDÉ")
            output.append(f"     ES surperforme NQ de {(es_ppt/nq_ppt - 1)*100:.0f}%")
        else:
            output.append("  ⚖️ GARDER LES DEUX")
            output.append("     Performances équivalentes, diversification bénéfique")

        output.append("")
        output.append("=" * 90)
        output.append("")

        return "\n".join(output)

    def save_dashboard(self, output_file: str = "ml/output/dashboard_es_vs_nq.txt"):
        """Sauvegarde le dashboard dans un fichier"""
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)

        dashboard = self.generate_dashboard()

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(dashboard)

        print(f"✅ Dashboard sauvegardé: {output_file}")
        print(dashboard)

        return output_file


def main():
    """Point d'entrée principal"""
    dashboard = PnLDashboard()
    dashboard.save_dashboard()


if __name__ == "__main__":
    main()







