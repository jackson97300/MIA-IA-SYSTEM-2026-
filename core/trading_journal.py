"""
📔 TRADING JOURNAL AUTOMATISÉ
Génère un rapport détaillé quotidien avec analyse et leçons apprises
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class TradingJournal:
    """Journal de trading automatisé avec analyse détaillée"""
    
    def __init__(self, journal_dir: str = "trading_journal"):
        self.journal_dir = Path(journal_dir)
        self.journal_dir.mkdir(exist_ok=True)
        
        # Fichiers de données
        self.trades_file = self.journal_dir / "trades_history.jsonl"
        self.rejections_file = self.journal_dir / "rejections_history.jsonl"
        self.session_data = {}
        
    def log_trade(self, trade_data: Dict[str, Any]) -> None:
        """Enregistre un trade exécuté"""
        trade_data['timestamp'] = datetime.now().isoformat()
        trade_data['type'] = 'TRADE'
        
        with open(self.trades_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(trade_data, ensure_ascii=False) + '\n')
    
    def log_rejection(self, rejection_data: Dict[str, Any]) -> None:
        """Enregistre un signal rejeté avec raison"""
        rejection_data['timestamp'] = datetime.now().isoformat()
        rejection_data['type'] = 'REJECTION'
        
        with open(self.rejections_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(rejection_data, ensure_ascii=False) + '\n')
    
    def _read_jsonl(self, filepath: Path, date_filter: Optional[str] = None) -> List[Dict]:
        """Lit un fichier JSONL et filtre par date"""
        if not filepath.exists():
            return []
        
        entries = []
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    
                    # Filtrer par date si spécifié
                    if date_filter:
                        entry_date = entry['timestamp'][:10]  # YYYY-MM-DD
                        if entry_date != date_filter:
                            continue
                    
                    entries.append(entry)
                except Exception as e:
                    logger.error(f"Erreur lecture ligne journal: {e}")
                    continue
        
        return entries
    
    def _analyze_rejections(self, rejections: List[Dict]) -> Dict[str, Any]:
        """Analyse les rejets pour identifier patterns"""
        if not rejections:
            return {}
        
        rejection_reasons = {}
        by_symbol = {}
        by_strategy = {}
        
        for rej in rejections:
            # Count reasons
            reason = rej.get('reason', 'UNKNOWN')
            rejection_reasons[reason] = rejection_reasons.get(reason, 0) + 1
            
            # Count by symbol
            symbol = rej.get('symbol', 'UNKNOWN')
            by_symbol[symbol] = by_symbol.get(symbol, 0) + 1
            
            # Count by strategy
            strategy = rej.get('strategy', 'UNKNOWN')
            by_strategy[strategy] = by_strategy.get(strategy, 0) + 1
        
        # Sort by frequency
        rejection_reasons = dict(sorted(rejection_reasons.items(), key=lambda x: x[1], reverse=True))
        
        return {
            'total': len(rejections),
            'reasons': rejection_reasons,
            'by_symbol': by_symbol,
            'by_strategy': by_strategy
        }
    
    def _analyze_trades(self, trades: List[Dict]) -> Dict[str, Any]:
        """Analyse des trades exécutés"""
        if not trades:
            return {}
        
        wins = [t for t in trades if t.get('pnl', 0) > 0]
        losses = [t for t in trades if t.get('pnl', 0) < 0]
        
        total_pnl = sum(t.get('pnl', 0) for t in trades)
        total_fees = sum(t.get('fees', 0) for t in trades)
        
        win_rate = len(wins) / len(trades) if trades else 0
        
        # Analyze by symbol
        by_symbol = {}
        for t in trades:
            symbol = t.get('symbol', 'UNKNOWN')
            if symbol not in by_symbol:
                by_symbol[symbol] = {
                    'trades': [],
                    'pnl': 0,
                    'wins': 0,
                    'losses': 0
                }
            by_symbol[symbol]['trades'].append(t)
            by_symbol[symbol]['pnl'] += t.get('pnl', 0)
            if t.get('pnl', 0) > 0:
                by_symbol[symbol]['wins'] += 1
            else:
                by_symbol[symbol]['losses'] += 1
        
        # Calculate stats per symbol
        for symbol, data in by_symbol.items():
            total = data['wins'] + data['losses']
            data['win_rate'] = data['wins'] / total if total > 0 else 0
            
            # Profit Factor
            gross_profit = sum(t.get('pnl', 0) for t in data['trades'] if t.get('pnl', 0) > 0)
            gross_loss = abs(sum(t.get('pnl', 0) for t in data['trades'] if t.get('pnl', 0) < 0))
            data['profit_factor'] = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # Analyze by strategy
        by_strategy = {}
        for t in trades:
            strategy = t.get('strategy', 'UNKNOWN')
            if strategy not in by_strategy:
                by_strategy[strategy] = {
                    'trades': [],
                    'pnl': 0,
                    'wins': 0,
                    'losses': 0
                }
            by_strategy[strategy]['trades'].append(t)
            by_strategy[strategy]['pnl'] += t.get('pnl', 0)
            if t.get('pnl', 0) > 0:
                by_strategy[strategy]['wins'] += 1
            else:
                by_strategy[strategy]['losses'] += 1
        
        # Calculate stats per strategy
        for strategy, data in by_strategy.items():
            total = data['wins'] + data['losses']
            data['win_rate'] = data['wins'] / total if total > 0 else 0
            
            # Profit Factor
            gross_profit = sum(t.get('pnl', 0) for t in data['trades'] if t.get('pnl', 0) > 0)
            gross_loss = abs(sum(t.get('pnl', 0) for t in data['trades'] if t.get('pnl', 0) < 0))
            data['profit_factor'] = gross_profit / gross_loss if gross_loss > 0 else 0
        
        return {
            'total_trades': len(trades),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'total_fees': total_fees,
            'net_pnl': total_pnl - total_fees,
            'by_symbol': by_symbol,
            'by_strategy': by_strategy
        }
    
    def _generate_lessons_learned(self, trades_analysis: Dict, rejections_analysis: Dict) -> List[str]:
        """Génère automatiquement les leçons apprises"""
        lessons = []
        
        if not trades_analysis:
            lessons.append("⚠️ Aucun trade exécuté aujourd'hui")
            return lessons
        
        # Win Rate Analysis
        wr = trades_analysis.get('win_rate', 0)
        if wr >= 0.5:
            lessons.append(f"✅ Excellent Win Rate: {wr*100:.1f}% (maintenir stratégies actuelles)")
        elif wr >= 0.4:
            lessons.append(f"⚠️ Win Rate acceptable: {wr*100:.1f}% (optimiser filtres)")
        else:
            lessons.append(f"❌ Win Rate faible: {wr*100:.1f}% (réviser stratégies)")
        
        # Symbol Performance
        by_symbol = trades_analysis.get('by_symbol', {})
        if by_symbol:
            # Best symbol
            best_symbol = max(by_symbol.items(), key=lambda x: x[1]['pnl'])
            lessons.append(f"🏆 Meilleur marché: {best_symbol[0]} (+${best_symbol[1]['pnl']:.2f}, WR {best_symbol[1]['win_rate']*100:.0f}%)")
            
            # Worst symbol
            worst_symbol = min(by_symbol.items(), key=lambda x: x[1]['pnl'])
            if worst_symbol[1]['pnl'] < -100:
                lessons.append(f"⚠️ Pire marché: {worst_symbol[0]} (${worst_symbol[1]['pnl']:.2f}) → Réduire exposition ou désactiver")
        
        # Strategy Performance
        by_strategy = trades_analysis.get('by_strategy', {})
        if by_strategy:
            # Best strategy
            best_strat = max(by_strategy.items(), key=lambda x: x[1]['pnl'])
            lessons.append(f"🎯 Meilleure stratégie: {best_strat[0]} (+${best_strat[1]['pnl']:.2f}, WR {best_strat[1]['win_rate']*100:.0f}%)")
            
            # Underperforming strategies
            for strat_name, data in by_strategy.items():
                if data['pnl'] < -100:
                    lessons.append(f"❌ Stratégie sous-performante: {strat_name} (${data['pnl']:.2f}) → Réviser ou désactiver")
        
        # Rejection Analysis
        if rejections_analysis:
            top_rejection = list(rejections_analysis.get('reasons', {}).items())[0] if rejections_analysis.get('reasons') else None
            if top_rejection:
                reason, count = top_rejection
                total_signals = trades_analysis['total_trades'] + rejections_analysis['total']
                pct = (count / total_signals * 100) if total_signals > 0 else 0
                lessons.append(f"🚫 Rejet principal: {reason} ({count} fois, {pct:.0f}%) → Calibrer filtres")
        
        return lessons
    
    def _generate_recommendations(self, trades_analysis: Dict, rejections_analysis: Dict) -> List[str]:
        """Génère des recommandations actionnables"""
        recommendations = []
        
        if not trades_analysis:
            return ["🔧 Vérifier connexion données et filtres de trading"]
        
        # Win Rate recommendations
        wr = trades_analysis.get('win_rate', 0)
        if wr < 0.4:
            recommendations.append("🔧 Augmenter seuils de confidence minimum (50% → 60%)")
            recommendations.append("🔧 Activer mode filtrage strict (confluence > 0.7)")
        
        # Symbol-specific recommendations
        by_symbol = trades_analysis.get('by_symbol', {})
        for symbol, data in by_symbol.items():
            if data['pnl'] < -150:
                recommendations.append(f"⚠️ {symbol}: Réduire taille position ou désactiver temporairement")
            elif data['win_rate'] < 0.3:
                recommendations.append(f"⚠️ {symbol}: Augmenter cooldown entre trades (3min → 5min)")
        
        # Strategy-specific recommendations
        by_strategy = trades_analysis.get('by_strategy', {})
        for strat_name, data in by_strategy.items():
            if data['profit_factor'] < 0.8:
                recommendations.append(f"🔧 {strat_name}: PF faible ({data['profit_factor']:.2f}) → Réviser paramètres")
        
        # Rejection-based recommendations
        if rejections_analysis:
            reasons = rejections_analysis.get('reasons', {})
            if 'Layer 2: OrderFlow rejects' in reasons:
                count = reasons['Layer 2: OrderFlow rejects']
                if count > 20:
                    recommendations.append("🔧 OrderFlow trop strict → Assouplir règle 2/3 → 1/3")
            
            if 'Insufficient confidence across layers' in reasons:
                count = reasons['Insufficient confidence across layers']
                if count > 15:
                    recommendations.append("🔧 Confidence insuffisante fréquente → Revoir pondération layers")
        
        if not recommendations:
            recommendations.append("✅ Système performant, maintenir configuration actuelle")
        
        return recommendations
    
    def generate_daily_report(self, date: Optional[str] = None) -> str:
        """
        Génère le rapport journalier complet
        
        Args:
            date: Date au format YYYY-MM-DD (aujourd'hui par défaut)
        
        Returns:
            Contenu du rapport en markdown
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        # Lire les données
        trades = self._read_jsonl(self.trades_file, date)
        rejections = self._read_jsonl(self.rejections_file, date)
        
        # Analyser
        trades_analysis = self._analyze_trades(trades)
        rejections_analysis = self._analyze_rejections(rejections)
        
        # Générer insights
        lessons = self._generate_lessons_learned(trades_analysis, rejections_analysis)
        recommendations = self._generate_recommendations(trades_analysis, rejections_analysis)
        
        # Construire le rapport
        report_lines = [
            f"# 📔 JOURNAL DE TRADING — {date}",
            "",
            f"*Généré automatiquement le {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
            "",
            "---",
            "",
            "## 📊 RÉSUMÉ DES PERFORMANCES",
            ""
        ]
        
        if trades_analysis:
            ta = trades_analysis
            report_lines.extend([
                f"**P&L Net**: ${ta['net_pnl']:.2f} (fees: ${ta['total_fees']:.2f})",
                f"**Trades**: {ta['total_trades']} | **Win Rate**: {ta['win_rate']*100:.0f}%",
                ""
            ])
            
            # Performance par marché
            if ta.get('by_symbol'):
                report_lines.append("### 📈 Performance par Marché")
                report_lines.append("")
                for symbol, data in sorted(ta['by_symbol'].items(), key=lambda x: x[1]['pnl'], reverse=True):
                    total = data['wins'] + data['losses']
                    report_lines.append(
                        f"- **{symbol}**: {total}T | WR {data['win_rate']*100:.0f}% | "
                        f"PF {data['profit_factor']:.1f} | P&L ${data['pnl']:.2f}"
                    )
                report_lines.append("")
            
            # Performance par stratégie
            if ta.get('by_strategy'):
                report_lines.append("### 🎯 Performance par Stratégie")
                report_lines.append("")
                for strat, data in sorted(ta['by_strategy'].items(), key=lambda x: x[1]['pnl'], reverse=True):
                    total = data['wins'] + data['losses']
                    report_lines.append(
                        f"- **{strat}**: {total}T | WR {data['win_rate']*100:.0f}% | "
                        f"PF {data['profit_factor']:.1f} | P&L ${data['pnl']:.2f}"
                    )
                report_lines.append("")
        else:
            report_lines.append("*Aucun trade exécuté aujourd'hui*")
            report_lines.append("")
        
        # Analyse des rejets
        if rejections_analysis:
            report_lines.extend([
                "## 🚫 ANALYSE DES REJETS",
                "",
                f"**Total rejets**: {rejections_analysis['total']}",
                ""
            ])
            
            if rejections_analysis.get('reasons'):
                report_lines.append("### Raisons principales:")
                report_lines.append("")
                for reason, count in list(rejections_analysis['reasons'].items())[:5]:
                    pct = (count / rejections_analysis['total'] * 100)
                    report_lines.append(f"- {reason}: **{count}** fois ({pct:.0f}%)")
                report_lines.append("")
        
        # Leçons apprises
        report_lines.extend([
            "## 💡 LEÇONS APPRISES",
            ""
        ])
        for lesson in lessons:
            report_lines.append(f"{lesson}")
        report_lines.append("")
        
        # Recommandations
        report_lines.extend([
            "## 🎯 ACTIONS RECOMMANDÉES",
            ""
        ])
        for rec in recommendations:
            report_lines.append(f"{rec}")
        report_lines.append("")
        
        # Footer
        report_lines.extend([
            "---",
            "",
            "*Ce rapport est généré automatiquement. Consultez les logs détaillés pour plus d'informations.*"
        ])
        
        return "\n".join(report_lines)
    
    def save_daily_report(self, date: Optional[str] = None) -> Path:
        """Génère et sauvegarde le rapport journalier"""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        report_content = self.generate_daily_report(date)
        
        # Sauvegarder
        report_file = self.journal_dir / f"journal_{date}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        logger.info(f"📔 Journal journalier sauvegardé: {report_file}")
        return report_file


# Instance globale
_journal_instance = None

def get_trading_journal() -> TradingJournal:
    """Récupère l'instance du journal (singleton)"""
    global _journal_instance
    if _journal_instance is None:
        _journal_instance = TradingJournal()
    return _journal_instance


