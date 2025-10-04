# -*- coding: utf-8 -*-
"""
core/mia_data_generator.py — "simulateur de marché unifié"

🎯 Rôle
Générer des flux réalistes mia_unified_YYYYMMDD.jsonl offline pour dev/tests : patterns, VIX regimes, MenthorQ (BL/Gamma/Swing), hot windows, bruits contrôlés.

🔌 Scénarios paramétrables
Régimes : VIX LOW / MID / HIGH (impacte ranges & vitesse).
MQ : near_BL, near_GammaWall, swing_confluence, clear.
Tendance : bullish, bearish, choppy, range_break.
MTF : aligné/désaligné M1 vs M30.
Bruit : variance volume/delta, slippage synthétique.

🧱 Événements émis (exactement nos types)
basedata_m1, vwap_m1, vp_m1, nbcv_m1, m30_ohlc, vwap_m30_current/prev, nbcv_m30, vix, menthorq_gamma, menthorq_blind_spots, menthorq_swing, trades/quotes (light).

📤 Sorties
Un fichier unique mia_unified_YYYYMMDD.jsonl + meta (seed, params).
Option stream (stdout) pour launch_24_7 en mode "replay".

🔗 Interfaces
generate(session_len='90m', regime='MID', mq_scenario='near_BL', trend='choppy', seed=42) -> path
replay(path, speed=1.0) (optionnel, utile en dev)

🧪 Tests (acceptance)
Générer 3 scénarios : near_BL, near_GammaWall, clear → test_menthorq_integration.py doit passer avec NO_TRADE, size réduite, GO respectivement.
Débit stable (≥ 1k lignes/min possible).

📈 Logs attendus
INFO generator: wrote 18,420 lines to mia_unified_20250907.jsonl (regime=MID mq=near_BL)
INFO replay: 1.6k l/min speed=1.0x
"""

import json
import math
import random
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Literal, Union, Tuple
from pathlib import Path

import numpy as np

from core.logger import get_logger

logger = get_logger(__name__)

# === TYPES ===

@dataclass
class GenerationConfig:
    """Configuration de génération de données"""
    session_len: str = '90m'  # '30m', '60m', '90m', '120m'
    regime: Literal['LOW', 'MID', 'HIGH'] = 'MID'
    mq_scenario: Literal['near_BL', 'near_GammaWall', 'swing_confluence', 'clear'] = 'near_BL'
    trend: Literal['bullish', 'bearish', 'choppy', 'range_break'] = 'choppy'
    mtf_aligned: bool = True  # M1 vs M30 aligné
    noise_level: float = 0.1  # 0.0 = parfait, 1.0 = très bruité
    seed: int = 42

@dataclass
class GenerationMeta:
    """Métadonnées de génération"""
    generated_at: str
    config: GenerationConfig
    total_lines: int
    duration_seconds: float
    symbols: List[str]
    vix_range: Tuple[float, float]
    price_range: Dict[str, Tuple[float, float]]

# === GÉNÉRATEUR PRINCIPAL ===

class MIAUnifiedDataGenerator:
    """Générateur de données MIA unifié pour tests et développement"""
    
    def __init__(self, seed: int = 42):
        self.seed = seed
        self.rng = random.Random(seed)
        self.np_rng = np.random.default_rng(seed)
        
        # Configuration par défaut
        self.symbols = ['ESU25_FUT_CME']
        self.tick_size = 0.25
        self.base_price = 5295.0
        
        # Paramètres VIX par régime
        self.vix_params = {
            'LOW': {'base': 12.0, 'vol': 0.5, 'range': (10.0, 16.0)},
            'MID': {'base': 18.0, 'vol': 1.0, 'range': (15.0, 25.0)},
            'HIGH': {'base': 28.0, 'vol': 2.0, 'range': (22.0, 40.0)}
        }
        
        # Paramètres de tendance
        self.trend_params = {
            'bullish': {'drift': 0.0002, 'vol_mult': 0.8},
            'bearish': {'drift': -0.0002, 'vol_mult': 0.8},
            'choppy': {'drift': 0.0, 'vol_mult': 0.6},
            'range_break': {'drift': 0.0005, 'vol_mult': 1.2}
        }

    def generate(self, config: GenerationConfig) -> str:
        """
        Génère un fichier mia_unified_YYYYMMDD.jsonl
        
        Returns:
            str: Chemin du fichier généré
        """
        start_time = time.time()
        logger.info(f"Génération démarrée: {config}")
        
        # Calcul de la durée
        duration_minutes = self._parse_duration(config.session_len)
        end_time = datetime.now(timezone.utc) + timedelta(minutes=duration_minutes)
        
        # Initialisation des séries temporelles
        vix_series = self._generate_vix_series(config, duration_minutes)
        price_series = self._generate_price_series(config, duration_minutes)
        
        # Génération des événements
        events = []
        events.extend(self._generate_menthorq_events(config, vix_series, price_series))
        events.extend(self._generate_market_data_events(config, price_series))
        events.extend(self._generate_vix_events(config, vix_series))
        
        # Tri par timestamp
        events.sort(key=lambda x: x['ts'])
        
        # Écriture du fichier
        output_path = self._write_unified_file(events, config)
        
        # Métadonnées
        duration_seconds = time.time() - start_time
        meta = GenerationMeta(
            generated_at=datetime.now(timezone.utc).isoformat(),
            config=config,
            total_lines=len(events),
            duration_seconds=duration_seconds,
            symbols=self.symbols,
            vix_range=(min(vix_series), max(vix_series)),
            price_range={sym: (min(price_series), max(price_series)) for sym in self.symbols}
        )
        
        # Écriture des métadonnées
        self._write_meta_file(output_path, meta)
        
        logger.info(f"Génération terminée: {len(events)} lignes en {duration_seconds:.1f}s -> {output_path}")
        return str(output_path)

    def replay(self, file_path: str, speed: float = 1.0) -> None:
        """
        Replay un fichier généré en streaming
        
        Args:
            file_path: Chemin du fichier à rejouer
            speed: Multiplicateur de vitesse (1.0 = temps réel)
        """
        logger.info(f"Replay démarré: {file_path} (speed={speed}x)")
        
        start_time = time.time()
        lines_count = 0
        
        with open(file_path, 'r', encoding='utf-8') as f:
            first_line = f.readline()
            if not first_line:
                logger.warning("Fichier vide")
                return
                
            # Premier timestamp
            first_event = json.loads(first_line)
            first_ts = datetime.fromisoformat(first_event['ts'].replace('Z', '+00:00'))
            
            # Replay
            f.seek(0)
            for line in f:
                if not line.strip():
                    continue
                    
                event = json.loads(line)
                event_ts = datetime.fromisoformat(event['ts'].replace('Z', '+00:00'))
                
                # Calcul du délai
                delay = (event_ts - first_ts).total_seconds() / speed
                elapsed = time.time() - start_time
                
                if delay > elapsed:
                    time.sleep(delay - elapsed)
                
                # Émission de l'événement
                print(json.dumps(event, ensure_ascii=False))
                lines_count += 1
                
                # Log de progression
                if lines_count % 1000 == 0:
                    rate = lines_count / (time.time() - start_time) * 60
                    logger.info(f"Replay: {lines_count} lignes, {rate:.1f} l/min")
        
        total_time = time.time() - start_time
        rate = lines_count / total_time * 60
        logger.info(f"Replay terminé: {lines_count} lignes en {total_time:.1f}s ({rate:.1f} l/min)")

    # === MÉTHODES PRIVÉES ===

    def _parse_duration(self, duration_str: str) -> int:
        """Parse une durée comme '90m' en minutes"""
        if duration_str.endswith('m'):
            return int(duration_str[:-1])
        elif duration_str.endswith('h'):
            return int(duration_str[:-1]) * 60
        else:
            return int(duration_str)

    def _generate_vix_series(self, config: GenerationConfig, duration_minutes: int) -> List[float]:
        """Génère une série VIX réaliste selon le régime"""
        vix_config = self.vix_params[config.regime]
        n_points = duration_minutes * 2  # Point toutes les 30s
        
        # Marche aléatoire avec retour à la moyenne
        vix_series = [vix_config['base']]
        for i in range(1, n_points):
            # Retour à la moyenne + bruit
            mean_reversion = (vix_config['base'] - vix_series[-1]) * 0.01
            noise = self.np_rng.normal(0, vix_config['vol'])
            new_vix = vix_series[-1] + mean_reversion + noise
            
            # Contraintes
            new_vix = max(vix_config['range'][0], min(vix_config['range'][1], new_vix))
            vix_series.append(new_vix)
        
        return vix_series

    def _generate_price_series(self, config: GenerationConfig, duration_minutes: int) -> List[float]:
        """Génère une série de prix réaliste selon la tendance"""
        trend_config = self.trend_params[config.trend]
        vix_config = self.vix_params[config.regime]
        
        n_points = duration_minutes * 4  # Point toutes les 15s
        
        # Volatilité basée sur VIX
        base_vol = 0.3 * (vix_config['base'] / 20.0) * trend_config['vol_mult']
        
        # Génération du prix
        price_series = [self.base_price]
        for i in range(1, n_points):
            # Drift + bruit
            drift = trend_config['drift'] * self.base_price
            noise = self.np_rng.normal(0, base_vol)
            new_price = price_series[-1] + drift + noise
            
            # Arrondi au tick
            new_price = round(new_price / self.tick_size) * self.tick_size
            price_series.append(new_price)
        
        return price_series

    def _generate_menthorq_events(self, config: GenerationConfig, vix_series: List[float], price_series: List[float]) -> List[Dict]:
        """Génère les événements MenthorQ selon le scénario"""
        events = []
        base_time = datetime.now(timezone.utc)
        
        # Génération des niveaux selon le scénario
        if config.mq_scenario == 'near_BL':
            # Proche d'un Blind Level
            bl_price = price_series[len(price_series)//2] + self.tick_size * 2
            events.extend(self._generate_blind_spots_events(base_time, bl_price, len(price_series)))
            
        elif config.mq_scenario == 'near_GammaWall':
            # Proche d'un Gamma Wall
            gw_price = price_series[len(price_series)//2] - self.tick_size * 3
            events.extend(self._generate_gamma_levels_events(base_time, gw_price, len(price_series)))
            
        elif config.mq_scenario == 'swing_confluence':
            # Confluence de niveaux swing
            events.extend(self._generate_swing_levels_events(base_time, price_series))
            
        elif config.mq_scenario == 'clear':
            # Pas de niveaux significatifs
            pass
        
        return events

    def _generate_blind_spots_events(self, base_time: datetime, bl_price: float, n_points: int) -> List[Dict]:
        """Génère des événements Blind Spots"""
        events = []
        for i in range(0, n_points, 10):  # Toutes les 10 itérations
            ts = base_time + timedelta(seconds=i*15)
            events.append({
                "type": "menthorq_blind_spots",
                "graph": 10,
                "sym": "ESU25_FUT_CME",
                "study_id": 2,
                "sg": 1,
                "label": "BL 1",
                "price": bl_price + self.np_rng.normal(0, self.tick_size),
                "ts": ts.isoformat(),
                "ingest_ts": (ts + timedelta(milliseconds=100)).isoformat()
            })
        return events

    def _generate_gamma_levels_events(self, base_time: datetime, gw_price: float, n_points: int) -> List[Dict]:
        """Génère des événements Gamma Levels"""
        events = []
        for i in range(0, n_points, 8):  # Toutes les 8 itérations
            ts = base_time + timedelta(seconds=i*15)
            events.append({
                "type": "menthorq_gamma_levels",
                "graph": 10,
                "sym": "ESU25_FUT_CME",
                "study_id": 1,
                "sg": 9,
                "label": "Gamma Wall 0DTE",
                "price": gw_price + self.np_rng.normal(0, self.tick_size),
                "ts": ts.isoformat(),
                "ingest_ts": (ts + timedelta(milliseconds=100)).isoformat()
            })
        return events

    def _generate_swing_levels_events(self, base_time: datetime, price_series: List[float]) -> List[Dict]:
        """Génère des événements Swing Levels"""
        events = []
        # Niveaux de support/résistance basés sur les prix
        support = min(price_series) + (max(price_series) - min(price_series)) * 0.2
        resistance = min(price_series) + (max(price_series) - min(price_series)) * 0.8
        
        for i in range(0, len(price_series), 12):  # Toutes les 12 itérations
            ts = base_time + timedelta(seconds=i*15)
            events.append({
                "type": "menthorq_swing_levels",
                "graph": 10,
                "sym": "ESU25_FUT_CME",
                "study_id": 3,
                "sg": 1,
                "label": "SG1",
                "price": support if i % 24 < 12 else resistance,
                "ts": ts.isoformat(),
                "ingest_ts": (ts + timedelta(milliseconds=100)).isoformat()
            })
        return events

    def _generate_market_data_events(self, config: GenerationConfig, price_series: List[float]) -> List[Dict]:
        """Génère les événements de données de marché"""
        events = []
        base_time = datetime.now(timezone.utc)
        
        for i, price in enumerate(price_series):
            ts = base_time + timedelta(seconds=i*15)
            
            # Basedata M1
            if i % 4 == 0:  # Toutes les minutes
                events.append(self._generate_basedata_event(ts, price, i))
            
            # VWAP M1
            if i % 4 == 0:
                events.append(self._generate_vwap_event(ts, price, i))
            
            # Volume Profile M1
            if i % 4 == 0:
                events.append(self._generate_vp_event(ts, price, i))
            
            # NBCV M1
            if i % 4 == 0:
                events.append(self._generate_nbcv_event(ts, price, i))
            
            # M30 OHLC (toutes les 30 minutes)
            if i % 120 == 0:
                events.append(self._generate_m30_ohlc_event(ts, price, i))
            
            # VWAP M30
            if i % 120 == 0:
                events.append(self._generate_vwap_m30_event(ts, price, i))
            
            # NBCV M30
            if i % 120 == 0:
                events.append(self._generate_nbcv_m30_event(ts, price, i))
            
            # Trades et Quotes (légers)
            if i % 2 == 0:  # Toutes les 30s
                events.append(self._generate_quote_event(ts, price))
                events.append(self._generate_trade_event(ts, price))

        return events

    def _generate_basedata_event(self, ts: datetime, price: float, index: int) -> Dict:
        """Génère un événement basedata M1"""
        spread = self.tick_size * self.rng.randint(1, 3)
        volume = self.rng.randint(800, 2000)
        bidvol = volume // 2 + self.rng.randint(-100, 100)
        askvol = volume - bidvol
        
        return {
            "type": "basedata",
            "graph": 3,
            "sym": "ESU25_FUT_CME",
            "o": price - self.tick_size * self.rng.randint(0, 2),
            "h": price + self.tick_size * self.rng.randint(0, 3),
            "l": price - self.tick_size * self.rng.randint(0, 3),
            "c": price,
            "v": volume,
            "bidvol": max(0, bidvol),
            "askvol": max(0, askvol),
            "oi": 0,
            "ts": ts.isoformat(),
            "ingest_ts": (ts + timedelta(milliseconds=100)).isoformat()
        }

    def _generate_vwap_event(self, ts: datetime, price: float, index: int) -> Dict:
        """Génère un événement VWAP M1"""
        vwap = price + self.np_rng.normal(0, self.tick_size * 0.5)
        sd = self.tick_size * self.rng.uniform(1.0, 2.0)
        
        return {
            "type": "vwap",
            "graph": 3,
            "sym": "ESU25_FUT_CME",
            "v": vwap,
            "up1": vwap + sd,
            "dn1": vwap - sd,
            "up2": vwap + 2*sd,
            "dn2": vwap - 2*sd,
            "src": "study",
            "ts": ts.isoformat(),
            "ingest_ts": (ts + timedelta(milliseconds=100)).isoformat()
        }

    def _generate_vp_event(self, ts: datetime, price: float, index: int) -> Dict:
        """Génère un événement Volume Profile M1"""
        return {
            "type": "vva",
            "graph": 3,
            "sym": "ESU25_FUT_CME",
            "vah": price + self.tick_size * 2,
            "val": price - self.tick_size * 2,
            "vpoc": price,
            "pvah": 4505.0,
        "pval": 4495.0,
        "ppoc": 4500.0,
            "id_curr": ts.strftime("%Y%m%d-RTH"),
            "id_prev": (ts - timedelta(days=1)).strftime("%Y%m%d-RTH"),
            "ts": ts.isoformat(),
            "ingest_ts": (ts + timedelta(milliseconds=100)).isoformat()
        }

    def _generate_nbcv_event(self, ts: datetime, price: float, index: int) -> Dict:
        """Génère un événement NBCV M1"""
        return {
            "type": "vap",
            "graph": 3,
            "sym": "ESU25_FUT_CME",
            "bar": 12345 + index,
            "k": 0,
            "price": price,
            "vol": self.rng.randint(100, 500),
            "ts": ts.isoformat(),
            "ingest_ts": (ts + timedelta(milliseconds=100)).isoformat()
        }

    def _generate_m30_ohlc_event(self, ts: datetime, price: float, index: int) -> Dict:
        """Génère un événement M30 OHLC"""
        return {
            "type": "m30_ohlc",
            "graph": 30,
            "sym": "ESU25_FUT_CME",
            "o": price - self.tick_size * 5,
            "h": price + self.tick_size * 8,
            "l": price - self.tick_size * 8,
            "c": price,
            "v": self.rng.randint(5000, 15000),
            "ts": ts.isoformat(),
            "ingest_ts": (ts + timedelta(milliseconds=100)).isoformat()
        }

    def _generate_vwap_m30_event(self, ts: datetime, price: float, index: int) -> Dict:
        """Génère un événement VWAP M30"""
        vwap = price + self.np_rng.normal(0, self.tick_size)
        return {
            "type": "vwap_m30_current",
            "graph": 30,
            "sym": "ESU25_FUT_CME",
            "v": vwap,
            "ts": ts.isoformat(),
            "ingest_ts": (ts + timedelta(milliseconds=100)).isoformat()
        }

    def _generate_nbcv_m30_event(self, ts: datetime, price: float, index: int) -> Dict:
        """Génère un événement NBCV M30"""
        return {
            "type": "nbcv_m30",
            "graph": 30,
            "sym": "ESU25_FUT_CME",
            "bar": 54321 + index,
            "k": 0,
            "price": price,
            "vol": self.rng.randint(1000, 3000),
            "ts": ts.isoformat(),
            "ingest_ts": (ts + timedelta(milliseconds=100)).isoformat()
        }

    def _generate_quote_event(self, ts: datetime, price: float) -> Dict:
        """Génère un événement quote"""
        spread = self.tick_size * self.rng.randint(1, 2)
        return {
            "type": "quote",
            "graph": 3,
            "sym": "ESU25_FUT_CME",
            "kind": "BIDASK",
            "bid": price - spread/2,
            "ask": price + spread/2,
            "bq": self.rng.randint(20, 50),
            "aq": self.rng.randint(20, 50),
            "seq": 1000000 + self.rng.randint(0, 10000),
            "ts": ts.isoformat(),
            "ingest_ts": (ts + timedelta(milliseconds=100)).isoformat()
        }

    def _generate_trade_event(self, ts: datetime, price: float) -> Dict:
        """Génère un événement trade"""
        return {
            "type": "trade",
            "graph": 3,
            "sym": "ESU25_FUT_CME",
            "px": price,
            "vol": self.rng.randint(1, 20),
            "seq": 2000000 + self.rng.randint(0, 10000),
            "ts": ts.isoformat(),
            "ingest_ts": (ts + timedelta(milliseconds=100)).isoformat()
        }

    def _generate_vix_events(self, config: GenerationConfig, vix_series: List[float]) -> List[Dict]:
        """Génère les événements VIX"""
        events = []
        base_time = datetime.now(timezone.utc)
        
        for i, vix_value in enumerate(vix_series):
            if i % 2 == 0:  # Toutes les 30s
                ts = base_time + timedelta(seconds=i*30)
                events.append({
                    "type": "vix",
                    "graph": 8,
                    "sym": "^VIX",
                    "last": round(vix_value, 1),
                    "mode": "study",
                    "ts": ts.isoformat(),
                    "ingest_ts": (ts + timedelta(milliseconds=100)).isoformat()
                })
        
        return events

    def _write_unified_file(self, events: List[Dict], config: GenerationConfig) -> Path:
        """Écrit le fichier mia_unified_YYYYMMDD.jsonl"""
        today = datetime.now().strftime("%Y%m%d")
        filename = f"mia_unified_{today}.jsonl"
        output_path = Path(filename)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for event in events:
                f.write(json.dumps(event, ensure_ascii=False) + '\n')
        
        return output_path

    def _write_meta_file(self, output_path: Path, meta: GenerationMeta) -> None:
        """Écrit le fichier de métadonnées"""
        meta_path = output_path.with_suffix('.meta.json')
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(asdict(meta), f, indent=2, ensure_ascii=False)

# === INTERFACE PUBLIQUE ===

def generate(session_len: str = '90m', 
             regime: str = 'MID', 
             mq_scenario: str = 'near_BL', 
             trend: str = 'choppy', 
             seed: int = 42) -> str:
    """
    Interface publique pour générer des données MIA unifiées
    
    Args:
        session_len: Durée de la session ('30m', '60m', '90m', '120m')
        regime: Régime VIX ('LOW', 'MID', 'HIGH')
        mq_scenario: Scénario MenthorQ ('near_BL', 'near_GammaWall', 'swing_confluence', 'clear')
        trend: Tendance ('bullish', 'bearish', 'choppy', 'range_break')
        seed: Graine aléatoire
        
    Returns:
        str: Chemin du fichier généré
    """
    config = GenerationConfig(
        session_len=session_len,
        regime=regime,
        mq_scenario=mq_scenario,
        trend=trend,
        seed=seed
    )
    
    generator = MIAUnifiedDataGenerator(seed=seed)
    return generator.generate(config)

def replay(file_path: str, speed: float = 1.0) -> None:
    """
    Interface publique pour rejouer un fichier généré
    
    Args:
        file_path: Chemin du fichier à rejouer
        speed: Multiplicateur de vitesse
    """
    generator = MIAUnifiedDataGenerator()
    generator.replay(file_path, speed)

# === EXEMPLE D'UTILISATION ===

if __name__ == "__main__":
    # Exemple de génération
    print("Génération d'un scénario near_BL...")
    file_path = generate(
        session_len='90m',
        regime='MID',
        mq_scenario='near_BL',
        trend='choppy',
        seed=42
    )
    print(f"Fichier généré: {file_path}")
    
    # Exemple de replay
    print("\nReplay du fichier...")
    replay(file_path, speed=2.0)

