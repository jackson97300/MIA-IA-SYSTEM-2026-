
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MIA Unified Stream Builder (enhanced)
-------------------------------------
Lit les fichiers JSONL spécialisés par chart/type (ex: chart_3_basedata_YYYYMMDD.jsonl)
et produit un flux unifié JSONL par buckets de temps.

Types supportés:
- basedata, vwap, vva, pvwap, vix, quote, trade, depth, nbcv, menthorq
- atr, cumulative_delta, correlation (nouveaux)
- menthorq_gamma, menthorq_blind_spots, correlation_unified (Chart 3 v2.1)

Ajouts:
- --menthorq-filter : applique un filtre optionnel (config.menthorq_runtime.should_emit_level)
- --only vwap,vva,atr,... : sélectionne uniquement certains blocs dans la sortie
- --gzip : écrit la sortie compressée (.gz)

Usage:
  python mia_unifier.py --indir "D:\\MIA_IA_system" --date today --tol 0.2 --gzip --only vwap,vva,atr
"""

import os, sys, json, glob, math, argparse, datetime, gzip, importlib, time
from collections import defaultdict
import calendar

SUPPORTED_ONLY = {"basedata","vwap","vva","pvwap","vix","quote","trade","depth","nbcv","menthorq","extra","atr","cumulative_delta","correlation","menthorq_gamma","menthorq_blind_spots","correlation_unified"}

# === CALCULATEUR CUMULATIVE DELTA INTERNE ===
class CumulativeDeltaCalculator:
    """
    Calculateur de Cumulative Delta interne pour corriger les valeurs erronées de Sierra Chart.
    
    Problème identifié : Sierra Chart avec configuration Tick Reversal produit des valeurs
    incohérentes de Cumulative Delta. Ce calculateur utilise les données NBCV fiables
    pour recalculer le Cumulative Delta correctement.
    """
    
    def __init__(self, reset_mode="daily"):
        self.reset_mode = reset_mode
        self.cumulative_delta = 0.0
        self.last_reset_date = None
        self.initialized = False
        
    def should_reset(self, timestamp):
        """Vérifier si on doit faire un reset (quotidien à 00:00)"""
        if self.reset_mode == "daily":
            # Convertir timestamp en date
            try:
                current_date = datetime.datetime.fromtimestamp(timestamp).date()
                if self.last_reset_date != current_date:
                    self.last_reset_date = current_date
                    return True
            except (ValueError, OSError):
                # Si conversion échoue, pas de reset
                pass
        return False
    
    def calculate_delta_from_nbcv(self, unified_line):
        """Calculer le delta à partir des données NBCV (utilise la dernière entrée)"""
        extra = unified_line.get("extra", [])
        
        # Trouver la dernière entrée NBCV (la plus récente)
        last_nbcv = None
        for nbcv in extra:
            if nbcv.get("type") == "nbcv":
                last_nbcv = nbcv
        
        if last_nbcv:
            ask_volume = last_nbcv.get("ask_volume", 0)
            bid_volume = last_nbcv.get("bid_volume", 0)
            delta = ask_volume - bid_volume
            return delta
        
        # Si pas de données NBCV, retourner 0
        return 0.0
    
    def update(self, unified_line):
        """Mettre à jour le cumulative delta et retourner les nouvelles valeurs"""
        # Vérifier reset quotidien
        if self.should_reset(unified_line["t"]):
            self.cumulative_delta = 0.0
            self.initialized = False
        
        # Calculer le delta de cette minute
        current_delta = self.calculate_delta_from_nbcv(unified_line)
        
        # Si pas encore initialisé, synchroniser avec la valeur Sierra Chart existante
        if not self.initialized and unified_line.get("cumulative_delta"):
            sierra_value = unified_line["cumulative_delta"].get("close", 0)
            if sierra_value != 0:
                self.cumulative_delta = sierra_value
                self.initialized = True
        
        # Mettre à jour le cumulative
        self.cumulative_delta += current_delta
        
        return {
            "close": self.cumulative_delta,  # Valeur cumulative depuis 00:00
            "delta": current_delta           # Delta de cette minute
        }

# Instance globale du calculateur
cumulative_delta_calc = CumulativeDeltaCalculator("daily")

def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--indir", type=str, required=True, help="Dossier d'entrée (ex: D:\\MIA_IA_system)")
    ap.add_argument("--date", type=str, default="today", help="YYYYMMDD ou 'today' (heure locale machine)")
    ap.add_argument("--out", type=str, default=None, help="Fichier de sortie JSONL (sinon: organisé sous CHART_<id>)")
    ap.add_argument("--chart", type=str, default=None, help="Filtrer et écrire pour un chart précis (ex: 3, 9)")
    ap.add_argument("--symbol", type=str, default=None, help="Filtrer les enregistrements par symbole (préfixe, ex: ES, NQ)")
    ap.add_argument("--tol", type=float, default=0.2, help="Tolérance de bucket (secondes, défaut 0.2)")
    ap.add_argument("--max_depth_levels", type=int, default=20, help="Max niveaux DOM par côté (défaut 20)")
    ap.add_argument("--menthorq-filter", action="store_true", help="Activer le filtre MenthorQ si disponible")
    ap.add_argument("--only", type=str, default=None, help="Liste séparée par virgules de sections à inclure (ex: vwap,vva,vix). Par défaut: tout")
    ap.add_argument("--gzip", action="store_true", help="Écrire en gzip (.gz)")
    # Mode append/stream (n'écrase pas, ajoute uniquement les nouveaux buckets)
    ap.add_argument("--append-stream", action="store_true", help="Mode append/stream: ajoute seulement les nouveaux buckets à la fin du fichier")
    ap.add_argument("--rollover-minutes", type=int, default=0, help="Crée un nouveau fichier toutes les N minutes (ex: 60 → unified_YYYYMMDD_HH.jsonl)")
    ap.add_argument("--watch-seconds", type=float, default=0.0, help="Relance l’unification toutes les N secondes (active append-stream)")
    ap.add_argument("--minute-mode", action="store_true", help="Mode M1 strict: force l’agrégation à 1 minute (tol=60.0)")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--tick-size", type=float, default=0.25, help="Taille de tick (ex: 0.25 pour ES)")
    
    # === NOUVEAUX ARGUMENTS CLUSTER ALERTS ===
    ap.add_argument("--pg-distance", type=float, default=2.5, help="Distance max (points ES) au niveau pour pré-gating (défaut 2.5)")
    ap.add_argument("--touch-thr", type=float, default=1.0, help="Seuil (ticks) pour considérer un 'touch' (défaut 1.0)")
    ap.add_argument("--zone-cooldown", type=int, default=300, help="Cooldown par zone (secondes) après une alerte (défaut 300)")
    ap.add_argument("--ttl-seconds", type=int, default=900, help="Durée de validité d'un niveau MenthorQ (défaut 900=15min)")
    ap.add_argument("--menthorq-decisions", action="store_true", help="Activer MenthorQDecisionEngine")
    ap.add_argument("--mia-optimal", action="store_true", help="Activer scoring MIA Optimal v2.1")
    ap.add_argument("--correlation-ttl-seconds", type=int, default=120, help="TTL (secondes) pour conserver la dernière corrélation si absente")
    ap.add_argument("--rollover-bytes", type=int, default=0, help="Bascule le fichier si sa taille dépasse N octets (ex: 134217728 pour 128MB)")
    ap.add_argument("--timezone-offset", type=float, default=0.0, help="Décalage de fuseau horaire en heures (ex: -6 pour France->NY, +6 pour NY->France)")
    
    return ap.parse_args()

def resolve_date(s: str) -> str:
    if s.lower() == "today":
        return datetime.datetime.now().strftime("%Y%m%d")
    return s

def get_month_name(month_num: str) -> str:
    """Convertit le numéro de mois en nom français"""
    month_names = {
        "01": "JANVIER", "02": "FEVRIER", "03": "MARS", "04": "AVRIL",
        "05": "MAI", "06": "JUIN", "07": "JUILLET", "08": "AOUT",
        "09": "SEPTEMBRE", "10": "OCTOBRE", "11": "NOVEMBRE", "12": "DECEMBRE"
    }
    return month_names.get(month_num, "INCONNU")

def get_organized_data_path(base_dir: str, ymd: str) -> str:
    """Génère le chemin organisé pour les données"""
    year = ymd[:4]
    month_num = ymd[4:6]
    month_name = get_month_name(month_num)
    
    return os.path.join(base_dir, "DATA_SIERRA_CHART", f"DATA_{year}", month_name, ymd)

def _read_last_unified_ts(out_path: str) -> float:
    """Lit le dernier timestamp 't' écrit dans le fichier unified (jsonl). Retourne 0.0 si inconnu.
    Lecture en arrière à partir de la fin pour trouver la dernière ligne non vide/valide.
    """
    try:
        if not os.path.exists(out_path) or os.path.getsize(out_path) == 0:
            return 0.0
        # Lire les dernières ~64KB pour trouver une ligne complète
        with open(out_path, "rb") as f:
            size = f.seek(0, os.SEEK_END)
            read_size = min(65536, size)
            f.seek(-read_size, os.SEEK_END)
            chunk = f.read(read_size)
        # Découper par lignes et parser en sens inverse
        lines = chunk.decode("utf-8", errors="ignore").splitlines()
        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                t = obj.get("t")
                if isinstance(t, (int, float)):
                    return float(t)
            except Exception:
                continue
        return 0.0
    except Exception:
        return 0.0

def ensure_directory_exists(path: str) -> None:
    """Crée le répertoire s'il n'existe pas"""
    try:
        os.makedirs(path, exist_ok=True)
        print(f"[OK] Répertoire créé/vérifié: {path}")
    except Exception as e:
        print(f"[ERREUR] Erreur création répertoire {path}: {e}")
        raise

def iter_jsonl(path):
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except Exception:
                continue

def list_inputs(indir: str, yyyymmdd: str, chart: str | None = None):
    """Liste les fichiers d'entrée dans la nouvelle structure organisée"""
    # Chemin organisé
    organized_path = get_organized_data_path(indir, yyyymmdd)
    
    # Patterns avec la nouvelle structure
    chart_id = str(chart) if chart is not None else "3"
    chart_dir = os.path.join(organized_path, f"CHART_{chart_id}")

    patterns = [
        os.path.join(chart_dir, f"chart_{chart_id}_basedata_{yyyymmdd}.jsonl"),
        os.path.join(chart_dir, f"chart_{chart_id}_trade_{yyyymmdd}.jsonl"),
        os.path.join(chart_dir, f"chart_{chart_id}_quote_{yyyymmdd}.jsonl"),
        os.path.join(chart_dir, f"chart_{chart_id}_depth_{yyyymmdd}.jsonl"),
        os.path.join(chart_dir, f"chart_{chart_id}_nbcv_{yyyymmdd}.jsonl"),
        os.path.join(chart_dir, f"chart_{chart_id}_vwap_{yyyymmdd}.jsonl"),
        os.path.join(chart_dir, f"chart_{chart_id}_vva_{yyyymmdd}.jsonl"),
        os.path.join(chart_dir, f"chart_{chart_id}_pvwap_{yyyymmdd}.jsonl"),
        os.path.join(chart_dir, f"chart_{chart_id}_atr_{yyyymmdd}.jsonl"),
        os.path.join(chart_dir, f"chart_{chart_id}_cumulative_delta_{yyyymmdd}.jsonl"),
        os.path.join(chart_dir, f"chart_{chart_id}_vix_{yyyymmdd}.jsonl"),
        # Nouveaux
        os.path.join(chart_dir, f"chart_{chart_id}_menthorq_gamma_{yyyymmdd}.jsonl"),
        os.path.join(chart_dir, f"chart_{chart_id}_menthorq_blind_spots_{yyyymmdd}.jsonl"),
        os.path.join(chart_dir, f"chart_{chart_id}_correlation_unified_{yyyymmdd}.jsonl"),
        os.path.join(chart_dir, f"chart_{chart_id}_correlation_{yyyymmdd}.jsonl"),
    ]

    # VIX depuis CHART_8 (optionnel si exporté là)
    vix_c8 = os.path.join(organized_path, "CHART_8", f"chart_8_vix_{yyyymmdd}.jsonl")
    if os.path.exists(vix_c8):
        paths.append(vix_c8)
    
    paths = []
    for p in patterns:
        if os.path.exists(p):
            paths.append(p)
        else:
            # Fallback: chercher dans l'ancienne structure (racine)
            fallback_pattern = os.path.basename(p)
            fallback_path = os.path.join(indir, fallback_pattern)
            if os.path.exists(fallback_path):
                paths.append(fallback_path)
                print(f"[INFO] Utilisation fallback: {fallback_path}")
    
    # Si aucun fichier trouvé, essayer l'ancienne méthode
    if not paths:
        pat = os.path.join(indir, f"chart_*_{yyyymmdd}.jsonl")
        paths = sorted(glob.glob(pat))
        if paths:
            print(f"[INFO] Utilisation ancienne structure: {len(paths)} fichiers trouvés")
    
    return paths

def bucket_key(t_float: float, tol: float) -> float:
    secs = t_float * 86400.0
    return round(secs / tol) * tol

def ensure_vva_sanity(vva: dict):
    vah = vva.get("vah")
    vpoc = vva.get("vpoc")
    val = vva.get("val")
    if all(isinstance(x, (int, float)) and x > 0 for x in [vah, vpoc, val]):
        ordered = sorted([vah, vpoc, val], reverse=True)
        if [vah, vpoc, val] != ordered:
            vva["vah"], vva["vpoc"], vva["val"] = ordered
    return vva

def ensure_vwap_bands_sanity(vwap: dict):
    v = vwap.get("v")
    for k_up, k_dn in [("up1","dn1"), ("up2","dn2"), ("up3","dn3")]:
        up = vwap.get(k_up); dn = vwap.get(k_dn)
        if up is None or dn is None:
            continue
        if up < dn:
            vwap[k_up], vwap[k_dn] = dn, up
    return vwap

def load_menthorq_filter(enabled: bool):
    if not enabled:
        return None
    try:
        mod = importlib.import_module("config.menthorq_runtime")
        fn = getattr(mod, "should_emit_level", None)
        return fn
    except Exception:
        return None

def apply_menthorq_filter(levels, fn):
    if fn is None:
        return levels
    out = []
    for obj in levels:
        try:
            price = obj.get("price")
            symbol = obj.get("sym") or obj.get("symbol") or "ES"
            # 'kind' n'est pas explicite ici; on transmet 'level' + sg si utile
            ok = fn(symbol=symbol, price=price, sg=obj.get("sg"), raw=obj)
            if ok:
                out.append(obj)
        except Exception:
            # En cas d'erreur de filtre, fallback: conserver l'élément
            out.append(obj)
    return out

# === GESTION TTL ET COOLDOWN ===

# État global pour TTL et cooldown
ttl_map = {}  # key: level_id → expires_at
zone_cooldown = {}  # key: zone_key → rearm_at

def apply_ttl(levels, now, ttl_seconds):
    """Applique le TTL aux niveaux MenthorQ"""
    kept = []
    for level in levels:
        lid = level.get("id") or f"{level.get('level_type', 'unknown')}@{level.get('price', 0)}"
        exp = ttl_map.get(lid)
        if not exp or now <= exp:
            kept.append(level)
            ttl_map[lid] = now + ttl_seconds
    return kept

def can_fire(zone_key, now):
    """Vérifie si une zone peut émettre une alerte (pas en cooldown)"""
    return now >= zone_cooldown.get(zone_key, 0)

def arm_zone(zone_key, now, cooldown):
    """Arme le cooldown pour une zone"""
    zone_cooldown[zone_key] = now + cooldown

def distance_ticks(price, level_price, tick_size=0.25):
    """Calcule la distance en ticks entre deux prix"""
    return abs(price - level_price) / tick_size

def pre_gating_ok(last_price, levels, pg_distance_points, tick_size=0.25):
    """Vérifie si le prix est assez proche d'un niveau pour le pré-gating"""
    for level in levels:
        if abs(last_price - level.get("price", 0)) <= pg_distance_points:
            return True
    return False

def is_touch(last_price, zone_min, zone_max, touch_thr_ticks, tick_size=0.25):
    """Vérifie si le prix touche une zone (dans le seuil)"""
    d_min = abs(last_price - zone_min) / tick_size
    d_max = abs(last_price - zone_max) / tick_size
    return min(d_min, d_max) <= touch_thr_ticks

def zone_key(zone_min, zone_max, level_type="cluster"):
    """Génère une clé unique pour une zone"""
    return f"{level_type}:{zone_min:.2f}-{zone_max:.2f}"

def mia_optimal(last_price, vwap, orderflow, vix, dealers_bias=None):
    """
    Calcule le score MIA Optimal v2.1 (stub simplifié)
    
    Args:
        last_price: Prix actuel
        vwap: VWAP
        orderflow: Données OrderFlow
        vix: Valeur VIX
        dealers_bias: Biais des dealers (optionnel)
        
    Returns:
        Dict avec score et side
    """
    try:
        bias = 0.0
        
        # VWAP bias
        if vwap and last_price > vwap:
            bias += 0.4
        elif vwap and last_price < vwap:
            bias -= 0.4
        
        # OrderFlow bias
        if orderflow and orderflow.get("delta", 0) > 0:
            bias += 0.3
        elif orderflow and orderflow.get("delta", 0) < 0:
            bias -= 0.3
        
        # Dealers bias
        if dealers_bias and dealers_bias > 0:
            bias += 0.3
        elif dealers_bias and dealers_bias < 0:
            bias -= 0.3
        
        # VIX adjustment
        if vix:
            if vix > 28:  # Volatilité élevée
                bias *= 0.8  # Réduire la confiance
            elif vix < 15:  # Volatilité faible
                bias *= 1.2  # Augmenter la confiance
        
        # Normaliser le score
        score = max(-1.0, min(1.0, bias))
        
        # Déterminer le côté
        if score >= 0.25:
            side = "LONG"
        elif score <= -0.25:
            side = "SHORT"
        else:
            side = "FLAT"
        
        return {
            "score": round(score, 3),
            "side": side,
            "components": {
                "vwap_bias": 0.4 if vwap and last_price > vwap else (-0.4 if vwap and last_price < vwap else 0),
                "orderflow_bias": 0.3 if orderflow and orderflow.get("delta", 0) > 0 else (-0.3 if orderflow and orderflow.get("delta", 0) < 0 else 0),
                "dealers_bias": 0.3 if dealers_bias and dealers_bias > 0 else (-0.3 if dealers_bias and dealers_bias < 0 else 0),
                "vix_adjustment": 0.8 if vix and vix > 28 else (1.2 if vix and vix < 15 else 1.0)
            }
        }
        
    except Exception as e:
        return {
            "score": 0.0,
            "side": "FLAT",
            "error": str(e)
        }

def compute_cluster_alerts(levels, current_price, tick_size=0.25, confluence_thr=3.0, cluster_thr=3.0, 
                          pg_distance=2.5, touch_thr=1.0, zone_cooldown_sec=300, ttl_sec=900, 
                          enable_menthorq_decisions=False, enable_mia_optimal=False, 
                          vwap=None, orderflow=None, vix=None):
    """
    Calcule les cluster alerts depuis les niveaux MenthorQ avec pré-gating et cooldown
    
    Args:
        levels: Liste des niveaux MenthorQ
        current_price: Prix actuel
        tick_size: Taille du tick (défaut 0.25 pour ES)
        confluence_thr: Seuil confluence en ticks (défaut 3.0)
        cluster_thr: Seuil cluster en ticks (défaut 3.0)
        pg_distance: Distance max pour pré-gating (points ES)
        touch_thr: Seuil touch en ticks
        zone_cooldown_sec: Cooldown par zone en secondes
        ttl_sec: TTL des niveaux en secondes
        enable_menthorq_decisions: Activer MenthorQDecisionEngine
        enable_mia_optimal: Activer MIA Optimal
        vwap: VWAP pour MIA Optimal
        orderflow: OrderFlow pour MIA Optimal
        vix: VIX pour MIA Optimal
        
    Returns:
        Dict avec les alerts cluster enrichies ou None
    """
    if not levels or current_price is None:
        return None
    
    try:
        now = time.time()
        
        # === 1. APPLIQUER TTL ===
        levels_with_ttl = apply_ttl(levels, now, ttl_sec)
        
        # === 2. PRÉ-GATING ===
        pre_gating_result = pre_gating_ok(current_price, levels_with_ttl, pg_distance, tick_size)
        
        if not pre_gating_result:
            return {
                "pre_gating": {"ok": False, "pg_distance": pg_distance, "reason": "TOO_FAR_FROM_LEVELS"},
                "ttl": {"levels_kept": len(levels_with_ttl), "ttl_seconds": ttl_sec}
            }
        
        # === 3. CONFLUENCE GAMMA + BLIND ===
        confluence = compute_confluence(levels_with_ttl, current_price, confluence_thr, tick_size)
        
        # === 4. CLUSTERS ===
        clusters = compute_clusters(levels_with_ttl, current_price, cluster_thr, tick_size)
        
        # === 5. MENTHORQ ALERTS AVEC COOLDOWN ===
        menthorq_alerts = []
        armed_zones = []
        
        for cluster in clusters:
            zone_key_str = zone_key(cluster["zone_min"], cluster["zone_max"], "cluster")
            
            # Vérifier cooldown
            if not can_fire(zone_key_str, now):
                continue
            
            # Déterminer le type d'alerte
            kind = "NEAR" if is_touch(current_price, cluster["zone_min"], cluster["zone_max"], touch_thr, tick_size) else "WATCH"
            
            alert = {
                "zone_min": cluster["zone_min"],
                "zone_max": cluster["zone_max"],
                "center": cluster["center"],
                "score": cluster["score"],
                "kind": kind,
                "groups": cluster["groups"],
                "count": cluster["count"],
                "width_ticks": cluster["width_ticks"]
            }
            
            menthorq_alerts.append(alert)
            armed_zones.append(zone_key_str)
            
            # Armer le cooldown si c'est un touch
            if kind == "NEAR":
                arm_zone(zone_key_str, now, zone_cooldown_sec)
        
        # === 6. SUMMARY ===
        summary = compute_summary(clusters, current_price, tick_size)
        
        # === 7. MIA OPTIMAL ===
        mia_result = None
        if enable_mia_optimal:
            mia_result = mia_optimal(current_price, vwap, orderflow, vix)
        
        # === 8. RÉSULTAT ENRICHI ===
        result = {
            "pre_gating": {"ok": True, "pg_distance": pg_distance, "reason": "NEAR_LEVEL"},
            "menthorq_alerts": menthorq_alerts,
            "ttl": {"levels_kept": len(levels_with_ttl), "ttl_seconds": ttl_sec},
            "cooldowns": {"armed_zones": armed_zones},
            "unifier_meta": {
                "version": "2.1-hybrid",
                "tick_size": tick_size,
                "timestamp": now
            }
        }
        
        # Ajouter les champs optionnels
        if confluence:
            result["confluence"] = confluence
            result["confluence_strength"] = confluence.get("strength", 0.0)
        
        if clusters:
            result["clusters"] = clusters
        
        if summary:
            result["summary"] = summary
        
        if mia_result:
            result["mia_optimal"] = mia_result
        
        return result
        
    except Exception as e:
        print(f"Erreur compute_cluster_alerts: {e}")
        return None

def compute_confluence(levels, current_price, threshold_ticks, tick_size):
    """Calcule la confluence gamma + blind spots"""
    gamma_levels = [l for l in levels if "gamma" in (l.get("level_type", "").lower())]
    blind_levels = [l for l in levels if "blind" in (l.get("level_type", "").lower())]
    
    if not gamma_levels or not blind_levels:
        return None
    
    # Trouver le gamma le plus proche
    closest_gamma = min(gamma_levels, key=lambda x: abs(x.get("price", 0) - current_price))
    gamma_distance = abs(closest_gamma.get("price", 0) - current_price) / tick_size
    
    # Trouver le blind spot le plus proche
    closest_blind = min(blind_levels, key=lambda x: abs(x.get("price", 0) - current_price))
    blind_distance = abs(closest_blind.get("price", 0) - current_price) / tick_size
    
    # Vérifier confluence (les deux dans le seuil)
    if gamma_distance <= threshold_ticks and blind_distance <= threshold_ticks:
        strength = max(0.0, 1.0 - (max(gamma_distance, blind_distance) / threshold_ticks))
        return {
            "type": "confluence",
            "price": (closest_gamma.get("price", 0) + closest_blind.get("price", 0)) / 2,
            "gamma": {
                "level_type": closest_gamma.get("level_type", ""),
                "price": closest_gamma.get("price", 0),
                "ticks": gamma_distance,
                "sg": closest_gamma.get("sg", 0)
            },
            "blind": {
                "level_type": closest_blind.get("level_type", ""),
                "price": closest_blind.get("price", 0),
                "ticks": blind_distance,
                "sg": closest_blind.get("sg", 0)
            },
            "threshold_ticks": threshold_ticks,
            "tick_size": tick_size,
            "strength": strength
        }
    
    return None

def compute_clusters(levels, current_price, threshold_ticks, tick_size):
    """Groupe les niveaux en clusters"""
    if not levels:
        return []
    
    # Grouper par proximité
    clusters = []
    used_levels = set()
    
    for i, level in enumerate(levels):
        if i in used_levels:
            continue
            
        cluster = [level]
        used_levels.add(i)
        level_price = level.get("price", 0)
        
        # Trouver les niveaux proches
        for j, other_level in enumerate(levels):
            if j in used_levels:
                continue
                
            other_price = other_level.get("price", 0)
            distance_ticks = abs(level_price - other_price) / tick_size
            
            if distance_ticks <= threshold_ticks:
                cluster.append(other_level)
                used_levels.add(j)
        
        if len(cluster) >= 2:  # Minimum 2 niveaux pour un cluster
            clusters.append(create_cluster(cluster, current_price, tick_size))
    
    return clusters

def create_cluster(levels, current_price, tick_size):
    """Crée un cluster à partir d'une liste de niveaux"""
    prices = [l.get("price", 0) for l in levels if l.get("price")]
    if not prices:
        return None
    
    zone_min = min(prices)
    zone_max = max(prices)
    center = (zone_min + zone_max) / 2
    width_ticks = (zone_max - zone_min) / tick_size
    
    # Déterminer les groupes
    groups = []
    for level in levels:
        level_type = (level.get("level_type", "") or "").lower()
        if "gamma" in level_type:
            groups.append("gamma")
        elif "blind" in level_type:
            groups.append("blind")
        elif "gex" in level_type:
            groups.append("gex")
        elif "hvl" in level_type:
            groups.append("hvl")
    
    groups = list(set(groups))  # Dédupliquer
    
    # Calculer le score
    score = len(levels) * 0.5 + len(groups) * 0.3 + (1.0 / max(1.0, width_ticks)) * 0.2
    
    return {
        "type": "cluster",
        "price": center,
        "zone_min": zone_min,
        "zone_max": zone_max,
        "center": center,
        "width_ticks": width_ticks,
        "count": len(levels),
        "groups": groups,
        "score": score,
        "levels": levels,
        "threshold_ticks": 3.0,
        "tick_size": tick_size
    }

def compute_summary(clusters, current_price, tick_size):
    """Calcule le summary avec le cluster le plus proche"""
    if not clusters:
        return None
    
    # Trouver le cluster le plus proche
    nearest_cluster = min(clusters, key=lambda c: abs(c.get("center", 0) - current_price))
    
    # Calculer la distance et le status
    center = nearest_cluster.get("center", 0)
    zone_min = nearest_cluster.get("zone_min", 0)
    zone_max = nearest_cluster.get("zone_max", 0)
    
    distance_ticks = min(
        abs(current_price - zone_min) / tick_size,
        abs(current_price - zone_max) / tick_size
    )
    
    # Déterminer le status
    if zone_min <= current_price <= zone_max:
        status = "inside"
        distance_ticks = 0.0
    elif current_price < zone_min:
        status = "below"
        distance_ticks = (zone_min - current_price) / tick_size
    else:  # current_price > zone_max
        status = "above"
        distance_ticks = (current_price - zone_max) / tick_size
    
    # Calculer les signaux
    signals = {
        "cluster_confluence": len(nearest_cluster.get("groups", [])) >= 2,
        "cluster_strong": nearest_cluster.get("score", 0) >= 2.5 or nearest_cluster.get("width_ticks", 0) <= 3.0,
        "cluster_touch": distance_ticks <= 1.0
    }
    
    return {
        "nearest_cluster": {
            "zone_min": zone_min,
            "zone_max": zone_max,
            "center": center,
            "width_ticks": nearest_cluster.get("width_ticks", 0),
            "groups": nearest_cluster.get("groups", []),
            "score": nearest_cluster.get("score", 0),
            "distance_ticks": distance_ticks,
            "status": status
        },
        "signals": signals
    }

def unify(indir: str, yyyymmdd: str, out_path: str, tol: float, max_depth_levels: int, verbose: bool=False,
          only_set=None, menthorq_filter_enabled=False, gzip_enabled=False, args=None):
    # Filtrage par chart si fourni
    chart_id = args.chart if args and getattr(args, "chart", None) else None
    paths = list_inputs(indir, yyyymmdd, chart=chart_id)
    if not paths:
        raise FileNotFoundError(f"Aucun fichier d'entrée pour la date {yyyymmdd} dans {indir}")

    buckets = defaultdict(lambda: {
        "t_sc": None,
        "records": {},
        "quotes": None,
        "trades": None,
        "depth": { "BID": {}, "ASK": {} },
        "nbcv": {},
        "menthorq_levels": [],
        "extra": []
    })

    # État de conservation (carry-forward) inter-buckets
    carry_state = {
        "menthorq": {"levels": [], "ts_sec": 0.0},
        "correlation": {"value": None, "ts_sec": 0.0},
    }

    n_lines = 0
    # Anti-doublons: n'émettre qu'une ligne par minute (index minute basé sur t_sc)
    last_emitted_minute_index = None
    for p in paths:
        if verbose:
            print(f"Lecture: {p}", file=sys.stderr)
        for obj in iter_jsonl(p):
            n_lines += 1
            t = obj.get("t")
            if t is None:
                continue
            
            # Conversion de fuseau horaire si spécifié
            if args and getattr(args, "timezone_offset", 0.0) != 0.0:
                t = float(t) + (args.timezone_offset * 3600.0)  # Convertir heures en secondes
                obj["t"] = t
            
            key = bucket_key(float(t), tol)
            b = buckets[key]
            if b["t_sc"] is None:
                b["t_sc"] = t

            typ = obj.get("type")
            # Filtre symbole si demandé
            if args and getattr(args, "symbol", None):
                sym = (obj.get("sym") or obj.get("symbol") or "").upper()
                if sym and not sym.startswith(args.symbol.upper()):
                    continue
            if typ == "basedata":
                b["records"]["basedata"] = obj
            elif typ == "vwap":
                b["records"]["vwap"] = ensure_vwap_bands_sanity(dict(obj))
            elif typ == "vva":
                b["records"]["vva"] = ensure_vva_sanity(dict(obj))
            elif typ == "pvwap":
                b["records"]["pvwap"] = obj
            elif typ == "vix":
                b["records"]["vix"] = obj
            elif typ == "quote":
                b["quotes"] = obj
            elif typ == "trade":
                b["trades"] = obj
            elif typ == "depth":
                side = obj.get("side"); lvl = obj.get("lvl")
                if side in ("BID","ASK") and isinstance(lvl, int) and 1 <= lvl <= max_depth_levels:
                    b["depth"][side][lvl] = {"price": obj.get("price"), "size": obj.get("size")}
            elif typ == "correlation":
                b["records"]["correlation"] = obj
            elif typ in ("nbcv_footprint", "nbcv_metrics", "nbcv_orderflow"):
                i = obj.get("i", -1)
                entry = b["nbcv"].setdefault(i, {})
                if typ == "nbcv_footprint": entry["footprint"] = obj
                elif typ == "nbcv_metrics": entry["metrics"] = obj
                else: entry["orderflow"] = obj
            elif typ in ("menthorq_level", "menthorq"):
                # Appliquer la correction timezone aux données MenthorQ
                if args and getattr(args, "timezone_offset", 0.0) != 0.0:
                    obj_copy = obj.copy()
                    obj_copy["t"] = float(obj["t"]) + (args.timezone_offset * 3600.0)
                    b["menthorq_levels"].append(obj_copy)
                else:
                    b["menthorq_levels"].append(obj)
            elif typ in ("menthorq_gamma", "menthorq_blind_spots"):
                # Considérer ces objets comme des niveaux MenthorQ consolidés
                if args and getattr(args, "timezone_offset", 0.0) != 0.0:
                    obj_copy = obj.copy()
                    obj_copy["t"] = float(obj.get("t", 0.0)) + (args.timezone_offset * 3600.0)
                    b["menthorq_levels"].append(obj_copy)
                else:
                    b["menthorq_levels"].append(obj)
            elif typ == "correlation_unified":
                # Garder uniquement la dernière valeur par bucket (fallback possible)
                b["records"]["correlation_unified"] = obj
            elif typ == "atr":
                b["records"]["atr"] = obj
            elif typ == "cumulative_delta":
                b["records"]["cumulative_delta"] = obj
            else:
                b["extra"].append(obj)

    # MenthorQ filter (post-bucket)
    fn_filter = load_menthorq_filter(menthorq_filter_enabled)
    if fn_filter is not None:
        for b in buckets.values():
            b["menthorq_levels"] = apply_menthorq_filter(b["menthorq_levels"], fn_filter)

    # Writer (gzip/plain)
    if args and getattr(args, "append_stream", False):
        # En mode append-stream, on force le format non compressé pour append fiable
        if gzip_enabled:
            if verbose:
                print("[WARN] --append-stream ignorera --gzip (append non supporté en gzip)", file=sys.stderr)
            gzip_enabled = False
        mode = "a"  # append
    else:
        mode = "wt" if gzip_enabled else "w"

    if gzip_enabled and not out_path.endswith(".gz"):
        out_path = out_path + ".gz"

    opener = gzip.open if gzip_enabled else open
    total_written = 0

    keys_sorted = sorted(buckets.keys())
    # Déduplication: si append-stream, ne pas réécrire les buckets déjà sortis
    last_written_t = 0.0
    if args and getattr(args, "append_stream", False):
        last_written_t = _read_last_unified_ts(out_path)

    with opener(out_path, mode, encoding="utf-8") as out:
        for k in keys_sorted:
            b = buckets[k]
            unified = {}

            # Toujours inclure le temps
            unified["t"] = b["t_sc"]

            # Calcul temps en secondes pour TTL carry-forward
            try:
                current_ts_sec = float(unified["t"]) * 86400.0 if unified["t"] is not None else 0.0
            except Exception:
                current_ts_sec = 0.0

            # Skip si déjà écrit (append-stream)
            if args and getattr(args, "append_stream", False):
                try:
                    t_val = float(unified["t"]) if unified["t"] is not None else 0.0
                    if t_val <= last_written_t:
                        continue
                except Exception:
                    # si t invalide, on écrit quand même
                    pass

            # Assemble blocs
            if (only_set is None) or ("basedata" in only_set):
                unified["basedata"] = b["records"].get("basedata")
            if (only_set is None) or ("vwap" in only_set):
                unified["vwap"] = b["records"].get("vwap")
            if (only_set is None) or ("vva" in only_set):
                unified["vva"] = b["records"].get("vva")
            if (only_set is None) or ("pvwap" in only_set):
                unified["pvwap"] = b["records"].get("pvwap")
            if (only_set is None) or ("vix" in only_set):
                unified["vix"] = b["records"].get("vix")
            if (only_set is None) or ("quote" in only_set):
                unified["quote"] = b["quotes"]
            if (only_set is None) or ("trade" in only_set):
                unified["trade"] = b["trades"]
            if (only_set is None) or ("depth" in only_set):
                unified["depth"] = {
                    "BID": [{"lvl": lvl, **vals} for lvl, vals in sorted(b["depth"]["BID"].items())],
                    "ASK": [{"lvl": lvl, **vals} for lvl, vals in sorted(b["depth"]["ASK"].items())],
                }
            if (only_set is None) or ("nbcv" in only_set):
                unified["nbcv"] = b["nbcv"]
            if (only_set is None) or ("menthorq" in only_set):
                # Mise à jour carry-forward si niveaux présents
                if b["menthorq_levels"]:
                    unified["menthorq"] = b["menthorq_levels"]
                    carry_state["menthorq"]["levels"] = b["menthorq_levels"]
                    carry_state["menthorq"]["ts_sec"] = current_ts_sec
                    if verbose:
                        print(f"[MENTHORQ] NOUVELLES DONNÉES: {len(b['menthorq_levels'])} niveaux")
                else:
                    # Injecter derniers niveaux si encore valides
                    ttl_sec_cf = args.ttl_seconds if args else 900
                    last = carry_state["menthorq"]
                    if last["levels"] and (current_ts_sec - last["ts_sec"]) <= ttl_sec_cf:
                        unified["menthorq"] = last["levels"]
                        if verbose:
                            print(f"[CARRY-FORWARD] MenthorQ: {len(last['levels'])} niveaux (TTL: {ttl_sec_cf}s, age: {current_ts_sec - last['ts_sec']:.1f}s)")
                    else:
                        unified["menthorq"] = []
                        if verbose:
                            if last["levels"]:
                                print(f"[CARRY-FORWARD] MenthorQ: expiré (TTL: {ttl_sec_cf}s, age: {current_ts_sec - last['ts_sec']:.1f}s)")
                            else:
                                print(f"[CARRY-FORWARD] MenthorQ: aucune donnée précédente")
                
        # === CLUSTER ALERTS GENERATION ===
        if b["menthorq_levels"]:
            # Extraire les données pour MIA Optimal
            vwap_data = unified.get("vwap", {})
            vwap_value = vwap_data.get("vwap") if vwap_data else None
            
            orderflow_data = unified.get("nbcv", {})
            
            vix_data = unified.get("vix", {})
            vix_value = vix_data.get("value") if vix_data else None
            
            # Paramètres par défaut si args n'est pas fourni
            pg_distance = args.pg_distance if args else 2.5
            touch_thr = args.touch_thr if args else 1.0
            zone_cooldown_sec = args.zone_cooldown if args else 300
            ttl_sec = args.ttl_seconds if args else 900
            enable_menthorq_decisions = args.menthorq_decisions if args else False
            enable_mia_optimal = args.mia_optimal if args else False
            
            # Sécuriser le prix courant si basedata est absent
            _bd = unified.get("basedata") or {}
            current_price = _bd.get("c")
            alerts = compute_cluster_alerts(
                b["menthorq_levels"], 
                current_price,
                tick_size=(args.tick_size if args else 0.25),
                confluence_thr=3.0,
                cluster_thr=3.0,
                pg_distance=pg_distance,
                touch_thr=touch_thr,
                zone_cooldown_sec=zone_cooldown_sec,
                ttl_sec=ttl_sec,
                enable_menthorq_decisions=enable_menthorq_decisions,
                enable_mia_optimal=enable_mia_optimal,
                vwap=vwap_value,
                orderflow=orderflow_data,
                vix=vix_value
            )
            if alerts:
                unified["alerts"] = alerts

        # === CORRELATION (Graph 10) AVEC CARRY-FORWARD ===
        try:
            corr_obj = b["records"].get("correlation")
        except Exception:
            corr_obj = None
        # Fallback: utiliser correlation_unified si corr standard absent ou nul
        corr_unified_obj = b["records"].get("correlation_unified")
        chosen_cc = None
        if corr_obj is not None and isinstance(corr_obj.get("cc"), (int, float)) and corr_obj.get("cc") != 0:
            chosen_cc = corr_obj.get("cc")
        elif corr_unified_obj is not None and isinstance(corr_unified_obj.get("cc"), (int, float)):
            chosen_cc = corr_unified_obj.get("cc")
        # Filtrer valeurs sentinelles/invalides
        if isinstance(chosen_cc, (int, float)) and (chosen_cc == 0 or abs(chosen_cc - 0.427) < 1e-6):
            chosen_cc = None
        if chosen_cc is not None:
            unified["correlation"] = {"cc": chosen_cc}
            carry_state["correlation"]["value"] = chosen_cc
            carry_state["correlation"]["ts_sec"] = current_ts_sec
        else:
            ttl_corr = (args.correlation_ttl_seconds if args else 120)
            lastc = carry_state["correlation"]
            if lastc["value"] is not None and (current_ts_sec - lastc["ts_sec"]) <= ttl_corr:
                unified["correlation"] = {"cc": lastc["value"]}
        
        # === ASSEMBLAGE FINAL ===
        if (only_set is None) or ("atr" in only_set):
            unified["atr"] = b["records"].get("atr")
        if (only_set is None) or ("cumulative_delta" in only_set):
            unified["cumulative_delta"] = b["records"].get("cumulative_delta")
        if (only_set is None) or ("extra" in only_set):
            unified["extra"] = b["extra"]

        # === CORRECTION CUMULATIVE DELTA ===
        # Remplacer les valeurs Sierra Chart erronées par notre calculateur interne
        if unified.get("cumulative_delta") is not None:
            try:
                # Calculer notre cumulative delta basé sur les données NBCV
                our_cumulative = cumulative_delta_calc.update(unified)
                
                # Remplacer les valeurs Sierra Chart
                unified["cumulative_delta"]["close"] = our_cumulative["close"]
                unified["cumulative_delta"]["delta"] = our_cumulative["delta"]
                
                if verbose:
                    print(f"[CUMULATIVE_DELTA] Corrigé: {our_cumulative['close']:.1f} (delta: {our_cumulative['delta']:.1f})")
                    
            except Exception as e:
                if verbose:
                    print(f"[CUMULATIVE_DELTA] Erreur correction: {e}")

        # N'écrire qu'une ligne par minute
        current_minute_index = int(current_ts_sec // 60)
        if (last_emitted_minute_index is None) or (current_minute_index != last_emitted_minute_index):
            out.write(json.dumps(unified, ensure_ascii=False) + "\n")
            total_written += 1
            last_emitted_minute_index = current_minute_index

    return {
        "inputs": len(paths),
        "lines_read": n_lines,
        "buckets": len(buckets),
        "written": total_written,
        "out": out_path,
        "gzip": gzip_enabled,
        "only": (sorted(only_set) if only_set else None),
        "menthorq_filter": bool(fn_filter)
    }

def main():
    args = parse_args()

    # Mode M1 strict: force une agrégation à 60 secondes
    if getattr(args, "minute_mode", False):
        try:
            args.tol = 60.0
        except Exception:
            pass

    def compute_out_path(ymd: str) -> str:
        organized_path = get_organized_data_path(args.indir, ymd)
        # Si un chart spécifique est demandé, écrire sous son dossier CHART_<id>
        chart_id = str(args.chart) if getattr(args, "chart", None) else None
        if chart_id:
            organized_path = os.path.join(organized_path, f"CHART_{chart_id}")
        ensure_directory_exists(organized_path)
        if args.rollover_minutes and args.rollover_minutes > 0:
            now = datetime.datetime.now()
            if args.rollover_minutes % 60 == 0:
                suffix = now.strftime("%H")
                out_default = os.path.join(organized_path, f"unified_{ymd}_{suffix}.jsonl")
            else:
                window_index = (now.minute // max(1, args.rollover_minutes))
                suffix = f"{now.strftime('%H')}-{window_index:02d}"
                out_default = os.path.join(organized_path, f"unified_{ymd}_{suffix}.jsonl")
        else:
            if chart_id:
                out_default = os.path.join(organized_path, f"unified_chart_{chart_id}_{ymd}.jsonl")
            else:
                out_default = os.path.join(organized_path, f"unified_{ymd}.jsonl")
            
        # Rollover par taille de fichier si activé
        if getattr(args, "rollover_bytes", 0) > 0:
            try:
                if os.path.exists(out_default) and os.path.getsize(out_default) >= args.rollover_bytes:
                    # On suffixe HHMM pour ouvrir un nouveau fichier journalier « segmenté »
                    seg = datetime.datetime.now().strftime("%H%M")
                    if chart_id:
                        out_default = os.path.join(organized_path, f"unified_chart_{chart_id}_{ymd}_{seg}.jsonl")
                    else:
                        out_default = os.path.join(organized_path, f"unified_{ymd}_{seg}.jsonl")
            except Exception:
                pass
                
        return args.out or out_default

    def run_once(current_ymd: str):
        out_path = compute_out_path(current_ymd)

        only_set = None
        if args.only:
            only_set = set(s.strip().lower() for s in args.only.split(",")) - {""}
            unknown = sorted(only_set - SUPPORTED_ONLY)
            if unknown:
                raise ValueError(f"--only contient des clés non supportées: {unknown}. Clés valides: {sorted(SUPPORTED_ONLY)}")

        print(f"=== MIA UNIFIER v2.1-HYBRID ===")
        print(f"  - Date: {current_ymd}")
        print(f"  - Sortie: {out_path}")
        print(f"  - Tolérance: {args.tol}s")
        print(f"  - Rollover: {args.rollover_minutes} min")
        print(f"  - Append-stream: {'OUI' if getattr(args, 'append_stream', False) else 'NON'}")
        print()

        stats = unify(
            args.indir, current_ymd, out_path,
            tol=args.tol,
            max_depth_levels=args.max_depth_levels,
            verbose=args.verbose,
            only_set=only_set,
            menthorq_filter_enabled=args.menthorq_filter,
            gzip_enabled=args.gzip,
            args=args
        )
        print(json.dumps(stats, indent=2, ensure_ascii=False))
        return stats

    if args.watch_seconds and args.watch_seconds > 0:
        # En mode watch, forcer append-stream et interdire gzip
        args.append_stream = True
        if args.gzip:
            print("[WARN] --watch-seconds ignore --gzip (append non supporté en gzip)", file=sys.stderr)
            args.gzip = False

        print(f"[WATCH] démarrage: interval={args.watch_seconds}s (append-stream ON)")
        try:
            while True:
                current_ymd = resolve_date(args.date)
                stats = run_once(current_ymd)
                if args.verbose:
                    print(f"[WATCH] +{stats.get('written',0)} buckets -> {stats.get('out','')}")
                time.sleep(max(0.1, args.watch_seconds))
        except KeyboardInterrupt:
            print("[WATCH] arrêté proprement.")
    else:
        current_ymd = resolve_date(args.date)
        run_once(current_ymd)

if __name__ == "__main__":
    main()