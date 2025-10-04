# 📊 TRADINGVIEW MENTHORQ INTEGRATION

**Date de création :** 28 Septembre 2025  
**Version :** 1.0  
**Statut :** Développement

---

## 🎯 OBJECTIF

Ce dossier contient tous les scripts liés à l'intégration TradingView pour récupérer les niveaux MenthorQ.

---

## 📁 STRUCTURE DU DOSSIER

```
menthorq/tradingview/
├── README.md                           # Ce document
├── tradingview_connector.py            # Connecteur principal TradingView
├── q_levels_reader.py                  # Lecteur du tableau Q-Levels
├── momentum_reader.py                  # Lecteur du Momentum Indicator
├── levels_converter.py                 # Convertisseur de niveaux
├── config_tradingview.py               # Configuration TradingView
├── tests/
│   ├── test_connector.py              # Tests du connecteur
│   ├── test_q_levels.py               # Tests Q-Levels
│   └── test_momentum.py               # Tests Momentum
└── examples/
    ├── read_levels_example.py         # Exemple lecture niveaux
    └── integration_example.py         # Exemple intégration
```

---

## 🚀 PREMIÈRE ÉTAPE : LECTURE DES NIVEAUX

### **Script Principal : `q_levels_reader.py`**
- Récupère les niveaux MenthorQ depuis TradingView
- Lit le tableau Q-Levels avec distances
- Formate les données pour notre système

### **Fonctionnalités**
- ✅ Lecture des 5 indicateurs MenthorQ
- ✅ Récupération des distances automatiques
- ✅ Format compatible avec notre système
- ✅ Gestion d'erreurs robuste

---

## 📋 PROCHAINES ÉTAPES

1. **Développer `q_levels_reader.py`** - Lecture des niveaux
2. **Tester la connexion** TradingView
3. **Valider le format** des données
4. **Intégrer avec** le système existant

---

**Dernière mise à jour :** 28 Septembre 2025










