#!/usr/bin/env python3
"""
MIA_IA_SYSTEM - Discord Notifier Multi-Webhooks (Version Étendue)
Configuration avec vos 7 webhooks Discord (ajout #logs et #backtest)
Phase 1: Embeds professionnels intégrés
"""

import json
import logging
import asyncio
import aiohttp
from typing import Dict, Optional, Any, List
from datetime import datetime
from pathlib import Path
import time

# ✨ Import styles & embeds professionnels
from monitoring.discord_styles import (
    build_trade_opened_embed,
    build_trade_closed_embed,
    build_heartbeat_embed,
    build_daily_summary_embed  # ✨ Phase 2.3
)

logger = logging.getLogger(__name__)

# VOS WEBHOOKS CONFIGURÉS (ÉTENDU AVEC #LOGS ET #BACKTEST)
CONFIGURED_WEBHOOKS = {
    "trades_webhook": "https://discordapp.com/api/webhooks/1389206251287609374/X4n1-OQLbW0kfkZenmg2GG0k_0a90PbWMTzgySv4uh6levLeXifEEn8cXtf__EWRWKbd",
    "alertes_webhook": "https://discordapp.com/api/webhooks/1389207100550414429/U0vrnm6tnOyWbbAtjA-phA6FZfNKLz0rWV5UyR6NaY90XdsmOKPZHwo1BqQj67VCfqoq",
    "performance_webhook": "https://discordapp.com/api/webhooks/1389206948745842818/3B-CjZ0jw5poaYtp7B6oktAGQAizo-fLDLFO0JHClC7RPXLltIGd8QtxttppFe-Wkyme",
    "signal_webhook": "https://discordapp.com/api/webhooks/1389206780822687756/rFOdqy1K20rA2a70bkjzZ2XZQ8Q3BGSVcMWmU5xN5zEq-UMPwFNMr5Tfqa0aFSzkzjTy",
    "admin_webhook": "https://discordapp.com/api/webhooks/1389206555282640987/v0WvrD3ntDkwGJIyxRh0EEAFNoh1NpSY8Oloxy8tWMZjsFGRed_OYpG1zaSdP2dWH2j7",
    # 🆕 NOUVEAUX WEBHOOKS
    "logs_webhook": "https://discordapp.com/api/webhooks/1390111589146820669/lh5qRGOtJ1TpZXXAlVGM8DYgu54pZxJ3By96Ibeg0FCBXj6zEENE5zYjBX8KTeYN_d9m",
    "backtest_webhook": "https://discordapp.com/api/webhooks/1390111994337689620/8Ot44JzHmJEqEe_AKSrmJ17ANYxYmLK2-_Xg6iqU--08YmC5U0K7bQxy7JDuh-XCssOd",
    # 🆕 WEBHOOKS TRADES PAR SYMBOLE (17/11/2025)
    "trades_es_webhook": "https://discordapp.com/api/webhooks/1440116834992128050/uRiFpNyxLitwDJISRP6hiFGaCOCyNbe1e82aCbk9_dXZRr4RnYs74EPgijh9EjR5cxJl",
    "trades_nq_webhook": "https://discordapp.com/api/webhooks/1440117242845991024/-pzicBzNdPmKpagCThu7649YjBemzCNjx4vzp16exZm-1JUfpDv5K3sydUywEEhcbDaF",
    "trades_rty_webhook": "https://discordapp.com/api/webhooks/1440117462845751479/8cZdev-4-p6P7wvPUTXDNSWFUC_0VCCJpUT6cYl1QGDeCWpYaoF3xkLP9f7IG484pBfa",
    # 🆕 WEBHOOK MONITORING (17/11/2025)
    "monitoring_webhook": "https://discordapp.com/api/webhooks/1440118650190303364/mxT0RO1kbA8mNNaDRWLSjg2Y7-KS56ym3gh5THjdswhHyASn80kmfXts_cxqFDGnsHj9",
    # 🆕 WEBHOOK TRADES ALL (17/11/2025)
    "trades_all_webhook": "https://discordapp.com/api/webhooks/1440120214476820622/RTtUmwUB6APBVJquOK219P5upiYfXUqE5kY1FWQ40ljP1IkcWmcZfRKw0YKTq9fygB_I"
}

class MultiWebhookDiscordNotifier:
    """Discord Notifier avec vos 12 webhooks - chaque message va au bon channel

    ✅ 17/11/2025: Ajout webhooks trades par symbole (#trades-es, #trades-nq, #trades-rty)
    ✅ 17/11/2025: Ajout webhook monitoring (#monitoring)
    ✅ 17/11/2025: Ajout webhook trades-all (#trades-all)
    """

    def __init__(self):
        """Initialise avec vos webhooks"""
        self.config = self._load_config()
        self.session = None
        self.stats = {'messages_sent': 0, 'messages_failed': 0, 'messages_retried': 0}

        # 🆕 MESSAGE QUEUE pour robustesse
        self.message_queue: List[Dict[str, Any]] = []
        self.is_processing_queue = False
        self.max_queue_size = 100

        # 🆕 RATE LIMITING
        self.last_message_time = 0
        self.messages_this_minute = 0
        self.minute_start = time.time()
        self.max_messages_per_minute = 10

        if self.config:
            webhooks = self.config.get('webhooks', {})
            logger.info(f"🔗 Mode MULTI-WEBHOOK configuré ({len(webhooks)} webhooks)")
            logger.info("✅ Configuration MULTI-WEBHOOK validée")
            logger.info("✅ MultiWebhookDiscordNotifier initialisé avec Queue & Retry")

    def _find_config_file(self) -> Optional[str]:
        """Trouve automation_params.json"""
        possible_locations = [
            'automation_params.json',
            'config_files/automation_params.json',
            'config/automation_params.json',
            '../automation_params.json'
        ]

        for location in possible_locations:
            if Path(location).exists():
                return location
        return None

    def _load_config(self) -> Dict:
        """Charge config avec fallback vers webhooks hardcodés"""
        config_path = self._find_config_file()

        # Configuration de base avec webhooks hardcodés
        base_config = {
            'mode': 'multi_webhook',
            'webhooks': CONFIGURED_WEBHOOKS
        }

        if not config_path:
            logger.info("✅ Utilisation webhooks hardcodés (config non trouvée)")
            return base_config

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            discord_config = config.get('notifications', {}).get('discord_integration', {})

            # Vérifier multi-webhooks dans config
            multi_config = discord_config.get('multi_webhooks', {})
            if multi_config.get('enabled', False):
                config_webhooks = multi_config.get('webhooks', {})
                if config_webhooks:
                    # 🆕 FUSIONNER avec les webhooks hardcodés pour garantir la compatibilité
                    merged_webhooks = CONFIGURED_WEBHOOKS.copy()
                    merged_webhooks.update(config_webhooks)

                    logger.info(f"✅ Multi-webhooks depuis config + hardcodés: {len(merged_webhooks)} webhooks")
                    return {
                        'mode': 'multi_webhook',
                        'webhooks': merged_webhooks,
                        'channels': discord_config.get('channels', {}),
                        'channel_mapping': discord_config.get('channel_mapping', {})
                    }

            # Fallback vers webhooks hardcodés
            logger.info("✅ Fallback vers webhooks hardcodés")
            return base_config

        except Exception as e:
            logger.error(f"Erreur lecture config: {e}")
            logger.info("✅ Utilisation webhooks hardcodés (erreur config)")
            return base_config

    def _get_webhook_for_channel_type(self, channel_type: str) -> Optional[str]:
        """Obtient l'URL webhook pour un type de channel"""
        webhooks = self.config.get('webhooks', {})

        # Mapping précis de vos channels vers vos webhooks (COMPLET)
        webhook_mappings = {
            # Channels existants
            'trade_executions': 'trades_webhook',
            'post_mortem_analysis': 'trades_webhook',
            'system_alerts': 'alertes_webhook',
            'critical_errors': 'alertes_webhook',
            'performance_milestones': 'performance_webhook',
            'daily_summary': 'performance_webhook',
            'signals_analysis': 'signal_webhook',
            'admin_messages': 'admin_webhook',
            'system_status': 'admin_webhook',
            'main_trading': 'trades_webhook',
            'general_info': 'admin_webhook',

            # Channels logs et backtest
            'technical_logs': 'logs_webhook',
            'error_logs': 'logs_webhook',
            'audit_logs': 'logs_webhook',
            'config_changes': 'logs_webhook',
            'network_logs': 'logs_webhook',
            'backtest_results': 'backtest_webhook',
            'strategy_optimization': 'backtest_webhook',
            'performance_comparison': 'backtest_webhook',
            'ab_testing': 'backtest_webhook',
            'pattern_analysis': 'backtest_webhook',

            # 🆕 ASSISTANT TRADING PERSONNEL
            'trading_assistant': 'mia_ia_trading_webhook',
            'opportunity_alert': 'mia_ia_trading_webhook',
            'position_management': 'mia_ia_trading_webhook',
            'market_insights': 'mia_ia_trading_webhook',
            'setup_confirmation': 'mia_ia_trading_webhook',
            'risk_alert': 'mia_ia_trading_webhook',
            'live_dashboard': 'mia_ia_trading_webhook',

            # 🆕 MONITORING (17/11/2025)
            'system_monitoring': 'monitoring_webhook',
            'health_check': 'monitoring_webhook',
            'heartbeat': 'monitoring_webhook',
            'system_metrics': 'monitoring_webhook'
        }

        webhook_key = webhook_mappings.get(channel_type)
        if webhook_key and webhook_key in webhooks:
            webhook_url = webhooks[webhook_key]
            logger.debug(f"Webhook résolu: {channel_type} → {webhook_key}")
            return webhook_url

        # Fallback vers webhook trades
        if 'trades_webhook' in webhooks:
            logger.warning(f"Fallback trades webhook pour {channel_type}")
            return webhooks['trades_webhook']

        logger.error(f"Aucun webhook trouvé pour {channel_type}")
        return None

    def _get_webhook_for_symbol(self, symbol: str) -> Optional[str]:
        """
        ✅ 17/11/2025: Obtient l'URL webhook pour un symbole spécifique

        Routing:
        - ES → trades_es_webhook (#trades-es)
        - NQ → trades_nq_webhook (#trades-nq)
        - RTY → trades_rty_webhook (#trades-rty)
        - Autre → None (fallback vers trades_webhook général)

        Args:
            symbol: Symbole (ES, NQ, RTY, etc.)

        Returns:
            URL webhook ou None si non trouvé
        """
        webhooks = self.config.get('webhooks', {})

        # Normaliser le symbole (enlever suffixe comme ES1, NQ1, etc.)
        symbol_base = symbol[:2].upper() if len(symbol) >= 2 else symbol.upper()

        # Mapping symbole → webhook
        symbol_webhook_mapping = {
            'ES': 'trades_es_webhook',
            'NQ': 'trades_nq_webhook',
            'RT': 'trades_rty_webhook',  # RTY peut être abrégé RT
            'RTY': 'trades_rty_webhook'
        }

        webhook_key = symbol_webhook_mapping.get(symbol_base)
        if webhook_key and webhook_key in webhooks:
            webhook_url = webhooks[webhook_key]
            logger.debug(f"✅ Webhook symbole résolu: {symbol} ({symbol_base}) → {webhook_key}")
            return webhook_url

        # Si symbole non reconnu, retourner None pour utiliser fallback
        logger.debug(f"⚠️ Symbole non mappé: {symbol} ({symbol_base}) → fallback vers trades_webhook général")
        return None

    async def _get_session(self):
        """Obtient session aiohttp"""
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self.session

    async def send_webhook_message(self, webhook_url: str, message_data: Dict,
                                 retry_count: int = 0) -> bool:
        """Envoie message via webhook spécifique avec retry robuste"""
        max_retries = 3
        base_delay = 2

        try:
            # 🆕 RATE LIMITING avancé
            await self._apply_rate_limiting()

            session = await self._get_session()

            async with session.post(webhook_url, json=message_data) as response:
                if response.status in [200, 204]:
                    self.stats['messages_sent'] += 1
                    return True

                # 🆕 GESTION ERREURS SPÉCIFIQUES
                elif response.status == 429:  # Rate limit
                    retry_after = int(response.headers.get('retry-after', 60))
                    logger.warning(f"⚠️ Rate limit Discord: attente {retry_after}s")

                    if retry_count < max_retries:
                        await asyncio.sleep(retry_after)
                        self.stats['messages_retried'] += 1
                        return await self.send_webhook_message(webhook_url, message_data, retry_count + 1)

                elif response.status == 404:  # Webhook invalide
                    logger.error(f"❌ Webhook invalide ou supprimé: {webhook_url[:50]}...")
                    self.stats['messages_failed'] += 1
                    return False

                elif response.status >= 500:  # Erreur serveur Discord
                    logger.warning(f"⚠️ Erreur serveur Discord: {response.status}")

                    if retry_count < max_retries:
                        delay = base_delay ** (retry_count + 1)  # Délai exponentiel
                        await asyncio.sleep(delay)
                        self.stats['messages_retried'] += 1
                        return await self.send_webhook_message(webhook_url, message_data, retry_count + 1)

                else:
                    logger.error(f"❌ Erreur webhook {response.status}: {await response.text()}")
                    self.stats['messages_failed'] += 1
                    return False

        except asyncio.TimeoutError:
            logger.error("⚠️ Timeout webhook Discord")
            if retry_count < max_retries:
                delay = base_delay ** (retry_count + 1)
                await asyncio.sleep(delay)
                self.stats['messages_retried'] += 1
                return await self.send_webhook_message(webhook_url, message_data, retry_count + 1)

        except aiohttp.ClientError as e:
            logger.error(f"⚠️ Erreur réseau: {e}")
            if retry_count < max_retries:
                delay = base_delay ** (retry_count + 1)
                await asyncio.sleep(delay)
                self.stats['messages_retried'] += 1
                return await self.send_webhook_message(webhook_url, message_data, retry_count + 1)

        except Exception as e:
            logger.error(f"❌ Erreur inattendue webhook: {e}")
            self.stats['messages_failed'] += 1
            return False

        self.stats['messages_failed'] += 1
        return False

    async def send_custom_message(self, channel_type: str, title: str,
                                description: str, color: int = 0x00ff00, urgent: bool = False) -> bool:
        """Envoie message vers le webhook approprié avec queue et retry"""

        # Préparer les données du message
        message_payload = {
            'channel_type': channel_type,
            'title': title,
            'description': description,
            'color': color,
            'urgent': urgent,
            'timestamp': datetime.utcnow(),
            'attempts': 0
        }

        # 🆕 Si urgent, envoyer immédiatement
        if urgent:
            return await self._send_message_direct(message_payload)

        # 🆕 Sinon, utiliser le système de queue
        return await self._send_message_with_queue(message_payload)

    async def _send_message_direct(self, message_payload: Dict[str, Any]) -> bool:
        """Envoie message directement sans queue"""
        webhook_url = self._get_webhook_for_channel_type(message_payload['channel_type'])
        if not webhook_url:
            logger.error(f"Aucun webhook pour {message_payload['channel_type']}")
            return False

        # Créer le message Discord
        message_data = self._create_discord_message(message_payload)

        # Envoyer avec retry
        success = await self.send_webhook_message(webhook_url, message_data)

        if success:
            logger.info(f"✅ Message urgent envoyé: {message_payload['channel_type']} → {message_payload['title']}")
        else:
            logger.error(f"❌ Échec message urgent: {message_payload['channel_type']} → {message_payload['title']}")

        return success

    async def _send_message_with_queue(self, message_payload: Dict[str, Any]) -> bool:
        """Envoie message avec système de queue"""
        # 🆕 Ajouter à la queue
        if len(self.message_queue) >= self.max_queue_size:
            logger.warning(f"⚠️ Queue pleine ({self.max_queue_size}), suppression ancien message")
            self.message_queue.pop(0)

        self.message_queue.append(message_payload)

        # 🆕 Traiter la queue si pas déjà en cours
        if not self.is_processing_queue:
            asyncio.create_task(self._process_message_queue())

        return True

    async def _process_message_queue(self):
        """🆕 Traite la queue de messages avec retry logic"""
        if self.is_processing_queue:
            return

        self.is_processing_queue = True

        try:
            while self.message_queue:
                message_payload = self.message_queue.pop(0)

                # Vérifier si message pas trop vieux (5 minutes max)
                age_seconds = (datetime.utcnow() - message_payload['timestamp']).total_seconds()
                if age_seconds > 300:  # 5 minutes
                    logger.warning(f"⚠️ Message trop ancien ignoré: {message_payload['title']}")
                    continue

                # Tenter d'envoyer
                success = await self._send_message_direct(message_payload)

                # 🆕 Si échec, retry avec délai
                if not success:
                    message_payload['attempts'] += 1

                    if message_payload['attempts'] < 3:
                        # Re-ajouter à la fin de la queue pour retry
                        delay = 2 ** message_payload['attempts']  # Délai exponentiel
                        logger.info(f"🔄 Retry dans {delay}s: {message_payload['title']}")

                        await asyncio.sleep(delay)
                        self.message_queue.append(message_payload)
                    else:
                        logger.error(f"❌ Message abandonné après 3 tentatives: {message_payload['title']}")

                # Délai entre messages pour éviter spam
                await asyncio.sleep(0.5)

        except Exception as e:
            logger.error(f"❌ Erreur traitement queue: {e}")

        finally:
            self.is_processing_queue = False

    def _create_discord_message(self, message_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Crée le message Discord formaté"""
        # Déterminer le nom du channel de destination (ÉTENDU)
        channel_names = {
            # Channels existants
            'trade_executions': '#trades',
            'post_mortem_analysis': '#trades',
            'system_alerts': '#alertes',
            'critical_errors': '#alertes',
            'performance_milestones': '#performance',
            'daily_summary': '#performance',
            'signals_analysis': '#signal',
            'admin_messages': '#admin',
            'system_status': '#admin',
            'main_trading': '#trades',
            'general_info': '#admin',

            # Channels logs et backtest
            'technical_logs': '#logs',
            'error_logs': '#logs',
            'audit_logs': '#logs',
            'config_changes': '#logs',
            'network_logs': '#logs',
            'backtest_results': '#backtest',
            'strategy_optimization': '#backtest',
            'performance_comparison': '#backtest',
            'ab_testing': '#backtest',
            'pattern_analysis': '#backtest',

            # 🆕 ASSISTANT TRADING PERSONNEL
            'trading_assistant': '#mia_ia_trading',
            'opportunity_alert': '#mia_ia_trading',
            'position_management': '#mia_ia_trading',
            'market_insights': '#mia_ia_trading',
            'setup_confirmation': '#mia_ia_trading',
            'risk_alert': '#mia_ia_trading',
            'live_dashboard': '#mia_ia_trading',

            # 🆕 MONITORING (17/11/2025)
            'system_monitoring': '#monitoring',
            'health_check': '#monitoring',
            'heartbeat': '#monitoring',
            'system_metrics': '#monitoring',

            # 🆕 TRADES ALL (17/11/2025)
            'trades_all': '#trades-all'
        }

        channel_name = channel_names.get(message_payload['channel_type'], '#unknown')

        # Créer embed avec indication du channel de destination
        embed = {
            "title": message_payload['title'],
            "description": message_payload['description'],
            "color": message_payload['color'],
            "timestamp": message_payload['timestamp'].isoformat(),
            "footer": {
                "text": f"MIA → {message_payload['channel_type']} → {channel_name} | Attempt #{message_payload['attempts'] + 1}"
            }
        }

        return {
            "username": "MIA_IA_SYSTEM",
            "embeds": [embed]
        }

    async def _apply_rate_limiting(self):
        """🆕 Rate limiting avancé"""
        current_time = time.time()

        # Reset compteur si nouvelle minute
        if current_time - self.minute_start >= 60:
            self.messages_this_minute = 0
            self.minute_start = current_time

        # Si limite atteinte, attendre
        if self.messages_this_minute >= self.max_messages_per_minute:
            wait_time = 60 - (current_time - self.minute_start)
            logger.warning(f"⚠️ Rate limit atteint, attente {wait_time:.1f}s")
            await asyncio.sleep(wait_time)
            self.messages_this_minute = 0
            self.minute_start = time.time()

        # Délai minimum entre messages
        time_since_last = current_time - self.last_message_time
        if time_since_last < 1.0:  # 1 seconde minimum
            await asyncio.sleep(1.0 - time_since_last)

        self.messages_this_minute += 1
        self.last_message_time = time.time()

    async def send_trade_executed(self, trade_data: Dict) -> bool:
        """
        Notification trade exécuté → #trades-es, #trades-nq, ou #trades-rty + #trades-all (EMBED PROFESSIONNEL)

        Phase 1: Utilise discord_styles.build_trade_opened_embed()
        ✅ 17/11/2025: Routing par symbole vers webhooks dédiés + envoi vers #trades-all
        ✅ 10/12/2025: Ajout logs détaillés pour debug
        """
        symbol = trade_data.get('symbol', 'N/A')
        side = trade_data.get('side', 'N/A')

        try:
            logger.debug(f"📱 [DISCORD] Préparation notification trade ouvert: {symbol} {side}")

            # Construire embed professionnel
            embed_payload = build_trade_opened_embed(trade_data)
            logger.debug(f"📱 [DISCORD] Embed OPEN construit avec succès pour {symbol}")

            # ✅ 17/11/2025: Router vers webhook spécifique au symbole
            webhook_url = self._get_webhook_for_symbol(symbol)
            if not webhook_url:
                # Fallback vers webhook trades général
                webhook_url = self._get_webhook_for_channel_type('trade_executions')
                if not webhook_url:
                    logger.error(f"❌ [DISCORD] Webhook 'trade_executions' non trouvé pour {symbol}")
                    return False
                logger.warning(f"⚠️ [DISCORD] Utilisation webhook fallback pour {symbol}")

            # Envoyer vers webhook spécifique au symbole
            logger.debug(f"📱 [DISCORD] Envoi OPEN vers webhook symbole: {symbol}")
            success_symbol = await self.send_webhook_message(webhook_url, embed_payload)

            if not success_symbol:
                logger.error(f"❌ [DISCORD] ÉCHEC envoi webhook symbole pour {symbol} OPEN")
            else:
                logger.info(f"✅ [DISCORD] Notification OPEN envoyée vers webhook {symbol}")

            # ✅ 17/11/2025: Envoyer aussi vers #trades-all (tous les trades)
            webhooks = self.config.get('webhooks', {})
            trades_all_webhook = webhooks.get('trades_all_webhook')
            if trades_all_webhook:
                logger.debug(f"📱 [DISCORD] Envoi OPEN vers #trades-all")
                success_all = await self.send_webhook_message(trades_all_webhook, embed_payload)

                if not success_all:
                    logger.error(f"❌ [DISCORD] ÉCHEC envoi #trades-all pour {symbol} OPEN")
                else:
                    logger.info(f"✅ [DISCORD] Notification OPEN envoyée vers #trades-all")

                return success_symbol and success_all

            return success_symbol

        except Exception as e:
            logger.error(f"❌ Erreur send_trade_executed (embed): {e}")
            import traceback
            traceback.print_exc()
            # Fallback vers texte brut si embed échoue
            return await self.send_custom_message(
                'trade_executions',
                f"🟢 TRADE OUVERT - {symbol} {side}",
                f"Erreur embed: {e}",
                0x00ff00
            )

    async def send_trade_closed(self, trade_data: Dict) -> bool:
        """
        Notification trade fermé → #trades-es, #trades-nq, ou #trades-rty + #trades-all (EMBED PROFESSIONNEL)

        Phase 1: Utilise discord_styles.build_trade_closed_embed()
        ✅ 17/11/2025: Routing par symbole vers webhooks dédiés + envoi vers #trades-all
        ✅ 28/11/2025: Logging détaillé pour audit
        """
        symbol = trade_data.get('symbol', 'N/A')
        trade_id = trade_data.get('trade_id', 'N/A')

        try:
            logger.debug(f"📱 [DISCORD] Préparation notification trade fermé: {symbol} (ID: {trade_id})")

            # Construire embed professionnel
            embed_payload = build_trade_closed_embed(trade_data)
            logger.debug(f"📱 [DISCORD] Embed construit avec succès pour {symbol}")

            # ✅ 17/11/2025: Router vers webhook spécifique au symbole
            webhook_url = self._get_webhook_for_symbol(symbol)
            if not webhook_url:
                # Fallback vers webhook trades général
                webhook_url = self._get_webhook_for_channel_type('trade_executions')
                if not webhook_url:
                    logger.error(f"❌ [DISCORD] Webhook 'trade_executions' non trouvé pour {symbol}")
                    return False
                logger.warning(f"⚠️ [DISCORD] Utilisation webhook fallback pour {symbol}")

            # Envoyer vers webhook spécifique au symbole
            logger.debug(f"📱 [DISCORD] Envoi vers webhook symbole: {symbol}")
            success_symbol = await self.send_webhook_message(webhook_url, embed_payload)

            if not success_symbol:
                logger.error(f"❌ [DISCORD] Échec envoi webhook symbole pour {symbol}")
            else:
                logger.info(f"✅ [DISCORD] Notification envoyée vers webhook {symbol}")

            # ✅ 17/11/2025: Envoyer aussi vers #trades-all (tous les trades)
            webhooks = self.config.get('webhooks', {})
            trades_all_webhook = webhooks.get('trades_all_webhook')
            if trades_all_webhook:
                logger.debug(f"📱 [DISCORD] Envoi vers #trades-all")
                success_all = await self.send_webhook_message(trades_all_webhook, embed_payload)

                if not success_all:
                    logger.error(f"❌ [DISCORD] Échec envoi #trades-all pour {symbol}")
                else:
                    logger.info(f"✅ [DISCORD] Notification envoyée vers #trades-all")

                return success_symbol and success_all
            else:
                logger.warning(f"⚠️ [DISCORD] Webhook #trades-all non configuré")

            return success_symbol

        except Exception as e:
            logger.error(f"❌ [DISCORD] Erreur send_trade_closed pour {symbol} (ID: {trade_id}): {e}")
            import traceback
            logger.error(f"❌ [DISCORD] Traceback: {traceback.format_exc()}")

            # Fallback vers texte brut si embed échoue
            pnl = trade_data.get('pnl', 0)
            pnl_net = trade_data.get('pnl_net', pnl)
            emoji = "✅" if pnl_net > 0 else "❌"

            try:
                fallback_success = await self.send_custom_message(
                    'trade_executions',
                    f"{emoji} TRADE FERMÉ - {symbol}",
                    f"P&L Net: ${pnl_net:+.2f} | Erreur embed: {e}",
                    0x00ff00 if pnl_net > 0 else 0xff0000
                )
                if fallback_success:
                    logger.info(f"✅ [DISCORD] Message fallback envoyé pour {symbol}")
                return fallback_success
            except Exception as e2:
                logger.error(f"❌ [DISCORD] Échec message fallback pour {symbol}: {e2}")
                return False

    async def send_heartbeat_embed(self, heartbeat_data: Dict) -> bool:
        """
        ✨ NOUVEAU: Envoie heartbeat avec embed professionnel

        Phase 1: Utilise discord_styles.build_heartbeat_embed()

        Args:
            heartbeat_data: {
                'uptime_hours': int,
                'uptime_minutes': int,
                'cycles': int,
                'positions': Dict[str, Any],
                'daily_pnl': float,
                'pnl_by_market': Dict[str, float],
                'trades_by_market': Dict[str, Dict],
                'can_trade': bool,
                'kill_switch_reason': str (optionnel)
            }
        """
        try:
            # Construire embed professionnel
            embed_payload = build_heartbeat_embed(heartbeat_data)

            # ✅ CORRECTION 17/11: Heartbeat vers #monitoring (au lieu de #admin)
            webhook_url = self._get_webhook_for_channel_type('heartbeat')
            if not webhook_url:
                logger.error("❌ Webhook 'heartbeat' non trouvé")
                return False

            # Envoyer via webhook
            return await self.send_webhook_message(webhook_url, embed_payload)

        except Exception as e:
            logger.error(f"❌ Erreur send_heartbeat_embed: {e}")
            # ✅ CORRECTION 17/11: Fallback vers #monitoring
            uptime_h = heartbeat_data.get('uptime_hours', 0)
            uptime_m = heartbeat_data.get('uptime_minutes', 0)
            daily_pnl = heartbeat_data.get('daily_pnl', 0)
            return await self.send_custom_message(
                'heartbeat',  # ✅ Vers #monitoring
                '💓 HEARTBEAT',
                f"Uptime: {uptime_h}h {uptime_m}min | P&L: ${daily_pnl:+.2f} | Erreur embed: {e}",
                0x06B6D4
            )

    async def send_daily_summary_embed(self, daily_data: Dict) -> bool:
        """
        ✨ Phase 2.3: Envoie Daily Summary (23h59)

        Args:
            daily_data: {
                'trades': list[trade_record],
                'by_market': {'ES': [...], 'NQ': [...], 'RTY': [...]},
                'by_session': {...},
                'by_strategy': {...},
                'total_pnl': float,
                'total_fees': float,
                'date': datetime,
                'issues': list[str]
            }

        Returns:
            True si succès
        """
        try:
            embed_payload = build_daily_summary_embed(daily_data)

            # Récupérer webhook URL pour admin_messages
            webhook_url = self._get_webhook_for_channel_type('admin_messages')
            if not webhook_url:
                logger.error("❌ Webhook 'admin_messages' non trouvé")
                return False

            # Envoyer via webhook
            return await self.send_webhook_message(webhook_url, embed_payload)

        except Exception as e:
            logger.error(f"❌ Erreur send_daily_summary_embed: {e}")
            # Fallback texte brut
            total_pnl = daily_data.get('total_pnl', 0)
            total_trades = len(daily_data.get('trades', []))
            return await self.send_custom_message(
                'admin_messages',
                '🧾 DAILY SUMMARY',
                f"P&L: ${total_pnl:+.2f} | {total_trades} trades | Erreur embed: {e}",
                0x3498db
            )

    async def send_daily_report(self, report_data: Dict) -> bool:
        """Envoie rapport quotidien → #performance"""
        title = f"📊 RAPPORT QUOTIDIEN - {report_data.get('date', 'N/A')}"

        description = f"""
**P&L Total:** ${report_data.get('total_pnl', 0):+.2f}
**Trades:** {report_data.get('total_trades', 0)}
**Win Rate:** {report_data.get('win_rate', 0):.1%}
**Profit Factor:** {report_data.get('profit_factor', 0):.2f}
**Signaux détectés:** {report_data.get('signals_detected', 0)}
**Signaux pris:** {report_data.get('signals_taken', 0)}
**Sélectivité:** {report_data.get('selectivity', 0):.1%}
**Meilleur trade:** ${report_data.get('best_trade', 0):+.2f}
**Pire trade:** ${report_data.get('worst_trade', 0):+.2f}
        """.strip()

        if 'ml_insights' in report_data and report_data['ml_insights']:
            description += "\n\n**Insights ML:**\n" + "\n".join(f"• {insight}" for insight in report_data['ml_insights'])

        return await self.send_custom_message('daily_summary', title, description, 0x3498db)

    # 🆕 NOUVELLES FONCTIONS POUR #LOGS (OPTION 1: CRITIQUES SEULEMENT)

    async def send_critical_error_log(self, module: str, error_type: str, message: str,
                                     impact: str = None, action_taken: str = None) -> bool:
        """🔴 Envoie erreur CRITIQUE → #logs (URGENT)"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        title = f"🔴 ERREUR CRITIQUE - {module}"

        description = f"""
**[{timestamp}] {error_type.upper()}**
**Module:** {module}
**Message:** {message}
        """.strip()

        if impact:
            description += f"\n**Impact:** {impact}"
        if action_taken:
            description += f"\n**Action:** {action_taken}"

        return await self.send_custom_message('error_logs', title, description, 0xff0000, urgent=True)

    async def send_vix_alert_log(self, vix_level: float, threshold: float, action: str) -> bool:
        """⚠️ Envoie alerte VIX → #logs"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        title = f"⚠️ ALERTE VIX - Trading bloqué"

        emoji = "🔴" if vix_level >= 35 else "🟠"
        description = f"""
**[{timestamp}] VIX ÉLEVÉ**
{emoji} **VIX actuel:** {vix_level:.1f}
🛑 **Seuil limite:** {threshold:.1f}
🔒 **Action:** {action}
        """.strip()

        return await self.send_custom_message('error_logs', title, description, 0xf59e0b, urgent=True)

    async def send_kill_switch_log(self, reason: str, trigger_value: Any, daily_pnl: float) -> bool:
        """🔒 Envoie activation Kill Switch → #logs"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        title = f"🔒 KILL SWITCH ACTIVÉ"

        description = f"""
**[{timestamp}] ARRÊT D'URGENCE**
🚨 **Raison:** {reason}
📊 **Valeur déclencheur:** {trigger_value}
💰 **P&L journalier:** ${daily_pnl:+.2f}
🛑 **Status:** Tous les nouveaux trades sont bloqués
        """.strip()

        return await self.send_custom_message('error_logs', title, description, 0xdc2626, urgent=True)

    async def send_economic_calendar_block_log(self, event_name: str, event_time: str,
                                              stars: int, minutes_before: int) -> bool:
        """🔒 Envoie blocage économique → #logs"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        stars_display = "⭐" * stars
        title = f"🔒 BLOCAGE CALENDRIER - {stars_display}"

        description = f"""
**[{timestamp}] ANNONCE ÉCONOMIQUE**
📅 **Événement:** {event_name}
{stars_display} **Importance:** {stars}/3 étoiles
🕐 **Heure annonce:** {event_time}
⏱️ **Trading bloqué:** {minutes_before}min avant l'annonce
🔓 **Reprise:** 30min après l'annonce
        """.strip()

        return await self.send_custom_message('error_logs', title, description, 0xf59e0b)

    async def send_dtc_connection_log(self, status: str, symbol: str = None, error_msg: str = None) -> bool:
        """🔌 Envoie status connexion DTC → #logs"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if status == "DISCONNECTED":
            title = f"🔴 CONNEXION DTC PERDUE"
            emoji = "❌"
            color = 0xff0000
            urgent = True
        elif status == "RECONNECTED":
            title = f"✅ CONNEXION DTC RÉTABLIE"
            emoji = "🟢"
            color = 0x00ff00
            urgent = False
        elif status == "CONNECTING":
            title = f"🔄 TENTATIVE RECONNEXION DTC"
            emoji = "🔄"
            color = 0xf59e0b
            urgent = False
        else:
            title = f"🔌 STATUS DTC - {status}"
            emoji = "⚪"
            color = 0x6b7280
            urgent = False

        description = f"""
**[{timestamp}] CONNEXION BROKER**
{emoji} **Status:** {status}
        """.strip()

        if symbol:
            description += f"\n📊 **Symbole:** {symbol}"
        if error_msg:
            description += f"\n❌ **Erreur:** {error_msg}"

        if status == "DISCONNECTED":
            description += "\n🔄 Tentative de reconnexion automatique..."

        return await self.send_custom_message('error_logs', title, description, color, urgent=urgent)

    async def send_data_quality_alert_log(self, symbol: str, issue: str, age_seconds: float) -> bool:
        """⚠️ Envoie alerte qualité données → #logs"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        title = f"⚠️ DONNÉES PÉRIMÉES - {symbol}"

        description = f"""
**[{timestamp}] QUALITÉ DONNÉES**
📊 **Symbole:** {symbol}
⚠️ **Problème:** {issue}
⏱️ **Âge données:** {age_seconds:.1f}s (limite: 5s)
🔒 **Action:** Trading bloqué jusqu'à données fraîches
        """.strip()

        return await self.send_custom_message('error_logs', title, description, 0xf59e0b)

    async def send_daily_summary_log(self, summary_data: Dict[str, Any]) -> bool:
        """📊 Envoie résumé journalier → #logs (23:30)"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        title = f"📊 RÉSUMÉ JOURNALIER"

        total_trades = summary_data.get('total_trades', 0)
        wins = summary_data.get('wins', 0)
        losses = summary_data.get('losses', 0)
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
        daily_pnl = summary_data.get('daily_pnl', 0)

        pnl_emoji = "✅" if daily_pnl > 0 else "❌" if daily_pnl < 0 else "⚪"

        description = f"""
**[{timestamp}] FIN DE SESSION**
📈 **Trades:** {total_trades} ({wins}W - {losses}L)
🎯 **Win Rate:** {win_rate:.1f}%
{pnl_emoji} **P&L:** ${daily_pnl:+.2f}

**Par symbole:**
        """.strip()

        # Stats par symbole
        for symbol in ['ES', 'NQ', 'RTY']:
            symbol_data = summary_data.get(f'{symbol}_stats', {})
            if symbol_data.get('trades', 0) > 0:
                s_trades = symbol_data.get('trades', 0)
                s_wins = symbol_data.get('wins', 0)
                s_pnl = symbol_data.get('pnl', 0)
                s_emoji = "💰" if s_pnl > 0 else "🩸" if s_pnl < 0 else "💵"
                description += f"\n• **{symbol}:** {s_trades}T ({s_wins}W) {s_emoji} ${s_pnl:+.2f}"

        # Signaux analysés vs pris
        signals_analyzed = summary_data.get('signals_analyzed', 0)
        signals_taken = summary_data.get('signals_taken', 0)
        if signals_analyzed > 0:
            selectivity = (signals_taken / signals_analyzed * 100)
            description += f"\n\n**Filtrage ML:**"
            description += f"\n• Signaux analysés: {signals_analyzed}"
            description += f"\n• Signaux acceptés: {signals_taken}"
            description += f"\n• Sélectivité: {selectivity:.1f}%"

        return await self.send_custom_message('technical_logs', title, description, 0x3498db)

    async def send_session_change_log(self, old_session: str, new_session: str) -> bool:
        """🕐 Envoie changement de session → #logs"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        title = f"🕐 CHANGEMENT SESSION"

        description = f"""
**[{timestamp}] TRANSITION**
⏰ Ancienne session: {old_session}
🆕 Nouvelle session: {new_session}
        """.strip()

        return await self.send_custom_message('technical_logs', title, description, 0x06b6d4)

    # ═══════════════════════════════════════════════════════════════════════════
    # 🔧 LOGS DEBUG - PROBLÈMES TECHNIQUES (pour monitoring à distance)
    # ═══════════════════════════════════════════════════════════════════════════

    async def send_module_load_error(self, module_name: str, error: str, is_critical: bool = False) -> bool:
        """❌ Module qui ne charge pas → #logs"""
        timestamp = datetime.now().strftime("%H:%M:%S")

        emoji = "🔴" if is_critical else "🟠"
        title = f"{emoji} MODULE ÉCHEC - {module_name}"

        description = f"""
**[{timestamp}] CHARGEMENT ÉCHOUÉ**
📦 **Module:** `{module_name}`
❌ **Erreur:** {error}
⚠️ **Critique:** {"OUI - Bot peut mal fonctionner" if is_critical else "NON - Fallback utilisé"}
        """.strip()

        return await self.send_custom_message('error_logs', title, description,
                                              0xdc2626 if is_critical else 0xf59e0b, urgent=is_critical)

    async def send_function_error(self, function_name: str, module: str, error: str,
                                  input_data: str = None) -> bool:
        """❌ Fonction qui échoue → #logs"""
        timestamp = datetime.now().strftime("%H:%M:%S")

        title = f"❌ FONCTION ERREUR - {function_name}"

        description = f"""
**[{timestamp}] EXCEPTION**
📦 **Module:** `{module}`
🔧 **Fonction:** `{function_name}()`
❌ **Erreur:** {error}
        """.strip()

        if input_data:
            # Tronquer si trop long
            if len(str(input_data)) > 200:
                input_data = str(input_data)[:200] + "..."
            description += f"\n📥 **Input:** `{input_data}`"

        return await self.send_custom_message('error_logs', title, description, 0xff0000)

    async def send_timeout_error(self, operation: str, timeout_seconds: float,
                                 symbol: str = None) -> bool:
        """⏱️ Timeout détecté → #logs"""
        timestamp = datetime.now().strftime("%H:%M:%S")

        title = f"⏱️ TIMEOUT - {operation}"

        description = f"""
**[{timestamp}] OPÉRATION TROP LENTE**
🔧 **Opération:** {operation}
⏱️ **Timeout:** {timeout_seconds:.1f}s
        """.strip()

        if symbol:
            description += f"\n📊 **Symbole:** {symbol}"

        description += "\n🔄 **Action:** Retry automatique..."

        return await self.send_custom_message('error_logs', title, description, 0xf59e0b)

    async def send_data_missing_error(self, data_type: str, symbol: str,
                                      expected_fields: List[str] = None) -> bool:
        """📭 Données manquantes → #logs"""
        timestamp = datetime.now().strftime("%H:%M:%S")

        title = f"📭 DONNÉES MANQUANTES - {symbol}"

        description = f"""
**[{timestamp}] DATA INVALIDE**
📊 **Symbole:** {symbol}
📦 **Type données:** {data_type}
        """.strip()

        if expected_fields:
            description += f"\n❌ **Champs manquants:** {', '.join(expected_fields)}"

        return await self.send_custom_message('error_logs', title, description, 0xf59e0b)

    async def send_value_anomaly(self, field_name: str, value: Any, expected_range: str,
                                 symbol: str = None) -> bool:
        """🔍 Valeur anormale détectée → #logs"""
        timestamp = datetime.now().strftime("%H:%M:%S")

        title = f"🔍 VALEUR ANORMALE - {field_name}"

        description = f"""
**[{timestamp}] ANOMALIE DÉTECTÉE**
📊 **Champ:** `{field_name}`
❓ **Valeur:** `{value}`
✅ **Attendu:** {expected_range}
        """.strip()

        if symbol:
            description += f"\n📈 **Symbole:** {symbol}"

        return await self.send_custom_message('error_logs', title, description, 0xf59e0b)

    async def send_retry_exhausted(self, operation: str, max_retries: int,
                                   last_error: str) -> bool:
        """🔄 Retries épuisés → #logs"""
        timestamp = datetime.now().strftime("%H:%M:%S")

        title = f"🔄 RETRIES ÉPUISÉS - {operation}"

        description = f"""
**[{timestamp}] ÉCHEC DÉFINITIF**
🔧 **Opération:** {operation}
🔄 **Tentatives:** {max_retries}/{max_retries} (toutes échouées)
❌ **Dernière erreur:** {last_error}
🛑 **Status:** Opération abandonnée
        """.strip()

        return await self.send_custom_message('error_logs', title, description, 0xdc2626, urgent=True)

    async def send_startup_status(self, modules_status: Dict[str, bool],
                                  connections_status: Dict[str, bool]) -> bool:
        """🚀 Status démarrage bot → #logs"""
        timestamp = datetime.now().strftime("%H:%M:%S")

        # Compter succès/échecs modules
        modules_ok = sum(1 for v in modules_status.values() if v)
        modules_fail = len(modules_status) - modules_ok

        # Compter succès/échecs connexions
        conn_ok = sum(1 for v in connections_status.values() if v)
        conn_fail = len(connections_status) - conn_ok

        # Déterminer couleur/status global
        if modules_fail == 0 and conn_fail == 0:
            title = f"✅ BOT DÉMARRÉ - Tous systèmes OK"
            color = 0x00ff00
        elif modules_fail > 0 or conn_fail > 0:
            title = f"⚠️ BOT DÉMARRÉ - {modules_fail + conn_fail} problème(s)"
            color = 0xf59e0b

        description = f"""
**[{timestamp}] DÉMARRAGE MIA**

📦 **Modules:** {modules_ok}/{len(modules_status)} chargés
        """.strip()

        # Lister modules échoués
        failed_modules = [k for k, v in modules_status.items() if not v]
        if failed_modules:
            description += f"\n❌ **Échecs:** {', '.join(failed_modules)}"

        description += f"\n\n🔌 **Connexions:** {conn_ok}/{len(connections_status)} établies"

        # Lister connexions échouées
        failed_conn = [k for k, v in connections_status.items() if not v]
        if failed_conn:
            description += f"\n❌ **Échecs:** {', '.join(failed_conn)}"

        return await self.send_custom_message('technical_logs', title, description, color)

    async def send_loop_stuck_alert(self, loop_name: str, last_activity_seconds: float) -> bool:
        """🔒 Boucle bloquée détectée → #logs"""
        timestamp = datetime.now().strftime("%H:%M:%S")

        title = f"🔒 BOUCLE BLOQUÉE - {loop_name}"

        description = f"""
**[{timestamp}] WATCHDOG ALERT**
🔄 **Boucle:** {loop_name}
⏱️ **Dernière activité:** il y a {last_activity_seconds:.0f}s
⚠️ **Seuil normal:** < 10s
🚨 **Action requise:** Vérifier si bot frozen
        """.strip()

        return await self.send_custom_message('error_logs', title, description, 0xdc2626, urgent=True)

    async def send_memory_warning(self, memory_mb: float, threshold_mb: float) -> bool:
        """💾 Mémoire élevée → #logs"""
        timestamp = datetime.now().strftime("%H:%M:%S")

        title = f"💾 MÉMOIRE ÉLEVÉE"

        description = f"""
**[{timestamp}] RESOURCE WARNING**
💾 **Mémoire utilisée:** {memory_mb:.0f} MB
⚠️ **Seuil alerte:** {threshold_mb:.0f} MB
📈 **Tendance:** À surveiller
        """.strip()

        return await self.send_custom_message('error_logs', title, description, 0xf59e0b)

    async def send_config_validation_error(self, config_name: str, field: str,
                                           value: Any, reason: str) -> bool:
        """⚙️ Erreur config → #logs"""
        timestamp = datetime.now().strftime("%H:%M:%S")

        title = f"⚙️ CONFIG INVALIDE - {config_name}"

        description = f"""
**[{timestamp}] VALIDATION ÉCHOUÉE**
📄 **Config:** `{config_name}`
🔧 **Champ:** `{field}`
❓ **Valeur:** `{value}`
❌ **Raison:** {reason}
        """.strip()

        return await self.send_custom_message('error_logs', title, description, 0xf59e0b)

    # 🆕 ANCIENNES FONCTIONS (compatibilité)
    async def send_error_log(self, module: str, error_type: str, message: str,
                           impact: str = None, action_taken: str = None) -> bool:
        """Envoie log d'erreur → #logs (redirige vers critical)"""
        return await self.send_critical_error_log(module, error_type, message, impact, action_taken)


    # 🆕 NOUVELLES FONCTIONS POUR #BACKTEST
    async def send_backtest_result(self, backtest_data: Dict) -> bool:
        """Envoie résultat de backtest → #backtest"""
        title = f"🧪 BACKTEST #{backtest_data.get('id', 'N/A')} - {backtest_data.get('strategy_name', 'N/A')}"

        description = f"""
**📅 Période:** {backtest_data.get('start_date', 'N/A')} → {backtest_data.get('end_date', 'N/A')}

**📊 RÉSULTATS:**
• **Trades:** {backtest_data.get('total_trades', 0)}
• **Win Rate:** {backtest_data.get('win_rate', 0):.1%}
• **Profit Factor:** {backtest_data.get('profit_factor', 0):.2f}
• **Max Drawdown:** {backtest_data.get('max_drawdown', 0):.1%}
• **ROI:** {backtest_data.get('roi', 0):+.1%}

**🎯 TOP PATTERNS:**
        """.strip()

        # Ajouter les top patterns s'ils existent
        if 'top_patterns' in backtest_data:
            for i, pattern in enumerate(backtest_data['top_patterns'][:3], 1):
                description += f"\n{i}. {pattern['name']}: {pattern['win_rate']:.1%} win rate"

        # Comparaison avec le live
        if 'live_comparison' in backtest_data:
            description += f"\n\n⚡ **vs LIVE:** {backtest_data['live_comparison']:+.1%} différence"

        color = 0x00ff00 if backtest_data.get('roi', 0) > 0 else 0xff0000
        return await self.send_custom_message('backtest_results', title, description, color)

    async def send_strategy_optimization(self, optimization_data: Dict) -> bool:
        """Envoie résultat d'optimisation de stratégie → #backtest"""
        title = f"⚙️ OPTIMISATION - {optimization_data.get('strategy_name', 'N/A')}"

        description = f"""
**🎯 Objectif:** {optimization_data.get('objective', 'N/A')}
**⏱️ Durée:** {optimization_data.get('duration_minutes', 0)} min

**📈 AMÉLIORATION:**
• **Avant:** {optimization_data.get('before_metric', 0):.2f}
• **Après:** {optimization_data.get('after_metric', 0):.2f}
• **Gain:** {optimization_data.get('improvement_percent', 0):+.1%}

**🔧 PARAMÈTRES OPTIMAUX:**
        """.strip()

        # Ajouter les paramètres optimaux
        if 'optimal_params' in optimization_data:
            for param, value in optimization_data['optimal_params'].items():
                description += f"\n• **{param}:** {value}"

        return await self.send_custom_message('strategy_optimization', title, description, 0x3498db)

    async def send_ab_test_result(self, ab_test_data: Dict) -> bool:
        """Envoie résultat de test A/B → #backtest"""
        title = f"🔬 A/B TEST - {ab_test_data.get('test_name', 'N/A')}"

        description = f"""
**📅 Période:** {ab_test_data.get('duration_days', 0)} jours

**📊 VERSION A (Contrôle):**
• **ROI:** {ab_test_data.get('version_a_roi', 0):+.1%}
• **Win Rate:** {ab_test_data.get('version_a_winrate', 0):.1%}
• **Trades:** {ab_test_data.get('version_a_trades', 0)}

**📊 VERSION B (Test):**
• **ROI:** {ab_test_data.get('version_b_roi', 0):+.1%}
• **Win Rate:** {ab_test_data.get('version_b_winrate', 0):.1%}
• **Trades:** {ab_test_data.get('version_b_trades', 0)}

**🏆 GAGNANT:** Version {ab_test_data.get('winner', 'N/A')}
**📈 Amélioration:** {ab_test_data.get('improvement_percent', 0):+.1%}
        """.strip()

        # Ajouter la recommandation
        if 'recommendation' in ab_test_data:
            description += f"\n\n**💡 Recommandation:** {ab_test_data['recommendation']}"

        return await self.send_custom_message('ab_testing', title, description, 0x9b59b6)

    # 🆕 FONCTIONS ASSISTANT TRADING PERSONNEL
    async def send_trading_opportunity(self, opportunity_data: Dict) -> bool:
        """Alerte opportunité trading → #mia_ia_trading"""
        urgency = opportunity_data.get('urgency', 'normal')

        if urgency == 'critical':
            title = f"🚨 OPPORTUNITÉ CRITIQUE - {opportunity_data.get('symbol', 'ES')}"
            color = 0xFF4500  # Red-Orange
        elif urgency == 'high':
            title = f"⚡ OPPORTUNITÉ PREMIUM - {opportunity_data.get('symbol', 'ES')}"
            color = 0xFFD700  # Gold
        else:
            title = f"🎯 OPPORTUNITÉ - {opportunity_data.get('symbol', 'ES')}"
            color = 0x00FF00  # Green

        description = f"""
**📊 Setup:** {opportunity_data.get('setup_name', 'N/A')}
**📈 Direction:** {opportunity_data.get('direction', 'N/A')} @ {opportunity_data.get('current_price', 0)}
**🎯 Entry suggéré:** {opportunity_data.get('entry_price', 0)}
**🛑 Stop suggéré:** {opportunity_data.get('stop_price', 0)}
**💰 Target 1:** {opportunity_data.get('target1', 0)} | **Target 2:** {opportunity_data.get('target2', 0)}
**📊 Probabilité:** {opportunity_data.get('probability', 0):.1%}
**⚡ Confluence:** {opportunity_data.get('confluence_count', 0)} facteurs
**⏰ Fenêtre:** {opportunity_data.get('time_window', 'N/A')}
        """.strip()

        if opportunity_data.get('notes'):
            description += f"\n\n**💡 Notes:** {opportunity_data['notes']}"

        is_urgent = urgency in ['critical', 'high']
        return await self.send_custom_message('opportunity_alert', title, description, color, urgent=is_urgent)

    async def send_position_management_alert(self, position_data: Dict) -> bool:
        """Alerte gestion de position → #mia_ia_trading"""
        alert_type = position_data.get('alert_type', 'update')

        title_map = {
            'profit_protection': f"💪 PROTECTION PROFIT - {position_data.get('symbol', 'ES')}",
            'stop_adjustment': f"🔧 AJUSTEMENT STOP - {position_data.get('symbol', 'ES')}",
            'target_approach': f"🎯 APPROCHE TARGET - {position_data.get('symbol', 'ES')}",
            'risk_warning': f"⚠️ ALERTE RISQUE - {position_data.get('symbol', 'ES')}",
            'exit_signal': f"🚪 SIGNAL SORTIE - {position_data.get('symbol', 'ES')}"
        }

        title = title_map.get(alert_type, f"📊 POSITION UPDATE - {position_data.get('symbol', 'ES')}")

        description = f"""
**📊 Position:** {position_data.get('side', 'N/A')} @ {position_data.get('entry_price', 0)}
**💰 P&L actuel:** ${position_data.get('current_pnl', 0):+.2f} ({position_data.get('pnl_ticks', 0):+.1f} ticks)
**📈 Prix actuel:** {position_data.get('current_price', 0)}
**🛑 Stop actuel:** {position_data.get('current_stop', 0)}
**🎯 Target proche:** {position_data.get('next_target', 0)}
        """.strip()

        if position_data.get('suggestion'):
            description += f"\n\n**💡 Suggestion:** {position_data['suggestion']}"

        if position_data.get('reasoning'):
            description += f"\n**📋 Raison:** {position_data['reasoning']}"

        color_map = {
            'profit_protection': 0x32CD32,  # Lime Green
            'stop_adjustment': 0x4169E1,   # Royal Blue
            'target_approach': 0xFFD700,   # Gold
            'risk_warning': 0xFF6347,      # Tomato
            'exit_signal': 0xFF1493        # Deep Pink
        }
        color = color_map.get(alert_type, 0x3498db)

        is_urgent = alert_type in ['risk_warning', 'exit_signal']
        return await self.send_custom_message('position_management', title, description, color, urgent=is_urgent)

    async def send_market_insight(self, insight_data: Dict) -> bool:
        """Insight marché IA → #mia_ia_trading"""
        insight_type = insight_data.get('type', 'general')

        title_map = {
            'pattern_detection': f"🔍 PATTERN DÉTECTÉ - {insight_data.get('pattern_name', 'N/A')}",
            'volume_analysis': f"📊 ANALYSE VOLUME - {insight_data.get('symbol', 'ES')}",
            'support_resistance': f"📈 NIVEAU CRITIQUE - {insight_data.get('level_price', 0)}",
            'momentum_shift': f"⚡ CHANGEMENT MOMENTUM - {insight_data.get('direction', 'N/A')}",
            'correlation_alert': f"🔗 CORRÉLATION - {insight_data.get('correlation_info', 'N/A')}"
        }

        title = title_map.get(insight_type, f"🧠 MIA INSIGHT - {insight_data.get('symbol', 'ES')}")

        description = f"""
**📊 Analyse:** {insight_data.get('analysis', 'N/A')}
**📈 Confiance:** {insight_data.get('confidence', 0):.1%}
**⚡ Impact:** {insight_data.get('impact_level', 'Moyen')}
**⏰ Validité:** {insight_data.get('validity_time', 'N/A')}
        """.strip()

        if insight_data.get('key_levels'):
            description += f"\n**🎯 Niveaux clés:** {', '.join(map(str, insight_data['key_levels']))}"

        if insight_data.get('recommendation'):
            description += f"\n\n**💡 Recommandation:** {insight_data['recommendation']}"

        return await self.send_custom_message('market_insights', title, description, 0x9932CC)

    async def send_setup_confirmation(self, setup_data: Dict) -> bool:
        """Confirmation de setup → #mia_ia_trading"""
        confirmation_level = setup_data.get('confirmation_level', 'medium')

        if confirmation_level == 'high':
            title = f"✅ SETUP CONFIRMÉ A+ - {setup_data.get('setup_name', 'N/A')}"
            color = 0x00FF00  # Green
        elif confirmation_level == 'medium':
            title = f"🟡 SETUP VALIDÉ - {setup_data.get('setup_name', 'N/A')}"
            color = 0xFFD700  # Gold
        else:
            title = f"🟠 SETUP EN COURS - {setup_data.get('setup_name', 'N/A')}"
            color = 0xFF8C00  # Dark Orange

        description = f"""
**🎯 Setup:** {setup_data.get('setup_name', 'N/A')}
**📊 Qualité:** {setup_data.get('quality_score', 0)}/100
**⚡ Confluence:** {setup_data.get('confluence_factors', [])}
**📈 Historique:** {setup_data.get('historical_performance', 'N/A')}
**🎯 Ton win rate sur ce setup:** {setup_data.get('personal_winrate', 0):.1%}
        """.strip()

        if setup_data.get('risk_reward'):
            description += f"\n**💰 Risk/Reward:** 1:{setup_data['risk_reward']:.2f}"

        if setup_data.get('notes'):
            description += f"\n\n**📝 Notes:** {setup_data['notes']}"

        return await self.send_custom_message('setup_confirmation', title, description, color)

    async def send_live_dashboard(self, dashboard_data: Dict) -> bool:
        """Dashboard trading live → #mia_ia_trading"""
        session_status = dashboard_data.get('session_status', 'active')

        if session_status == 'profit_target':
            title = f"🎯 OBJECTIF ATTEINT - {dashboard_data.get('session_name', 'Session')}"
            color = 0x32CD32  # Lime Green
        elif session_status == 'risk_limit':
            title = f"🛑 LIMITE RISQUE - {dashboard_data.get('session_name', 'Session')}"
            color = 0xFF4500  # Red Orange
        else:
            title = f"📊 DASHBOARD LIVE - {dashboard_data.get('session_name', 'Session')}"
            color = 0x3498db  # Blue

        description = f"""
**📊 Position actuelle:** {dashboard_data.get('current_position', 'Flat')}
**💰 P&L Session:** ${dashboard_data.get('session_pnl', 0):+.2f}
**📈 P&L Journalier:** ${dashboard_data.get('daily_pnl', 0):+.2f}
**🎯 Trades:** {dashboard_data.get('trades_count', 0)} ({dashboard_data.get('win_rate', 0):.1%} win rate)
**⚡ Risk utilisé:** {dashboard_data.get('risk_used_percent', 0):.1%} / 100%
**🔍 Prochain signal:** {dashboard_data.get('next_signal_status', 'En surveillance')}
        """.strip()

        if dashboard_data.get('market_condition'):
            description += f"\n**🌊 Condition marché:** {dashboard_data['market_condition']}"

        if dashboard_data.get('key_levels'):
            description += f"\n**🎯 Niveaux clés:** {dashboard_data['key_levels']}"

        is_urgent = session_status in ['profit_target', 'risk_limit']
        return await self.send_custom_message('live_dashboard', title, description, color, urgent=is_urgent)

    async def close(self):
        """Ferme la session et traite les messages restants"""
        # 🆕 Traiter les messages restants dans la queue
        if self.message_queue:
            logger.info(f"📨 Traitement final de {len(self.message_queue)} messages en queue")
            await self._process_message_queue()

        if self.session:
            await self.session.close()
            self.session = None
            logger.info("✅ Session Discord fermée")

    def get_stats(self) -> Dict[str, Any]:
        """🆕 Retourne les statistiques détaillées"""
        return {
            'messages_sent': self.stats['messages_sent'],
            'messages_failed': self.stats['messages_failed'],
            'messages_retried': self.stats['messages_retried'],
            'messages_queued': len(self.message_queue),
            'queue_processing': self.is_processing_queue,
            'rate_limit_messages_this_minute': self.messages_this_minute
        }

# Factory functions pour compatibilité
def create_discord_notifier():
    """Crée notifier Discord multi-webhooks"""
    return MultiWebhookDiscordNotifier()

def notify_discord_available() -> bool:
    """Vérifie si Discord est disponible"""
    return True  # Toujours disponible avec webhooks hardcodés

# 🆕 ALIAS DE COMPATIBILITÉ pour l'ancien système
DiscordNotifier = MultiWebhookDiscordNotifier

# Test direct si exécuté
if __name__ == "__main__":
    async def test():
        print("🧪 Test rapide multi-webhooks (7 channels)")
        notifier = create_discord_notifier()
        if notifier:
            # Test channel existant
            await notifier.send_custom_message(
                'system_status',
                'Test Discord Multi-Webhooks ROBUSTE',
                'Configuration réussie avec vos 7 webhooks + Queue + Retry!'
            )

            # 🆕 Test message urgent
            await notifier.send_custom_message(
                'critical_errors',
                'Test Message URGENT',
                'Ce message urgent bypass la queue',
                color=0xff0000,
                urgent=True
            )

            # 🆕 Test nouveau channel #logs
            await notifier.send_error_log(
                module="TestModule",
                error_type="CONNECTION",
                message="Test d'erreur pour validation #logs",
                impact="Aucun impact (test)",
                action_taken="Test réussi"
            )

            # 🆕 Test nouveau channel #backtest
            await notifier.send_backtest_result({
                'id': 'TEST001',
                'strategy_name': 'Test Strategy',
                'start_date': '2025-01-01',
                'end_date': '2025-01-03',
                'total_trades': 10,
                'win_rate': 0.7,
                'profit_factor': 1.5,
                'max_drawdown': 0.05,
                'roi': 0.15,
                'top_patterns': [
                    {'name': 'Pattern Test', 'win_rate': 0.8}
                ],
                'live_comparison': 0.03
            })

            await notifier.close()

            # 🆕 Afficher les stats
            stats = notifier.get_stats()
            print(f"📊 STATISTIQUES:")
            print(f"   • Messages envoyés: {stats['messages_sent']}")
            print(f"   • Messages échoués: {stats['messages_failed']}")
            print(f"   • Messages retentés: {stats['messages_retried']}")
            print(f"   • Messages en queue: {stats['messages_queued']}")
            print("✅ Test terminé - Vérifiez vos 8 channels Discord!")
        else:
            print("❌ Notifier non disponible")

    asyncio.run(test())
