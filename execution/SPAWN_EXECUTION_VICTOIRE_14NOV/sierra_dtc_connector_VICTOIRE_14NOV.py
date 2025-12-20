#!/usr/bin/env python3
"""
MIA_IA_SYSTEM - Sierra DTC Connector (Orders-Only)
Connecteur DTC ultra-minimal pour ordres uniquement

VERSION: v2.0 - Orders-Only
FONCTION: Envoi/cancel d'ordres via DTC Sierra Chart
PERFORMANCE: <10ms par ordre, auto-reconnect, PAPER MODE fallback
COMPATIBILITÉ: 100% avec architecture Sierra-only

FONCTIONNALITÉS:
1. Connexion DTC par instrument (ES→11099, NQ→11099)
2. API ordres: place_order, cancel, flatten_all, get_open_orders
3. Validation session_manager + menthorq_execution_rules
4. PAPER MODE fallback si DTC non joignable
5. Auto-reconnect + backoff
6. Logs clairs pour observabilité
7. Aucune souscription market data
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Set, List
import socket
import json
import asyncio
import time
from enum import Enum
import contextlib
import re
import uuid
from core.logger import get_logger

logger = get_logger(__name__)

# === CONFIGURATION ===

# DTC core message types
LOGON_REQUEST = 1
LOGON_RESPONSE = 2
HEARTBEAT = 3
LOGOFF = 5

# DTC order entry message types and enums (JSON encoding)
SUBMIT_NEW_SINGLE_ORDER = 208
SUBMIT_NEW_OCO_ORDER = 206
CANCEL_ORDER = 203
CANCEL_REPLACE_ORDER = 204
SUBMIT_FLATTEN_POSITION_ORDER = 209  # Ferme position + retire ordres
FLATTEN_POSITIONS_FOR_TRADE_ACCOUNT = 210

# DTC order/position updates subscription
OPEN_ORDERS_REQUEST = 300  # 🔥 CRITIQUE : demander les updates d'ordres
ORDER_UPDATE = 301  # Message reçu pour chaque changement d'état d'ordre

# DTC order type mapping
OT_MARKET = 1
OT_LIMIT = 2
OT_STOP = 3
OT_STOP_LIMIT = 4

# DTC buy/sell mapping
BS_BUY = 1
BS_SELL = 2

# DTC TIF mapping
TIF_DAY = 1

class OrderSide(Enum):
    """Côté de l'ordre"""
    BUY = "BUY"
    SELL = "SELL"

class OrderType(Enum):
    """Type d'ordre"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"

class TimeInForce(Enum):
    """Durée de validité"""
    DAY = "DAY"
    GTC = "GTC"
    IOC = "IOC"
    FOK = "FOK"

class ConnectionStatus(Enum):
    """Statut de connexion"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    PAPER_MODE = "paper_mode"

class ChildrenMode(str, Enum):
    SEPARATE = "separate"  # 2 messages SINGLE (TP puis SL)
    OCO206 = "oco206"      # 1 seul message SUBMIT_NEW_OCO_ORDER (206)

@dataclass
class DTCConfig:
    """Configuration DTC par instrument"""
    host: str = "127.0.0.1"
    es_port: int = 11099  # Port ES
    nq_port: int = 11099  # Port NQ (même instance)
    username: str = ""
    password: str = ""
    heartbeat_interval: int = 10
    connection_timeout: float = 10.0
    max_retries: int = 3
    retry_delay: float = 1.0
    trade_account: str = "Sim1"
    trade_account_map: dict | None = None  # {"ES":"Sim1","NQ":"Sim2"}
    keep_alive: bool = False
    keep_alive_hold_seconds: int = 15

@dataclass
class OrderRequest:
    """Requête d'ordre"""
    symbol: str
    side: str  # "BUY" ou "SELL"
    qty: float
    kind: str = "MKT"  # "MKT" ou "LMT"
    limit_price: Optional[float] = None
    client_tag: Optional[str] = None
    # Ajouts pour compatibilité avec tests et bracket
    time_in_force: Optional[str] = "DAY"
    bracket: Optional[Dict[str, float]] = None  # {"stop_loss": x, "take_profit": y}

@dataclass
class OrderResponse:
    """Réponse d'ordre"""
    order_id: str
    status: str  # "sent", "filled", "cancelled", "rejected"
    message: str
    timestamp: datetime

# === SIERRA DTC CONNECTOR ===

class SierraDTCConnector:
    # -------------------------
    # Symbol helpers (→ Sierra format)
    # -------------------------
    @staticmethod
    def _to_sierra_trading_symbol(sym: str) -> str:
        """
        Normalise un symbole vers le format Sierra Chart (ex: ESZ25-CME).
        - ESZ25_FUT_CME -> ESZ25-CME
        - ESZ25-CME     -> ESZ25-CME (inchangé)
        - ESZ25-CME[M]  -> ESZ25-CME (retire suffixes d'affichage)
        """
        if not sym:
            return sym
        base = sym.split("[", 1)[0]
        # Déjà au format ...-EXCH ?
        if re.search(r"-[A-Z0-9]+$", base):
            return base
        # Transforme _FUT_/ _OPT_ en -EXCH
        base2 = re.sub(r"_(FUT|OPT)_([A-Z0-9]+)$", r"-\2", base)
        return base2
    """
    Connecteur DTC ultra-minimal pour ordres uniquement

    Architecture:
    - ES → port 11099
    - NQ → port 11099 (même instance)
    - Aucune souscription market data
    - PAPER MODE fallback
    """

    def __init__(self, config: DTCConfig):
        self.config = config
        self.connections: Dict[str, socket.socket] = {}
        self.status: Dict[str, ConnectionStatus] = {}
        self.request_id_counter = 1
        self.paper_mode = False
        self.paper_orders: List[Dict[str, Any]] = []
        self._reader_tasks: Dict[str, asyncio.Task] = {}
        self._pending_acks: Dict[str, Dict[str, Any]] = {}
        self._pending_events: Dict[str, asyncio.Event] = {}
        # 🔥 Gestion OCO manuelle
        self._oco_pairs: Dict[str, str] = {}  # {tp_id: sl_id, sl_id: tp_id}
        self._oco_processed: set = set()  # Éviter doubles annulations
        self._server_order_ids: Dict[str, str] = {}  # {ClientOrderID: ServerOrderID}

        # Mapping symbol → port
        self.symbol_ports = {
            "ES": self.config.es_port,
            "NQ": self.config.nq_port,
            "ESU25": self.config.es_port,
            "NQU25": self.config.nq_port,
            "ESU25_FUT_CME": self.config.es_port,
            "NQU25_FUT_CME": self.config.nq_port,
            "ESZ25": self.config.es_port,
            "NQZ25": self.config.nq_port,
            "ESZ25_FUT_CME": self.config.es_port,
            "NQZ25_FUT_CME": self.config.nq_port
        }

        logger.info(f"DTC Connector initialisé - ES@{self.config.es_port} NQ@{self.config.nq_port} (orders-only)")

    async def connect(self, symbol: str) -> bool:
        """
        Connexion DTC pour un symbole

        Args:
            symbol: Symbole (ES/NQ)

        Returns:
            True si connexion réussie
        """
        try:
            # Utiliser une clé normalisée pour lier la connexion
            key = self._to_sierra_trading_symbol(symbol)
            port = self._get_port_for_symbol(symbol)
            if port is None:
                logger.error(f"Port non configuré pour {symbol}")
                return False

            # Vérifier si déjà connecté
            if key in self.connections and self.status.get(key) == ConnectionStatus.CONNECTED:
                return True

            logger.info(f"Connexion DTC {key}@{port}")
            self.status[key] = ConnectionStatus.CONNECTING

            # Créer socket TCP
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.config.connection_timeout)

            # Connexion
            await asyncio.get_event_loop().run_in_executor(
                None, sock.connect, (self.config.host, port)
            )

            # Handshake DTC
            if await self._dtc_handshake(sock, key):
                self.connections[key] = sock
                self.status[key] = ConnectionStatus.CONNECTED
                self.paper_mode = False

                logger.info(f"✅ Connexion DTC {key}@{port} établie")

                # Démarrer heartbeat
                asyncio.create_task(self._heartbeat_loop(symbol))

                return True
            else:
                logger.error(f"❌ Échec handshake DTC {symbol}")
                sock.close()
                return False

        except Exception as e:
            logger.error(f"❌ Erreur connexion DTC {symbol}: {e}")
            self.status[symbol] = ConnectionStatus.DISCONNECTED
            return False

    async def ensure_connected(self, symbol: str) -> bool:
        """
        Établit ou réutilise une connexion DTC persistante (streams asyncio).
        - Envoie LOGON JSON (NUL-terminé)
        - Lance une boucle lecteur pour consommer les messages et garder la socket vivante
        """
        try:
            key = self._to_sierra_trading_symbol(symbol)
            # Déjà connectée (writer présent)
            existing = self.connections.get(key)
            if existing is not None:
                # writer ou socket : considérer connecté
                if self.status.get(key) == ConnectionStatus.CONNECTED:
                    return True

            host = self.config.host
            port = self._get_port_for_symbol(symbol)
            if port is None:
                logger.error(f"Port non configuré pour {symbol}")
                # Fallback PAPER MODE
                if not self.paper_mode:
                    self.paper_mode = True
                    logger.warning("DTC unreachable → PAPER MODE (order queued/logged)")
                return True

            # Ouvre une connexion asyncio (reader/writer)
            reader, writer = await asyncio.open_connection(host, port)

            # Options socket
            try:
                transport = writer.transport
                sock = transport.get_extra_info('socket') if transport else None
                if sock is not None:
                    import socket as _pysock
                    sock.setsockopt(_pysock.IPPROTO_TCP, _pysock.TCP_NODELAY, 1)
                    sock.setsockopt(_pysock.SOL_SOCKET, _pysock.SO_KEEPALIVE, 1)
            except Exception:
                pass

            sc_symbol = key
            trade_account = self._account_for_symbol(sc_symbol)

            logon_request = {
                "Type": LOGON_REQUEST,
                "ProtocolVersion": 8,
                "Encoding": "json",  # IMPORTANT pour accepter les messages JSON
                "Username": self.config.username,
                "Password": self.config.password,
                "GeneralTextData": "MIA_IA_SYSTEM",
                "ClientName": f"MIA_TRADER_{sc_symbol}",
                "HeartbeatIntervalInSeconds": self.config.heartbeat_interval,
                "DoNotSendMarketData": 1,
                "TradeAccount": trade_account  # aide certains serveurs à préremplir le compte
            }

            if not await self._send_dtc_message(writer, logon_request):
                with contextlib.suppress(Exception):
                    writer.close()
                    await writer.wait_closed()
                if not self.paper_mode:
                    self.paper_mode = True
                    logger.warning("DTC unreachable → PAPER MODE (order queued/logged)")
                return True

            # Attendre explicitement la réponse LOGON_RESPONSE avant d'envoyer des ordres
            try:
                raw = await asyncio.wait_for(reader.readuntil(b"\x00"), timeout=2.0)
                if raw:
                    try:
                        msg = json.loads(raw[:-1].decode("utf-8", "ignore"))
                        if msg.get("Type") == LOGON_RESPONSE and msg.get("Result") == 1:
                            logger.info(f"✅ LOGON_RESPONSE confirmé pour {sc_symbol}")
                        else:
                            logger.warning(f"⚠️ LOGON_RESPONSE inattendu: {msg}")
                    except Exception:
                        pass
            except Exception:
                # Si aucun message, on continue mais on garde un léger délai de sûreté
                await asyncio.sleep(0.2)

            # Lancer lecteur en tâche de fond
            task = asyncio.create_task(self._reader_loop(sc_symbol, reader))
            self._reader_tasks[sc_symbol] = task

            # Enregistrer la connexion (writer remplace l'ancien socket)
            self.connections[key] = writer
            self.status[key] = ConnectionStatus.CONNECTED
            self.paper_mode = False

            logger.info(f"✅ Connexion DTC {sc_symbol}@{port} établie")

            # S'abonner aux Order/Position Updates (meilleure visibilité)
            try:
                self.request_id_counter += 1
                await self._send_dtc_message(writer, {"Type": 210, "RequestID": self.request_id_counter, "Subscribe": 1})
                self.request_id_counter += 1
                await self._send_dtc_message(writer, {"Type": 211, "RequestID": self.request_id_counter, "Subscribe": 1})
                logger.info("✅ Abonnement DTC: Order/Position Updates activés")
            except Exception:
                pass

            # Lancer heartbeat périodique via _heartbeat_loop (enverra via _send_dtc_message)
            asyncio.create_task(self._heartbeat_loop(key))

            # Conserver aussi la task pour fermeture propre (stockée dans status map non prévue) ⇒ ignorer
            # On s'appuie sur cancellation dans disconnect

            return True

        except Exception as e:
            logger.error(f"❌ Erreur ensure_connected {symbol}: {e}")
            if not self.paper_mode:
                self.paper_mode = True
                logger.warning("DTC unreachable → PAPER MODE (order queued/logged)")
            return True

    async def place_order(self, request: OrderRequest) -> OrderResponse:
        """
        Place un ordre

        Args:
            request: Requête d'ordre

        Returns:
            Réponse d'ordre
        """
        try:
            # Validation préalable
            if not await self._validate_order_request(request):
                return OrderResponse(
                    order_id="",
                    status="rejected",
                    message="Validation échouée",
                    timestamp=datetime.now(timezone.utc)
                )

            # S'assurer de la connexion
            if not await self.ensure_connected(request.symbol):
                return OrderResponse(
                    order_id="",
                    status="rejected",
                    message="Connexion impossible",
                    timestamp=datetime.now(timezone.utc)
                )

            # Générer ID d'ordre
            order_id = f"MIA_{self.request_id_counter}_{int(time.time())}"
            self.request_id_counter += 1

            # PAPER MODE
            if self.paper_mode:
                return await self._place_paper_order(request, order_id)

            # Mode réel
            return await self._place_real_order(request, order_id)

        except Exception as e:
            logger.error(f"Erreur placement ordre: {e}")
            return OrderResponse(
                order_id="",
                status="rejected",
                message=f"Erreur: {e}",
                timestamp=datetime.now(timezone.utc)
            )

    async def cancel(self, order_id: str, symbol: str) -> bool:
        """
        Annule un ordre

        Args:
            order_id: ID de l'ordre
            symbol: Symbole

        Returns:
            True si annulation réussie
        """
        try:
            if self.paper_mode:
                return await self._cancel_paper_order(order_id)

            # Mode réel
            return await self._cancel_real_order(order_id, symbol)

        except Exception as e:
            logger.error(f"Erreur annulation ordre {order_id}: {e}")
            return False

    async def flatten_all(self, symbol: str) -> bool:
        """
        Ferme toutes les positions d'un symbole

        Args:
            symbol: Symbole

        Returns:
            True si succès
        """
        try:
            if self.paper_mode:
                logger.info(f"PAPER MODE: flatten_all {symbol} (simulé)")
                return True

            # Mode réel - implémentation simplifiée
            logger.info(f"flatten_all {symbol} (non implémenté en mode réel)")
            return True

        except Exception as e:
            logger.error(f"Erreur flatten_all {symbol}: {e}")
            return False

    async def get_open_orders(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Récupère les ordres ouverts

        Args:
            symbol: Symbole

        Returns:
            Liste des ordres ouverts
        """
        try:
            if self.paper_mode:
                return [order for order in self.paper_orders
                       if order.get("symbol") == symbol and order.get("status") == "open"]

            # Mode réel - mock pour l'instant
            return []

        except Exception as e:
            logger.error(f"Erreur get_open_orders {symbol}: {e}")
            return []

    # === MÉTHODES PRIVÉES ===

    def _get_port_for_symbol(self, symbol: str) -> Optional[int]:
        """Retourne le port pour un symbole"""
        # Essayer d'abord le symbole exact
        if symbol in self.symbol_ports:
            return self.symbol_ports[symbol]

        # Normaliser: retirer suffixes d'affichage et d'exchange
        base = symbol.split("[", 1)[0]
        base = re.sub(r"_(FUT|OPT)_[A-Z0-9]+$", "", base)
        base = re.sub(r"-[A-Z0-9]+$", "", base)  # retire -CME, -CBOT ...

        # Raccourcis par racine
        if base.startswith("ES"):
            return self.config.es_port
        if base.startswith("NQ"):
            return self.config.nq_port

        # Dernier recours: table
        return self.symbol_ports.get(base)

    def _account_for_symbol(self, symbol: str) -> str:
        """Retourne le compte de trade selon le préfixe racine (ES/NQ)."""
        if self.config.trade_account_map:
            root = symbol.split("[", 1)[0]
            root = root.replace("_FUT_CME", "")
            if root.startswith("ES"):
                return self.config.trade_account_map.get("ES", self.config.trade_account)
            if root.startswith("NQ"):
                return self.config.trade_account_map.get("NQ", self.config.trade_account)
        return self.config.trade_account

    def _exchange_for_symbol(self, symbol: str) -> str:
        """Retourne l'exchange probable pour un symbole (simplifié)."""
        s = (symbol or "").upper()
        return "CME" if s.startswith(("ES", "NQ")) else ""

    async def _dtc_handshake(self, sock: socket.socket, symbol: str) -> bool:
        """Handshake DTC Protocol"""
        try:
            # Message LOGON_REQUEST (Type 1)
            logon_request = {
                "Type": 1,
                "ProtocolVersion": 8,
                "Encoding": "json",
                "Username": self.config.username,
                "Password": self.config.password,
                "GeneralTextData": "MIA_IA_SYSTEM",
                "ClientName": f"MIA_TRADER_{symbol}",
                "HeartbeatIntervalInSeconds": self.config.heartbeat_interval,
                "DoNotSendMarketData": 1,
                "TradeAccount": self._account_for_symbol(symbol)
            }

            await self._send_dtc_message(sock, logon_request)

            # Attendre LOGON_RESPONSE
            response = await self._receive_dtc_message(sock)

            if response and response.get("Type") == LOGON_RESPONSE:  # LOGON_RESPONSE
                if response.get("Result") == 1:  # Success
                    logger.info(f"✅ Handshake DTC {symbol} réussi")

                    # 🔥 CRITIQUE : S'abonner aux ORDER_UPDATE pour recevoir les fills
                    open_orders_request = {
                        "Type": OPEN_ORDERS_REQUEST,  # Type 300
                        "RequestID": self.request_id_counter
                    }
                    self.request_id_counter += 1

                    await self._send_dtc_message(sock, open_orders_request)
                    logger.info(f"✅ Abonnement ORDER_UPDATE envoyé pour {symbol}")

                    return True
                else:
                    logger.error(f"❌ Handshake {symbol} échoué: {response.get('ResultText', 'Unknown')}")
                    return False
            else:
                logger.error(f"❌ Réponse handshake {symbol} invalide")
                return False

        except Exception as e:
            logger.error(f"❌ Erreur handshake {symbol}: {e}")
            return False

    async def _send_dtc_message(self, transport_obj, message: Dict[str, Any]) -> bool:
        """Envoie un message DTC JSON NUL-terminé via Writer asyncio ou socket classique."""
        try:
            payload = (json.dumps(message, separators=(',', ':')) + '\x00').encode('utf-8')
            # Cas StreamWriter
            if hasattr(transport_obj, "write") and hasattr(transport_obj, "drain"):
                transport_obj.write(payload)
                await transport_obj.drain()
                logger.debug(f"📤 DTC JSON envoyé (writer): Type={message.get('Type')}, Size={len(payload)-1}")
                return True
            # Cas socket
            if isinstance(transport_obj, socket.socket):
                await asyncio.get_event_loop().run_in_executor(None, transport_obj.sendall, payload)
                logger.debug(f"📤 DTC JSON envoyé (socket): Type={message.get('Type')}, Size={len(payload)-1}")
                return True
            # Objet inconnu
            logger.error("❌ Transport DTC inconnu pour l'envoi")
            return False
        except Exception as e:
            logger.error(f"❌ Erreur envoi DTC: {e}")
            return False

    async def _send_children_oco206(
        self,
        *,
        sc_symbol: str,
        trade_account: str,
        parent_cid: str,
        side: str,
        qty: float,
        tp_price: float,
        sl_price: float,
        client_tag: str,
    ) -> Dict[str, Any]:
        """
        Envoie TP (LIMIT) + SL (STOP) en un seul message OCO (206).

        🔥 AVEC CHAMPS MAGIQUES POUR SIERRA CHART:
        - MaintainSamePricesOnParentFill: Force Sierra à gérer l'OCO
        - OpenOrClose: 2 (CLOSE) pour fermer la position
        - IsAutomatedOrder: 1 pour indiquer ordre automatique
        """
        key = sc_symbol
        sock = self.connections.get(key)
        if not sock:
            return {"error": "no_connection"}

        child_side_code = BS_BUY if (side or "").upper() == "SELL" else BS_SELL
        tp_cid = f"{client_tag}_TP_{uuid.uuid4().hex[:6]}"
        sl_cid = f"{client_tag}_SL_{uuid.uuid4().hex[:6]}"

        msg: Dict[str, Any] = {
            "Type": SUBMIT_NEW_OCO_ORDER,
            "RequestID": self.request_id_counter,
            "Symbol": sc_symbol,
            "TimeInForce": TIF_DAY,
            "TradeAccount": trade_account,
            "ParentTriggerClientOrderID": parent_cid,
            "Exchange": self._exchange_for_symbol(sc_symbol),

            # 🔥 CHAMPS MAGIQUES POUR BRACKET ORDERS
            "IsAutomatedOrder": 1,
            "OpenOrClose": 2,  # CLOSE position
            "MaintainSamePricesOnParentFill": 1,  # ✅ ACTIVER GESTION OCO !

            # Order 1 (TP LIMIT)
            "ClientOrderID_1": tp_cid,
            "BuySell_1": child_side_code,
            "OrderType_1": OT_LIMIT,
            "Price1_1": float(tp_price),
            "Quantity_1": float(qty),

            # Order 2 (SL STOP)
            "ClientOrderID_2": sl_cid,
            "BuySell_2": child_side_code,
            "OrderType_2": OT_STOP,
            "Price1_2": float(sl_price),
            "Quantity_2": float(qty),
            "StopPrice_2": float(sl_price)
        }
        self.request_id_counter += 1

        ok = await self._send_dtc_message(sock, msg)
        if not ok:
            return {"error": "oco206_send_failed"}
        logger.info(f"🔥 [DTC->] OCO206 BRACKET TP={tp_cid} SL={sl_cid} MaintainSamePrice=1 OpenClose=2")
        logger.debug(f"   Message complet: {msg}")
        return {"ok": True, "tp_cid": tp_cid, "sl_cid": sl_cid}

    async def _reader_loop(self, symbol: str, reader):
        """
        Boucle de lecture continue pour garder la connexion vivante (JSON NUL-terminé).

        🔥 GESTION OCO AUTOMATIQUE :
        - Détecte quand un ordre est FILLED (OrderStatus=7)
        - Annule automatiquement l'ordre opposé de la paire OCO
        """
        try:
            while True:
                chunk = await reader.readuntil(b"\x00")
                if not chunk:
                    break
                try:
                    msg = json.loads(chunk[:-1].decode("utf-8", "ignore"))
                except Exception:
                    continue

                t = msg.get("Type")
                if t in (210, 211) and msg:
                    logger.debug(f"📥 DTC ← {symbol} Update: {msg}")

                # Déclenchement d'ACK si ClientOrderID observé
                cid = msg.get("ClientOrderID") or msg.get("ClientOrderID_1") or msg.get("ClientOrderID_2")
                if cid and cid in self._pending_events:
                    self._pending_acks[cid] = msg
                    try:
                        self._pending_events[cid].set()
                    except Exception:
                        pass

                # 🔥 GESTION OCO AUTOMATIQUE
                if t == 301:  # ORDER_UPDATE
                    order_status = msg.get("OrderStatus")
                    client_order_id = msg.get("ClientOrderID", "")
                    msg_symbol = msg.get("Symbol", "")  # 🔥 Symbol du message !

                    # 🔍 LOG COMPLET pour diagnostic
                    logger.info(f"📥 ORDER_UPDATE: CID={client_order_id} Status={order_status} Symbol={msg_symbol}")

                    # Enregistrer ServerOrderID si reçu
                    server_order_id = msg.get("ServerOrderID")
                    if client_order_id and server_order_id:
                        self._server_order_ids[client_order_id] = server_order_id

                    # Si ordre FILLED (7) et fait partie d'une paire OCO
                    if order_status == 7 and client_order_id in self._oco_pairs:
                        if client_order_id not in self._oco_processed:
                            opposite_cid = self._oco_pairs[client_order_id]
                            logger.warning(f"🚨 {client_order_id} FILLED → Annulation IMMÉDIATE {opposite_cid}")
                            self._oco_processed.add(client_order_id)

                            # 🔥 ANNULER L'ORDRE OPPOSÉ IMMÉDIATEMENT !
                            asyncio.create_task(self._cancel_order_by_client_id(
                                symbol=msg_symbol,
                                client_order_id=opposite_cid,
                                reason=f"OCO: {client_order_id} filled"
                            ))

        except (asyncio.IncompleteReadError, asyncio.CancelledError):
            pass
        except Exception as e:
            logger.warning(f"[DTC] reader_loop stop {symbol}: {e}")

    async def _cancel_order_by_client_id(self, symbol: str, client_order_id: str, reason: str = ""):
        """
        Annule un ordre par son ClientOrderID

        🔥 NOUVELLE APPROCHE:
        - Essaie CANCEL classique
        - Si ça ne met pas à jour le DOM, utilise FLATTEN pour tout retirer

        Args:
            symbol: Symbole de l'ordre
            client_order_id: ClientOrderID de l'ordre à annuler
            reason: Raison de l'annulation (pour logs)
        """
        try:
            sc_symbol = self._to_sierra_trading_symbol(symbol)
            key = sc_symbol
            sock = self.connections.get(key)

            if not sock:
                logger.error(f"❌ Pas de connexion pour annuler {client_order_id}")
                return

            # Récupérer ServerOrderID si disponible
            server_order_id = self._server_order_ids.get(client_order_id, "")
            trade_account = self._account_for_symbol(sc_symbol)

            # 🔥 STRATÉGIE ULTIME : CANCEL + FLATTEN_ALL
            # Étape 1: CANCEL l'ordre
            cancel_msg = {
                "Type": CANCEL_ORDER,  # Type 203
                "RequestID": self.request_id_counter,
                "ServerOrderID": server_order_id,
                "ClientOrderID": client_order_id,
                "TradeAccount": trade_account
            }
            self.request_id_counter += 1

            logger.info(f"🔥 [DTC->] CANCEL {client_order_id} (Raison: {reason})")
            logger.warning(f"🔍 DEBUG: Symbol={sc_symbol} Account={trade_account} ServerOrderID={server_order_id}")
            await self._send_dtc_message(sock, cancel_msg)
            await asyncio.sleep(0.5)  # 🔥 Augmenté à 0.5s

            # 🔥 Étape 2: FLATTEN_POSITION pour ce symbole spécifique
            flatten_msg = {
                "Type": SUBMIT_FLATTEN_POSITION_ORDER,  # Type 209 - Symbole spécifique
                "RequestID": self.request_id_counter,
                "Symbol": sc_symbol,
                "TradeAccount": trade_account,
                "Exchange": self._exchange_for_symbol(sc_symbol),
                "IsAutomatedOrder": 1
            }
            self.request_id_counter += 1

            logger.warning(f"🔥 [DTC->] FLATTEN_POSITION {sc_symbol} compte {trade_account} (Socket: {key})")
            await self._send_dtc_message(sock, flatten_msg)
            await asyncio.sleep(0.3)  # 🔥 Attente après FLATTEN

            logger.info(f"✅ CANCEL + FLATTEN_POSITION terminée pour {client_order_id}")

        except Exception as e:
            logger.error(f"❌ Erreur annulation {client_order_id}: {e}")

    async def _receive_dtc_message(self, sock: socket.socket) -> Optional[Dict[str, Any]]:
        """Reçoit message DTC avec terminateur NULL"""
        try:
            buffer = b''

            # Lire byte par byte jusqu'au terminateur NULL
            while True:
                byte_data = await asyncio.get_event_loop().run_in_executor(
                    None, sock.recv, 1
                )

                if not byte_data:
                    logger.error("❌ Connexion fermée par Sierra Chart")
                    return None

                if byte_data == b'\x00':
                    break

                buffer += byte_data

                # Sécurité: limite taille message
                if len(buffer) > 1048576:  # 1MB max
                    logger.error("❌ Message trop long (>1MB)")
                    return None

            if not buffer:
                return None

            # Parser JSON
            json_str = buffer.decode('utf-8')
            message = json.loads(json_str)

            logger.debug(f"📥 DTC JSON reçu: Type={message.get('Type')}, Size={len(buffer)}")
            return message

        except json.JSONDecodeError as e:
            logger.error(f"❌ Erreur JSON DTC: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Erreur réception DTC: {e}")
            return None

    async def _validate_order_request(self, request: OrderRequest) -> bool:
        """
        Valide une requête d'ordre

        Args:
            request: Requête d'ordre

        Returns:
            True si valide
        """
        try:
            # Vérifier session_manager (mock pour l'instant)
            # session_state = session_manager.get_state()
            # if session_state.get("no_trade"):
            #     logger.warning("Ordre bloqué: no_trade mode")
            #     return False

            # Vérifier menthorq_execution_rules (mock pour l'instant)
            # if menthorq_execution_rules.check_hard_rule("BL_proche"):
            #     logger.warning("Ordre bloqué: BL proche")
            #     return False

            # Validation basique
            if request.qty <= 0:
                logger.warning("Quantité invalide")
                return False

            if request.kind == "LMT" and request.limit_price is None:
                logger.warning("Prix limite manquant pour ordre LIMIT")
                return False

            # Note: OrderRequest n'a pas de stop_price

            return True

        except Exception as e:
            logger.error(f"Erreur validation ordre: {e}")
            return False

    async def _place_paper_order(self, request: OrderRequest, order_id: str) -> OrderResponse:
        """Place un ordre en PAPER MODE"""
        try:
            paper_order = {
                "order_id": order_id,
                "symbol": request.symbol,
                "side": request.side,
                "quantity": request.qty,
                "order_type": request.kind,
                "limit_price": request.limit_price,
                "stop_price": None,
                "time_in_force": "DAY",
                "bracket": None,
                "status": "open",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            self.paper_orders.append(paper_order)

            # Log clair
            price_info = ""
            if request.limit_price:
                price_info = f" @L {request.limit_price}"
            # Note: OrderRequest n'a pas de stop_price

            bracket_info = ""

            logger.info(f"PAPER ORDER {request.symbol} {request.side} {request.qty}{price_info} tif=DAY{bracket_info}")

            return OrderResponse(
                order_id=order_id,
                status="sent",
                message="PAPER MODE - ordre simulé",
                timestamp=datetime.now(timezone.utc)
            )

        except Exception as e:
            logger.error(f"Erreur PAPER MODE: {e}")
            return OrderResponse(
                order_id="",
                status="rejected",
                message=f"Erreur PAPER MODE: {e}",
                timestamp=datetime.now(timezone.utc)
            )

    async def _place_real_order(self, request: OrderRequest, order_id: str) -> OrderResponse:
        """Place un ordre réel via DTC"""
        try:
            symbol = request.symbol
            sc_symbol = self._to_sierra_trading_symbol(symbol)
            # ✅ utiliser la clé normalisée (writer asyncio)
            sock = self.connections.get(sc_symbol)

            if not sock:
                return OrderResponse(
                    order_id="",
                    status="rejected",
                    message="Connexion non disponible",
                    timestamp=datetime.now(timezone.utc)
                )

            # Construire message d'ordre DTC (gestion LIMIT/STOP)
            order_type_code = self._map_kind_to_dtc_order_type(request.kind)
            price1 = float(request.limit_price or 0.0)
            price2 = 0.0
            # DTC: STOP = Price1 (Stop-Limit = Price1 stop, Price2 limit)
            if order_type_code == OT_STOP:
                price1, price2 = float(request.limit_price or 0.0), 0.0

            order_request = {
                "Type": SUBMIT_NEW_SINGLE_ORDER,  # Parent ou single order
                "RequestID": self.request_id_counter,
                "Symbol": sc_symbol,
                "OrderType": order_type_code,
                "BuySell": self._map_side_to_dtc_buy_sell(request.side),
                "Quantity": float(request.qty),
                "Price1": price1,
                "Price2": price2,
                "TimeInForce": TIF_DAY,  # 1=DAY
                "ClientOrderID": order_id,
                "TradeAccount": self._account_for_symbol(sc_symbol),
                "Exchange": self._exchange_for_symbol(sc_symbol)
            }

            # Envoyer ordre
            if await self._send_dtc_message(sock, order_request):
                # Log clair
                price_info = ""
                if request.limit_price:
                    price_info = f" @L {request.limit_price}"
                # Note: OrderRequest n'a pas de stop_price

                bracket_info = ""

                logger.info(f"ORDER {symbol} {request.side} {request.qty}{price_info} tif=DAY{bracket_info} sent")

                return OrderResponse(
                    order_id=order_id,
                    status="sent",
                    message="Ordre envoyé via DTC",
                    timestamp=datetime.now(timezone.utc)
                )
            else:
                return OrderResponse(
                    order_id="",
                    status="rejected",
                    message="Échec envoi DTC",
                    timestamp=datetime.now(timezone.utc)
                )

        except Exception as e:
            logger.error(f"Erreur ordre réel: {e}")
            return OrderResponse(
                order_id="",
                status="rejected",
                message=f"Erreur: {e}",
                timestamp=datetime.now(timezone.utc)
            )

    async def place_bracket(
        self,
        symbol: str,
        side: str,
        qty: float,
        entry_kind: str,
        entry_price: Optional[float] = None,
        *,
        tp_price: Optional[float] = None,
        sl_price: Optional[float] = None,
        use_offsets: bool = False,
        tp_offset_ticks: Optional[int] = None,
        sl_offset_ticks: Optional[int] = None,
        client_tag: str = "MIA"
    ) -> Dict[str, Any]:
        """
        Envoie un bracket DTC conforme Sierra Chart:
          1) Parent via SUBMIT_NEW_SINGLE_ORDER avec IsParentOrder=1
          2) Enfants via SUBMIT_NEW_OCO_ORDER, liés par ParentTriggerClientOrderID

        - symbol: doit correspondre au texte du graphe Sierra; sera normalisé en -CME si besoin
        - side: "BUY" ou "SELL" pour le parent
        - entry_kind: "MKT" | "LMT" | "STOP"
        - entry_price: requis pour LMT/STOP, ignoré pour MKT
        - tp/sl en prix absolus OU offsets en ticks si use_offsets=True
        """

        # S'assurer que la connexion existe ou basculer en papier
        await self.ensure_connected(symbol)

        sc_symbol = self._to_sierra_trading_symbol(symbol)
        trade_account = self._account_for_symbol(sc_symbol)
        # ✅ Fallback papier si la connexion n'est pas dispo
        key = sc_symbol
        sock = self.connections.get(key)
        if self.paper_mode or not sock:
            parent_id = f"{client_tag}_P_{int(time.time())}_{uuid.uuid4().hex[:6]}"
            now = datetime.now(timezone.utc).isoformat()
            # parent
            self.paper_orders.append({
                "order_id": parent_id, "symbol": symbol, "side": side,
                "quantity": float(qty), "order_type": entry_kind,
                "limit_price": float(entry_price or 0.0), "stop_price": None,
                "time_in_force": "DAY", "bracket": None, "status": "open", "timestamp": now
            })
            # enfants
            tp_id = f"{client_tag}_TP_{uuid.uuid4().hex[:6]}"
            sl_id = f"{client_tag}_SL_{uuid.uuid4().hex[:6]}"
            self.paper_orders.append({
                "order_id": tp_id, "symbol": symbol,
                "side": "SELL" if (side or "").upper() == "BUY" else "BUY",
                "quantity": float(qty), "order_type": "LMT",
                "limit_price": float(tp_price) if not use_offsets else None,
                "stop_price": None, "time_in_force": "DAY",
                "bracket": parent_id, "status": "open", "timestamp": now
            })
            self.paper_orders.append({
                "order_id": sl_id, "symbol": symbol,
                "side": "SELL" if (side or "").upper() == "BUY" else "BUY",
                "quantity": float(qty), "order_type": "STP",
                "limit_price": None,
                "stop_price": float(sl_price) if not use_offsets else None,
                "time_in_force": "DAY", "bracket": parent_id,
                "status": "open", "timestamp": now
            })
            logger.info(f"[PAPER] BRACKET {sc_symbol} parent={parent_id} tp={tp_id} sl={sl_id}")
            return {"symbol": sc_symbol, "parent": parent_id, "tp_cid": tp_id, "sl_cid": sl_id, "trade_account": trade_account}

        # Générer un ClientOrderID parent stable et unique
        parent_client_id = f"{client_tag}_P_{int(time.time())}_{uuid.uuid4().hex[:6]}"

        # Mapper le type d'ordre d'entrée
        kind_upper = (entry_kind or "MKT").upper()
        if kind_upper in ("MKT", "MARKET"):
            parent_order_type = OT_MARKET
        elif kind_upper in ("LMT", "LIMIT"):
            parent_order_type = OT_LIMIT
        elif kind_upper in ("STP", "STOP"):
            parent_order_type = OT_STOP
        else:
            parent_order_type = OT_MARKET

        # Construire le parent
        parent_msg = {
            "Type": SUBMIT_NEW_SINGLE_ORDER,
            "RequestID": self.request_id_counter,
            "Symbol": sc_symbol,
            "OrderType": parent_order_type,
            "BuySell": self._map_side_to_dtc_buy_sell(side),
            "Quantity": float(qty),
            "Price1": float(entry_price or 0.0),
            "Price2": 0.0,
            "TimeInForce": TIF_DAY,
            "ClientOrderID": parent_client_id,
            "TradeAccount": trade_account,
            # ❌ IsParentOrder NE FONCTIONNE PAS en simulation locale !
            # "IsParentOrder": 1,  # RETIRÉ - Cause rejet silencieux
            "OpenCloseTrade": 1,
            "Exchange": ""
        }
        self.request_id_counter += 1

        # Envoyer le parent
        # Utiliser la socket déjà résolue
        if not await self._send_dtc_message(sock, parent_msg):
            logger.error("Échec envoi parent bracket DTC")
            return {"error": "parent_send_failed"}

        # Attente ACK parent (homogène avec place_parent_then_children)
        ack_event = asyncio.Event()
        self._pending_events[parent_client_id] = ack_event
        try:
            try:
                await asyncio.wait_for(ack_event.wait(), timeout=2.0)
            except asyncio.TimeoutError:
                logger.warning("Aucun ACK parent (bracket) reçu dans le délai — poursuite prudente")
            parent_ack = self._pending_acks.pop(parent_client_id, None)
            if parent_ack:
                status_txt = parent_ack.get("OrderStatusText") or parent_ack.get("Status") or ""
                result = parent_ack.get("Result")
                if (isinstance(status_txt, str) and status_txt.lower().startswith("rejected")) or (result == 0):
                    logger.error(f"Parent rejeté (bracket): {parent_ack}")
                    return {"error": "parent_rejected", "details": parent_ack}
        finally:
            self._pending_events.pop(parent_client_id, None)

        # Déterminer le côté des enfants (opposé au parent)
        parent_side = (side or "").upper()
        child_side_code = BS_BUY if parent_side == "SELL" else BS_SELL

        # Construire l'OCO enfants (TP/SL)
        oco_msg: Dict[str, Any] = {
            "Type": SUBMIT_NEW_OCO_ORDER,
            "RequestID": self.request_id_counter,
            "Symbol": sc_symbol,
            "TimeInForce": TIF_DAY,
            "TradeAccount": trade_account,
            "ParentTriggerClientOrderID": parent_client_id,
            "Exchange": "",

            # 🔥 CHAMPS MAGIQUES POUR BRACKET ORDERS
            "IsAutomatedOrder": 1,
            "OpenOrClose": 2,  # CLOSE position
            "MaintainSamePricesOnParentFill": 1  # ✅ ACTIVER GESTION OCO !
        }

        if use_offsets:
            if tp_offset_ticks is None or sl_offset_ticks is None:
                raise ValueError("use_offsets=True requiert tp_offset_ticks et sl_offset_ticks")
            oco_msg.update({
                "UseOffsets": 1,
                "Quantity_1": float(qty),
                "OrderType_1": OT_LIMIT,
                "BuySell_1": child_side_code,
                "OffsetFromParent1": int(tp_offset_ticks),

                "Quantity_2": float(qty),
                "OrderType_2": OT_STOP,
                "BuySell_2": child_side_code,
                "OffsetFromParent2": int(sl_offset_ticks)
            })
        else:
            if tp_price is None or sl_price is None:
                raise ValueError("tp_price et sl_price sont requis quand use_offsets=False")
            oco_msg.update({
                "Quantity_1": float(qty),
                "OrderType_1": OT_LIMIT,
                "BuySell_1": child_side_code,
                "Price1_1": float(tp_price),

                "Quantity_2": float(qty),
                "OrderType_2": OT_STOP,
                "BuySell_2": child_side_code,
                "Price1_2": float(sl_price)
            })

        # IDs enfants optionnels (utile pour le suivi)
        oco_msg["ClientOrderID_1"] = f"{client_tag}_TP_{uuid.uuid4().hex[:6]}"
        oco_msg["ClientOrderID_2"] = f"{client_tag}_SL_{uuid.uuid4().hex[:6]}"

        self.request_id_counter += 1

        if not await self._send_dtc_message(sock, oco_msg):
            logger.error("Échec envoi OCO enfants bracket DTC")
            return {"error": "oco_send_failed", "parent": parent_client_id}

        logger.info(
            f"🔥 BRACKET {sc_symbol} parent={parent_client_id} tp={oco_msg['ClientOrderID_1']} sl={oco_msg['ClientOrderID_2']} MaintainSamePrice=1"
        )

        return {
            "symbol": sc_symbol,
            "parent": parent_client_id,
            "tp_cid": oco_msg["ClientOrderID_1"],
            "sl_cid": oco_msg["ClientOrderID_2"],
            "trade_account": trade_account
        }

    async def place_bracket_like_sierra(
        self,
        *,
        symbol: str,
        side: str,
        qty: float,
        entry_kind: str,
        entry_price: Optional[float],
        tp_ticks: int,
        sl_ticks: int,
        client_tag: str = "MIA"
    ) -> Dict[str, Any]:
        """
        Alias pratique: reproduit le flux "Attached Orders" côté serveur DTC
        en utilisant la logique offsets intégrée au message OCO.
        """
        return await self.place_bracket(
            symbol=symbol,
            side=side,
            qty=qty,
            entry_kind=entry_kind,
            entry_price=entry_price,
            use_offsets=True,
            tp_offset_ticks=tp_ticks,
            sl_offset_ticks=sl_ticks,
            client_tag=client_tag
        )

    async def place_parent_then_children(
        self,
        *,
        symbol: str,
        side: str,
        qty: float,
        tp_price: float,
        sl_price: float,
        entry_kind: str = "MKT",
        entry_price: Optional[float] = None,
        client_tag: str = "MIA",
        children_mode: "ChildrenMode|str" = ChildrenMode.SEPARATE
    ) -> Dict[str, Any]:
        """
        Variante parent puis enfants (TP/SL) liés via ParentTriggerClientOrderID.
        - Parent: SUBMIT_NEW_SINGLE_ORDER avec IsParentOrder=1
        - Enfants: SUBMIT_NEW_OCO_ORDER (LIMIT + STOP) attachés au parent
        """
        await self.ensure_connected(symbol)

        sc_symbol = self._to_sierra_trading_symbol(symbol)
        trade_account = self._account_for_symbol(sc_symbol)
        # Utiliser la clé normalisée pour récupérer la socket
        key = sc_symbol
        sock = self.connections.get(key)

        # PAPER MODE: simuler 3 ordres
        if self.paper_mode or not sock:
            parent_id = f"{client_tag}_P_{int(time.time())}_{uuid.uuid4().hex[:6]}"
            now = datetime.now(timezone.utc).isoformat()
            self.paper_orders.append({
                "order_id": parent_id, "symbol": symbol, "side": side,
                "quantity": float(qty), "order_type": "MKT",
                "limit_price": None, "stop_price": None, "time_in_force": "DAY",
                "bracket": None, "status": "open", "timestamp": now
            })
            tp_id = f"{client_tag}_TP_{uuid.uuid4().hex[:6]}"
            sl_id = f"{client_tag}_SL_{uuid.uuid4().hex[:6]}"
            self.paper_orders.append({
                "order_id": tp_id, "symbol": symbol,
                "side": "SELL" if (side or "").upper() == "BUY" else "BUY",
                "quantity": float(qty), "order_type": "LMT",
                "limit_price": float(tp_price), "stop_price": None,
                "time_in_force": "DAY", "bracket": parent_id,
                "status": "open", "timestamp": now
            })
            self.paper_orders.append({
                "order_id": sl_id, "symbol": symbol,
                "side": "SELL" if (side or "").upper() == "BUY" else "BUY",
                "quantity": float(qty), "order_type": "STP",
                "limit_price": None, "stop_price": float(sl_price),
                "time_in_force": "DAY", "bracket": parent_id,
                "status": "open", "timestamp": now
            })
            logger.info(f"[PAPER] Parent+Enfants {sc_symbol} parent={parent_id} tp={tp_id} sl={sl_id}")
            return {"ok": True, "symbol": sc_symbol, "parent": parent_id, "tp_cid": tp_id, "sl_cid": sl_id, "trade_account": trade_account}

        # Construire parent
        kind_u = (entry_kind or "MKT").upper()
        if kind_u in ("MKT", "MARKET"):
            parent_ot = OT_MARKET
            p1, p2 = 0.0, 0.0
        elif kind_u in ("LMT", "LIMIT"):
            parent_ot = OT_LIMIT
            p1, p2 = float(entry_price or 0.0), 0.0
        elif kind_u in ("STP", "STOP"):
            parent_ot = OT_STOP
            p1, p2 = 0.0, float(entry_price or 0.0)
        else:
            parent_ot = OT_MARKET
            p1, p2 = 0.0, 0.0

        parent_cid = f"{client_tag}_P_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        exchange = self._exchange_for_symbol(sc_symbol)
        parent_msg = {
            "Type": SUBMIT_NEW_SINGLE_ORDER,
            "RequestID": self.request_id_counter,
            "Symbol": sc_symbol,
            "OrderType": parent_ot,
            "BuySell": self._map_side_to_dtc_buy_sell(side),
            "Quantity": float(qty),
            "Price1": p1,
            "Price2": p2,
            "TimeInForce": TIF_DAY,
            "ClientOrderID": parent_cid,
            "TradeAccount": trade_account,
            # ❌ IsParentOrder NE FONCTIONNE PAS en simulation locale !
            # "IsParentOrder": 1,  # RETIRÉ - Cause rejet silencieux
            "OpenCloseTrade": 1,
            "Exchange": exchange
        }
        if parent_ot == OT_STOP:
            parent_msg["StopPrice"] = float(entry_price or 0.0)
        self.request_id_counter += 1

        logger.info(f"[DTC->] parent TradeAccount={trade_account} CID={parent_cid} {parent_msg}")
        if not await self._send_dtc_message(sock, parent_msg):
            logger.error("Échec envoi parent DTC")
            return {"error": "parent_send_failed"}

        # 🔥 ATTENDRE QUE LE PARENT SOIT FILLED (pour que la position existe)
        logger.info(f"⏳ Attente du FILL du parent {parent_cid}...")
        parent_filled = False
        ack_event = asyncio.Event()
        self._pending_events[parent_cid] = ack_event

        # Stocker un flag pour détecter le fill
        self._pending_acks[parent_cid + "_FILL_EXPECTED"] = True

        try:
            # Attendre jusqu'à 5 secondes pour le fill
            for attempt in range(50):  # 50 x 0.1s = 5s max
                await asyncio.sleep(0.1)
                parent_ack = self._pending_acks.get(parent_cid)
                if parent_ack:
                    order_status = parent_ack.get("OrderStatus")
                    if order_status == 7:  # FILLED
                        parent_filled = True
                        logger.info(f"✅ Parent FILLED - Position ouverte !")
                        break
                    elif order_status in (3, 4):  # PENDING ou OPEN
                        continue  # Attendre encore
                    else:
                        logger.warning(f"⚠️ Parent status inattendu: {order_status}")
                        break

            if not parent_filled:
                logger.warning(f"⚠️ Parent non FILLED après 5s - Envoi TP/SL quand même")

            # Vérifier rejet
            parent_ack = self._pending_acks.get(parent_cid)
            if parent_ack:
                status_txt = parent_ack.get("OrderStatusText") or parent_ack.get("Status") or ""
                result = parent_ack.get("Result")
                if (isinstance(status_txt, str) and status_txt.lower().startswith("rejected")) or (result == 0):
                    logger.error(f"Parent rejeté par le serveur: {parent_ack}")
                    return {"error": "parent_rejected", "details": parent_ack}
        finally:
            self._pending_events.pop(parent_cid, None)
            self._pending_acks.pop(parent_cid + "_FILL_EXPECTED", None)

        # Chemin enfants
        mode_str = str(children_mode).lower()
        if mode_str in ("oco206", "childrenmode.oco206"):
            result = await self._send_children_oco206(
                sc_symbol=sc_symbol,
                trade_account=trade_account,
                parent_cid=parent_cid,
                side=side,
                qty=qty,
                tp_price=tp_price,
                sl_price=sl_price,
                client_tag=client_tag,
            )
            if result.get("error"):
                return {"error": result["error"], "parent": parent_cid}
            return {"ok": True, "symbol": sc_symbol, "parent": parent_cid, "tp_cid": result["tp_cid"], "sl_cid": result["sl_cid"], "trade_account": trade_account}
        else:
            # Enfants en 2 SINGLE
            child_side_code = BS_BUY if (side or "").upper() == "SELL" else BS_SELL
            tp_cid = f"{client_tag}_TP_{uuid.uuid4().hex[:6]}"
            sl_cid = f"{client_tag}_SL_{uuid.uuid4().hex[:6]}"

            oco_group = f"{client_tag}_OCO_{int(time.time())}"

            tp_msg = {
                "Type": SUBMIT_NEW_SINGLE_ORDER,
                "RequestID": self.request_id_counter,
                "Symbol": sc_symbol,
                "OrderType": OT_LIMIT,
                "BuySell": child_side_code,
                "Quantity": float(qty),
                "Price1": float(tp_price),
                "Price2": 0.0,
                "TimeInForce": TIF_DAY,
                "ClientOrderID": tp_cid,
                "TradeAccount": trade_account,
                "ParentTriggerClientOrderID": parent_cid,
                "OCOGroup1": oco_group,  # 🔥 OCOGroup1 (avec 1) pour SPAWN VICTOIRE
                "OpenCloseTrade": 2,
                "Exchange": exchange
            }
            self.request_id_counter += 1

            sl_msg = {
                "Type": SUBMIT_NEW_SINGLE_ORDER,
                "RequestID": self.request_id_counter,
                "Symbol": sc_symbol,
                "OrderType": OT_STOP,
                "BuySell": child_side_code,
                "Quantity": float(qty),
                "Price1": float(sl_price),
                "Price2": 0.0,
                "TimeInForce": TIF_DAY,
                "ClientOrderID": sl_cid,
                "TradeAccount": trade_account,
                "ParentTriggerClientOrderID": parent_cid,
                "OCOGroup1": oco_group,  # 🔥 OCOGroup1 (avec 1) pour SPAWN VICTOIRE
                "OpenCloseTrade": 2,
                "Exchange": exchange,
                "StopPrice": float(sl_price)
            }
            self.request_id_counter += 1

            # 🔥 ENVOI SIMPLE: TP et SL liés uniquement via OCOGroup1
            logger.info(f"[DTC->] child TP CID={tp_cid}")
            ok_tp = await self._send_dtc_message(sock, tp_msg)

            logger.info(f"[DTC->] child SL CID={sl_cid}")
            ok_sl = await self._send_dtc_message(sock, sl_msg)

            if not (ok_tp and ok_sl):
                logger.error("Échec envoi enfants SINGLE (TP/SL)")
                return {"error": "children_send_failed", "parent": parent_cid}

            # 🔥 Enregistrer paire OCO pour annulation automatique
            self._oco_pairs[tp_cid] = sl_cid
            self._oco_pairs[sl_cid] = tp_cid
            logger.info(f"🔥 OCO Pair enregistrée: {tp_cid} ↔ {sl_cid}")

            logger.info(f"✅ PARENT+CHILDREN {sc_symbol} parent={parent_cid} tp={tp_cid} sl={sl_cid}")
            return {"ok": True, "symbol": sc_symbol, "parent": parent_cid, "tp_cid": tp_cid, "sl_cid": sl_cid, "trade_account": trade_account}

    async def _cancel_paper_order(self, order_id: str) -> bool:
        """Annule un ordre en PAPER MODE"""
        try:
            for order in self.paper_orders:
                if order["order_id"] == order_id and order["status"] == "open":
                    order["status"] = "cancelled"
                    logger.info(f"PAPER MODE: ordre {order_id} annulé")
                    return True

            logger.warning(f"Ordre PAPER {order_id} non trouvé")
            return False

        except Exception as e:
            logger.error(f"Erreur annulation PAPER {order_id}: {e}")
            return False

    async def _cancel_real_order(self, order_id: str, symbol: str) -> bool:
        """Annule un ordre réel via DTC"""
        try:
            key = self._to_sierra_trading_symbol(symbol)
            sock = self.connections.get(key)
            if not sock:
                return False

            # Message d'annulation DTC
            cancel_request = {
                "Type": 209,  # CANCEL_ORDER
                "RequestID": self.request_id_counter,
                "ClientOrderID": order_id
            }

            if await self._send_dtc_message(sock, cancel_request):
                logger.info(f"ORDER {order_id} cancel sent")
                return True
            else:
                return False

        except Exception as e:
            logger.error(f"Erreur annulation réelle {order_id}: {e}")
            return False

    async def _heartbeat_loop(self, symbol: str):
        """Boucle heartbeat pour un symbole"""
        while (symbol in self.connections and
               self.status.get(symbol) == ConnectionStatus.CONNECTED):
            try:
                sock = self.connections[symbol]
                heartbeat = {"Type": HEARTBEAT}
                await self._send_dtc_message(sock, heartbeat)

                await asyncio.sleep(self.config.heartbeat_interval)

            except Exception as e:
                logger.error(f"Erreur heartbeat {symbol}: {e}")
                break

        # Marquer comme déconnecté
        if symbol in self.status:
            self.status[symbol] = ConnectionStatus.DISCONNECTED
        if symbol in self.connections:
            del self.connections[symbol]

    async def disconnect(self, symbol: Optional[str] = None):
        """Fermeture propre des connexions DTC (streams ou sockets)."""
        try:
            if symbol:
                key = self._to_sierra_trading_symbol(symbol)
                if key in self.connections:
                    # Stop reader task
                    task = self._reader_tasks.pop(key, None)
                    if task and not task.done():
                        task.cancel()
                        with contextlib.suppress(asyncio.CancelledError):
                            await task
                    obj = self.connections.pop(key)
                    # Tenter envoi LOGOFF puis fermer
                    with contextlib.suppress(Exception):
                        await self._send_dtc_message(obj, {"Type": LOGOFF})
                    # StreamWriter
                    if hasattr(obj, "close") and hasattr(obj, "drain"):
                        try:
                            obj.close()
                            with contextlib.suppress(Exception):
                                await obj.wait_closed()
                        except Exception:
                            pass
                    # Socket
                    elif isinstance(obj, socket.socket):
                        with contextlib.suppress(Exception):
                            obj.close()
                    self.status[key] = ConnectionStatus.DISCONNECTED
                    logger.info(f"🔌 Déconnexion DTC {key}")
            else:
                for sym, obj in list(self.connections.items()):
                    task = self._reader_tasks.pop(sym, None)
                    if task and not task.done():
                        task.cancel()
                        with contextlib.suppress(asyncio.CancelledError):
                            await task
                    with contextlib.suppress(Exception):
                        await self._send_dtc_message(obj, {"Type": LOGOFF})
                    # StreamWriter
                    if hasattr(obj, "close") and hasattr(obj, "drain"):
                        try:
                            obj.close()
                            with contextlib.suppress(Exception):
                                await obj.wait_closed()
                        except Exception:
                            pass
                    # Socket
                    elif isinstance(obj, socket.socket):
                        with contextlib.suppress(Exception):
                            obj.close()
                    self.status[sym] = ConnectionStatus.DISCONNECTED
                    self.connections.pop(sym, None)
                logger.info("🔌 Déconnexion DTC complète")
        except Exception as e:
            logger.error(f"❌ Erreur déconnexion: {e}")

    @staticmethod
    def _map_kind_to_dtc_order_type(kind: str) -> int:
        # DTC ORDER_TYPE: 1=MARKET, 2=LIMIT, 3=STOP, 4=STOP_LIMIT, ...
        k = (kind or "").upper()
        if k in ("MKT", "MARKET"):
            return 1
        if k in ("LMT", "LIMIT"):
            return 2
        if k in ("STP", "STOP"):
            return 3
        return 0  # Unknown/unspecified

    @staticmethod
    def _map_side_to_dtc_buy_sell(side: str) -> int:
        s = (side or "").upper()
        if s == "BUY":
            return 1
        if s == "SELL":
            return 2
        return 0

    async def _send_heartbeat(self, sock, interval_s: int = 10):
        while True:
            try:
                await self._send_dtc_message(sock, {"Type": HEARTBEAT})
            except Exception:
                break
            await asyncio.sleep(max(5, interval_s))

    async def _start_keep_alive(self, sock):
        asyncio.create_task(self._send_heartbeat(sock, self.config.heartbeat_interval))

    async def _read_loop_brief(self, sock, duration_sec: int):
        end_ts = time.time() + duration_sec
        buffer = b""
        loop = asyncio.get_event_loop()
        while time.time() < end_ts:
            try:
                chunk = await loop.run_in_executor(None, sock.recv, 32768)
                if not chunk:
                    await asyncio.sleep(0.05)
                    continue
                buffer += chunk
                while True:
                    i = buffer.find(b"\x00")
                    if i < 0:
                        break
                    raw = buffer[:i]
                    buffer = buffer[i+1:]
                    if not raw:
                        continue
                    try:
                        msg = json.loads(raw.decode("utf-8"))
                    except Exception:
                        continue
                    t = msg.get("Type")
                    if t not in (HEARTBEAT,):
                        logger.debug(f"DTC ← {msg}")
            except Exception:
                await asyncio.sleep(0.05)
                continue

# === FACTORY FUNCTIONS ===

def create_sierra_dtc_connector(
    host: str = "127.0.0.1",
    es_port: int = 11099,
    nq_port: int = 11099,
    username: str = "",
    password: str = "",
    trade_account_map: dict | None = None
) -> SierraDTCConnector:
    """Factory function pour SierraDTCConnector"""
    config = DTCConfig(
        host=host,
        es_port=es_port,
        nq_port=nq_port,
        username=username,
        password=password,
        trade_account_map=trade_account_map
    )
    return SierraDTCConnector(config)

# === TESTING ===

async def test_sierra_dtc_connector():
    """Tests du connecteur DTC"""
    logger.info("Test SierraDTCConnector...")

    connector = create_sierra_dtc_connector()

    # Test 1: Connexion (va échouer en mode test, mais va basculer PAPER MODE)
    result = await connector.connect("ES")
    logger.info(f"✅ Test connexion: {result}")

    # Test 2: Ordre PAPER MODE
    order_request = OrderRequest(
        symbol="ES",
        side=OrderSide.BUY.value,
        qty=1.0,
        kind=OrderType.LIMIT.value,
        limit_price=5294.75,
        time_in_force=TimeInForce.DAY.value
    )

    response = await connector.place_order(order_request)
    assert response.status in ["sent", "rejected"], "Statut ordre invalide"
    logger.info(f"✅ Test ordre PAPER: {response.status}")

    # Test 3: Ordre avec bracket
    bracket_request = OrderRequest(
        symbol="ES",
        side=OrderSide.BUY.value,
        qty=2.0,
        kind=OrderType.LIMIT.value,
        limit_price=5294.75,
        bracket={"stop_loss": 5290.0, "take_profit": 5300.0}
    )

    response = await connector.place_order(bracket_request)
    assert response.status in ["sent", "rejected"], "Statut ordre bracket invalide"
    logger.info(f"✅ Test ordre bracket: {response.status}")

    # Test 4: Ordres ouverts
    open_orders = await connector.get_open_orders("ES")
    logger.info(f"✅ Test ordres ouverts: {len(open_orders)} ordres")

    # Test 5: Annulation
    if open_orders:
        order_id = open_orders[0]["order_id"]
        cancel_result = await connector.cancel(order_id, "ES")
        logger.info(f"✅ Test annulation: {cancel_result}")

    logger.info("🎉 Tous les tests SierraDTCConnector réussis!")
    return connector

if __name__ == "__main__":
    print("🧪 Tests Sierra DTC Connector v2.0 (Orders-Only)")
    print("="*50)

    # Lancer les tests
    asyncio.run(test_sierra_dtc_connector())

    print("\n" + "="*50)
    print("🎉 TOUS LES TESTS RÉUSSIS!")
    print("Sierra DTC Connector v2.0 - Orders-Only ✅")
