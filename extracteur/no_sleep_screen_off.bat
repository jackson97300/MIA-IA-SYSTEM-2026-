@echo off
REM ============================
REM  No Sleep (secteur) + Ecran OFF apres X min + Capot ferme = Ne rien faire
REM ============================

set X=5  REM <- ecran s’eteint apres 5 minutes (secteur). Change la valeur si besoin.

echo [*] Jamais dormir sur secteur, ecran s’eteint apres %X% min...
powercfg -change -standby-timeout-ac 0
powercfg -change -monitor-timeout-ac %X%

echo [*] Desactivation veille hybride (secteur)
powercfg -setacvalueindex SCHEME_CURRENT SUB_SLEEP HYBRIDSLEEP 0

echo [*] Capot ferme = NE RIEN FAIRE (secteur)
REM Codes: 0=Ne rien faire, 1=Veille, 2=Hibernation, 3=Arret
powercfg -setacvalueindex SCHEME_CURRENT SUB_BUTTONS LIDACTION 0

REM ----- (Optionnel) Reglages batterie -----
REM Jamais dormir sur batterie
REM powercfg -change -standby-timeout-dc 0
REM Ecran OFF apres 3 minutes sur batterie
REM powercfg -change -monitor-timeout-dc 3
REM Veille hybride OFF sur batterie
REM powercfg -setdcvalueindex SCHEME_CURRENT SUB_SLEEP HYBRIDSLEEP 0
REM Capot ferme = NE RIEN FAIRE sur batterie
REM powercfg -setdcvalueindex SCHEME_CURRENT SUB_BUTTONS LIDACTION 0

echo [*] Application du schema courant...
powercfg -SetActive SCHEME_CURRENT

echo [OK] Parametres appliques. Verification rapide:
echo --- SLEEP/SCREEN ---
powercfg /query SCHEME_CURRENT SUB_SLEEP STANDBYIDLE
powercfg /change
echo --- HYBRID SLEEP ---
powercfg /query SCHEME_CURRENT SUB_SLEEP HYBRIDSLEEP
echo --- LID ACTION ---
powercfg /query SCHEME_CURRENT SUB_BUTTONS LIDACTION

pause
