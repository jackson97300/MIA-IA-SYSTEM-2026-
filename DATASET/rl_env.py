# rl_env.py
# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
import gymnasium as gym
from gymnasium import spaces

LEAK_COLS = {
    "c_fwd","ret_h","hi_win","lo_win",  # colonnes futures
}
def drop_leak_cols(df: pd.DataFrame) -> pd.DataFrame:
    drops = set(LEAK_COLS) | {c for c in df.columns if c.startswith("y_")}
    drops |= {"ts","sym"}
    return df.drop(columns=[c for c in drops if c in df.columns], errors="ignore")

class TradingDatasetEnv(gym.Env):
    """
    Env simple:
      - Obs: features normalisées (float32)
      - Action:
         * discret=True  -> {0: FLAT, 1: LONG, 2: SHORT}
         * discret=False -> position in [-1, +1] (SAC)
      - Reward: PnL/ATR - costs, sans fuite d'info
    """
    metadata = {"render.modes": []}

    def __init__(self, df: pd.DataFrame, scaler=None, discret=True,
                 price_col="c", atr_col="atr",
                 trans_cost=0.0, hold_cost=0.0):
        super().__init__()
        assert price_col in df.columns, f"{price_col} manquant"
        self.df_raw = df.copy()
        self.dfX = drop_leak_cols(self.df_raw)
        self.feature_cols = [c for c in self.dfX.columns if c not in (price_col,)]
        self.price_col = price_col
        self.atr_col = atr_col
        self.discret = discret
        self.trans_cost = float(trans_cost)  # coût par changement de position (en points d'ATR)
        self.hold_cost = float(hold_cost)    # coût par step * |pos|
        # NaN -> 0 (tu as déjà des masques avail_*)
        self.dfX[self.feature_cols] = self.dfX[self.feature_cols].fillna(0.0)
        # scaler optionnel (StandardScaler etc.) déjà fit avant
        self.scaler = scaler
        if self.scaler is not None:
            self.dfX[self.feature_cols] = self.scaler.transform(self.dfX[self.feature_cols])

        self.X = self.dfX[self.feature_cols].astype("float32").values
        self.p = self.df_raw[self.price_col].astype("float32").values
        self.atr = self.df_raw[self.atr_col].replace(0, np.nan).astype("float32").values
        self.atr = np.nan_to_num(self.atr, nan=np.nanmedian(self.atr) if np.isfinite(np.nanmedian(self.atr)) else 1.0)
        self.n = len(self.df_raw)

        # spaces
        if self.discret:
            self.action_space = spaces.Discrete(3)  # 0 FLAT, 1 LONG, 2 SHORT
        else:
            self.action_space = spaces.Box(low=-1.0, high=1.0, shape=(1,), dtype=np.float32)
        self.observation_space = spaces.Box(low=-10, high=10, shape=(len(self.feature_cols),), dtype=np.float32)

        self.reset(seed=None)

    def _action_to_pos(self, a):
        if self.discret:
            return {0: 0.0, 1: +1.0, 2: -1.0}[int(a)]
        else:
            return float(np.clip(a[0], -1.0, 1.0))

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.t = 0
        self.pos = 0.0
        self._done = False
        return self.X[self.t], {}

    def step(self, action):
        if self._done:
            raise RuntimeError("call reset()")
        # position désirée
        new_pos = self._action_to_pos(action)
        # reward du step basé sur move t->t+1
        if self.t >= self.n - 1:
            self._done = True
            return self.X[self.t], 0.0, True, False, {}

        # variation de prix normalisée par ATR courant (unitless)
        atr = self.atr[self.t] if self.atr[self.t] > 0 else 1.0
        price_ret = (self.p[self.t+1] - self.p[self.t]) / atr

        # coûts
        trans = self.trans_cost * abs(new_pos - self.pos)
        carry = self.hold_cost * abs(self.pos)

        reward = self.pos * price_ret - trans - carry

        # avancer
        self.pos = new_pos
        self.t += 1
        self._done = self.t >= self.n - 1
        return self.X[self.t], float(reward), self._done, False, {}

    def render(self):
        pass


