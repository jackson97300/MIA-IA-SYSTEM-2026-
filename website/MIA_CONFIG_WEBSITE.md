# 🔧 CONFIGURATION MIA IA SYSTEM - WEBSITE

## 📧 ADRESSES EMAIL PROFESSIONNELLES

| Adresse | Usage |
|---------|-------|
| `contact@mia-ia-system.com` | Contact général (formulaire site) |
| `support@mia-ia-system.com` | Support client / SAV |
| `commercial@mia-ia-system.com` | Ventes / Offres / Partenariats |
| `mia@mia-ia-system.com` | Direction / Personnel |

**Destination:** Tous les emails arrivent dans `MIA.IA.SYSTEM@gmail.com`

---

## 🌐 URLS ET DOMAINES

| Type | URL |
|------|-----|
| **Site principal** | `https://mia-ia-system.com` |
| **IP VPS** | `193.70.87.126` |
| **Port Streamlit** | `8504` |

---

## 🔑 CONFIGURATION .ENV (sur le VPS)

```env
# Fichier: /home/ubuntu/mia_ia_system/website/.env

EMAIL_ADDRESS=contact@mia-ia-system.com
EMAIL_PASSWORD=
SITE_URL=https://mia-ia-system.com
COPILOT_URL=http://localhost:8503
SECRET_KEY=mia_ia_system_secret_key_2025_very_secure
```

---

## 📝 CONFIGURATION config.py

### Emails à utiliser dans le code:

```python
# Email pour l'envoi (formulaire contact, newsletter)
EMAIL_CONFIG = {
    "CONTACT_EMAIL": "contact@mia-ia-system.com",
    "SUPPORT_EMAIL": "support@mia-ia-system.com",
    "COMMERCIAL_EMAIL": "commercial@mia-ia-system.com",
    "NOREPLY_EMAIL": "noreply@mia-ia-system.com",  # À créer si besoin
}

# Email d'envoi SMTP (Gmail)
SMTP_CONFIG = {
    "EMAIL_ADDRESS": "MIA.IA.SYSTEM@gmail.com",
    "SMTP_SERVER": "smtp.gmail.com",
    "SMTP_PORT": 587,
}
```

### Informations légales à compléter:

```python
LEGAL_INFO = {
    "owner_name": "LAZARD",  # Ton nom complet
    "owner_status": "Auto-entrepreneur",  # ou "Particulier" ou "Société"
    "siret": "",  # Si applicable
    "address": "",  # Adresse (optionnel)
    "email": "contact@mia-ia-system.com",
    "phone": "",  # Optionnel
}
```

---

## 🖥️ INFORMATIONS VPS OVH

| Paramètre | Valeur |
|-----------|--------|
| **Nom** | vps-dff469d2.vps.ovh.net |
| **IP** | 193.70.87.126 |
| **IPv6** | 2001:41d0:305:2100::4330 |
| **User** | ubuntu |
| **OS** | Ubuntu 25.04 |
| **Specs** | 4 vCore, 8GB RAM, 75GB SSD |
| **Datacenter** | France - Gravelines |
| **Prix** | 4.49€ HT/mois |

---

## 📂 CHEMINS SUR LE VPS

```
/home/ubuntu/mia_ia_system/website/
├── app.py                 # Application principale
├── config.py              # Configuration
├── database.py            # Base de données
├── .env                   # Variables d'environnement
├── auth/                  # Authentification
├── components/            # Composants UI
├── pages/                 # Pages
├── i18n/                  # Traductions
├── static/                # Logo et assets
└── data/                  # Base SQLite
```

---

## 🔄 COMMANDES UTILES VPS

```bash
# Se connecter au VPS
ssh ubuntu@193.70.87.126

# Redémarrer le site
sudo systemctl restart mia-website

# Voir les logs
sudo journalctl -u mia-website -f

# Statut du service
sudo systemctl status mia-website

# Redémarrer Nginx
sudo systemctl restart nginx
```

---

## 🌐 CONFIGURATION DNS (Cloudflare)

| Type | Name | Content | Proxy |
|------|------|---------|-------|
| A | mia-ia-system.com | 193.70.87.126 | Proxied ☁️ |
| MX | @ | route1.mx.cloudflare.net | DNS only |
| MX | @ | route2.mx.cloudflare.net | DNS only |
| MX | @ | route3.mx.cloudflare.net | DNS only |

**SSL Mode:** Flexible

---

## 💰 COÛTS RÉCAPITULATIFS

| Service | Coût mensuel |
|---------|--------------|
| VPS OVH | 4.49€ HT (~5.39€ TTC) |
| Domaine | ~1€/mois (12€/an) |
| SSL | GRATUIT (Cloudflare) |
| Emails | GRATUIT (Cloudflare) |
| **TOTAL** | **~6.50€/mois** |

---

## ✅ CHECKLIST DÉPLOIEMENT

- [x] VPS OVH commandé
- [x] Ubuntu configuré
- [x] Python + Streamlit installé
- [x] Code transféré
- [x] Service systemd 24/7
- [x] Nginx configuré
- [x] DNS Cloudflare
- [x] SSL HTTPS
- [x] Emails professionnels
- [ ] Tester inscription/connexion
- [ ] Compléter mentions légales
- [ ] Ajouter www.mia-ia-system.com (optionnel)

---

**Dernière mise à jour:** 20 décembre 2025
