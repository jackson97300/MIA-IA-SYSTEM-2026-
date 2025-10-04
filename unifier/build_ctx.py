def build_ctx(snapshot) -> dict:
    return {
        "sym": snapshot["sym"],            # "ES" / "NQ"
        "t": snapshot["t"],                # epoch seconds
        "price": snapshot["last"],
        "current_price": snapshot["last"],  # Pour compatibilité avec les méthodes Elite
        "timestamp": snapshot["t"],         # Pour compatibilité avec les méthodes Elite
        "session": {
            "phase": snapshot.get("phase") or snapshot.get("session", {}).get("phase", "REGULAR"), 
            "regime": snapshot.get("regime") or snapshot.get("session", {}).get("regime", "TREND")
        },
        "macro": {
            "vix": snapshot.get("vix") or snapshot.get("macro", {}).get("vix", 20.0), 
            "vix_trend": snapshot.get("vix_trend") or snapshot.get("macro", {}).get("vix_trend", "NEUTRAL")
        },
        "mentorq": {
            "gamma":   snapshot.get("mentorq_gamma") or snapshot.get("mentorq", {}).get("gamma", {}),
            "swing":   snapshot.get("mentorq_swing") or snapshot.get("mentorq", {}).get("swing", {"avail": False}),
            "blind":   snapshot.get("mentorq_blind") or snapshot.get("mentorq", {}).get("blind", {}),
            "scanner": snapshot.get("scanner") or snapshot.get("mentorq", {}).get("scanner", {"recent": {}}),
            "qscore":  snapshot.get("qscore") or snapshot.get("mentorq", {}).get("qscore", 0)
        },
        "micro": {
            "vwap": snapshot.get("vwap") or snapshot.get("micro", {}).get("vwap", {}),
            "vp":   snapshot.get("vp") or snapshot.get("micro", {}).get("vp", {})
        },
        "ofdom": snapshot.get("ofdom") or {},
        "lead":  snapshot.get("lead", {"nq_stronger_than_es": False, "sync_ok": True}),
        "leadership": snapshot.get("lead", {"nq_stronger_than_es": False, "sync_ok": True}),  # Alias pour compatibilité
        "cluster": snapshot.get("cluster", {"signals": {}}),
        "mia":   {
            "score": snapshot.get("mia_score") or snapshot.get("mia", {}).get("score", 0.0), 
            "state": snapshot.get("mia_state") or snapshot.get("mia", {}).get("state", "NEUTRE")
        },
        "prev":  {"state": snapshot.get("prev_state", "NEUTRE")},
        # === NOUVEAUX CHAMPS POUR MÉTHODES ELITE ===
        "elite_methods": {
            "menthorq_elite_enabled": True,
            "battle_navale_elite_enabled": True,
            "kernel_smooth_enabled": True,
            "orderflow_advanced_enabled": True,
            "dom_health_enabled": True
        },
        "qc_context": {
            "options_snapshot_age_min": snapshot.get("options_age_min", 0),
            "vwap_qc_p95": snapshot.get("vwap_qc_p95", 0.0),
            "data_quality_score": snapshot.get("data_quality", 1.0),
            "atr_per_bar": snapshot.get("atr_per_bar", 1.0),
            "atr_relative": snapshot.get("atr_relative", 1.0),
            "l1_bbo_ratio_rolling": snapshot.get("l1_bbo_ratio_rolling", 1.0),
            "symbol": snapshot["sym"],
            "tick_size": 0.25 if "ES" in snapshot["sym"] or "NQ" in snapshot["sym"] else 0.25
        }
    }
