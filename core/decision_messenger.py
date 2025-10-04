#!/usr/bin/env python3
"""
DECISION MESSENGER - Système de messages clairs et sympas
========================================================

Génère des messages courts, clairs et sympas pour chaque décision de trading.
Répond à deux questions essentielles :
1. Trade ? (oui/non)
2. Pourquoi ? (les 2-4 raisons clés + le plan si on exécute)

Version: 1.0.0
Date: Janvier 2025
"""

import json
import csv
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
import os

class DecisionMessenger:
    """
    Générateur de messages de décision clairs et sympas
    
    Fonctionnalités :
    - Messages standardisés (EXECUTE/WAIT)
    - Templates sympas et compacts
    - Support Slack/Discord/Telegram
    - Historique CSV
    - Mode compact/détaillé
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialisation du Decision Messenger"""
        self.config = config or {
            "verbose": True,           # Mode détaillé par défaut
            "language": "FR",          # Français par défaut
            "save_history": True,      # Sauvegarder l'historique
            "cooldown_seconds": 2,     # Cooldown entre messages
            "webhook_url": None,       # URL webhook (Slack/Discord)
            "telegram_bot_token": None, # Token bot Telegram
            "telegram_chat_id": None   # Chat ID Telegram
        }
        
        self.last_message_time = 0
        self.message_count = 0
        
        # Créer le dossier de logs si nécessaire
        if self.config["save_history"]:
            self.log_dir = Path("logs/decisions")
            self.log_dir.mkdir(parents=True, exist_ok=True)
            self.csv_file = self.log_dir / f"decisions_{datetime.now().strftime('%Y%m%d')}.csv"
            self._init_csv()
        
        print("📱 Decision Messenger initialisé")
    
    def _init_csv(self):
        """Initialise le fichier CSV d'historique"""
        if not self.csv_file.exists():
            with open(self.csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp', 'mode', 'symbol', 'direction', 'execute',
                    'final_score', 'mq_score', 'bn_score', 'gates_ok',
                    'reasons', 'plan', 'context', 'message'
                ])
    
    def _save_to_csv(self, decision: Dict[str, Any], message: str):
        """Sauvegarde la décision dans le CSV"""
        if not self.config["save_history"]:
            return
        
        try:
            with open(self.csv_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    datetime.now().isoformat(),
                    decision["mode"],
                    decision["symbol"],
                    decision["direction"],
                    decision["final"]["execute"],
                    decision["final"]["score"],
                    decision["menthorq"]["score"],
                    decision["battle_navale"]["score"],
                    decision["battle_navale"].get("gates_detail", {}).get("final_ok", False),
                    " | ".join(self._build_reasons(decision)),
                    json.dumps(decision.get("plan", {})),
                    json.dumps(decision.get("context", {})),
                    message.replace('\n', ' | ')
                ])
        except Exception as e:
            print(f"⚠️ Erreur sauvegarde CSV: {e}")
    
    def _pretty_bool(self, b: bool) -> str:
        """Convertit un booléen en emoji"""
        return "✅" if b else "❌"
    
    def _format_direction(self, direction: int) -> str:
        """Formate la direction"""
        return "LONG" if direction == 1 else "SHORT"
    
    def _format_gates_line(self, gates_status: dict) -> str:
        """Source unique de vérité pour l'affichage des gates"""
        dom_ok = bool(gates_status.get('dom_health_gate_ok', False))
        struct_ok = bool(gates_status.get('battle_navale_gates_ok', False))
        lead_ok = bool(gates_status.get('leadership_gate_ok', False))  # si pas dispo → False
        final_ok = bool(gates_status.get('overall_gates_ok', False))
        return (f"DOM {self._pretty_bool(dom_ok)} | "
                f"Struct {self._pretty_bool(struct_ok)} | "
                f"Lead {self._pretty_bool(lead_ok)} | "
                f"Final {self._pretty_bool(final_ok)}")
    
    def _why_reason(self, syn: dict) -> str:
        """Raison principale basée sur les gates bloquants"""
        gs = syn.get('gates_status', {})
        blockers = []
        if not gs.get('overall_gates_ok', False):
            if not gs.get('battle_navale_gates_ok', True): blockers.append("BN insuffisant")
            if not gs.get('dom_health_gate_ok', True): blockers.append("DOM faible")
            if not gs.get('leadership_gate_ok', True): blockers.append("Leadership insuffisant")
            if blockers:
                return ", ".join(blockers)
        # fallback: plus faible composant
        comps = syn.get('component_scores', {})
        if comps:
            kmin = min(comps, key=comps.get)
            return f"{kmin.replace('_',' ').upper()} faible"
        return "Signal insuffisant"
    
    def _signal_label(self, rec: str) -> str:
        """Jamais 'ERROR' à l'écran: on mappe dur → NO_GO par défaut"""
        return {"GO": "GO", "SCOUT_GO": "SCOUT_GO", "NO_GO": "NO_GO"}.get(str(rec), "NO_GO")
    
    def _build_follow_up(self, elite_synthesis: Dict[str, Any]) -> str:
        """Construit le message de suivi UNIQUE basé sur la recommendation"""
        rec = elite_synthesis.get("recommendation", "NO_GO")
        component_scores = elite_synthesis.get("component_scores", {}) or {}
        bn_score = component_scores.get("battle_navale_elite", 0.0)
        of_score = component_scores.get("orderflow_advanced", 0.0)
        
        if rec == "SCOUT_GO":
            # Utiliser ASCII pour compatibilité console Windows
            return f"Suivi: SCOUT_GO - demi-taille sur retest VWAP/HVL | BN>=0.30 act:{bn_score:.2f} | OF>=0.20 act:{of_score:.2f}"
        elif rec == "GO":
            return "Suivi: GO LIVE - pleine taille sur break/retest HVL/VWAP + validation OF"
        else:
            return "Suivi: Attendre retest VWAP ou signal BN>0.40"
    
    def _build_reasons(self, decision: Dict[str, Any]) -> List[str]:
        """Construit la liste des raisons principales - Gates bloquants en priorité"""
        reasons = []
        
        # Source unique de vérité : Elite Synthesis
        elite_synthesis = decision.get("elite_synthesis", {})
        gates_status = elite_synthesis.get("gates_status", {})
        component_scores = elite_synthesis.get("component_scores", {})
        
        if elite_synthesis:
            # Priorité 1: Gates bloquants (overall_gates_ok=False)
            if not gates_status.get("overall_gates_ok", False):
                if not gates_status.get("battle_navale_gates_ok", True):
                    bn_score = component_scores.get("battle_navale_elite", 0)
                    reasons.append(f"BN insuffisant ({bn_score:.2f})")
                if not gates_status.get("dom_health_gate_ok", True):
                    dom_score = component_scores.get("dom_health", 0)
                    reasons.append(f"DOM faible ({dom_score:.2f})")
                
                if reasons:
                    return reasons[:2]  # Retourner les gates bloquants
            
            # Priorité 2: Composant le plus faible (si tous les gates OK)
            if component_scores:
                weakest = min(component_scores, key=component_scores.get)
                score = component_scores[weakest]
                reasons.append(f"{weakest.replace('_', ' ').upper()} faible ({score:.2f})")
        else:
            # Fallback sur l'ancienne structure
            mq = decision.get("menthorq", {})
            bn = decision.get("battle_navale", {})
            gates = bn.get("gates_detail", {})
            
            if not gates.get("final_ok", True):
                reasons.append("BN insuffisant")
            elif not mq.get("signal"):
                reasons.append("MQ faible")
        
        return reasons[:2] if reasons else ["Signal insuffisant"]
    
    def _compose_detailed_message(self, decision: Dict[str, Any]) -> str:
        """Compose un message détaillé"""
        mode = decision["mode"]
        sym = decision["symbol"]
        side = self._format_direction(decision["direction"])
        mq_score = decision["menthorq"]["score"]
        bn_score = decision["battle_navale"]["score"]
        final_score = decision["final"]["score"]
        execute = decision["final"]["execute"]
        # ✅ Utiliser elite_synthesis.gates_status comme source unique de vérité
        elite_synthesis = decision.get("elite_synthesis", {})
        elite_gates = elite_synthesis.get("gates_status", {})
        if elite_gates:
            gates = {
                'dom_ok': elite_gates.get('dom_health_gate_ok', False),
                'structure_ok': elite_gates.get('battle_navale_gates_ok', False),
                'leadership_ok': elite_gates.get('leadership_gate_ok', False),
                'final_ok': elite_gates.get('overall_gates_ok', False)
            }
        else:
            gates = decision["battle_navale"].get("gates_detail", {})
        ctx = decision.get("context", {})
        reasons = self._build_reasons(decision)
        
        # Ligne des gates - source unique de vérité
        elite_synthesis = decision.get("elite_synthesis", {})
        gates_status = elite_synthesis.get("gates_status", {})
        gates_line = self._format_gates_line(gates_status)
        
        # Raison principale - gates bloquants en priorité
        why_reason = self._why_reason(elite_synthesis)
        
        # Header
        header_emoji = "📈" if execute else "⏸️"
        header_status = "EXECUTE" if execute else "WAIT (pas d'exécution)"
        header = f"{header_emoji} [{mode}] {sym} {side} — {header_status}"
        
        # Scores
        scores = f"Final {final_score:.3f} (MQ {mq_score:.2f} • BN {bn_score:.2f}) — Gates: {gates_line}"
        
        # Pourquoi
        why = f"Pourquoi: {why_reason}"
        
        # Plan ou suivi - UN SEUL affichage basé sur recommendation
        if execute and "plan" in decision:
            p = decision["plan"]
            plan = f"Plan: Entrée {p['entry']:.2f} | SL {p['stop']:.2f} | TP1 {p['tp1']:.2f} | Taille {p['size']} | R/R {p['rr']:.2f}"
        else:
            # Construire le message de suivi UNIQUE
            elite_synthesis = decision.get("elite_synthesis", {})
            plan = self._build_follow_up(elite_synthesis)
        
        # Contexte
        ctx_line = f"Contexte: VIX {ctx.get('vix', '?')} | Opt snapshot {ctx.get('options_age_min', '?')} min | Latence {ctx.get('latency_ms', '?')} ms"
        
        return "\n".join([header, scores, why, plan, ctx_line])
    
    def _compose_compact_message(self, decision: Dict[str, Any]) -> str:
        """Compose un message compact (une ligne)"""
        mode = decision["mode"]
        sym = decision["symbol"]
        side = self._format_direction(decision["direction"])
        final_score = decision["final"]["score"]
        execute = decision["final"]["execute"]
        elite_gates = decision.get("elite_gates_status") or {}
        if elite_gates:
            gates = {
                'final_ok': elite_gates.get('overall_gates_ok', False)
            }
        else:
            gates = decision["battle_navale"].get("gates_detail", {})
        
        status = "EXECUTE" if execute else "WAIT"
        final_ok = self._pretty_bool(gates.get('final_ok', True))
        
        return f"{status} [{mode}] {sym} {side} — Final {final_score:.3f} | Final {final_ok}"
    
    def send_decision(self, decision: Dict[str, Any], force: bool = False) -> str:
        """
        Envoie un message de décision
        
        Args:
            decision: Dictionnaire de décision
            force: Forcer l'envoi (ignorer le cooldown)
            
        Returns:
            Message généré
        """
        import time
        
        # Vérifier le cooldown
        current_time = time.time()
        if not force and (current_time - self.last_message_time) < self.config["cooldown_seconds"]:
            return ""  # Pas de message à cause du cooldown
        
        # Générer le message
        if self.config["verbose"]:
            message = self._compose_detailed_message(decision)
        else:
            message = self._compose_compact_message(decision)
        
        # Sauvegarder dans le CSV
        self._save_to_csv(decision, message)
        
        # Afficher le message dans la console
        print(f"\n{message}\n")
        
        # ✅ Afficher aussi un message compact pour les updates fréquentes
        if not self.config["verbose"]:
            compact_msg = self._compose_compact_message(decision)
            print(f"💬 {compact_msg}")
        
        # Envoyer via webhook si configuré
        self._send_webhook(message)
        
        # Envoyer via Telegram si configuré
        self._send_telegram(message)
        
        # Mettre à jour les compteurs
        self.last_message_time = current_time
        self.message_count += 1
        
        return message
    
    def _send_webhook(self, message: str):
        """Envoie le message via webhook (Slack/Discord)"""
        webhook_url = self.config.get("webhook_url")
        if not webhook_url:
            return
        
        try:
            import requests
            
            payload = {
                "text": message,
                "username": "MIA Trading Bot",
                "icon_emoji": ":robot_face:"
            }
            
            response = requests.post(webhook_url, json=payload, timeout=5)
            if response.status_code == 200:
                print("📤 Message envoyé via webhook")
            else:
                print(f"⚠️ Erreur webhook: {response.status_code}")
                
        except Exception as e:
            print(f"⚠️ Erreur envoi webhook: {e}")
    
    def _send_telegram(self, message: str):
        """Envoie le message via Telegram"""
        bot_token = self.config.get("telegram_bot_token")
        chat_id = self.config.get("telegram_chat_id")
        
        if not bot_token or not chat_id:
            return
        
        try:
            import requests
            
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
            
            response = requests.post(url, json=payload, timeout=5)
            if response.status_code == 200:
                print("📱 Message envoyé via Telegram")
            else:
                print(f"⚠️ Erreur Telegram: {response.status_code}")
                
        except Exception as e:
            print(f"⚠️ Erreur envoi Telegram: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du messenger"""
        return {
            "messages_sent": self.message_count,
            "last_message_time": self.last_message_time,
            "config": self.config,
            "csv_file": str(self.csv_file) if self.config["save_history"] else None
        }

def create_decision_messenger(config: Optional[Dict[str, Any]] = None) -> DecisionMessenger:
    """Factory function pour créer un Decision Messenger"""
    return DecisionMessenger(config)

# Fonction de compatibilité
def send_decision_message(decision: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> str:
    """
    Fonction de compatibilité pour envoyer un message de décision
    
    Args:
        decision: Dictionnaire de décision
        config: Configuration optionnelle
        
    Returns:
        Message généré
    """
    messenger = create_decision_messenger(config)
    return messenger.send_decision(decision)

if __name__ == "__main__":
    # Test du Decision Messenger
    print("🧪 Test Decision Messenger...")
    
    # Décision de test - EXECUTE
    test_decision_execute = {
        "mode": "LIVE",
        "symbol": "ES",
        "direction": 1,
        "menthorq": {
            "score": 0.875,
            "signal": True,
            "strength": "STRONG"
        },
        "battle_navale": {
            "score": 0.620,
            "gates_detail": {
                "dom_ok": True,
                "structure_ok": True,
                "leadership_ok": True,
                "final_ok": True,
                "bn_score": 0.620,
                "final_thr": 0.60
            },
            "blocked_by": []
        },
        "final": {
            "score": 0.780,
            "execute": True,
            "override": "off"
        },
        "plan": {
            "entry": 6715.75,
            "stop": 6713.50,
            "tp1": 6718.25,
            "size": 2,
            "rr": 1.3
        },
        "context": {
            "vix": 18.5,
            "options_age_min": 2,
            "latency_ms": 1.4
        }
    }
    
    # Décision de test - WAIT
    test_decision_wait = {
        "mode": "PAPER",
        "symbol": "ES",
        "direction": 1,
        "menthorq": {
            "score": 0.875,
            "signal": True,
            "strength": "STRONG"
        },
        "battle_navale": {
            "score": 0.360,
            "gates_detail": {
                "dom_ok": True,
                "structure_ok": True,
                "leadership_ok": True,
                "final_ok": False,
                "bn_score": 0.360,
                "final_thr": 0.60,
                "why": "bn_score < final_thr"
            },
            "blocked_by": ["final_ok"]
        },
        "final": {
            "score": 0.669,
            "execute": False,
            "override": "blocked"
        },
        "context": {
            "vix": 18.5,
            "options_age_min": 2,
            "latency_ms": 1.4
        }
    }
    
    # Test avec configuration
    config = {
        "verbose": True,
        "save_history": True,
        "cooldown_seconds": 0  # Pas de cooldown pour le test
    }
    
    messenger = create_decision_messenger(config)
    
    print("\n=== TEST EXECUTE ===")
    messenger.send_decision(test_decision_execute, force=True)
    
    print("\n=== TEST WAIT ===")
    messenger.send_decision(test_decision_wait, force=True)
    
    print("\n=== STATS ===")
    stats = messenger.get_stats()
    print(json.dumps(stats, indent=2))
    
    print("✅ Test Decision Messenger terminé")
