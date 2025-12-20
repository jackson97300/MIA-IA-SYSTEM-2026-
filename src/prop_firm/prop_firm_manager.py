"""
PropFirmManager - Classe principale qui orchestre tout le module
"""
from datetime import datetime, date
from typing import Optional, Dict
import json
import os

from .config.prop_firm_rules import get_prop_firm_config, get_account_config
from .config.risk_parameters import RiskParameters, get_risk_params
from .core.position_sizer import PropFirmPositionSizer, PositionSize
from .core.drawdown_tracker import DrawdownTracker, DrawdownState, DrawdownStatus
from .stats.trade_stats import Trade, TradeStats, TradeDirection, TradeResult
from .stats.daily_stats import DailyStats
from .stats.evaluation_tracker import EvaluationTracker, EvaluationStatus
from .alerts.risk_alerts import RiskAlertManager, Alert
from .dashboard.discord_dashboard import DiscordDashboard


class PropFirmManager:
    """
    Gestionnaire principal pour le trading Prop Firm

    Orchestre:
    - Position sizing
    - Drawdown tracking
    - Stats journalières et globales
    - Alertes de risque
    - Dashboard Discord

    Usage:
        manager = PropFirmManager(
            prop_firm="APEX",
            account_size="50K",
            mode="EVALUATION",
            discord_webhook="https://discord.com/api/webhooks/..."
        )

        # Avant chaque trade
        can_trade = manager.can_trade()
        if can_trade["allowed"]:
            size = manager.calculate_position("ES", stop_loss_ticks=12)
            # ... exécuter le trade ...

        # Après chaque trade
        manager.record_trade(trade)
    """

    def __init__(
        self,
        prop_firm: str,
        account_size: str,
        mode: str = "EVALUATION",
        risk_params: Optional[RiskParameters] = None,
        discord_webhook: Optional[str] = None,
        data_dir: str = "./prop_firm_data"
    ):
        self.prop_firm = prop_firm
        self.account_size = account_size
        self.mode = mode
        self.data_dir = data_dir

        # Charger les configurations
        self.firm_config = get_prop_firm_config(prop_firm)
        self.account_config = get_account_config(prop_firm, account_size)
        self.risk_params = risk_params or get_risk_params(mode)

        # Initialiser les composants
        self.position_sizer = PropFirmPositionSizer(
            prop_firm, account_size, mode, self.risk_params
        )

        self.drawdown_tracker = DrawdownTracker(
            prop_firm, account_size,
            on_alert_callback=self._on_drawdown_alert
        )

        self.eval_tracker = EvaluationTracker(
            prop_firm, account_size, mode
        )

        self.alert_manager = RiskAlertManager(
            on_alert=self._on_alert
        )

        # Dashboard Discord (optionnel)
        self.discord: Optional[DiscordDashboard] = None
        if discord_webhook:
            self.discord = DiscordDashboard(discord_webhook)

        # État
        self.is_trading_day_started = False
        self.today_trade_count = 0
        self.current_loss_streak = 0

        # Créer le répertoire de données
        os.makedirs(data_dir, exist_ok=True)

    # ═══════════════════════════════════════════════════════════════════════════
    # VÉRIFICATIONS PRÉ-TRADE
    # ═══════════════════════════════════════════════════════════════════════════

    def can_trade(self) -> Dict:
        """
        Vérifie si on peut trader

        Returns:
            {
                "allowed": bool,
                "reasons": list,  # Raisons si non autorisé
                "warnings": list, # Avertissements
            }
        """
        result = {
            "allowed": True,
            "reasons": [],
            "warnings": []
        }

        # 1. Vérifier le drawdown
        dd_state = self.drawdown_tracker.get_state()
        if not dd_state.can_trade:
            result["allowed"] = False
            result["reasons"].append(f"⛔ Drawdown {dd_state.status.value}: {dd_state.dd_used_percent:.1f}%")
        elif dd_state.status == DrawdownStatus.DANGER:
            result["warnings"].append(f"🔴 Drawdown DANGER: {dd_state.dd_used_percent:.1f}%")
        elif dd_state.status == DrawdownStatus.WARNING:
            result["warnings"].append(f"🟡 Drawdown WARNING: {dd_state.dd_used_percent:.1f}%")

        # 2. Vérifier le daily loss (si applicable)
        daily_state = self.drawdown_tracker.get_daily_loss_state()
        if daily_state and daily_state["is_breached"]:
            result["allowed"] = False
            result["reasons"].append(f"⛔ Daily loss limit atteint: ${daily_state['daily_loss_used']:.2f}")

        # 3. Vérifier le nombre de trades
        if self.today_trade_count >= self.risk_params.max_trades_per_day:
            result["allowed"] = False
            result["reasons"].append(f"⛔ Max trades atteint: {self.today_trade_count}/{self.risk_params.max_trades_per_day}")
        elif self.today_trade_count >= self.risk_params.max_trades_per_day - 1:
            result["warnings"].append(f"⚠️ Dernier trade autorisé: {self.today_trade_count}/{self.risk_params.max_trades_per_day}")

        # 4. Vérifier la série de pertes
        if self.current_loss_streak >= self.risk_params.max_loss_streak_before_stop:
            result["allowed"] = False
            result["reasons"].append(f"⛔ {self.current_loss_streak} pertes consécutives - STOP!")
        elif self.current_loss_streak >= self.risk_params.max_loss_streak_before_stop - 1:
            result["warnings"].append(f"⚠️ {self.current_loss_streak} pertes - dernier trade avant stop")

        # 5. Vérifier le status de l'évaluation
        if self.eval_tracker.status == EvaluationStatus.PASSED:
            result["warnings"].append("🎉 Évaluation passée! Vérifier les prochaines étapes.")
        elif self.eval_tracker.status in [EvaluationStatus.FAILED_DD, EvaluationStatus.FAILED_DAILY_LOSS]:
            result["allowed"] = False
            result["reasons"].append(f"⛔ Évaluation échouée: {self.eval_tracker.status.value}")

        return result

    def calculate_position(
        self,
        symbol: str,
        stop_loss_ticks: int,
        prefer_micros: Optional[bool] = None
    ) -> PositionSize:
        """
        Calcule la taille de position optimale

        Args:
            symbol: ES, NQ, MES, MNQ, etc.
            stop_loss_ticks: Distance du stop en ticks
            prefer_micros: Force micros (défaut: selon risk_params)

        Returns:
            PositionSize avec tous les détails
        """
        # Mettre à jour l'état du sizer avec la balance actuelle
        dd_state = self.drawdown_tracker.get_state()
        self.position_sizer.update_account_state(
            dd_state.current_balance,
            dd_state.high_water_mark
        )

        return self.position_sizer.calculate_position_size(
            symbol, stop_loss_ticks, prefer_micros
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # GESTION DES TRADES
    # ═══════════════════════════════════════════════════════════════════════════

    def start_trading_day(self):
        """Appelé au début de chaque journée de trading"""
        self.is_trading_day_started = True
        self.today_trade_count = 0
        self.drawdown_tracker.start_new_day()

    def end_trading_day(self):
        """Appelé en fin de journée"""
        self.drawdown_tracker.end_of_day()
        self.is_trading_day_started = False

        # Envoyer le rapport journalier
        if self.discord:
            self.discord.send_daily_report(self.eval_tracker, self.drawdown_tracker)

        # Sauvegarder les données
        self.save_data()

    def record_trade(self, trade: Trade) -> Dict:
        """
        Enregistre un trade terminé

        Args:
            trade: Trade fermé

        Returns:
            Status complet après le trade
        """
        if not self.is_trading_day_started:
            self.start_trading_day()

        self.today_trade_count += 1

        # Mettre à jour la série de pertes
        if trade.result == TradeResult.LOSS:
            self.current_loss_streak += 1
        else:
            self.current_loss_streak = 0

        # Enregistrer dans l'eval tracker
        self.eval_tracker.record_trade(trade)

        # Mettre à jour le drawdown
        self.drawdown_tracker.update(self.eval_tracker.current_balance)

        # Vérifier les alertes
        self._check_all_alerts()

        # Vérifier si l'évaluation est passée
        if self.eval_tracker.status == EvaluationStatus.PASSED:
            if self.discord:
                self.discord.send_evaluation_passed(self.eval_tracker)

        # Envoyer la mise à jour Discord
        if self.discord:
            self.discord.send_trade_update(
                trade, self.eval_tracker, self.drawdown_tracker
            )

        return self.get_status()

    # ═══════════════════════════════════════════════════════════════════════════
    # ALERTES
    # ═══════════════════════════════════════════════════════════════════════════

    def _check_all_alerts(self):
        """Vérifie toutes les conditions d'alerte"""
        dd_state = self.drawdown_tracker.get_state()

        # Drawdown
        self.alert_manager.check_drawdown(dd_state.dd_used_percent)

        # Daily loss
        daily_state = self.drawdown_tracker.get_daily_loss_state()
        if daily_state:
            self.alert_manager.check_daily_loss(
                daily_state["daily_loss_used"],
                daily_state["daily_loss_limit"]
            )

        # Loss streak
        self.alert_manager.check_loss_streak(
            self.current_loss_streak,
            self.risk_params.max_loss_streak_before_stop
        )

        # Max trades
        self.alert_manager.check_max_trades(
            self.today_trade_count,
            self.risk_params.max_trades_per_day
        )

        # Consistance
        consistency = self.eval_tracker.check_consistency()
        if consistency.rule_percent:
            today = date.today()
            if today in self.eval_tracker.daily_stats:
                daily_pnl = self.eval_tracker.daily_stats[today].net_pnl
                self.alert_manager.check_consistency(
                    daily_pnl,
                    consistency.max_allowed_daily_pnl,
                    consistency.rule_percent
                )

        # Target atteint
        if self.eval_tracker.total_pnl >= self.eval_tracker.profit_target:
            self.alert_manager.notify_target_reached(
                self.eval_tracker.profit_target,
                self.eval_tracker.total_pnl
            )

    def _on_drawdown_alert(self, alert_type: str, message: str):
        """Callback pour les alertes drawdown"""
        pass  # Géré par le RiskAlertManager

    def _on_alert(self, alert: Alert):
        """Callback pour toutes les alertes"""
        if self.discord:
            self.discord.send_alert(alert)

    # ═══════════════════════════════════════════════════════════════════════════
    # STATUS ET RAPPORTS
    # ═══════════════════════════════════════════════════════════════════════════

    def get_status(self) -> Dict:
        """Retourne le status complet"""
        dd_state = self.drawdown_tracker.get_state()
        eval_status = self.eval_tracker.get_status()

        return {
            # Identification
            "prop_firm": self.prop_firm,
            "account_size": self.account_size,
            "mode": self.mode,

            # État du jour
            "today": {
                "trades": self.today_trade_count,
                "max_trades": self.risk_params.max_trades_per_day,
                "loss_streak": self.current_loss_streak,
            },

            # Drawdown
            "drawdown": {
                "type": dd_state.drawdown_type.value,
                "status": dd_state.status.value,
                "percent_used": dd_state.dd_used_percent,
                "remaining": dd_state.dd_remaining,
                "can_trade": dd_state.can_trade,
            },

            # Évaluation
            "evaluation": eval_status,

            # Alertes
            "alerts": self.alert_manager.get_alert_summary(),

            # Peut trader?
            "can_trade": self.can_trade(),
        }

    def get_daily_report(self) -> str:
        """Génère un rapport journalier textuel"""
        status = self.get_status()
        dd = status["drawdown"]
        eval_s = status["evaluation"]

        return f"""
╔══════════════════════════════════════════════════════════════╗
║          📊 RAPPORT - {date.today()}                        ║
╠══════════════════════════════════════════════════════════════╣
║  COMPTE: {self.prop_firm} {self.account_size} ({self.mode})
╠══════════════════════════════════════════════════════════════╣
║  📈 TRADES DU JOUR: {status['today']['trades']}/{status['today']['max_trades']}
║  🔥 Série pertes: {status['today']['loss_streak']}
╠══════════════════════════════════════════════════════════════╣
║  🎯 PROGRESSION
║  ├── Target: ${eval_s['progress']['target']:,.0f}
║  ├── Réalisé: ${eval_s['progress']['current']:+,.2f}
║  ├── Progress: {eval_s['progress']['percent']:.1f}%
║  └── Restant: ${eval_s['progress']['remaining']:,.2f}
╠══════════════════════════════════════════════════════════════╣
║  📉 DRAWDOWN ({dd['type']})
║  ├── Status: {dd['status']}
║  ├── Utilisé: {dd['percent_used']:.1f}%
║  └── Restant: ${dd['remaining']:,.2f}
╠══════════════════════════════════════════════════════════════╣
║  📊 STATS GLOBALES
║  ├── Trades: {eval_s['trades']['total']}
║  ├── Win Rate: {eval_s['trades']['win_rate']:.1f}%
║  ├── Profit Factor: {eval_s['trades']['profit_factor']:.2f}
║  └── Jours: {eval_s['trading_days']}/{eval_s['min_trading_days']}
╚══════════════════════════════════════════════════════════════╝
"""

    # ═══════════════════════════════════════════════════════════════════════════
    # PERSISTENCE
    # ═══════════════════════════════════════════════════════════════════════════

    def save_data(self):
        """Sauvegarde les données"""
        filepath = os.path.join(
            self.data_dir,
            f"{self.prop_firm}_{self.account_size}_{self.mode}.json"
        )

        data = {
            "saved_at": datetime.now().isoformat(),
            "status": self.get_status(),
            "evaluation": self.eval_tracker.get_status(),
        }

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)

    def load_data(self) -> bool:
        """Charge les données précédentes"""
        filepath = os.path.join(
            self.data_dir,
            f"{self.prop_firm}_{self.account_size}_{self.mode}.json"
        )

        if not os.path.exists(filepath):
            return False

        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            # TODO: Restaurer l'état depuis les données
            return True
        except Exception as e:
            print(f"Erreur chargement données: {e}")
            return False

