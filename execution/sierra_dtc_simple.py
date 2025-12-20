#!/usr/bin/env python3
"""
Sierra DTC Connector ULTRA-SIMPLE - Version qui MARCHE
"""

import socket
import json
import time
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from core.logger import get_logger

logger = get_logger(__name__)

class SierraDTCSimple:
    """Connecteur DTC ultra-simple qui MARCHE"""
    
    def __init__(self, username: str = "", password: str = ""):
        self.username = username
        self.password = password
        self.host = "127.0.0.1"
        self.port = 11099
        
    async def connect(self):
        """Connexion simple"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            
            # Logon simple
            logon = {
                "Type": 1,
                "ProtocolVersion": 8,
                "HeartbeatInterval": 10,
                "ClientName": "MIA_SIMPLE",
                "Username": self.username,
                "Password": self.password
            }
            
            self._send(logon)
            logger.info("✅ Connexion DTC simple établie")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur connexion: {e}")
            return False
    
    def _send(self, data: dict):
        """Envoi message DTC"""
        msg = (json.dumps(data, separators=(",", ":")) + "\n").encode("utf-8")
        self.sock.sendall(msg)
    
    async def place_simple_order(self, symbol: str, side: str, qty: float, 
                                order_type: str = "MARKET", price: float = 0.0,
                                trade_account: str = "Sim1") -> Dict[str, Any]:
        """Place un ordre simple qui MARCHE"""
        
        # Mapping simple
        order_type_map = {
            "MARKET": 1,
            "LIMIT": 2,
            "STOP": 3,
            "STOP_LIMIT": 4
        }
        
        side_map = {
            "BUY": 1,
            "SELL": 2
        }
        
        # Message DTC simple
        order = {
            "Type": 208,  # SUBMIT_NEW_SINGLE_ORDER
            "RequestID": int(time.time() * 1000) & 0x7fffffff,
            "Symbol": symbol,
            "OrderType": order_type_map.get(order_type, 1),
            "BuySell": side_map.get(side, 1),
            "Quantity": float(qty),
            "Price1": float(price),
            "Price2": 0.0,
            "TimeInForce": 1,  # DAY
            "ClientOrderID": f"MIA_{int(time.time())}",
            "TradeAccount": trade_account
        }
        
        try:
            self._send(order)
            logger.info(f"✅ Ordre {side} {qty} {symbol} @ {order_type} envoyé")
            return {"ok": True, "order_id": order["ClientOrderID"]}
            
        except Exception as e:
            logger.error(f"❌ Erreur envoi ordre: {e}")
            return {"ok": False, "error": str(e)}
    
    async def disconnect(self):
        """Déconnexion simple"""
        try:
            if hasattr(self, 'sock'):
                self.sock.close()
            logger.info("🔌 Déconnexion DTC simple")
        except:
            pass

# Fonction de création simple
def create_simple_connector(username: str = "", password: str = ""):
    """Crée un connecteur simple"""
    return SierraDTCSimple(username, password)
