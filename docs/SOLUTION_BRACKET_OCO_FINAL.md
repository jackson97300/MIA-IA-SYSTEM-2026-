# 🎯 SOLUTION FINALE: Bracket Orders avec OCO - Sierra Chart DTC

**Date**: 1er Décembre 2025
**Status**: ✅ VALIDÉ EN PRODUCTION

---

## 📋 Résumé du Problème

Les bracket orders (Entry + TP + SL) ne fonctionnaient pas correctement en simulation locale Sierra Chart:
- TP ou SL disparaissaient immédiatement
- Quand TP était touché, SL restait actif (ordres orphelins)
- Les offsets TP/SL étaient inversés pour SHORT

---

## ✅ Solution Validée

### 1. NE PAS utiliser `ParentTriggerClientOrderID`

```python
# ❌ NE FONCTIONNE PAS en simulation locale:
tp_msg = {
    "ParentTriggerClientOrderID": parent_cid,  # ← RETIRE ÇA!
    ...
}

# ✅ FONCTIONNE:
tp_msg = {
    "OCOGroup1": oco_group,  # ← SEUL lien entre TP et SL
    ...
}
```

### 2. Calcul des Offsets selon la Direction

```python
# 🔥 FIX CRITIQUE: Calcul selon la direction!
if parent_side == "BUY":  # LONG
    tp_price = fill_price + (tp_offset_ticks * tick_size)  # TP AU-DESSUS
    sl_price = fill_price - (sl_offset_ticks * tick_size)  # SL EN-DESSOUS
else:  # SHORT (SELL)
    tp_price = fill_price - (tp_offset_ticks * tick_size)  # TP EN-DESSOUS
    sl_price = fill_price + (sl_offset_ticks * tick_size)  # SL AU-DESSUS
```

### 3. OCO Manuel (Sierra Chart ne le fait pas automatiquement)

```python
# Dans _dtc_listener():
if order_status == 7 and client_order_id in self._oco_pairs:
    opposite_cid = self._oco_pairs[client_order_id]
    logger.warning(f"🚨 {client_order_id} FILLED → Annulation IMMÉDIATE {opposite_cid}")
    asyncio.create_task(self._cancel_order_by_client_id(
        symbol=msg_symbol,
        client_order_id=opposite_cid,
        reason=f"OCO: {client_order_id} filled",
        skip_flatten=True  # Position déjà fermée par le FILL
    ))
```

---

## 📊 Séquence des Messages DTC

```
1️⃣ ENTRY (MARKET)
   Type: 208 (SUBMIT_NEW_SINGLE_ORDER)
   OrderType: 1 (MARKET)
   BuySell: 1=BUY ou 2=SELL
   OpenCloseTrade: 1 (Open)

   → Attendre Status=7 (FILLED)

2️⃣ TAKE PROFIT (LIMIT)
   Type: 208 (SUBMIT_NEW_SINGLE_ORDER)
   OrderType: 2 (LIMIT)
   BuySell: OPPOSÉ à l'entrée
   Price1: Prix TP absolu
   OCOGroup1: "TAG_OCO_timestamp"
   OpenCloseTrade: 2 (Close)

3️⃣ STOP LOSS (STOP)
   Type: 208 (SUBMIT_NEW_SINGLE_ORDER)
   OrderType: 3 (STOP)
   BuySell: OPPOSÉ à l'entrée
   Price1: Prix SL absolu
   StopPrice: Prix SL absolu
   OCOGroup1: "TAG_OCO_timestamp"  ← MÊME groupe que TP!
   OpenCloseTrade: 2 (Close)
```

---

## ⚠️ Pièges à Éviter

### ❌ Ce qui NE FONCTIONNE PAS:

1. `IsParentOrder=1` - Ignoré en simulation
2. `ParentTriggerClientOrderID` - Cause des ordres fantômes
3. `AttachedOrderType` - Non supporté
4. `SUBMIT_NEW_OCO_ORDER` (Type 206) avec parent - Bugué
5. Compter sur Sierra pour annuler l'OCO automatiquement

### ✅ Ce qui FONCTIONNE:

1. 3 ordres SÉPARÉS (entry + TP + SL)
2. `OCOGroup1` identique pour TP et SL
3. OCO géré manuellement côté bot
4. Prix ABSOLUS calculés depuis le fill réel

---

## 🧪 Test Validé

```
Entry SHORT @ 6842.75
TP @ 6837.75 (20t en-dessous) ✅
SL @ 6847.75 (20t au-dessus) ✅

~3 minutes plus tard...

TP FILLED!
🚨 ES_TP_321593 FILLED → Annulation IMMÉDIATE ES_SL_96d78b
✅ CANCEL terminée pour ES_SL_96d78b
```

---

## 📁 Fichiers Modifiés

- `execution/sierra_dtc_connector.py`:
  - Méthode `place_parent_then_children()` - Calcul offsets corrigé
  - Méthode `_dtc_listener()` - OCO manuel
  - Retiré `ParentTriggerClientOrderID` des messages TP/SL

---

## 🚨 RÈGLE D'OR

> **Ne JAMAIS utiliser `ParentTriggerClientOrderID` en simulation locale Sierra Chart.**
> **Toujours gérer l'OCO manuellement côté bot.**

---

## 📚 Références

- Documentation DTC Sierra Chart: https://www.sierrachart.com/index.php?page=doc/DTCProtocol.html
- Backup fonctionnel: `ARCHIVE/old_folders/EXECUTION BAKUP/`
