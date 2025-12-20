#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
⚙️ LEADERSHIP CONFIG - MIA_IA_SYSTEM (patched)
- Unités fenêtres en MINUTES (alignées avec le moteur)
- Chargement YAML typé + filtre clés inconnues
- Écriture atomique
- Validation étendue (cohérences et bornes)
- Adaptateur -> LeadershipConfig (utilisé ailleurs)
"""

import sys
import io
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict, fields
from threading import RLock

# Ajouter le chemin du projet
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from core.logger import get_logger
logger = get_logger(__name__)

# --- Dataclasses ---

@dataclass
class LeadershipCalibration:
    """Calibration persistée (YAML)"""

    # Seuils de base
    corr_min: float = 0.75
    leader_strength_min: float = 0.35
    persistence_bars: int = 3

    # Multiplicateurs de risque
    risk_multiplier_tight_corr: float = 0.5
    risk_multiplier_weak_corr: float = 0.7
    risk_multiplier_high_vol: float = 0.8

    # Options
    allow_half_size_if_neutral: bool = False
    max_latency_ms: int = 50

    # Seuils de régimes
    vol_low_threshold: float = 0.008      # 0.8%
    vol_high_threshold: float = 0.015     # 1.5%
    corr_weak_threshold: float = 0.70
    corr_tight_threshold: float = 0.90
    gamma_near_wall_threshold: float = 0.003
    gamma_expansion_threshold: float = 0.010

    # Pondérations (somme = 1.0)
    momentum_weight: float = 0.40
    flow_weight: float = 0.35
    efficiency_weight: float = 0.25

    # Fenêtres de calcul (⚠️ en MINUTES, aligné moteur)
    window_1m: int = 1
    window_5m: int = 5
    window_15m: int = 15

    # TF en minutes par barre (utilisé par le moteur)
    bars_timeframe_minutes: int = 1

    # Sessions Paris (heures décimales)
    session_open_start: float = 15.5
    session_open_end: float = 17.0
    session_power_start: float = 20.0
    session_power_end: float = 22.0

    # Historique / monitoring
    max_history_size: int = 1000
    log_rotation_size_mb: int = 100
    performance_update_interval_hours: int = 24


# Dataclass runtime consommée ailleurs (MarketStateAnalyzer/Validator/Engine)
@dataclass
class LeadershipConfig:
    corr_min: float = 0.75
    leader_strength_min: float = 0.35
    persistence_bars: int = 3
    risk_multiplier_tight_corr: float = 0.5
    allow_half_size_if_neutral: bool = False
    max_latency_ms: int = 50


class LeadershipConfigManager:
    """Gestionnaire de configuration fiable (YAML atomique + typage)"""

    def __init__(self, config_file: str = "config/leadership_calibration.yaml", auto_load: bool = True):
        self.config_file = Path(config_file)
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self.calibration = LeadershipCalibration()
        self._field_types = {f.name: f.type for f in fields(LeadershipCalibration)}
        self._locked = False  # quand True, on ne recharge plus depuis YAML
        # Charger la configuration
        if auto_load:
            self.load_config()
        logger.info("⚙️ LeadershipConfigManager initialisé")

    # --------- I/O ---------

    def load_config(self):
        """Charge la config depuis YAML, sauf si verrouillée."""
        if getattr(self, "_locked", False):
            logger.info("⛔ Ignoré: reload YAML (calibration verrouillée)")
            return
        # --- corps original conservé en dessous ---
        with self._lock:
            try:
                if self.config_file.exists():
                    with open(self.config_file, "r", encoding="utf-8") as f:
                        data = yaml.safe_load(f) or {}
                    cleaned, unknown = self._clean_and_cast(data)
                    if unknown:
                        logger.warning(f"⚠️ Clés inconnues ignorées dans YAML: {sorted(list(unknown))}")
                    for k, v in cleaned.items():
                        setattr(self.calibration, k, v)
                    logger.info(f"✅ Configuration chargée: {self.config_file}")
                else:
                    self.save_config()  # crée le fichier
                    logger.info(f"📝 Configuration par défaut créée: {self.config_file}")
            except Exception as e:
                logger.exception(f"❌ Erreur chargement configuration: {e}")
                logger.info("🔄 Utilisation configuration par défaut")

    def save_config(self):
        """Sauvegarde atomique du YAML."""
        with self._lock:
            try:
                tmp = self.config_file.with_suffix(".yaml.tmp")
                data = asdict(self.calibration)
                with open(tmp, "w", encoding="utf-8") as f:
                    yaml.dump(data, f, default_flow_style=False, indent=2, allow_unicode=True)
                tmp.replace(self.config_file)
                logger.info(f"💾 Configuration sauvegardée: {self.config_file}")
            except Exception as e:
                logger.exception(f"❌ Erreur sauvegarde configuration: {e}")

    def reload(self):
        """Reload disque -> mémoire (hot-reload)."""
        self.load_config()

    # --------- Helpers ---------

    def _clean_and_cast(self, raw: Dict[str, Any]) -> Tuple[Dict[str, Any], set]:
        """Ne garde que les clés valides + cast vers types dataclass."""
        valid = {}
        unknown = set()
        for k, v in (raw or {}).items():
            if k not in self._field_types:
                unknown.add(k)
                continue
            t = self._field_types[k]
            try:
                # Casting simple; pour bool YAML gère déjà
                if t is int:
                    v = int(v)
                elif t is float:
                    v = float(v)
                elif t is bool:
                    v = bool(v)
                valid[k] = v
            except Exception:
                logger.warning(f"⚠️ Type invalide pour '{k}' ({v}) — valeur ignorée.")
        return valid, unknown

    # --------- API publique ---------

    def update_calibration(self, updates: Dict[str, Any]):
        """Patch paramétrique + persistance."""
        with self._lock:
            try:
                updated = False
                for k, v in (updates or {}).items():
                    if hasattr(self.calibration, k):
                        old = getattr(self.calibration, k)
                        # cast cohérent
                        t = self._field_types.get(k, type(old))
                        try:
                            if t is int: v = int(v)
                            elif t is float: v = float(v)
                            elif t is bool: v = bool(v)
                        except Exception:
                            logger.warning(f"⚠️ Impossible de caster '{k}' -> {t}, MAJ ignorée.")
                            continue
                        if old != v:
                            setattr(self.calibration, k, v)
                            logger.info(f"🔧 {k}: {old} → {v}")
                            updated = True
                if updated:
                    # Valider avant d'écrire
                    if self.validate_config():
                        self.save_config()
                        # <<< NEW: relire depuis YAML pour s'assurer que tout est appliqué/normalisé
                        self.load_config()
                        logger.info("✅ Calibration mise à jour & rechargée")
                    else:
                        logger.error("❌ Mise à jour refusée (validation échouée) — rollback mémoire conseillé.")
                else:
                    logger.info("ℹ️ Aucune mise à jour nécessaire")
            except Exception:
                logger.exception("❌ Erreur mise à jour calibration")

    def get_calibration(self) -> LeadershipCalibration:
        return self.calibration

    # --- AJOUTS ---
    def set_calibration(self, calibration: LeadershipCalibration, lock: bool = False) -> None:
        """Force une calibration runtime (optionnellement verrouillée contre les reload)."""
        self.calibration = calibration
        if lock:
            self._locked = True
        logger.info("🔒 Calibration runtime appliquée" + (" (lock activé)" if lock else ""))

    def get_config_dict(self) -> Dict[str, Any]:
        return asdict(self.calibration)

    def to_leadership_config(self) -> LeadershipConfig:
        """Adaptateur pour les composants qui attendent LeadershipConfig."""
        c = self.calibration
        return LeadershipConfig(
            corr_min=c.corr_min,
            leader_strength_min=c.leader_strength_min,
            persistence_bars=c.persistence_bars,
            risk_multiplier_tight_corr=c.risk_multiplier_tight_corr,
            allow_half_size_if_neutral=c.allow_half_size_if_neutral,
            max_latency_ms=c.max_latency_ms,
        )

    # --------- Validation ---------

    def validate_config(self) -> bool:
        """Validation étendue (cohérences & bornes)."""
        try:
            c = self.calibration

            # Bornes simples
            if not (0.0 <= c.corr_min <= 1.0): raise ValueError("corr_min ∉ [0,1]")
            if not (0.0 <= c.leader_strength_min <= 1.0): raise ValueError("leader_strength_min ∉ [0,1]")
            if c.persistence_bars < 1: raise ValueError("persistence_bars < 1")

            for name in ("risk_multiplier_tight_corr", "risk_multiplier_weak_corr", "risk_multiplier_high_vol"):
                val = getattr(c, name)
                if not (0.0 <= val <= 1.0):
                    raise ValueError(f"{name} ∉ [0,1]")

            # Pondérations
            total = c.momentum_weight + c.flow_weight + c.efficiency_weight
            if abs(total - 1.0) > 1e-3:
                raise ValueError(f"Somme des poids ≠ 1.0 (actuel: {total:.3f})")

            # Cohérences régimes
            if not (0.0 < c.vol_low_threshold < c.vol_high_threshold < 0.25):
                raise ValueError("vol_* thresholds incohérents")
            if not (0.0 <= c.corr_weak_threshold < c.corr_tight_threshold <= 1.0):
                raise ValueError("corr_* thresholds incohérents")
            if not (0.0 < c.gamma_near_wall_threshold < c.gamma_expansion_threshold < 0.05):
                raise ValueError("gamma_* thresholds incohérents")

            # Sessions (heures Paris)
            if not (0.0 <= c.session_open_start < c.session_open_end <= 24.0):
                raise ValueError("session open incohérente")
            if not (0.0 <= c.session_power_start < c.session_power_end <= 24.0):
                raise ValueError("session power incohérente")

            # Fenêtres & TF
            if c.window_1m <= 0 or c.window_5m <= 0 or c.window_15m <= 0:
                raise ValueError("fenêtres minutes doivent être > 0")
            if c.bars_timeframe_minutes <= 0:
                raise ValueError("bars_timeframe_minutes doit être > 0")

            logger.info("✅ Configuration validée")
            return True

        except Exception as e:
            logger.error(f"❌ Erreur validation configuration: {e}")
            return False

    def reset_to_defaults(self):
        with self._lock:
            try:
                self.calibration = LeadershipCalibration()
                self.save_config()
                logger.info("🔄 Configuration réinitialisée aux valeurs par défaut")
            except Exception:
                logger.exception("❌ Erreur réinitialisation")

    def get_optimization_suggestions(self, performance_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Heuristiques d'optimisation basées sur perfs."""
        suggestions: Dict[str, Any] = {}
        try:
            c = self.calibration
            for regime_key, stats in (performance_stats or {}).items():
                winrate = float(stats.get('winrate', 0.5))
                pass_rate = float(stats.get('pass_rate', 0.5))
                # strict
                if winrate < 0.45 and pass_rate > 0.7:
                    suggestions[f"{regime_key}_strict"] = {
                        'action': 'increase_thresholds',
                        'reason': f'Winrate faible ({winrate:.1%}) avec pass rate élevé ({pass_rate:.1%})',
                        'suggestions': [
                            f'Augmenter leader_strength_min → {min(0.45, c.leader_strength_min + 0.05):.3f}',
                            f'Augmenter persistence_bars → {c.persistence_bars + 1}',
                        ]
                    }
                # loose
                if winrate > 0.65 and pass_rate < 0.3:
                    suggestions[f"{regime_key}_loose"] = {
                        'action': 'decrease_thresholds',
                        'reason': f'Winrate élevé ({winrate:.1%}) avec pass rate faible ({pass_rate:.1%})',
                        'suggestions': [
                            f'Diminuer leader_strength_min → {max(0.25, c.leader_strength_min - 0.05):.3f}',
                            f'Diminuer persistence_bars → {max(2, c.persistence_bars - 1)}',
                        ]
                    }
            return suggestions
        except Exception:
            logger.exception("❌ Erreur génération suggestions")
            return {}

def test_leadership_config():
    """Test du gestionnaire de configuration (PATCH: tests enrichis)"""
    logger.info("🧮 TEST LEADERSHIP CONFIG (patched)")
    logger.info("=" * 50)
    
    # Initialiser le gestionnaire
    config_manager = LeadershipConfigManager()
    
    # Afficher la configuration actuelle
    calibration = config_manager.get_calibration()
    logger.info("📊 CONFIGURATION ACTUELLE:")
    logger.info(f"  📈 Corr min: {calibration.corr_min:.2f}")
    logger.info(f"  💪 Leader strength min: {calibration.leader_strength_min:.2f}")
    logger.info(f"  ⏱️ Persistence bars: {calibration.persistence_bars}")
    logger.info(f"  🎯 Risk multiplier tight corr: {calibration.risk_multiplier_tight_corr:.1f}")
    logger.info(f"  📊 Pondérations: M={calibration.momentum_weight:.2f}, F={calibration.flow_weight:.2f}, E={calibration.efficiency_weight:.2f}")
    logger.info(f"  ⏰ Fenêtres (minutes): 1m={calibration.window_1m}, 5m={calibration.window_5m}, 15m={calibration.window_15m}")
    
    # Valider la configuration
    is_valid = config_manager.validate_config()
    logger.info(f"✅ Configuration valide: {is_valid}")
    
    # Test adaptateur LeadershipConfig
    runtime_config = config_manager.to_leadership_config()
    logger.info(f"🔄 Adaptateur LeadershipConfig: corr_min={runtime_config.corr_min}, persistence_bars={runtime_config.persistence_bars}")
    
    # Test de mise à jour
    updates = {
        'leader_strength_min': 0.40,
        'persistence_bars': 4
    }
    
    logger.info("\n🔧 TEST MISE À JOUR:")
    config_manager.update_calibration(updates)
    
    # Afficher la nouvelle configuration
    new_calibration = config_manager.get_calibration()
    logger.info(f"  💪 Nouveau leader strength min: {new_calibration.leader_strength_min:.2f}")
    logger.info(f"  ⏱️ Nouveau persistence bars: {new_calibration.persistence_bars}")
    
    # Test suggestions d'optimisation
    performance_stats = {
        ('normal', 'normal', 'open', 'neutral'): {
            'winrate': 0.42,
            'pass_rate': 0.75,
            'reject_rate': 0.25
        },
        ('high', 'tight', 'power', 'near_wall'): {
            'winrate': 0.68,
            'pass_rate': 0.25,
            'reject_rate': 0.75
        }
    }
    
    suggestions = config_manager.get_optimization_suggestions(performance_stats)
    
    logger.info("\n💡 SUGGESTIONS D'OPTIMISATION:")
    for key, suggestion in suggestions.items():
        logger.info(f"  🎯 {key}:")
        logger.info(f"    📝 Raison: {suggestion['reason']}")
        for s in suggestion['suggestions']:
            logger.info(f"    💡 {s}")

if __name__ == "__main__":
    test_leadership_config()
