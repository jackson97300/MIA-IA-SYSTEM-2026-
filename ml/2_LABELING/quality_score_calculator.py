"""
🎯 QUALITY SCORE CALCULATOR - ML 3-Layer Strategy
Version: 1.0
Date: 15 novembre 2025

Calcule un score de qualité (0-100) pour chaque trade basé sur 5 composantes :
1. Résultat WIN/LOSS (40 points max) - Proportionnel au ratio P&L/SL
2. Magnitude P&L (20 points max) - Normalisé par MAX_TP_TICKS
3. Confluence Signal (20 points max) - Weighted Layer 1 + Total
4. Durée Optimale (10 points max) - Récompense 5-30 minutes
5. Gestion Risque (10 points max + 5 bonus) - MAE/MFE efficiency

Score final : 0-100 (normalisé)
Seuil recommandé production : quality_score >= 60
"""

from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class QualityScoreCalculator:
    """
    Calculateur de Quality Score pour évaluer la qualité des trades.
    
    Usage:
        calculator = QualityScoreCalculator()
        score = calculator.calculate(trade_data, symbol='ES')
    """
    
    def __init__(self):
        """Initialise le calculateur avec les paramètres par défaut."""
        
        # ═══════════════════════════════════════════════════════════
        # PARAMÈTRES DE CONFIGURATION
        # ═══════════════════════════════════════════════════════════
        
        # Max TP attendus par symbole (en ticks)
        self.MAX_TP_TICKS = {
            'ES': 30,   # ES: 30 ticks = $75
            'NQ': 35,   # NQ: 35 ticks = $175
            'RTY': 40   # RTY: 40 ticks = $40
        }
        
        # Tick size par symbole
        self.TICK_SIZE = {
            'ES': 0.25,
            'NQ': 0.25,
            'RTY': 0.10
        }
        
        # Durée optimale (minutes)
        self.OPTIMAL_MIN = 5      # Durée minimale optimale
        self.OPTIMAL_MAX = 30     # Durée maximale optimale
        self.PENALTY_THRESHOLD = 60  # Au-delà = pénalité forte
        
        # Pondération Layer 1 (MenthorQ) vs Total
        self.LAYER1_WEIGHT = 0.6  # 60% Layer 1 (MenthorQ)
        self.LAYER_TOTAL_WEIGHT = 0.4  # 40% Total (Layers 2+3)
        
        logger.info("✅ QualityScoreCalculator initialisé")
    
    
    def calculate(
        self, 
        trade: Dict, 
        symbol: str = 'ES',
        debug: bool = False
    ) -> float:
        """
        Calcule le Quality Score d'un trade (0-100).
        
        Args:
            trade: Dictionnaire contenant les données du trade
                Champs requis:
                - pnl_ticks (int): P&L en ticks
                - entry_price (float): Prix d'entrée
                - stop (float): Prix du stop loss
                - confluence (float): Score confluence 0-1
                - duration_minutes (float): Durée du trade en minutes
                Champs optionnels:
                - layer1_confidence (float): Confidence Layer 1
                - ml_confidence (float): Confidence totale ML
                - mae (float): Maximum Adverse Excursion
                - mfe (float): Maximum Favorable Excursion
            
            symbol: Symbole tradé ('ES', 'NQ', 'RTY')
            debug: Si True, affiche les détails de calcul
        
        Returns:
            float: Score de qualité 0-100
        """
        
        if debug:
            logger.info(f"\n{'='*70}")
            logger.info(f"🎯 CALCUL QUALITY SCORE - {symbol}")
            logger.info(f"{'='*70}")
        
        # ═══════════════════════════════════════════════════════════
        # 0️⃣ EXTRACTION DONNÉES DE BASE
        # ═══════════════════════════════════════════════════════════
        
        pnl_ticks = trade.get('pnl_ticks', 0)
        entry_price = trade.get('entry_price', 0)
        stop_price = trade.get('stop', entry_price)
        tick_size = self.TICK_SIZE.get(symbol, 0.25)
        
        # Calcul SL en ticks
        sl_distance = abs(entry_price - stop_price)
        sl_ticks = sl_distance / tick_size if tick_size > 0 else 10
        
        if debug:
            logger.info(f"\n📊 DONNÉES DE BASE:")
            logger.info(f"   P&L: {pnl_ticks:+.1f} ticks")
            logger.info(f"   Entry: {entry_price:.2f}")
            logger.info(f"   Stop: {stop_price:.2f}")
            logger.info(f"   SL: {sl_ticks:.1f} ticks")
        
        # ═══════════════════════════════════════════════════════════
        # 1️⃣ RÉSULTAT WIN/LOSS (40 points max)
        # ═══════════════════════════════════════════════════════════
        
        if pnl_ticks > 0:
            # WIN: Score proportionnel au ratio P&L/SL
            # Ratio 1.0 (P&L = SL) → 20 points
            # Ratio 2.0 (P&L = 2×SL) → 40 points (capé)
            if sl_ticks > 0:
                win_ratio = pnl_ticks / sl_ticks
                win_component = min(40, win_ratio * 20)
            else:
                win_component = 20  # Fallback
        else:
            # LOSS: Pénalité proportionnelle (max -10)
            # Loss 50% SL → -5 points
            # Loss 100% SL → -10 points
            if sl_ticks > 0:
                loss_ratio = pnl_ticks / sl_ticks
                win_component = max(-10, loss_ratio * 10)
            else:
                win_component = -10  # Fallback
        
        if debug:
            logger.info(f"\n1️⃣ WIN/LOSS COMPONENT:")
            logger.info(f"   Ratio P&L/SL: {pnl_ticks/sl_ticks if sl_ticks > 0 else 0:.2f}")
            logger.info(f"   Score: {win_component:+.2f} / 40.00")
        
        # ═══════════════════════════════════════════════════════════
        # 2️⃣ MAGNITUDE P&L (20 points max)
        # ═══════════════════════════════════════════════════════════
        
        max_tp_ticks = self.MAX_TP_TICKS.get(symbol, 30)
        pnl_ratio = abs(pnl_ticks) / max_tp_ticks if max_tp_ticks > 0 else 0
        pnl_component = min(20, pnl_ratio * 20)
        
        if debug:
            logger.info(f"\n2️⃣ P&L MAGNITUDE COMPONENT:")
            logger.info(f"   Max TP: {max_tp_ticks} ticks")
            logger.info(f"   Ratio: {pnl_ratio:.2f}")
            logger.info(f"   Score: {pnl_component:.2f} / 20.00")
        
        # ═══════════════════════════════════════════════════════════
        # 3️⃣ CONFLUENCE SIGNAL (20 points max)
        # ═══════════════════════════════════════════════════════════
        
        # Prioriser Layer 1 (MenthorQ) 60% + Total 40%
        layer1_conf = trade.get('layer1_confidence', trade.get('confluence', 0.5))
        total_conf = trade.get('ml_confidence', trade.get('confluence', 0.5))
        
        confluence_score = (
            self.LAYER1_WEIGHT * layer1_conf + 
            self.LAYER_TOTAL_WEIGHT * total_conf
        )
        confluence_component = 20 * confluence_score
        
        if debug:
            logger.info(f"\n3️⃣ CONFLUENCE COMPONENT:")
            logger.info(f"   Layer 1: {layer1_conf:.2%} (poids: 60%)")
            logger.info(f"   Total: {total_conf:.2%} (poids: 40%)")
            logger.info(f"   Combined: {confluence_score:.2%}")
            logger.info(f"   Score: {confluence_component:.2f} / 20.00")
        
        # ═══════════════════════════════════════════════════════════
        # 4️⃣ DURÉE OPTIMALE (10 points max)
        # ═══════════════════════════════════════════════════════════
        
        duration_min = trade.get('duration_minutes', 15)
        
        if self.OPTIMAL_MIN <= duration_min <= self.OPTIMAL_MAX:
            # Zone optimale: 10 points
            duration_component = 10
        elif duration_min < self.OPTIMAL_MIN:
            # Trop rapide: 5-10 points (proportionnel)
            duration_component = 5 + 5 * (duration_min / self.OPTIMAL_MIN)
        elif self.OPTIMAL_MAX < duration_min <= self.PENALTY_THRESHOLD:
            # Un peu long: 10-5 points (dégressif)
            ratio = (duration_min - self.OPTIMAL_MAX) / (self.PENALTY_THRESHOLD - self.OPTIMAL_MAX)
            duration_component = 10 - 5 * ratio
        else:
            # Très long: 5-0 points (forte pénalité)
            excess = duration_min - self.PENALTY_THRESHOLD
            duration_component = max(0, 5 - excess / 60)
        
        if debug:
            logger.info(f"\n4️⃣ DURATION COMPONENT:")
            logger.info(f"   Durée: {duration_min:.1f} min")
            logger.info(f"   Optimal: {self.OPTIMAL_MIN}-{self.OPTIMAL_MAX} min")
            logger.info(f"   Score: {duration_component:.2f} / 10.00")
        
        # ═══════════════════════════════════════════════════════════
        # 5️⃣ GESTION RISQUE (10 points max + 5 bonus)
        # ═══════════════════════════════════════════════════════════
        
        mae_ticks = abs(trade.get('mae', 0))
        mfe_ticks = abs(trade.get('mfe', pnl_ticks))
        
        # Base: Ratio drawdown vs SL
        if sl_ticks > 0:
            drawdown_ratio = 1 - (mae_ticks / sl_ticks)
            risk_base = 10 * drawdown_ratio
        else:
            risk_base = 0
        
        # Bonus efficiency: MFE/MAE ratio
        if mae_ticks > 0:
            efficiency_ratio = mfe_ticks / mae_ticks
            if efficiency_ratio >= 3.0:
                efficiency_bonus = 5    # Excellent
            elif efficiency_ratio >= 2.0:
                efficiency_bonus = 3    # Bon
            elif efficiency_ratio >= 1.5:
                efficiency_bonus = 1    # Acceptable
            else:
                efficiency_bonus = 0    # Faible
        else:
            efficiency_bonus = 0
        
        risk_mgmt_component = max(-5, min(15, risk_base + efficiency_bonus))
        
        if debug:
            logger.info(f"\n5️⃣ RISK MANAGEMENT COMPONENT:")
            logger.info(f"   MAE: {mae_ticks:.1f} ticks")
            logger.info(f"   MFE: {mfe_ticks:.1f} ticks")
            logger.info(f"   Drawdown ratio: {drawdown_ratio:.2%}")
            logger.info(f"   Efficiency (MFE/MAE): {mfe_ticks/mae_ticks if mae_ticks > 0 else 0:.2f}")
            logger.info(f"   Base: {risk_base:.2f}")
            logger.info(f"   Bonus: {efficiency_bonus:.2f}")
            logger.info(f"   Score: {risk_mgmt_component:.2f} / 15.00")
        
        # ═══════════════════════════════════════════════════════════
        # 📊 SCORE FINAL (0-100)
        # ═══════════════════════════════════════════════════════════
        
        raw_score = (
            win_component +          # -10 à 40
            pnl_component +          # 0 à 20
            confluence_component +   # 0 à 20
            duration_component +     # 0 à 10
            risk_mgmt_component      # -5 à 15
        )
        
        # Normalisation: raw_score peut aller de -15 (pire) à 105 (parfait)
        # On ramène à 0-100
        normalized_score = ((raw_score + 15) / 120) * 100
        final_score = max(0, min(100, normalized_score))
        
        if debug:
            logger.info(f"\n{'='*70}")
            logger.info(f"📊 SCORE FINAL:")
            logger.info(f"{'='*70}")
            logger.info(f"   Raw Score: {raw_score:.2f} / 105")
            logger.info(f"   Normalized: {normalized_score:.2f}")
            logger.info(f"   Final (0-100): {final_score:.2f}")
            logger.info(f"{'='*70}\n")
        
        return final_score
    
    
    def calculate_batch(
        self, 
        trades: list, 
        symbol: str = 'ES'
    ) -> list:
        """
        Calcule le Quality Score pour une liste de trades.
        
        Args:
            trades: Liste de dictionnaires de trades
            symbol: Symbole tradé
        
        Returns:
            list: Liste des scores calculés
        """
        scores = []
        for trade in trades:
            score = self.calculate(trade, symbol, debug=False)
            scores.append(score)
        
        logger.info(f"✅ {len(scores)} trades évalués")
        logger.info(f"   Score moyen: {sum(scores)/len(scores):.1f}")
        logger.info(f"   Score min: {min(scores):.1f}")
        logger.info(f"   Score max: {max(scores):.1f}")
        
        return scores
    
    
    def get_decision_threshold(self, risk_level: str = 'moderate') -> float:
        """
        Retourne le seuil de décision recommandé selon le niveau de risque.
        
        Args:
            risk_level: 'conservative', 'moderate', 'aggressive'
        
        Returns:
            float: Seuil minimum recommandé
        """
        thresholds = {
            'conservative': 65,  # Moins de trades, haute qualité
            'moderate': 60,      # Balance qualité/quantité
            'aggressive': 55     # Plus de trades, risque +5%
        }
        
        return thresholds.get(risk_level, 60)


# ═══════════════════════════════════════════════════════════════
# EXEMPLES D'UTILISATION
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    """Exemples de calcul de Quality Score."""
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s'
    )
    
    calculator = QualityScoreCalculator()
    
    print("\n" + "="*70)
    print("🎯 EXEMPLES CALCUL QUALITY SCORE")
    print("="*70)
    
    # ═══════════════════════════════════════════════════════════
    # EXEMPLE 1: EXCELLENT TRADE ⭐⭐⭐⭐⭐
    # ═══════════════════════════════════════════════════════════
    
    print("\n\n" + "🌟"*35)
    print("EXEMPLE 1: EXCELLENT TRADE")
    print("🌟"*35)
    
    excellent_trade = {
        'pnl_ticks': 25,          # WIN +25 ticks (TP1)
        'entry_price': 6000.00,
        'stop': 5990.00,          # SL 10 ticks
        'confluence': 0.85,
        'layer1_confidence': 0.90,
        'ml_confidence': 0.80,
        'duration_minutes': 15,   # Optimal
        'mae': -3,                # MAE 3 ticks (excellent)
        'mfe': 27                 # MFE 27 ticks
    }
    
    score = calculator.calculate(excellent_trade, 'ES', debug=True)
    print(f"\n🎯 RÉSULTAT: {score:.1f}/100 ⭐⭐⭐⭐⭐")
    
    # ═══════════════════════════════════════════════════════════
    # EXEMPLE 2: BON TRADE ⭐⭐⭐⭐
    # ═══════════════════════════════════════════════════════════
    
    print("\n\n" + "⭐"*35)
    print("EXEMPLE 2: BON TRADE")
    print("⭐"*35)
    
    good_trade = {
        'pnl_ticks': 12,
        'entry_price': 6000.00,
        'stop': 5988.00,          # SL 12 ticks
        'confluence': 0.70,
        'layer1_confidence': 0.75,
        'ml_confidence': 0.65,
        'duration_minutes': 22,
        'mae': -6,
        'mfe': 15
    }
    
    score = calculator.calculate(good_trade, 'ES', debug=True)
    print(f"\n🎯 RÉSULTAT: {score:.1f}/100 ⭐⭐⭐⭐")
    
    # ═══════════════════════════════════════════════════════════
    # EXEMPLE 3: LOSS CONTRÔLÉ ⭐⭐
    # ═══════════════════════════════════════════════════════════
    
    print("\n\n" + "⚠️"*35)
    print("EXEMPLE 3: LOSS CONTRÔLÉ")
    print("⚠️"*35)
    
    loss_trade = {
        'pnl_ticks': -8,
        'entry_price': 6000.00,
        'stop': 5990.00,          # SL 10 ticks
        'confluence': 0.65,
        'layer1_confidence': 0.70,
        'ml_confidence': 0.60,
        'duration_minutes': 12,
        'mae': -8,
        'mfe': 3
    }
    
    score = calculator.calculate(loss_trade, 'ES', debug=True)
    print(f"\n🎯 RÉSULTAT: {score:.1f}/100 ⭐⭐")
    
    # ═══════════════════════════════════════════════════════════
    # SEUILS DE DÉCISION
    # ═══════════════════════════════════════════════════════════
    
    print("\n\n" + "="*70)
    print("🎯 SEUILS DE DÉCISION RECOMMANDÉS")
    print("="*70)
    print(f"   Conservative (65+): Haute qualité, moins de trades")
    print(f"   Moderate (60+):     Balance qualité/quantité ✅ RECOMMANDÉ")
    print(f"   Aggressive (55+):   Plus de trades, risque +5%")
    print("="*70 + "\n")

