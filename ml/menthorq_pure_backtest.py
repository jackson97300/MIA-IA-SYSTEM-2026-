"""
MenthorQ Pure Strategy - Backtest
==================================

Objectif: Tester une stratégie PURE basée uniquement sur les niveaux MenthorQ Premium
         sans filtres complexes, pour reproduire le trading manuel de l'utilisateur.

Comparaison directe avec T4 Baseline (+0.30 t/trade).

Auteur: MIA Trading System
Date: 15 Novembre 2025
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class MenthorQLevel:
    """Représente un niveau MenthorQ"""
    price: float
    level_type: str  # 'gex_wall', 'blind_spot', 'hvl', 'call_wall', 'put_wall'
    strength: float  # 0-100
    distance_ticks: float  # Distance au prix actuel


@dataclass
class TradeResult:
    """Résultat d'un trade simulé"""
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    direction: str  # 'LONG' or 'SHORT'
    pnl_ticks: float
    exit_reason: str  # 'TP', 'SL', 'TIME', 'MANUAL'
    level_type: str
    level_price: float
    duration_seconds: float


class MenthorQPureStrategy:
    """
    Stratégie Pure MenthorQ - Reproduction du trading manuel

    Principes:
    1. Trade uniquement les niveaux MenthorQ de haute qualité
    2. Entry au touch du niveau (±2 ticks)
    3. Direction selon le type de niveau (bounce sur support, rejection sur resistance)
    4. SL/TP adaptés au type de niveau
    5. Exit rapide si pas de mouvement (5-10 min max)
    """

    def __init__(
        self,
        # Paramètres d'entrée
        max_distance_ticks: int = 3,  # Distance max pour considérer "au touch"
        min_level_strength: float = 60.0,  # Force minimum du niveau

        # Paramètres SL/TP
        sl_ticks_default: int = 10,
        tp_ticks_default: int = 20,

        # Paramètres de temps
        max_trade_duration_minutes: int = 8,

        # Priorité des niveaux (ordre d'importance)
        level_priority: List[str] = None,

        # Fees
        fees_per_trade: float = 0.62
    ):
        self.max_distance_ticks = max_distance_ticks
        self.min_level_strength = min_level_strength
        self.sl_ticks_default = sl_ticks_default
        self.tp_ticks_default = tp_ticks_default
        self.max_trade_duration_minutes = max_trade_duration_minutes
        self.fees_per_trade = fees_per_trade

        # Ordre de priorité des niveaux (par défaut)
        self.level_priority = level_priority or [
            'gex_wall',
            'blind_spot',
            'hvl',
            'call_wall',
            'put_wall'
        ]

        logger.info("MenthorQPureStrategy initialisee")
        logger.info(f"  Max distance: {max_distance_ticks} ticks")
        logger.info(f"  Min strength: {min_level_strength}")
        logger.info(f"  SL/TP: {sl_ticks_default}t / {tp_ticks_default}t")
        logger.info(f"  Max duration: {max_trade_duration_minutes} min")
        logger.info(f"  Fees: {fees_per_trade}t (Option A - PropFirms Moyennes)")

    def _extract_menthorq_levels(self, snapshot: Dict) -> List[MenthorQLevel]:
        """
        Extrait les niveaux MenthorQ d'un snapshot

        Args:
            snapshot: Dictionnaire contenant les données du snapshot

        Returns:
            Liste des niveaux MenthorQ triés par priorité
        """
        levels = []
        current_price = snapshot.get('entry_price', snapshot.get('close', 0))

        # GEX Levels (gex_1 à gex_5)
        for i in range(1, 6):
            gex_key = f'gex_{i}'
            if pd.notna(snapshot.get(gex_key)):
                gex_price = float(snapshot[gex_key])
                levels.append(MenthorQLevel(
                    price=gex_price,
                    level_type='gex_wall',
                    strength=85.0 - (i * 3),  # Force décroissante
                    distance_ticks=abs(current_price - gex_price) * 4
                ))

        # Blind Spots (blind_spot_0, blind_spot_1, blind_spot_2)
        for i in range(3):
            blind_key = f'blind_spot_{i}'
            if pd.notna(snapshot.get(blind_key)):
                blind_price = float(snapshot[blind_key])
                levels.append(MenthorQLevel(
                    price=blind_price,
                    level_type='blind_spot',
                    strength=75.0 - (i * 5),  # Force décroissante
                    distance_ticks=abs(current_price - blind_price) * 4
                ))

        # HVL (High Value Levels)
        if pd.notna(snapshot.get('hvl')):
            hvl_price = float(snapshot['hvl'])
            levels.append(MenthorQLevel(
                price=hvl_price,
                level_type='hvl',
                strength=70.0,
                distance_ticks=abs(current_price - hvl_price) * 4
            ))

        # Call/Put Walls
        if pd.notna(snapshot.get('call_resistance')):
            call_price = float(snapshot['call_resistance'])
            levels.append(MenthorQLevel(
                price=call_price,
                level_type='call_wall',
                strength=75.0,
                distance_ticks=abs(current_price - call_price) * 4
            ))

        if pd.notna(snapshot.get('put_support')):
            put_price = float(snapshot['put_support'])
            levels.append(MenthorQLevel(
                price=put_price,
                level_type='put_wall',
                strength=75.0,
                distance_ticks=abs(current_price - put_price) * 4
            ))

        return levels

    def _find_best_level(self, levels: List[MenthorQLevel]) -> Optional[MenthorQLevel]:
        """
        Trouve le meilleur niveau à trader selon:
        1. Distance (le plus proche dans la limite max_distance_ticks)
        2. Force (strength)
        3. Priorité (type de niveau)
        """
        # Filtrer les niveaux trop loin
        valid_levels = [
            level for level in levels
            if level.distance_ticks <= self.max_distance_ticks
            and level.strength >= self.min_level_strength
        ]

        if not valid_levels:
            return None

        # Trier par:
        # 1. Priorité du type
        # 2. Distance (plus proche = mieux)
        # 3. Force (plus fort = mieux)
        def level_score(level: MenthorQLevel) -> Tuple:
            priority_idx = (
                self.level_priority.index(level.level_type)
                if level.level_type in self.level_priority
                else 999
            )
            return (priority_idx, level.distance_ticks, -level.strength)

        valid_levels.sort(key=level_score)
        return valid_levels[0]

    def _determine_direction(self, level: MenthorQLevel, snapshot: Dict) -> str:
        """
        Détermine la direction du trade selon:
        - Type de niveau
        - Position du prix par rapport au niveau
        - Contexte marché (bias si disponible)
        """
        current_price = snapshot.get('close', 0)

        # Logique simple: bounce sur support, rejection sur resistance
        if level.level_type in ['put_wall', 'hvl']:
            # Support → LONG si prix proche ou en dessous
            if current_price <= level.price + 0.5:  # ±2 ticks
                return 'LONG'
            else:
                return 'SHORT'

        elif level.level_type in ['call_wall', 'gex_wall']:
            # Resistance → SHORT si prix proche ou au dessus
            if current_price >= level.price - 0.5:
                return 'SHORT'
            else:
                return 'LONG'

        elif level.level_type == 'blind_spot':
            # Blind spots: on trade la rejection
            # Si prix au dessus → SHORT, si en dessous → LONG
            if current_price > level.price:
                return 'SHORT'
            else:
                return 'LONG'

        # Par défaut: LONG si en dessous, SHORT si au dessus
        return 'LONG' if current_price < level.price else 'SHORT'

    def _calculate_sl_tp(
        self,
        entry_price: float,
        direction: str,
        level: MenthorQLevel
    ) -> Tuple[float, float]:
        """
        Calcule SL et TP selon:
        - Direction
        - Type de niveau
        - Prix d'entrée
        """
        # SL/TP en ticks
        sl_ticks = self.sl_ticks_default
        tp_ticks = self.tp_ticks_default

        # Ajustement selon le type de niveau
        if level.level_type == 'gex_wall':
            # GEX walls = fort, on peut élargir TP
            tp_ticks = 25
        elif level.level_type == 'blind_spot':
            # Blind spots = plus volatil, SL/TP serrés
            sl_ticks = 8
            tp_ticks = 18

        # Conversion ticks → prix (1 tick ES = 0.25)
        tick_value = 0.25

        if direction == 'LONG':
            sl = entry_price - (sl_ticks * tick_value)
            tp = entry_price + (tp_ticks * tick_value)
        else:  # SHORT
            sl = entry_price + (sl_ticks * tick_value)
            tp = entry_price - (tp_ticks * tick_value)

        return sl, tp

    def should_enter_trade(self, snapshot: Dict) -> Optional[Dict]:
        """
        Décide si on doit entrer en trade sur ce snapshot

        Returns:
            Dict avec détails du setup si trade, None sinon
        """
        # Extraire les niveaux MenthorQ
        levels = self._extract_menthorq_levels(snapshot)

        if not levels:
            return None

        # Trouver le meilleur niveau
        best_level = self._find_best_level(levels)

        if not best_level:
            return None

        # Déterminer direction
        direction = self._determine_direction(best_level, snapshot)

        # Prix d'entrée
        entry_price = snapshot.get('close', 0)

        # Calculer SL/TP
        sl, tp = self._calculate_sl_tp(entry_price, direction, best_level)

        return {
            'entry_price': entry_price,
            'direction': direction,
            'sl': sl,
            'tp': tp,
            'level': best_level,
            'entry_time': snapshot.get('timestamp'),
            'symbol': snapshot.get('symbol', 'ES')
        }

    def simulate_trade(
        self,
        setup: Dict,
        df_price_data: pd.DataFrame
    ) -> TradeResult:
        """
        Simule l'exécution d'un trade avec gestion SL/TP/TIME

        Args:
            setup: Détails du setup (entry_price, direction, sl, tp, etc.)
            df_price_data: DataFrame avec données de prix tick par tick

        Returns:
            TradeResult avec le résultat du trade
        """
        entry_time = setup['entry_time']
        entry_price = setup['entry_price']
        direction = setup['direction']
        sl = setup['sl']
        tp = setup['tp']
        level = setup['level']

        # Filtrer les données après l'entrée
        df_after_entry = df_price_data[df_price_data.index > entry_time].copy()

        # Temps max en trade
        max_time = entry_time + timedelta(minutes=self.max_trade_duration_minutes)
        df_after_entry = df_after_entry[df_after_entry.index <= max_time]

        if df_after_entry.empty:
            # Pas de données → exit à break-even
            return TradeResult(
                entry_time=entry_time,
                exit_time=entry_time,
                entry_price=entry_price,
                exit_price=entry_price,
                direction=direction,
                pnl_ticks=0,
                exit_reason='NO_DATA',
                level_type=level.level_type,
                level_price=level.price,
                duration_seconds=0
            )

        # Simuler tick par tick
        for timestamp, row in df_after_entry.iterrows():
            high = row.get('high', row.get('close'))
            low = row.get('low', row.get('close'))
            close = row.get('close')

            # Check TP/SL
            if direction == 'LONG':
                # TP hit?
                if high >= tp:
                    pnl_ticks = (tp - entry_price) * 4
                    return TradeResult(
                        entry_time=entry_time,
                        exit_time=timestamp,
                        entry_price=entry_price,
                        exit_price=tp,
                        direction=direction,
                        pnl_ticks=pnl_ticks,
                        exit_reason='TP',
                        level_type=level.level_type,
                        level_price=level.price,
                        duration_seconds=(timestamp - entry_time).total_seconds()
                    )
                # SL hit?
                if low <= sl:
                    pnl_ticks = (sl - entry_price) * 4
                    return TradeResult(
                        entry_time=entry_time,
                        exit_time=timestamp,
                        entry_price=entry_price,
                        exit_price=sl,
                        direction=direction,
                        pnl_ticks=pnl_ticks,
                        exit_reason='SL',
                        level_type=level.level_type,
                        level_price=level.price,
                        duration_seconds=(timestamp - entry_time).total_seconds()
                    )
            else:  # SHORT
                # TP hit?
                if low <= tp:
                    pnl_ticks = (entry_price - tp) * 4
                    return TradeResult(
                        entry_time=entry_time,
                        exit_time=timestamp,
                        entry_price=entry_price,
                        exit_price=tp,
                        direction=direction,
                        pnl_ticks=pnl_ticks,
                        exit_reason='TP',
                        level_type=level.level_type,
                        level_price=level.price,
                        duration_seconds=(timestamp - entry_time).total_seconds()
                    )
                # SL hit?
                if high >= sl:
                    pnl_ticks = (entry_price - sl) * 4
                    return TradeResult(
                        entry_time=entry_time,
                        exit_time=timestamp,
                        entry_price=entry_price,
                        exit_price=sl,
                        direction=direction,
                        pnl_ticks=pnl_ticks,
                        exit_reason='SL',
                        level_type=level.level_type,
                        level_price=level.price,
                        duration_seconds=(timestamp - entry_time).total_seconds()
                    )

        # Temps max atteint → exit au dernier prix
        exit_time = df_after_entry.index[-1]
        exit_price = df_after_entry.iloc[-1]['close']

        if direction == 'LONG':
            pnl_ticks = (exit_price - entry_price) * 4
        else:
            pnl_ticks = (entry_price - exit_price) * 4

        return TradeResult(
            entry_time=entry_time,
            exit_time=exit_time,
            entry_price=entry_price,
            exit_price=exit_price,
            direction=direction,
            pnl_ticks=pnl_ticks,
            exit_reason='TIME',
            level_type=level.level_type,
            level_price=level.price,
            duration_seconds=(exit_time - entry_time).total_seconds()
        )


class MenthorQPureBacktester:
    """
    Backtester pour la stratégie MenthorQ Pure
    """

    def __init__(
        self,
        strategy: MenthorQPureStrategy,
        data_path: str = "ml/data/labeled_trades.parquet"
    ):
        self.strategy = strategy
        self.data_path = Path(data_path)
        self.trades: List[TradeResult] = []

        logger.info("MenthorQPureBacktester initialise")
        logger.info(f"  Data path: {self.data_path}")

    def load_data(self) -> pd.DataFrame:
        """Charge les données de trades"""
        if not self.data_path.exists():
            raise FileNotFoundError(f"Fichier introuvable: {self.data_path}")

        df = pd.read_parquet(self.data_path)
        logger.info(f"Donnees chargees: {len(df)} snapshots")

        # Convertir timestamp si nécessaire
        if 'timestamp' in df.columns and not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
            df['timestamp'] = pd.to_datetime(df['timestamp'])

        if 'timestamp' in df.columns:
            df = df.set_index('timestamp')

        return df

    def run_backtest(self) -> pd.DataFrame:
        """
        Lance le backtest complet

        Logique simplifiée:
        - Charge les trades déjà exécutés (labeled_trades.parquet)
        - Pour chaque trade, vérifie s'il aurait été pris par MenthorQ Pure
        - Garde seulement les trades validés par la stratégie

        Returns:
            DataFrame avec tous les trades validés
        """
        logger.info("Demarrage backtest MenthorQ Pure...")

        # Charger données (trades déjà exécutés)
        df = self.load_data()

        # Pour chaque trade, vérifier si MenthorQ Pure l'aurait pris
        trades_taken = 0
        trades_skipped = 0

        validated_trades = []

        for idx in range(len(df)):
            row = df.iloc[idx]
            snapshot = row.to_dict()

            # Vérifier si on doit entrer selon MenthorQ Pure
            setup = self.strategy.should_enter_trade(snapshot)

            if setup is None:
                trades_skipped += 1
                continue

            # Trade validé par MenthorQ Pure → on garde le résultat réel
            validated_trades.append({
                'entry_time': pd.to_datetime(row.get('entry_time'), unit='ms') if 'entry_time' in row else None,
                'exit_time': None,  # Pas disponible dans les données
                'entry_price': row['entry_price'],
                'exit_price': row['exit_price'],
                'direction': row['direction'],
                'pnl_ticks': row['pnl_ticks'],
                'exit_reason': row.get('exit_reason', 'UNKNOWN'),
                'level_type': setup['level'].level_type,
                'level_price': setup['level'].price,
                'duration_seconds': row.get('duration_minutes', 0) * 60
            })

            trades_taken += 1

            if trades_taken % 100 == 0:
                logger.info(f"  Trades valides: {trades_taken}")

        logger.info(f"Backtest termine: {trades_taken} trades valides, {trades_skipped} rejetes")
        logger.info(f"  Taux selection: {trades_taken/(trades_taken+trades_skipped)*100:.1f}%")

        # Convertir en DataFrame
        if not validated_trades:
            logger.warning("Aucun trade valide!")
            return pd.DataFrame()

        df_trades = pd.DataFrame(validated_trades)

        return df_trades

    def calculate_metrics(self, df_trades: pd.DataFrame) -> Dict:
        """
        Calcule les métriques de performance
        """
        if df_trades.empty:
            return {}

        # P&L brut
        pnl_gross = df_trades['pnl_ticks'].sum()

        # Nombre de trades
        n_trades = len(df_trades)

        # Fees
        fees_total = n_trades * self.strategy.fees_per_trade

        # P&L net
        pnl_net = pnl_gross - fees_total

        # P&L par trade
        pnl_per_trade = pnl_net / n_trades if n_trades > 0 else 0

        # WinRate
        wins = (df_trades['pnl_ticks'] > 0).sum()
        losses = (df_trades['pnl_ticks'] < 0).sum()
        winrate = wins / n_trades if n_trades > 0 else 0

        # Profit Factor
        gross_profit = df_trades[df_trades['pnl_ticks'] > 0]['pnl_ticks'].sum()
        gross_loss = abs(df_trades[df_trades['pnl_ticks'] < 0]['pnl_ticks'].sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else np.inf

        # Sharpe Ratio (simplifié)
        daily_pnl = df_trades.set_index('entry_time')['pnl_ticks'].resample('D').sum()
        sharpe = (daily_pnl.mean() / daily_pnl.std() * np.sqrt(252)) if daily_pnl.std() > 0 else 0

        # Max Drawdown
        cumulative_pnl = df_trades['pnl_ticks'].cumsum()
        running_max = cumulative_pnl.cummax()
        drawdown = running_max - cumulative_pnl
        max_dd = drawdown.max()

        # Durée moyenne
        avg_duration_min = df_trades['duration_seconds'].mean() / 60

        return {
            'pnl_gross': pnl_gross,
            'pnl_net': pnl_net,
            'pnl_per_trade': pnl_per_trade,
            'n_trades': n_trades,
            'n_wins': wins,
            'n_losses': losses,
            'winrate': winrate,
            'profit_factor': profit_factor,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_dd,
            'avg_duration_min': avg_duration_min,
            'fees_total': fees_total
        }

    def generate_comparison_report(
        self,
        df_trades: pd.DataFrame,
        metrics: Dict,
        baseline_metrics: Dict = None
    ) -> str:
        """
        Génère un rapport comparatif avec T4 Baseline
        """
        report = []
        report.append("=" * 80)
        report.append("RAPPORT COMPARATIF: MENTHORQ PURE vs T4 BASELINE")
        report.append("=" * 80)
        report.append("")

        # Métriques MenthorQ Pure
        report.append("## MENTHORQ PURE STRATEGY")
        report.append("")
        report.append(f"P&L Brut:        {metrics['pnl_gross']:+.2f} ticks")
        report.append(f"Fees:            -{metrics['fees_total']:.2f} ticks")
        report.append(f"P&L Net:         {metrics['pnl_net']:+.2f} ticks")
        report.append(f"P&L/trade:       {metrics['pnl_per_trade']:+.3f} ticks")
        report.append("")
        report.append(f"Trades:          {metrics['n_trades']}")
        report.append(f"Wins:            {metrics['n_wins']} ({metrics['winrate']*100:.1f}%)")
        report.append(f"Losses:          {metrics['n_losses']}")
        report.append(f"Profit Factor:   {metrics['profit_factor']:.2f}")
        report.append(f"Sharpe Ratio:    {metrics['sharpe_ratio']:.2f}")
        report.append(f"Max Drawdown:    {metrics['max_drawdown']:.2f} ticks")
        report.append(f"Duree moy:       {metrics['avg_duration_min']:.1f} min")
        report.append("")

        # Baseline (si fournie)
        if baseline_metrics:
            report.append("## T4 BASELINE (Reference)")
            report.append("")
            report.append(f"P&L Net:         {baseline_metrics.get('pnl_net', 0):+.2f} ticks")
            report.append(f"P&L/trade:       {baseline_metrics.get('pnl_per_trade', 0):+.3f} ticks")
            report.append(f"Trades:          {baseline_metrics.get('n_trades', 0)}")
            report.append(f"WinRate:         {baseline_metrics.get('winrate', 0)*100:.1f}%")
            report.append("")

            # Comparaison
            report.append("## COMPARAISON")
            report.append("")
            delta_pnl = metrics['pnl_per_trade'] - baseline_metrics.get('pnl_per_trade', 0)
            delta_pct = (delta_pnl / baseline_metrics.get('pnl_per_trade', 1)) * 100

            symbol = "+" if delta_pnl > 0 else ""
            report.append(f"Delta P&L/trade: {symbol}{delta_pnl:.3f} ticks ({symbol}{delta_pct:.1f}%)")

            if delta_pnl > 0.10:
                report.append("VERDICT: MENTHORQ PURE > BASELINE [OK]")
            elif delta_pnl > -0.10:
                report.append("VERDICT: MENTHORQ PURE = BASELINE (equivalent)")
            else:
                report.append("VERDICT: MENTHORQ PURE < BASELINE [ECHEC]")

        report.append("")
        report.append("=" * 80)

        return "\n".join(report)


def main():
    """Point d'entrée principal"""

    logger.info("=" * 80)
    logger.info("MENTHORQ PURE BACKTEST")
    logger.info("=" * 80)
    logger.info("")

    # Créer la stratégie
    strategy = MenthorQPureStrategy(
        max_distance_ticks=10,  # Élargi de 3 à 10 ticks
        min_level_strength=50.0,  # Réduit de 60 à 50
        sl_ticks_default=10,
        tp_ticks_default=20,
        max_trade_duration_minutes=8,
        fees_per_trade=0.12  # OPTION A: PropFirms Moyennes (Apex/TopStep/Elite)
    )

    # Créer le backtester
    backtester = MenthorQPureBacktester(
        strategy=strategy,
        data_path="ml/data/labeled_trades.parquet"
    )

    # Lancer le backtest
    df_trades = backtester.run_backtest()

    if df_trades.empty:
        logger.error("Aucun trade genere! Verifiez les parametres.")
        return

    # Calculer métriques
    metrics = backtester.calculate_metrics(df_trades)

    # Métriques baseline (T4) - Avec fees correctes (0.12t au lieu de 0.62t)
    baseline_metrics = {
        'pnl_net': 800.0,  # Recalculé avec fees 0.12t: +920t brut - 120t fees
        'pnl_per_trade': 0.80,  # Au lieu de 0.30t avec fees incorrectes
        'n_trades': 1000,
        'winrate': 0.48
    }

    # Générer rapport
    report = backtester.generate_comparison_report(df_trades, metrics, baseline_metrics)

    print("")
    print(report)

    # Sauvegarder résultats
    output_dir = Path("ml/output")
    output_dir.mkdir(exist_ok=True)

    # Sauvegarder trades
    trades_file = output_dir / f"menthorq_pure_trades_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df_trades.to_csv(trades_file, index=False)
    logger.info(f"Trades sauvegardes: {trades_file}")

    # Sauvegarder rapport
    report_file = output_dir / f"menthorq_pure_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    report_file.write_text(report)
    logger.info(f"Rapport sauvegarde: {report_file}")

    logger.info("")
    logger.info("BACKTEST TERMINE ✅")


if __name__ == "__main__":
    main()
