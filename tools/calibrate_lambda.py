import json
import math
import numpy as np
from pathlib import Path
from typing import List, Dict


class LambdaCalibrator:
    def __init__(self):
        self.tick_sizes = {'ES': 0.25, 'NQ': 0.25}
        self.results: Dict[str, Dict] = {}

    def load_unified_data(self, file_path: str) -> List[Dict]:
        data: List[Dict] = []
        p = Path(file_path)
        if not p.exists():
            return data
        with p.open('r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data.append(json.loads(line))
                except Exception:
                    continue
        return data

    def calibrate_gamma_lambda(self, data: List[Dict], symbol: str) -> float:
        gamma_analysis = []
        tick = self.tick_sizes.get(symbol, 0.25)
        for i in range(len(data) - 1):
            curr = data[i]
            nxt = data[i + 1]
            gamma_max = curr.get('gamma_max', 0) or curr.get('gex_max', 0)
            current_price = curr.get('c') or curr.get('price') or curr.get('last') or 0
            next_price = nxt.get('c') or nxt.get('price') or nxt.get('last') or 0
            if gamma_max and current_price and next_price:
                distance_ticks = abs(current_price - gamma_max) / tick
                price_move = abs(next_price - current_price) / tick
                gamma_analysis.append({'distance': distance_ticks, 'movement': price_move})

        if len(gamma_analysis) < 50:
            return 4.0

        best_lambda = 4.0
        best_corr = 0.0
        for lam in [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 12.0, 15.0]:
            scores = [math.exp(-d['distance'] / lam) for d in gamma_analysis]
            moves = [d['movement'] for d in gamma_analysis]
            corr = np.corrcoef(scores, moves)[0, 1]
            if not np.isnan(corr) and abs(corr) > abs(best_corr):
                best_lambda, best_corr = lam, corr
        print(f"🎯 {symbol} Gamma: λ={best_lambda:.1f} (corrélation={best_corr:.3f}, échantillons={len(gamma_analysis)})")
        return best_lambda

    def calibrate_blind_spots_lambda(self, data: List[Dict], symbol: str) -> float:
        blind_analysis = []
        tick = self.tick_sizes.get(symbol, 0.25)
        for i in range(len(data) - 1):
            curr = data[i]
            nxt = data[i + 1]
            blind_spot = curr.get('blind_spot_1') or curr.get('liquidity_gap') or 0
            current_price = curr.get('c') or curr.get('price') or curr.get('last') or 0
            next_price = nxt.get('c') or nxt.get('price') or nxt.get('last') or 0
            if blind_spot and current_price and next_price:
                distance_ticks = abs(current_price - blind_spot) / tick
                volatility = abs(next_price - current_price) / tick
                blind_analysis.append({'distance': distance_ticks, 'volatility': volatility})

        if len(blind_analysis) < 50:
            return 3.5

        best_lambda = 3.5
        best_corr = 0.0
        for lam in [1.0, 2.0, 3.0, 3.5, 4.0, 5.0, 6.0, 8.0, 10.0]:
            scores = [math.exp(-d['distance'] / lam) for d in blind_analysis]
            vols = [d['volatility'] for d in blind_analysis]
            corr = np.corrcoef(scores, vols)[0, 1]
            if not np.isnan(corr) and abs(corr) > abs(best_corr):
                best_lambda, best_corr = lam, corr
        print(f"🎯 {symbol} Blind Spots: λ={best_lambda:.1f} (corrélation={best_corr:.3f}, échantillons={len(blind_analysis)})")
        return best_lambda

    def run_calibration(self) -> Dict[str, float]:
        print("🚀 CALIBRATION DES PARAMÈTRES λ")
        print("=" * 50)
        files_to_analyze = [
            # ES / CHART_3
            ("DATA_SIERRA_CHART/DATA_2025/SEPTEMBRE/20250929/CHART_3/chart_3_unified_20250929.jsonl", "ES"),
            ("DATA_SIERRA_CHART/DATA_2025/SEPTEMBRE/20250930/CHART_3/chart_3_unified_20250930.jsonl", "ES"),
            ("DATA_SIERRA_CHART/DATA_2025/OCTOBRE/20251001/CHART_3/chart_3_unified_20251001.jsonl", "ES"),
            # NQ / CHART_9
            ("DATA_SIERRA_CHART/DATA_2025/SEPTEMBRE/20250929/CHART_9/chart_9_unified_20250929.jsonl", "NQ"),
            ("DATA_SIERRA_CHART/DATA_2025/SEPTEMBRE/20250930/CHART_9/chart_9_unified_20250930.jsonl", "NQ"),
            ("DATA_SIERRA_CHART/DATA_2025/OCTOBRE/20251001/CHART_9/chart_9_unified_20251001.jsonl", "NQ"),
        ]

        results: Dict[str, Dict] = {}
        for fp, sym in files_to_analyze:
            if Path(fp).exists():
                print(f"\n📊 Analyse de {fp}")
                data = self.load_unified_data(fp)
                print(f"   📈 {len(data)} barres chargées")
                lg = self.calibrate_gamma_lambda(data, sym)
                lb = self.calibrate_blind_spots_lambda(data, sym)
                results[sym] = {"gamma": lg, "blind": lb, "samples": len(data)}
            else:
                print(f"❌ Fichier non trouvé: {fp}")

        print("\n🎯 RÉSULTATS DE CALIBRATION")
        print("=" * 50)
        final_config: Dict[str, float] = {}
        for sym, res in results.items():
            print(f"📊 {sym}:")
            print(f"   λ_gamma: {res['gamma']:.1f}")
            print(f"   λ_blind: {res['blind']:.1f}")
            print(f"   Échantillons: {res['samples']}")
            final_config[f"{sym}_gamma"] = res['gamma']
            final_config[f"{sym}_blind"] = res['blind']

        cfg_path = Path('config/lambda_calibrated.json')
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
        with cfg_path.open('w', encoding='utf-8') as f:
            json.dump(final_config, f, indent=2)
        print(f"\n✅ Configuration sauvegardée dans {cfg_path}")
        return final_config


if __name__ == "__main__":
    calibrator = LambdaCalibrator()
    calibrator.run_calibration()


