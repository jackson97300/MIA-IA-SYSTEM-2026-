"""
Dashboard Discord pour le suivi en temps réel
"""
import requests
from datetime import datetime, date
from typing import Optional

from ..stats.trade_stats import Trade, TradeResult, TradeDirection
from ..stats.evaluation_tracker import EvaluationTracker, EvaluationStatus
from ..core.drawdown_tracker import DrawdownTracker, DrawdownStatus
from ..alerts.risk_alerts import Alert, AlertLevel


class DiscordDashboard:
    """
    Dashboard Discord avec embeds formatés
    """

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send_trade_update(
        self,
        trade: Trade,
        eval_tracker: EvaluationTracker,
        dd_tracker: DrawdownTracker
    ):
        """Envoie une mise à jour après chaque trade"""
        status = eval_tracker.get_status()
        dd_state = dd_tracker.get_state()

        # Couleur selon résultat
        colors = {
            TradeResult.WIN: 0x00FF00,      # Vert
            TradeResult.LOSS: 0xFF0000,     # Rouge
            TradeResult.BREAKEVEN: 0xFFFF00, # Jaune
            TradeResult.OPEN: 0x808080,     # Gris
        }
        color = colors.get(trade.result, 0xFFFFFF)

        # Emoji résultat
        result_emoji = {
            TradeResult.WIN: "✅",
            TradeResult.LOSS: "❌",
            TradeResult.BREAKEVEN: "⚪",
            TradeResult.OPEN: "🔄",
        }

        # Emoji drawdown
        dd_emoji = "🟢" if dd_state.dd_used_percent < 50 else "🟡" if dd_state.dd_used_percent < 75 else "🔴"

        # Daily PnL
        today = date.today()
        today_pnl = 0.0
        if today in eval_tracker.daily_stats:
            today_pnl = eval_tracker.daily_stats[today].net_pnl

        embed = {
            "title": f"{result_emoji[trade.result]} Trade #{len(eval_tracker.all_trades)}",
            "color": color,
            "fields": [
                {
                    "name": "📊 Trade",
                    "value": (
                        f"**{trade.direction.value}** {trade.contracts}x {trade.symbol}\n"
                        f"Entry: {trade.entry_price}\n"
                        f"Exit: {trade.exit_price or 'OPEN'}\n"
                        f"PnL: **${trade.net_pnl:+.2f}** ({trade.pnl_ticks:+d}t)\n"
                        f"Session: {trade.session}"
                    ),
                    "inline": True
                },
                {
                    "name": "📅 Aujourd'hui",
                    "value": (
                        f"Trades: {status['trades']['total']}\n"
                        f"W/L: {status['trades']['wins']}/{status['trades']['losses']}\n"
                        f"WR: {status['trades']['win_rate']:.1f}%\n"
                        f"PnL: **${today_pnl:+.2f}**"
                    ),
                    "inline": True
                },
                {
                    "name": "🎯 Progression",
                    "value": (
                        f"Target: ${status['progress']['target']:,.0f}\n"
                        f"Réalisé: ${status['progress']['current']:+,.2f}\n"
                        f"Progress: **{status['progress']['percent']:.1f}%**\n"
                        f"Restant: ${status['progress']['remaining']:,.2f}"
                    ),
                    "inline": True
                },
                {
                    "name": f"{dd_emoji} Drawdown ({dd_state.drawdown_type.value})",
                    "value": (
                        f"HWM: ${dd_state.high_water_mark:,.2f}\n"
                        f"Utilisé: {dd_state.dd_used_percent:.1f}%\n"
                        f"Restant: ${dd_state.dd_remaining:,.2f}\n"
                        f"Distance: ${dd_state.distance_to_breach:,.2f}"
                    ),
                    "inline": True
                },
                {
                    "name": "📊 Global",
                    "value": (
                        f"Total: {status['trades']['total']} trades\n"
                        f"WR: {status['trades']['win_rate']:.1f}%\n"
                        f"PF: {status['trades']['profit_factor']:.2f}\n"
                        f"Jours: {status['trading_days']}/{status['min_trading_days']}"
                    ),
                    "inline": True
                },
                {
                    "name": "💰 Payouts",
                    "value": (
                        f"Nombre: {status['payouts']['count']}\n"
                        f"Total: ${status['payouts']['total']:,.2f}"
                    ),
                    "inline": True
                },
            ],
            "footer": {
                "text": f"{eval_tracker.prop_firm} {eval_tracker.account_size} | {eval_tracker.mode} | {status['status']}"
            },
            "timestamp": datetime.utcnow().isoformat()
        }

        self._send_embed(embed)

    def send_daily_report(self, eval_tracker: EvaluationTracker, dd_tracker: DrawdownTracker):
        """Envoie le rapport de fin de journée"""
        status = eval_tracker.get_status()
        dd_state = dd_tracker.get_state()

        # Déterminer la couleur globale
        today_pnl = 0
        today_date = date.today()
        if today_date in eval_tracker.daily_stats:
            today_pnl = eval_tracker.daily_stats[today_date].net_pnl

        color = 0x00FF00 if today_pnl > 0 else 0xFF0000 if today_pnl < 0 else 0xFFFF00

        embed = {
            "title": f"📊 Rapport Journalier - {today_date}",
            "color": color,
            "description": f"**{eval_tracker.prop_firm} {eval_tracker.account_size}** | {eval_tracker.mode}",
            "fields": [
                {
                    "name": "💰 PnL du Jour",
                    "value": f"**${today_pnl:+,.2f}**",
                    "inline": True
                },
                {
                    "name": "📈 Trades",
                    "value": f"{status['trades']['total']} (WR: {status['trades']['win_rate']:.1f}%)",
                    "inline": True
                },
                {
                    "name": "🎯 Progression",
                    "value": f"{status['progress']['percent']:.1f}% (${status['progress']['remaining']:,.2f} restant)",
                    "inline": True
                },
                {
                    "name": "📉 Drawdown",
                    "value": f"{dd_state.dd_used_percent:.1f}% utilisé",
                    "inline": True
                },
                {
                    "name": "📅 Jours",
                    "value": f"{status['trading_days']}/{status['min_trading_days']}",
                    "inline": True
                },
                {
                    "name": "📊 PF / R:R",
                    "value": f"{status['trades']['profit_factor']:.2f} / {status['trades']['avg_rr']:.2f}",
                    "inline": True
                },
            ],
            "footer": {
                "text": f"Status: {status['status']}"
            },
            "timestamp": datetime.utcnow().isoformat()
        }

        self._send_embed(embed)

    def send_alert(self, alert: Alert):
        """Envoie une alerte"""
        colors = {
            AlertLevel.INFO: 0x0099FF,
            AlertLevel.WARNING: 0xFFFF00,
            AlertLevel.DANGER: 0xFF6600,
            AlertLevel.CRITICAL: 0xFF0000,
        }

        embed = {
            "title": alert.title,
            "description": alert.message,
            "color": colors.get(alert.level, 0xFFFFFF),
            "fields": [
                {
                    "name": "Action requise",
                    "value": alert.action_required or "Aucune",
                    "inline": False
                }
            ],
            "footer": {
                "text": f"{alert.alert_type.value} | {alert.level.value}"
            },
            "timestamp": alert.timestamp.isoformat()
        }

        if alert.value is not None and alert.threshold is not None:
            embed["fields"].insert(0, {
                "name": "Valeur / Seuil",
                "value": f"{alert.value:.2f} / {alert.threshold:.2f}",
                "inline": True
            })

        self._send_embed(embed)

    def send_evaluation_passed(self, eval_tracker: EvaluationTracker):
        """Notification spéciale quand l'évaluation est passée"""
        status = eval_tracker.get_status()

        embed = {
            "title": "🎉🎉🎉 ÉVALUATION RÉUSSIE! 🎉🎉🎉",
            "description": f"Félicitations! Tu as passé l'évaluation **{eval_tracker.prop_firm} {eval_tracker.account_size}**!",
            "color": 0x00FF00,
            "fields": [
                {
                    "name": "📊 Résultats Finaux",
                    "value": (
                        f"Target: ${status['progress']['target']:,.0f}\n"
                        f"Réalisé: ${status['progress']['current']:+,.2f}\n"
                        f"Jours: {status['trading_days']}\n"
                        f"Trades: {status['trades']['total']}\n"
                        f"Win Rate: {status['trades']['win_rate']:.1f}%"
                    ),
                    "inline": False
                }
            ],
            "timestamp": datetime.utcnow().isoformat()
        }

        self._send_embed(embed)

    def _send_embed(self, embed: dict):
        """Envoie un embed via webhook"""
        try:
            payload = {"embeds": [embed]}
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            response.raise_for_status()
        except Exception as e:
            print(f"Erreur envoi Discord: {e}")

    def send_message(self, content: str):
        """Envoie un message texte simple"""
        try:
            payload = {"content": content}
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            response.raise_for_status()
        except Exception as e:
            print(f"Erreur envoi Discord: {e}")

