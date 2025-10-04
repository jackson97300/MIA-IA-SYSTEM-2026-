# -*- coding: utf-8 -*-
"""
MenthorQDecisionEngine.py
Matrice décisionnelle ES/NQ (MIA + MentorQ) — version intégrée 2025-09-24

Inputs attendus (dict 'ctx') — format compact, agnostique côté source:
{
  "sym": "ES"|"NQ",
  "t":  1695465600.0,                # epoch seconds
  "price": 4567.25,                  # last/close
  "session": {"phase":"OPEN|MID|POWER|OFF","regime":"TREND|RANGE|DEFENSIF"},
  "macro":   {"vix":17.2,"vix_trend":"down|flat|up"},
  "mentorq":{
      "gamma":   {"dist_to_HVL_pts":2.0,"flip_active":true,"wall_side":"CALL|PUT|None"},
      "swing":   {"avail":true,"state":"below|at|above","dist_pts":3.0,"retest_ok":false},
      "blind":   {"nearby":false,"distance_ticks":12,"direction":"up|down|None"},
      "scanner": {"recent":{"HVL_BREAK":{"age":18},"1D_MAX_TOUCH":{"age":35}}},
      "qscore":  3.8                                  # 0..5 ou None
  },
  "micro":{
      "vwap":{"above":true,"slope":"up|flat|down","band":"inside|sd1|sd2"},
      "vp":{"at_level":"POC|VAH|VAL|none","reclaim":true}
  },
  "ofdom":{
      "ask_imbalance":1.6,"seller_absorption":true,
      "l1_eq_bbo":true,"spread_ticks":1
  },
  "lead":{"nq_stronger_than_es":true,"sync_ok":true}, # soft bonus
  "cluster":{"signals":{"cluster_confluence":true,"cluster_strong":true,"status":"inside|outside"}},
  "mia": {"score":72.4,"state":"BULLISH|NEUTRE|BEARISH"},  # si non fourni, la Gate sera NEUTRE
  "prev": {"state":"NEUTRE"}                               # hystérèse éventuelle côté appelant
}

Sortie:
{
  "action":"ENTER|UPDATE|LIQUIDATE|FLAT",
  "side":"LONG|SHORT|NONE",
  "reason":"text",
  "entry":4568.5, "stop":4566.5, "tp1":4572.5, "tp2":4576.5,
  "scenario":"TOUCH_FADE|BREAK_TREND|RETEST_PREMIUM",
  "confidence":0.0..1.0, "label":"Weak|Moderate|Strong|Extreme",
  "risk":{"sl_ticks":8,"tp1_r":1.0,"tp2_r":2.0,"time_stop_min":15,"size_lots":1}
}
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple

TICK = 0.25

# ========================= CONFIG =========================

WEIGHTS = {
    "mentorq_gamma": 0.30,
    "mentorq_swing": 0.20,
    "mentorq_blind": 0.10,
    "scanner":       0.10,
    "vwap_vp":       0.12,
    "leadership":    0.06,   # soft, Trend only
    "footprint_dom": 0.08,
    "vix":           0.02,
    "qscore":        0.10
}

PARAMS = {
    # Règles risk/stops
    "sl_ticks": 8,
    "tp1_R": 1.0,
    "tp2_R": 2.0,
    "time_stop_min": 15,

    # Scanner temps réel
    "scanner_ttl": 90,
    "scanner_debounce": 20,

    # VIX regimes (sizing)
    "vix_upsize_max": 18.0,
    "vix_hi_cap":     25.0,

    # True break & retest
    "true_break_follow_ticks": 4,
    "retest_window_min": 3,
    "retest_window_max": 10,

    # Confluence pour autoriser upsize
    "min_ofdom_for_upsize": 0.75,
    "min_vwapvp_for_upsize": 0.60,
    "min_gamma_or_swing_for_upsize": (0.55, 0.60),  # gamma>=.55 OR swing>=.60

    # Leadership
    "leadership_trend_only": True
}

# ========================= HELPERS =========================

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

def vix_regime(vix: float) -> str:
    if vix is None: return "NORMAL"
    if vix < 15: return "LOW"
    if vix <= 25: return "NORMAL"
    return "HIGH"

def soft_lead_bonus(ctx: Dict[str,Any], side: str) -> float:
    # Trend only, soft bonus/pénalité [-1..+1] réduit
    if PARAMS["leadership_trend_only"] and ctx.get("session",{}).get("regime") != "TREND":
        return 0.0
    lead = ctx.get("lead",{})
    nq_gt_es = bool(lead.get("nq_stronger_than_es", False))
    align = 1.0 if side == "LONG" else -1.0
    raw = 1.0 if nq_gt_es else -1.0
    return clamp(0.5 * raw * align, -1.0, 1.0)

def scanner_bonus(scanner: Dict[str,Any]) -> float:
    if not scanner: return 0.0
    val = 0.0
    for evt, meta in (scanner.get("recent") or {}).items():
        age = float(meta.get("age", 9e9))
        if age > PARAMS["scanner_ttl"]: 
            continue
        if evt == "HVL_BREAK": val += 0.6
        elif evt == "1D_MAX_TOUCH": val += 0.4
        elif evt == "PUT_SUPPORT_BREAK": val -= 0.6
    return clamp(val, -1.0, 1.0)

def component_scores(ctx: Dict[str,Any], side: str) -> Dict[str,float]:
    # ---- MentorQ: Gamma
    g = ctx.get("mentorq",{}).get("gamma",{}) or {}
    sc_gamma = 0.0
    if g.get("flip_active") and (g.get("dist_to_HVL_pts", 9e9) <= 2):
        sc_gamma += 1.0
    elif g.get("dist_to_HVL_pts", 9e9) <= 5:
        sc_gamma += 0.55
    sc_scan = scanner_bonus(ctx.get("mentorq",{}).get("scanner"))
    sc_gamma += 0.15 * max(0.0, sc_scan)
    sc_gamma = clamp(sc_gamma, 0.0, 1.0)

    # ---- MentorQ: Swing
    s = ctx.get("mentorq",{}).get("swing",{}) or {}
    sc_swing = 0.0
    if s.get("avail"):
        state = s.get("state")
        if state == "at": sc_swing += 0.6
        elif state == "above": sc_swing += (1.0 if s.get("retest_ok") else 0.6)
        # bonus micro
        vwap = ctx.get("micro",{}).get("vwap",{}) or {}
        vp   = ctx.get("micro",{}).get("vp",{}) or {}
        if vwap.get("above") and vwap.get("slope") == "up": sc_swing += 0.2
        if vp.get("reclaim"): sc_swing += 0.2
    sc_swing = clamp(sc_swing, 0.0, 1.0)

    # ---- MentorQ: Blind
    b = ctx.get("mentorq",{}).get("blind",{}) or {}
    of = ctx.get("ofdom",{}) or {}
    sc_blind = 0.0
    if b.get("nearby") and b.get("distance_ticks", 999) <= 10:
        sc_blind = 0.7 if (of.get("ask_imbalance",1.0)>=1.4 and of.get("seller_absorption")) else 0.3

    # ---- Micro: VWAP/VP
    vwap = ctx.get("micro",{}).get("vwap",{}) or {}
    vp   = ctx.get("micro",{}).get("vp",{}) or {}
    sc_vwapvp = 0.0
    if vwap.get("above") and vwap.get("slope") == "up": sc_vwapvp += 0.6
    if vwap.get("band") in ("sd1","sd2"): sc_vwapvp += 0.3
    if vp.get("reclaim"): sc_vwapvp += 0.3
    if vp.get("at_level") in ("VAH","VAL") and (sc_gamma>=0.55 or sc_swing>=0.6): sc_vwapvp += 0.2
    sc_vwapvp = clamp(sc_vwapvp, 0.0, 1.0)

    # ---- Leadership soft
    sc_lead = soft_lead_bonus(ctx, side)

    # ---- Footprint/DOM
    sc_ofdom = 0.0
    if of.get("ask_imbalance",1.0)>=1.4 and of.get("seller_absorption"): sc_ofdom += 0.75
    if of.get("l1_eq_bbo") and of.get("spread_ticks",9) <= 1: sc_ofdom += 0.25
    sc_ofdom = clamp(sc_ofdom, 0.0, 1.0)

    # ---- VIX
    m = ctx.get("macro",{}) or {}
    sc_vix = 1.0 if (m.get("vix",99) <= 18 and m.get("vix_trend") in ("down","flat")) else 0.0

    # ---- Q-Score
    q = ctx.get("mentorq",{}).get("qscore")
    if q is None: sc_q = 0.0
    else: sc_q = clamp((float(q)-2.5)/2.5, -1.0, 1.0)

    # ---- Scanner (déjà calculé sc_scan)
    parts = {
        "mentorq_gamma": sc_gamma,
        "mentorq_swing": sc_swing,
        "mentorq_blind": clamp(sc_blind,0.0,1.0),
        "scanner":       sc_scan,
        "vwap_vp":       sc_vwapvp,
        "leadership":    sc_lead,
        "footprint_dom": sc_ofdom,
        "vix":           sc_vix,
        "qscore":        sc_q
    }
    return parts

def confluence_score(parts: Dict[str,float]) -> float:
    # pondération → conf [-1..+1] puis mapping [0..100]
    total = 0.0
    for k,v in parts.items():
        total += WEIGHTS.get(k,0.0)*v
    return clamp(total, -1.0, 1.0)

def label_from_conf(conf: float) -> Tuple[str,float]:
    # conf ∈ [-1..+1] ; on renvoie label + confidence (0..1)
    c = (conf+1.0)/2.0
    if c >= 0.85: return "Extreme", c
    if c >= 0.70: return "Strong", c
    if c >= 0.55: return "Moderate", c
    return "Weak", c

def gate_mia(ctx: Dict[str,Any], desired_side: str) -> Tuple[bool,str]:
    mia = ctx.get("mia",{}) or {}
    state = mia.get("state","NEUTRE")
    if desired_side == "LONG" and state != "BULLISH":
        return False, f"MIA gate: state={state} != BULLISH"
    if desired_side == "SHORT" and state != "BEARISH":
        return False, f"MIA gate: state={state} != BEARISH"
    return True, "OK"

def cluster_hint(ctx: Dict[str,Any]) -> Optional[str]:
    s = (ctx.get("cluster",{}) or {}).get("signals",{}) or {}
    if s.get("cluster_confluence") and s.get("cluster_strong"):
        return "inside" if s.get("status") == "inside" else "outside"
    return None

def scenario_detect(ctx: Dict[str,Any]) -> str:
    """
    Décide le scénario cible en fonction:
    - Cluster hint (inside → fade ; outside → breakout)
    - Swing state/HVL proximity + scanner
    """
    hint = cluster_hint(ctx)
    mq = ctx.get("mentorq",{})
    g  = mq.get("gamma",{}) or {}
    s  = mq.get("swing",{}) or {}
    scan = scanner_bonus(mq.get("scanner"))

    if hint == "inside":
        return "TOUCH_FADE"
    if hint == "outside":
        return "BREAK_TREND"

    # Sans cluster, heuristiques:
    if s.get("avail") and s.get("state") == "at":
        return "TOUCH_FADE"
    if g.get("dist_to_HVL_pts",9e9) <= 2 and scan > 0:
        return "BREAK_TREND"
    if s.get("avail") and s.get("state") == "above" and s.get("retest_ok"):
        return "RETEST_PREMIUM"
    return "RETEST_PREMIUM"  # défaut “sûr” (attente retest)

def compute_levels(price: float, side: str, scenario: str) -> Tuple[float,float,float,float]:
    """
    Calcule entry/stop/tp1/tp2 en fonction du scénario.
    Rappels:
      - jamais pile sur le niveau: offset +1 tick
      - SL fixe 8 ticks
      - TP1=1R, TP2=2R
    """
    sl_ticks = PARAMS["sl_ticks"]
    R = sl_ticks * TICK
    if side == "LONG":
        entry = price + 1*TICK
        stop  = entry - sl_ticks*TICK
        tp1   = entry + R
        tp2   = entry + 2*R
    else:
        entry = price - 1*TICK
        stop  = entry + sl_ticks*TICK
        tp1   = entry - R
        tp2   = entry - 2*R
    # Ajustements mineurs par scénario (optionnels, conservateurs)
    if scenario == "TOUCH_FADE":
        # TP1 un peu plus proche pour fade
        k = 0.9
        if side == "LONG": tp1 = entry + k*R
        else:              tp1 = entry - k*R
    return round(entry,2), round(stop,2), round(tp1,2), round(tp2,2)

def sizing_from(ctx: Dict[str,Any], parts: Dict[str,float], conf: float) -> int:
    vix = ctx.get("macro",{}).get("vix", 30.0)
    ofdom = parts.get("footprint_dom",0.0)
    vwapvp = parts.get("vwap_vp",0.0)
    gamma_ok = parts.get("mentorq_gamma",0.0) >= PARAMS["min_gamma_or_swing_for_upsize"][0]
    swing_ok = parts.get("mentorq_swing",0.0) >= PARAMS["min_gamma_or_swing_for_upsize"][1]
    confluence_ok = (ofdom >= PARAMS["min_ofdom_for_upsize"] and
                     vwapvp >= PARAMS["min_vwapvp_for_upsize"] and
                     (gamma_ok or swing_ok))
    if vix > PARAMS["vix_hi_cap"]:
        return 1
    if conf >= 0.70 and vix < PARAMS["vix_upsize_max"] and confluence_ok:
        return 2
    return 1

# ========================= CORE DECISION =========================

def decide(ctx: Dict[str,Any]) -> Dict[str,Any]:
    """
    Décision E/U/L complète. Côté appelant, on fournit 'ctx' (cf. schema en tête).
    """
    price = float(ctx.get("price", 0.0))
    # Déterminer le côté par MIA (sinon neutre → FLAT)
    mia_state = (ctx.get("mia",{}) or {}).get("state","NEUTRE")
    if mia_state == "BULLISH":
        side = "LONG"
    elif mia_state == "BEARISH":
        side = "SHORT"
    else:
        return {
            "action":"FLAT","side":"NONE","reason":"MIA neutral",
            "scenario":None,"confidence":0.0,"label":"Weak",
            "risk":{"sl_ticks":PARAMS["sl_ticks"],"tp1_r":PARAMS["tp1_R"],"tp2_r":PARAMS["tp2_R"],
                    "time_stop_min":PARAMS["time_stop_min"],"size_lots":0}
        }

    # Composants de confluence
    parts = component_scores(ctx, side)
    conf  = confluence_score(parts)             # [-1..+1]
    label, conf01 = label_from_conf(conf)      # (label, 0..1)

    # Gating MIA (bloquant)
    ok, why = gate_mia(ctx, side)
    if not ok:
        return {"action":"FLAT","side":"NONE","reason":why,"scenario":None,
                "confidence":conf01,"label":label,
                "risk":{"sl_ticks":PARAMS["sl_ticks"],"tp1_r":PARAMS["tp1_R"],"tp2_r":PARAMS["tp2_R"],
                        "time_stop_min":PARAMS["time_stop_min"],"size_lots":0},
                "explain":parts}

    # Déterminer scénario (cluster + heuristiques)
    scen = scenario_detect(ctx)

    # Paramétrer prix d'entrée/stop/tp selon scénario
    entry, stop, tp1, tp2 = compute_levels(price, side, scen)

    # Taille (lots)
    lots = sizing_from(ctx, parts, conf01)

    # Action: ENTER si confluence suffisante et DOM sain; sinon FLAT / UPDATE minimal
    of = ctx.get("ofdom",{}) or {}
    dom_ok = of.get("l1_eq_bbo") and of.get("spread_ticks",9) <= 2
    if conf01 >= 0.55 and dom_ok:
        action = "ENTER"
        reason = f"{scen} with confluence {label}"
    else:
        action = "FLAT"
        reason = "Confluence/DOM insufficient"

    # Ajustement par Cluster Alerts (tactique)
    hint = cluster_hint(ctx)
    if hint == "inside" and scen != "TOUCH_FADE":
        scen = "TOUCH_FADE"; reason += " (cluster→fade)"
    elif hint == "outside" and scen != "BREAK_TREND":
        scen = "BREAK_TREND"; reason += " (cluster→break)"

    # Packaging final
    out = {
        "action": action,
        "side": side if action=="ENTER" else "NONE" if action=="FLAT" else side,
        "reason": reason,
        "entry": entry, "stop": stop, "tp1": tp1, "tp2": tp2,
        "scenario": scen,
        "confidence": round(conf01,3),
        "label": label,
        "risk": {
            "sl_ticks": PARAMS["sl_ticks"],
            "tp1_r": PARAMS["tp1_R"],
            "tp2_r": PARAMS["tp2_R"],
            "time_stop_min": PARAMS["time_stop_min"],
            "size_lots": lots
        },
        "explain": {k: round(float(v),3) for k,v in parts.items()},
        "meta": {
            "vix_regime": vix_regime(ctx.get("macro",{}).get("vix", None)),
            "tick": TICK
        }
    }
    return out


# ========================= EXEMPLE RAPIDE =========================
if __name__ == "__main__":
    # Petit smoke test
    ctx_demo = {
        "sym":"NQ","price": 18500.25,
        "session":{"phase":"MID","regime":"TREND"},
        "macro":{"vix":16.5,"vix_trend":"flat"},
        "mentorq":{
            "gamma":{"dist_to_HVL_pts":1.5,"flip_active":True,"wall_side":"CALL"},
            "swing":{"avail":True,"state":"above","dist_pts":3.0,"retest_ok":True},
            "blind":{"nearby":True,"distance_ticks":8,"direction":"up"},
            "scanner":{"recent":{"HVL_BREAK":{"age":30}}},
            "qscore":4.1
        },
        "micro":{
            "vwap":{"above":True,"slope":"up","band":"sd1"},
            "vp":{"at_level":"POC","reclaim":True}
        },
        "ofdom":{"ask_imbalance":1.6,"seller_absorption":True,"l1_eq_bbo":True,"spread_ticks":1},
        "lead":{"nq_stronger_than_es":True,"sync_ok":True},
        "cluster":{"signals":{"cluster_confluence":True,"cluster_strong":True,"status":"outside"}},
        "mia":{"score":72.4,"state":"BULLISH"}
    }
    import json
    print(json.dumps(decide(ctx_demo), indent=2))
