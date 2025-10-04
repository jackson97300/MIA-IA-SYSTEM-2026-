#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pour vérifier les prix dans les fichiers trade et quote
"""

import json
from pathlib import Path

def analyze_prices(base_path, chart_name):
    """Analyse les prix dans les fichiers trade et quote"""
    chart_path = base_path / chart_name
    
    if not chart_path.exists():
        print(f"{chart_name}: Dossier non trouvé")
        return
    
    print(f"\n--- {chart_name} ---")
    
    # Trade
    trade_files = list(chart_path.glob('chart_*_trade_*.jsonl'))
    if trade_files:
        latest_trade = max(trade_files, key=lambda p: p.stat().st_mtime)
        print(f"TRADE: {latest_trade.name}")
        with open(latest_trade, 'r') as f:
            lines = f.readlines()
            if lines:
                try:
                    data = json.loads(lines[-1].strip())
                    price = data.get('price', 'N/A')
                    px_raw = data.get('px_raw', 'N/A')
                    sym = data.get('sym', 'N/A')
                    print(f"  Dernier: {sym} price={price}, px_raw={px_raw}")
                    
                    # Analyse de l'échelle
                    if isinstance(price, (int, float)) and isinstance(px_raw, (int, float)):
                        if px_raw > 0:
                            ratio = px_raw / price
                            print(f"  Ratio px_raw/price: {ratio:.2f}")
                            if abs(ratio - 100.0) < 1.0:
                                print("  ✅ Prix normalisé (÷100)")
                            else:
                                print("  ⚠️ Prix non normalisé")
                except Exception as e:
                    print(f"  Erreur parsing JSON: {e}")
    else:
        print("TRADE: Aucun fichier trouvé")
    
    # Quote  
    quote_files = list(chart_path.glob('chart_*_quote_*.jsonl'))
    if quote_files:
        latest_quote = max(quote_files, key=lambda p: p.stat().st_mtime)
        print(f"QUOTE: {latest_quote.name}")
        with open(latest_quote, 'r') as f:
            lines = f.readlines()
            if lines:
                try:
                    data = json.loads(lines[-1].strip())
                    bid = data.get('bid', 'N/A')
                    ask = data.get('ask', 'N/A')
                    sym = data.get('sym', 'N/A')
                    print(f"  Dernier: {sym} bid={bid}, ask={ask}")
                    
                    # Analyse de l'échelle
                    if isinstance(bid, (int, float)) and isinstance(ask, (int, float)):
                        if bid > 10000:
                            print("  ⚠️ Prix en échelle x100 (non normalisé)")
                        elif 1000 < bid < 10000:
                            print("  ✅ Prix en échelle humaine")
                        else:
                            print("  ❓ Échelle incertaine")
                except Exception as e:
                    print(f"  Erreur parsing JSON: {e}")
    else:
        print("QUOTE: Aucun fichier trouvé")

if __name__ == "__main__":
    # Analyser le 29 septembre
    print("=== ANALYSE 29 SEPTEMBRE ===")
    base_29 = Path(r'D:\MIA_IA_system\DATA_SIERRA_CHART\DATA_2025\SEPTEMBRE\20250929')
    for chart in ['CHART_3', 'CHART_9']:
        analyze_prices(base_29, chart)
    
    # Analyser le 30 septembre
    print("\n=== ANALYSE 30 SEPTEMBRE ===")
    base_30 = Path(r'D:\MIA_IA_system\DATA_SIERRA_CHART\DATA_2025\SEPTEMBRE\20250930')
    for chart in ['CHART_3', 'CHART_9']:
        analyze_prices(base_30, chart)






