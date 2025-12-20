"""
Debug: Vérifier la synchronisation ES/NQ
"""

import sys
import json
from pathlib import Path
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_PATH = Path(r"D:\MIA_IA_system\DATA_SIERRA_CHART\DATA_2025\DECEMBRE\20251205")

# Charger quelques lignes ES et NQ
es_path = BASE_PATH / "CHART_3" / "ML_READY"
nq_path = BASE_PATH / "CHART_9" / "ML_READY"

print("="*80)
print("DEBUG: Synchronisation ES/NQ - 05/12/2025")
print("="*80)

# ES
es_files = list(es_path.glob("*.jsonl"))
print(f"\nES files: {es_files}")

if es_files:
    with open(es_files[0], 'r') as f:
        print("\n[ES] Premiers 5 snapshots:")
        for i, line in enumerate(f):
            if i >= 5:
                break
            data = json.loads(line)
            t = data.get('t_ms', 0)
            dt = datetime.fromtimestamp(t/1000) if t > 0 else "N/A"
            print(f"   t_ms={t} | time={dt} | mid={data.get('mid',0)} | delta={data.get('delta',0)}")

# NQ
nq_files = list(nq_path.glob("*.jsonl"))
print(f"\nNQ files: {nq_files}")

if nq_files:
    with open(nq_files[0], 'r') as f:
        print("\n[NQ] Premiers 5 snapshots:")
        for i, line in enumerate(f):
            if i >= 5:
                break
            data = json.loads(line)
            t = data.get('t_ms', 0)
            dt = datetime.fromtimestamp(t/1000) if t > 0 else "N/A"
            print(f"   t_ms={t} | time={dt} | mid={data.get('mid',0)} | delta={data.get('delta',0)}")

# Comparer les plages de timestamps
print("\n[COMPARE] Plage de timestamps:")

if es_files:
    es_times = []
    with open(es_files[0], 'r') as f:
        for line in f:
            data = json.loads(line)
            t = data.get('t_ms', 0)
            if t > 0:
                es_times.append(t)

    if es_times:
        print(f"   ES: min={es_times[0]} ({datetime.fromtimestamp(es_times[0]/1000)})")
        print(f"       max={es_times[-1]} ({datetime.fromtimestamp(es_times[-1]/1000)})")

if nq_files:
    nq_times = []
    with open(nq_files[0], 'r') as f:
        for line in f:
            data = json.loads(line)
            t = data.get('t_ms', 0)
            if t > 0:
                nq_times.append(t)

    if nq_times:
        print(f"   NQ: min={nq_times[0]} ({datetime.fromtimestamp(nq_times[0]/1000)})")
        print(f"       max={nq_times[-1]} ({datetime.fromtimestamp(nq_times[-1]/1000)})")

# Vérifier si les plages se chevauchent
if es_times and nq_times:
    overlap_start = max(es_times[0], nq_times[0])
    overlap_end = min(es_times[-1], nq_times[-1])

    if overlap_start < overlap_end:
        print(f"\n   OVERLAP: {datetime.fromtimestamp(overlap_start/1000)} -> {datetime.fromtimestamp(overlap_end/1000)}")
    else:
        print(f"\n   [ERREUR] PAS DE CHEVAUCHEMENT!")
        print(f"   ES se termine avant que NQ commence, ou inversement.")
