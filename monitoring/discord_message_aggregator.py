#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DISCORD MESSAGE AGGREGATOR - Anti-Spam System
Groupe les messages similaires pour éviter le flood Discord
"""

import time
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)


class DiscordMessageAggregator:
    """
    Agrégateur de messages Discord pour anti-spam
    
    Groupe les messages similaires par catégorie/fenêtre temporelle
    et envoie un résumé groupé au lieu de multiples messages individuels.
    
    Exemple:
        Au lieu de:
        - "Signal rejeté (ML < 0.60)" x 15 fois
        
        Envoie:
        - "15 signaux rejetés (ML < 0.60) en 10 minutes"
    """
    
    def __init__(self, window_minutes: int = 10, max_buffer_size: int = 100):
        """
        Args:
            window_minutes: Durée fenêtre d'agrégation (défaut 10 min)
            max_buffer_size: Taille max du buffer avant flush forcé
        """
        self.window_minutes = window_minutes
        self.max_buffer_size = max_buffer_size
        
        # Buffers par catégorie
        self.message_buffers: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.last_flush: Dict[str, float] = {}
        
        # Stats
        self.stats = {
            'messages_buffered': 0,
            'messages_flushed': 0,
            'categories': set()
        }
        
        logger.info(f"✅ DiscordMessageAggregator initialisé (fenêtre: {window_minutes} min)")
    
    def add_message(self, category: str, message_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Ajoute un message au buffer
        
        Args:
            category: Catégorie du message (ex: 'signal_rejected', 'warning_vix')
            message_data: Données du message {title, description, timestamp, ...}
        
        Returns:
            Dict avec message groupé si fenêtre complète, sinon None
        """
        # Initialiser catégorie si nouvelle
        if category not in self.last_flush:
            self.last_flush[category] = time.time()
            self.stats['categories'].add(category)
        
        # Ajouter timestamp si absent
        if 'timestamp' not in message_data:
            message_data['timestamp'] = time.time()
        
        # Ajouter au buffer
        self.message_buffers[category].append(message_data)
        self.stats['messages_buffered'] += 1
        
        # Vérifier si flush nécessaire
        time_since_flush = time.time() - self.last_flush[category]
        buffer_size = len(self.message_buffers[category])
        
        # Flush si fenêtre dépassée OU buffer plein
        if time_since_flush > self.window_minutes * 60 or buffer_size >= self.max_buffer_size:
            return self.flush_category(category)
        
        return None
    
    def flush_category(self, category: str) -> Optional[Dict[str, Any]]:
        """
        Flush une catégorie et retourne message groupé
        
        Args:
            category: Catégorie à flush
        
        Returns:
            Dict avec résumé groupé
        """
        messages = self.message_buffers.get(category, [])
        if not messages:
            return None
        
        count = len(messages)
        
        # Calculer durée réelle de la fenêtre
        first_timestamp = messages[0]['timestamp']
        last_timestamp = messages[-1]['timestamp']
        duration_minutes = (last_timestamp - first_timestamp) / 60.0
        
        # Extraire informations communes
        reasons = defaultdict(int)
        for msg in messages:
            reason = msg.get('reason', 'Unknown')
            reasons[reason] += 1
        
        # Top 3 raisons
        top_reasons = sorted(reasons.items(), key=lambda x: x[1], reverse=True)[:3]
        
        # Créer message groupé
        grouped_message = {
            'category': category,
            'count': count,
            'duration_minutes': duration_minutes,
            'window_minutes': self.window_minutes,
            'top_reasons': top_reasons,
            'timestamp': datetime.now(),
            'summary': self._create_summary(category, count, duration_minutes, top_reasons)
        }
        
        # Reset buffer
        self.message_buffers[category] = []
        self.last_flush[category] = time.time()
        self.stats['messages_flushed'] += count
        
        logger.info(f"📊 Flush {category}: {count} messages groupés ({duration_minutes:.1f} min)")
        
        return grouped_message
    
    def _create_summary(self, category: str, count: int, duration_minutes: float, 
                       top_reasons: List[tuple]) -> str:
        """Crée résumé formaté"""
        
        # Titres par catégorie
        titles = {
            'signal_rejected': '🚫 SIGNAUX REJETÉS',
            'warning_vix': '⚠️ ALERTES VIX',
            'warning_latency': '⏱️ ALERTES LATENCE',
            'error_network': '🌐 ERREURS RÉSEAU',
            'error_data': '📊 ERREURS DATA'
        }
        
        title = titles.get(category, f'📋 {category.upper()}')
        
        # Construire résumé
        summary = f"""
**{title}**

**Total:** {count} événements en {duration_minutes:.1f} minutes

**Top raisons:**
"""
        
        for i, (reason, cnt) in enumerate(top_reasons, 1):
            summary += f"\n{i}. {reason}: {cnt}x ({cnt/count*100:.1f}%)"
        
        return summary.strip()
    
    def flush_all(self) -> List[Dict[str, Any]]:
        """
        Flush toutes les catégories
        
        Returns:
            Liste de messages groupés
        """
        grouped_messages = []
        
        for category in list(self.message_buffers.keys()):
            grouped = self.flush_category(category)
            if grouped:
                grouped_messages.append(grouped)
        
        logger.info(f"📊 Flush ALL: {len(grouped_messages)} catégories flushed")
        return grouped_messages
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne statistiques"""
        return {
            'messages_buffered': self.stats['messages_buffered'],
            'messages_flushed': self.stats['messages_flushed'],
            'categories_count': len(self.stats['categories']),
            'categories': list(self.stats['categories']),
            'current_buffer_sizes': {
                cat: len(buf) for cat, buf in self.message_buffers.items() if buf
            }
        }
    
    def should_aggregate(self, category: str) -> bool:
        """
        Vérifie si une catégorie doit être agrégée
        
        Certaines catégories critiques ne doivent jamais être agrégées
        (ex: trades, kill switch)
        """
        # Catégories à ne JAMAIS agréger
        never_aggregate = [
            'trade_executions',
            'trade_closed',
            'kill_switch',
            'critical_errors',
            'daily_summary',
            'heartbeat'
        ]
        
        return category not in never_aggregate


# Factory function
def create_message_aggregator(window_minutes: int = 10, max_buffer_size: int = 100):
    """Crée aggregator avec config"""
    return DiscordMessageAggregator(window_minutes, max_buffer_size)


# Test
if __name__ == "__main__":
    import asyncio
    
    async def test():
        print("🧪 Test DiscordMessageAggregator")
        
        aggregator = create_message_aggregator(window_minutes=1)
        
        # Simuler 10 rejets en 30 secondes
        for i in range(10):
            result = aggregator.add_message(
                'signal_rejected',
                {
                    'title': f'Signal rejeté #{i+1}',
                    'reason': 'ML confidence < 0.60' if i % 2 == 0 else 'VIX trop élevé',
                    'description': f'Rejet test {i+1}'
                }
            )
            
            if result:
                print(f"\n📊 MESSAGE GROUPÉ:")
                print(result['summary'])
            
            await asyncio.sleep(0.1)
        
        # Attendre 1 minute puis flush
        print("\n⏳ Attente 1 minute...")
        await asyncio.sleep(61)
        
        # Force flush
        grouped = aggregator.flush_category('signal_rejected')
        if grouped:
            print(f"\n📊 FLUSH FORCÉ:")
            print(grouped['summary'])
        
        # Stats
        stats = aggregator.get_stats()
        print(f"\n📊 STATS:")
        print(f"   Messages buffered: {stats['messages_buffered']}")
        print(f"   Messages flushed: {stats['messages_flushed']}")
        print(f"   Categories: {stats['categories']}")
        print("\n✅ Test terminé")
    
    asyncio.run(test())

