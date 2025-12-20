# ==============================================================================
# ECONOMIC CALENDAR MODULE - Intégration Trading Bot (INVESTPY)
# ==============================================================================
#
# Ce module permet de:
# - Récupérer les événements économiques via Investing.com (100% GRATUIT)
# - Bloquer les trades pendant les événements ⭐⭐⭐ (3 étoiles) SEULEMENT
# - Cache intelligent pour minimiser les requêtes
# - Système d'impact basé sur Investing.com
#
# NIVEAUX D'IMPACT (BASÉ INVESTING.COM):
# ┌──────────┬─────────┬───────────────────────────────────────────────┐
# │ NIVEAU   │ ETOILES │ COMPORTEMENT BOT                              │
# ├──────────┼─────────┼───────────────────────────────────────────────┤
# │ CRITICAL │ ⭐⭐⭐  │ BLOQUER: -15min / +30min (FOMC, NFP, CPI)     │
# │ HIGH     │ ⭐⭐    │ TRADING NORMAL (Fed speech, GDP, ISM)         │
# │ MEDIUM   │ ⭐      │ TRADING NORMAL (Jobless, Trade Balance)       │
# │ LOW      │ (rien)  │ IGNORÉ                                        │
# └──────────┴─────────┴───────────────────────────────────────────────┘
#
# INSTALLATION:
# pip install investpy
#
# ==============================================================================

import sys
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

# Fix encodage Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

logger = logging.getLogger(__name__)

# Importer investpy
try:
    import investpy
    INVESTPY_AVAILABLE = True
except ImportError:
    INVESTPY_AVAILABLE = False
    logger.warning("⚠️ investpy non disponible - pip install investpy")


# ==============================================================================
# CONFIGURATION DES NIVEAUX D'IMPACT
# ==============================================================================

class EventImpact(Enum):
    """
    Niveau d'impact des événements économiques (basé Investing.com)
    """
    LOW = 1       # 🟢 Ignoré
    MEDIUM = 2    # 🟡 Trading normal
    HIGH = 3      # 🟠 Trading normal
    CRITICAL = 4  # 🔴 ⭐⭐⭐ BLOQUER


# Configuration du comportement par niveau d'impact
IMPACT_CONFIG = {
    EventImpact.CRITICAL: {  # ⭐⭐⭐ SEULEMENT
        'emoji': '🔴',
        'label': 'CRITICAL',
        'minutes_before': 15,   # Arrêter 15 min AVANT
        'minutes_after': 30,    # Reprendre 30 min APRÈS
        'block_trading': True,  # ✅ BLOQUER
        'examples': ['FOMC Decision', 'NFP', 'CPI', 'Fed Chair Powell']
    },
    EventImpact.HIGH: {  # ⭐⭐ - NE PAS BLOQUER
        'emoji': '🟠',
        'label': 'HIGH',
        'minutes_before': 0,
        'minutes_after': 0,
        'block_trading': False,  # ✅ TRADING NORMAL
        'examples': ['Fed Speech', 'GDP', 'ISM', 'Retail Sales', 'PPI']
    },
    EventImpact.MEDIUM: {  # ⭐ - NE PAS BLOQUER
        'emoji': '🟡',
        'label': 'MEDIUM',
        'minutes_before': 0,
        'minutes_after': 0,
        'block_trading': False,  # ✅ TRADING NORMAL
        'examples': ['Jobless Claims', 'Trade Balance', 'Empire State']
    },
    EventImpact.LOW: {
        'emoji': '🟢',
        'label': 'LOW',
        'minutes_before': 0,
        'minutes_after': 0,
        'block_trading': False,
        'examples': ['Treasury Auction', 'Minor Reports']
    }
}


@dataclass
class EconomicEvent:
    """Structure d'un événement économique avec impact détaillé"""
    name: str
    country: str
    currency: str
    time: datetime
    impact: EventImpact
    actual: Optional[str] = None
    forecast: Optional[str] = None
    previous: Optional[str] = None

    @property
    def impact_score(self) -> int:
        """Retourne le score numérique (1-4)"""
        return self.impact.value

    @property
    def impact_emoji(self) -> str:
        """Retourne l'emoji du niveau"""
        return IMPACT_CONFIG[self.impact]['emoji']

    @property
    def impact_label(self) -> str:
        """Retourne le label (CRITICAL, HIGH, etc.)"""
        return IMPACT_CONFIG[self.impact]['label']

    @property
    def minutes_before(self) -> int:
        """Minutes à bloquer AVANT l'event"""
        return IMPACT_CONFIG[self.impact]['minutes_before']

    @property
    def minutes_after(self) -> int:
        """Minutes à bloquer APRÈS l'event"""
        return IMPACT_CONFIG[self.impact]['minutes_after']

    def __str__(self) -> str:
        if self.minutes_before > 0 or self.minutes_after > 0:
            return (f"{self.impact_emoji} [{self.impact_label}] {self.name} "
                    f"@ {self.time.strftime('%H:%M')} "
                    f"(bloc: -{self.minutes_before}min / +{self.minutes_after}min)")
        else:
            return (f"{self.impact_emoji} [{self.impact_label}] {self.name} "
                    f"@ {self.time.strftime('%H:%M')} (trading normal)")


# ==============================================================================
# CLASSE PRINCIPALE
# ==============================================================================

class EconomicCalendar:
    """
    Calendrier économique avec système d'impact intelligent (investpy).

    Fonctionnement:
    - Fetch au démarrage + refresh toutes les 2h
    - Check du cache à chaque tick (0 latence)
    - Bloque trades SEULEMENT pour events ⭐⭐⭐ (3 étoiles)
    - Logs détaillés avec emoji et timing
    """

    def __init__(
        self,
        refresh_interval_hours: float = 2.0,
        block_medium_impact: bool = False,
        custom_impact_config: Dict = None
    ):
        """
        Initialise le calendrier économique.

        Args:
            refresh_interval_hours: Intervalle de refresh du cache (défaut: 2h)
            block_medium_impact: Bloquer aussi les events MEDIUM (défaut: False)
            custom_impact_config: Override la config d'impact par défaut
        """
        if not INVESTPY_AVAILABLE:
            logger.error("❌ investpy non installé - pip install investpy")
            self.available = False
            return

        self.available = True

        # Configuration timing
        self.refresh_interval = timedelta(hours=refresh_interval_hours)
        self.block_medium = block_medium_impact

        # Config d'impact (peut être personnalisée)
        self.impact_config = custom_impact_config or IMPACT_CONFIG

        # Cache
        self.cached_events: List[EconomicEvent] = []
        self.last_fetch: Optional[datetime] = None
        self.fetch_error_count = 0

        # Stats
        self.stats = {
            'total_api_calls': 0,
            'cache_hits': 0,
            'trades_blocked': 0,
            'trades_blocked_by_level': {
                'CRITICAL': 0,
                'HIGH': 0,
                'MEDIUM': 0
            },
            'events_today': 0
        }

        # Premier fetch au démarrage
        self._initial_fetch()

    def _initial_fetch(self):
        """Fetch initial au démarrage du bot"""
        logger.info("📅 ══════════════════════════════════════════════════")
        logger.info("📅 INITIALISATION CALENDRIER ÉCONOMIQUE (INVESTPY)")
        logger.info("📅 ══════════════════════════════════════════════════")

        success = self.fetch_events()

        if success:
            # Compter par niveau
            today = datetime.now().date()
            today_events = [e for e in self.cached_events if e.time.date() == today]

            critical = sum(1 for e in today_events if e.impact == EventImpact.CRITICAL)
            high = sum(1 for e in today_events if e.impact == EventImpact.HIGH)
            medium = sum(1 for e in today_events if e.impact == EventImpact.MEDIUM)

            logger.info(f"✅ Calendrier chargé: {len(self.cached_events)} events total")
            logger.info(f"📊 AUJOURD'HUI: {len(today_events)} events")
            logger.info(f"   🔴 CRITICAL (⭐⭐⭐): {critical} → BLOQUER")
            logger.info(f"   🟠 HIGH (⭐⭐): {high} → Trading normal")
            logger.info(f"   🟡 MEDIUM (⭐): {medium} → Trading normal")

            # Afficher les events critiques d'aujourd'hui
            critical_events = [e for e in today_events if e.impact == EventImpact.CRITICAL]
            if critical_events:
                logger.info("🔴 EVENTS CRITIQUES À BLOQUER:")
                for event in sorted(critical_events, key=lambda x: x.time):
                    logger.info(f"   {event}")
        else:
            logger.warning("⚠️ Impossible de charger le calendrier - "
                          "Le bot fonctionnera sans filtre économique")

        logger.info("📅 ══════════════════════════════════════════════════")

    def fetch_events(self) -> bool:
        """
        Récupère les événements économiques depuis Investing.com.
        Appelé automatiquement toutes les X heures.

        Returns:
            bool: True si succès, False si erreur
        """
        if not self.available:
            return False

        try:
            # Période: aujourd'hui + 7 jours
            today = datetime.now()
            end_date = today + timedelta(days=7)

            logger.debug(f"📅 Fetch investpy: {today.strftime('%d/%m/%Y')} → {end_date.strftime('%d/%m/%Y')}")

            # Récupérer calendrier économique US
            calendar_df = investpy.economic_calendar(
                countries=['united states'],
                from_date=today.strftime('%d/%m/%Y'),
                to_date=end_date.strftime('%d/%m/%Y')
            )

            self.stats['total_api_calls'] += 1

            # Parser les events
            self.cached_events = self._parse_events(calendar_df)
            self.last_fetch = datetime.now()
            self.fetch_error_count = 0

            logger.debug(f"📅 investpy: {len(self.cached_events)} events chargés")
            return True

        except Exception as e:
            logger.error(f"❌ Erreur calendrier économique (investpy): {e}")
            self.fetch_error_count += 1
            return False

    def _parse_events(self, calendar_df) -> List[EconomicEvent]:
        """Parse les événements bruts en objets EconomicEvent"""
        parsed = []

        for idx, row in calendar_df.iterrows():
            try:
                # Parser le temps (investpy format: DD/MM/YYYY + HH:MM)
                date_str = row['date']  # "01/12/2025"
                time_str = row['time']  # "15:45"

                # Combiner date + time
                datetime_str = f"{date_str} {time_str}"
                # ✅ FIX 10/12/2025: investpy retourne DÉJÀ les heures en heure LOCALE Paris
                # PAS de conversion timezone nécessaire!
                # Bug précédent: +6h décalait tous les events (FOMC 20:00 → 02:00 lendemain)
                event_time = datetime.strptime(datetime_str, '%d/%m/%Y %H:%M')
                # PAS de modification de timezone - investpy est déjà en heure locale

                # Déterminer l'impact depuis Investing.com
                importance = row['importance']  # 'high', 'medium', 'low'
                impact = self._determine_impact_from_investing(importance)

                # Ne garder que les events medium+ (ignorer low impact)
                if impact == EventImpact.LOW:
                    continue

                parsed.append(EconomicEvent(
                    name=row['event'],
                    country='US',
                    currency=row.get('currency', 'USD'),
                    time=event_time,
                    impact=impact,
                    actual=row.get('actual'),
                    forecast=row.get('forecast'),
                    previous=row.get('previous')
                ))

            except Exception as e:
                logger.debug(f"Erreur parsing event: {e}")
                continue

        # Trier par date
        parsed.sort(key=lambda x: x.time)
        return parsed

    def _determine_impact_from_investing(self, importance: str) -> EventImpact:
        """
        Convertit l'importance Investing.com en notre système.

        Investing.com utilise: 'high' (⭐⭐⭐), 'medium' (⭐⭐), 'low' (⭐)
        On bloque SEULEMENT 'high' (⭐⭐⭐)
        """
        importance_lower = importance.lower()

        if importance_lower == 'high':
            return EventImpact.CRITICAL  # 🔴 BLOQUER (⭐⭐⭐)
        elif importance_lower == 'medium':
            return EventImpact.HIGH       # 🟠 Trading normal (⭐⭐)
        elif importance_lower == 'low':
            return EventImpact.MEDIUM     # 🟡 Trading normal (⭐)
        else:
            return EventImpact.LOW        # 🟢 Ignoré

    def _should_refresh(self) -> bool:
        """Vérifie si le cache doit être rafraîchi"""
        if self.last_fetch is None:
            return True
        return datetime.now() - self.last_fetch > self.refresh_interval

    # ==========================================================================
    # MÉTHODES PRINCIPALES À UTILISER DANS TON BOT
    # ==========================================================================

    def check_and_refresh(self) -> None:
        """
        À appeler dans run_cycle() - Rafraîchit le cache si nécessaire.
        Coût: quasi-nul (simple check datetime)
        """
        if not self.available:
            return

        if self._should_refresh():
            self.fetch_events()

    def is_trading_blocked(self) -> Tuple[bool, Optional[EconomicEvent], str]:
        """
        Vérifie si le trading doit être bloqué à cause d'un événement.

        À appeler AVANT chaque trade.
        Coût: O(n) sur le cache, ~0.01ms

        Returns:
            Tuple[bool, Optional[EconomicEvent], str]:
                - (True, event, reason) si bloqué
                - (False, None, "") si OK pour trader
        """
        if not self.available:
            return False, None, ""

        self.stats['cache_hits'] += 1
        now = datetime.now()

        for event in self.cached_events:
            # Récupérer les temps de blocage SELON LE NIVEAU D'IMPACT
            minutes_before = event.minutes_before
            minutes_after = event.minutes_after

            # Si pas de blocage configuré, skip
            if minutes_before == 0 and minutes_after == 0:
                continue

            # Calculer la fenêtre de blocage
            window_start = event.time - timedelta(minutes=minutes_before)
            window_end = event.time + timedelta(minutes=minutes_after)

            # Vérifier si on est dans la fenêtre
            if window_start <= now <= window_end:

                # 🔴 CRITICAL (⭐⭐⭐) - TOUJOURS bloqué
                if event.impact == EventImpact.CRITICAL:
                    self.stats['trades_blocked'] += 1
                    self.stats['trades_blocked_by_level']['CRITICAL'] += 1

                    # Calculer temps restant
                    if now < event.time:
                        time_info = f"dans {int((event.time - now).seconds / 60)} min"
                    else:
                        time_left = int((window_end - now).seconds / 60)
                        time_info = f"reprend dans {time_left} min"

                    reason = (f"🔴 STOP TOTAL (⭐⭐⭐) - {event.name} @ {event.time.strftime('%H:%M')} "
                             f"({time_info})")
                    return True, event, reason

        return False, None, ""

    def get_next_event(self, min_impact: EventImpact = EventImpact.HIGH) -> Optional[EconomicEvent]:
        """Retourne le prochain événement avec impact minimum spécifié"""
        if not self.available:
            return None

        now = datetime.now()
        for event in self.cached_events:
            if event.time > now and event.impact.value >= min_impact.value:
                return event
        return None

    def get_events_today(self, min_impact: EventImpact = EventImpact.MEDIUM) -> List[EconomicEvent]:
        """Retourne tous les événements d'aujourd'hui avec impact minimum"""
        if not self.available:
            return []

        today = datetime.now().date()
        return [e for e in self.cached_events
                if e.time.date() == today and e.impact.value >= min_impact.value]

    def get_stats(self) -> Dict:
        """Retourne les statistiques d'utilisation"""
        if not self.available:
            return {}

        today = datetime.now().date()
        today_events = [e for e in self.cached_events if e.time.date() == today]

        return {
            **self.stats,
            'cached_events': len(self.cached_events),
            'last_fetch': self.last_fetch.isoformat() if self.last_fetch else None,
            'events_today': {
                'total': len(today_events),
                'critical': sum(1 for e in today_events if e.impact == EventImpact.CRITICAL),
                'high': sum(1 for e in today_events if e.impact == EventImpact.HIGH),
                'medium': sum(1 for e in today_events if e.impact == EventImpact.MEDIUM),
            }
        }

    def print_daily_schedule(self):
        """Affiche le planning des events du jour dans les logs"""
        if not self.available:
            return

        today_events = self.get_events_today(EventImpact.MEDIUM)

        if not today_events:
            logger.info("📅 Aucun event économique majeur aujourd'hui")
            return

        logger.info("📅 ═══════════════════════════════════════════")
        logger.info("📅 PLANNING ÉCONOMIQUE DU JOUR")
        logger.info("📅 ═══════════════════════════════════════════")

        for event in sorted(today_events, key=lambda x: x.time):
            if event.minutes_before > 0 or event.minutes_after > 0:
                block_start = event.time - timedelta(minutes=event.minutes_before)
                block_end = event.time + timedelta(minutes=event.minutes_after)
                logger.info(f"   {event.impact_emoji} {event.time.strftime('%H:%M')} - {event.name}")
                logger.info(f"      └─ Bloc: {block_start.strftime('%H:%M')} → {block_end.strftime('%H:%M')}")
            else:
                logger.info(f"   {event.impact_emoji} {event.time.strftime('%H:%M')} - {event.name} (trading normal)")

        logger.info("📅 ═══════════════════════════════════════════")


# ==============================================================================
# TEST LOCAL
# ==============================================================================

if __name__ == "__main__":
    # Configuration logging pour test
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(message)s'
    )

    print("=" * 70)
    print("TEST CALENDRIER ÉCONOMIQUE - INVESTPY")
    print("=" * 70)

    # Initialiser le calendrier
    calendar = EconomicCalendar()

    if calendar.available:
        # Afficher planning du jour
        calendar.print_daily_schedule()

        # Test blocage
        is_blocked, event, reason = calendar.is_trading_blocked()
        print(f"\n🚦 TRADING STATUS:")
        if is_blocked:
            print(f"   ❌ BLOQUÉ")
            print(f"   Raison: {reason}")
        else:
            print(f"   ✅ AUTORISÉ")

        # Stats
        stats = calendar.get_stats()
        print(f"\n📈 STATISTIQUES:")
        print(f"   Events en cache: {stats['cached_events']}")
        print(f"   Events aujourd'hui: {stats['events_today']}")
    else:
        print("❌ investpy non disponible")

    print("\n" + "=" * 70)

class TradingBot:
    def __init__(self):
        # ... ton code existant ...

        # Initialiser le calendrier économique
        self.calendar = EconomicCalendar(
            api_key="d4j49s1r01queualep5g",  # Ta clé Finnhub
            refresh_interval_hours=2.0,       # Refresh toutes les 2h
            block_medium_impact=False         # Ignorer events MEDIUM
        )

        # Afficher le planning du jour au démarrage
        self.calendar.print_daily_schedule()

    async def run_cycle(self, symbol):
        '''Cycle principal'''

        # 1. Refresh cache si nécessaire (quasi gratuit)
        self.calendar.check_and_refresh()

        # 2. Vérifier si trading bloqué (avec raison détaillée)
        is_blocked, event, reason = self.calendar.is_trading_blocked()

        if is_blocked:
            # Log avec emoji et détails
            logger.warning(f"⚠️ TRADING PAUSE - {reason}")
            return None  # Skip ce cycle

        # 3. Optionnel: ajuster taille position si event proche
        size_multiplier = self.calendar.get_position_size_multiplier()
        if size_multiplier < 1.0:
            logger.info(f"📉 Taille réduite à {size_multiplier*100:.0f}% (event proche)")

        # 4. Ton code normal de trading
        tick = await self.get_tick_data(symbol)
        signal = await self.process_signal(tick)

        if signal:
            # Ajuster la taille
            signal.size = int(signal.size * size_multiplier)
            await self.execute_trade(signal)

        return signal

    def log_daily_summary(self):
        '''Log résumé en fin de journée'''
        stats = self.calendar.get_stats()
        logger.info("📅 ═══════════════════════════════════════════")
        logger.info("📅 RÉSUMÉ CALENDRIER ÉCONOMIQUE")
        logger.info(f"   API calls: {stats['total_api_calls']}")
        logger.info(f"   Trades bloqués: {stats['trades_blocked']}")
        logger.info(f"     - CRITICAL: {stats['trades_blocked_by_level']['CRITICAL']}")
        logger.info(f"     - HIGH: {stats['trades_blocked_by_level']['HIGH']}")
        logger.info(f"     - MEDIUM: {stats['trades_blocked_by_level']['MEDIUM']}")
        logger.info("📅 ═══════════════════════════════════════════")


# ==============================================================================
# TEST LOCAL
# ==============================================================================

if __name__ == "__main__":
    # Configuration logging pour test
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(message)s'
    )

    print("=" * 70)
    print("TEST CALENDRIER ÉCONOMIQUE - SYSTÈME D'IMPACT INTELLIGENT")
    print("=" * 70)

    # ✅ Clé API Finnhub configurée
    API_KEY = "d4j49s1r01queualep5g"

    print(f"\n✅ Clé API configurée: {API_KEY[:10]}...")

    # Afficher la configuration des niveaux d'impact
    print("\n📊 CONFIGURATION DES NIVEAUX D'IMPACT:")
    print("┌──────────┬─────────┬────────────────────────────────────────┐")
    print("│ NIVEAU   │ TIMING  │ EXEMPLES                               │")
    print("├──────────┼─────────┼────────────────────────────────────────┤")
    for impact, config in IMPACT_CONFIG.items():
        timing = f"-{config['minutes_before']}min / +{config['minutes_after']}min"
        examples = ", ".join(config['examples'][:2])
        print(f"│ {config['emoji']} {config['label']:8} │ {timing:7} │ {examples[:38]:38} │")
    print("└──────────┴─────────┴────────────────────────────────────────┘")

    # Initialiser le calendrier
    calendar = EconomicCalendar(api_key=API_KEY)

    # Afficher statut actuel
    print(f"\n📊 STATUT ACTUEL: {calendar.get_status_summary()}")

    # Events aujourd'hui
    today_events = calendar.get_events_today(EventImpact.MEDIUM)
    if today_events:
        print(f"\n📅 EVENTS AUJOURD'HUI ({len(today_events)}):")
        for event in sorted(today_events, key=lambda x: x.time):
            print(f"   {event}")
    else:
        print("\n✅ Aucun event économique majeur aujourd'hui")

    # Prochain event
    next_event = calendar.get_next_event()
    if next_event:
        time_until = calendar.time_until_next_event()
        print(f"\n⏰ PROCHAIN EVENT:")
        print(f"   {next_event}")
        print(f"   Dans: {time_until}")

    # Test blocage
    is_blocked, event, reason = calendar.is_trading_blocked()
    print(f"\n🚦 TRADING STATUS:")
    if is_blocked:
        print(f"   ❌ BLOQUÉ")
        print(f"   Raison: {reason}")
    else:
        print(f"   ✅ AUTORISÉ")
        print(f"   Multiplicateur taille: {calendar.get_position_size_multiplier():.0%}")

    # Stats
    stats = calendar.get_stats()
    print(f"\n📈 STATISTIQUES:")
    print(f"   Events en cache: {stats['cached_events']}")
    print(f"   Events aujourd'hui: {stats['events_today']}")
    print(f"   Trades bloqués: {stats['trades_blocked']}")

    print("\n" + "=" * 70)
    print("FIN DU TEST")
    print("=" * 70)
