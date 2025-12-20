# 🚀 MIA IA SYSTEM - Site Web Next.js

Site vitrine professionnel pour MIA IA SYSTEM - Intelligence Artificielle pour le Trading Futures.

![MIA IA SYSTEM](public/images/logo-dark.jpg)

## ✨ Fonctionnalités

- 🎨 **Design moderne** avec Glassmorphism
- 🌊 **Animations fluides** avec Framer Motion
- 📱 **100% Responsive** (Mobile, Tablet, Desktop)
- ⚡ **Ultra-rapide** (Site statique Next.js)
- 🔍 **SEO optimisé**
- 🌐 **Déploiement Cloudflare Pages** (gratuit)

## 🛠️ Stack Technique

- **Framework:** Next.js 14
- **Styling:** Tailwind CSS
- **Animations:** Framer Motion
- **Icons:** Lucide React
- **Language:** TypeScript
- **Déploiement:** Cloudflare Pages

## 📦 Installation

### Prérequis

- Node.js 18+ installé
- npm ou yarn

### Étapes

```bash
# 1. Aller dans le dossier du projet
cd mia-ia-system

# 2. Installer les dépendances
npm install

# 3. Lancer le serveur de développement
npm run dev

# 4. Ouvrir http://localhost:3000
```

## 🏗️ Structure du Projet

```
mia-ia-system/
├── public/
│   └── images/
│       ├── logo-dark.jpg      # Logo fond sombre
│       └── logo-light.jpg     # Logo fond clair
├── src/
│   ├── app/
│   │   ├── layout.tsx         # Layout principal
│   │   └── page.tsx           # Page d'accueil
│   ├── components/
│   │   ├── Header.tsx         # Navigation sticky
│   │   ├── Hero.tsx           # Section hero
│   │   ├── Features.tsx       # Fonctionnalités
│   │   ├── Pricing.tsx        # Tarifs
│   │   ├── FAQ.tsx            # Questions fréquentes
│   │   ├── Contact.tsx        # Contact + Newsletter
│   │   └── Footer.tsx         # Pied de page
│   └── styles/
│       └── globals.css        # Styles globaux
├── tailwind.config.js         # Config Tailwind
├── next.config.js             # Config Next.js
├── tsconfig.json              # Config TypeScript
└── package.json
```

## 🎨 Personnalisation

### Couleurs

Les couleurs sont définies dans `tailwind.config.js` :

```javascript
colors: {
  mia: {
    gold: '#D4AF37',      // Or - Couleur principale
    cyan: '#00B4DC',      // Cyan - Accent
    blue: '#1E3A5F',      // Bleu - Fond
  },
  // ...
}
```

### Logo

Remplacez les fichiers dans `public/images/` :
- `logo-dark.jpg` - Pour fond sombre
- `logo-light.jpg` - Pour fond clair

### Contenu

Modifiez directement les textes dans les composants (`src/components/`).

## 🚀 Déploiement sur Cloudflare Pages

### Option 1: Via GitHub (Recommandé)

1. **Push sur GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/votre-user/mia-ia-system.git
   git push -u origin main
   ```

2. **Connecter à Cloudflare Pages**
   - Aller sur [Cloudflare Dashboard](https://dash.cloudflare.com)
   - Pages → Create a project → Connect to Git
   - Sélectionner le repo GitHub
   - Configuration:
     - **Build command:** `npm run build`
     - **Build output directory:** `out`
     - **Node.js version:** `18`

3. **Configurer le domaine**
   - Custom domains → Add domain → `mia-ia-system.com`

### Option 2: Déploiement manuel

```bash
# Build le projet
npm run build

# Le dossier 'out' contient le site statique
# Upload ce dossier sur Cloudflare Pages
```

## 📝 Commandes Utiles

```bash
# Développement
npm run dev

# Build production
npm run build

# Lancer build production localement
npm run start

# Lint
npm run lint
```

## 🔧 Configuration Cloudflare

Dans Cloudflare Dashboard, assurez-vous que :

- ✅ "Block AI bots" est **désactivé** (pour le SEO)
- ✅ SSL/TLS est sur **Full**
- ✅ Le domaine pointe vers Cloudflare Pages

## 📱 Responsive Breakpoints

| Breakpoint | Taille |
|------------|--------|
| Mobile | < 640px |
| Tablet | 640px - 1024px |
| Desktop | > 1024px |

## 🎯 Performance

Le site est optimisé pour :
- **Lighthouse Score:** 95+
- **First Contentful Paint:** < 1s
- **Time to Interactive:** < 2s

## 📞 Support

Pour toute question : MIA.IA.SYSTEM@GMAIL.COM

---

**Fait avec ❤️ pour MIA IA SYSTEM**
