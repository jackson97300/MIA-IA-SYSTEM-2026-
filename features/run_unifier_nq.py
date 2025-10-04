#!/usr/bin/env python3
import os, sys, subprocess, time, datetime

# ---- PARAMS ----
BASE = r"D:\MIA_IA_system"
PYTHON = sys.executable
CHART  = "9"
SYMBOL = "NQ"
TICK   = "0.25"
WATCH_SECONDS = "60"
TTL_SECONDS   = "900"
CORR_TTL      = "120"
LOG_DIR = os.path.join(BASE, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

def run_once():
    today = datetime.datetime.now().strftime("%Y%m%d")
    logf  = os.path.join(LOG_DIR, f"run_unifier_nq_{today}.log")
    cmd = [
        PYTHON, os.path.join(BASE, "features", "mia_unifier.py"),
        "--indir", BASE,
        "--date", "today",
        "--chart", CHART,
        "--symbol", SYMBOL,
        "--tick-size", TICK,
        "--minute-mode",
        "--watch-seconds", WATCH_SECONDS,
        "--append-stream",
        "--menthorq-filter",
        "--mia-optimal",
        "--correlation-ttl-seconds", CORR_TTL,
        "--ttl-seconds", TTL_SECONDS,
        "--verbose",
    ]
    with open(logf, "a", encoding="utf-8") as lf:
        lf.write("\n\n==== START NQ Unifier " + datetime.datetime.now().isoformat() + " ====\n")
        return subprocess.call(cmd, stdout=lf, stderr=lf)

if __name__ == "__main__":
    while True:
        try:
            run_once()
        except Exception as e:
            try:
                with open(os.path.join(LOG_DIR, "run_unifier_nq_errors.log"), "a", encoding="utf-8") as ef:
                    ef.write(f"[{datetime.datetime.now().isoformat()}] {e}\n")
            except Exception:
                pass
        time.sleep(3)




















