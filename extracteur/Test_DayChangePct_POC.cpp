// ============================================================================
// Test_DayChangePct_POC.cpp
//
// POC (Proof of Concept) pour valider le calcul day_change_pct
// depuis le Previous Close (Settlement) au lieu du Session Open
//
// OBJECTIF : Valider que la méthode Daily Chart donne des résultats
//            cohérents avec CME/Bloomberg avant intégration dans MIA_Dumper
//
// USAGE :
// 1. Compiler cette DLL
// 2. Dans Sierra Chart, créer un Daily Chart pour NQZ25 (ex: Chart #10)
// 3. Sur votre chart intraday NQ, ajouter cette étude
// 4. Configurer l'Input "Daily Chart Number" = 10
// 5. Vérifier les logs dans Message Log
//
// VALIDATION :
// - Comparer "Day Change % (Settlement)" avec CME/Bloomberg
// - L'écart doit être < 0.05%
//
// Date: 2025-11-05
// Version: POC v1.0
// ============================================================================

#include "sierrachart.h"

// ============================================================================
// NOM DE LA DLL (OBLIGATOIRE pour Sierra Chart)
// ============================================================================
SCDLLName("Test Day Change Pct POC")

// Fonction d'entrée de l'étude
SCSFExport scsf_TestDayChangePct(SCStudyInterfaceRef sc)
{
    // ========================================================================
    // CONFIGURATION DE L'ÉTUDE
    // ========================================================================

    if (sc.SetDefaults)
    {
        sc.GraphName = "Test Day Change % POC";
        sc.StudyDescription = "POC: Test Previous Close vs Session Open";

        sc.AutoLoop = 1;  // Appeler pour chaque barre
        sc.GraphRegion = 1;  // Sous-graphe séparé

        // ====================================================================
        // INPUTS
        // ====================================================================

        // Input 0: Numéro du Daily Chart à utiliser comme référence
        sc.Input[0].Name = "Daily Chart Number";
        sc.Input[0].SetInt(10);
        sc.Input[0].SetDescription("Numéro du chart Daily à référencer (ex: Chart #10)");

        // Input 1: Afficher les logs de debug
        sc.Input[1].Name = "Enable Debug Logs";
        sc.Input[1].SetYesNo(1);  // Oui par défaut

        // ====================================================================
        // SUBGRAPHS (pour affichage graphique)
        // ====================================================================

        // Subgraph 0: Day Change % (méthode Settlement)
        sc.Subgraph[0].Name = "Day Change % (Settlement)";
        sc.Subgraph[0].DrawStyle = DRAWSTYLE_LINE;
        sc.Subgraph[0].PrimaryColor = RGB(0, 255, 0);  // Vert
        sc.Subgraph[0].LineWidth = 2;

        // Subgraph 1: Day Change % (méthode Session Open - pour comparaison)
        sc.Subgraph[1].Name = "Day Change % (Session Open)";
        sc.Subgraph[1].DrawStyle = DRAWSTYLE_LINE;
        sc.Subgraph[1].PrimaryColor = RGB(255, 0, 0);  // Rouge
        sc.Subgraph[1].LineWidth = 1;
        sc.Subgraph[1].LineStyle = LINESTYLE_DOT;

        // Subgraph 2: Différence entre les deux méthodes
        sc.Subgraph[2].Name = "Delta (Settlement - SessionOpen)";
        sc.Subgraph[2].DrawStyle = DRAWSTYLE_LINE;
        sc.Subgraph[2].PrimaryColor = RGB(255, 255, 0);  // Jaune
        sc.Subgraph[2].LineWidth = 1;

        return;
    }

    // ========================================================================
    // TRAITEMENT PRINCIPAL
    // ========================================================================

    // Récupérer les inputs
    int dailyChartNumber = sc.Input[0].GetInt();
    bool enableDebugLogs = sc.Input[1].GetYesNo();

    // Prix actuel
    float currentPrice = sc.Close[sc.Index];

    // ========================================================================
    // MÉTHODE 1 : PREVIOUS CLOSE (depuis Daily Chart) ✅ NOUVELLE MÉTHODE
    // ========================================================================

    float previousClose = 0.0f;
    float dayChangePct_Settlement = 0.0f;

    // Récupérer les données du Daily Chart
    SCGraphData DailyBaseData;
    sc.GetChartBaseData(dailyChartNumber, DailyBaseData);

    if (DailyBaseData[SC_LAST].GetArraySize() > 0)
    {
        int dailyLastIndex = DailyBaseData[SC_LAST].GetArraySize() - 1;

        // Vérifier si la dernière barre du daily chart est aujourd'hui
        // Note: On ne peut pas accéder directement aux timestamps du Daily Chart
        // depuis GetChartBaseData, donc on suppose que la dernière barre est aujourd'hui
        // et on prend J-1 systématiquement

        int previousCloseIndex = dailyLastIndex - 1;  // Toujours prendre J-1

        // Sécurité : vérifier l'index
        if (previousCloseIndex >= 0)
        {
            previousClose = DailyBaseData[SC_LAST][previousCloseIndex];

            // Calculer la variation depuis le settlement
            if (previousClose > 0.0f)
            {
                dayChangePct_Settlement = ((currentPrice - previousClose) / previousClose) * 100.0f;
            }
        }
    }

    // ========================================================================
    // MÉTHODE 2 : SESSION OPEN ❌ ANCIENNE MÉTHODE (pour comparaison)
    // ========================================================================

    float sessionOpen = 0.0f;
    float dayChangePct_SessionOpen = 0.0f;

    // Obtenir le temps de début de session
    int sessionStartTimeInt = sc.SessionStartTime();

    // Scanner les dernières 500 barres pour trouver le session start
    const int lookback = (sc.Index < 500) ? sc.Index : 500;

    for (int i = sc.Index - lookback; i <= sc.Index; i++)
    {
        if (i < 0) continue;

        int barTimeInt = sc.BaseDateTimeIn[i].GetTime();

        // Tolérance de 60 secondes
        if (abs(barTimeInt - sessionStartTimeInt) <= 60)
        {
            sessionOpen = sc.Open[i];
            break;
        }
    }

    // Calculer la variation depuis le session open
    if (sessionOpen > 0.0f)
    {
        dayChangePct_SessionOpen = ((currentPrice - sessionOpen) / sessionOpen) * 100.0f;
    }

    // ========================================================================
    // CALCUL DE LA DIFFÉRENCE
    // ========================================================================

    float deltaMethodsPct = dayChangePct_Settlement - dayChangePct_SessionOpen;

    // ========================================================================
    // STOCKER LES RÉSULTATS DANS LES SUBGRAPHS
    // ========================================================================

    sc.Subgraph[0][sc.Index] = dayChangePct_Settlement;
    sc.Subgraph[1][sc.Index] = dayChangePct_SessionOpen;
    sc.Subgraph[2][sc.Index] = deltaMethodsPct;

    // ========================================================================
    // LOGS DE DEBUG (uniquement sur la dernière barre)
    // ========================================================================

    if (enableDebugLogs && sc.Index == sc.ArraySize - 1)
    {
        SCString logMsg;

        logMsg.Format("========== TEST DAY CHANGE PCT ==========");
        sc.AddMessageToLog(logMsg, 0);

        logMsg.Format("Prix Actuel           : %.2f", currentPrice);
        sc.AddMessageToLog(logMsg, 0);

        logMsg.Format("------------------------------------------");
        sc.AddMessageToLog(logMsg, 0);

        logMsg.Format("MÉTHODE 1 (Settlement - NOUVELLE):");
        sc.AddMessageToLog(logMsg, 0);

        logMsg.Format("  Previous Close      : %.2f", previousClose);
        sc.AddMessageToLog(logMsg, 0);

        logMsg.Format("  Day Change %%        : %.4f%%", dayChangePct_Settlement);
        sc.AddMessageToLog(logMsg, 0);

        logMsg.Format("------------------------------------------");
        sc.AddMessageToLog(logMsg, 0);

        logMsg.Format("MÉTHODE 2 (Session Open - ANCIENNE):");
        sc.AddMessageToLog(logMsg, 0);

        logMsg.Format("  Session Open        : %.2f", sessionOpen);
        sc.AddMessageToLog(logMsg, 0);

        logMsg.Format("  Day Change %%        : %.4f%%", dayChangePct_SessionOpen);
        sc.AddMessageToLog(logMsg, 0);

        logMsg.Format("------------------------------------------");
        sc.AddMessageToLog(logMsg, 0);

        logMsg.Format("DIFFÉRENCE            : %.4f%% (Settlement - SessionOpen)", deltaMethodsPct);
        sc.AddMessageToLog(logMsg, 0);

        // Évaluation
        if (fabs(deltaMethodsPct) < 0.05f)
        {
            logMsg.Format("STATUT : ✅ Méthodes quasi-identiques (< 0.05%%)");
            sc.AddMessageToLog(logMsg, 0);
        }
        else if (fabs(deltaMethodsPct) < 1.0f)
        {
            logMsg.Format("STATUT : ⚠️ Écart modéré (< 1%%)");
            sc.AddMessageToLog(logMsg, 0);
        }
        else
        {
            logMsg.Format("STATUT : ❌ ÉCART IMPORTANT (>= 1%%) - Gap overnight détecté");
            sc.AddMessageToLog(logMsg, 0);
        }

        logMsg.Format("==========================================");
        sc.AddMessageToLog(logMsg, 0);

        // Instructions pour validation
        logMsg.Format("VALIDATION : Comparez 'Day Change %% (Settlement)' avec :");
        sc.AddMessageToLog(logMsg, 0);

        logMsg.Format("  - CME Group : https://www.cmegroup.com/markets/equities/nasdaq/e-mini-nasdaq-100.html");
        sc.AddMessageToLog(logMsg, 0);

        logMsg.Format("  - TradingView : https://www.tradingview.com/symbols/CME_MINI-NQ1!/");
        sc.AddMessageToLog(logMsg, 0);
    }

    // ========================================================================
    // AFFICHAGE DANS LE TITLE BAR (résumé)
    // ========================================================================

    if (sc.Index == sc.ArraySize - 1)
    {
        SCString titleBarMsg;
        titleBarMsg.Format("Settlement: %.2f%% | SessionOpen: %.2f%% | Δ: %.2f%%",
                          dayChangePct_Settlement,
                          dayChangePct_SessionOpen,
                          deltaMethodsPct);

        sc.GraphName.Format("Test Day Change %% - %s", titleBarMsg.GetChars());
    }
}
