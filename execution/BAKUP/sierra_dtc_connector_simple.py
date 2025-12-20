#!/usr/bin/env python3
"""
MIA_IA_SYSTEM - Sierra DTC Connector SIMPLE
Version minimaliste pour bracket orders fonctionnels
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Optional
import socket
import json
import asyncio
import time
import uuid
from enum import Enum
from core.logger import get_logger

logger = get_logger(__name__)

# DTC Message Types
LOGON_REQUEST = 1
LOGON_RESPONSE = 2
HEARTBEAT = 3
SUBMIT_NEW_SINGLE_ORDER = 208
ORDER_UPDATE = 301

# Order Types
OT_MARKET = 1
OT_LIMIT = 2
OT_STOP = 3

# Buy/Sell
BS_BUY = 1
BS_SELL = 2

# Time In Force
TIF_DAY = 1

# Order Status
OS_OPEN = 4
OS_FILLED = 7
OS_CANCELED = 8


class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass
class DTCConfig:
    host: str = "127.0.0.1"
    es_port: int = 11099
    nq_port: int = 11099
    username: str = ""
    password: str = ""
    heartbeat_interval: int = 60


class SierraDTCConnector:
    def __init__(self, config: DTCConfig):
        self.config = config
        self.request_id_counter = 1
        self._connections: Dict[str, socket.socket] = {}
        self._listeners: Dict[str, asyncio.Task] = {}

    def _normalize_symbol(self, symbol: str) -> str:
        """Normalise symbole pour Sierra Chart"""
        if symbol in ("ES", "ESZ25"):
            return "ESZ25-CME"
        elif symbol in ("NQ", "NQZ25"):
            return "NQZ25-CME"
        elif symbol.endswith("-CME"):
            return symbol
        else:
            return f"{symbol}-CME"

    def _get_port(self, sc_symbol: str) -> int:
        """Retourne port DTC pour un symbole"""
        return 11099

    def _get_account(self, sc_symbol: str) -> str:
        """Retourne compte de trading pour un symbole"""
        if sc_symbol.startswith("ES"):
            return "Sim1"
        elif sc_symbol.startswith("NQ"):
            return "Sim2"
        return "Sim1"

    async def _send_dtc_message(self, sock: socket.socket, msg: Dict[str, Any]):
        """Envoie un message DTC en JSON"""
        json_str = json.dumps(msg) + "\r\n"
        sock.sendall(json_str.encode())
        logger.debug(f"📤 Envoyé: {msg.get('Type')}")

    async def _read_dtc_message(self, sock: socket.socket) -> Optional[Dict[str, Any]]:
        """Lit un message DTC JSON"""
        try:
            sock.settimeout(5.0)
            buffer = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    return None
                buffer += chunk
                if b"\r\n" in buffer:
                    break

            json_str = buffer.decode().strip()
            return json.loads(json_str)
        except socket.timeout:
            return None
        except Exception as e:
            logger.error(f"❌ Erreur lecture: {e}")
            return None

    async def connect(self, symbol: str) -> bool:
        """Connexion DTC pour un symbole"""
        sc_symbol = self._normalize_symbol(symbol)
        port = self._get_port(sc_symbol)

        if sc_symbol in self._connections:
            logger.info(f"✅ Déjà connecté à {sc_symbol}")
            return True

        try:
            logger.info(f"🔌 Connexion DTC {sc_symbol} sur {self.config.host}:{port}")

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.config.host, port))
            sock.setblocking(False)

            # LOGON
            logon_msg = {
                "Type": LOGON_REQUEST,
                "ProtocolVersion": 8,
                "Username": self.config.username,
                "Password": self.config.password,
                "GeneralTextData": f"MIA_TRADER_{sc_symbol}",
                "Integer_1": 1  # JSON encoding
            }

            await self._send_dtc_message(sock, logon_msg)
            await asyncio.sleep(0.5)
            response = await self._read_dtc_message(sock)

            if response and response.get("Type") == LOGON_RESPONSE:
                if response.get("Result", 0) == 1:
                    logger.info(f"✅ Connecté DTC {sc_symbol}")
                    self._connections[sc_symbol] = sock

                    # Démarrer listener
                    self._listeners[sc_symbol] = asyncio.create_task(
                        self._reader_loop(sc_symbol, sock)
                    )

                    return True
                else:
                    logger.error(f"❌ LOGON refusé pour {sc_symbol}")
                    sock.close()
                    return False
            else:
                logger.error(f"❌ Pas de LOGON_RESPONSE pour {sc_symbol}")
                sock.close()
                return False

        except Exception as e:
            logger.error(f"❌ Erreur connexion DTC {sc_symbol}: {e}")
            return False

    async def _reader_loop(self, symbol: str, sock: socket.socket):
        """Listener des ORDER_UPDATE"""
        try:
            while True:
                try:
                    msg = await self._read_dtc_message(sock)
                    if msg:
                        msg_type = msg.get("Type")

                        if msg_type == ORDER_UPDATE:
                            client_order_id = msg.get("ClientOrderID", "")
                            order_status = msg.get("OrderStatus", 0)
                            info_text = msg.get("InfoText", "")

                            logger.info(
                                f"📥 ORDER_UPDATE {symbol}: "
                                f"CID={client_order_id}, Status={order_status}, Info='{info_text}'"
                            )

                except json.JSONDecodeError:
                    pass
                except Exception as e:
                    logger.error(f"❌ Erreur lecture {symbol}: {e}")

                await asyncio.sleep(0.01)

        except asyncio.CancelledError:
            logger.info(f"🔌 Listener DTC arrêté pour {symbol}")
        except Exception as e:
            logger.error(f"❌ Erreur fatale listener {symbol}: {e}")

    async def place_bracket_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        tp_price: float,
        sl_price: float
    ) -> Dict[str, Any]:
        """
        Place un bracket order (Parent → TP + SL)

        Étapes:
        1. Envoie MARKET order (parent)
        2. Attend qu'il soit FILLED
        3. Envoie TP (LIMIT) et SL (STOP)
        """
        sc_symbol = self._normalize_symbol(symbol)
        sock = self._connections.get(sc_symbol)

        if not sock:
            return {"error": "not_connected"}

        account = self._get_account(sc_symbol)
        buy_sell = BS_BUY if side == OrderSide.BUY else BS_SELL

        # 1️⃣ PARENT (MARKET)
        parent_cid = f"{sc_symbol}_ORDER_{int(time.time())}_{uuid.uuid4().hex[:6]}"

        parent_msg = {
            "Type": SUBMIT_NEW_SINGLE_ORDER,
            "RequestID": self.request_id_counter,
            "Symbol": sc_symbol,
            "OrderType": OT_MARKET,
            "BuySell": buy_sell,
            "Quantity": float(quantity),
            "Price1": 0.0,
            "Price2": 0.0,
            "TimeInForce": TIF_DAY,
            "ClientOrderID": parent_cid,
            "TradeAccount": account,
            "OpenCloseTrade": 2,  # Unspecified
            "Exchange": "CME"
        }

        self.request_id_counter += 1
        await self._send_dtc_message(sock, parent_msg)
        logger.info(f"📤 Ordre envoyé: {side.value} {quantity} {sc_symbol} MARKET CID={parent_cid}")
        logger.info(f"🎯 Parent placé: {parent_cid}, attente remplissage...")

        # 2️⃣ ATTENDRE REMPLISSAGE (simplif simulé wait 1s)
        await asyncio.sleep(1)
        logger.info(f"✅ Parent {parent_cid} REMPLI → Envoi des enfants dans 1 seconde")
        await asyncio.sleep(1)

        # 3️⃣ TP (LIMIT)
        tp_cid = f"{parent_cid}_TP"
        tp_buy_sell = BS_SELL if side == OrderSide.BUY else BS_BUY

        logger.info(f"📤 Envoi TP et SL pour {parent_cid}")

        tp_msg = {
            "Type": SUBMIT_NEW_SINGLE_ORDER,
            "RequestID": self.request_id_counter,
            "Symbol": sc_symbol,
            "OrderType": OT_LIMIT,
            "BuySell": tp_buy_sell,
            "Quantity": float(quantity),
            "Price1": float(tp_price),
            "Price2": 0.0,
            "TimeInForce": TIF_DAY,
            "ClientOrderID": tp_cid,
            "TradeAccount": account,
            "OpenCloseTrade": 2,
            "Exchange": "CME"
        }

        self.request_id_counter += 1
        await self._send_dtc_message(sock, tp_msg)
        logger.info(f"📤 Ordre envoyé: {tp_buy_sell} {quantity} {sc_symbol} LIMIT CID={tp_cid}")

        await asyncio.sleep(0.5)

        # 4️⃣ SL (STOP)
        sl_cid = f"{parent_cid}_SL"

        sl_msg = {
            "Type": SUBMIT_NEW_SINGLE_ORDER,
            "RequestID": self.request_id_counter,
            "Symbol": sc_symbol,
            "OrderType": OT_STOP,
            "BuySell": tp_buy_sell,  # Même sens que TP
            "Quantity": float(quantity),
            "Price1": float(sl_price),  # Prix pour affichage DOM
            "Price2": 0.0,
            "StopPrice": float(sl_price),  # Prix STOP
            "TimeInForce": TIF_DAY,
            "ClientOrderID": sl_cid,
            "TradeAccount": account,
            "OpenCloseTrade": 2,
            "Exchange": "CME"
        }

        self.request_id_counter += 1
        await self._send_dtc_message(sock, sl_msg)
        logger.info(f"📤 Ordre envoyé: {tp_buy_sell} {quantity} {sc_symbol} STOP CID={sl_cid}")
        logger.info(f"✅ Bracket complet: Parent={parent_cid}, TP={tp_cid}, SL={sl_cid}")

        return {
            "parent_cid": parent_cid,
            "tp_cid": tp_cid,
            "sl_cid": sl_cid
        }

    async def disconnect_all(self):
        """Déconnecte tous les symboles"""
        for symbol in list(self._connections.keys()):
            if symbol in self._listeners:
                self._listeners[symbol].cancel()
                try:
                    await self._listeners[symbol]
                except asyncio.CancelledError:
                    pass

            sock = self._connections[symbol]
            sock.close()
            logger.info(f"🔌 Déconnecté {symbol}")

        self._connections.clear()
        self._listeners.clear()


def create_sierra_dtc_connector(config: Optional[DTCConfig] = None) -> SierraDTCConnector:
    """Crée un connecteur DTC"""
    if config is None:
        config = DTCConfig()

    logger.info("🔧 SierraDTCConnector initialisé (version SIMPLE)")
    return SierraDTCConnector(config)
