"""
Configuration Discord pour le module Prop Firm
Webhook dédié au canal #prop-firm
"""

# ═══════════════════════════════════════════════════════════════════════════════
# WEBHOOK PROP FIRM DÉDIÉ
# ═══════════════════════════════════════════════════════════════════════════════

PROP_FIRM_WEBHOOK = "https://discordapp.com/api/webhooks/1451190102557724753/kw-leOfUArWaNdI6vfn7u0d_8NZEv2-icPu2aqFJCd4FqXA1x6NYwXQQgEaSuGuT3Ksz"

# Informations du webhook
WEBHOOK_INFO = {
    "name": "Prop firm",
    "channel_id": "1451189977864994877",
    "guild_id": "1388949780079575142",
    "webhook_id": "1451190102557724753",
}


def get_prop_firm_webhook() -> str:
    """Retourne l'URL du webhook Prop Firm"""
    return PROP_FIRM_WEBHOOK

