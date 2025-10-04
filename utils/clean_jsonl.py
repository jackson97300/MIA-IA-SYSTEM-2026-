"""
utils/clean_jsonl.py
Outils de nettoyage des exports Sierra Chart pour filtrer par symbole (sym).

Fourni:
- clean_symbol_file: filtre un fichier JSONL (streaming via pandas) sur un symbole.
- batch_clean_symbol_dir: nettoie en lot tous les fichiers JSONL d'un dossier pour un symbole donné.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

import pandas as pd


def clean_symbol_file(input_path: str | os.PathLike, output_path: str | os.PathLike, sym: str, chunksize: int = 100_000) -> int:
    """
    Nettoie un fichier JSONL Sierra Chart (cum_delta, nbcv, basedata, trade, quote, etc.)
    en gardant uniquement les lignes correspondant au symbole `sym`.

    Args:
        input_path: chemin du fichier source (JSONL brut).
        output_path: chemin du fichier filtré (JSONL propre).
        sym: symbole à garder (ex: "ESZ25-CME" ou "NQZ25-CME").
        chunksize: taille des lots pour lecture en streaming.

    Returns:
        Nombre de lignes écrites dans le fichier de sortie.
    """
    input_path = str(input_path)
    output_path = str(output_path)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    rows_written = 0
    with pd.read_json(input_path, lines=True, chunksize=chunksize) as reader:
        with open(output_path, "w", encoding="utf-8") as out:
            for chunk in reader:
                if "sym" not in chunk.columns:
                    continue
                filtered = chunk[chunk["sym"] == sym]
                if filtered.empty:
                    continue
                filtered.to_json(out, orient="records", lines=True, force_ascii=False)
                rows_written += int(len(filtered))
    return rows_written


def batch_clean_symbol_dir(src_dir: str | os.PathLike, sym: str, out_dir: str | os.PathLike, patterns: Iterable[str] | None = None, chunksize: int = 100_000) -> int:
    """
    Nettoie en lot tous les fichiers JSONL d'un dossier `src_dir` pour un symbole donné,
    et écrit les résultats dans `out_dir` en conservant les noms de fichiers.

    Args:
        src_dir: dossier contenant des JSONL Sierra Chart.
        sym: symbole cible (ex: "ESZ25-CME").
        out_dir: dossier de sortie (créé si absent).
        patterns: motifs de fichiers à inclure (ex: ["*.jsonl"]). Si None, tous les .jsonl.
        chunksize: taille des lots pour lecture streaming.

    Returns:
        Nombre total de lignes écrites sur l'ensemble des fichiers.
    """
    src_path = Path(src_dir)
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    if patterns is None:
        patterns = ["*.jsonl"]

    total = 0
    for pattern in patterns:
        for fp in sorted(src_path.glob(pattern)):
            dst = out_path / fp.name
            try:
                n = clean_symbol_file(fp, dst, sym=sym, chunksize=chunksize)
                total += n
            except Exception:
                # On continue même si un fichier est invalide
                continue
    return total


__all__ = [
    "clean_symbol_file",
    "batch_clean_symbol_dir",
]





