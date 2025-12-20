#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
⚔️ LEADERSHIP ENGINE ES/NQ - MIA_IA_SYSTEM (patched)
- Fenêtres en minutes converties en nombre de barres selon bars_timeframe_minutes
- Protection NaN sur vol_ma
- Clipping anti-outliers
- Persistance en barres (pas seulement minutes)
"""
import sys
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from collections import deque

sys.path.append(str(Path(__file__).parent.parent))
from core.logger import get_logger
logger = get_logger(__name__)

@dataclass
class LeadershipResult:
    leader: Optional[str]
    strength: float
    persisted: bool
    votes: List[str]
    scores: Dict[str, Any]

class LeadershipZMom:
    WINDOWS_MIN = {"1m": 1, "5m": 5, "15m": 15}
    
    def __init__(self, max_history: int = 1000, bars_timeframe_minutes: int = 1):
        self.current_leader: Optional[str] = None
        self.confirm_until: Optional[datetime] = None
        self.cooldown_until: Optional[datetime] = None  # PATCH: anti ping-pong
        self.history = deque(maxlen=max_history)
        self.last_calculation: Optional[datetime] = None
        self.calculation_count: int = 0
        self.tf_min = max(1, int(bars_timeframe_minutes))
        # PATCH: Fenêtres converties en barres selon bars_timeframe_minutes
        self.windows = self._convert_windows_to_bars()
        logger.info(f"⚔️ LeadershipZMom initialisé (TF={self.tf_min}m, fenêtres={self.windows})")
    
    def _convert_windows_to_bars(self) -> Dict[str, int]:
        """Convertit les fenêtres exprimées en minutes -> nombre de barres"""
        def to_bars(minutes: int) -> int:
            minutes = max(int(minutes), 1)
            return max(2, minutes // max(self.tf_min, 1))  # au moins 2 barres
        return {
            "1m": to_bars(self.WINDOWS_MIN["1m"]),
            "5m": to_bars(self.WINDOWS_MIN["5m"]),
            "15m": to_bars(self.WINDOWS_MIN["15m"]),
        }
    
    def apply_config_windows(self, bars_tf_min: int, w1: int, w5: int, w15: int):
        """Convertit les fenêtres exprimées en minutes YAML -> nombre de barres"""
        def to_bars(minutes: int) -> int:
            minutes = max(int(minutes), 1)
            return max(2, minutes // max(bars_tf_min, 1))  # au moins 2 barres
        self.windows = {
            "1m": to_bars(w1),
            "5m": to_bars(w5),
            "15m": to_bars(w15),
        }
        logger.info(f"🔧 Fenêtres configurées: {self.windows} (TF={bars_tf_min}m)")
    
    @staticmethod
    def _safe_std(series: pd.Series) -> float:
        std = series.std()
        if not np.isfinite(std) or std <= 0:
            return 1e-6
        return float(std)
    
    @staticmethod
    def _clip(x: float, lo: float, hi: float) -> float:
        return float(np.clip(x, lo, hi))
    
    def _window_in_bars(self, minutes: int) -> int:
        return max(1, int(round(minutes / self.tf_min)))
    
    def compute_scores(self, df: pd.DataFrame, window_bars: int) -> Dict[str, float]:
        try:
            if len(df) < window_bars:
                return {'momentum': 0.0, 'flow': 0.0, 'efficiency': 0.0, 'total': 0.0}
            
            window_data = df.tail(window_bars)
            
            # 1) Momentum normalisé (retours / vol)
            returns = window_data['close'].pct_change().dropna()
            if returns.empty:
                momentum = 0.0
                ret_sum = 0.0
                vol = 1e-6
            else:
                ret_sum = float(returns.sum())
                vol = self._safe_std(returns)
                momentum = ret_sum / vol
            
            # 2) Volume relatif et order flow
            current_vol = float(window_data['volume'].sum()) if 'volume' in window_data.columns else 0.0
            
            if 'volume' in df.columns:
                # moyenne sur 5x la fenêtre, calculée en tail pour éviter NaN
                span = window_bars * 5
                vol_ma = float(df['volume'].tail(span).mean()) if span <= len(df) else float(df['volume'].mean())
                vol_ma = float(np.nan_to_num(vol_ma, nan=1e-6))
                vol_rel = current_vol / max(vol_ma, 1e-6)
            else:
                vol_rel = 1.0
            
            # clamp vol_rel pour éviter explosions
            vol_rel = self._clip(vol_rel, 0.0, 5.0)
            
            # Imbalance
            if 'buy_volume' in window_data.columns and 'sell_volume' in window_data.columns:
                buy_vol = float(window_data['buy_volume'].sum())
                sell_vol = float(window_data['sell_volume'].sum())
                denom = max(1e-6, buy_vol + sell_vol)
                imbalance = (buy_vol - sell_vol) / denom
            else:
                imbalance = 0.0
            
            imbalance = self._clip(imbalance, -0.99, 0.99)
            flow = vol_rel * (1.0 + imbalance)
            
            # 3) Efficacité = |ret| / vol
            efficiency = abs(ret_sum) / max(vol, 1e-6)
            
            # Clipping doux des composantes (robustesse)
            momentum = self._clip(momentum, -10.0, 10.0)
            efficiency = self._clip(efficiency, 0.0, 10.0)
            flow = self._clip(flow, 0.0, 10.0)
            
            # 4) Score pondéré
            total_score = 0.40 * momentum + 0.35 * flow + 0.25 * efficiency
            
            return {
                'momentum': float(momentum), 'flow': float(flow),
                'efficiency': float(efficiency), 'total': float(total_score)
            }
            
        except Exception as e:
            logger.exception(f"❌ Erreur calcul scores (window_bars={window_bars}): {e}")
            return {'momentum': 0.0, 'flow': 0.0, 'efficiency': 0.0, 'total': 0.0}
    
    def decide_leader(
        self, es_df: pd.DataFrame, nq_df: pd.DataFrame, now_ts: datetime, 
        persistence_bars: int, min_strength: float
    ) -> LeadershipResult:
        """
        Retourne un leader confirmé après hystérésis.
        Pendant la phase de confirmation, leader reste = current_leader (peut être None),
        persisted=False, votes/scores renseignés pour debug.
        """
        try:
            votes: List[str] = []
            es_scores: Dict[str, Dict[str, float]] = {}
            nq_scores: Dict[str, Dict[str, float]] = {}
            
            # Calcul par fenêtres (converties en barres selon config)
            for name, bars in self.windows.items():
                es_score = self.compute_scores(es_df, bars)
                nq_score = self.compute_scores(nq_df, bars)
                es_scores[name] = es_score
                nq_scores[name] = nq_score
                votes.append('ES' if es_score['total'] > nq_score['total'] else 'NQ')
            
            if not votes:
                return LeadershipResult(None, 0.0, False, [], {})
            
            leader_candidate = max(set(votes), key=votes.count)
            strength = votes.count(leader_candidate) / len(votes)  # 0.33/0.66/1.0
            
            # Pas de leader clair
            if strength < float(min_strength):
                self.calculation_count += 1
                self.last_calculation = now_ts
                return LeadershipResult(None, strength, False, votes, {'ES': es_scores, 'NQ': nq_scores})
            
            # Hystérésis + Cooldown anti ping-pong (PATCH)
            persisted = True
            if leader_candidate != self.current_leader:
                # Vérifier cooldown pour éviter flip immédiat après changement
                if self.cooldown_until and now_ts < self.cooldown_until:
                    # En cooldown → ignorer le changement, garder leader actuel
                    persisted = False
                    logger.debug(f"🔧 Cooldown actif jusqu'à {self.cooldown_until} → ignore flip {self.current_leader} → {leader_candidate}")
                elif self.confirm_until is None:
                    # première observation du switch → démarre le compte à rebours
                    self.confirm_until = now_ts + timedelta(minutes=persistence_bars * self.tf_min)
                    persisted = False
                    logger.debug(f"🔧 Switch détecté {self.current_leader} → {leader_candidate}, confirmation jusqu'à {self.confirm_until}")
                elif now_ts >= self.confirm_until:
                    # confirmation acquise → on bascule + active cooldown
                    old_leader = self.current_leader
                    self.current_leader = leader_candidate
                    self.confirm_until = None
                    self.cooldown_until = now_ts + timedelta(minutes=2 * self.tf_min)  # 2 barres de cooldown
                    persisted = True
                    self.history.append({
                        'ts': now_ts.isoformat(), 'leader': self.current_leader,
                        'strength': round(strength, 3), 'votes': votes
                    })
                    logger.debug(f"🔧 Leader confirmé: {old_leader} → {self.current_leader}, cooldown jusqu'à {self.cooldown_until}")
                else:
                    # en attente confirmation
                    persisted = False
            else:
                # leader reste le même → pas de latence, clear cooldown si expiré
                self.confirm_until = None
                if self.cooldown_until and now_ts >= self.cooldown_until:
                    self.cooldown_until = None
                    logger.debug("🔧 Cooldown expiré")
                persisted = True
            
            self.calculation_count += 1
            self.last_calculation = now_ts
            
            return LeadershipResult(
                leader=self.current_leader,  # peut être None si jamais confirmé
                strength=strength, persisted=persisted,
                votes=votes, scores={'ES': es_scores, 'NQ': nq_scores}
            )
            
        except Exception as e:
            logger.exception(f"❌ Erreur décision leader: {e}")
            return LeadershipResult(None, 0.0, False, [], {})
    
    def get_leader_score(self) -> float:
        return 1.0 if self.current_leader == "ES" else (-1.0 if self.current_leader == "NQ" else 0.0)
    
    def get_status(self) -> Dict[str, Any]:
        return {
            'current_leader': self.current_leader,
            'confirm_until': self.confirm_until.isoformat() if self.confirm_until else None,
            'history_count': len(self.history),
            'calculation_count': self.calculation_count,
            'last_calculation': self.last_calculation.isoformat() if self.last_calculation else None
        }
    
    def get_recent_history(self, count: int = 10) -> List[Dict]:
        return list(self.history)[-count:]
    
    def reset(self):
        self.current_leader = None
        self.confirm_until = None
        self.cooldown_until = None  # PATCH: reset cooldown
        self.history.clear()
        self.last_calculation = None
        self.calculation_count = 0
        logger.info("🔄 LeadershipZMom réinitialisé")

# --- Petit test local ---
def test_leadership_engine():
    logger.info("🧮 TEST LEADERSHIP ENGINE")
    logger.info("=" * 50)
    
    dates = pd.date_range('2025-08-22 15:00:00', periods=100, freq='1min')
    
    es_data = pd.DataFrame({
        'close': [6397 + i*0.5 + np.random.normal(0, 0.1) for i in range(100)],
        'volume': [1000 + np.random.normal(0, 100) for _ in range(100)],
        'buy_volume': [600 + np.random.normal(0, 50) for _ in range(100)],
        'sell_volume': [400 + np.random.normal(0, 50) for _ in range(100)]
    }, index=dates)
    
    nq_data = pd.DataFrame({
        'close': [23246 + i*0.2 + np.random.normal(0, 0.2) for i in range(100)],
        'volume': [800 + np.random.normal(0, 80) for _ in range(100)],
        'buy_volume': [450 + np.random.normal(0, 40) for _ in range(100)],
        'sell_volume': [350 + np.random.normal(0, 40) for _ in range(100)]
    }, index=dates)
    
    engine = LeadershipZMom(bars_timeframe_minutes=1)
    
    for i in range(20, 100, 10):
        es_window = es_data.iloc[:i]
        nq_window = nq_data.iloc[:i]
        now_ts = dates[i-1]
        
        result = engine.decide_leader(
            es_window, nq_window, now_ts, 
            persistence_bars=3, min_strength=0.35
        )
        
        logger.info(f"Période {i}:")
        logger.info(f"  🎯 Leader: {result.leader}")
        logger.info(f"  💪 Force: {result.strength:.3f}")
        logger.info(f"  ✅ Persistant: {result.persisted}")
        logger.info(f"  📊 Votes: {result.votes}")
        logger.info("")
    
    status = engine.get_status()
    logger.info("📋 STATUT FINAL:")
    logger.info(f"  🎯 Leader actuel: {status['current_leader']}")
    logger.info(f"  📊 Calculs effectués: {status['calculation_count']}")
    logger.info(f"  📈 Changements enregistrés: {status['history_count']}")
    
    recent = engine.get_recent_history(5)
    if recent:
        logger.info("📜 HISTORIQUE RÉCENT:")
        for entry in recent:
            logger.info(f"  {entry['ts']}: {entry['leader']} (force: {entry['strength']:.3f})")

if __name__ == "__main__":
    test_leadership_engine()
