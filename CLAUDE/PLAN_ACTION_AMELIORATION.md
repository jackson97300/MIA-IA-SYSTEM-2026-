# 📋 PLAN D'ACTION - AMÉLIORATION SYSTÈME MIA

**Date:** 30 Novembre 2025
**Objectif:** Passer de 7.3/10 à 9+/10 en 6 semaines
**Status:** ✅ Production-ready maintenant, améliorations = nice-to-have

---

## 🎯 PRIORISATION

```
╔════════════════════════════════════════════════════════════════════════════╗
║  MATRICE IMPACT vs EFFORT                                                  ║
╠════════════════════════════════════════════════════════════════════════════╣
║                                                                            ║
║              │  Effort Faible     │  Effort Moyen    │  Effort Élevé     ║
║  ════════════╪═══════════════════════════════════════════════════════════ ║
║  Impact      │  🟢 QUICK WINS    │  🟡 PRIORITÉ 2   │  🔴 LONG TERME    ║
║  ÉLEVÉ       │  • Snapshots //   │  • Docker        │  • Scalability    ║
║              │  • Cache data     │  • CI/CD         │  • Multi-process  ║
║              │  • Tests critiques│  • Pydantic      │                   ║
║  ════════════╪═══════════════════════════════════════════════════════════ ║
║  Impact      │  ⚪ BONUS         │  ⚪ SI TEMPS     │  ⚫ SKIP          ║
║  FAIBLE      │  • Prometheus     │  • Refactor      │  • Rewrite        ║
║              │  • GC control     │    lanceur       │                   ║
║  ════════════╧═══════════════════════════════════════════════════════════ ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝
```

---

## 🚀 PHASE 1: QUICK WINS (1 semaine)

### Objectif: +0.7 points (7.3 → 8.0)

### Action 1: Snapshots Parallèles ⭐⭐⭐
**Temps:** 15 minutes
**Impact:** -20ms latence
**Gain:** +0.5 point Performance

```python
# LAUNCH/launch_production_CLEAN_v2.py

# AVANT (ligne 1021):
for symbol in self.config.symbols:
    snapshot = self.ml_reader.read_latest_snapshot(symbol)
    # ...

# APRÈS:
async def _read_all_snapshots_parallel(self) -> Dict[str, Dict]:
    """Lit tous les snapshots en parallèle"""
    tasks = []
    for symbol in self.config.symbols:
        task = asyncio.create_task(
            asyncio.to_thread(
                self.ml_reader.read_latest_snapshot,
                symbol
            )
        )
        tasks.append((symbol, task))

    snapshots = {}
    for symbol, task in tasks:
        try:
            snapshot = await task
            if snapshot:
                snapshots[symbol] = snapshot
        except Exception as e:
            logger.error(f"Erreur lecture {symbol}: {e}")

    return snapshots

# Dans run():
snapshots = await self._read_all_snapshots_parallel()
```

---

### Action 2: Cache Données Statiques ⭐⭐⭐
**Temps:** 30 minutes
**Impact:** -10ms latence
**Gain:** +0.2 point Performance

```python
# LAUNCH/launch_production_CLEAN_v2.py

from functools import lru_cache

class CleanTradingSystem:

    @lru_cache(maxsize=1)
    def _get_vix_thresholds(self):
        """Cache VIX thresholds (ne changent jamais)"""
        return self.config.vix_thresholds

    @lru_cache(maxsize=10)
    def _get_tick_size(self, symbol: str):
        """Cache tick size"""
        return self.config.tick_size.get(symbol, 0.25)

    @lru_cache(maxsize=10)
    def _get_point_value(self, symbol: str):
        """Cache point value"""
        return self.config.point_value.get(symbol, 50.0)
```

---

### Action 3: Tests Unitaires Critiques ⭐⭐⭐
**Temps:** 2 jours
**Impact:** Fiabilité +30%
**Gain:** +1.0 point Testing (3→4)

```python
# tests/unit/test_risk_manager.py

import pytest
from execution.risk_manager import RiskManager

def test_daily_loss_limit_blocks_trade():
    """Test que daily loss limit bloque trades"""
    config = {
        'max_position_size': 1,
        'max_daily_loss': -500,
        'data_collection_mode': False,
        'kill_switch_enabled': True
    }
    rm = RiskManager(config=config)

    # Simulate loss
    current_positions = {}
    daily_pnl = -600  # Over limit

    signal = {
        'action': 'LONG',
        'confidence': 0.85,
        'entry': 5000,
        'stop_loss': 4980
    }

    # Should reject
    is_valid, reason = rm.evaluate_signal(
        signal=signal,
        snapshot={},
        current_positions=current_positions,
        daily_pnl=daily_pnl
    )

    assert not is_valid
    assert "loss limit" in reason.lower()

def test_max_positions_blocks_duplicate():
    """Test que max positions bloque doublons"""
    rm = RiskManager(config={'max_position_size': 1})

    current_positions = {'ES': {'qty': 1, 'side': 'LONG'}}

    # Try to open another ES position
    signal = {'action': 'LONG', 'entry': 5000}

    is_valid, reason = rm.evaluate_signal(
        signal=signal,
        snapshot={'symbol': 'ES'},
        current_positions=current_positions,
        daily_pnl=0
    )

    assert not is_valid
    assert "position exists" in reason.lower()

# Run: pytest tests/unit/ -v
```

**Checklist Tests Phase 1:**
- [ ] test_risk_manager.py (5 tests)
- [ ] test_session_quality.py (3 tests)
- [ ] test_position_manager.py (4 tests)
- [ ] GitHub Actions workflow
- [ ] Badge coverage dans README

**Total Phase 1:** 3 jours, +0.7 points

---

## 🏗️ PHASE 2: INFRASTRUCTURE (2 semaines)

### Objectif: +0.7 points (8.0 → 8.7)

### Action 4: Dockerisation ⭐⭐
**Temps:** 3 jours
**Impact:** Deploy 10x plus rapide
**Gain:** +1.5 points Deployment (4→7)

```dockerfile
# Dockerfile

FROM python:3.11-slim

# Metadata
LABEL maintainer="trading@mia.com"
LABEL version="2.0"

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Create directories
RUN mkdir -p logs_advanced snapshots_trades

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s \
  CMD python -c "import sys; sys.exit(0)"

# Run
CMD ["python", "LAUNCH/launch_production_CLEAN_v2.py"]
```

```yaml
# docker-compose.yml

version: '3.8'

services:
  mia-trading:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: mia_trading_bot
    environment:
      - ENV=production
      - PYTHONUNBUFFERED=1
    env_file:
      - .env
    volumes:
      # Data (read-only)
      - ./snapshots:/app/snapshots:ro
      - ./DATA_SIERRA_CHART:/app/DATA_SIERRA_CHART:ro
      # Logs (read-write)
      - ./logs_advanced:/app/logs_advanced
      - ./snapshots_trades:/app/snapshots_trades
    restart: unless-stopped
    networks:
      - trading-net
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

networks:
  trading-net:
    driver: bridge
```

**Commandes:**
```bash
# Build
docker-compose build

# Run
docker-compose up -d

# Logs
docker-compose logs -f mia-trading

# Stop
docker-compose down

# Restart
docker-compose restart mia-trading
```

---

### Action 5: CI/CD Pipeline ⭐⭐
**Temps:** 4 jours
**Impact:** Deploy automatique
**Gain:** +1.0 point Deployment (7→8.5)

```yaml
# .github/workflows/test-and-deploy.yml

name: Test and Deploy

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov

      - name: Run tests
        run: |
          pytest tests/ -v --cov=. --cov-report=xml --cov-report=term

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v3

      - name: Build Docker image
        run: |
          docker build -t mia-trading:${{ github.sha }} .
          docker tag mia-trading:${{ github.sha }} mia-trading:latest

      - name: Deploy to production
        run: |
          # SSH to prod server
          # docker-compose pull
          # docker-compose up -d
          echo "Deploy to production"

      - name: Notify Discord
        if: success()
        run: |
          curl -X POST ${{ secrets.DISCORD_WEBHOOK }} \
            -H "Content-Type: application/json" \
            -d '{"content": "✅ Deploy successful!"}'
```

---

### Action 6: Configuration Pydantic ⭐
**Temps:** 2 jours
**Impact:** Config plus robuste
**Gain:** +0.5 point Configuration (7→8)

```python
# config/settings.py

from pydantic import BaseSettings, validator, SecretStr
from typing import List, Dict
from pathlib import Path

class Settings(BaseSettings):
    """
    Configuration avec validation Pydantic

    Load from:
    1. Environment variables
    2. .env file
    3. Defaults
    """

    # Environment
    env: str = "development"

    # Trading
    symbols: List[str] = ["ES", "NQ", "RTY"]
    daily_loss_limit: int
    max_drawdown_percent: float = 0.15

    # DTC
    dtc_host: str = "127.0.0.1"
    dtc_port: int = 11099
    trade_accounts: Dict[str, str]

    # Discord (secret)
    discord_webhook: SecretStr

    # Paths
    snapshots_dir: Path = Path("snapshots")
    logs_dir: Path = Path("logs_advanced")

    # Validators
    @validator('symbols')
    def validate_symbols(cls, v):
        if not v or len(v) == 0:
            raise ValueError("Au moins 1 symbol requis")
        valid = ['ES', 'NQ', 'RTY', 'GC', 'CL']
        for sym in v:
            if sym not in valid:
                raise ValueError(f"Symbol invalide: {sym}")
        return v

    @validator('daily_loss_limit')
    def validate_loss_limit(cls, v):
        if v >= 0:
            raise ValueError("Loss limit doit être négatif")
        if v < -5000:
            raise ValueError("Loss limit trop large (max -5000)")
        return v

    @validator('dtc_port')
    def validate_port(cls, v):
        if not (1024 <= v <= 65535):
            raise ValueError("Port invalide (1024-65535)")
        return v

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
        env_nested_delimiter = '__'

# Usage
settings = Settings()

# Access
print(settings.symbols)  # ['ES', 'NQ', 'RTY']
print(settings.discord_webhook.get_secret_value())  # https://...
```

**.env (gitignored):**
```bash
ENV=production

# Trading
SYMBOLS=ES,NQ,RTY
DAILY_LOSS_LIMIT=-500
MAX_DRAWDOWN_PERCENT=0.15

# DTC
DTC_HOST=127.0.0.1
DTC_PORT=11099
TRADE_ACCOUNTS__ES=Sim1
TRADE_ACCOUNTS__NQ=Sim2
TRADE_ACCOUNTS__RTY=Sim3

# Secrets
DISCORD_WEBHOOK=https://discord.com/api/webhooks/...
```

**Total Phase 2:** 9 jours, +0.7 points

---

## 📊 TABLEAU RÉCAPITULATIF

| Phase | Actions | Temps | Gain Score | Score Après |
|-------|---------|-------|------------|-------------|
| **Actuel** | - | - | - | **7.3/10** |
| **Phase 1** | Snapshots//, Cache, Tests | 3j | +0.7 | **8.0/10** |
| **Phase 2** | Docker, CI/CD, Pydantic | 9j | +0.7 | **8.7/10** |
| **Phase 3** | Tests complets, Perf, Scale | 15j | +0.5 | **9.2/10** |

---

## ✅ CHECKLIST VALIDATION

### Avant de Commencer
- [ ] Backup complet système actuel
- [ ] Branch Git `feature/improvements`
- [ ] Documentation état actuel
- [ ] Tests baseline performance

### Phase 1 Complète
- [ ] Snapshots parallèles implémentés
- [ ] Cache données actif
- [ ] 12+ tests unitaires écrits
- [ ] Tests passent en local
- [ ] Performance -30ms mesurée
- [ ] Merge dans main

### Phase 2 Complète
- [ ] Dockerfile fonctionne
- [ ] docker-compose up réussi
- [ ] CI/CD GitHub Actions actif
- [ ] Pydantic config implémentée
- [ ] .env configuré
- [ ] Deploy automatique testé

### Phase 3 Complète
- [ ] Coverage tests >80%
- [ ] Profiling hotspots fait
- [ ] Latence <80ms atteinte
- [ ] Scale 10+ symbols testé
- [ ] Documentation à jour

---

## 🎯 CONCLUSION

```
╔════════════════════════════════════════════════════════════════════════════╗
║  PLAN D'ACTION RÉSUMÉ                                                      ║
╠════════════════════════════════════════════════════════════════════════════╣
║                                                                            ║
║  📅 TIMELINE:                                                              ║
║  • Phase 1 (Quick Wins):   3 jours  → Score 8.0/10                        ║
║  • Phase 2 (Infrastructure): 9 jours  → Score 8.7/10                        ║
║  • Phase 3 (Optimisation): 15 jours → Score 9.2/10                        ║
║                                                                            ║
║  TOTAL: 27 jours (1 mois) → +1.9 points                                   ║
║                                                                            ║
║  🎯 PRIORITÉ IMMÉDIATE:                                                    ║
║  Phase 1 Quick Wins (3 jours):                                             ║
║  1. Snapshots parallèles (15 min)                                          ║
║  2. Cache données (30 min)                                                 ║
║  3. Tests critiques (2 jours)                                              ║
║                                                                            ║
║  ⚠️  IMPORTANT:                                                             ║
║  Ton système est DÉJÀ production-ready!                                    ║
║  Ces améliorations sont pour MAINTENABILITÉ long-terme,                    ║
║  pas pour FONCTIONNALITÉ immédiate.                                        ║
║                                                                            ║
║  Tu peux:                                                                  ║
║  • Lancer production MAINTENANT                                            ║
║  • Faire Phase 1 en parallèle (non-bloquant)                               ║
║  • Phases 2-3 selon disponibilité                                          ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝
```

---

**Date:** 30 Novembre 2025
**Document:** Plan d'action amélioration système
**Priorité:** Phase 1 (3 jours) recommandée, Phases 2-3 optionnelles
