# train_sac.py
# -*- coding: utf-8 -*-
import os, joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from stable_baselines3 import SAC
from stable_baselines3.common.vec_env import DummyVecEnv

from rl_env import TradingDatasetEnv

DATASET = r"D:\MIA_IA_system\DATASET\dataset_20251002_20251003.parquet"
OUTMODELS = r"D:\MIA_IA_system\DATASET\models"

os.makedirs(OUTMODELS, exist_ok=True)

def load_df(dataset_path):
    df = pd.read_parquet(dataset_path)
    df = df.sort_values("ts").reset_index(drop=True)
    df = df.dropna(subset=["c","atr"]).copy()
    return df

def make_split(df, pivot_q=0.7):
    pivot_time = df["ts"].quantile(pivot_q)
    train = df[df["ts"] < pivot_time].copy()
    test  = df[df["ts"] >= pivot_time].copy()
    return train, test, pivot_time

def fit_scaler(train_df):
    from rl_env import drop_leak_cols
    X = drop_leak_cols(train_df)
    X = X.drop(columns=[c for c in ["c"] if c in X.columns], errors="ignore")
    X = X.fillna(0.0).astype("float32")
    scaler = StandardScaler(with_mean=True, with_std=True)
    scaler.fit(X.values)
    return scaler

def main():
    df = load_df(DATASET)
    train_df, test_df, pivot_time = make_split(df, 0.7)
    scaler = fit_scaler(train_df)
    joblib.dump(scaler, os.path.join(OUTMODELS, "scaler_sac.pkl"))

    def make_env_train():
        return TradingDatasetEnv(train_df, scaler=scaler, discret=False,
                                 trans_cost=0.01, hold_cost=0.000)
    def make_env_test():
        return TradingDatasetEnv(test_df, scaler=scaler, discret=False,
                                 trans_cost=0.01, hold_cost=0.000)

    env = DummyVecEnv([make_env_train])
    model = SAC("MlpPolicy", env,
                learning_rate=3e-4, buffer_size=100_000,
                batch_size=256, tau=0.005, gamma=0.99,
                train_freq=64, gradient_steps=64, learning_starts=1000,
                ent_coef="auto", verbose=1)
    model.learn(total_timesteps=50_000)

    model_path = os.path.join(OUTMODELS, "sac_continuous.zip")
    model.save(model_path)
    print("Saved:", model_path)

    # quick eval
    test_env = make_env_test()
    obs, _ = test_env.reset()
    done = False
    ep_rew = 0.0
    while not done:
        action, _ = model.predict(obs, deterministic=True)
        obs, r, done, _, _ = test_env.step(action)
        ep_rew += r
    print("Test episode reward (unitless):", ep_rew)

if __name__ == "__main__":
    main()


