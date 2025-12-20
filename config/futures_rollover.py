"""
═══════════════════════════════════════════════════════════════════════════════
                    GESTION AUTOMATIQUE DES ROLLOVERS FUTURES
═══════════════════════════════════════════════════════════════════════════════

🎯 SOLUTION DÉFINITIVE - AUCUNE MISE À JOUR MANUELLE NÉCESSAIRE!

Ce fichier calcule AUTOMATIQUEMENT le bon contrat basé sur la date actuelle.
Plus jamais de bug de rollover!

CALENDRIER DES ROLLOVERS (2ème jeudi du mois d'expiration):
    - Mars (H)      → Rollover ~11 Mars      → Vers Juin (M)
    - Juin (M)      → Rollover ~11 Juin      → Vers Septembre (U)
    - Septembre (U) → Rollover ~11 Septembre → Vers Décembre (Z)
    - Décembre (Z)  → Rollover ~11 Décembre  → Vers Mars (H) année suivante

CODES DES MOIS:
    H = Mars, M = Juin, U = Septembre, Z = Décembre

UTILISATION:
    from config.futures_rollover import get_active_contract, get_sierra_symbol

    # Obtenir le symbole actif
    contract = get_active_contract("ES")  # → "ESH26" (automatique!)

    # Obtenir le symbole Sierra Chart complet
    sc_symbol = get_sierra_symbol("ES")   # → "ESH26-CME"

═══════════════════════════════════════════════════════════════════════════════
"""

from datetime import datetime, date, timedelta
from typing import Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
#                           CONFIGURATION STATIQUE
# ═══════════════════════════════════════════════════════════════════════════════

# Codes des mois futures (trimestres)
MONTH_CODES = {
    3: 'H',   # Mars
    6: 'M',   # Juin
    9: 'U',   # Septembre
    12: 'Z',  # Décembre
}

# Code → Mois numérique
CODE_TO_MONTH = {
    'H': 3,   # Mars
    'M': 6,   # Juin
    'U': 9,   # Septembre
    'Z': 12,  # Décembre
}

# Séquence des mois futures
MONTH_SEQUENCE = ['H', 'M', 'U', 'Z']  # Mars, Juin, Sept, Déc

# Jour typique du rollover (2ème jeudi = généralement entre 8 et 14)
ROLLOVER_DAY = 11  # Approximation sûre

# Symboles de base supportés
SUPPORTED_SYMBOLS = ['ES', 'NQ', 'RTY', 'MES', 'MNQ']

# ═══════════════════════════════════════════════════════════════════════════════
#                    🎯 FONCTION PRINCIPALE - 100% AUTOMATIQUE
# ═══════════════════════════════════════════════════════════════════════════════

def _calculate_active_contract_auto() -> Tuple[str, int]:
    """
    Calcule AUTOMATIQUEMENT le mois et l'année du contrat actif.

    LOGIQUE:
    - Trouve le prochain mois d'expiration (H, M, U, Z)
    - Si on est APRÈS le jour de rollover, passe au trimestre suivant
    - Calcule l'année correcte (gère le passage Z → H nouvelle année)

    Returns:
        (code_mois, année) ex: ('H', 26) pour Mars 2026
    """
    today = date.today()
    current_month = today.month
    current_day = today.day
    current_year = today.year % 100  # 2025 → 25, 2026 → 26

    # Trouver le trimestre actuel et le suivant
    # Les mois d'expiration: 3 (Mars), 6 (Juin), 9 (Sept), 12 (Déc)
    expiry_months = [3, 6, 9, 12]

    # Trouver le prochain mois d'expiration
    next_expiry_month = None
    for exp_month in expiry_months:
        if current_month < exp_month:
            next_expiry_month = exp_month
            break
        elif current_month == exp_month:
            # On est dans le mois d'expiration
            if current_day < ROLLOVER_DAY:
                # Avant le rollover → contrat actuel
                next_expiry_month = exp_month
            else:
                # Après le rollover → contrat suivant
                idx = expiry_months.index(exp_month)
                if idx == 3:  # Décembre → Mars année suivante
                    next_expiry_month = 3
                    current_year += 1
                else:
                    next_expiry_month = expiry_months[idx + 1]
            break

    # Si on a passé décembre, le prochain est mars de l'année suivante
    if next_expiry_month is None:
        next_expiry_month = 3
        current_year += 1

    month_code = MONTH_CODES[next_expiry_month]
    return (month_code, current_year)


def get_active_contract(symbol: str) -> str:
    """
    🎯 Retourne le symbole complet du contrat actif - 100% AUTOMATIQUE!

    Args:
        symbol: 'ES', 'NQ', 'RTY', 'MES', 'MNQ'

    Returns:
        Symbole complet (ex: 'ESH26' pour Mars 2026)

    Example:
        >>> get_active_contract("ES")
        'ESH26'  # Si on est après le rollover de décembre 2025
    """
    month_code, year = _calculate_active_contract_auto()
    base = symbol.upper()

    # Normaliser le symbole de base
    if base.startswith('M'):
        # Micro futures: MES, MNQ
        return f"{base}{month_code}{year}"
    else:
        # Standard: ES, NQ, RTY
        return f"{base}{month_code}{year}"


def get_sierra_symbol(symbol: str) -> str:
    """
    🎯 Retourne le symbole Sierra Chart complet - 100% AUTOMATIQUE!

    Args:
        symbol: 'ES', 'NQ', 'RTY'

    Returns:
        Symbole Sierra (ex: 'ESH26-CME')

    Example:
        >>> get_sierra_symbol("ES")
        'ESH26-CME'
    """
    contract = get_active_contract(symbol)
    return f"{contract}-CME"


def get_active_month_code() -> str:
    """Retourne le code du mois actif (H, M, U, Z) - AUTOMATIQUE."""
    month_code, _ = _calculate_active_contract_auto()
    return month_code


def get_active_year() -> int:
    """Retourne l'année du contrat actif (25, 26, etc.) - AUTOMATIQUE."""
    _, year = _calculate_active_contract_auto()
    return year


# ═══════════════════════════════════════════════════════════════════════════════
#                           COMPATIBILITÉ LEGACY
# ═══════════════════════════════════════════════════════════════════════════════

# Ces variables sont maintenant calculées automatiquement!
# Gardées pour compatibilité avec l'ancien code

@property
def _legacy_active_contracts():
    """Génère automatiquement ACTIVE_CONTRACTS."""
    return {
        'ES': get_active_contract('ES'),
        'NQ': get_active_contract('NQ'),
        'RTY': get_active_contract('RTY'),
    }

# Variables legacy (pour compatibilité)
def get_legacy_active_contracts() -> Dict[str, str]:
    """Retourne le dict ACTIVE_CONTRACTS (calculé automatiquement)."""
    return {
        'ES': get_active_contract('ES'),
        'NQ': get_active_contract('NQ'),
        'RTY': get_active_contract('RTY'),
    }

ACTIVE_CONTRACTS = get_legacy_active_contracts()
ACTIVE_YEAR = get_active_year()


# ═══════════════════════════════════════════════════════════════════════════════
#                           FONCTIONS UTILITAIRES
# ═══════════════════════════════════════════════════════════════════════════════

def get_contract_expiry_month() -> Tuple[int, int]:
    """
    Retourne le mois et l'année d'expiration du contrat actif.

    Returns:
        (mois, année) ex: (3, 2026) pour Mars 2026
    """
    month_code, year = _calculate_active_contract_auto()
    month = CODE_TO_MONTH[month_code]
    return (month, 2000 + year)


def get_next_rollover_date() -> Optional[date]:
    """
    Retourne la prochaine date de rollover (approximative).

    Returns:
        date du prochain rollover
    """
    today = date.today()
    month_code, year = _calculate_active_contract_auto()
    expiry_month = CODE_TO_MONTH[month_code]
    expiry_year = 2000 + year

    # Le rollover est environ le 11 du mois d'expiration
    rollover_date = date(expiry_year, expiry_month, ROLLOVER_DAY)

    # Si cette date est passée, calculer le prochain trimestre
    if rollover_date <= today:
        idx = MONTH_SEQUENCE.index(month_code)
        if idx == 3:  # Z → H (nouvelle année)
            next_month_code = 'H'
            next_year = expiry_year + 1
        else:
            next_month_code = MONTH_SEQUENCE[idx + 1]
            next_year = expiry_year

        next_expiry_month = CODE_TO_MONTH[next_month_code]
        rollover_date = date(next_year, next_expiry_month, ROLLOVER_DAY)

    return rollover_date


def days_until_rollover() -> int:
    """Retourne le nombre de jours avant le prochain rollover."""
    next_date = get_next_rollover_date()
    if next_date:
        return (next_date - date.today()).days
    return 999


def check_rollover_warning() -> Optional[str]:
    """
    Vérifie si un rollover approche et retourne un message d'alerte.

    Returns:
        Message d'alerte si rollover < 7 jours, None sinon
    """
    days = days_until_rollover()

    if days <= 0:
        return f"🔄 ROLLOVER EN COURS - Contrats mis à jour automatiquement"
    elif days <= 3:
        return f"⚠️ ROLLOVER dans {days} jours - Vérifier liquidité des nouveaux contrats"
    elif days <= 7:
        return f"📅 Rollover prévu dans {days} jours"

    return None


def get_rollover_status() -> Dict:
    """
    Retourne un status complet du rollover.

    Returns:
        Dict avec toutes les infos rollover
    """
    next_rollover = get_next_rollover_date()
    days = days_until_rollover()

    return {
        'active_contracts': get_legacy_active_contracts(),
        'active_month': get_active_month_code(),
        'active_year': get_active_year(),
        'expiry_month_year': get_contract_expiry_month(),
        'next_rollover_date': next_rollover.isoformat() if next_rollover else None,
        'days_until_rollover': days,
        'warning': check_rollover_warning(),
        'auto_mode': True,  # 🎯 Toujours automatique maintenant!
    }


def log_rollover_status():
    """Log le status du rollover au démarrage du bot."""
    status = get_rollover_status()

    logger.info("="*60)
    logger.info("📊 STATUS CONTRATS FUTURES (MODE AUTOMATIQUE)")
    logger.info("="*60)

    for symbol, contract in status['active_contracts'].items():
        logger.info(f"   {symbol}: {contract}")

    logger.info(f"   Mois actif: {status['active_month']}")
    logger.info(f"   Prochain rollover: {status['next_rollover_date']} ({status['days_until_rollover']} jours)")

    if status['warning']:
        logger.warning(status['warning'])

    logger.info("="*60)


# ═══════════════════════════════════════════════════════════════════════════════
#                           CONVERSION SYMBOLES
# ═══════════════════════════════════════════════════════════════════════════════

def sierra_to_base_symbol(sierra_symbol: str) -> str:
    """
    Convertit un symbole Sierra vers le symbole de base.

    Args:
        sierra_symbol: ex: 'ESH26-CME', 'ESZ25_FUT_CME', 'NQH26-CME'

    Returns:
        Symbole de base: 'ES', 'NQ', 'RTY'

    Example:
        >>> sierra_to_base_symbol("ESH26-CME")
        'ES'
        >>> sierra_to_base_symbol("NQZ25_FUT_CME")
        'NQ'
    """
    # Retirer suffixes
    base = sierra_symbol.split("-")[0].split("_")[0]

    # Retirer le code mois/année (H26, Z25, M26, U26, etc.)
    for month in MONTH_SEQUENCE:
        for year in range(20, 40):  # 2020-2039
            suffix = f"{month}{year}"
            if base.endswith(suffix):
                return base[:-len(suffix)]

    # Si pas de match, retourner les 2-3 premiers caractères
    if base.startswith('RTY'):
        return 'RTY'
    elif base.startswith('MES') or base.startswith('MNQ'):
        return base[:3]
    else:
        return base[:2]


def is_valid_contract_symbol(symbol: str) -> bool:
    """
    Vérifie si un symbole de contrat est valide et actuel.

    Args:
        symbol: ex: 'ESH26', 'ESZ25-CME'

    Returns:
        True si le symbole correspond au contrat actif
    """
    base = sierra_to_base_symbol(symbol)
    expected = get_active_contract(base)

    # Normaliser pour comparaison
    clean_symbol = symbol.split("-")[0].split("_")[0].upper()
    return clean_symbol == expected.upper()


# ═══════════════════════════════════════════════════════════════════════════════
#                           VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

def validate_contracts() -> bool:
    """
    Valide que les contrats calculés sont cohérents.

    Returns:
        True si OK (toujours True en mode auto!)
    """
    # En mode automatique, les contrats sont toujours valides
    contracts = get_legacy_active_contracts()

    # Vérifier que tous ont le même mois
    month_codes = set()
    for contract in contracts.values():
        month_codes.add(contract[-3])

    if len(month_codes) > 1:
        logger.error(f"❌ Incohérence: Différents mois détectés: {month_codes}")
        return False

    logger.info(f"✅ Contrats validés: {contracts}")
    return True


# ═══════════════════════════════════════════════════════════════════════════════
#                           TEST
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n" + "="*60)
    print("   🎯 TEST FUTURES ROLLOVER - MODE AUTOMATIQUE")
    print("="*60)

    print(f"\n📅 Date actuelle: {date.today()}")

    print(f"\n📊 Contrats actifs (calculés automatiquement):")
    for sym in ['ES', 'NQ', 'RTY']:
        contract = get_active_contract(sym)
        sierra = get_sierra_symbol(sym)
        print(f"   {sym} → {contract} → {sierra}")

    print(f"\n📅 Mois actif: {get_active_month_code()}")
    print(f"📅 Année: 20{get_active_year()}")
    print(f"📅 Expiration: {get_contract_expiry_month()}")
    print(f"📅 Prochain rollover: {get_next_rollover_date()}")
    print(f"📅 Jours restants: {days_until_rollover()}")

    warning = check_rollover_warning()
    if warning:
        print(f"\n⚠️ {warning}")
    else:
        print(f"\n✅ Pas de rollover imminent")

    print(f"\n🔄 Test conversion symboles:")
    test_symbols = ["ESH26-CME", "NQZ25_FUT_CME", "RTYH26-CME", "ESM26"]
    for sym in test_symbols:
        base = sierra_to_base_symbol(sym)
        valid = is_valid_contract_symbol(sym)
        print(f"   {sym} → {base} (valide: {'✅' if valid else '❌'})")

    print("\n" + "="*60)
    print("   ✅ MODE AUTOMATIQUE - PLUS JAMAIS DE MISE À JOUR MANUELLE!")
    print("="*60 + "\n")
