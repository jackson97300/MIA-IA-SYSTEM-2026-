import json
from datetime import datetime, timezone

f = open(r'D:\MIA_IA_system\DATA_SIERRA_CHART\DATA_2025\DECEMBRE\20251205\CHART_9\ML_READY\ml_NQZ25_FUT_CME_9.jsonl')
lines = [json.loads(l) for l in list(f)[:10]]

print("Premiers snapshots du 05/12/2025:")
for s in lines:
    t_ms = s['t_ms']
    dt = datetime.fromtimestamp(t_ms / 1000, tz=timezone.utc)
    print(f"  t_ms={t_ms}, UTC={dt}, mid={s.get('mid',0):.2f}, pressure={s.get('pressure_strength',0):.4f}")

# Chercher snapshots autour de 20h (19h UTC)
print("\n\nCherche snapshots vers 19h-20h UTC (20h-21h Paris)...")
f.seek(0)
found = 0
for line in f:
    s = json.loads(line)
    t_ms = s['t_ms']
    dt = datetime.fromtimestamp(t_ms / 1000, tz=timezone.utc)
    if dt.hour >= 19 and dt.hour <= 20 and found < 5:
        print(f"  t_ms={t_ms}, UTC={dt}, mid={s.get('mid',0):.2f}, pressure={s.get('pressure_strength',0):.4f}")
        found += 1
