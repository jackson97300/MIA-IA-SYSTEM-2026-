#!/usr/bin/env python3
"""
DECISION MESSENGER ML_READY - Version adaptée pour nouvelle architecture
=========================================================================

Version: 3.1 - Compatible ML_READY + Phase 3.5 (Nov 2025)
Date: Novembre 2025

Adapte DecisionMessenger v1.0 pour fonctionner avec TradingSignal, PatternSignal et ML_READY data.
Messages clairs et sympas pour chaque décision de trading.

**Nouveautés Phase 3.5** :
- Support PatternSignal (pas seulement dict)
- Logging des rejets (WAIT) avec raisons
- Intégration avec RejectionDiagnosticLogger
- CSV enrichi avec rejection_reason
"""

import json
import csv
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
from core.logger import get_logger

logger = get_logger(__name__)

class DecisionMessengerMLReady:
    """
    Générateur de messages de décision adapté pour ML_READY

    Fonctionnalités :
    - Messages standardisés (EXECUTE/WAIT)
    - Support Slack/Discord/Telegram
    - Historique CSV
    - Mode compact/détaillé
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialisation"""
        self.config = config or {
            "verbose": True,
            "save_history": True,
            "cooldown_seconds": 2
        }

        self.last_message_time = 0
        self.message_count = 0

        # Créer le dossier de logs si nécessaire
        if self.config["save_history"]:
            self.log_dir = Path("logs/decisions")
            self.log_dir.mkdir(parents=True, exist_ok=True)
            self.csv_file = self.log_dir / f"decisions_{datetime.now().strftime('%Y%m%d')}.csv"
            self._init_csv()

        logger.info("✅ DecisionMessengerMLReady initialisé")

    def _init_csv(self):
        """Initialise le fichier CSV"""
        if not self.csv_file.exists():
            with open(self.csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp', 'symbol', 'action', 'execute',
                    'confidence', 'strategy', 'bullish_score',
                    'entry', 'sl', 'tp', 'vwap_pos', 'mia_bias',  # ✅ RENOMMÉ: dealers_bias → mia_bias
                    'rejection_reason', 'message'
                ])

    def _save_to_csv(self, signal: Any, ml_data: Dict[str, Any], message: str, execute: bool, rejection_reason: str = ""):
        """Sauvegarde dans le CSV"""
        if not self.config["save_history"]:
            return

        try:
            # ✅ Support PatternSignal ET dict
            if isinstance(signal, dict):
                symbol = signal.get('symbol', 'ES')
                action = signal.get('action', 'NEUTRAL')
                confidence = signal.get('confidence', 0.0)
                strategy = signal.get('strategy', 'unknown')
                entry_price = signal.get('entry_price', 0.0)
                stop_loss = signal.get('stop_loss', 0.0)
                take_profit = signal.get('take_profit', 0.0)
            else:
                # PatternSignal ou TradingSignal object
                symbol = getattr(signal, 'symbol', 'ES')
                action = getattr(signal, 'action', None) or getattr(signal, 'side', 'NEUTRAL')
                if hasattr(action, 'name'):  # Enum
                    action = action.name
                confidence = getattr(signal, 'confidence', 0.0)
                strategy = getattr(signal, 'strategy', 'unknown')
                entry_price = getattr(signal, 'entry_price', 0.0)
                stop_loss = getattr(signal, 'stop_loss', 0.0)
                take_profit = getattr(signal, 'take_profit', 0.0)

            with open(self.csv_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    datetime.now().isoformat(),
                    symbol,
                    action,
                    execute,
                    confidence,
                    strategy,
                    ml_data.get('bullish_score', 0.0),
                    entry_price,
                    stop_loss,
                    take_profit,
                    "above" if ml_data.get('mid', 0) > ml_data.get('vwap', 0) else "below",
                    ml_data.get('bullish_score', 0.0),  # ✅ CORRIGÉ: bullish_score au lieu de dealers_bias
                    rejection_reason,  # ✅ Nouvelle colonne
                    message.replace('\n', ' | ')
                ])
        except Exception as e:
            logger.error(f"⚠️ Erreur sauvegarde CSV: {e}")

    def _compose_detailed_message(self, signal: Any, ml_data: Dict[str, Any], execute: bool, rejection_reason: str = "") -> str:
        """Compose un message détaillé"""
        # ✅ Support PatternSignal ET dict
        if isinstance(signal, dict):
            symbol = signal.get('symbol', 'ES')
            action = signal.get('action', 'NEUTRAL')
            confidence = signal.get('confidence', 0.0)
            strategy = signal.get('strategy', 'unknown')
            entry = signal.get('entry_price', ml_data.get('mid', 0))
            sl = signal.get('stop_loss', None)
            tp = signal.get('take_profit', None)
        else:
            symbol = getattr(signal, 'symbol', 'ES')
            action = getattr(signal, 'action', None) or getattr(signal, 'side', 'NEUTRAL')
            if hasattr(action, 'name'):  # Enum
                action = action.name
            confidence = getattr(signal, 'confidence', 0.0)
            strategy = getattr(signal, 'strategy', 'unknown')
            entry = getattr(signal, 'entry_price', ml_data.get('mid', 0))
            sl = getattr(signal, 'stop_loss', None)
            tp = getattr(signal, 'take_profit', None)

        # Header
        header_emoji = "📈" if execute else "⏸️"
        header_status = "EXECUTE" if execute else f"WAIT (Raison: {rejection_reason or 'condition non remplie'})"
        header = f"{header_emoji} [{symbol}] {action} — {header_status}"

        # Scores
        bullish_score = ml_data.get('bullish_score', 0.0)
        bullish_emoji = "🟢" if bullish_score > 0.3 else "🔴" if bullish_score < -0.3 else "🟡"
        scores = f"Conf {confidence:.2f} | Strategy: {strategy} | Bullish: {bullish_emoji} {bullish_score:+.2f}"

        # VWAP
        vwap = ml_data.get('vwap', 0)
        mid = ml_data.get('mid', 0)
        vwap_pos = "above" if mid > vwap else "below"
        vwap_line = f"VWAP: {vwap:.2f} ({vwap_pos})"

        # Plan ou suivi
        if execute and sl and tp:
            rr = abs((tp - entry) / (entry - sl)) if sl != entry else 0
            plan = f"Plan: Entry {entry:.2f} | SL {sl:.2f} | TP {tp:.2f} | R/R {rr:.2f}"
        else:
            plan = f"Suivi: {rejection_reason or 'Attendre confirmation VWAP ou signal plus fort'}"

        # Contexte
        mia_bias = ml_data.get('bullish_score', 0)  # ✅ CORRIGÉ: bullish_score au lieu de dealers_bias
        vix = ml_data.get('vix', 0)
        session = ml_data.get('session', 'UNKNOWN')
        ctx_line = f"Contexte: VIX {vix:.1f} | MIA Bias {mia_bias:+.2f} | Session {session}"

        return "\n".join([header, scores, vwap_line, plan, ctx_line])

    def _compose_compact_message(self, signal: Any, ml_data: Dict[str, Any], execute: bool) -> str:
        """Compose un message compact (une ligne)"""
        symbol = getattr(signal, 'symbol', 'ES')
        action = getattr(signal, 'action', None) or getattr(signal, 'side', 'NEUTRAL')
        confidence = getattr(signal, 'confidence', 0.0)
        bullish_score = ml_data.get('bullish_score', 0.0)
        bullish_emoji = "🟢" if bullish_score > 0.3 else "🔴" if bullish_score < -0.3 else "🟡"

        status = "EXECUTE" if execute else "WAIT"

        return f"{status} [{symbol}] {action} {confidence:.2f} | Bullish: {bullish_emoji} {bullish_score:+.2f}"

    def send_signal(self, signal: Any, ml_data: Dict[str, Any], execute: bool = True, rejection_reason: str = "", force: bool = False) -> str:
        """
        Envoie un message pour un signal

        Args:
            signal: TradingSignal, PatternSignal ou dict
            ml_data: Données ML_READY
            execute: Si True, le signal sera exécuté
            rejection_reason: Raison du rejet si execute=False
            force: Forcer l'envoi (ignorer le cooldown)

        Returns:
            Message généré
        """
        import time

        # Vérifier le cooldown
        current_time = time.time()
        if not force and (current_time - self.last_message_time) < self.config["cooldown_seconds"]:
            return ""

        # Générer le message
        if self.config["verbose"]:
            message = self._compose_detailed_message(signal, ml_data, execute, rejection_reason)
        else:
            message = self._compose_compact_message(signal, ml_data, execute)

        # Sauvegarder dans le CSV
        self._save_to_csv(signal, ml_data, message, execute, rejection_reason)

        # Afficher dans la console
        logger.info(f"\n{message}\n")

        # Mettre à jour les compteurs
        self.last_message_time = current_time
        self.message_count += 1

        return message

    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques"""
        return {
            "messages_sent": self.message_count,
            "last_message_time": self.last_message_time,
            "config": self.config,
            "csv_file": str(self.csv_file) if self.config["save_history"] else None
        }

# === FACTORY FUNCTION ===

def create_decision_messenger_ml_ready(config: Optional[Dict[str, Any]] = None) -> DecisionMessengerMLReady:
    """Factory function"""
    return DecisionMessengerMLReady(config)

# === TEST FUNCTION ===

if __name__ == "__main__":
    from dataclasses import dataclass

    @dataclass
    class TestSignal:
        symbol: str
        action: str
        confidence: float
        strategy: str
        entry_price: float
        stop_loss: float
        take_profit: float

    logger.info("=== TEST DECISION MESSENGER ML_READY ===")

    messenger = create_decision_messenger_ml_ready(config={
        "verbose": True,
        "save_history": False,
        "cooldown_seconds": 0
    })

    # Test signal EXECUTE
    signal = TestSignal(
        symbol="ES",
        action="LONG",
        confidence=0.75,
        strategy="hybrid_strategy",
        entry_price=5300.0,
        stop_loss=5295.0,
        take_profit=5310.0
    )

    ml_data = {
        "mid": 5300.0,
        "vwap": 5298.5,
        "bullish_score": 0.62,
        "dealers_bias": 0.15,
        "vix": 18.5,
        "session": "NY_OPEN"
    }

    logger.info("\n=== TEST EXECUTE ===")
    messenger.send_signal(signal, ml_data, execute=True, force=True)

    logger.info("\n=== TEST WAIT ===")
    signal.confidence = 0.45
    ml_data["bullish_score"] = -0.20
    messenger.send_signal(signal, ml_data, execute=False, force=True)

    logger.info(f"\n=== STATS ===")
    stats = messenger.get_stats()
    logger.info(json.dumps(stats, indent=2, default=str))

    logger.info("✅ Test réussi!")
