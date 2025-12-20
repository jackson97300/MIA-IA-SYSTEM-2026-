"""
Moteur de Règles Elite pour MIA IA System

Interprète les règles JSON et évalue les conditions sur les données ML_READY
"""

import json
import os
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class RuleEvaluation:
    """Résultat de l'évaluation d'une règle"""
    rule_id: str
    rule_name: str
    passed: bool
    priority: int
    entry_side: str
    entry_type: str
    entry_price_strategy: str
    stop_loss: Dict[str, Any]
    take_profit: List[Dict[str, Any]]
    position_size: int
    confidence: float
    failed_conditions: List[str]
    metadata: Dict[str, Any]


class RulesEngine:
    """
    Moteur de règles pour évaluer les signaux de trading
    """
    
    def __init__(self, rules_file: str = "rules/rules_elite_es_nq.json"):
        """
        Initialise le moteur de règles
        
        Args:
            rules_file: Chemin vers le fichier JSON des règles
        """
        self.rules_file = rules_file
        self.rules = self._load_rules()
        self.global_filters = self.rules.get("global_filters", {})
        self.rule_list = self.rules.get("rules", [])
        
        # Cooldown tracking
        self.last_signal_time: Dict[str, datetime] = {}
        
        logger.info(f"🎯 RulesEngine initialisé: {len(self.rule_list)} règles chargées")
    
    def _load_rules(self) -> Dict[str, Any]:
        """Charge les règles depuis le fichier JSON"""
        try:
            with open(self.rules_file, 'r', encoding='utf-8') as f:
                rules = json.load(f)
            logger.info(f"✅ Règles chargées depuis {self.rules_file}")
            return rules
        except FileNotFoundError:
            logger.error(f"❌ Fichier de règles introuvable: {self.rules_file}")
            return {"rules": [], "global_filters": {}}
        except json.JSONDecodeError as e:
            logger.error(f"❌ Erreur JSON dans {self.rules_file}: {e}")
            return {"rules": [], "global_filters": {}}
    
    def _get_nested_value(self, data: Dict[str, Any], field_path: str) -> Any:
        """
        Récupère une valeur imbriquée depuis un dictionnaire
        
        Args:
            data: Dictionnaire de données
            field_path: Chemin du champ (ex: "next_wall.side")
        
        Returns:
            Valeur du champ ou None
        """
        keys = field_path.split('.')
        value = data
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        
        return value
    
    def _evaluate_condition(self, condition: Dict[str, Any], data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Évalue une condition individuelle
        
        Args:
            condition: Définition de la condition
            data: Données de marché ML_READY
        
        Returns:
            (passed, reason) - True si condition passée, raison si échec
        """
        field = condition.get("field")
        operator = condition.get("operator")
        expected_value = condition.get("value")
        comment = condition.get("comment", field)
        
        # Récupérer la valeur actuelle
        actual_value = self._get_nested_value(data, field)
        
        if actual_value is None:
            return False, f"{comment}: Champ '{field}' introuvable"
        
        # Évaluer selon l'opérateur
        try:
            if operator == ">=":
                passed = actual_value >= expected_value
            elif operator == "<=":
                passed = actual_value <= expected_value
            elif operator == ">":
                passed = actual_value > expected_value
            elif operator == "<":
                passed = actual_value < expected_value
            elif operator == "==":
                passed = actual_value == expected_value
            elif operator == "!=":
                passed = actual_value != expected_value
            elif operator == "between":
                passed = expected_value[0] <= actual_value <= expected_value[1]
            elif operator == "in":
                passed = actual_value in expected_value
            else:
                logger.warning(f"⚠️ Opérateur inconnu: {operator}")
                return False, f"Opérateur '{operator}' inconnu"
            
            if not passed:
                return False, f"{comment}: {actual_value} {operator} {expected_value}"
            
            return True, ""
        
        except Exception as e:
            logger.error(f"❌ Erreur évaluation condition '{field}': {e}")
            return False, f"Erreur: {str(e)}"
    
    def _evaluate_conditions_block(self, conditions: Dict[str, Any], data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Évalue un bloc de conditions (AND/OR)
        
        Args:
            conditions: Bloc de conditions
            data: Données de marché
        
        Returns:
            (passed, failed_reasons)
        """
        failed_reasons = []
        
        # Mode AND
        if "and" in conditions:
            for condition in conditions["and"]:
                passed, reason = self._evaluate_condition(condition, data)
                if not passed:
                    failed_reasons.append(reason)
            
            return len(failed_reasons) == 0, failed_reasons
        
        # Mode OR
        elif "or" in conditions:
            for condition in conditions["or"]:
                passed, reason = self._evaluate_condition(condition, data)
                if passed:
                    return True, []
                failed_reasons.append(reason)
            
            return False, failed_reasons
        
        else:
            logger.warning("⚠️ Bloc de conditions sans 'and' ou 'or'")
            return False, ["Bloc de conditions invalide"]
    
    def _apply_global_filters(self, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Applique les filtres globaux
        
        Args:
            data: Données de marché
        
        Returns:
            (passed, failed_reasons)
        """
        failed_reasons = []
        
        # Vérifier spread_ticks_max
        if "spread_ticks_max" in self.global_filters:
            spread_ticks = data.get("spread_ticks", 999)
            if spread_ticks > self.global_filters["spread_ticks_max"]:
                failed_reasons.append(f"Spread trop large: {spread_ticks} ticks")
        
        # Vérifier volatility_regime
        if "volatility_regime_allowed" in self.global_filters:
            vol_regime = data.get("volatility_regime", 0)
            if vol_regime not in self.global_filters["volatility_regime_allowed"]:
                failed_reasons.append(f"Volatility regime non autorisé: {vol_regime}")
        
        # Vérifier session
        if "session_allowed" in self.global_filters:
            session = data.get("session_id", "Unknown")
            if session not in self.global_filters["session_allowed"]:
                failed_reasons.append(f"Session non autorisée: {session}")
        
        # Vérifier DOM depth
        if "min_dom_depth_total" in self.global_filters:
            dom_features = data.get("dom_features", {})
            depth_total = dom_features.get("depth_bid", 0) + dom_features.get("depth_ask", 0)
            if depth_total < self.global_filters["min_dom_depth_total"]:
                failed_reasons.append(f"DOM depth insuffisant: {depth_total}")
        
        # Vérifier DOM fresh
        if self.global_filters.get("is_dom_fresh", False):
            if not data.get("is_dom_fresh", False):
                failed_reasons.append("DOM pas frais")
        
        # Vérifier data quality
        if "data_quality" in self.global_filters:
            if data.get("data_quality") != self.global_filters["data_quality"]:
                failed_reasons.append(f"Data quality: {data.get('data_quality')}")
        
        return len(failed_reasons) == 0, failed_reasons
    
    def _check_cooldown(self, rule_id: str, cooldown_config: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Vérifie si le cooldown est respecté
        
        Args:
            rule_id: ID de la règle
            cooldown_config: Configuration du cooldown
        
        Returns:
            (passed, reason)
        """
        if rule_id not in self.last_signal_time:
            return True, ""
        
        bars_cooldown = cooldown_config.get("bars", 0)
        last_time = self.last_signal_time[rule_id]
        
        # Chaque bar = ~1 seconde pour simplifier (ajuster selon votre timeframe)
        cooldown_seconds = bars_cooldown * 1
        
        elapsed = (datetime.now() - last_time).total_seconds()
        
        if elapsed < cooldown_seconds:
            return False, f"Cooldown actif: {int(cooldown_seconds - elapsed)}s restantes"
        
        return True, ""
    
    def _calculate_position_size(self, sizing_config: Dict[str, Any], data: Dict[str, Any]) -> int:
        """
        Calcule la taille de position selon la configuration
        
        Args:
            sizing_config: Configuration du sizing
            data: Données de marché
        
        Returns:
            Taille de position en contrats
        """
        base_size = sizing_config.get("base_size", 1)
        
        # Scaling par confiance
        if sizing_config.get("confidence_scaling", False):
            scaling_field = sizing_config.get("scaling_factor", "battle_navale_confidence")
            confidence = self._get_nested_value(data, scaling_field) or 0.5
            max_size = sizing_config.get("max_size", 2)
            
            if confidence >= 0.90:
                return min(max_size, 2)
            elif confidence >= 0.80:
                return min(max_size, int(base_size * 1.5))
            else:
                return base_size
        
        return base_size
    
    def evaluate_all_rules(self, data: Dict[str, Any], symbol: str = "ES") -> List[RuleEvaluation]:
        """
        Évalue toutes les règles sur les données
        
        Args:
            data: Données ML_READY
            symbol: Symbole (ES, NQ, etc.)
        
        Returns:
            Liste des règles qui ont passé, triées par priorité
        """
        # Filtres globaux
        global_passed, global_reasons = self._apply_global_filters(data)
        if not global_passed:
            logger.debug(f"❌ Filtres globaux échoués: {', '.join(global_reasons)}")
            return []
        
        passed_rules = []
        
        for rule in self.rule_list:
            # Vérifier si règle activée
            if not rule.get("enabled", True):
                continue
            
            rule_id = rule["id"]
            rule_name = rule["name"]
            
            # Vérifier cooldown
            cooldown_passed, cooldown_reason = self._check_cooldown(
                rule_id, 
                rule.get("cooldown", {})
            )
            if not cooldown_passed:
                logger.debug(f"⏸️ {rule_name}: {cooldown_reason}")
                continue
            
            # Évaluer conditions
            conditions = rule.get("conditions", {})
            conditions_passed, failed_reasons = self._evaluate_conditions_block(conditions, data)
            
            if conditions_passed:
                # Calculer position size
                position_size = self._calculate_position_size(
                    rule.get("position_sizing", {}),
                    data
                )
                
                # Calculer confiance
                confidence_field = rule.get("position_sizing", {}).get("scaling_factor", "battle_navale_confidence")
                confidence = self._get_nested_value(data, confidence_field) or 0.5
                
                evaluation = RuleEvaluation(
                    rule_id=rule_id,
                    rule_name=rule_name,
                    passed=True,
                    priority=rule.get("priority", 1),
                    entry_side=rule["entry"]["side"],
                    entry_type=rule["entry"]["type"],
                    entry_price_strategy=rule["entry"].get("price_strategy", "market"),
                    stop_loss=rule["risk_management"]["stop_loss"],
                    take_profit=rule["risk_management"]["take_profit"],
                    position_size=position_size,
                    confidence=confidence,
                    failed_conditions=[],
                    metadata={
                        "symbol": symbol,
                        "timestamp": datetime.now().isoformat(),
                        "rule_category": rule_name.split(":")[0].strip(),
                        "cooldown": rule.get("cooldown", {}),
                        "entry_comment": rule["entry"].get("comment", "")
                    }
                )
                
                passed_rules.append(evaluation)
                logger.info(f"✅ {rule_name} DÉCLENCHÉ (priorité: {rule['priority']})")
            else:
                logger.debug(f"❌ {rule_name}: {', '.join(failed_reasons[:2])}")  # Limiter log
        
        # Trier par priorité (décroissante)
        passed_rules.sort(key=lambda x: x.priority, reverse=True)
        
        return passed_rules
    
    def get_best_signal(self, data: Dict[str, Any], symbol: str = "ES") -> Optional[RuleEvaluation]:
        """
        Retourne le meilleur signal (priorité la plus élevée)
        
        Args:
            data: Données ML_READY
            symbol: Symbole
        
        Returns:
            RuleEvaluation ou None
        """
        passed_rules = self.evaluate_all_rules(data, symbol)
        
        if not passed_rules:
            logger.debug(f"📊 [{symbol}] Aucune règle déclenchée")
            return None
        
        best = passed_rules[0]
        
        # Marquer le cooldown
        self.last_signal_time[best.rule_id] = datetime.now()
        
        logger.info(f"🎯 [{symbol}] Meilleur signal: {best.rule_name} (priorité: {best.priority}, conf: {best.confidence:.2f})")
        
        return best
    
    def format_signal_for_execution(self, evaluation: RuleEvaluation, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Formate un signal pour l'exécution
        
        Args:
            evaluation: RuleEvaluation
            data: Données ML_READY (pour calculer prix exact)
        
        Returns:
            Dictionnaire de signal formaté
        """
        # Calculer prix d'entrée selon stratégie
        entry_price = None
        
        if evaluation.entry_price_strategy == "market":
            entry_price = None  # Market order
        elif evaluation.entry_price_strategy == "current_bid":
            entry_price = data.get("best_bid")
        elif evaluation.entry_price_strategy == "current_ask":
            entry_price = data.get("best_ask")
        elif evaluation.entry_price_strategy == "next_wall_price":
            next_wall = data.get("next_wall", {})
            entry_price = next_wall.get("price")
        elif evaluation.entry_price_strategy.startswith("vwap"):
            entry_price = data.get(evaluation.entry_price_strategy)
        else:
            entry_price = data.get("mid")
        
        # Calculer SL
        sl_config = evaluation.stop_loss
        sl_ticks = sl_config.get("ticks", 10)
        
        if sl_config.get("strategy") == "atr_based":
            atr = data.get("atr", 0.70)
            atr_mult = sl_config.get("atr_multiplier", 1.5)
            tick_size = data.get("tick_size", 0.25)
            sl_ticks = int((atr * atr_mult) / tick_size)
            sl_ticks = max(sl_config.get("min_ticks", 8), min(sl_ticks, sl_config.get("max_ticks", 20)))
        
        # Calculer TP
        tp_list = []
        for tp_config in evaluation.take_profit:
            if tp_config["strategy"] == "fixed_ticks":
                tp_ticks = tp_config["ticks"]
                tp_list.append({
                    "ticks": tp_ticks,
                    "percent": tp_config["quantity_percent"]
                })
            elif tp_config["strategy"] == "vwap_level":
                vwap_price = data.get(tp_config["level"])
                if vwap_price and entry_price:
                    tp_ticks = abs(int((vwap_price - entry_price) / data.get("tick_size", 0.25)))
                    tp_list.append({
                        "price": vwap_price,
                        "ticks": tp_ticks,
                        "percent": tp_config["quantity_percent"]
                    })
        
        return {
            "strategy": evaluation.rule_id,
            "rule_name": evaluation.rule_name,
            "side": evaluation.entry_side,
            "entry_type": evaluation.entry_type,
            "entry_price": entry_price,
            "stop_loss_ticks": sl_ticks,
            "take_profit": tp_list,
            "position_size": evaluation.position_size,
            "confidence": evaluation.confidence,
            "priority": evaluation.priority,
            "metadata": evaluation.metadata,
            "symbol": data.get("sym", "ES")
        }


# Factory function
def create_rules_engine(rules_file: str = "rules/rules_elite_es_nq.json") -> RulesEngine:
    """Factory pour créer une instance du moteur de règles"""
    return RulesEngine(rules_file)


if __name__ == "__main__":
    # Test rapide
    from core.logger import setup_logger
    setup_logger()
    
    engine = create_rules_engine()
    
    # Données de test (vos données)
    test_data = {
        "sym": "ESZ25_FUT_CME",
        "mid": 6899.88,
        "spread_ticks": 1,
        "best_bid": 6899.75,
        "best_ask": 6900.00,
        "battle_navale_signal_strength": 1.135366,
        "battle_navale_confidence": 1.000000,
        "confluence_strength": 1.135366,
        "smart_money_flow": -0.448276,
        "level1_imbalance": -0.684211,
        "next_wall": {"side": "call", "dist_ticks": 1, "strength": 0.8, "price": 6900.0},
        "volatility_regime": 1,
        "session_id": "Asia",
        "dom_features": {"depth_bid": 319, "depth_ask": 372},
        "is_dom_fresh": True,
        "data_quality": "OK",
        "atr": 0.70,
        "tick_size": 0.25,
        "gamma_call_confluence": True,
        "menthor_distances": {"near_gex_up": 1},
        "vwap": 6900.38,
        "vwap_up1": 6911.18,
        "vwap_dn1": 6878.79
    }
    
    print("\n" + "="*60)
    print("🎯 TEST DU MOTEUR DE RÈGLES")
    print("="*60 + "\n")
    
    # Évaluer toutes les règles
    passed = engine.evaluate_all_rules(test_data, "ES")
    
    print(f"\n📊 Résultat: {len(passed)} règle(s) déclenchée(s)\n")
    
    for rule_eval in passed:
        print(f"✅ {rule_eval.rule_name}")
        print(f"   Priorité: {rule_eval.priority}, Confiance: {rule_eval.confidence:.2f}")
        print(f"   Side: {rule_eval.entry_side}, Type: {rule_eval.entry_type}")
        print()
    
    # Meilleur signal
    best = engine.get_best_signal(test_data, "ES")
    if best:
        signal = engine.format_signal_for_execution(best, test_data)
        print("\n🏆 MEILLEUR SIGNAL:")
        print(json.dumps(signal, indent=2))

