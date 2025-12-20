#!/usr/bin/env python3
"""
🎯 MIA Q-Score Calculator
Score quantitatif unifié (0-100) inspiré de MenthorQ

Combine:
- Layer 1 (MenthorQ): 40%
- Layer 2 (OrderFlow): 30%
- Layer 3 (Context): 20%
- Bonus Confluence: 10%

Grade: A++ (90+), A+ (80+), A (70+), B (60+), C (50+), D (40+), F (<40)
"""

from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class MIAQScore:
    """
    Calculateur Q-Score MIA (0-100)
    Inspiré de MenthorQ mais adapté à notre système
    """

    # Seuils de grade (comme école américaine)
    GRADE_THRESHOLDS = {
        90: ('A++', '🏆 EXCEPTIONNEL - Setup parfait'),
        80: ('A+', '⭐ EXCELLENT - Trade prioritaire'),
        70: ('A', '✅ TRÈS BON - Trade recommandé'),
        60: ('B', '👍 BON - Trade acceptable'),
        50: ('C', '⚠️ MOYEN - Trade risqué'),
        40: ('D', '📊 ACCEPTABLE - Seuil bas'),
        0: ('F', '📊 SCORE BAS - Seuil désactivé')
    }

    @staticmethod
    def calculate(
        ml_3layer_result: Dict[str, Any],
        tick: Dict[str, Any],
        best_signal: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Calcule Q-Score MIA (0-100)

        Args:
            ml_3layer_result: Résultats ML 3-Layer System
            tick: Données tick ML_READY
            best_signal: Signal stratégie (optionnel)

        Returns:
            {
                'qscore': float (0-100),
                'grade': str,
                'interpretation': str,
                'components': dict,
                'breakdown': dict
            }
        """
        # ═══════════════════════════════════════════════════════════════
        # ÉTAPE 1: Extraire composants Layer 1, 2, 3
        # ═══════════════════════════════════════════════════════════════
        layer1 = min(ml_3layer_result.get('layer1_confidence', 0.0), 1.0)
        layer2 = min(ml_3layer_result.get('layer2_confidence', 0.0), 1.0)
        layer3 = min(ml_3layer_result.get('layer3_confidence', 0.0), 1.0)

        # ═══════════════════════════════════════════════════════════════
        # ÉTAPE 2: Calculer confluence (alignement multi-stratégies)
        # ═══════════════════════════════════════════════════════════════
        confluence = 0.0
        if best_signal:
            confluence = min(best_signal.get('confluence', 0.0), 1.0)
        elif 'confluence' in ml_3layer_result:
            confluence = min(ml_3layer_result.get('confluence', 0.0), 1.0)

        # ═══════════════════════════════════════════════════════════════
        # ÉTAPE 3: Bonus scores MenthorQ natifs (si disponibles)
        # ═══════════════════════════════════════════════════════════════
        menthorq_impact = tick.get('menthorq_impact_score', 0.0)
        menthorq_proximity = tick.get('menthorq_proximity_strength', 0.0)
        battle_navale = tick.get('battle_navale_confidence', 0.0)

        # Bonus Layer 1 si scores MenthorQ natifs forts
        layer1_bonus = 0.0
        if menthorq_impact > 0.05:  # > 5%
            layer1_bonus += 0.05
        if menthorq_proximity > 0.10:  # > 10%
            layer1_bonus += 0.05
        if battle_navale > 0.20:  # > 20%
            layer1_bonus += 0.05

        layer1 = min(layer1 + layer1_bonus, 1.0)

        # ═══════════════════════════════════════════════════════════════
        # ÉTAPE 4: CALCUL Q-SCORE (0-100)
        # ═══════════════════════════════════════════════════════════════
        # Pondération:
        # - Layer 1 (MenthorQ): 40%
        # - Layer 2 (OrderFlow): 30%
        # - Layer 3 (Context): 20%
        # - Confluence: 10%
        # ═══════════════════════════════════════════════════════════════
        qscore = (
            layer1 * 40 +       # MenthorQ (niveaux options)
            layer2 * 30 +       # OrderFlow (pression achat/vente)
            layer3 * 20 +       # Context (biais marché)
            confluence * 10     # Confluence (alignement stratégies)
        )

        # ═══════════════════════════════════════════════════════════════
        # ÉTAPE 5: Attribution GRADE
        # ═══════════════════════════════════════════════════════════════
        grade = 'F'
        interpretation = '🚫 TRÈS FAIBLE - Rejeter'

        for threshold in sorted(MIAQScore.GRADE_THRESHOLDS.keys(), reverse=True):
            if qscore >= threshold:
                grade, interpretation = MIAQScore.GRADE_THRESHOLDS[threshold]
                break

        # ═══════════════════════════════════════════════════════════════
        # ÉTAPE 6: Breakdown détaillé
        # ═══════════════════════════════════════════════════════════════
        result = {
            'qscore': round(qscore, 1),
            'grade': grade,
            'interpretation': interpretation,
            'components': {
                'layer1_menthorq': round(layer1 * 40, 1),
                'layer2_orderflow': round(layer2 * 30, 1),
                'layer3_context': round(layer3 * 20, 1),
                'confluence': round(confluence * 10, 1)
            },
            'breakdown': {
                'layer1_raw': round(layer1, 3),
                'layer2_raw': round(layer2, 3),
                'layer3_raw': round(layer3, 3),
                'confluence_raw': round(confluence, 3),
                'layer1_bonus': round(layer1_bonus, 3),
                'menthorq_impact': round(menthorq_impact, 3),
                'menthorq_proximity': round(menthorq_proximity, 3),
                'battle_navale': round(battle_navale, 3)
            }
        }

        # Log pour debugging
        logger.info(f"📊 Q-Score MIA: {qscore:.1f} ({grade}) - {interpretation}")
        logger.debug(f"   Components: MenthorQ={layer1 * 40:.1f}, OrderFlow={layer2 * 30:.1f}, Context={layer3 * 20:.1f}, Confluence={confluence * 10:.1f}")
        logger.debug(f"   Native Scores: impact={menthorq_impact:.3f}, proximity={menthorq_proximity:.3f}, battle={battle_navale:.3f}")

        return result

    @staticmethod
    def get_recommended_action(qscore: float) -> str:
        """
        Retourne action recommandée selon Q-Score

        Args:
            qscore: Score 0-100

        Returns:
            str: Action recommandée
        """
        if qscore >= 80:
            return "✅ TRADE PRIORITAIRE - Risque standard"
        elif qscore >= 70:
            return "✅ TRADE RECOMMANDÉ - Risque standard"
        elif qscore >= 60:
            return "⚠️ TRADE ACCEPTABLE - Réduire risque -30%"
        elif qscore >= 50:
            return "⚠️ TRADE RISQUÉ - Réduire risque -50%"
        else:
            return "❌ REJETER TRADE - Score insuffisant"


# ═══════════════════════════════════════════════════════════════════════
# TESTS UNITAIRES
# ═══════════════════════════════════════════════════════════════════════

def test_qscore_calculation():
    """Test calcul Q-Score"""

    # Test 1: Score maximum (100)
    ml_result = {
        'layer1_confidence': 1.0,
        'layer2_confidence': 1.0,
        'layer3_confidence': 1.0,
        'confluence': 1.0
    }
    tick = {}
    result = MIAQScore.calculate(ml_result, tick)
    assert result['qscore'] == 100.0, f"Expected 100.0, got {result['qscore']}"
    assert result['grade'] == 'A++', f"Expected A++, got {result['grade']}"
    print("[OK] Test 1 passed: Score maximum (100 / A++)")

    # Test 2: Score excellent (85)
    ml_result = {
        'layer1_confidence': 0.90,
        'layer2_confidence': 0.80,
        'layer3_confidence': 0.85,
        'confluence': 0.80
    }
    result = MIAQScore.calculate(ml_result, tick)
    expected = 0.90 * 40 + 0.80 * 30 + 0.85 * 20 + 0.80 * 10  # 85.0
    assert 84 <= result['qscore'] <= 86, f"Expected ~85, got {result['qscore']}"
    assert result['grade'] == 'A+', f"Expected A+, got {result['grade']}"
    print(f"[OK] Test 2 passed: Score excellent ({result['qscore']} / A+)")

    # Test 3: Score moyen ES actuel (68)
    ml_result = {
        'layer1_confidence': 0.59,  # ES Layer 1
        'layer2_confidence': 0.16,  # OrderFlow
        'layer3_confidence': 0.32,  # Context
        'confluence': 1.0           # Confluence max
    }
    result = MIAQScore.calculate(ml_result, tick)
    # 0.59*40 + 0.16*30 + 0.32*20 + 1.0*10 = 23.6 + 4.8 + 6.4 + 10 = 44.8
    assert result['grade'] in ['D', 'C'], f"Expected D or C, got {result['grade']}"
    print(f"[OK] Test 3 passed: Score moyen ES ({result['qscore']} / {result['grade']})")

    # Test 4: Bonus MenthorQ natif
    ml_result = {
        'layer1_confidence': 0.50,
        'layer2_confidence': 0.20,
        'layer3_confidence': 0.30,
        'confluence': 0.70
    }
    tick_with_bonus = {
        'menthorq_impact_score': 0.06,      # > 0.05 → +0.05 bonus
        'menthorq_proximity_strength': 0.15, # > 0.10 → +0.05 bonus
        'battle_navale_confidence': 0.25     # > 0.20 → +0.05 bonus
    }
    result = MIAQScore.calculate(ml_result, tick_with_bonus)
    # Layer1 = 0.50 + 0.15 (bonus) = 0.65
    # Q-Score = 0.65*40 + 0.20*30 + 0.30*20 + 0.70*10 = 26 + 6 + 6 + 7 = 45
    assert result['breakdown']['layer1_bonus'] == 0.15, f"Expected bonus 0.15, got {result['breakdown']['layer1_bonus']}"
    print(f"[OK] Test 4 passed: Bonus MenthorQ natif ({result['qscore']} avec bonus +{result['breakdown']['layer1_bonus']:.2f})")

    print("\n[SUCCESS] Tous les tests Q-Score passes !")


if __name__ == "__main__":
    # Exécuter tests
    test_qscore_calculation()
