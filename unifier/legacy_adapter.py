#!/usr/bin/env python3
"""
LEGACY ADAPTER - Mapper les snapshots legacy vers le format Elite
================================================================

Adapter layer pour mapper les snapshots "legacy" vers le format requis
par MenthorQ Elite et Battle Navale Elite.

Version: 1.0.0
Date: Janvier 2025
"""

import sys
import os
from pathlib import Path
import glob
import json
from typing import Dict, Any, Optional, List, Tuple
# from datetime import datetime  # ✅ Supprimé - non utilisé
import time

# Ajouter le répertoire racine au path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# import os  # ✅ Supprimé - déjà importé plus haut
import logging
from core.logger import get_logger

logger = get_logger(__name__)

# ✅ Logging dynamique avec variable d'environnement
def _setup_dynamic_logging():
    """Configure le niveau de logging dynamiquement"""
    log_level = os.environ.get("LEGACY_ADAPTER_LOG", "INFO")
    try:
        logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        logger.debug(f"🔧 Logging configuré: niveau={log_level.upper()}")
    except Exception as e:
        logger.warning(f"⚠️ Erreur configuration logging: {e}")

# Appliquer la configuration au chargement du module
_setup_dynamic_logging()

class LegacyAdapter:
    """
    Adapter pour mapper les snapshots legacy vers le format Elite
    
    Fonctionnalités :
    - Mapping des champs legacy vers Elite
    - Validation des données manquantes
    - Fallback robuste
    """
    
    def __init__(self, base_day_dir: str = None, ymd: str = None, chart_id: int = None):
        """Initialisation de l'adapter
        Args:
            base_day_dir: Dossier du jour (…/YYYYMMDD) contenant CHART_3/CHART_9
            ymd: Date YYYYMMDD
            chart_id: 3 ou 9
        """
        self.mapping_stats = {
            "total_mappings": 0,
            "successful_mappings": 0,
            "fallback_used": 0,
            "missing_fields": []
        }
        self.base_day_dir = Path(base_day_dir) if base_day_dir else None
        self.ymd = ymd
        self.chart_id = chart_id
        logger.info("🔄 Legacy Adapter initialisé")

    # ---- Helpers fichiers MenthorQ/VWAP ----
    def _latest(self, pattern: str) -> Optional[Path]:
        files = sorted(glob.glob(pattern))
        return Path(files[-1]) if files else None

    def _read_last_jsonl(self, path: Path) -> Optional[dict]:
        if not path or not path.exists():
            return None
        last = None
        try:
            with open(path, "r", encoding="utf-8") as f:
                for ln in f:
                    try:
                        last = json.loads(ln)
                    except Exception:
                        continue
        except Exception:
            return None
        return last

    def _normalize_px(self, v: float, tick: float) -> float:
        try:
            if not isinstance(v, (int, float)):
                return v
            vv = float(v)
            # Sécuriser le rescale: ne pas /100 pour ES/NQ
            sym_hint = getattr(self, "_last_sym", "")
            if vv > 10000:
                if sym_hint and ("ES" in sym_hint or "NQ" in sym_hint):
                    pass  # NE PAS /100 pour CME index (ES/NQ)
                elif tick and tick < 0.02:
                    vv = vv / 100.0
                    # ✅ FIX: Logger le rescale pour éviter les surprises
                    logger.debug(f"🔄 Prix rescalé /100: {v} → {vv} (tick={tick}, sym={sym_hint})")
            if not tick or tick <= 0:
                return vv
            return round(round(vv / tick) * tick, 10)
        except Exception:
            return float(v) if isinstance(v, (int, float)) else v

    def _merge_menthorq_vwap_from_files(self, snapshot: dict) -> dict:
        """Charge menthorq_gamma + vwap depuis fichiers et fusionne dans snapshot si possible."""
        if not (self.base_day_dir and self.ymd and self.chart_id):
            return snapshot

        sym = snapshot.get("sym") or snapshot.get("symbol")
        self._last_sym = sym  # ✅ Stocker le symbole pour l'EMA multi-symbole
        tick = snapshot.get("qc_context", {}).get("tick_size") or snapshot.get("tick_size") or 0.25
        # garder un hint symbole et tick pour la normalisation
        try:
            self._last_sym = sym or ""
            self._last_tick = tick
        except Exception:
            pass

        chart_dir = self.base_day_dir / f"CHART_{self.chart_id}"
        clean_dir = chart_dir / "CLEAN"

        # MenthorQ
        mq_path = None
        if clean_dir.exists() and sym:
            mq_path = self._latest(str(clean_dir / f"chart_{self.chart_id}_menthorq_gamma_{sym}_{self.ymd}.jsonl"))
        if not mq_path:
            mq_path = self._latest(str(chart_dir / f"chart_{self.chart_id}_menthorq_gamma_{sym}_*.jsonl"))
        rec_mq = self._read_last_jsonl(mq_path) if mq_path else None
        if rec_mq:
            for k, v in rec_mq.items():
                if (
                    (isinstance(k, str) and k.startswith("gex_"))
                    or k in (
                        "hvl", "hvl_0dte",
                        "call_resistance", "call_resistance_0dte",
                        "put_support", "put_support_0dte",
                        "1d_min", "1d_max", "gamma_wall_0dte"
                    )
                ):
                    snapshot[k] = self._normalize_px(v, tick)

        # VWAP — lire le vrai format (study) et l'ancien format
        vwap_path = None
        if clean_dir.exists() and sym:
            vwap_path = self._latest(str(clean_dir / f"chart_{self.chart_id}_vwap_{sym}_{self.ymd}.jsonl"))
        if not vwap_path:
            vwap_path = self._latest(str(chart_dir / f"chart_{self.chart_id}_vwap_{sym}_*.jsonl"))
        
        rec_vwap = self._read_last_jsonl(vwap_path) if vwap_path else None
        if rec_vwap:
            snapshot.setdefault("vwap", {})
            
            # ✅ Nouveau format study (type="vwap", src="study")
            if rec_vwap.get("type") == "vwap" and rec_vwap.get("src") == "study":
                # Valeur principale
                vwap_val = rec_vwap.get("v")
                if vwap_val:
                    snapshot["vwap"]["v"] = self._normalize_px(vwap_val, tick)
                    snapshot["vwap"]["vwap"] = self._normalize_px(vwap_val, tick)  # Compatibilité
                
                # Toutes les bandes de déviation
                for band in ["up1", "dn1", "up2", "dn2", "up3", "dn3"]:
                    if band in rec_vwap:
                        snapshot["vwap"][band] = self._normalize_px(rec_vwap[band], tick)
                
                # Slope et deviation si présents
                if "slope" in rec_vwap:
                    snapshot["vwap"]["slope"] = float(rec_vwap["slope"])
                if "deviation" in rec_vwap:
                    snapshot["vwap"]["deviation"] = float(rec_vwap["deviation"])
                
                # Si seulement la valeur v est disponible, générer les bandes dynamiquement
                if not any(snapshot["vwap"].get(band) for band in ["up1", "dn1", "up2", "dn2", "up3", "dn3"]):
                    # Récupérer VIX et ATR pour la génération dynamique
                    vix_val = snapshot.get("vix", 18.5)
                    atr_points = 0.0
                    try:
                        atr_data = snapshot.get("atr", {})
                        if isinstance(atr_data, dict):
                            atr_points = float(atr_data.get("points", 0.0))
                    except Exception:
                        pass
                    
                    # Déterminer le régime VIX
                    def _vix_regime(v):
                        if v < 13: return "calm"
                        if v < 18: return "normal"
                        if v < 24: return "elevated"
                        return "high"
                    
                    vix_regime = _vix_regime(vix_val)
                    
                    # Générer les bandes
                    dynamic_bands = self._generate_vwap_bands_from_volatility(vwap_val, vix_regime, atr_points, tick)
                    snapshot["vwap"].update(dynamic_bands)
                    
                    logger.debug(f"🔄 Bandes VWAP générées dynamiquement (VIX={vix_val}, ATR={atr_points}): up1={dynamic_bands.get('up1')}, dn1={dynamic_bands.get('dn1')}")
                
                # Contrôle de cohérence des bandes
                self._validate_vwap_bands(snapshot["vwap"], vwap_val)
                
                logger.debug(f"✅ VWAP study chargé: v={vwap_val}, up1={rec_vwap.get('up1')}, dn1={rec_vwap.get('dn1')}")
            
            # ✅ Ancien format (compatibilité)
            else:
                for k in ("vwap", "upper_band", "lower_band", "deviation", "slope"):
                    if k in rec_vwap:
                        snapshot["vwap"][k] = self._normalize_px(rec_vwap[k], tick)
                
                # Mapping des anciens noms vers les nouveaux
                if "upper_band" in snapshot["vwap"]:
                    snapshot["vwap"]["up1"] = snapshot["vwap"]["upper_band"]
                if "lower_band" in snapshot["vwap"]:
                    snapshot["vwap"]["dn1"] = snapshot["vwap"]["lower_band"]
                
                logger.debug(f"✅ VWAP legacy chargé: vwap={rec_vwap.get('vwap')}, upper_band={rec_vwap.get('upper_band')}")
        
        elif vwap_path:
            logger.warning(f"⚠️ Fichier VWAP trouvé mais vide: {vwap_path}")
        else:
            logger.debug(f"🔍 Aucun fichier VWAP trouvé pour chart_{self.chart_id}")

        # VVA (Volume Profile: vpoc/val/vah)
        try:
            vva_path = None
            if clean_dir.exists() and sym:
                vva_path = self._latest(str(clean_dir / f"chart_{self.chart_id}_vva_{sym}_{self.ymd}.jsonl"))
            if not vva_path:
                vva_path = self._latest(str(chart_dir / f"chart_{self.chart_id}_vva_{sym}_*.jsonl"))
            rec_vva = self._read_last_jsonl(vva_path) if vva_path else None
            if rec_vva:
                snapshot.setdefault("vp", {})
                for k_src, k_dst in (("vpoc", "vpoc"), ("val", "val"), ("vah", "vah")):
                    if k_src in rec_vva:
                        try:
                            v = float(rec_vva[k_src])
                        except Exception:
                            continue
                        if v and v != 0.0:
                            snapshot["vp"][k_dst] = self._normalize_px(v, tick)
        except Exception:
            pass

        # Blind spots (lecture facultative, fusion légère)
        try:
            bs_path = None
            if clean_dir.exists() and sym:
                bs_path = self._latest(str(clean_dir / f"chart_{self.chart_id}_menthorq_blind_spots_{sym}_{self.ymd}.jsonl"))
            if not bs_path:
                bs_path = self._latest(str(chart_dir / f"chart_{self.chart_id}_menthorq_blind_spots_{sym}_*.jsonl"))
            rec_bs = self._read_last_jsonl(bs_path) if bs_path else None
            if rec_bs:
                # Conserver l'identifiant si présent
                if "i" in rec_bs and "menthorq_blind_id" not in snapshot:
                    snapshot["menthorq_blind_id"] = rec_bs.get("i")
                # Construire un bloc compact des blind spots valides
                bs_levels = {}
                for k, v in rec_bs.items():
                    if isinstance(k, str) and k.startswith("blind_spot_"):
                        try:
                            val = float(v or 0.0)
                        except Exception:
                            continue
                        # Filtrer les zéros évidents
                        if val == 0.0:
                            continue
                        bs_levels[k] = self._normalize_px(val, tick)
                if bs_levels:
                    snapshot["menthorq_blind_spots"] = bs_levels
        except Exception:
            # Ne jamais casser le flux sur une erreur de lecture des blind spots
            pass

        # PVWAP (VWAP session précédente)
        try:
            pvwap_path = None
            if clean_dir.exists() and sym:
                pvwap_path = self._latest(str(clean_dir / f"chart_{self.chart_id}_pvwap_{sym}_{self.ymd}.jsonl"))
            if not pvwap_path:
                pvwap_path = self._latest(str(chart_dir / f"chart_{self.chart_id}_pvwap_{sym}_*.jsonl"))
            rec_pvwap = self._read_last_jsonl(pvwap_path) if pvwap_path else None
            if rec_pvwap and rec_pvwap.get("type") == "pvwap":
                pvwap_val = rec_pvwap.get("pvwap") or rec_pvwap.get("v")
                up1 = rec_pvwap.get("up1")
                dn1 = rec_pvwap.get("dn1")
                up2 = rec_pvwap.get("up2")
                dn2 = rec_pvwap.get("dn2")
                
                if pvwap_val and pvwap_val > 0:
                    # Validation: pvwap dans une plage raisonnable
                    current_price = snapshot.get("last", 0.0)
                    if current_price > 0:
                        # ✅ FIX: Seuil plus strict selon l'instrument (0.2-0.5% au lieu de 10%)
                        sym_hint = snapshot.get("sym", "")
                        if "NQ" in sym_hint:
                            price_range = current_price * 0.005  # 0.5% pour NQ (plus volatil)
                        else:
                            price_range = current_price * 0.002  # 0.2% pour ES/autres
                        
                        if abs(pvwap_val - current_price) <= price_range:
                            # Éviter double-comptage si pvwap ≈ vwap courant
                            vwap_current = snapshot.get("vwap", {}).get("vwap", 0.0)
                            if vwap_current > 0:
                                tick_size = float(tick) if float(tick) > 0 else 0.25
                                if abs(pvwap_val - vwap_current) < 2 * tick_size:
                                    # PVWAP trop proche du VWAP courant, ne pas l'utiliser
                                    logger.debug(f"PVWAP ignoré: trop proche du VWAP courant ({pvwap_val} vs {vwap_current})")
                                else:
                                    snapshot["pvwap"] = {
                                        "v": self._normalize_px(pvwap_val, tick),
                                        "up1": self._normalize_px(up1, tick) if up1 else None,
                                        "dn1": self._normalize_px(dn1, tick) if dn1 else None,
                                        "up2": self._normalize_px(up2, tick) if up2 else None,
                                        "dn2": self._normalize_px(dn2, tick) if dn2 else None
                                    }
                            else:
                                # Pas de VWAP courant, utiliser PVWAP
                                snapshot["pvwap"] = {
                                    "v": self._normalize_px(pvwap_val, tick),
                                    "up1": self._normalize_px(up1, tick) if up1 else None,
                                    "dn1": self._normalize_px(dn1, tick) if dn1 else None,
                                    "up2": self._normalize_px(up2, tick) if up2 else None,
                                    "dn2": self._normalize_px(dn2, tick) if dn2 else None
                                }
        except Exception:
            # Ne jamais casser le flux sur une erreur de lecture PVWAP
            pass

        # ATR (Average True Range) — vraies données
        try:
            atr_path = None
            if clean_dir.exists() and sym:
                atr_path = self._latest(str(clean_dir / f"chart_{self.chart_id}_atr_{sym}_{self.ymd}.jsonl"))
            if not atr_path:
                atr_path = self._latest(str(chart_dir / f"chart_{self.chart_id}_atr_{sym}_*.jsonl"))

            rec_atr = self._read_last_jsonl(atr_path) if atr_path else None
            if rec_atr and ("atr" in rec_atr):
                # valeurs brutes
                atr_points = float(rec_atr.get("atr") or 0.0)
                tick = float(tick or 0.25)
                atr_ticks = atr_points / tick if tick > 0 else 0.0

                # prix de ref pour ratio
                ref_px = float(snapshot.get("last") or 0.0) or float(snapshot.get("vwap",{}).get("v") or snapshot.get("vwap",{}).get("vwap") or 0.0)
                atr_relative = (atr_points / ref_px) if (ref_px and ref_px > 0) else 0.0

                # exposer proprement
                snapshot["atr"] = {
                    "points": round(atr_points, 6),
                    "ticks": round(atr_ticks, 2),
                    "study": rec_atr.get("study"),
                    "sg": rec_atr.get("sg"),
                }

                # QC context + rétro-compat
                qc = snapshot.setdefault("qc_context", {})
                qc["atr_per_bar_points"] = round(atr_points, 6)
                qc["atr_per_bar_ticks"]  = round(atr_ticks, 2)
                qc["atr_relative"]       = round(atr_relative, 6)

                # Ancien champ si certains modules le lisent encore
                qc["atr_per_bar"] = qc["atr_per_bar_ticks"]
        except Exception:
            pass

        # VIX — lecture réelle
        try:
            snapshot["vix"] = self._read_vix_from_files(snapshot)
        except Exception:
            pass

        # ✅ BASEDATA — vraies données OHLC, volume, delta
        try:
            basedata_path = None
            if clean_dir.exists() and sym:
                # Essayer le format: chart_{id}_basedata_{sym}_{ymd}.jsonl
                basedata_path = self._latest(str(clean_dir / f"chart_{self.chart_id}_basedata_{sym}_{self.ymd}.jsonl"))
            if not basedata_path:
                # Fallback: chart_{id}_basedata_{sym}_*.jsonl
                basedata_path = self._latest(str(chart_dir / f"chart_{self.chart_id}_basedata_{sym}_*.jsonl"))
            
            rec_basedata = self._read_last_jsonl(basedata_path) if basedata_path else None
            if rec_basedata and rec_basedata.get("type") == "basedata":
                # Données OHLC
                snapshot["open"] = self._normalize_px(rec_basedata.get("o", 0.0), tick)
                snapshot["high"] = self._normalize_px(rec_basedata.get("h", 0.0), tick)
                snapshot["low"] = self._normalize_px(rec_basedata.get("l", 0.0), tick)
                snapshot["close"] = self._normalize_px(rec_basedata.get("c", 0.0), tick)
                snapshot["last"] = snapshot["close"]  # Close = last price
                
                # Volume et delta
                snapshot["volume"] = int(rec_basedata.get("v", 0))
                snapshot["bidvol"] = int(rec_basedata.get("bidvol", 0))
                snapshot["askvol"] = int(rec_basedata.get("askvol", 0))
                snapshot["cum_delta_day"] = float(rec_basedata.get("cum_delta_day", 0.0))
                snapshot["cum_delta_session"] = float(rec_basedata.get("cum_delta_session", 0.0))
                
                # Session info
                snapshot["session_id"] = rec_basedata.get("session_id", "US")
                
                # Calculer le spread bid/ask approximatif (si pas de DOM)
                if not snapshot.get("best_bid") and not snapshot.get("best_ask"):
                    # Estimation basée sur le tick size
                    mid_price = snapshot["close"]
                    snapshot["best_bid"] = self._normalize_px(mid_price - tick/2, tick)
                    snapshot["best_ask"] = self._normalize_px(mid_price + tick/2, tick)
                
                logger.debug(f"✅ Basedata chargé: OHLC={snapshot['open']}/{snapshot['high']}/{snapshot['low']}/{snapshot['close']}, vol={snapshot['volume']}, bidvol={snapshot['bidvol']}, askvol={snapshot['askvol']}, delta={snapshot['cum_delta_session']}, session={snapshot['session_id']}")
            
            elif basedata_path:
                logger.warning(f"⚠️ Fichier basedata trouvé mais format incorrect: {basedata_path}")
            else:
                logger.debug(f"🔍 Aucun fichier basedata trouvé pour chart_{self.chart_id}")
                
        except Exception as e:
            logger.debug(f"Erreur lecture basedata: {e}")

        # ✅ TRADE SUMMARY — données agrégées de trading
        try:
            trade_summary_path = None
            if clean_dir.exists() and sym:
                trade_summary_path = self._latest(str(clean_dir / f"chart_{self.chart_id}_trade_summary_{sym}_{self.ymd}.jsonl"))
            if not trade_summary_path:
                trade_summary_path = self._latest(str(chart_dir / f"chart_{self.chart_id}_trade_summary_{sym}_*.jsonl"))
            
            rec_trade_summary = self._read_last_jsonl(trade_summary_path) if trade_summary_path else None
            if rec_trade_summary and rec_trade_summary.get("type") == "trade_summary":
                # Données de trading agrégées
                snapshot["buy_trades"] = int(rec_trade_summary.get("buy_trades", 0))
                snapshot["sell_trades"] = int(rec_trade_summary.get("sell_trades", 0))
                snapshot["buy_vol"] = int(rec_trade_summary.get("buy_vol", 0))
                snapshot["sell_vol"] = int(rec_trade_summary.get("sell_vol", 0))
                
                # Delta cumulé (peut être plus récent que basedata)
                if rec_trade_summary.get("cum_delta_session") is not None:
                    snapshot["cum_delta_session"] = float(rec_trade_summary.get("cum_delta_session", 0.0))
                if rec_trade_summary.get("cum_delta_day") is not None:
                    snapshot["cum_delta_day"] = float(rec_trade_summary.get("cum_delta_day", 0.0))
                
                logger.debug(f"✅ Trade Summary chargé: buy_trades={snapshot['buy_trades']}, sell_trades={snapshot['sell_trades']}, buy_vol={snapshot['buy_vol']}, sell_vol={snapshot['sell_vol']}")
            
            elif trade_summary_path:
                logger.warning(f"⚠️ Fichier trade_summary trouvé mais format incorrect: {trade_summary_path}")
            else:
                logger.debug(f"🔍 Aucun fichier trade_summary trouvé pour chart_{self.chart_id}")
                
        except Exception as e:
            logger.debug(f"Erreur lecture trade_summary: {e}")

        # ✅ TRADE INDIVIDUELS — dernier trade pour prix/volume en temps réel
        try:
            trade_path = None
            if clean_dir.exists() and sym:
                trade_path = self._latest(str(clean_dir / f"chart_{self.chart_id}_trade_{sym}_{self.ymd}.jsonl"))
            if not trade_path:
                trade_path = self._latest(str(chart_dir / f"chart_{self.chart_id}_trade_{sym}_*.jsonl"))
            
            rec_trade = self._read_last_jsonl(trade_path) if trade_path else None
            if rec_trade and rec_trade.get("type") == "trade":
                # Dernier trade pour prix en temps réel
                last_trade_price = self._normalize_px(rec_trade.get("price", 0.0), tick)
                last_trade_size = int(rec_trade.get("size", 0))
                last_trade_side = rec_trade.get("side", "")
                
                # Mettre à jour le prix si plus récent que basedata
                if last_trade_price > 0:
                    snapshot["last"] = last_trade_price
                    snapshot["last_trade_price"] = last_trade_price
                    snapshot["last_trade_size"] = last_trade_size
                    snapshot["last_trade_side"] = last_trade_side
                
                # Delta cumulé (peut être le plus récent)
                if rec_trade.get("cum_delta_session") is not None:
                    snapshot["cum_delta_session"] = float(rec_trade.get("cum_delta_session", 0.0))
                if rec_trade.get("cum_delta_day") is not None:
                    snapshot["cum_delta_day"] = float(rec_trade.get("cum_delta_day", 0.0))
                
                logger.debug(f"✅ Dernier trade: {last_trade_side} {last_trade_size} @ {last_trade_price}")
            
            elif trade_path:
                logger.warning(f"⚠️ Fichier trade trouvé mais format incorrect: {trade_path}")
            else:
                logger.debug(f"🔍 Aucun fichier trade trouvé pour chart_{self.chart_id}")
                
        except Exception as e:
            logger.debug(f"Erreur lecture trade: {e}")

        # ✅ DOM — Fusion Quote + Depth (Quote = vérité L1, Depth = niveaux supplémentaires)
        try:
            # 1. Lire Quote (source de vérité L1)
            quote_path = None
            if clean_dir.exists() and sym:
                quote_path = self._latest(str(clean_dir / f"chart_{self.chart_id}_quote_{sym}_{self.ymd}.jsonl"))
            if not quote_path:
                quote_path = self._latest(str(chart_dir / f"chart_{self.chart_id}_quote_{sym}_*.jsonl"))
            
            rec_quote = self._read_last_jsonl(quote_path) if quote_path else None
            quote_timestamp = 0
            if rec_quote and rec_quote.get("type") == "quote":
                quote_timestamp = rec_quote.get("t", 0)
                # Données bid/ask niveau 1 (source de vérité)
                snapshot["best_bid"] = self._normalize_px(rec_quote.get("bid", 0.0), tick)
                snapshot["best_ask"] = self._normalize_px(rec_quote.get("ask", 0.0), tick)
                snapshot["bid_size"] = int(rec_quote.get("bq", 0))
                snapshot["ask_size"] = int(rec_quote.get("aq", 0))
                snapshot["quote_seq"] = int(rec_quote.get("seq", 0))
                
                # Calculer le spread
                if snapshot["best_bid"] > 0 and snapshot["best_ask"] > 0:
                    snapshot["spread"] = snapshot["best_ask"] - snapshot["best_bid"]
                
                logger.debug(f"✅ Quote L1: bid={snapshot['best_bid']}@{snapshot['bid_size']}, ask={snapshot['best_ask']}@{snapshot['ask_size']}, seq={snapshot['quote_seq']}")
            
            # 2. Lire Depth (niveaux supplémentaires)
            depth_data = None  # ✅ Initialiser pour éviter UnboundLocalError
            depth_path = None
            if clean_dir.exists() and sym:
                depth_path = self._latest(str(clean_dir / f"chart_{self.chart_id}_depth_{sym}_{self.ymd}.jsonl"))
            if not depth_path:
                depth_path = self._latest(str(chart_dir / f"chart_{self.chart_id}_depth_{sym}_*.jsonl"))
            
            if depth_path and depth_path.exists():
                depth_data = self._read_depth_data(depth_path, quote_timestamp)
                if depth_data:
                    # Fusionner quote (L1) + depth (L2+)
                    snapshot["dom"] = depth_data
                    snapshot["depth_levels"] = len(depth_data.get("bids", [])) + len(depth_data.get("asks", []))
                    
                    # Calculer l'imbalance de profondeur
                    total_bid_size = sum(level.get("size", 0) for level in depth_data.get("bids", []))
                    total_ask_size = sum(level.get("size", 0) for level in depth_data.get("asks", []))
                    if total_bid_size + total_ask_size > 0:
                        snapshot["depth_imbalance"] = (total_bid_size - total_ask_size) / (total_bid_size + total_ask_size)
                    
                    logger.debug(f"✅ DOM fusionné: {len(depth_data.get('bids', []))} bids, {len(depth_data.get('asks', []))} asks, imbalance={snapshot.get('depth_imbalance', 0.0):.3f}")
            
            if not rec_quote and not depth_data:
                logger.debug(f"🔍 Aucun fichier DOM trouvé pour chart_{self.chart_id}")
                
        except Exception as e:
            logger.debug(f"Erreur lecture DOM: {e}")

        # ✅ NBCV — données Net Bid/Ask Volume
        try:
            nbcv_path = None
            if clean_dir.exists() and sym:
                nbcv_path = self._latest(str(clean_dir / f"chart_{self.chart_id}_nbcv_{sym}_{self.ymd}.jsonl"))
            if not nbcv_path:
                nbcv_path = self._latest(str(chart_dir / f"chart_{self.chart_id}_nbcv_{sym}_*.jsonl"))
            
            rec_nbcv = self._read_last_jsonl(nbcv_path) if nbcv_path else None
            if rec_nbcv and rec_nbcv.get("type") == "nbcv":
                # Données NBCV complètes
                snapshot["nbcv"] = {
                    "ask_volume": int(rec_nbcv.get("ask_volume", 0)),
                    "bid_volume": int(rec_nbcv.get("bid_volume", 0)),
                    "delta": int(rec_nbcv.get("delta", 0)),
                    "trades": int(rec_nbcv.get("trades", 0)),
                    "cumulative_delta": int(rec_nbcv.get("cumulative_delta", 0)),
                    "total_volume": int(rec_nbcv.get("total_volume", 0)),
                    "delta_ratio": float(rec_nbcv.get("delta_ratio", 0.0)),
                    "ask_percent": float(rec_nbcv.get("ask_percent", 0.0)),
                    "bid_percent": float(rec_nbcv.get("bid_percent", 0.0)),
                    "bid_ask_ratio": float(rec_nbcv.get("bid_ask_ratio", 0.0)),
                    "ask_bid_ratio": float(rec_nbcv.get("ask_bid_ratio", 0.0)),
                    "pressure_bullish": int(rec_nbcv.get("pressure_bullish", 0)),
                    "pressure_bearish": int(rec_nbcv.get("pressure_bearish", 0)),
                    "pressure": int(rec_nbcv.get("pressure", 0))
                }
                
                # Calculer des métriques dérivées
                if snapshot["nbcv"]["total_volume"] > 0:
                    snapshot["nbcv"]["volume_imbalance"] = (snapshot["nbcv"]["bid_volume"] - snapshot["nbcv"]["ask_volume"]) / snapshot["nbcv"]["total_volume"]
                    snapshot["nbcv"]["volume_ratio"] = snapshot["nbcv"]["bid_volume"] / snapshot["nbcv"]["ask_volume"] if snapshot["nbcv"]["ask_volume"] > 0 else 0.0
                
                # ✅ Calculer la pression de marché normalisée et lissée
                if snapshot["nbcv"]["pressure_bullish"] == 0 and snapshot["nbcv"]["pressure_bearish"] == 0:
                    # Utiliser la nouvelle logique pro-safe
                    bull, bear, pressure, pressure_smooth = self._compute_pressure_from_nbcv(
                        snapshot["nbcv"]["bid_volume"],
                        snapshot["nbcv"]["ask_volume"], 
                        snapshot["nbcv"]["delta"],
                        snapshot["nbcv"]["total_volume"]
                    )
                    
                    snapshot["nbcv"]["pressure_bullish"] = bull
                    snapshot["nbcv"]["pressure_bearish"] = bear
                    snapshot["nbcv"]["pressure"] = pressure
                    snapshot["nbcv"]["pressure_smooth"] = pressure_smooth
                
                # Logging enrichi avec pression lissée
                pressure_smooth = snapshot['nbcv'].get('pressure_smooth', 0.0)
                logger.debug(f"✅ NBCV chargé: ask_vol={snapshot['nbcv']['ask_volume']}, bid_vol={snapshot['nbcv']['bid_volume']}, delta={snapshot['nbcv']['delta']}, trades={snapshot['nbcv']['trades']}, cum_delta={snapshot['nbcv']['cumulative_delta']}, pressure={snapshot['nbcv']['pressure']:.3f} (bull={snapshot['nbcv']['pressure_bullish']:.3f}, bear={snapshot['nbcv']['pressure_bearish']:.3f}) smooth={pressure_smooth:.3f}")
            
            elif nbcv_path:
                logger.warning(f"⚠️ Fichier NBCV trouvé mais format incorrect: {nbcv_path}")
            else:
                logger.debug(f"🔍 Aucun fichier NBCV trouvé pour chart_{self.chart_id}")
                
        except Exception as e:
            logger.debug(f"Erreur lecture NBCV: {e}")

        # ✅ CUMULATIVE DELTA — données de delta cumulatif (étude + session)
        try:
            # 1. Essayer cumulative_delta (étude technique)
            cum_delta_path = None
            if clean_dir.exists() and sym:
                cum_delta_path = self._latest(str(clean_dir / f"chart_{self.chart_id}_cumulative_delta_{sym}_{self.ymd}.jsonl"))
            if not cum_delta_path:
                cum_delta_path = self._latest(str(chart_dir / f"chart_{self.chart_id}_cumulative_delta_{sym}_*.jsonl"))
            
            rec_cum_delta = self._read_last_jsonl(cum_delta_path) if cum_delta_path else None
            
            # 2. Essayer cumulative_delta_heartbeat (données de session)
            cum_delta_hb_path = None
            if clean_dir.exists() and sym:
                cum_delta_hb_path = self._latest(str(clean_dir / f"chart_{self.chart_id}_cumulative_delta_heartbeat_{sym}_{self.ymd}.jsonl"))
            if not cum_delta_hb_path:
                cum_delta_hb_path = self._latest(str(chart_dir / f"chart_{self.chart_id}_cumulative_delta_heartbeat_{sym}_*.jsonl"))
            
            rec_cum_delta_hb = self._read_last_jsonl(cum_delta_hb_path) if cum_delta_hb_path else None
            
            # Fusionner les données des deux sources
            if rec_cum_delta and rec_cum_delta.get("type") == "cumulative_delta":
                # Données d'étude technique
                cum_delta_study = float(rec_cum_delta.get("close", 0.0))
                study_period = int(rec_cum_delta.get("study", 32))
                signal_generated = int(rec_cum_delta.get("sg", 0))
                
                snapshot["cumulative_delta"] = {
                    "study_value": cum_delta_study,
                    "study_period": study_period,
                    "signal_generated": signal_generated,
                    "source": "study"
                }
                
                logger.debug(f"✅ Cumulative Delta (étude) chargé: value={cum_delta_study}, period={study_period}, signal={signal_generated}")
            
            if rec_cum_delta_hb and rec_cum_delta_hb.get("type") == "cumulative_delta_heartbeat":
                # Données de session temps réel
                cum_delta_day = float(rec_cum_delta_hb.get("cum_delta_day", 0.0))
                cum_delta_session = float(rec_cum_delta_hb.get("cum_delta_session", 0.0))
                session_id = rec_cum_delta_hb.get("session_id", "US")
                
                # Ajouter ou compléter les données
                if "cumulative_delta" not in snapshot:
                    snapshot["cumulative_delta"] = {}
                
                snapshot["cumulative_delta"].update({
                    "cum_delta_day": cum_delta_day,
                    "cum_delta_session": cum_delta_session,
                    "session_id": session_id,
                    "source": "heartbeat"
                })
                
                logger.debug(f"✅ Cumulative Delta (session) chargé: day={cum_delta_day}, session={cum_delta_session}, session_id={session_id}")
            
            # Si aucun fichier trouvé
            if not rec_cum_delta and not rec_cum_delta_hb:
                logger.debug(f"🔍 Aucun fichier cumulative delta trouvé pour chart_{self.chart_id}")
                
        except Exception as e:
            logger.debug(f"Erreur lecture cumulative delta: {e}")

        # ✅ CORRELATION — données de corrélation ES/NQ
        try:
            # Essayer d'abord correlation_unified, puis correlation standard
            correlation_path = None
            if clean_dir.exists() and sym:
                correlation_path = self._latest(str(clean_dir / f"chart_{self.chart_id}_correlation_unified_{sym}_{self.ymd}.jsonl"))
            if not correlation_path:
                correlation_path = self._latest(str(chart_dir / f"chart_{self.chart_id}_correlation_unified_{sym}_*.jsonl"))
            if not correlation_path:
                if clean_dir.exists() and sym:
                    correlation_path = self._latest(str(clean_dir / f"chart_{self.chart_id}_correlation_{sym}_{self.ymd}.jsonl"))
                if not correlation_path:
                    correlation_path = self._latest(str(chart_dir / f"chart_{self.chart_id}_correlation_{sym}_*.jsonl"))
            
            rec_correlation = self._read_last_jsonl(correlation_path) if correlation_path else None
            if rec_correlation and rec_correlation.get("type") in ["correlation", "correlation_unified"]:
                # Données de corrélation réelles
                correlation_value = float(rec_correlation.get("cc", 0.0))
                study_period = int(rec_correlation.get("study", 50))
                signal_generated = int(rec_correlation.get("sg", 0))
                
                snapshot["correlation"] = {
                    "cc": correlation_value,
                    "study_period": study_period,
                    "signal_generated": signal_generated,
                    "timestamp": rec_correlation.get("t", 0.0)
                }
                
                # Calculer des métriques dérivées
                if abs(correlation_value) > 0.7:
                    snapshot["correlation"]["strength"] = "strong"
                elif abs(correlation_value) > 0.4:
                    snapshot["correlation"]["strength"] = "moderate"
                else:
                    snapshot["correlation"]["strength"] = "weak"
                
                # Déterminer la direction de la corrélation
                if correlation_value > 0.1:
                    snapshot["correlation"]["direction"] = "positive"
                elif correlation_value < -0.1:
                    snapshot["correlation"]["direction"] = "negative"
                else:
                    snapshot["correlation"]["direction"] = "neutral"
                
                logger.debug(f"✅ Corrélation chargée: cc={correlation_value:.4f}, strength={snapshot['correlation']['strength']}, direction={snapshot['correlation']['direction']}")
            
            elif correlation_path:
                logger.warning(f"⚠️ Fichier corrélation trouvé mais format incorrect: {correlation_path}")
            else:
                logger.debug(f"🔍 Aucun fichier corrélation trouvé pour chart_{self.chart_id}")
                
        except Exception as e:
            logger.debug(f"Erreur lecture corrélation: {e}")

        return snapshot
    
    def _validate_vwap_bands(self, vwap_data: dict, vwap_val: float) -> None:
        """
        Valide la cohérence des bandes VWAP (dn1 < v < up1, etc.)
        
        Args:
            vwap_data: Dictionnaire des données VWAP
            vwap_val: Valeur VWAP principale
        """
        if not vwap_val or vwap_val <= 0:
            return
        
        try:
            # Vérifier l'ordre des bandes
            bands = ["dn3", "dn2", "dn1", "up1", "up2", "up3"]
            band_values = {}
            
            for band in bands:
                if band in vwap_data and vwap_data[band]:
                    try:
                        band_values[band] = float(vwap_data[band])
                    except (ValueError, TypeError):
                        continue
            
            # Validation de l'ordre
            issues = []
            
            # Vérifier dn1 < v < up1
            if "dn1" in band_values and band_values["dn1"] >= vwap_val:
                issues.append(f"dn1 ({band_values['dn1']}) >= v ({vwap_val})")
            if "up1" in band_values and band_values["up1"] <= vwap_val:
                issues.append(f"up1 ({band_values['up1']}) <= v ({vwap_val})")
            
            # Vérifier l'ordre des bandes supérieures
            if "up1" in band_values and "up2" in band_values and band_values["up1"] >= band_values["up2"]:
                issues.append(f"up1 ({band_values['up1']}) >= up2 ({band_values['up2']})")
            if "up2" in band_values and "up3" in band_values and band_values["up2"] >= band_values["up3"]:
                issues.append(f"up2 ({band_values['up2']}) >= up3 ({band_values['up3']})")
            
            # Vérifier l'ordre des bandes inférieures
            if "dn1" in band_values and "dn2" in band_values and band_values["dn1"] <= band_values["dn2"]:
                issues.append(f"dn1 ({band_values['dn1']}) <= dn2 ({band_values['dn2']})")
            if "dn2" in band_values and "dn3" in band_values and band_values["dn2"] <= band_values["dn3"]:
                issues.append(f"dn2 ({band_values['dn2']}) <= dn3 ({band_values['dn3']})")
            
            if issues:
                # ✅ FIX: Ajouter la valeur tick dans le warning pour faciliter le debug
                tick_info = f" (tick={getattr(self, '_last_tick', 'unknown')})"
                logger.warning(f"⚠️ Incohérences VWAP détectées{tick_info}: {'; '.join(issues)}")
            else:
                logger.debug(f"✅ Bandes VWAP cohérentes: v={vwap_val}, up1={band_values.get('up1')}, dn1={band_values.get('dn1')}")
                
        except Exception as e:
            logger.debug(f"Erreur validation bandes VWAP: {e}")

    def _generate_vwap_bands_from_volatility(self, vwap_val: float, vix_regime: str, atr_points: float, tick_size: float) -> dict:
        """
        Génère dynamiquement les bandes VWAP basées sur la volatilité (VIX/ATR)
        
        Args:
            vwap_val: Valeur VWAP principale
            vix_regime: Régime VIX ("calm", "normal", "elevated", "high")
            atr_points: ATR en points
            tick_size: Taille du tick
            
        Returns:
            Dict avec up1, dn1, up2, dn2, up3, dn3
        """
        if not vwap_val or vwap_val <= 0:
            return {}
        
        try:
            # Base de déviation selon le régime VIX
            base_dev = 1.25  # ES/NQ standard
            
            if vix_regime == "calm":
                base_dev = 0.75
            elif vix_regime == "normal":
                base_dev = 1.25
            elif vix_regime == "elevated":
                base_dev = 2.0
            elif vix_regime == "high":
                base_dev = 3.0
            
            # Ajustement par ATR (si disponible)
            if atr_points > 0:
                # Utiliser ATR comme base si plus large que la déviation VIX
                # ✅ FIX: Clipper la déviation ATR pour éviter les valeurs énormes en panique
                atr_dev = min(atr_points * 0.5, 3.0)  # Cap à 3 pts ES/NQ
                base_dev = max(base_dev, atr_dev)
            
            # ✅ FIX: Clipper final pour éviter les déviations excessives
            base_dev = min(base_dev, 5.0)  # Cap global à 5 pts
            
            # Normaliser au tick
            base_dev = round(base_dev / tick_size) * tick_size if tick_size > 0 else base_dev
            
            return {
                "up1": round(vwap_val + base_dev, 6),
                "dn1": round(vwap_val - base_dev, 6),
                "up2": round(vwap_val + (base_dev * 2), 6),
                "dn2": round(vwap_val - (base_dev * 2), 6),
                "up3": round(vwap_val + (base_dev * 3), 6),
                "dn3": round(vwap_val - (base_dev * 3), 6)
            }
            
        except Exception as e:
            logger.debug(f"Erreur génération bandes VWAP: {e}")
            return {}

    def _read_depth_data(self, depth_path: Path, quote_timestamp: float = 0) -> dict:
        """
        Lit les données DOM multi-niveaux depuis le fichier depth avec fusion quote
        
        Args:
            depth_path: Chemin vers le fichier depth
            quote_timestamp: Timestamp du quote pour la tolérance temporelle
            
        Returns:
            Dict avec bids et asks structurés par niveau (fusionnés avec quote)
        """
        try:
            bids = []
            asks = []
            tolerance_ms = 300  # Tolérance de 300ms pour la fusion quote+depth
            
            with open(depth_path, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        rec = json.loads(line.strip())
                        if rec.get("type") == "depth" and rec.get("valid", 0) == 1:
                            # Vérifier la tolérance temporelle avec le quote
                            depth_timestamp = rec.get("t", 0)
                            if quote_timestamp > 0:
                                time_diff_ms = abs(depth_timestamp - quote_timestamp) * 1000
                                if time_diff_ms > tolerance_ms:
                                    continue  # Ignorer les données trop anciennes
                            
                            level_data = {
                                "level": int(rec.get("lvl", 0)),
                                "price": float(rec.get("price", 0.0)),
                                "size": int(rec.get("size", 0)),
                                "match_l1": bool(rec.get("match_L1", 0)),
                                "has_l1": bool(rec.get("has_l1", 0)),
                                "tol_ms_used": int(rec.get("tol_ms_used", 0)),
                                "dt_ms_to_l1": int(rec.get("dt_ms_to_l1", 0))
                            }
                            
                            if rec.get("side") == "BID":
                                bids.append(level_data)
                            elif rec.get("side") == "ASK":
                                asks.append(level_data)
                    except (json.JSONDecodeError, ValueError):
                        continue
            
            # Trier par niveau
            bids.sort(key=lambda x: x["level"])
            asks.sort(key=lambda x: x["level"])
            
            return {
                "bids": bids,
                "asks": asks,
                "timestamp": time.time(),
                "quote_timestamp": quote_timestamp,
                "tolerance_ms": tolerance_ms
            }
            
        except Exception as e:
            logger.debug(f"Erreur lecture depth data: {e}")
            return {}

    # --- SAFE helpers pour le calcul de pression ---------------------------------
    def _safediv(self, num: float, den: float, default: float = 0.0) -> float:
        """Division sécurisée avec fallback"""
        return num / den if den else default

    def _squash_tanh(self, x: float, k: float) -> float:
        """Bornage doux avec tanh pour éviter les pics aberrants"""
        from math import tanh
        return tanh(self._safediv(x, k, 0.0))

    def _compute_pressure_from_nbcv(self, bid_volume: int, ask_volume: int, delta: int, total_volume: int) -> tuple:
        """
        Calcule la pression de marché normalisée et lissée (pro-safe)
        
        Args:
            bid_volume: Volume bid
            ask_volume: Volume ask  
            delta: Delta net (ask - bid)
            total_volume: Volume total
            
        Returns:
            Tuple (pressure_bullish, pressure_bearish, pressure, pressure_smooth)
        """
        # Params tunables (à mettre en config si nécessaire)
        W_DELTA = 0.7
        W_IMB = 0.3
        K_DELTA = 0.02   # ~2% du volume de barre => pression ~0.76
        K_IMB = 0.10     # 10% d'imbalance => pression ~0.76
        EMA_ALPHA = 0.30
        
        # Cas sans échange
        if total_volume <= 0:
            sym = getattr(self, '_last_sym', "GENERIC")
            if not hasattr(self, '_pressure_ema'):
                self._pressure_ema = {}
            return 0.0, 0.0, 0.0, float(self._pressure_ema.get(sym, 0.0))
        
        # Normalisations robustes
        delta_norm = self._safediv(float(delta), float(total_volume), 0.0)
        imbalance = self._safediv(float(bid_volume - ask_volume), float(total_volume), 0.0)
        
        # Termes squashés
        delta_term = self._squash_tanh(delta_norm, K_DELTA)
        imb_term = self._squash_tanh(imbalance, K_IMB)
        
        # Agrégation pondérée
        pressure_signed = W_DELTA * delta_term + W_IMB * imb_term
        
        # Décomposition bull/bear
        pressure_bullish = max(pressure_signed, 0.0)
        pressure_bearish = max(-pressure_signed, 0.0)
        
        # EMA lissée (état persistant) - Multi-symbole
        if not hasattr(self, '_pressure_ema'):
            self._pressure_ema = {}  # {sym: float}
        
        # Utiliser le symbole pour l'EMA (éviter mélange multi-symboles)
        sym = getattr(self, '_last_sym', "GENERIC")  # Utiliser le dernier symbole traité
        prev_ema = float(self._pressure_ema.get(sym, 0.0))
        
        self._pressure_ema[sym] = EMA_ALPHA * pressure_signed + (1.0 - EMA_ALPHA) * prev_ema
        pressure_smooth = self._pressure_ema[sym]
        
        return pressure_bullish, pressure_bearish, pressure_signed, pressure_smooth

    def _read_vix_from_files(self, snapshot: dict) -> float:
        """
        Lit le dernier VIX dispo pour le chart, sinon 0.0.
        Cherche d'abord en CLEAN par sym, puis CHART_X générique.
        """
        if not (self.base_day_dir and self.ymd and self.chart_id):
            return float(snapshot.get("vix", 0.0) or 0.0)

        sym = snapshot.get("sym") or snapshot.get("symbol") or ""
        chart_dir = self.base_day_dir / f"CHART_{self.chart_id}"
        clean_dir = chart_dir / "CLEAN"

        vix_path = None
        if clean_dir.exists() and sym:
            vix_path = self._latest(str(clean_dir / f"chart_{self.chart_id}_vix_{sym}_{self.ymd}.jsonl"))
        if not vix_path:
            vix_path = self._latest(str(chart_dir / f"chart_{self.chart_id}_vix_{sym}_*.jsonl"))

        rec = self._read_last_jsonl(vix_path) if vix_path else None
        try:
            return float((rec or {}).get("vix", snapshot.get("vix", 0.0)) or 0.0)
        except Exception:
            return float(snapshot.get("vix", 0.0) or 0.0)
    
    def adapt_snapshot_for_elite(self, legacy_snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """
        Adapter un snapshot legacy pour les méthodes Elite
        
        Args:
            legacy_snapshot: Snapshot au format legacy
            
        Returns:
            Snapshot adapté pour les méthodes Elite
        """
        self.mapping_stats["total_mappings"] += 1
        
        try:
            # 🔗 Merge éventuelle depuis fichiers (si base_day_dir/ymd/chart_id fournis)
            legacy_snapshot = self._merge_menthorq_vwap_from_files(dict(legacy_snapshot))
            # ✅ Sécuriser l'accès aux variables (avant tout try/except)
            vp = (legacy_snapshot.get("vp") or {})
            vwap_src = (legacy_snapshot.get("vwap") or {})
            ofdom = (legacy_snapshot.get("ofdom") or {})
            lead = (legacy_snapshot.get("lead") or {})
            micro = (legacy_snapshot.get("micro") or {})
            cluster = (legacy_snapshot.get("cluster") or {})
            mia = (legacy_snapshot.get("mia") or {})
            
            # Créer le snapshot adapté
            elite_snapshot = {
                # Champs de base
                "sym": legacy_snapshot.get("sym", "ES"),
                "t": legacy_snapshot.get("t", int(time.time())),
                "last": legacy_snapshot.get("last", 0.0),
                "current_price": legacy_snapshot.get("last", 0.0),
                "timestamp": legacy_snapshot.get("t", int(time.time())),
                
                # Session et régime
                "session": {
                    "phase": legacy_snapshot.get("phase", "REGULAR"),
                    "regime": legacy_snapshot.get("regime", "TREND")
                },
                
                # Macro (VIX)
                "macro": {
                    "vix": legacy_snapshot.get("vix", 20.0),
                    "vix_trend": legacy_snapshot.get("vix_trend", "NEUTRAL")
                },
                
                # MenthorQ
                "mentorq": self._adapt_mentorq(legacy_snapshot),
                
                # Microstructure
                "micro": self._adapt_microstructure(legacy_snapshot),
                
                # Order Flow / DOM
                "ofdom": self._adapt_ofdom(legacy_snapshot),
                
                # Leadership
                "leadership": self._adapt_leadership(legacy_snapshot),
                
                # Cluster
                "cluster": self._adapt_cluster(legacy_snapshot),
                
                # MIA
                "mia": self._adapt_mia(legacy_snapshot),
                
                # Contexte précédent
                "prev": {
                    "state": legacy_snapshot.get("prev_state", "NEUTRE")
                },
                
                # Configuration Elite
                "elite_methods": {
                    "menthorq_elite_enabled": True,
                    "battle_navale_elite_enabled": True,
                    "kernel_smooth_enabled": True,
                    "orderflow_advanced_enabled": True,
                    "dom_health_enabled": True
                },
                
                # Contexte QC
                "qc_context": self._adapt_qc_context(legacy_snapshot)
            }
            
            # ✅ Préserver OrderFlow trade_summary (courant + historique)
            if legacy_snapshot.get("trade_summary_current"):
                elite_snapshot["trade_summary_current"] = legacy_snapshot.get("trade_summary_current")
            if legacy_snapshot.get("trade_summary_history"):
                elite_snapshot["trade_summary_history"] = legacy_snapshot.get("trade_summary_history")
            
            # ✅ PRÉSERVER TOUTES LES CLÉS JSONL MENTHORQ
            jsonl_keys = [k for k in legacy_snapshot.keys() if k.startswith("gex_") or k in ["hvl", "hvl_0dte", "call_resistance", "call_resistance_0dte", "put_support", "put_support_0dte", "gamma_wall_0dte", "1d_max", "1d_min", "type", "i", "chart"]]
            for key in jsonl_keys:
                elite_snapshot[key] = legacy_snapshot[key]
            
            # ✅ PRÉSERVER LES DONNÉES OHLC POUR ATR
            ohlc_keys = ["price_highs", "price_lows", "price_closes"]
            for key in ohlc_keys:
                if key in legacy_snapshot:
                    elite_snapshot[key] = legacy_snapshot[key]
            
            logger.info(f"🎯 Clés JSONL préservées: {jsonl_keys}")
            
            self.mapping_stats["successful_mappings"] += 1
            logger.debug("✅ Snapshot adapté avec succès")
            return elite_snapshot
            
        except Exception as e:
            logger.error(f"❌ Erreur adaptation snapshot: {e}")
            self.mapping_stats["fallback_used"] += 1
            return self._create_fallback_snapshot(legacy_snapshot)
    
    def _adapt_mentorq(self, legacy: Dict[str, Any]) -> Dict[str, Any]:
        """Adapter les données MenthorQ (support clés directes + legacy)"""
        # ✅ Support des clés directes (nouvelles)
        gamma_max = legacy.get("gamma_max", 0.0)
        call_wall = legacy.get("call_wall", 0.0)
        put_wall = legacy.get("put_wall", 0.0)
        zero_gamma = legacy.get("zero_gamma", 0.0)
        gamma_flip = legacy.get("gamma_flip", False)
        flip_price = legacy.get("flip_price", 0.0)
        flip_age_minutes = legacy.get("flip_age_minutes", 0)
        
        blind_spot_1 = legacy.get("blind_spot_1", 0.0)
        blind_spot_2 = legacy.get("blind_spot_2", 0.0)
        liquidity_gap = legacy.get("liquidity_gap", 0.0)
        dead_zone = legacy.get("dead_zone", 0.0)
        
        bias_score = legacy.get("bias_score", 0.0)
        bias_strength = legacy.get("bias_strength", 0.0)
        bias_confidence = legacy.get("bias_confidence", 0.0)
        
        study_vwap = legacy.get("study_vwap", 0.0)
        vwap_up1 = legacy.get("vwap_up1", 0.0)
        vwap_dn1 = legacy.get("vwap_dn1", 0.0)
        
        vix_level = legacy.get("vix_level", 0.0)
        
        # ✅ Fallback vers clés legacy si clés directes vides
        if gamma_max == 0.0:
            mentorq = legacy.get("mentorq_gamma", {})
            gamma_max = mentorq.get("gamma_max", 0.0)
            call_wall = mentorq.get("call_wall", 0.0)
            put_wall = mentorq.get("put_wall", 0.0)
            zero_gamma = mentorq.get("zero_gamma", 0.0)
        
        if blind_spot_1 == 0.0:
            mentorq_blind = legacy.get("mentorq_blind", {})
            blind_spot_1 = mentorq_blind.get("spot_1", 0.0)
            blind_spot_2 = mentorq_blind.get("spot_2", 0.0)
        
        if bias_score == 0.0:
            # Pas de fallback pour dealers bias, on garde 0.0
            pass
        
        if study_vwap == 0.0:
            vwap_legacy = legacy.get("vwap", {})
            study_vwap = vwap_legacy.get("value", 0.0)
            vwap_up1 = vwap_legacy.get("upper_band", 0.0)
            vwap_dn1 = vwap_legacy.get("lower_band", 0.0)
        
        if vix_level == 0.0:
            vix_level = legacy.get("vix", 0.0)
        
        return {
            "gamma": {
                "levels": legacy.get("mentorq_gamma", {}).get("levels", []),
                "call_wall": call_wall,
                "put_wall": put_wall,
                "zero_gamma": zero_gamma,
                "gamma_max": gamma_max,
                "gamma_flip": gamma_flip,
                "flip_price": flip_price,
                "flip_age_minutes": flip_age_minutes
            },
            "swing": legacy.get("mentorq_swing", {"avail": False}),
            "blind": {
                "spots": legacy.get("mentorq_blind", {}).get("spots", []),
                "spot_1": blind_spot_1,
                "spot_2": blind_spot_2,
                "liquidity_gap": liquidity_gap,
                "dead_zone": dead_zone
            },
            "dealers_bias": {
                "bias_score": bias_score,
                "bias_strength": bias_strength,
                "bias_confidence": bias_confidence
            },
            "vwap": {
                "vwap": study_vwap,
                "up1": vwap_up1,
                "dn1": vwap_dn1,
                "slope": 0.0
            },
            "vix": {
                "vix": vix_level
            },
            "scanner": legacy.get("scanner", {"recent": {}}),
            "qscore": legacy.get("qscore", 0)
        }
    
    def _adapt_microstructure(self, legacy: Dict[str, Any]) -> Dict[str, Any]:
        """Adapter les données de microstructure (support clés directes + legacy)"""
        # ✅ Support des clés directes (nouvelles)
        vpoc = legacy.get("vpoc", 0.0)
        val = legacy.get("val", 0.0)
        vah = legacy.get("vah", 0.0)
        
        # ✅ Fallback vers clés legacy si clés directes vides
        vp = legacy.get("vp") or legacy.get("volume_profile") or {}  # ✅ Multi-alias
        if vpoc == 0.0:
            vpoc = vp.get("vpoc", 0.0)
            val = vp.get("val", 0.0)
            vah = vp.get("vah", 0.0)
        
        # ✅ VWAP (tolère plusieurs formats + nouvelles bandes)
        vw = legacy.get("vwap", {})
        vwap_val = vw.get("v") or vw.get("vwap") or vw.get("value", 0.0)
        vwap_up1 = vw.get("up1") or vw.get("upper_band", 0.0)
        vwap_dn1 = vw.get("dn1") or vw.get("lower_band", 0.0)
        vwap_up2 = vw.get("up2", 0.0)
        vwap_dn2 = vw.get("dn2", 0.0)
        vwap_up3 = vw.get("up3", 0.0)
        vwap_dn3 = vw.get("dn3", 0.0)
        vwap_slope = vw.get("slope", 0.0)
        
        # ✅ PVWAP (VWAP session précédente)
        pvwap_data = legacy.get("pvwap", {})
        pvwap_val = pvwap_data.get("v", 0.0)
        pvwap_up1 = pvwap_data.get("up1", 0.0)
        pvwap_dn1 = pvwap_data.get("dn1", 0.0)
        pvwap_up2 = pvwap_data.get("up2", 0.0)
        pvwap_dn2 = pvwap_data.get("dn2", 0.0)
        
        return {
            "vwap": {
                "value": vwap_val,
                "upper_band": vwap_up1,  # Compatibilité
                "lower_band": vwap_dn1,  # Compatibilité
                "up1": vwap_up1,
                "dn1": vwap_dn1,
                "up2": vwap_up2,
                "dn2": vwap_dn2,
                "up3": vwap_up3,
                "dn3": vwap_dn3,
                "deviation": vw.get("deviation", 0.0),
                "slope": vwap_slope
            },
            "pvwap": {
                "value": pvwap_val,
                "up1": pvwap_up1,
                "dn1": pvwap_dn1,
                "up2": pvwap_up2,
                "dn2": pvwap_dn2
            },
            "vp": {
                "vpoc": vpoc,
                "val": val,
                "vah": vah,
                "volume": vp.get("volume", 0.0)
            }
        }
    
    def _adapt_ofdom(self, legacy: Dict[str, Any]) -> Dict[str, Any]:
        """Adapter les données Order Flow / DOM (support clés directes + legacy)"""
        # ✅ Support des clés directes (nouvelles)
        best_bid = legacy.get("best_bid", 0.0)
        best_ask = legacy.get("best_ask", 0.0)
        l1_bbo_ratio = legacy.get("l1_bbo_ratio", 1.0)
        l1_bbo_ratio_rolling = legacy.get("l1_bbo_ratio_rolling", 1.0)
        depth_levels = legacy.get("depth_levels", 0)
        
        # ✅ Volume et delta depuis trade_summary (priorité) puis basedata
        buy_vol = legacy.get("buy_vol", 0)  # Volume d'achat depuis trade_summary
        sell_vol = legacy.get("sell_vol", 0)  # Volume de vente depuis trade_summary
        cum_delta_session = legacy.get("cum_delta_session", 0)
        
        # Fallback vers basedata si trade_summary non disponible
        if buy_vol == 0 and sell_vol == 0:
            buy_vol = legacy.get("bidvol", 0)  # Volume bid = buy volume
            sell_vol = legacy.get("askvol", 0)  # Volume ask = sell volume
        
        # ✅ Fallback final vers ofdom imbriqué si toujours vide
        if buy_vol == 0 and sell_vol == 0:
            ofd = legacy.get("ofdom", {}) or {}
            buy_vol = ofd.get("buy_vol", 0)
            sell_vol = ofd.get("sell_vol", 0)
        
        # ✅ Fallback vers clés legacy si clés directes vides
        if best_bid == 0.0:
            ofdom = legacy.get("ofdom", {})
            best_bid = ofdom.get("best_bid", 0.0)
            best_ask = ofdom.get("best_ask", 0.0)
            l1_bbo_ratio = ofdom.get("l1_bbo_ratio", 1.0)
        
        # ✅ Fallback vers basedata si toujours vide
        if best_bid == 0.0 and best_ask == 0.0:
            # Utiliser les données basedata pour estimer bid/ask
            close_price = legacy.get("close", legacy.get("last", 0.0))
            if close_price > 0:
                tick_size = legacy.get("tick_size", 0.25)  # ✅ Récupérer le vrai tick si dispo
                best_bid = close_price - tick_size/2
                best_ask = close_price + tick_size/2
        
        # ✅ Récupérer tailles L1 si dispo
        bid_size = legacy.get("ofdom", {}).get("bid_size", 0)
        ask_size = legacy.get("ofdom", {}).get("ask_size", 0)
        
        # ✅ Calculer l1_bbo_ratio (rapport de tailles si possible)
        if best_bid > 0 and best_ask > 0 and (best_bid + best_ask) > 0:
            if bid_size > 0 and ask_size > 0:
                l1_bbo_ratio = bid_size / ask_size
            else:
                # Fallback vers rapport de prix (l1_ba_price_ratio - moins informatif, mais stable)
                l1_bbo_ratio = best_bid / best_ask if best_ask > 0 else 1.0
        
        return {
            "best_bid": best_bid,
            "best_ask": best_ask,
            "spread": best_ask - best_bid if best_ask > 0 and best_bid > 0 else 0.0,
            "bid_size": legacy.get("ofdom", {}).get("bid_size", 0),
            "ask_size": legacy.get("ofdom", {}).get("ask_size", 0),
            "volume_imbalance": legacy.get("ofdom", {}).get("volume_imbalance", 0.0),
            "l1_bbo_ratio": l1_bbo_ratio,
            "l1_bbo_ratio_rolling": l1_bbo_ratio_rolling,
            "depth_levels": depth_levels,
            "depth_imbalance": legacy.get("ofdom", {}).get("depth_imbalance", 0.0),
            "buy_vol": buy_vol,
            "sell_vol": sell_vol,
            "cum_delta_session": cum_delta_session
        }
    
    def _adapt_leadership(self, legacy: Dict[str, Any]) -> Dict[str, Any]:
        """Adapter les données de leadership avec vraies données de corrélation"""
        lead = legacy.get("lead", {})
        
        # ✅ Utiliser les vraies données de corrélation si disponibles
        correlation_data = legacy.get("correlation", {})
        real_correlation = correlation_data.get("cc", 0.0) if correlation_data else 0.0
        
        # Déterminer si NQ est plus fort que ES basé sur la corrélation
        nq_stronger = real_correlation > 0.1  # Corrélation positive = NQ leader
        
        # Synchronisation basée sur la force de la corrélation
        sync_ok = abs(real_correlation) > 0.3  # Corrélation modérée = sync OK
        
        return {
            "nq_stronger_than_es": nq_stronger,
            "sync_ok": sync_ok,
            "correlation": real_correlation,
            "lead_lag": lead.get("lead_lag", 0.0),
            # ✅ Ajouter les métadonnées de corrélation
            "correlation_strength": correlation_data.get("strength", "weak") if correlation_data else "weak",
            "correlation_direction": correlation_data.get("direction", "neutral") if correlation_data else "neutral",
            "correlation_study_period": correlation_data.get("study_period", 50) if correlation_data else 50
        }
    
    def _adapt_cluster(self, legacy: Dict[str, Any]) -> Dict[str, Any]:
        """Adapter les données de cluster"""
        cluster = legacy.get("cluster", {})
        
        return {
            "signals": cluster.get("signals", {}),
            "confluence_score": cluster.get("confluence_score", 0.0),
            "strength": cluster.get("strength", "NEUTRAL")
        }
    
    def _adapt_mia(self, legacy: Dict[str, Any]) -> Dict[str, Any]:
        """Adapter les données MIA"""
        return {
            "score": legacy.get("mia_score", 0.0),
            "state": legacy.get("mia_state", "NEUTRE")
        }
    
    def _adapt_qc_context(self, legacy: Dict[str, Any]) -> Dict[str, Any]:
        """Adapter le contexte QC"""
        return {
            "options_snapshot_age_min": legacy.get("options_age_min", 0),
            "vwap_qc_p95": legacy.get("vwap_qc_p95", 0.0),
            "data_quality_score": legacy.get("data_quality", 1.0),
            "atr_per_bar": legacy.get("atr_per_bar", 1.0),
            "atr_relative": legacy.get("atr_relative", 1.0),
            "l1_bbo_ratio_rolling": legacy.get("l1_bbo_ratio_rolling", 1.0),
            "symbol": legacy.get("sym", "ES"),
            "tick_size": legacy.get("tick_size", 0.25)  # ✅ Lire depuis legacy si disponible
        }
    
    def _create_fallback_snapshot(self, legacy: Dict[str, Any]) -> Dict[str, Any]:
        """Créer un snapshot de fallback minimal"""
        logger.warning("🔄 Utilisation du fallback snapshot")
        
        return {
            "sym": legacy.get("sym", "ES"),
            "t": int(time.time()),
            "last": legacy.get("last", 4150.0),
            "current_price": legacy.get("last", 4150.0),
            "timestamp": int(time.time()),
            "session": {"phase": "REGULAR", "regime": "TREND"},
            "macro": {"vix": 20.0, "vix_trend": "NEUTRAL"},
            "mentorq": {
                "gamma": {"levels": [], "call_wall": 0.0, "put_wall": 0.0, "zero_gamma": 0.0, "gamma_max": 0.0},
                "swing": {"avail": False},
                "blind": {"spots": [], "spot_1": 0.0, "spot_2": 0.0},
                "scanner": {"recent": {}},
                "qscore": 0
            },
            "micro": {
                "vwap": {"value": 4150.0, "upper_band": 4155.0, "lower_band": 4145.0, "deviation": 0.0},
                "vp": {"vpoc": 4150.0, "val": 4145.0, "vah": 4155.0, "volume": 0.0}
            },
            "ofdom": {
                "best_bid": 4150.0, "best_ask": 4150.25, "spread": 0.25,
                "bid_size": 100, "ask_size": 100, "volume_imbalance": 0.0,
                "l1_bbo_ratio": 1.0, "depth_imbalance": 0.0
            },
            "leadership": {"nq_stronger_than_es": False, "sync_ok": True, "correlation": 0.0, "lead_lag": 0.0},
            "cluster": {"signals": {}, "confluence_score": 0.0, "strength": "NEUTRAL"},
            "mia": {"score": 0.0, "state": "NEUTRE"},
            "prev": {"state": "NEUTRE"},
            "elite_methods": {
                "menthorq_elite_enabled": True,
                "battle_navale_elite_enabled": True,
                "kernel_smooth_enabled": True,
                "orderflow_advanced_enabled": True,
                "dom_health_enabled": True
            },
            "qc_context": {
                "options_snapshot_age_min": 0,
                "vwap_qc_p95": 0.0,
                "data_quality_score": 1.0,
                "atr_per_bar": 1.0,
                "atr_relative": 1.0,
                "l1_bbo_ratio_rolling": 1.0,
                "symbol": "ES",
                "tick_size": 0.25
            }
        }
    
    def get_mapping_stats(self) -> Dict[str, Any]:
        """Obtenir les statistiques de mapping"""
        success_rate = 0.0
        if self.mapping_stats["total_mappings"] > 0:
            success_rate = (self.mapping_stats["successful_mappings"] / self.mapping_stats["total_mappings"]) * 100
        
        return {
            **self.mapping_stats,
            "success_rate_percent": success_rate
        }
    
    def map_menthorq_gamma(self, rec: dict, current_price: float = None, prefer_0dte: bool = True) -> dict:
        """
        Mapper les données MenthorQ gamma depuis le format JSONL vers le format Elite
        
        Args:
            rec: Record JSONL avec clés gex_*, hvl, call_resistance, etc.
            current_price: Prix actuel pour dériver les murs si nécessaire
            prefer_0dte: Préférer les données 0DTE si disponibles
            
        Returns:
            Dict avec gamma_max, call_wall, put_wall, zero_gamma, etc.
        """
        try:
            # 1) Collecte des niveaux GEX
            gex_keys = [k for k in rec.keys() if k.startswith("gex_")]
            gex_levels = sorted([float(rec[k]) for k in gex_keys if rec.get(k) is not None])
            
            # 2) gamma_max (ordre de priorité: hvl_0dte > hvl > médiane gex)
            gamma_max = 0.0
            if rec.get("hvl_0dte") is not None:
                gamma_max = float(rec["hvl_0dte"])
            elif rec.get("hvl") is not None:
                gamma_max = float(rec["hvl"])
            elif gex_levels:
                gamma_max = gex_levels[len(gex_levels)//2]  # médiane
            
            # 3) murs call/put (0DTE > global > dérivés des gex si prix fourni)
            call_wall = 0.0
            put_wall = 0.0
            
            if prefer_0dte and rec.get("call_resistance_0dte") is not None:
                call_wall = float(rec["call_resistance_0dte"])
            elif rec.get("call_resistance") is not None:
                call_wall = float(rec["call_resistance"])
            
            if prefer_0dte and rec.get("put_support_0dte") is not None:
                put_wall = float(rec["put_support_0dte"])
            elif rec.get("put_support") is not None:
                put_wall = float(rec["put_support"])
            
            # Si toujours 0 et current_price dispo, derive depuis gex
            if current_price is not None and gex_levels:
                if call_wall == 0.0:
                    above = [x for x in gex_levels if x >= current_price]
                    if above: 
                        call_wall = above[0]
                if put_wall == 0.0:
                    below = [x for x in gex_levels if x <= current_price]
                    if below: 
                        put_wall = below[-1]
            
            # 4) zero_gamma (fallback: midpoint)
            if call_wall > 0 and put_wall > 0:
                zero_gamma = (call_wall + put_wall) / 2.0
            else:
                zero_gamma = gamma_max  # fallback neutre
            
            # 5) flip (sans état → désactivé)
            gamma_flip = False
            flip_price = zero_gamma
            flip_age_minutes = 0
            
            return {
                "gamma_max": gamma_max,
                "call_wall": call_wall,
                "put_wall": put_wall,
                "zero_gamma": zero_gamma,
                "gamma_flip": gamma_flip,
                "flip_price": flip_price,
                "flip_age_minutes": flip_age_minutes,
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur mapping gamma MenthorQ: {e}")
            return {
                "gamma_max": 0.0,
                "call_wall": 0.0,
                "put_wall": 0.0,
                "zero_gamma": 0.0,
                "gamma_flip": False,
                "flip_price": 0.0,
                "flip_age_minutes": 0,
            }

    def build_menthorq_payload(self, rec_gamma: Dict[str, Any], current_price: float) -> Dict[str, Any]:
        """
        Construire un payload MenthorQ complet avec les vraies données JSONL
        
        Args:
            rec_gamma: Record JSONL avec données MenthorQ (gex_*, hvl, call_resistance, etc.)
            current_price: Prix actuel du marché
            
        Returns:
            Payload MenthorQ Elite complet et fonctionnel
        """
        try:
            # ✅ Mapping gamma avec les vraies données JSONL
            gamma = self.map_menthorq_gamma(rec_gamma, current_price, prefer_0dte=True)
            
            # VIX réel + régime
            vix_val = 0.0
            try:
                vix_val = float(rec_gamma.get("vix", 0.0) or 0.0)
            except Exception:
                vix_val = 0.0

            def _vix_regime(v):
                if v < 13: return "calm"
                if v < 18: return "normal"
                if v < 24: return "elevated"
                return "high"

            vix_regime = _vix_regime(vix_val)
            
            # ✅ VWAP enrichi avec toutes les bandes (nouveau format study)
            vv_block = rec_gamma.get("vwap", {})
            if isinstance(vv_block, dict):
                vwap_val = float(vv_block.get("v") or vv_block.get("vwap") or vv_block.get("value") or 0.0) or current_price
                slope = float(vv_block.get("slope") or 0.0)
                
                # ✅ Nouvelles bandes de déviation (format study)
                up1 = float(vv_block.get("up1") or 0.0)
                dn1 = float(vv_block.get("dn1") or 0.0)
                up2 = float(vv_block.get("up2") or 0.0)
                dn2 = float(vv_block.get("dn2") or 0.0)
                up3 = float(vv_block.get("up3") or 0.0)
                dn3 = float(vv_block.get("dn3") or 0.0)
                
                # Fallback vers ancien format si nouvelles bandes absentes
                if up1 == 0.0 and dn1 == 0.0:
                    if vv_block.get("upper_band") is not None and vv_block.get("lower_band") is not None:
                        try:
                            up1 = float(vv_block.get("upper_band"))
                            dn1 = float(vv_block.get("lower_band"))
                        except Exception:
                            up1 = vwap_val + 1.25
            dn1 = vwap_val - 1.25
                    elif vv_block.get("deviation") is not None:
                        try:
                            dev = abs(float(vv_block.get("deviation") or 0.0))
                        except Exception:
                            dev = 1.25
                        up1 = vwap_val + dev
                        dn1 = vwap_val - dev
                    else:
                        up1 = vwap_val + 1.25
                        dn1 = vwap_val - 1.25
                
                # Générer up2/dn2 et up3/dn3 si absents (multiples de la déviation de base)
                if up2 == 0.0 and dn2 == 0.0 and up1 > 0 and dn1 > 0:
                    base_dev = (up1 - vwap_val) if up1 > vwap_val else 1.25
                    up2 = vwap_val + (base_dev * 2)
                    dn2 = vwap_val - (base_dev * 2)
                
                if up3 == 0.0 and dn3 == 0.0 and up1 > 0 and dn1 > 0:
                    base_dev = (up1 - vwap_val) if up1 > vwap_val else 1.25
                    up3 = vwap_val + (base_dev * 3)
                    dn3 = vwap_val - (base_dev * 3)
                    
            else:
                vwap_val = float(vv_block or 0.0) or current_price
                slope = 0.0
                up1 = vwap_val + 1.25
                dn1 = vwap_val - 1.25
                up2 = vwap_val + 2.5
                dn2 = vwap_val - 2.5
                up3 = vwap_val + 3.75
                dn3 = vwap_val - 3.75

            # ✅ PVWAP (VWAP session précédente)
            pvwap_data = rec_gamma.get("pvwap", {})
            pvwap_val = 0.0
            pvwap_up1 = 0.0
            pvwap_dn1 = 0.0
            pvwap_up2 = 0.0
            pvwap_dn2 = 0.0
            
            if isinstance(pvwap_data, dict):
                pvwap_val = float(pvwap_data.get("v") or pvwap_data.get("pvwap") or 0.0)
                pvwap_up1 = float(pvwap_data.get("up1") or 0.0)
                pvwap_dn1 = float(pvwap_data.get("dn1") or 0.0)
                pvwap_up2 = float(pvwap_data.get("up2") or 0.0)
                pvwap_dn2 = float(pvwap_data.get("dn2") or 0.0)
            elif pvwap_data:
                pvwap_val = float(pvwap_data or 0.0)
            
            # ✅ Dealers bias (placeholder robuste)
            dealers = {
                "bias_score": float(rec_gamma.get("bias_score", 0.0)),
                "bias_strength": float(rec_gamma.get("bias_strength", 0.0)),
                "bias_confidence": float(rec_gamma.get("bias_confidence", 0.0))
            }
            
            # ✅ Tolérance de clustering sensible au VIX + ATR (plus large quand volatilité monte)
            sym = rec_gamma.get("sym", "ES")
            base_eps = 10.0 if "NQ" in sym else 4.0
            
            # Modulation par VIX
            if vix_regime == "calm":
                eps = base_eps * 0.8
            elif vix_regime == "normal":
                eps = base_eps
            elif vix_regime == "elevated":
                eps = base_eps * 1.3
            else:  # high
                eps = base_eps * 1.6
            
            # Modulation par ATR (si dispo dans snapshot)
            atr_points = 0.0
            try:
                atr_points = float((rec_gamma.get("atr") or {}).get("points", 0.0))
            except Exception:
                pass
            
            # élargir légèrement si volatilité/ATR monte (cap pour éviter l'excès)
            vol_factor = 1.0 + min(atr_points / 5.0, 0.6)   # +20%/pt jusqu'à +60% max
            eps_vol = eps * vol_factor
            
            # ✅ Blind spots (lecture élargie + clustering + score de renforcement)
            # Collecte depuis rec_gamma: dictionnaire direct menthorq_blind_spots ou clés blind_spot_*
            raw_blinds: Dict[str, float] = {}
            try:
                if isinstance(rec_gamma.get("menthorq_blind_spots"), dict):
                    for k, v in rec_gamma["menthorq_blind_spots"].items():
                        if isinstance(k, str) and k.startswith("blind_spot_"):
                            try:
                                val = float(v or 0.0)
                            except Exception:
                                continue
                            if val > 0:
                                raw_blinds[k] = val
                # Balayer rec_gamma pour toutes les clés blind_spot_*
                for k, v in rec_gamma.items():
                    if isinstance(k, str) and k.startswith("blind_spot_"):
                        try:
                            val = float(v or 0.0)
                        except Exception:
                            continue
                        if val > 0:
                            raw_blinds[k] = val
            except Exception:
                raw_blinds = {}

            # Construire liste triee des niveaux valides
            blind_levels = sorted(set(raw_blinds.values()))

            # Clustering simple par tolérance (eps basé sur le tick)
            qc_tick = None
            try:
                qc_tick = (rec_gamma.get("qc_context", {}) or {}).get("tick_size")
            except Exception:
                qc_tick = None
            try:
                tick = float(qc_tick or rec_gamma.get("tick_size") or 0.25)
            except Exception:
                tick = 0.25
            
            # ✅ FIX: Garder le PLUS LARGE entre EPS volatilité et garde-fou tick
            eps_tick = max(1e-9, 40.0 * float(tick))  # ~10 pts NQ (40×0.25), ~10 pts ES (40×0.25)
            eps = max(eps_vol, eps_tick)  # Prendre le plus large des deux

            def _cluster_blinds(levels: List[float], eps_points: float) -> List[Tuple[float, int]]:
                if not levels:
                    return []
                lv = sorted(levels)
                clusters: List[Tuple[float, int]] = []
                cur = [lv[0]]
                for v in lv[1:]:
                    if abs(v - cur[-1]) <= eps_points:
                        cur.append(v)
                    else:
                        clusters.append((sum(cur)/len(cur), len(cur)))
                        cur = [v]
                clusters.append((sum(cur)/len(cur), len(cur)))
                return clusters

            clusters = _cluster_blinds(blind_levels, eps)

            # Score de renforcement par confluence prix/HVL/walls
            reinforcement = 0
            try:
                hvl_val = float(rec_gamma.get("hvl") or rec_gamma.get("hvl_0dte") or 0.0)
            except Exception:
                hvl_val = 0.0
            try:
                cw = float(rec_gamma.get("call_resistance_0dte") or rec_gamma.get("call_resistance") or 0.0)
            except Exception:
                cw = 0.0
            try:
                pw = float(rec_gamma.get("put_support_0dte") or rec_gamma.get("put_support") or 0.0)
            except Exception:
                pw = 0.0

            # Pré-calculer VAH/VAL/VPOC une fois
            try:
                vah_cached = float(rec_gamma.get("vah") or rec_gamma.get("vp", {}).get("vah") or 0.0)
            except Exception:
                vah_cached = 0.0
            try:
                val_cached = float(rec_gamma.get("val") or rec_gamma.get("vp", {}).get("val") or 0.0)
            except Exception:
                val_cached = 0.0
            try:
                vpoc_cached = float(rec_gamma.get("vpoc") or rec_gamma.get("vp", {}).get("vpoc") or 0.0)
            except Exception:
                vpoc_cached = 0.0

            for c, cnt in clusters:
                # proximité du prix courant
                if current_price and abs(c - current_price) <= eps:
                    reinforcement += cnt * 10
                # proximité HVL
                if hvl_val and abs(c - hvl_val) <= eps:
                    reinforcement += 15
                # proximité murs gamma
                if (cw and abs(c - cw) <= eps) or (pw and abs(c - pw) <= eps):
                    reinforcement += 20
                # proximité VVA (VAH/VAL/VPOC)
                if vah_cached and abs(c - vah_cached) <= eps:
                    reinforcement += 15
                if val_cached and abs(c - val_cached) <= eps:
                    reinforcement += 15
                if vpoc_cached and abs(c - vpoc_cached) <= eps:
                    reinforcement += 15
                # proximité PVWAP (VWAP session précédente)
                if pvwap_val and abs(c - pvwap_val) <= eps:
                    reinforcement += 10

            # Plafond global du reinforcement
            reinforcement = min(reinforcement, 100)

            # Calcul de confluence (0-100) inspiré des règles proposées
            def _round_quarter_tick(x: float) -> float:
                try:
                    t = float(tick) if float(tick) > 0 else 0.25
                    return round(round(float(x) / t) * t, 6)
                except Exception:
                    return x

            try:
                one_d_min = float(rec_gamma.get("1d_min", 0.0) or 0.0)
            except Exception:
                one_d_min = 0.0
            try:
                one_d_max = float(rec_gamma.get("1d_max", 0.0) or 0.0)
            except Exception:
                one_d_max = 0.0

            # Liste des aimants GEX disponibles
            gex_list: List[float] = []
            try:
                for k, v in rec_gamma.items():
                    if isinstance(k, str) and k.startswith("gex_") and v is not None:
                        try:
                            gex_list.append(float(v))
                        except Exception:
                            continue
            except Exception:
                gex_list = []

            # Nettoyage/arrondi niveaux (quart de tick) + dédup
            cleaned_levels = sorted(set([_round_quarter_tick(v) for v in blind_levels if isinstance(v, (int, float)) and v > 0]))

            def _near(x: float, y: float, tolerance: float) -> bool:
                try:
                    return abs(float(x) - float(y)) <= tolerance
                except Exception:
                    return False

            zone_scores: List[int] = []
            for b in cleaned_levels:
                s = 0
                if hvl_val and _near(b, hvl_val, eps):
                    s += 20
                if rec_gamma.get("hvl_0dte") and _near(b, float(rec_gamma.get("hvl_0dte", 0.0) or 0.0), eps):
                    s += 20
                if pw and _near(b, pw, eps):
                    s += 20
                if cw and _near(b, cw, eps):
                    s += 20
                if gex_list:
                    if any(_near(b, g, eps) for g in gex_list):
                        s += 10
                if one_d_min and _near(b, one_d_min, eps):
                    s += 10
                if one_d_max and _near(b, one_d_max, eps):
                    s += 10
                # Ajout confluence avec VVA (cache)
                if vah_cached and _near(b, vah_cached, eps):
                    s += 15
                if val_cached and _near(b, val_cached, eps):
                    s += 15
                if vpoc_cached and _near(b, vpoc_cached, eps):
                    s += 15
                # Ajout confluence avec PVWAP
                if pvwap_val and _near(b, pvwap_val, eps):
                    s += 10
                
                # Modulation par régime VIX (bonus net pas disproportionné)
                if vix_regime == "calm":
                    s = s * 0.9
                elif vix_regime == "elevated":
                    s = s * 1.1
                elif vix_regime == "high":
                    s = s * 1.2
                
                zone_scores.append(min(s, 50))  # cap par zone

            zone_scores.sort(reverse=True)
            confluence_score = min(sum(zone_scores[:2]), 100)

            blind = {
                "spots": cleaned_levels or blind_levels,
                "clusters": [{"center": c, "count": n} for (c, n) in clusters],
                "reinforcement_score": reinforcement,
                "confluence_score": confluence_score,
                # compat héritage
                "blind_spot_1": float(rec_gamma.get("blind_spot_1", 0.0) or 0.0),
                "blind_spot_2": float(rec_gamma.get("blind_spot_2", 0.0) or 0.0),
                "liquidity_gap": float(rec_gamma.get("liquidity_gap", 0.0) or 0.0),
                "dead_zone": float(rec_gamma.get("dead_zone", 0.0) or 0.0),
            }
            
            # ✅ VIX réel + régime
            vix = {"vix": float(vix_val), "regime": vix_regime}
            
            # ✅ ATR dans payload MenthorQ
            atr_block = {}
            try:
                a = rec_gamma.get("atr") or {}
                if isinstance(a, dict) and (a.get("points") or a.get("ticks")):
                    atr_block = {"points": float(a.get("points") or 0.0), "ticks": float(a.get("ticks") or 0.0)}
            except Exception:
                pass
            
            # ✅ Données basedata pour le payload
            basedata_block = {}
            try:
                # Lire depuis rec_gamma (données basedata réelles)
                if rec_gamma.get("open") and rec_gamma.get("close"):
                    basedata_block = {
                        "open": float(rec_gamma.get("open", 0.0)),
                        "high": float(rec_gamma.get("high", 0.0)),
                        "low": float(rec_gamma.get("low", 0.0)),
                        "close": float(rec_gamma.get("close", 0.0)),
                        "volume": int(rec_gamma.get("volume", 0)),
                        "bidvol": int(rec_gamma.get("bidvol", 0)),
                        "askvol": int(rec_gamma.get("askvol", 0)),
                        "cum_delta_session": float(rec_gamma.get("cum_delta_session", 0.0)),
                        "session_id": rec_gamma.get("session_id", "US")
                    }
            except Exception:
                pass
            
            # ✅ Données de trading pour le payload
            trade_block = {}
            try:
                if rec_gamma.get("buy_trades") or rec_gamma.get("sell_trades"):
                    trade_block = {
                        "buy_trades": int(rec_gamma.get("buy_trades", 0)),
                        "sell_trades": int(rec_gamma.get("sell_trades", 0)),
                        "buy_vol": int(rec_gamma.get("buy_vol", 0)),
                        "sell_vol": int(rec_gamma.get("sell_vol", 0)),
                        "cum_delta_session": float(rec_gamma.get("cum_delta_session", 0.0)),
                        "cum_delta_day": float(rec_gamma.get("cum_delta_day", 0.0))
                    }
                
                # Ajouter le dernier trade si disponible
                if rec_gamma.get("last_trade_price"):
                    trade_block["last_trade"] = {
                        "price": float(rec_gamma.get("last_trade_price", 0.0)),
                        "size": int(rec_gamma.get("last_trade_size", 0)),
                        "side": rec_gamma.get("last_trade_side", "")
                    }
            except Exception:
                pass
            
            # ✅ Données DOM pour le payload (avec quote seq)
            dom_block = {}
            try:
                if rec_gamma.get("best_bid") and rec_gamma.get("best_ask"):
                    dom_block = {
                        "best_bid": float(rec_gamma.get("best_bid", 0.0)),
                        "best_ask": float(rec_gamma.get("best_ask", 0.0)),
                        "bid_size": int(rec_gamma.get("bid_size", 0)),
                        "ask_size": int(rec_gamma.get("ask_size", 0)),
                        "spread": float(rec_gamma.get("spread", 0.0)),
                        "quote_seq": int(rec_gamma.get("quote_seq", 0)),
                        "depth_levels": int(rec_gamma.get("depth_levels", 0)),
                        "depth_imbalance": float(rec_gamma.get("depth_imbalance", 0.0))
                    }
                
                # Ajouter les données DOM complètes si disponibles
                if rec_gamma.get("dom"):
                    dom_block["dom"] = rec_gamma.get("dom")
            except Exception:
                pass
            
            # ✅ Données NBCV pour le payload
            nbcv_block = {}
            try:
                if rec_gamma.get("nbcv"):
                    nbcv_data = rec_gamma.get("nbcv", {})
                    nbcv_block = {
                        "ask_volume": int(nbcv_data.get("ask_volume", 0)),
                        "bid_volume": int(nbcv_data.get("bid_volume", 0)),
                        "delta": int(nbcv_data.get("delta", 0)),
                        "trades": int(nbcv_data.get("trades", 0)),
                        "cumulative_delta": int(nbcv_data.get("cumulative_delta", 0)),
                        "total_volume": int(nbcv_data.get("total_volume", 0)),
                        "delta_ratio": float(nbcv_data.get("delta_ratio", 0.0)),
                        "ask_percent": float(nbcv_data.get("ask_percent", 0.0)),
                        "bid_percent": float(nbcv_data.get("bid_percent", 0.0)),
                        "bid_ask_ratio": float(nbcv_data.get("bid_ask_ratio", 0.0)),
                        "ask_bid_ratio": float(nbcv_data.get("ask_bid_ratio", 0.0)),
                        "pressure_bullish": float(nbcv_data.get("pressure_bullish", 0.0)),
                        "pressure_bearish": float(nbcv_data.get("pressure_bearish", 0.0)),
                        "pressure": float(nbcv_data.get("pressure", 0.0)),
                        "pressure_smooth": float(nbcv_data.get("pressure_smooth", 0.0)),
                        "volume_imbalance": float(nbcv_data.get("volume_imbalance", 0.0)),
                        "volume_ratio": float(nbcv_data.get("volume_ratio", 0.0))
                    }
            except Exception:
                pass
            
            # ✅ Données de corrélation pour le payload
            correlation_block = {}
            try:
                if rec_gamma.get("correlation"):
                    corr_data = rec_gamma.get("correlation", {})
                    correlation_block = {
                        "cc": float(corr_data.get("cc", 0.0)),
                        "study_period": int(corr_data.get("study_period", 50)),
                        "signal_generated": int(corr_data.get("signal_generated", 0)),
                        "strength": corr_data.get("strength", "weak"),
                        "direction": corr_data.get("direction", "neutral"),
                        "timestamp": float(corr_data.get("timestamp", 0.0))
                    }
            except Exception:
                pass
            
            # ✅ Données cumulative delta pour le payload
            cum_delta_block = {}
            try:
                cum_delta_data = rec_gamma.get("cumulative_delta", {})
                if cum_delta_data:
                    cum_delta_block = {
                        "study_value": float(cum_delta_data.get("study_value", 0.0)),
                        "study_period": int(cum_delta_data.get("study_period", 32)),
                        "signal_generated": int(cum_delta_data.get("signal_generated", 0)),
                        "cum_delta_day": float(cum_delta_data.get("cum_delta_day", 0.0)),
                        "cum_delta_session": float(cum_delta_data.get("cum_delta_session", 0.0)),
                        "session_id": cum_delta_data.get("session_id", "US"),
                        "source": cum_delta_data.get("source", "unknown"),
                        "timestamp": int(time.time())
                    }
            except Exception:
                pass
            
            payload = {
                "gamma": gamma,
                "blind_spots": blind,
                "dealers_bias": dealers,
                "vwap": {
                    "vwap": vwap_val, 
                    "up1": up1, "dn1": dn1, 
                    "up2": up2, "dn2": dn2, 
                    "up3": up3, "dn3": dn3, 
                    "slope": slope
                },
                "pvwap": {"pvwap": pvwap_val, "up1": pvwap_up1, "dn1": pvwap_dn1, "up2": pvwap_up2, "dn2": pvwap_dn2},
                "vol": {"atr": atr_block} if atr_block else {},
                "vix": vix,
                "basedata": basedata_block if basedata_block else {},
                "trading": trade_block if trade_block else {},
                "dom": dom_block if dom_block else {},
                "nbcv": nbcv_block if nbcv_block else {},
                "correlation": correlation_block if correlation_block else {},
                "cumulative_delta": cum_delta_block if cum_delta_block else {},
            }
            
            # Logging enrichi avec basedata et trading
            basedata_info = ""
            if basedata_block:
                basedata_info = f", OHLC={basedata_block.get('open')}/{basedata_block.get('high')}/{basedata_block.get('low')}/{basedata_block.get('close')}, vol={basedata_block.get('volume')}, delta={basedata_block.get('cum_delta_session')}"
            
            trading_info = ""
            if trade_block:
                trading_info = f", trades={trade_block.get('buy_trades')}/{trade_block.get('sell_trades')}, vol={trade_block.get('buy_vol')}/{trade_block.get('sell_vol')}"
                if trade_block.get("last_trade"):
                    lt = trade_block["last_trade"]
                    trading_info += f", last={lt.get('side')} {lt.get('size')}@{lt.get('price')}"
            
            dom_info = ""
            if dom_block:
                quote_seq = dom_block.get('quote_seq', 0)
                dom_info = f", bid={dom_block.get('best_bid')}@{dom_block.get('bid_size')}, ask={dom_block.get('best_ask')}@{dom_block.get('ask_size')}, spread={dom_block.get('spread')}, seq={quote_seq}, levels={dom_block.get('depth_levels')}"
            
            nbcv_info = ""
            if nbcv_block:
                pressure_smooth = nbcv_block.get('pressure_smooth', 0.0)
                nbcv_info = f", NBCV: ask_vol={nbcv_block.get('ask_volume')}, bid_vol={nbcv_block.get('bid_volume')}, delta={nbcv_block.get('delta')}, trades={nbcv_block.get('trades')}, cum_delta={nbcv_block.get('cumulative_delta')}, pressure={nbcv_block.get('pressure', 0.0):.3f}, smooth={pressure_smooth:.3f}"
            
            correlation_info = ""
            if correlation_block:
                correlation_info = f", CORR: cc={correlation_block.get('cc', 0.0):.4f}, strength={correlation_block.get('strength')}, direction={correlation_block.get('direction')}"
            
            cum_delta_info = ""
            if cum_delta_block:
                cum_delta_info = f", CUM_DELTA: study={cum_delta_block.get('study_value', 0.0):.1f}, day={cum_delta_block.get('cum_delta_day', 0.0):.1f}, session={cum_delta_block.get('cum_delta_session', 0.0):.1f}, source={cum_delta_block.get('source')}"
            
            logger.debug(f"🎯 Payload MenthorQ construit: gamma_max={gamma['gamma_max']}, call_wall={gamma['call_wall']}, put_wall={gamma['put_wall']}, vwap={vwap_val}{basedata_info}{trading_info}{dom_info}{nbcv_info}{correlation_info}{cum_delta_info}")
            return payload
            
        except Exception as e:
            logger.error(f"❌ Erreur construction payload MenthorQ: {e}")
            # Fallback minimal
            return {
                "gamma": {"gamma_max": 0.0, "call_wall": 0.0, "put_wall": 0.0, "zero_gamma": current_price, "gamma_flip": False, "flip_price": current_price, "flip_age_minutes": 0},
                "blind_spots": {"blind_spot_1": 0.0, "blind_spot_2": 0.0, "liquidity_gap": 0.0, "dead_zone": 0.0},
                "dealers_bias": {"bias_score": 0.0, "bias_strength": 0.0, "bias_confidence": 0.0},
                "vwap": {"vwap": current_price, "up1": current_price + 1.25, "dn1": current_price - 1.25, "slope": 0.0},
                "vix": {"vix": 18.5}
            }

    def to_menthorq_payload(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convertir un snapshot legacy vers le payload MenthorQ Elite
        
        Args:
            snapshot: Snapshot au format legacy
            
        Returns:
            Payload MenthorQ Elite correctement formaté
        """
        try:
            # ✅ Utiliser le nouveau mapping gamma si les données JSONL sont présentes
            current_price = snapshot.get("last", 0.0)
            
            # Vérifier si on a des données MenthorQ JSONL (gex_*, hvl, etc.)
            has_jsonl_data = any(k.startswith("gex_") or k in ["hvl", "hvl_0dte", "call_resistance", "call_resistance_0dte", "put_support", "put_support_0dte", "1d_min", "1d_max", "gamma_wall_0dte"] for k in snapshot.keys())
            logger.info(f"🔍 Détection JSONL: {has_jsonl_data}, clés disponibles: {[k for k in snapshot.keys() if k.startswith('gex_') or k in ['hvl', 'hvl_0dte', 'call_resistance', 'call_resistance_0dte', 'put_support', 'put_support_0dte']]}")
            
            # 🆕 Si JSONL présent → utiliser le builder complet (inclut clusters + score)
            if has_jsonl_data:
                return self.build_menthorq_payload(snapshot, current_price)

            else:
                # ✅ Fallback vers l'ancien mapping
                gamma_src = snapshot.get("mentorq_gamma", {}) or {}
                levels = gamma_src.get("levels") or []
                gamma_max = (max([l.get("gamma", 0) for l in levels if isinstance(l, dict)]) if levels else gamma_src.get("gamma_max", 0.0))
                
                gamma_data = {
                    "gamma_max": float(gamma_max or 0.0),
                    "call_wall": float(gamma_src.get("call_wall", 0.0) or 0.0),
                    "put_wall": float(gamma_src.get("put_wall", 0.0) or 0.0),
                    "zero_gamma": float(gamma_src.get("zero_gamma", current_price) or current_price),
                    "gamma_flip": bool(gamma_src.get("gamma_flip", False)),
                    "flip_price": float(gamma_src.get("flip_price", 0.0) or 0.0),
                    "flip_age_minutes": int(gamma_src.get("flip_age_minutes", 0) or 0),
                }
            
            # Autres composants (blind_spots, dealers_bias, vwap, vix)
            blind_src = snapshot.get("mentorq_blind", {}) or {}
            vwap_src = snapshot.get("vwap", {}) or {}
            vix_val = snapshot.get("vix", 0.0)
            
            return {
                "gamma": gamma_data,
                "blind_spots": {
                    "blind_spot_1": float(blind_src.get("spot_1", 0.0) or 0.0),
                    "blind_spot_2": float(blind_src.get("spot_2", 0.0) or 0.0),
                    "liquidity_gap": float(blind_src.get("liquidity_gap", 0.0) or 0.0),
                    "dead_zone": float(blind_src.get("dead_zone", 0.0) or 0.0),
                },
                "dealers_bias": {
                    "bias_score": float(snapshot.get("dealers_bias", {}).get("bias_score", 0.0) or 0.0),
                    "bias_strength": float(snapshot.get("dealers_bias", {}).get("bias_strength", 0.0) or 0.0),
                    "bias_confidence": float(snapshot.get("dealers_bias", {}).get("bias_confidence", 0.0) or 0.0),
                },
                "vwap": {
                    "vwap": float(vwap_src.get("value", 0.0) or 0.0),
                    "up1": float(vwap_src.get("upper_band", 0.0) or 0.0),
                    "dn1": float(vwap_src.get("lower_band", 0.0) or 0.0),
                    "slope": float(vwap_src.get("slope", 0.0) or 0.0),
                },
                "vix": {"vix": float(vix_val or 0.0)},
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur conversion payload MenthorQ: {e}")
            return {
                "gamma": {"gamma_max": 0.0, "call_wall": 0.0, "put_wall": 0.0, "zero_gamma": 0.0, "gamma_flip": False, "flip_price": 0.0, "flip_age_minutes": 0},
                "blind_spots": {"blind_spot_1": 0.0, "blind_spot_2": 0.0, "liquidity_gap": 0.0, "dead_zone": 0.0},
                "dealers_bias": {"bias_score": 0.0, "bias_strength": 0.0, "bias_confidence": 0.0},
                "vwap": {"vwap": 0.0, "up1": 0.0, "dn1": 0.0, "slope": 0.0},
                "vix": {"vix": 20.0}
            }

# Fonction d'export
def adapt_legacy_snapshot(legacy_snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fonction d'export pour adapter un snapshot legacy
    
    Args:
        legacy_snapshot: Snapshot au format legacy
        
    Returns:
        Snapshot adapté pour les méthodes Elite
    """
    adapter = LegacyAdapter()
    return adapter.adapt_snapshot_for_elite(legacy_snapshot)

# Test rapide
if __name__ == "__main__":
    print("🧪 Test Legacy Adapter...")
    
    # Test snapshot legacy
    legacy_snapshot = {
        "sym": "ESZ25_FUT_CME",
        "t": int(time.time()),
        "last": 4150.25,
        "phase": "REGULAR",
        "regime": "TREND",
        "vix": 18.5,
        "mentorq_gamma": {"levels": [], "call_wall": 4155.0, "put_wall": 4145.0},
        "mentorq_blind": {"spots": [], "spot_1": 4152.0, "spot_2": 4148.0},
        "vwap": {"value": 4150.0, "upper_band": 4155.0, "lower_band": 4145.0},
        "vp": {"vpoc": 4150.0, "val": 4145.0, "vah": 4155.0},
        "ofdom": {"best_bid": 4150.0, "best_ask": 4150.25, "spread": 0.25},
        "lead": {"nq_stronger_than_es": False, "sync_ok": True},
        "mia_score": 0.75,
        "mia_state": "BULLISH"
    }
    
    # Test adaptation
    adapter = LegacyAdapter()
    elite_snapshot = adapter.adapt_snapshot_for_elite(legacy_snapshot)
    
    print(f"✅ Snapshot adapté: {elite_snapshot['sym']} @ {elite_snapshot['last']}")
    print(f"📊 Stats: {adapter.get_mapping_stats()}")
