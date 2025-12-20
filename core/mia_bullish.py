# Auto-generated module: mia_bullish
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Deque, Tuple, List
from collections import deque
import math
import numpy as np

# === GPT v3.0 IMPORTS ===
try:
    from core.ml_ready_helpers import calculate_delta_ratio
    from core.corridor_manager import CorridorManager
    from core.timeframe_aligner import TimeframeAligner
    GPT_V3_ENABLED = True
except ImportError:
    GPT_V3_ENABLED = False

def clip01(x: float) -> float:
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x

@dataclass
class _BarCache:
    close: Optional[float] = None
    vwap: Optional[float] = None
    up1: Optional[float] = None
    dn1: Optional[float] = None
    vah: Optional[float] = None
    val: Optional[float] = None
    delta_ratio: Optional[float] = None
    pressure: Optional[int] = None  # -1 / 0 / 1
    cumdelta: Optional[float] = None
    t: Optional[float] = None  # timestamp (Sierra double), optional

class BullishScorer:
    def __init__(self, chart_id: int = 3, use_vix: bool = True):
        self.chart_id = chart_id
        self.use_vix = use_vix
        self.vix_value: Optional[float] = None
        self.cum_hist: Deque[Tuple[int, float]] = deque(maxlen=16)  # (i, cumdelta)
        self.bars: Dict[int, _BarCache] = {}

    def ingest(self, ev: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        ev_type = ev.get("type")
        chart = ev.get("chart") or ev.get("graph")
        if ev_type is None:
            return None
        # vix updates
        if self.use_vix and ev_type in ("vix", "vix_close"):
            last = ev.get("last") or ev.get("close") or ev.get("vix")
            if isinstance(last, (int, float)) and last > 0:
                self.vix_value = float(last)
            return None
        # only chart
        if chart != self.chart_id:
            return None
        i = ev.get("i")
        if i is None:
            return None
        bar = self.bars.get(i) or _BarCache()
        if "t" in ev and bar.t is None:
            try:
                bar.t = float(ev["t"])
            except Exception:
                pass
        if ev_type == "basedata":
            c = ev.get("c")
            if isinstance(c, (int, float)):
                bar.close = float(c)
        elif ev_type == "nbcv_footprint":
            # Fallback: utiliser le close du nbcv_footprint si basedata n'est pas disponible
            if bar.close is None:
                # Essayer de déduire le close du dernier trade ou du mid
                # Pour l'instant, on utilise une valeur par défaut
                pass
        elif ev_type == "vwap":
            v = ev.get("v")
            if isinstance(v, (int, float)):
                bar.vwap = float(v)
            up1 = ev.get("up1")
            dn1 = ev.get("dn1")
            if isinstance(up1, (int, float)):
                bar.up1 = float(up1)
            if isinstance(dn1, (int, float)):
                bar.dn1 = float(dn1)
        elif ev_type == "vva":
            vah = ev.get("vah")
            val = ev.get("val")
            if isinstance(vah, (int, float)):
                bar.vah = float(vah)
            if isinstance(val, (int, float)):
                bar.val = float(val)
        elif ev_type == "nbcv_footprint":
            cd = ev.get("cumulative_delta")
            if isinstance(cd, (int, float)):
                bar.cumdelta = float(cd)
                self._append_cum_hist(int(i), float(cd))
        elif ev_type in ("nbcv_metrics", "nbcv_footprint"):
            dr = ev.get("delta_ratio")
            if isinstance(dr, (int, float)):
                bar.delta_ratio = float(dr)
            bull = int(ev.get("pressure_bullish") == 1)
            bear = int(ev.get("pressure_bearish") == 1)
            bar.pressure = 1 if bull and not bear else (-1 if bear and not bull else 0)
        self.bars[i] = bar
        return self._maybe_compute(i)

    def _append_cum_hist(self, idx: int, cd: float) -> None:
        if len(self.cum_hist) == 0 or idx > self.cum_hist[-1][0]:
            self.cum_hist.append((idx, cd))
        elif idx == self.cum_hist[-1][0]:
            self.cum_hist[-1] = (idx, cd)

    def _cum_slope_score(self) -> float:
        if len(self.cum_hist) < 3:
            return 0.5
        xs = list(range(len(self.cum_hist)))
        ys = [v for _, v in self.cum_hist]
        xm = sum(xs) / len(xs)
        ym = sum(ys) / len(ys)
        num = sum((x - xm) * (y - ym) for x, y in zip(xs, ys))
        den = sum((x - xm) ** 2 for x in xs) or 1.0
        slope = num / den
        norm = abs(ym) * 0.05 + 50.0
        return clip01(slope / norm)

    def _maybe_compute(self, i: int) -> Optional[Dict[str, Any]]:
        bar = self.bars.get(i)
        if not bar:
            return None
        # Utiliser VWAP comme fallback pour close si nécessaire
        close_price = bar.close if bar.close is not None else bar.vwap
        if close_price is None or bar.vwap is None or bar.delta_ratio is None:
            return None

        # ========================================
        # BULLISH SCORER V2.0 - ENHANCED (10 COMPOSANTES)
        # ========================================

        # 1) Order-Flow Enhanced (25%) - Pressure + Delta Ratio
        of_core = 1.0 if bar.pressure == 1 else (0.0 if bar.pressure == -1 else 0.5)
        of_bonus = clip01(((bar.delta_ratio or 0.0) - 0.08) / (0.50 - 0.08))
        OF_score = 0.7 * of_core + 0.3 * of_bonus

        # 2) VWAP Position (15%) - Position relative aux bandes
        if bar.up1 is not None and bar.vwap is not None:
            band = max(1e-9, abs(bar.up1 - bar.vwap))
        else:
            band = max(1e-9, abs(bar.vwap) * 0.002)
        z = (close_price - bar.vwap) / band
        VWAP_score = clip01(0.5 + 0.5 * math.tanh(z))

        # 3) VVA - Value Area (10%)
        if bar.vah is not None and bar.val is not None:
            if close_price > bar.vah:
                VVA_score = 0.9; pos = "above_VAH"
            elif close_price < bar.val:
                VVA_score = 0.1; pos = "below_VAL"
            else:
                VVA_score = 0.5; pos = "inside_VA"
        else:
            VVA_score = 0.5; pos = "no_VA"

        # 4) Cumulative Delta Trend (10%)
        CD_score = self._cum_slope_score()

        # 5) VIX Factor (multiplicateur de confiance)
        if self.use_vix and isinstance(self.vix_value, (int, float)):
            vix = float(self.vix_value)
            if vix <= 12:   vix_factor = 0.95   # Complaisance
            elif vix <= 25: vix_factor = 1.00   # Normal
            elif vix <= 35: vix_factor = 0.95   # Nerveux
            else:           vix_factor = 0.85   # Panique
        else:
            vix_factor = 1.0

        # Score unidirectionnel (0 à 1)
        score = (0.25 * OF_score +
                 0.15 * VWAP_score +
                 0.10 * VVA_score +
                 0.10 * CD_score) * vix_factor

        # Conversion en score BIDIRECTIONNEL (-1 à +1)
        # Score = 0.5 → neutre (0.0)
        # Score = 1.0 → très bullish (+1.0)
        # Score = 0.0 → très bearish (-1.0)
        score_bidirectional = (score - 0.5) * 2.0
        score_bidirectional = max(-1.0, min(1.0, score_bidirectional))
        score_bidirectional = round(score_bidirectional, 3)

        # Calcul staleness des données
        import time
        current_time = time.time()
        staleness_ms = None
        staleness_status = "OK"

        if bar.t is not None:
            # Convertir timestamp Sierra/Excel vers epoch si nécessaire
            if bar.t > 10000:  # Sierra/Excel days format
                EXCEL_EPOCH_OFFSET_DAYS = 25569
                SECONDS_PER_DAY = 86400.0
                data_timestamp = (bar.t - EXCEL_EPOCH_OFFSET_DAYS) * SECONDS_PER_DAY
            else:
                data_timestamp = bar.t

            staleness_ms = (current_time - data_timestamp) * 1000

            # Déterminer le statut selon la staleness
            if staleness_ms > 5000:  # > 5 secondes
                staleness_status = "STALE"
            elif staleness_ms > 2100:  # > 2.1 secondes
                staleness_status = "OLD"
            else:
                staleness_status = "OK"

        # Logger la staleness si problématique
        try:
            from core.logger import get_logger
            logger = get_logger(__name__)

            if staleness_status != "OK":
                logger.warning(f"🕐 MIA Staleness: {staleness_status} - "
                             f"asof={staleness_ms:.1f}ms, score={score}, "
                             f"pressure={bar.pressure}, pos={pos}")
            else:
                logger.debug(f"✅ MIA Fresh: asof={staleness_ms:.1f}ms → {staleness_status}")

        except Exception:
            # Fallback silencieux si logger non disponible
            pass

        return {
            "t": bar.t,
            "chart": self.chart_id,
            "type": "mia_bullish",
            "i": i,
            "score": score_bidirectional,  # Score bidirectionnel (-1 à +1)
            "score_raw": round(score, 3),  # Score brut (0 à 1) pour debug
            "pressure": bar.pressure,
            "dr": round(bar.delta_ratio, 4) if bar.delta_ratio is not None else None,
            "pos": pos,
            "close": close_price,
            "vwap": bar.vwap,
            "staleness_ms": round(staleness_ms, 1) if staleness_ms is not None else None,
            "staleness_status": staleness_status,
            # Détails des composantes
            "components": {
                "orderflow": round(OF_score, 3),
                "vwap_pos": round(VWAP_score, 3),
                "vva": round(VVA_score, 3),
                "cum_delta": round(CD_score, 3),
                "vix_factor": round(vix_factor, 3)
            }
        }

    # Ancienne méthode calculate_bullish_score() SUPPRIMÉE - Utiliser calculate_bullish_score_ml_ready() à la place

    def calculate_bullish_score_ml_ready(self, ml_data: Dict) -> Dict[str, Any]:
        """
        🚀 VERSION AMÉLIORÉE - Calcule le score MIA Bullish avec TOUTES les données ML_READY

        Utilise 10 composantes au lieu de 5 :
        1. OrderFlow Enhanced (Smart Money + Institutional Pressure)
        2. VWAP Multi-Timeframe (Daily + Weekly + Monthly)
        3. DOM Imbalances (L1-L3 + Depth)
        4. Gamma Confluence (GEX + Call/Put Walls + Blind Spots)
        5. Volume Profile (VPOC + Value Area)
        6. Cumulative Delta Trend
        7. Tick Momentum
        8. Session Bias
        9. Volatility Regime
        10. VIX Factor

        Args:
            ml_data: Données ML_READY complètes (avec DOM, Gamma, OrderFlow, etc.)

        Returns:
            dict: {
                'score': float (-1 à +1, bidirectionnel),
                'confidence': float (0 à 1),
                'components': dict (détail des composantes),
                'signal': str ('BULLISH', 'BEARISH', 'NEUTRAL'),
                'strength': str ('STRONG', 'MODERATE', 'WEAK')
            }
        """
        try:
            # Prix de référence
            mid = ml_data.get('mid')
            close = ml_data.get('close', mid)

            if not mid or not close:
                return self._empty_score_result()

            # ========================================
            # 1️⃣ ORDER-FLOW ENHANCED (25%)
            # ========================================
            orderflow_score = self._calc_orderflow_enhanced(ml_data)

            # ========================================
            # 2️⃣ VWAP MULTI-TIMEFRAME (15%)
            # ========================================
            vwap_score = self._calc_vwap_multi_tf(ml_data, close)

            # ========================================
            # 3️⃣ DOM IMBALANCES (15%)
            # ========================================
            dom_score = self._calc_dom_imbalances(ml_data)

            # ========================================
            # 4️⃣ GAMMA CONFLUENCE (15%)
            # ========================================
            gamma_score = self._calc_gamma_confluence(ml_data, close)

            # ========================================
            # 5️⃣ VOLUME PROFILE (10%)
            # ========================================
            vpoc_score = self._calc_volume_profile(ml_data, close)

            # ========================================
            # 6️⃣ CUMULATIVE DELTA TREND (10%)
            # ========================================
            cum_delta = ml_data.get('cum_delta_day', 0)
            cd_score = 0.5 + (0.5 * math.tanh(cum_delta / 1000.0))

            # ========================================
            # 7️⃣ TICK MOMENTUM (5%)
            # ========================================
            tick_mom = ml_data.get('tick_momentum', 0.0)
            tick_score = 0.5 + (0.5 * tick_mom)

            # ========================================
            # 8️⃣ SESSION BIAS (3%)
            # ========================================
            session_score = self._calc_session_bias(ml_data)

            # ========================================
            # 9️⃣ VOLATILITY REGIME (2%)
            # ========================================
            vol_score = self._calc_volatility_regime(ml_data)

            # ========================================
            # 🔟 VIX FACTOR (multiplicateur)
            # ========================================
            vix = ml_data.get('vix', 15.0)
            if vix <= 12:
                vix_factor = 0.95   # Complaisance
            elif vix <= 25:
                vix_factor = 1.00   # Normal
            elif vix <= 35:
                vix_factor = 0.95   # Nerveux
            else:
                vix_factor = 0.85   # Panique

            # ========================================
            # 📊 AGRÉGATION PONDÉRÉE
            # ========================================
            weights = {
                'orderflow': 0.25,
                'vwap': 0.15,
                'dom': 0.15,
                'gamma': 0.15,
                'vpoc': 0.10,
                'cum_delta': 0.10,
                'tick_mom': 0.05,
                'session': 0.03,
                'volatility': 0.02
            }

            score_raw = (
                weights['orderflow'] * orderflow_score +
                weights['vwap'] * vwap_score +
                weights['dom'] * dom_score +
                weights['gamma'] * gamma_score +
                weights['vpoc'] * vpoc_score +
                weights['cum_delta'] * cd_score +
                weights['tick_mom'] * tick_score +
                weights['session'] * session_score +
                weights['volatility'] * vol_score
            ) * vix_factor

            # ========================================
            # 🚀 GPT v3.0 ENHANCEMENTS
            # ========================================
            gpt_v3_active = False
            headroom_factor = 1.0

            if GPT_V3_ENABLED:
                try:
                    # 1. Analyser Timeframe Alignment
                    aligner = TimeframeAligner(ml_data)
                    alignment = aligner.get_alignment()
                    weights_adj = aligner.get_weight_adjustments()

                    # 2. Ajuster scores des composantes si conflit timeframes
                    if alignment == -1:  # Conflit détecté
                        # Réappliquer les ajustements de poids
                        orderflow_adjusted = orderflow_score * weights_adj['of_weight']
                        vwap_adjusted = vwap_score * weights_adj['vwap_weight']
                        vpoc_adjusted = vpoc_score * weights_adj['vva_weight']

                        # Recalculer score avec ajustements
                        score_raw = (
                            weights['orderflow'] * orderflow_adjusted +
                            weights['vwap'] * vwap_adjusted +
                            weights['dom'] * dom_score +
                            weights['gamma'] * gamma_score +
                            weights['vpoc'] * vpoc_adjusted +
                            weights['cum_delta'] * cd_score +
                            weights['tick_mom'] * tick_score +
                            weights['session'] * session_score +
                            weights['volatility'] * vol_score
                        ) * vix_factor

                    # 3. Analyser Corridor et appliquer Headroom Factor
                    corridor = CorridorManager(ml_data)

                    # Déterminer direction probable du signal
                    probable_side = "LONG" if score_raw > 0.5 else "SHORT"
                    headroom_factor = corridor.headroom_factor(probable_side)

                    # Appliquer le facteur de headroom
                    score_raw *= headroom_factor

                    gpt_v3_active = True

                except Exception as e:
                    # Fallback silencieux au scoring v2.0
                    pass

            # Conversion en score BIDIRECTIONNEL (-1 à +1)
            score_bidirectional = (score_raw - 0.5) * 2.0
            score_bidirectional = max(-1.0, min(1.0, score_bidirectional))

            # Déterminer signal et force
            if score_bidirectional > 0.3:
                signal = 'BULLISH'
                strength = 'STRONG' if score_bidirectional > 0.6 else 'MODERATE'
            elif score_bidirectional < -0.3:
                signal = 'BEARISH'
                strength = 'STRONG' if score_bidirectional < -0.6 else 'MODERATE'
            else:
                signal = 'NEUTRAL'
                strength = 'WEAK'

            # Calculer confiance (combien de composantes sont actives)
            active_components = sum([
                orderflow_score != 0.5,
                vwap_score != 0.5,
                dom_score != 0.5,
                gamma_score != 0.5,
                vpoc_score != 0.5
            ])
            confidence = active_components / 5.0  # Sur 5 composantes principales

            return {
                'score': round(score_bidirectional, 3),
                'confidence': round(confidence, 2),
                'signal': signal,
                'strength': strength,
                'components': {
                    'orderflow': round(orderflow_score, 3),
                    'vwap': round(vwap_score, 3),
                    'dom': round(dom_score, 3),
                    'gamma': round(gamma_score, 3),
                    'vpoc': round(vpoc_score, 3),
                    'cum_delta': round(cd_score, 3),
                    'tick_mom': round(tick_score, 3),
                    'session': round(session_score, 3),
                    'volatility': round(vol_score, 3),
                    'vix_factor': round(vix_factor, 3)
                },
                'gpt_v3': {
                    'enabled': gpt_v3_active,
                    'headroom_factor': round(headroom_factor, 3) if gpt_v3_active else None,
                    'timeframe_alignment': alignment if gpt_v3_active else None
                }
            }

        except Exception as e:
            try:
                from core.logger import get_logger
                logger = get_logger(f"{__name__}.calculate_bullish_score_ml_ready")
                logger.error(f"❌ Erreur calcul MIA Bullish ML_READY: {e}")
            except Exception:
                pass
            return self._empty_score_result()

    # ========================================
    # 🔧 MÉTHODES HELPER POUR CHAQUE COMPOSANTE
    # ========================================

    def _empty_score_result(self) -> Dict[str, Any]:
        """Retourne un résultat vide en cas d'erreur"""
        return {
            'score': 0.0,
            'confidence': 0.0,
            'signal': 'NEUTRAL',
            'strength': 'WEAK',
            'components': {}
        }

    def _calc_orderflow_enhanced(self, ml_data: Dict) -> float:
        """
        Calcule le score OrderFlow Enhanced avec Smart Money + Institutional Pressure

        Returns: Score 0-1 (0.5 = neutre)
        """
        try:
            # Smart Money Flow
            smart_money = ml_data.get('smart_money_flow', 0.0)

            # Institutional Pressure
            inst_pressure = ml_data.get('institutional_pressure', 0.0)

            # Delta
            delta = ml_data.get('delta', 0)
            volume = ml_data.get('volume', 1)
            delta_pct = delta / max(volume, 1)

            # Pression
            pressure = ml_data.get('pressure', 0)

            # Agrégation
            of_score = 0.5  # Neutre par défaut

            # Smart Money (40%)
            of_score += 0.4 * smart_money

            # Institutional (30%)
            of_score += 0.3 * inst_pressure

            # Delta PCT (20%)
            of_score += 0.2 * delta_pct

            # Pressure boost (10%)
            if pressure == 1:
                of_score += 0.1
            elif pressure == -1:
                of_score -= 0.1

            return clip01(of_score)

        except Exception:
            return 0.5

    def _calc_vwap_multi_tf(self, ml_data: Dict, close: float) -> float:
        """
        Calcule le score VWAP Multi-Timeframe (Daily + Weekly + Monthly)

        Returns: Score 0-1 (0.5 = neutre)
        """
        try:
            # VWAP Daily
            vwap_daily = ml_data.get('vwap')
            d_vwap = ml_data.get('d_vwap', 0)

            # VWAP Weekly
            vwap_weekly = ml_data.get('vwap_weekly')
            d_vwap_weekly = ml_data.get('d_vwap_weekly', 0)

            # VWAP Monthly
            vwap_monthly = ml_data.get('vwap_monthly')
            d_vwap_monthly = ml_data.get('d_vwap_monthly', 0)

            scores = []

            # Score Daily (50%)
            if vwap_daily:
                atr = ml_data.get('atr', 1.0)
                z_daily = d_vwap / max(atr, 0.1)
                score_daily = 0.5 + 0.5 * math.tanh(z_daily / 2.0)
                scores.append((score_daily, 0.5))

            # Score Weekly (30%)
            if vwap_weekly:
                atr = ml_data.get('atr', 1.0)
                z_weekly = d_vwap_weekly / max(atr, 0.1)
                score_weekly = 0.5 + 0.5 * math.tanh(z_weekly / 2.0)
                scores.append((score_weekly, 0.3))

            # Score Monthly (20%)
            if vwap_monthly:
                atr = ml_data.get('atr', 1.0)
                z_monthly = d_vwap_monthly / max(atr, 0.1)
                score_monthly = 0.5 + 0.5 * math.tanh(z_monthly / 2.0)
                scores.append((score_monthly, 0.2))

            if not scores:
                return 0.5

            # Moyenne pondérée
            total_weight = sum(w for _, w in scores)
            weighted_score = sum(s * w for s, w in scores) / total_weight

            return clip01(weighted_score)

        except Exception:
            return 0.5

    def _calc_dom_imbalances(self, ml_data: Dict) -> float:
        """
        Calcule le score DOM Imbalances (L1-L3 + Depth)

        Returns: Score 0-1 (0.5 = neutre)
        """
        try:
            # Level 1 Imbalance
            level1_imb = ml_data.get('level1_imbalance', 0.0)

            # DOM Features
            dom_feat = ml_data.get('dom_features', {})
            imb_1_3 = dom_feat.get('imbalance_1_3', 0.0)
            imb_6_10 = dom_feat.get('imbalance_6_10', 0.0)

            # Depth Bid/Ask
            depth_bid = dom_feat.get('depth_bid', 0)
            depth_ask = dom_feat.get('depth_ask', 0)
            depth_total = depth_bid + depth_ask
            depth_imb = (depth_bid - depth_ask) / max(depth_total, 1) if depth_total > 0 else 0.0

            # Agrégation
            score = 0.5
            score += 0.4 * level1_imb      # 40% L1
            score += 0.3 * imb_1_3         # 30% L1-L3
            score += 0.2 * imb_6_10        # 20% L6-L10
            score += 0.1 * depth_imb       # 10% Depth

            return clip01(score)

        except Exception:
            return 0.5

    def _calc_gamma_confluence(self, ml_data: Dict, close: float) -> float:
        """
        Calcule le score Gamma Confluence (GEX + Call/Put Walls + Blind Spots)

        Returns: Score 0-1 (0.5 = neutre)
        """
        try:
            # Gamma Walls
            call_resistance = ml_data.get('call_resistance')
            put_support = ml_data.get('put_support')

            # HVL (High Value Level)
            hvl = ml_data.get('hvl')

            # Blind Spots
            blind_spot_confluence = ml_data.get('blind_spot_confluence', False)

            # Distances
            menthor_dist = ml_data.get('menthor_distances', {})
            d_call_wall = menthor_dist.get('d_call_wall_ticks')
            d_put_wall = menthor_dist.get('d_put_wall_ticks')
            d_hvl = menthor_dist.get('d_hvl_ticks')

            score = 0.5  # Neutre

            # Si près d'un PUT Support → Bullish
            if put_support and d_put_wall is not None:
                if abs(d_put_wall) < 20:  # < 20 ticks
                    score += 0.3

            # Si loin d'un CALL Resistance → Bullish
            if call_resistance and d_call_wall is not None:
                if d_call_wall > 50:  # > 50 ticks
                    score += 0.2

            # Si près d'un HVL → Magnétisme (neutre à bullish selon position)
            if hvl and d_hvl is not None:
                if abs(d_hvl) < 10:
                    score += 0.1

            # Blind Spot Confluence → Boost
            if blind_spot_confluence:
                score += 0.15

            return clip01(score)

        except Exception:
            return 0.5

    def _calc_volume_profile(self, ml_data: Dict, close: float) -> float:
        """
        Calcule le score Volume Profile (VPOC + Value Area)

        Returns: Score 0-1 (0.5 = neutre)
        """
        try:
            # VPOC
            vva = ml_data.get('vva', {})
            vpoc = vva.get('vpoc')
            vah = vva.get('vah')
            val = vva.get('val')

            # In Value Area?
            in_va = ml_data.get('in_value_area', False)

            # Distance à VPOC
            d_vpoc = ml_data.get('d_vpoc', 0)
            d_vpoc_ticks = ml_data.get('d_vpoc_ticks', 0)

            score = 0.5

            # Position par rapport à VAH/VAL
            if vah and val:
                if close > vah:
                    score = 0.8  # Au-dessus VAH → Bullish
                elif close < val:
                    score = 0.2  # En-dessous VAL → Bearish
                else:
                    score = 0.5  # Dans VA → Neutre

            # Distance à VPOC (magnétisme)
            if vpoc and abs(d_vpoc_ticks) < 20:
                # Proche du VPOC → Augmente légèrement le score actuel
                if score > 0.5:
                    score += 0.1
                elif score < 0.5:
                    score -= 0.1

            return clip01(score)

        except Exception:
            return 0.5

    def _calc_session_bias(self, ml_data: Dict) -> float:
        """
        Calcule le score Session Bias (Asia/London/US)

        Returns: Score 0-1 (0.5 = neutre)
        """
        try:
            session = ml_data.get('session_id', 'Asia')

            # Biais statistiques (à calibrer selon vos backtests)
            session_bias = {
                'Asia': 0.45,     # Légèrement bearish (range-bound)
                'London': 0.55,   # Légèrement bullish (breakout)
                'US': 0.50        # Neutre (volatile)
            }

            return session_bias.get(session, 0.5)

        except Exception:
            return 0.5

    def _calc_volatility_regime(self, ml_data: Dict) -> float:
        """
        Calcule le score Volatility Regime

        Returns: Score 0-1 (0.5 = neutre)
        """
        try:
            vol_regime = ml_data.get('volatility_regime', 1.0)

            # Volatilité Régime : 0 = low, 1 = normal, 2 = high
            # Low vol → Légèrement bullish (tendance)
            # High vol → Légèrement bearish (range)

            if vol_regime < 0.5:
                return 0.55  # Low vol → Bullish
            elif vol_regime > 1.5:
                return 0.45  # High vol → Bearish
            else:
                return 0.50  # Normal → Neutre

        except Exception:
            return 0.5

# --- HELPER POUR SNAPSHOTS UNIFIÉS ---

def feed_unified_snapshot(scorer: "BullishScorer", ev: dict, state: dict) -> dict | None:
    """
    Adapte un snapshot de type:
      {"timestamp": ..., "symbol": "...", "data_type": "unified_market_snapshot",
       "charts": [3], "bar_index": 1234 or None, "market_data": {...}}
    en une séquence d'évènements "bruts" pour BullishScorer.ingest().
    Retourne le dernier event dérivé (mia_bullish) si disponible.
    """
    if ev.get("data_type") != "unified_market_snapshot":
        return None

    md = ev.get("market_data") or {}
    charts = ev.get("charts") or []
    if 3 not in charts:
        return None

    # bar index (si pas fourni, on incrémente localement)
    bi = ev.get("bar_index")
    if bi is None:
        bi = state.setdefault("_i", -1) + 1
        state["_i"] = bi

    t = ev.get("timestamp")
    derived = None

    def push(e):
        nonlocal derived
        d = scorer.ingest(e)
        if d is not None:
            derived = d

    # --- basedata ---
    bd = md.get("basedata") or md.get("bd") or {}
    c = bd.get("close") or bd.get("c")
    if isinstance(c, (int, float)):
        push({"t": t, "type": "basedata", "chart": 3, "i": bi, "c": float(c)})

    # --- VWAP + bandes ---
    vwap = md.get("vwap") or {}
    v = vwap.get("v") or vwap.get("VWAP") or vwap.get("vwap")
    if isinstance(v, (int, float)):
        up1 = vwap.get("up1") or vwap.get("sigma1_up") or vwap.get("+1")
        dn1 = vwap.get("dn1") or vwap.get("sigma1_dn") or vwap.get("-1")
        push({
            "t": t, "type": "vwap", "chart": 3, "i": bi,
            "v": float(v),
            "up1": float(up1) if isinstance(up1, (int, float)) else None,
            "dn1": float(dn1) if isinstance(dn1, (int, float)) else None
        })

    # --- VVA (VAH/VAL) ---
    vva = md.get("vva") or {}
    vah = vva.get("vah") or vva.get("VAH")
    val = vva.get("val") or vva.get("VAL")
    if isinstance(vah, (int, float)) or isinstance(val, (int, float)):
        push({
            "t": t, "type": "vva", "chart": 3, "i": bi,
            "vah": float(vah) if isinstance(vah, (int, float)) else None,
            "val": float(val) if isinstance(val, (int, float)) else None
        })

    # --- NBCV metrics / footprint ---
    nbcv = md.get("nbcv") or {}
    metrics = nbcv.get("metrics") or nbcv
    dr = metrics.get("delta_ratio") or metrics.get("dr")
    bull = metrics.get("pressure_bullish") or metrics.get("bull") or 0
    bear = metrics.get("pressure_bearish") or metrics.get("bear") or 0
    if isinstance(dr, (int, float)) or bull or bear:
        push({
            "t": t, "type": "nbcv_metrics", "chart": 3, "i": bi,
            "delta_ratio": float(dr) if isinstance(dr, (int, float)) else None,
            "pressure_bullish": 1 if bull else 0,
            "pressure_bearish": 1 if bear else 0
        })

    fp = nbcv.get("footprint") or {}
    cd = fp.get("cumulative_delta") or fp.get("cumdelta") or fp.get("cum_delta")
    if isinstance(cd, (int, float)):
        push({
            "t": t, "type": "nbcv_footprint", "chart": 3, "i": bi,
            "cumulative_delta": float(cd)
        })

    # --- VIX (si snapshot l'expose) ---
    vix = (md.get("vix") or {}).get("close") or md.get("vix_close") or md.get("vix")
    if isinstance(vix, (int, float)):
        scorer.ingest({"t": t, "type": "vix_close", "close": float(vix), "chart": 8, "i": bi})

    return derived
