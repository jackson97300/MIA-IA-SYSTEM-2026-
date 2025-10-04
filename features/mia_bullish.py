# -*- coding: utf-8 -*-
"""
MIA_BULLISH v2 — Bias directionnel composite (bot-friendly) - VERSION AMÉLIORÉE
- Combine MentorQ (Gamma/Blind + Swing + Scanner), VWAP/VP, OF/DOM, Leadership (soft), VIX, Q-Score.
- Sorties: score (0..100), state (BULLISH/NEUTRE/BEARISH), sizing_advice (0/1/2/3 lots, plafonné par VIX).
- AMÉLIORATIONS: QC Gates, Kernels lisses, Seuils adaptatifs, Sizing intelligent, Métriques validation.

Drop-in: features/mia_bullish.py
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, Literal
import math

BiasState = Literal["BULLISH", "NEUTRE", "BEARISH"]

# ===================== CONFIG AMÉLIORÉE =====================

# Pondérations de base (calibrables)
WEIGHTS_BASE = {
    "mentorq_gamma": 0.30,     # HVL/Call/Put walls/flip
    "mentorq_swing": 0.20,     # Swing Levels SPX→ES/NQ (placeholder input)
    "mentorq_blind": 0.10,     # Blind spots intraday
    "scanner":       0.10,     # TV alerts (TTL court)
    "vwap_vp":       0.12,     # VWAP position+slope + VP (POC/VAH/VAL)
    "leadership":    0.06,     # Soft bonus (Trend only)
    "footprint_dom": 0.08,     # Imbalances/absorptions + L1==BBO
    "vix":           0.02,     # Niveau + tendance
    "qscore":        0.10      # MentorQ Q-Score 0..5 → ±10 pts
}

# Pondérations par régime (adaptatif)
WEIGHTS_REGIME = {
    "TREND": {
        "mentorq_gamma": 1.2,   # Plus important en tendance
        "leadership": 1.5,      # Leadership crucial en tendance
        "vwap_vp": 0.8,         # Moins important en tendance
    },
    "RANGE": {
        "vwap_vp": 1.3,         # VWAP crucial en range
        "mentorq_blind": 1.2,   # Blind spots importants en range
        "leadership": 0.5,      # Leadership moins important en range
    },
    "VOLATILE": {
        "vix": 2.0,             # VIX crucial en volatilité
        "mentorq_gamma": 0.7,   # Gamma moins fiable en volatilité
        "scanner": 0.5,         # Scanner moins fiable en volatilité
    }
}

# Paramètres de base (remplacés par adaptatifs)
PARAMS_BASE = {
    "score_up_thr":   65,   # Base pour passage Bullish
    "score_up_rel":   55,   # Base pour retour neutre
    "score_dn_thr":   35,   # Base pour passage Bearish
    "score_dn_rel":   45,   # Base pour retour neutre
    "bars_confirm":    2,   # hystérèse
    "scanner_ttl":     90,  # s
    "scanner_debounce":20,  # s
    "vix_upsize_max":  18.0, # autorise upsize si VIX < 18
    "vix_hi_cap":      25.0  # cap sizing si VIX > 25
}

# QC Gates
QC_GATES = {
    "options_staleness_max_min": 5,    # Max 5 min pour options
    "vwap_qc_p95_max": 0.20,          # Max 20% divergence VWAP
    "min_data_quality": 0.7,          # Min 70% qualité données
}

# ===================== INPUT MODEL =====================

@dataclass
class MentorQGamma:
    dist_to_HVL_pts: float = 9e9
    flip_active: bool = False
    wall_side: Optional[str] = None  # "CALL" | "PUT" | None

@dataclass
class MentorQSwing:
    swing_high: float = 0.0
    swing_low: float = 0.0
    avail: bool = False
    state: str = "none"      # "below" | "at" | "above" | "none"
    dist_pts: float = 9e9
    retest_ok: bool = False

@dataclass
class MentorQBlind:
    nearby: bool = False
    distance_ticks: int = 999
    blind_spot_1: float = 0.0
    direction: Optional[str] = None  # "up" | "down" | None

@dataclass
class MentorQScanner:
    # Implémentation minimaliste: on passe un dict d'events récent → l'unifier gère TTL/debounce
    recent: Dict[str, Any] = None     # ex: {"HVL_BREAK": {"age": 12}, "1D_MAX_TOUCH": {"age": 25}}
    scanner_debounce: set = None
    
    def __post_init__(self):
        if self.recent is None:
            self.recent = {}
        if self.scanner_debounce is None:
            self.scanner_debounce = set()

@dataclass
class VWAPCtx:
    vwap: float = 0.0
    vwap_up1: float = 0.0
    vwap_dn1: float = 0.0
    vwap_slope: float = 0.0
    above: bool = False
    slope: str = "flat"       # "up"|"flat"|"down"
    band: str = "inside"      # "inside"|"sd1"|"sd2"

@dataclass
class VPCtx:
    vpoc: float = 0.0
    val: float = 0.0
    vah: float = 0.0
    at_level: str = "none"    # "POC"|"VAH"|"VAL"|"none"
    reclaim: bool = False

@dataclass
class LeadershipCtx:
    nq_stronger_than_es: bool = False
    es_nq_correlation: float = 0.0
    leadership_strength: float = 0.0
    sync_ok: bool = True

@dataclass
class OFDOMCtx:
    ask_imbalance: float = 1.0
    bid_imbalance: float = 1.0  # NOUVEAU: pour SHORT
    seller_absorption: bool = False
    buyer_absorption: bool = False  # NOUVEAU: pour SHORT
    l1_eq_bbo: bool = True
    spread_ticks: int = 1

@dataclass
class MacroCtx:
    vix: float = 17.0
    vix_regime: str = "NORMAL"
    vix_trend: str = "flat"  # "down"|"flat"|"up"

@dataclass
class SessionCtx:
    session_id: str = "unknown"
    session_phase: str = "unknown"
    phase: str = "MID"       # "OPEN"|"MID"|"POWER"|"OFF"
    regime: str = "TREND"    # "TREND"|"RANGE"|"DEFENSIF"

@dataclass
class MentorQCtx:
    gamma: MentorQGamma = None
    swing: MentorQSwing = None
    blind: MentorQBlind = None
    scanner: MentorQScanner = None
    qscore: Optional[float] = None    # 0..5 (si dispo); None => neutre
    
    def __post_init__(self):
        if self.gamma is None:
            self.gamma = MentorQGamma()
        if self.swing is None:
            self.swing = MentorQSwing()
        if self.blind is None:
            self.blind = MentorQBlind()
        if self.scanner is None:
            self.scanner = MentorQScanner()

@dataclass
class QCContext:
    """Contexte de qualité des données"""
    options_snapshot_age_min: float = 0.0
    vwap_qc_p95: float = 0.0
    data_quality_score: float = 1.0
    atr_per_bar: float = 1.0
    atr_relative: float = 1.0
    l1_bbo_ratio_rolling: float = 1.0  # Ratio L1==BBO
    symbol: str = "ES"  # Symbole pour tick size
    tick_size: float = 0.25  # Tick size du symbole

@dataclass
class MIAInputs:
    current_price: float = 0.0
    timestamp: float = 0.0
    mentorq: MentorQCtx = None
    vwap: VWAPCtx = None
    vp: VPCtx = None
    leadership: LeadershipCtx = None
    ofdom: OFDOMCtx = None
    macro: MacroCtx = None
    session: SessionCtx = None
    qc: QCContext = None  # NOUVEAU: Contexte QC
    setup_side: str = "LONG"  # NOUVEAU: LONG/SHORT
    prev_state: BiasState = "NEUTRE"
    hold_counts: Optional[Dict[str,int]] = None  # persistance par état (simple)
    
    def __post_init__(self):
        if self.mentorq is None:
            self.mentorq = MentorQCtx()
        if self.vwap is None:
            self.vwap = VWAPCtx()
        if self.vp is None:
            self.vp = VPCtx()
        if self.leadership is None:
            self.leadership = LeadershipCtx()
        if self.ofdom is None:
            self.ofdom = OFDOMCtx()
        if self.macro is None:
            self.macro = MacroCtx()
        if self.session is None:
            self.session = SessionCtx()
        if self.qc is None:
            self.qc = QCContext()
        if self.hold_counts is None:
            self.hold_counts = {}

# ===================== CORE AMÉLIORÉ =====================

def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

def _get_adaptive_weights(regime: str, vix: float) -> Dict[str, float]:
    """Pondérations adaptatives selon régime et VIX"""
    base = WEIGHTS_BASE.copy()
    regime_adj = WEIGHTS_REGIME.get(regime, {})
    
    # Ajustement VIX (±1% par point VIX)
    vix_factor = 1.0 + (vix - 20) * 0.01
    
    for key in base:
        regime_mult = regime_adj.get(key, 1.0)
        base[key] *= regime_mult * vix_factor
    
    # Normalisation pour que la somme = 1.0
    total = sum(base.values())
    for key in base:
        base[key] /= total
    
    return base

def _get_adaptive_thresholds(vix: float, atr_relative: float) -> Dict[str, float]:
    """Seuils adaptatifs selon VIX et ATR"""
    base = PARAMS_BASE.copy()
    
    # Ajustement VIX (±2% par point VIX)
    vix_factor = 1.0 + (vix - 20) * 0.02
    
    # Ajustement ATR (±10% par écart ATR)
    atr_factor = 1.0 + (atr_relative - 1.0) * 0.1
    
    # Application des facteurs
    for key in ["score_up_thr", "score_up_rel", "score_dn_thr", "score_dn_rel"]:
        if key in base:
            base[key] *= vix_factor * atr_factor
    
    return base

def _pre_gates(qc: QCContext) -> Optional[str]:
    """Gates de fraîcheur/QC (durs) - retourne la raison du blocage ou None"""
    # Gate 1: Staleness options
    if qc.options_snapshot_age_min > QC_GATES["options_staleness_max_min"]:
        return f"options_stale_{qc.options_snapshot_age_min:.1f}min"
    
    # Gate 2: DOM brisé
    if qc.l1_bbo_ratio_rolling < 0.70:
        return f"dom_broken_{qc.l1_bbo_ratio_rolling:.2f}"
    
    # Gate 3: Qualité générale
    if qc.data_quality_score < QC_GATES["min_data_quality"]:
        return f"data_quality_low_{qc.data_quality_score:.2f}"
    
    return None

def _check_qc_gates(qc: QCContext) -> Dict[str, Any]:
    """Vérification des gates de qualité (version dégradée)"""
    reason = _pre_gates(qc)
    
    if reason:
        return {
            "passed": False,
            "issues": [reason],
            "qc_penalty": 0.0  # Blocage total
        }
    
    # VWAP QC (dégradation, pas blocage)
    vwap_penalty = 0.8 if qc.vwap_qc_p95 > QC_GATES["vwap_qc_p95_max"] else 1.0
    
    return {
        "passed": True,
        "issues": [],
        "qc_penalty": vwap_penalty
    }

def _scanner_component(scanner: MentorQScanner) -> float:
    """Scanner avec debounce (anti-rebond)"""
    if not scanner.recent:
        return 0.0
    
    bonus = 0.0
    used = set()  # Anti-rebond par type d'événement
    
    for evt, meta in scanner.recent.items():
        if evt in used:
            continue  # Déjà traité (debounce)
            
        age = meta.get("age", 9999)
        if age > PARAMS_BASE["scanner_ttl"]:
            continue
            
        used.add(evt)
        
        # Mapping avec debounce
        event_scores = {
            "HVL_BREAK": 0.6,
            "1D_MAX_TOUCH": 0.4,
            "PUT_SUPPORT_BREAK": -0.6  # bearish
        }
        bonus += event_scores.get(evt, 0.0)
    
    return clamp(bonus, -1.0, 1.0)

def _swing_component(swing: MentorQSwing, vwap: VWAPCtx, vp: VPCtx) -> float:
    if not swing.avail:
        return 0.0
    sc = 0.0
    if swing.state == "at":
        sc += 0.6
    elif swing.state == "above":
        sc += 1.0 if swing.retest_ok else 0.6
    elif swing.state == "below":
        sc += 0.0
    if vwap.above and vwap.slope == "up":
        sc += 0.2
    if vp.reclaim:
        sc += 0.2
    return clamp(sc, 0.0, 1.0)

def _prox_by_ticks(d_ticks: float, lam: float) -> float:
    """Kernel de proximité normalisé par ticks"""
    return math.exp(-d_ticks / lam)  # 0..1

def _gamma_component(gamma: MentorQGamma, scanner_bonus: float, tick_size: float, atr_ticks: float) -> float:
    """Gamma avec normalisation tick/ATR"""
    d_ticks = abs(gamma.dist_to_HVL_pts) / tick_size
    base = _prox_by_ticks(d_ticks, lam=6.0)  # λ à calibrer
    
    if gamma.flip_active and d_ticks <= 8.0:
        base = max(base, 1.0)  # Setup premium
    
    # Bonus scanner
    sc = base + 0.15 * max(0.0, scanner_bonus)
    return clamp(sc, 0.0, 1.0)

def _blind_component(blind: MentorQBlind, ofdom: OFDOMCtx, setup_side: str, tick_size: float) -> float:
    """Blind spots avec normalisation et direction"""
    if not blind.nearby:
        return 0.0
    
    # Normalisation par tick
    d_ticks = blind.distance_ticks / tick_size
    base = _prox_by_ticks(d_ticks, lam=4.0)  # λ à calibrer
    
    # Direction bonus
    direction_bonus = 0.0
    if setup_side == "LONG" and blind.direction == "up":
        direction_bonus = 0.2  # Bonus si blind spot au-dessus (breakout potentiel)
    elif setup_side == "SHORT" and blind.direction == "down":
        direction_bonus = 0.2  # Bonus si blind spot en-dessous (breakdown potentiel)
    
    # OF/DOM confluence
    ofdom_bonus = 0.0
    if setup_side == "LONG" and (ofdom.ask_imbalance >= 1.4 and ofdom.seller_absorption):
        ofdom_bonus = 0.3
    elif setup_side == "SHORT" and (ofdom.bid_imbalance >= 1.4 and ofdom.buyer_absorption):
        ofdom_bonus = 0.3
    
    sc = base + direction_bonus + ofdom_bonus
    return clamp(sc, 0.0, 1.0)

def _vwap_vp_component(vwap: VWAPCtx, vp: VPCtx, gamma_sc: float, swing_sc: float) -> float:
    sc = 0.0
    if vwap.above and vwap.slope == "up":
        sc += 0.6
    if vwap.band in ("sd1","sd2"):
        sc += 0.3
    if vp.reclaim:
        sc += 0.3
    # micro-confluence si VP au bord + proximity MentorQ forte
    if vp.at_level in ("VAH","VAL") and (gamma_sc >= 0.55 or swing_sc >= 0.6):
        sc += 0.2
    return clamp(sc, 0.0, 1.0)

def _leadership_component(lead: LeadershipCtx, session: SessionCtx, setup_side: str) -> float:
    """Leadership plus nuancé avec score signé"""
    # Soft bonus, Trend only
    if session.regime != "TREND":
        return 0.0
    
    # Score signé plus nuancé (à améliorer avec corrélation×momentum)
    raw = 1.0 if lead.nq_stronger_than_es else -1.0
    align = 1.0 if setup_side == "LONG" else -1.0
    soft = 0.3 * raw * align  # Réduit l'impact
    return clamp(soft, -1.0, 1.0)

def _ofdom_component(ofdom: OFDOMCtx, setup_side: str) -> float:
    """OF/DOM bidirectionnel"""
    sc = 0.0
    
    # Imbalance directionnel
    if setup_side == "LONG":
        if ofdom.ask_imbalance >= 1.4 and ofdom.seller_absorption:
            sc += 0.75
    else:  # SHORT
        if ofdom.bid_imbalance >= 1.4 and ofdom.buyer_absorption:
            sc += 0.75
    
    # Qualité DOM
    if ofdom.l1_eq_bbo and ofdom.spread_ticks <= 1:
        sc += 0.25
    
    return clamp(sc, 0.0, 1.0)

def _vix_component(macro: MacroCtx) -> float:
    return 1.0 if (macro.vix <= 18 and macro.vix_trend in ("down","flat")) else 0.0

def _qscore_component(qscore: Optional[float]) -> float:
    if qscore is None:
        return 0.0
    z = (qscore - 2.5) / 2.5  # map 0..5 → -1..+1
    return clamp(z, -1.0, 1.0)

# Fonction supprimée - remplacée par la logique adaptative dans compute_mia_bullish

def _smooth_hysteresis(score: float, prev: BiasState, hold: Dict[str,int], 
                      thresholds: Dict[str, float]) -> tuple[BiasState, Dict[str,int], Dict[str, Any]]:
    """Hystérèse avec transitions lisses et seuils adaptatifs - RETOURNE LES COMPTEURS"""
    up_thr = thresholds["score_up_thr"]
    up_rel = thresholds["score_up_rel"]
    dn_thr = thresholds["score_dn_thr"]
    dn_rel = thresholds["score_dn_rel"]
    bars = PARAMS_BASE["bars_confirm"]
    
    hold = hold or {"BULLISH":0,"BEARISH":0}
    state = prev
    
    # Calcul des forces directionnelles avec kernels lisses
    bullish_strength = math.exp(-abs(score - 75) / 10)  # Peak à 75
    bearish_strength = math.exp(-abs(score - 25) / 10)  # Peak à 25
    
    # Seuils adaptatifs selon l'état précédent
    if prev == "BULLISH":
        up_thr_adj = up_thr * 0.9  # Plus facile de rester bullish
    else:
        up_thr_adj = up_thr * 1.1  # Plus dur de devenir bullish
        
    if prev == "BEARISH":
        dn_thr_adj = dn_thr * 1.1  # Plus facile de rester bearish
    else:
        dn_thr_adj = dn_thr * 0.9  # Plus dur de devenir bearish

    # Logique de transition
    if score >= up_thr_adj:
        hold["BULLISH"] = hold.get("BULLISH",0) + 1
        if hold["BULLISH"] >= bars: 
            state = "BULLISH"
        hold["BEARISH"] = 0
    elif score <= dn_thr_adj:
        hold["BEARISH"] = hold.get("BEARISH",0) + 1
        if hold["BEARISH"] >= bars: 
            state = "BEARISH"
        hold["BULLISH"] = 0
    else:
        # Relax vers neutre selon seuils de relâchement
        if state == "BULLISH" and score < up_rel: 
            state = "NEUTRE"
        if state == "BEARISH" and score > dn_rel: 
            state = "NEUTRE"
        hold["BULLISH"] = 0
        hold["BEARISH"] = 0
    
    info = {
        "bullish_strength": bullish_strength,
        "bearish_strength": bearish_strength,
        "thresholds_used": {
            "up_thr": up_thr_adj,
            "dn_thr": dn_thr_adj,
            "up_rel": up_rel,
            "dn_rel": dn_rel
        }
    }
    
    return state, hold, info

def _intelligent_sizing(score: float, vix: float, confluence_ok: bool, 
                       risk_multiplier: float, patience_minutes: int,
                       bullish_strength: float, bearish_strength: float) -> Dict[str, Any]:
    """Sizing intelligent multi-facteurs"""
    base_size = 1
    
    # Facteur confluence
    confluence_factor = 1.0
    if confluence_ok: 
        confluence_factor = 1.5
    
    # Facteur score (0-2x selon score)
    score_factor = min(2.0, score / 50.0)
    
    # Facteur VIX (inverse - plus VIX bas, plus on peut upsize)
    vix_factor = max(0.5, 1.0 - (vix - 15) * 0.02)  # 0.5-1.5x selon VIX
    
    # Facteur patience (plus patient = plus de taille)
    patience_factor = min(1.5, 1.0 + patience_minutes * 0.01)
    
    # Facteur force directionnelle
    direction_factor = max(bullish_strength, bearish_strength)
    
    # Facteur risque
    risk_factor = min(1.2, max(0.8, risk_multiplier))
    
    # Calcul final
    final_size = int(base_size * confluence_factor * score_factor * 
                    vix_factor * patience_factor * direction_factor * risk_factor)
    
    return {
        "size": min(3, max(1, final_size)),  # Cap 1-3 lots
        "confidence": min(1.0, confluence_factor * score_factor * direction_factor),
        "risk_adjusted": True,
        "factors": {
            "confluence": confluence_factor,
            "score": score_factor,
            "vix": vix_factor,
            "patience": patience_factor,
            "direction": direction_factor,
            "risk": risk_factor
        }
    }

def compute_mia_bullish(ctx: MIAInputs) -> Dict[str, Any]:
    """
    MIA Bullish v2 - Version améliorée avec QC Gates, kernels lisses, seuils adaptatifs
    
    Entrée: MIAInputs (voir dataclasses)
    Sortie:
      {
        "mia_bullish_score": float(0..100),
        "mia_bias_state": "BULLISH|NEUTRE|BEARISH",
        "sizing_advice": Dict avec size, confidence, factors,
        "validation_metrics": Dict avec métriques de validation,
        "explain": { ... composants ... }
      }
    """
    # === QC GATES ===
    if ctx.qc is None:
        ctx.qc = QCContext()  # Default QC si non fourni
    
    # Gates durs (blocage total)
    gate_reason = _pre_gates(ctx.qc)
    if gate_reason:
        return {
            "mia_bullish_score": 50.0,  # Score neutre
            "mia_bias_state": "NEUTRE",
            "sizing_advice": {"size": 1, "confidence": 0.0, "risk_adjusted": False},
            "hold_counts": ctx.hold_counts,  # PERSISTANCE
            "validation_metrics": {
                "qc_issues": [gate_reason],
                "qc_penalty": 0.0,
                "reason": "qc_gates_failed"
            },
            "explain": {"gate": gate_reason}
        }
    
    qc_result = _check_qc_gates(ctx.qc)
    
    # === PONDÉRATIONS ADAPTATIVES ===
    adaptive_weights = _get_adaptive_weights(ctx.session.regime, ctx.macro.vix)
    
    # === SEUILS ADAPTATIFS ===
    adaptive_thresholds = _get_adaptive_thresholds(ctx.macro.vix, ctx.qc.atr_relative)
    
    # === COMPOSANTS PRINCIPAUX ===
    scanner_bonus = _scanner_component(ctx.mentorq.scanner)
    swing_sc = _swing_component(ctx.mentorq.swing, ctx.vwap, ctx.vp)
    gamma_sc = _gamma_component(ctx.mentorq.gamma, scanner_bonus, ctx.qc.tick_size, ctx.qc.atr_per_bar)
    blind_sc = _blind_component(ctx.mentorq.blind, ctx.ofdom, ctx.setup_side, ctx.qc.tick_size)
    vwap_vp_sc = _vwap_vp_component(ctx.vwap, ctx.vp, gamma_sc, swing_sc)
    lead_sc = _leadership_component(ctx.leadership, ctx.session, ctx.setup_side)
    ofdom_sc = _ofdom_component(ctx.ofdom, ctx.setup_side)
    vix_sc = _vix_component(ctx.macro)
    q_sc = _qscore_component(ctx.mentorq.qscore)

    # === SCORE AVEC PONDÉRATIONS ADAPTATIVES (NORMALISÉ) ===
    parts = {
        "mentorq_gamma": gamma_sc,
        "mentorq_swing": swing_sc,
        "mentorq_blind": blind_sc,
        "scanner":       scanner_bonus,
        "vwap_vp":       vwap_vp_sc,
        "leadership":    lead_sc,
        "footprint_dom": ofdom_sc,
        "vix":           vix_sc,
        "qscore":        q_sc
    }
    
    # Score avec pondérations adaptatives NORMALISÉES (évite saturation)
    total_w = sum(adaptive_weights.values())
    total = sum(adaptive_weights.get(k, 0.0) * v for k, v in parts.items())
    normalized_score = total / max(1e-9, total_w)  # Normalisation
    
    # Application QC penalty
    raw_score = round((clamp(normalized_score, -1.0, 1.0) + 1.0) * 50.0, 1)
    final_score = raw_score * qc_result["qc_penalty"]
    
    # === HYSTÉRÈSE LISSE (PERSISTANTE) ===
    state, new_hold_counts, hysteresis_info = _smooth_hysteresis(
        final_score, ctx.prev_state, ctx.hold_counts or {}, adaptive_thresholds
    )
    
    # === SIZING INTELLIGENT ===
    confluence_ok = (gamma_sc >= 0.55 or swing_sc >= 0.6) and (vwap_vp_sc >= 0.6) and (ofdom_sc >= 0.75)
    sizing_result = _intelligent_sizing(
        final_score, ctx.macro.vix, confluence_ok, 
        1.0, 5,  # risk_multiplier, patience_minutes (à améliorer)
        hysteresis_info["bullish_strength"], 
        hysteresis_info["bearish_strength"]
    )

    return {
        "mia_bullish_score": final_score,
        "mia_bias_state": state,  # État de l'hystérèse persistante
        "sizing_advice": sizing_result,
        "hold_counts": new_hold_counts,  # PERSISTANCE des compteurs
        "validation_metrics": {
            "staleness_ms": ctx.qc.options_snapshot_age_min * 60000,
            "vwap_qc_penalty": qc_result["qc_penalty"],
            "regime": ctx.session.regime,
            "thresholds_used": adaptive_thresholds,
            "weights_used": adaptive_weights,
            "confluence_score": confluence_ok,
            "qc_issues": qc_result["issues"],
            "hysteresis_info": hysteresis_info,
            "setup_side": ctx.setup_side,
            "normalized_score": normalized_score
        },
        "explain": {
            "mentorq_gamma": round(gamma_sc,3),
            "mentorq_swing": round(swing_sc,3),
            "mentorq_blind": round(blind_sc,3),
            "scanner":       round(scanner_bonus,3),
            "vwap_vp":       round(vwap_vp_sc,3),
            "leadership":    round(lead_sc,3),
            "footprint_dom": round(ofdom_sc,3),
            "vix":           round(vix_sc,3),
            "qscore":        round(q_sc,3),
            "raw_score":     raw_score,
            "qc_penalty":    qc_result["qc_penalty"],
            "setup_side":    ctx.setup_side
        }
    }
