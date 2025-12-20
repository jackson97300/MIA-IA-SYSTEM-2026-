#!/usr/bin/env bash
set -euo pipefail

############################################
# CONFIG – adapte ici si besoin
############################################
DATA_DIR="${DATA_DIR:-.}"                    # dossier des .jsonl
SAMPLE_LINES="${SAMPLE_LINES:-2000}"         # nb max de lignes lues par fichier pour les checks
ZERO_ZERO_THRESH="${ZERO_ZERO_THRESH:-30}"   # % max autorisé de lignes avec dom_bq1=0 & dom_aq1=0
BBO_SPREAD_MAX_TICKS="${BBO_SPREAD_MAX_TICKS:-5}" # spread ticks max toléré (filet)
TICK_ES="${TICK_ES:-0.25}"
TICK_NQ="${TICK_NQ:-0.25}"

############################################
# PRÉREQUIS
############################################
need() { command -v "$1" >/dev/null 2>&1 || { echo "Missing dep: $1"; exit 2; }; }
need jq; need awk; need sed; need wc; need stat; need bc

ts() { date +"%Y-%m-%d %H:%M:%S"; }

hr() { printf '%*s\n' "${COLUMNS:-80}" '' | tr ' ' -; }

############################################
# UTILITAIRES
############################################
# Imprime volume fichiers (taille + lignes)
report_files() {
  local glob="$1"
  echo "[files] $glob"
  printf "%-52s %12s %12s\n" "file" "size_bytes" "lines"
  # shellcheck disable=SC2012
  LC_ALL=C ls -1 $glob 2>/dev/null | while read -r f; do
    [ -f "$f" ] || continue
    sz=$(stat -c%s "$f" 2>/dev/null || stat -f%z "$f")
    ln=$(wc -l < "$f" || echo 0)
    printf "%-52s %12d %12d\n" "$(basename "$f")" "$sz" "$ln"
  done
}

# Calcule le % de lignes dom_bq1=0 & dom_aq1=0 (échantillon)
zero_zero_ratio() {
  local f="$1"
  awk_count=$(head -n "$SAMPLE_LINES" "$f" | jq -r '[.dom_bq1//0,.dom_aq1//0]|@tsv' 2>/dev/null \
    | awk 'BEGIN{n=0;z=0} {n++; if($1==0 && $2==0) z++} END{if(n>0) printf("%.2f", 100*z/n); else print "0.00"}')
  echo "$awk_count"
}

# Vérifie BBO vs DOM + spread ticks sur l'échantillon (tolérance 5%)
check_bbo_align() {
  local f="$1" sym instr_tick
  sym=$(head -n 1 "$f" | jq -r '.sym' 2>/dev/null)
  case "$sym" in
    ES* ) instr_tick="$TICK_ES" ;;
    NQ* ) instr_tick="$TICK_NQ" ;;
    *   ) instr_tick="$TICK_ES" ;;
  esac
  local fails total
  total=$(head -n "$SAMPLE_LINES" "$f" | wc -l)
  if [ "${total:-0}" -eq 0 ]; then echo "OK"; return; fi
  fails=$(head -n "$SAMPLE_LINES" "$f" \
    | jq --argjson tick "$instr_tick" --argjson maxsp "$BBO_SPREAD_MAX_TICKS" -r \
      '((.dom_bid1 <= .best_bid) and (.dom_ask1 >= .best_ask)
        and ((.best_ask - .best_bid)/$tick <= $maxsp)) | if . then 0 else 1 end' \
    | awk '{s+=$1} END{print s+0}')
  perc=$(echo "scale=6; 100*$fails/$total" | bc -l)
  awk -v p="$perc" 'BEGIN{if(p<=5.0) print "OK"; else print "FAIL"}'
}

# Vérifie familles prix (ES<10k, NQ>10k)
check_family() {
  local f="$1" sym
  sym=$(head -n 1 "$f" | jq -r '.sym' 2>/dev/null)
  if [[ "$sym" =~ ^ES ]]; then
    head -n "$SAMPLE_LINES" "$f" | jq -e '.dom_bid1 < 10000' >/dev/null && echo "OK" || echo "FAIL"
  elif [[ "$sym" =~ ^NQ ]]; then
    head -n "$SAMPLE_LINES" "$f" | jq -e '.dom_bid1 > 10000' >/dev/null && echo "OK" || echo "FAIL"
  else
    echo "OK"
  fi
}

# Vérifie monotonicité t_ms & seq (échantillon)
backsteps() {
  local f="$1" key="$2"
  head -n "$SAMPLE_LINES" "$f" | jq -r ".$key" 2>/dev/null | \
    awk 'BEGIN{prev=""; e=0} { if(prev!="" && $1<prev) e++; prev=$1 } END{print e+0}'
}

# JSON valide + MenthorQ dans l’objet (gex ou blind_spot)
json_sanity() {
  local f="$1"
  head -n "$SAMPLE_LINES" "$f" | jq -e . >/dev/null || { echo "JSON_ERR"; return; }
  head -n "$SAMPLE_LINES" "$f" | jq -e 'has("gex_7") or has("blind_spot_1")' >/dev/null && echo "OK" || echo "WARN_NO_MQ"
}

############################################
# RAPPORT
############################################
echo "=== UNIFIED HEALTH REPORT ===  $(ts)"
echo "DATA_DIR=$DATA_DIR  SAMPLE_LINES=$SAMPLE_LINES  ZERO_ZERO_THRESH=$ZERO_ZERO_THRESH%  SPREAD_MAX_TICKS=$BBO_SPREAD_MAX_TICKS"
hr

# 1) Volumes
report_files "$DATA_DIR/chart_*_{unified,trade,quote,depth}_*.jsonl" || true
hr

# 2) Checks par fichier UNIFIED
echo "[unified checks]"
printf "%-40s  %-8s  %-10s  %-10s  %-10s  %-10s  %-10s\n" "file" "JSON" "ZERO0(%)" "BBO" "FAMILY" "t_ms↓" "seq↓"
for f in $DATA_DIR/chart_*_unified_*.jsonl; do
  [ -f "$f" ] || continue
  json=$(json_sanity "$f")
  zz=$(zero_zero_ratio "$f")
  bbo=$(check_bbo_align "$f")
  fam=$(check_family "$f")
  tms=$(backsteps "$f" "t_ms")
  seq=$(backsteps "$f" "summary.seq")
  printf "%-40s  %-8s  %10s  %-10s  %-10s  %10s  %10s\n" "$(basename "$f")" "$json" "$zz" "$bbo" "$fam" "$tms" "$seq"
done
hr

# 3) Alerte si ZERO_ZERO au-dessus du seuil
alert=0
for f in $DATA_DIR/chart_*_unified_*.jsonl; do
  [ -f "$f" ] || continue
  ratio=$(zero_zero_ratio "$f")
  ratio_num=$(echo "$ratio" | sed 's/%//')
  if [ "$(echo "$ratio_num > $ZERO_ZERO_THRESH" | bc -l)" -eq 1 ]; then
    echo "ALERT: $(basename "$f") dom_bq1=0 & dom_aq1=0 ratio ${ratio_num}% > ${ZERO_ZERO_THRESH}%"
    alert=1
  fi
done

exit $alert
