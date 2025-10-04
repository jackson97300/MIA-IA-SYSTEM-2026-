#!/usr/bin/env python3
"""
Analyseur de fichier unified JSONL
 - Compte de lignes
 - Premier / Dernier timestamp
 - Intervalle moyen (approx)
 - Présence des sections (basedata, vwap, vva, pvwap, depth, nbcv, atr, cumulative_delta)
 - Champs manquants fréquents
 - Aperçu des dernières lignes
"""

import argparse
import json
import os
from pathlib import Path
from typing import Optional, Dict, Any


def tail_lines(path: Path, max_bytes: int = 65536) -> list[str]:
    if not path.exists():
        return []
    with open(path, "rb") as f:
        f.seek(0, os.SEEK_END)
        size = f.tell()
        read_size = min(max_bytes, size)
        f.seek(-read_size, os.SEEK_END)
        data = f.read(read_size)
    text = data.decode("utf-8", errors="ignore")
    return text.splitlines()


def count_lines(path: Path) -> int:
    if not path.exists():
        return 0
    n = 0
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for _ in f:
            n += 1
    return n


def parse_jsonl(path: Path, max_lines: Optional[int] = None):
    if not path.exists():
        return []
    out = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                out.append(obj)
            except Exception:
                pass
            if max_lines and len(out) >= max_lines:
                break
    return out


def parse_jsonl_tail(path: Path, tail_count: int = 200):
    lines = tail_lines(path)
    if not lines:
        return []
    # garder seulement la fin
    lines = lines[-tail_count:]
    out = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    return out


def summarize_sections(objs: list[Dict[str, Any]]) -> Dict[str, Any]:
    if not objs:
        return {}
    sections = ["basedata", "vwap", "vva", "pvwap", "depth", "nbcv", "atr", "cumulative_delta", "quote", "trade", "menthorq"]
    counts = {s: 0 for s in sections}
    ts_first = None
    ts_last = None
    for o in objs:
        t = o.get("t")
        if isinstance(t, (int, float)):
            ts_first = t if ts_first is None else min(ts_first, t)
            ts_last = t if ts_last is None else max(ts_last, t)
        for s in sections:
            if o.get(s) is not None:
                counts[s] += 1
    n = len(objs)
    presence = {s: round(counts[s] / n, 3) for s in sections}
    return {
        "count": n,
        "ts_first": ts_first,
        "ts_last": ts_last,
        "presence_ratio": presence,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", type=str, required=True, help="Chemin du fichier unified_*.jsonl à analyser")
    ap.add_argument("--show-tail", type=int, default=3, help="Afficher N dernières lignes (par défaut 3)")
    args = ap.parse_args()

    path = Path(args.file)
    if not path.exists():
        print(f"❌ Fichier introuvable: {path}")
        return

    print(f"📄 Fichier: {path}")
    print(f"📏 Taille: {path.stat().st_size} bytes")
    total = count_lines(path)
    print(f"🔢 Lignes totales: {total}")

    # Analyse globale approximative (parsing partiel: head + tail)
    head_objs = parse_jsonl(path, max_lines=200)
    tail_objs = parse_jsonl_tail(path, tail_count=200)

    if head_objs:
        s_head = summarize_sections(head_objs)
        print("\n🧭 Début du fichier:")
        print(json.dumps(s_head, indent=2))
    if tail_objs:
        s_tail = summarize_sections(tail_objs)
        print("\n🏁 Fin du fichier (échantillon):")
        print(json.dumps(s_tail, indent=2))

    # Dernières lignes
    if args.show_tail > 0:
        tail_show = parse_jsonl_tail(path, tail_count=args.show_tail)
        print(f"\n👀 Dernières {args.show_tail} lignes:")
        for obj in tail_show:
            t = obj.get("t")
            c = (obj.get("basedata") or {}).get("c")
            keys = [k for k, v in obj.items() if v is not None and k != "t"]
            print(json.dumps({"t": t, "close": c, "keys": keys}, ensure_ascii=False))


if __name__ == "__main__":
    main()
























