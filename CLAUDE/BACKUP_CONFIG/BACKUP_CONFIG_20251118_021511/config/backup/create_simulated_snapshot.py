#!/usr/bin/env python3
"""
create_simulated_snapshot.py

Script pour créer un snapshot de test avec données SIMULÉES
- Simule les données options pour tests
- Inclut tous les champs Dealer's Bias
- Permet de tester l'analyzer sans connexion IBKR
"""

import json
import os
from datetime import datetime
from pathlib import Path
import random

def create_simulated_snapshot(symbol: str = "SPX"):
    """Crée un snapshot de test avec données simulées"""
    
    # Prix sous-jacent simulé
    if symbol == "SPX":
        underlying_price = 6477.0
        strikes = [6200, 6250, 6300, 6350, 6400, 6450, 6500, 6550, 6600, 6650, 6700, 6750]
        vol_index = 18.5  # VIX
    else:  # NDX
        underlying_price = 18500.0
        strikes = [18000, 18250, 18500, 18750, 19000, 19250, 19500, 19750, 20000]
        vol_index = 22.3  # VXN
    
    # Générer options simulées
    options = []
    for strike in strikes:
        # Call
        call_iv = 0.15 + random.uniform(-0.05, 0.05)
        call_delta = max(0.01, min(0.99, (underlying_price - strike) / (underlying_price * 0.1)))
        call_gamma = 0.001 + random.uniform(0, 0.002)
        call_theta = -0.5 + random.uniform(-0.5, 0.5)
        call_vega = 50 + random.uniform(-20, 20)
        
        options.append({
            "symbol": symbol,
            "expiry": "20250919",
            "strike": strike,
            "type": "C",
            "bid": max(0.01, call_delta * underlying_price * 0.1),
            "ask": max(0.01, call_delta * underlying_price * 0.1 + 0.5),
            "last": max(0.01, call_delta * underlying_price * 0.1 + 0.25),
            "volume": random.randint(10, 500),
            "open_interest": random.randint(100, 2000),
            "delta": call_delta,
            "gamma": call_gamma,
            "theta": call_theta,
            "vega": call_vega,
            "iv": call_iv
        })
        
        # Put
        put_iv = 0.18 + random.uniform(-0.05, 0.05)  # IV plus élevée pour les puts
        put_delta = max(-0.99, min(-0.01, -(underlying_price - strike) / (underlying_price * 0.1)))
        put_gamma = 0.001 + random.uniform(0, 0.002)
        put_theta = -0.5 + random.uniform(-0.5, 0.5)
        put_vega = 50 + random.uniform(-20, 20)
        
        options.append({
            "symbol": symbol,
            "expiry": "20250919",
            "strike": strike,
            "type": "P",
            "bid": max(0.01, abs(put_delta) * underlying_price * 0.1),
            "ask": max(0.01, abs(put_delta) * underlying_price * 0.1 + 0.5),
            "last": max(0.01, abs(put_delta) * underlying_price * 0.1 + 0.25),
            "volume": random.randint(10, 500),
            "open_interest": random.randint(100, 2000),
            "delta": put_delta,
            "gamma": put_gamma,
            "theta": put_theta,
            "vega": put_vega,
            "iv": put_iv
        })
    
    # Calculer les métriques
    calls_oi = sum(o["open_interest"] for o in options if o["type"] == "C")
    puts_oi = sum(o["open_interest"] for o in options if o["type"] == "P")
    total_oi = calls_oi + puts_oi
    pcr_oi = puts_oi / calls_oi if calls_oi > 0 else 1.0
    
    calls_volume = sum(o["volume"] for o in options if o["type"] == "C")
    puts_volume = sum(o["volume"] for o in options if o["type"] == "P")
    pcr_volume = puts_volume / calls_volume if calls_volume > 0 else 1.0
    
    ivs = [o["iv"] for o in options if o["iv"]]
    iv_avg = sum(ivs) / len(ivs) if ivs else 0.16
    
    iv_calls = [o["iv"] for o in options if o["type"] == "C" and o["iv"]]
    iv_puts = [o["iv"] for o in options if o["type"] == "P" and o["iv"]]
    iv_calls_avg = sum(iv_calls) / len(iv_calls) if iv_calls else 0.15
    iv_puts_avg = sum(iv_puts) / len(iv_puts) if iv_puts else 0.18
    iv_skew = iv_puts_avg - iv_calls_avg
    
    # GEX simulé
    contract_multiplier = 100
    gex_total = 0.0
    for o in options:
        gamma = o["gamma"]
        oi = o["open_interest"]
        gex_total += gamma * underlying_price * underlying_price * oi * contract_multiplier
    
    # Gamma Flip simulé
    gamma_flip_strike = underlying_price + random.uniform(-100, 100)
    
    # Gamma Pins simulés
    gamma_pins = [
        {
            "strike": underlying_price + random.uniform(-50, 50),
            "gamma_exposure": random.uniform(1e9, 5e9),
            "distance_from_current": random.uniform(-50, 50),
            "strength": random.uniform(1.2, 2.0),
            "strength_category": "Strong"
        }
    ]
    
    # Dealer's Bias simulé
    dealers_bias_score = random.uniform(-0.8, 0.8)
    direction = "BULLISH" if dealers_bias_score > 0.2 else "BEARISH" if dealers_bias_score < -0.2 else "NEUTRAL"
    strength = "STRONG" if abs(dealers_bias_score) > 0.5 else "MODERATE" if abs(dealers_bias_score) > 0.2 else "WEAK"
    
    # Créer le snapshot
    snapshot = {
        "snapshot_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "symbol": symbol,
        "expiry": "20250919",
        "timestamp": datetime.now().isoformat(),
        "data_source": "SIMULATION",
        "options": options,
        "analysis": {
            "timestamp": datetime.now().isoformat(),
            "underlying_price": underlying_price,
            "put_call_ratio_oi": round(pcr_oi, 4),
            "put_call_ratio_volume": round(pcr_volume, 4),
            "implied_volatility_avg": round(iv_avg, 4),
            "iv_calls_avg": round(iv_calls_avg, 4),
            "iv_puts_avg": round(iv_puts_avg, 4),
            "iv_skew_puts_minus_calls": round(iv_skew, 4),
            "open_interest": {
                "calls_oi": calls_oi,
                "puts_oi": puts_oi,
                "total_oi": total_oi
            },
            "max_pain": underlying_price + random.uniform(-50, 50),
            "gex": {
                "gex_total_magnitude": abs(gex_total),
                "gex_total_signed": gex_total,
                "gex_calls_magnitude": abs(gex_total * 0.4),
                "gex_puts_magnitude": abs(gex_total * 0.6),
                "dealer_sign_assumption": -1,
                "normalized": {
                    "gex_total_signed_normalized": gex_total / 1e9,
                    "total_notional": total_oi * underlying_price * contract_multiplier
                }
            },
            "gamma_flip": {
                "gamma_flip_strike": gamma_flip_strike,
                "cumulative_gamma_at_flip": gex_total * 0.5,
                "distance_from_current": gamma_flip_strike - underlying_price
            },
            "gamma_pins": gamma_pins,
            "dealers_bias": {
                "dealers_bias_score": round(dealers_bias_score, 4),
                "dealers_bias_raw": round((dealers_bias_score + 1) / 2, 4),
                "components": {
                    "gamma_flip_bias": 0.5,
                    "gamma_pins_bias": 0.5,
                    "pcr_bias": 0.5,
                    "skew_bias": 0.5,
                    "vix_bias": 0.5,
                    "gex_bias": 0.5
                },
                "interpretation": {
                    "direction": direction,
                    "strength": strength
                }
            }
        }
    }
    
    # Ajouter l'indice de volatilité approprié
    if symbol == "SPX":
        snapshot["analysis"]["vix"] = vol_index
    else:
        snapshot["analysis"]["vxn"] = vol_index
    
    return snapshot

def save_simulated_snapshots():
    """Sauvegarde les snapshots simulés"""
    
    # Créer le dossier
    outdir = "data/options_snapshots/simulation"
    os.makedirs(outdir, exist_ok=True)
    
    # Créer SPX snapshot
    spx_snapshot = create_simulated_snapshot("SPX")
    spx_path = os.path.join(outdir, f"spx_simulated_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(spx_path, "w", encoding="utf-8") as f:
        json.dump(spx_snapshot, f, indent=2)
    
    # Créer NDX snapshot
    ndx_snapshot = create_simulated_snapshot("NDX")
    ndx_path = os.path.join(outdir, f"ndx_simulated_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(ndx_path, "w", encoding="utf-8") as f:
        json.dump(ndx_snapshot, f, indent=2)
    
    print(f"✅ SPX snapshot simulé créé: {spx_path}")
    print(f"✅ NDX snapshot simulé créé: {ndx_path}")
    
    return [spx_path, ndx_path]

if __name__ == "__main__":
    print("🚀 Création des snapshots SIMULÉS pour tests...")
    paths = save_simulated_snapshots()
    print(f"🎯 {len(paths)} snapshots simulés créés avec succès !")
    print("📊 Prêt pour tester l'analyzer DealersBiasAnalyzer (mode simulation)")
