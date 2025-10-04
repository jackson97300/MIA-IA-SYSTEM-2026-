# -*- coding: utf-8 -*-
"""
unify_chart1_day.py
Unifie les fichiers du CHART 1 (basedata, trade, quote, vwap study) d'une journée donnée.
Sorties:
- chart_1_unified_YYYYMMDD.jsonl : une ligne par i (barre), avec fields propres
- Résumé console: doublons supprimés, consolidations, anomalies volumes

Usage:
  python unifier/unify_chart1_day.py --root DATA_SIERRA_CHART/DATA_2025/SEPTEMBRE/20250924 --date 20250924
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, List, Tuple

from quality.cleaners import dedupe_by_keys


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not path.exists():
        return rows
    with open(path, 'r', encoding='utf-8') as f:
        for ln in f:
            try:
                rows.append(json.loads(ln))
            except Exception:
                continue
    return rows


def _check_study_inventory(root: Path, ymd: str) -> None:
    """Vérifie que la study VWAP (study_id=1) existe et que les subgraphs attendus sont présents.
    Log uniquement des alertes (n'interrompt pas l'unification).
    """
    candidates = [
        root / f"study_inventory_chart_1_{ymd}.jsonl",
        Path(f"study_inventory_chart_1_{ymd}.jsonl"),
    ]
    inv_rows: List[Dict[str, Any]] = []
    for fp in candidates:
        if fp.exists():
            inv_rows = _read_jsonl(fp)
            break
    if not inv_rows:
        print("[WARN] Study inventory introuvable (optional)")
        return

    # Chercher la study VWAP (id 1, nom contient 'Volume Weighted Average Price')
    vwap_study = None
    for r in inv_rows:
        if r.get("study_id") == 1 or str(r.get("name", "")).lower().startswith("volume weighted average price"):
            vwap_study = r
            break
    if vwap_study is None:
        print("[WARN] Study VWAP absente dans l'inventaire (study_id=1)")
        return

    # Vérifier subgraphs clés
    sg = vwap_study.get("subgraphs") or []
    expected = {
        0: "VWAP",
        1: "Top Band 1",
        2: "Bottom Band 1",
        3: "Top Band 2",
        4: "Bottom Band 2",
    }
    alerts = []
    for idx, name in expected.items():
        try:
            got = (sg[idx] or {}).get("name", "")
        except Exception:
            got = ""
        if not got or (name and got != name):
            alerts.append((idx, name, got))
    if alerts:
        print("[WARN] Study VWAP subgraphs inattendus:")
        for idx, exp, got in alerts:
            print(f"   - sg[{idx}] attendu='{exp}' obtenu='{got}'")
    else:
        print("[OK] Study VWAP (id=1) inventaire OK (subgraphs cles)")


def _dedupe_vwap_study(vwap_rows: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], int]:
    # garder la DERNIERE occurrence par (i,t)
    last_by_key: Dict[Tuple[Any, Any], Dict[str, Any]] = {}
    for r in vwap_rows:
        if r.get('type') != 'vwap':
            continue
        key = (r.get('i'), r.get('t'))
        last_by_key[key] = r
    deduped = list(last_by_key.values())
    removed = max(0, len(vwap_rows) - len(deduped))
    return sorted(deduped, key=lambda x: (x.get('i'), x.get('t'))), removed


def _consolidate_basedata(basedata_rows: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], int, int]:
    # garder le dernier enregistrement (t max) pour chaque i
    by_i: Dict[Any, Dict[str, Any]] = {}
    revisions = 0
    for r in basedata_rows:
        if r.get('type') != 'basedata':
            continue
        i = r.get('i')
        prev = by_i.get(i)
        if prev is None or (r.get('t', 0) or 0) >= (prev.get('t', 0) or 0):
            if prev is not None:
                revisions += 1
            by_i[i] = r
    consolidated = list(by_i.values())
    removed = max(0, len(basedata_rows) - len(consolidated))
    return sorted(consolidated, key=lambda x: x.get('i')), removed, revisions


def _validate_volumes_per_bar(final_rows: List[Dict[str, Any]]) -> Dict[str, int]:
    bad_neg = 0
    bad_sum = 0
    for r in final_rows:
        v = int(r.get('v', 0) or 0)
        bidv = int(r.get('bidvol', 0) or 0)
        askv = int(r.get('askvol', 0) or 0)
        if v < 0 or bidv < 0 or askv < 0:
            bad_neg += 1
        if bidv + askv != v:
            bad_sum += 1
    return {"negatives": bad_neg, "sum_mismatch": bad_sum}


def unify_chart1_day(root: Path, ymd: str) -> int:
    # Vérifier l'inventaire des studies (alerte seulement)
    _check_study_inventory(root, ymd)

    base_fp = root / f"CHART_1/chart_1_basedata_{ymd}.jsonl"
    vwap_fp = root / f"CHART_1/chart_1_vwap_{ymd}.jsonl"
    trade_fp = root / f"CHART_1/chart_1_trade_{ymd}.jsonl"  # réservé pour calculs ultérieurs
    quote_fp = root / f"CHART_1/chart_1_quote_{ymd}.jsonl"  # réservé pour contrôles quotes

    basedata_rows = _read_jsonl(base_fp)
    vwap_rows = _read_jsonl(vwap_fp)

    vwap_deduped, vwap_dupes_removed = _dedupe_vwap_study(vwap_rows)
    basedata_final, base_removed, base_revisions = _consolidate_basedata(basedata_rows)

    # joindre sur i
    vwap_by_i = {r.get('i'): r for r in vwap_deduped}
    unified: List[Dict[str, Any]] = []
    for r in basedata_final:
        i = r.get('i')
        w = vwap_by_i.get(i)
        out = {
            "chart": r.get('chart', 1),
            "i": i,
            "t": r.get('t'),
            "o": r.get('o'), "h": r.get('h'), "l": r.get('l'), "c": r.get('c'),
            "v": r.get('v'), "bidvol": r.get('bidvol'), "askvol": r.get('askvol'),
        }
        if w is not None:
            out["study_vwap"] = w.get('v')
        unified.append(out)

    vol_issues = _validate_volumes_per_bar(unified)

    # écrire sortie
    out_fp = root / f"CHART_1/chart_1_unified_{ymd}.jsonl"
    out_fp.parent.mkdir(parents=True, exist_ok=True)
    with open(out_fp, 'w', encoding='utf-8') as f:
        for r in unified:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"[OK] Unification CHART_1 terminee -> {out_fp}")
    print(f"VWAP study: doublons supprimes = {vwap_dupes_removed}")
    print(f"Basedata: lignes supprimees (intermediaires) = {base_removed}, revisions = {base_revisions}")
    print(f"Volumes: negatifs = {vol_issues['negatives']}, bid+ask!=v = {vol_issues['sum_mismatch']}")
    return 0


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="Dossier racine de la journée (…/20250924)")
    ap.add_argument("--date", required=True, help="YYYYMMDD")
    args = ap.parse_args()
    return unify_chart1_day(Path(args.root), args.date)


if __name__ == "__main__":
    raise SystemExit(main())


