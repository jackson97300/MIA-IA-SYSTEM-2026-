# 🎯 CONFIGURATION HYBRIDE COMPLÈTE - CORRECTIONS TECHNIQUES + SOLIDITÉ
# Date: 2025-08-11 - Intégration des meilleurs éléments des deux systèmes

class HybridTradingConfig:
    """🎯 Configuration hybride : Corrections techniques + Solidité risk management"""
    
    # ===== CORRECTIONS TECHNIQUES À GARDER =====
    
    # ✅ VWAP Bands - Maintenant fonctionnel
    VWAP_BANDS_ENABLED = True
    VWAP_BANDS_PERIOD = 20
    VWAP_BANDS_STD_DEV = 2.0
    
    # ✅ Volume ES - Affichage corrigé
    USE_TOTAL_VOLUME_FOR_ES = True  # Au lieu de es_volume
    
    # ✅ OrderFlow - Seuils optimisés
    MIN_CONFIDENCE_THRESHOLD = 0.100  # Garder les seuils qui marchent
    FOOTPRINT_THRESHOLD = 0.040
    VOLUME_THRESHOLD = 8
    DELTA_THRESHOLD = 0.06
    
    # ✅ SPX Retriever - Status correct
    SPX_RETRIEVER_FALLBACK_DISPLAY = "SAVED DATA MODE"
    
    # ===== SOLIDITÉ RISK MANAGEMENT (Ancien système) =====
    
    # 🛡️ LIMITES QUOTIDIENNES STRICTES
    DAILY_LOSS_LIMIT = 500.0              # 500$ max/jour
    DAILY_PROFIT_TARGET = 1000.0          # Target 1000$
    MAX_DAILY_TRADES = 10                 # 10 trades max/jour (vs illimité)
    MAX_DRAWDOWN_PERCENT = 5.0            # 5% max drawdown
    
    # 💰 GESTION DES POSITIONS
    BASE_POSITION_SIZE = 1                # Réduit de 2 à 1
    MAX_POSITION_SIZE = 3                 # Réduit de 5 à 3
    MAX_POSITIONS_CONCURRENT = 2          # Réduit de 3 à 2
    
    # 🛑 STOP LOSS ET TAKE PROFIT
    RISK_PER_TRADE_PERCENT = 0.5          # 0.5% du capital (vs 1%)
    MAX_RISK_PER_TRADE_DOLLARS = 250.0    # 250$ max/trade (vs 500$)
    MIN_RISK_REWARD_RATIO = 1.5           # 1.5:1 minimum
    
    # 🕐 RESTRICTIONS HORAIRES
    NO_TRADE_BEFORE = "09:35"             # 5 min après ouverture
    NO_TRADE_AFTER = "15:45"              # 15 min avant fermeture
    REDUCE_SIZE_AFTER = "15:00"           # Réduire après 15h
    
    # 📊 VALIDATION DE QUALITÉ
    MIN_BASE_QUALITY_FOR_TRADE = 0.6      # Augmenté de 0.5 à 0.6
    MIN_CONFLUENCE_SCORE = 0.60           # Augmenté de 0.55 à 0.60
    MIN_SIGNAL_PROBABILITY = 0.65         # Augmenté de 0.60 à 0.65
    GOLDEN_RULE_STRICT = True             # Règle rouge sous verte
    
    # 🌍 AJUSTEMENTS PAR SESSION (Ancien système)
    SESSION_RISK_MULTIPLIERS = {
        'asian': 0.4,      # Réduit de 0.5 à 0.4
        'london': 0.8,     # Réduit de 1.0 à 0.8
        'ny_am': 1.0,      # Réduit de 1.2 à 1.0
        'ny_pm': 0.6,      # Réduit de 0.8 à 0.6
        'close': 0.3       # Réduit de 0.5 à 0.3
    }
    
    # ⚡ VOLATILITÉ
    HIGH_VOLATILITY_THRESHOLD = 25.0      # Réduit de 30 à 25
    REDUCE_SIZE_HIGH_VOL = True
    
    # ===== PERFORMANCE TRACKER AVANCÉ (Ancien système) =====
    
    # 📊 MÉTRIQUES DÉTAILLÉES
    TRACK_PROFIT_FACTOR = True
    TRACK_TRADING_DURATION = True
    TRACK_ML_APPROVAL_RATE = True
    TRACK_GAMMA_OPTIMIZED = True
    
    # 📈 STATISTIQUES ORDERFLOW
    TRACK_VOLUME_PROFILE = True
    TRACK_DELTA_PROFILE = True
    TRACK_FOOTPRINT_PATTERNS = True
    TRACK_LEVEL2_ANALYSIS = True
    
    # ===== STRATÉGIES AVANCÉES (Ancien système) =====
    
    # 🧠 TECHNIQUES ELITE
    BATTLE_NAVALE_ENABLED = True
    BATTLE_NAVALE_LONG_THRESHOLD = 0.25
    BATTLE_NAVALE_SHORT_THRESHOLD = -0.25
    
    # 📊 MTF CONFLUENCE ELITE
    MTF_ELITE_ENABLED = True
    MIN_MTF_ELITE_SCORE = 0.70
    MIN_MTF_STANDARD_SCORE = 0.55
    
    # 💰 SMART MONEY TRACKER
    SMART_MONEY_ENABLED = True
    MIN_SMART_MONEY_CONFIDENCE = 0.65
    MIN_SMART_MONEY_INSTITUTIONAL = 0.75
    SMART_MONEY_ALIGNMENT_BONUS = 0.15
    
    # 🤖 ML ENSEMBLE FILTER
    ML_ENSEMBLE_ENABLED = True
    MIN_ML_ENSEMBLE_CONFIDENCE = 0.60
    ML_ENSEMBLE_BOOST_FACTOR = 1.2
    ML_ENSEMBLE_POSITION_BONUS = 0.1
    
    # 📈 GAMMA CYCLES
    GAMMA_CYCLES_ENABLED = True
    GAMMA_EXPIRY_WEEK_FACTOR = 1.3
    GAMMA_PEAK_FACTOR = 1.5
    GAMMA_MODERATE_FACTOR = 1.1
    
    # ===== CONFIGURATION INTELLIGENTE (Ancien système) =====
    
    # 🎯 SEUILS ADAPTATIFS
    CONFLUENCE_ADAPTIVE = True
    MIN_SIGNAL_CONFIDENCE = 0.45          # Réduit pour plus de trades
    CONFLUENCE_THRESHOLD = 0.15           # Réduit pour plus de trades
    
    # 🎭 SIMULATION POUR PAPER TRADING
    SIMULATE_VOLUME = True
    SIMULATED_VOLUME_RANGE = (100, 1000)
    SIMULATED_DELTA_RANGE = (0.1, 0.8)
    
    # 🔗 CONNEXION IBKR OPTIMISÉE
    IBKR_HOST = "127.0.0.1"
    IBKR_PORT = 7497  # TWS Paper Trading
    CONNECTION_TIMEOUT = 60
    HEARTBEAT_INTERVAL = 15
    
    # ===== MONITORING DÉTAILLÉ (Ancien système) =====
    
    # 📊 STATISTIQUES TEMPS RÉEL
    PERFORMANCE_UPDATE_INTERVAL = 30
    HEALTH_CHECK_INTERVAL = 15
    
    # 📈 MÉTRIQUES ORDERFLOW
    TRACK_TOTAL_VOLUME = True
    TRACK_DELTA_MOYEN = True
    TRACK_PATTERNS_DETECTES = True
    TRACK_VOLUME_PROFILE_POINTS = True
    TRACK_DELTA_PROFILE_POINTS = True
    
    # 🎭 MODE DE TEST
    DRY_RUN_MODE = True                   # Simulation uniquement
    DATA_COLLECTION_MODE = False          # ❌ DÉSACTIVÉ - Mode strict
    
    def __str__(self):
        return f"""
🎯 CONFIGURATION HYBRIDE COMPLÈTE - CORRECTIONS + SOLIDITÉ
├── ✅ CORRECTIONS TECHNIQUES GARDÉES:
│   ├── VWAP Bands: Fonctionnel
│   ├── Volume ES: Affichage corrigé
│   ├── OrderFlow: Seuils optimisés
│   └── SPX Retriever: Status correct
├── 🛡️ SOLIDITÉ RISK MANAGEMENT AJOUTÉE:
│   ├── Limites: {self.DAILY_LOSS_LIMIT}$/jour, {self.MAX_DAILY_TRADES} trades
│   ├── Positions: {self.BASE_POSITION_SIZE} base, {self.MAX_POSITION_SIZE} max
│   ├── Risque: {self.RISK_PER_TRADE_PERCENT}% capital, {self.MAX_RISK_PER_TRADE_DOLLARS}$ max
│   └── Qualité: {self.MIN_CONFLUENCE_SCORE*100}% confluence, {self.MIN_SIGNAL_PROBABILITY*100}% probabilité
├── 📊 PERFORMANCE TRACKER AVANCÉ:
│   ├── Profit Factor: {self.TRACK_PROFIT_FACTOR}
│   ├── ML Approval Rate: {self.TRACK_ML_APPROVAL_RATE}
│   ├── Gamma Optimized: {self.TRACK_GAMMA_OPTIMIZED}
│   └── Volume Profile: {self.TRACK_VOLUME_PROFILE}
├── 🧠 STRATÉGIES AVANCÉES:
│   ├── Battle Navale: {self.BATTLE_NAVALE_ENABLED}
│   ├── MTF Elite: {self.MTF_ELITE_ENABLED}
│   ├── Smart Money: {self.SMART_MONEY_ENABLED}
│   ├── ML Ensemble: {self.ML_ENSEMBLE_ENABLED}
│   └── Gamma Cycles: {self.GAMMA_CYCLES_ENABLED}
└── 🎭 Mode: {'DRY RUN' if self.DRY_RUN_MODE else 'LIVE'} - {'STRICT' if not self.DATA_COLLECTION_MODE else 'PERMISSIF'}
        """

# Instance globale
HYBRID_CONFIG = HybridTradingConfig()
