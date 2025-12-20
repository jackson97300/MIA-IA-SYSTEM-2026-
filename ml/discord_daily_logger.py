"""
📢 LOGGER DISCORD COMPACT - Résumé Quotidien
============================================

Envoie un résumé quotidien compact vers Discord:
- P&L du jour par symbole
- Nombre de trades
- WinRate
- Meilleur/Pire trade
- Exit breakdown rapide

Date: 15 Novembre 2025
"""

import json
from datetime import datetime, timedelta
from pathlib import Path


class DiscordDailySummary:
    """Générateur de résumé quotidien pour Discord"""

    def __init__(self, trades_file: str = "LAUNCH/daily_trades.json"):
        self.trades_file = trades_file
        self.tick_values = {'ES': 12.50, 'NQ': 5.00, 'RTY': 5.00}

    def load_today_trades(self):
        """Charge les trades du jour"""
        try:
            with open(self.trades_file, 'r') as f:
                trades = json.load(f)

            # Filtrer trades du jour
            today = datetime.now().date()
            today_trades = []

            for trade in trades:
                entry_time = datetime.fromisoformat(trade['entry_time'].replace('Z', '+00:00'))
                if entry_time.date() == today:
                    today_trades.append(trade)

            return today_trades
        except Exception as e:
            print(f"Erreur chargement: {e}")
            return []

    def generate_summary(self):
        """Génère le résumé quotidien"""

        trades = self.load_today_trades()

        if not trades:
            return {
                "content": "📊 **RÉSUMÉ QUOTIDIEN** - Aucun trade aujourd'hui",
                "embeds": []
            }

        # Analyser par symbole
        stats = {}

        for symbol in ['ES', 'NQ']:
            symbol_trades = [t for t in trades if t.get('symbol') == symbol]

            if not symbol_trades:
                continue

            n_trades = len(symbol_trades)
            wins = sum(1 for t in symbol_trades if t.get('pnl_ticks', 0) > 0)
            winrate = wins / n_trades * 100

            pnl_ticks = sum(t.get('pnl_ticks', 0) for t in symbol_trades)
            pnl_usd = pnl_ticks * self.tick_values[symbol]

            best_trade = max(symbol_trades, key=lambda t: t.get('pnl_ticks', 0))
            worst_trade = min(symbol_trades, key=lambda t: t.get('pnl_ticks', 0))

            # Exit breakdown
            exit_reasons = {}
            for t in symbol_trades:
                reason = t.get('exit_reason', 'UNKNOWN')
                exit_reasons[reason] = exit_reasons.get(reason, 0) + 1

            stats[symbol] = {
                'trades': n_trades,
                'wins': wins,
                'losses': n_trades - wins,
                'winrate': winrate,
                'pnl_ticks': pnl_ticks,
                'pnl_usd': pnl_usd,
                'best_trade': best_trade.get('pnl_ticks', 0),
                'worst_trade': worst_trade.get('pnl_ticks', 0),
                'exit_reasons': exit_reasons
            }

        # Construire embed Discord
        embeds = []

        # En-tête
        total_pnl_usd = sum(s['pnl_usd'] for s in stats.values())
        total_trades = sum(s['trades'] for s in stats.values())

        color = 0x00FF00 if total_pnl_usd > 0 else 0xFF0000  # Vert si positif, rouge si négatif

        # Embed principal
        embed_main = {
            "title": f"📊 RÉSUMÉ QUOTIDIEN - {datetime.now().strftime('%d/%m/%Y')}",
            "color": color,
            "fields": [
                {
                    "name": "💰 P&L Total",
                    "value": f"${total_pnl_usd:+,.2f}",
                    "inline": True
                },
                {
                    "name": "📈 Trades",
                    "value": f"{total_trades}",
                    "inline": True
                },
                {
                    "name": "⏱️ Timestamp",
                    "value": datetime.now().strftime('%H:%M:%S UTC'),
                    "inline": True
                }
            ]
        }

        embeds.append(embed_main)

        # Embed par symbole
        for symbol, data in stats.items():
            pnl_emoji = "🟢" if data['pnl_ticks'] > 0 else "🔴"

            embed_symbol = {
                "title": f"{pnl_emoji} {symbol} (S&P 500)" if symbol == 'ES' else f"{pnl_emoji} {symbol} (Nasdaq-100)",
                "color": 0x00FF00 if data['pnl_ticks'] > 0 else 0xFF0000,
                "fields": [
                    {
                        "name": "Trades",
                        "value": f"✅ {data['wins']} / ❌ {data['losses']} ({data['winrate']:.1f}%)",
                        "inline": False
                    },
                    {
                        "name": "P&L",
                        "value": f"{data['pnl_ticks']:+.1f} ticks (${data['pnl_usd']:+,.2f})",
                        "inline": False
                    },
                    {
                        "name": "Meilleur Trade",
                        "value": f"+{data['best_trade']:.1f} ticks",
                        "inline": True
                    },
                    {
                        "name": "Pire Trade",
                        "value": f"{data['worst_trade']:+.1f} ticks",
                        "inline": True
                    }
                ]
            }

            # Ajouter exit breakdown
            exit_str = " | ".join([f"{reason}: {count}" for reason, count in sorted(data['exit_reasons'].items(), key=lambda x: x[1], reverse=True)])

            if exit_str:
                embed_symbol['fields'].append({
                    "name": "🚪 Exit Breakdown",
                    "value": exit_str,
                    "inline": False
                })

            embeds.append(embed_symbol)

        # Message complet
        message = {
            "content": f"@here **RÉSUMÉ QUOTIDIEN** - {datetime.now().strftime('%d %B %Y')}",
            "embeds": embeds
        }

        return message

    def generate_compact_text(self):
        """Génère un résumé texte compact (alternative à embed)"""

        trades = self.load_today_trades()

        if not trades:
            return "📊 **RÉSUMÉ QUOTIDIEN** - Aucun trade aujourd'hui"

        lines = []
        lines.append("```")
        lines.append("=" * 60)
        lines.append(f"📊 RÉSUMÉ QUOTIDIEN - {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        lines.append("=" * 60)
        lines.append("")

        total_pnl = 0
        total_trades = 0

        for symbol in ['ES', 'NQ']:
            symbol_trades = [t for t in trades if t.get('symbol') == symbol]

            if not symbol_trades:
                continue

            n_trades = len(symbol_trades)
            wins = sum(1 for t in symbol_trades if t.get('pnl_ticks', 0) > 0)
            winrate = wins / n_trades * 100

            pnl_ticks = sum(t.get('pnl_ticks', 0) for t in symbol_trades)
            pnl_usd = pnl_ticks * self.tick_values[symbol]

            total_pnl += pnl_usd
            total_trades += n_trades

            emoji = "🟢" if pnl_ticks > 0 else "🔴"

            lines.append(f"{emoji} {symbol}")
            lines.append(f"  Trades:  {n_trades} (✅ {wins} / ❌ {n_trades - wins}) - WR {winrate:.1f}%")
            lines.append(f"  P&L:     {pnl_ticks:+.1f} ticks (${pnl_usd:+,.2f})")

            # Exit breakdown
            exit_reasons = {}
            for t in symbol_trades:
                reason = t.get('exit_reason', 'UNKNOWN')
                exit_reasons[reason] = exit_reasons.get(reason, 0) + 1

            exit_str = ", ".join([f"{reason}:{count}" for reason, count in sorted(exit_reasons.items(), key=lambda x: x[1], reverse=True)])
            lines.append(f"  Exits:   {exit_str}")
            lines.append("")

        lines.append("-" * 60)
        emoji_total = "🟢" if total_pnl > 0 else "🔴"
        lines.append(f"{emoji_total} TOTAL: {total_trades} trades | ${total_pnl:+,.2f}")
        lines.append("=" * 60)
        lines.append("```")

        return "\n".join(lines)

    def send_to_discord(self, webhook_url: str = None):
        """Envoie le résumé à Discord via webhook"""

        if not webhook_url:
            print("⚠️ Webhook URL non fourni, affichage console uniquement")
            print(self.generate_compact_text())
            return

        import requests

        message = self.generate_summary()

        try:
            response = requests.post(webhook_url, json=message)

            if response.status_code == 204:
                print("✅ Résumé envoyé à Discord")
            else:
                print(f"❌ Erreur Discord: {response.status_code}")
                print(response.text)
        except Exception as e:
            print(f"❌ Erreur envoi: {e}")

    def save_summary(self, output_file: str = "ml/output/daily_summary.txt"):
        """Sauvegarde le résumé dans un fichier"""
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)

        summary = self.generate_compact_text()

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(summary)

        print(f"✅ Résumé sauvegardé: {output_file}")
        print(summary)

        return output_file


def main():
    """Point d'entrée principal"""

    # Exemple d'utilisation
    logger = DiscordDailySummary()

    # Option 1: Afficher dans console
    print(logger.generate_compact_text())

    # Option 2: Envoyer à Discord (nécessite webhook URL)
    # webhook_url = "https://discord.com/api/webhooks/YOUR_WEBHOOK_URL"
    # logger.send_to_discord(webhook_url)

    # Option 3: Sauvegarder dans fichier
    # logger.save_summary()


if __name__ == "__main__":
    main()







