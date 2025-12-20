// === MIA_Dumper_G3_Core.cpp (header inlined - Approach 1) ===
// Utilities previously in "mia_dump_utils.hpp" are embedded below to allow
// single-file remote builds on Sierra Chart.

#include "sierrachart.h"
#ifdef _WIN32
  #include <windows.h>
#endif
#include <time.h>
#include <cmath>
#include <unordered_map>
#include <string>
#include <vector>
#include <algorithm>
using std::fabs;

// ========== UTILITAIRES COMMUNS ==========

// Création du répertoire de sortie
static void EnsureOutDir() {
#ifdef _WIN32
  CreateDirectoryA("D:\\MIA_IA_system", NULL);
#endif
}

// Génération du nom de fichier quotidien par chart et type
static SCString DailyFilenameForChartType(int chartNumber, const char* dataType) {
  time_t now = time(NULL);
  struct tm* lt = localtime(&now);
  int y = lt ? (lt->tm_year + 1900) : 1970;
  int m = lt ? (lt->tm_mon + 1) : 1;
  int d = lt ? lt->tm_mday : 1;
  SCString filename;
  filename.Format("D:\\MIA_IA_system\\chart_%d_%s_%04d%02d%02d.jsonl", 
                  chartNumber, dataType, y, m, d);
  return filename;
}

// Écriture dans le fichier spécialisé
static void WriteToSpecializedFile(int chartNumber, const char* dataType, const SCString& line) {
  EnsureOutDir();
  const SCString filename = DailyFilenameForChartType(chartNumber, dataType);
  FILE* f = fopen(filename.GetChars(), "a");
  if (f) { 
    fprintf(f, "%s\n", line.GetChars()); 
    fclose(f); 
  }
}

// Crée/touche un fichier quotidien vide si besoin
static void TouchDailyFile(int chartNumber, const char* dataType) {
  EnsureOutDir();
  const SCString filename = DailyFilenameForChartType(chartNumber, dataType);
  FILE* f = fopen(filename.GetChars(), "a");
  if (f) fclose(f);
}

// Écriture dans le fichier de debug local UNIQUE
static void WriteToDebugFile(const SCString& debugLine) {
  EnsureOutDir();
  time_t now = time(NULL);
  struct tm* lt = localtime(&now);
  int y = lt ? (lt->tm_year + 1900) : 1970;
  int m = lt ? (lt->tm_mon + 1) : 1;
  int d = lt ? lt->tm_mday : 1;
  
  // UN SEUL FICHIER DE DEBUG PAR JOUR
  SCString debugFilename;
  debugFilename.Format("D:\\MIA_IA_system\\debug_g3_%04d%02d%02d.log", y, m, d);
  
  FILE* f = fopen(debugFilename.GetChars(), "a");
  if (f) { 
    fprintf(f, "%s\n", debugLine.GetChars()); 
    fclose(f); 
  }
}

// Fonction de debug combinée (Sierra + fichier local)
static void DebugLog(SCStudyInterfaceRef& sc, const char* message) {
  // Log dans Sierra Chart
  sc.AddMessageToLog(message, 1);
  
  // Log dans fichier local avec timestamp
  time_t now = time(NULL);
  struct tm* lt = localtime(&now);
  int h = lt ? lt->tm_hour : 0;
  int min = lt ? lt->tm_min : 0;
  int s = lt ? lt->tm_sec : 0;
  
  SCString debugLine;
  debugLine.Format("[%02d:%02d:%02d] %s", h, min, s, message);
  WriteToDebugFile(debugLine);
}

// ========== NIVEAUX DE LOG ==========
enum LogLevel {
    LOG_ERROR = 0,    // Erreurs critiques uniquement
    LOG_KEY = 1,      // Événements importants (flush, erreurs)
    LOG_VERBOSE = 2   // Debug complet (développement)
};

// Helper: filtrage de logs par niveau (0=Errors,1=Key,2=Verbose)
static inline bool ShouldLog(const SCStudyInterfaceRef& sc, int level) {
  int cfg = 0;
  // sc.Input peut ne pas être initialisé très tôt; garde-fou
  if (&sc != nullptr) {
    // Input[29] défini dans SetDefaults
    cfg = sc.Input[29].GetInt();
  }
  return cfg >= level;
}


// ========== DÉDUPLICATION INTELLIGENTE AMÉLIORÉE ==========
// Structure pour la déduplication par (sym, t, i)
struct LastKey { 
  double t = 0.0; // timestamp
  double i = -1;  // bar index
};

// Structures pour la détection de changement d'état
struct LastBasedata {
  double c=0, o=0, h=0, l=0;
  double bidvol=0, askvol=0, v=0;
};

struct LastVWAP {
  double vwap=0, up1=0, dn1=0, up2=0, dn2=0, up3=0, dn3=0;
};

struct LastVVA {
  double vah=0, val=0, vpoc=0, pvah=0, pval=0, ppoc=0;
};

struct LastNBCV {
  double askVolume=0, bidVolume=0, delta=0, totalVolume=0;
  double deltaPct=0, askPct=0, bidPct=0;
  int pressure=0;
};

// Maps de déduplication par symbole
static std::unordered_map<std::string, LastKey> g_LastKeyBySym;
static std::unordered_map<std::string, LastBasedata> g_LastBaseBySym;
static std::unordered_map<std::string, LastVWAP> g_LastVWAPBySym;
static std::unordered_map<std::string, LastVVA> g_LastVVABySym;
static std::unordered_map<std::string, LastNBCV> g_LastNBCVBySym;

// Cache pour Cumulative Delta
struct LastCD { double close=0.0; };
static std::unordered_map<std::string, LastCD> g_LastCDBySym;

// Caches supplémentaires: ATR et Correlation
struct LastATR { double atr=0.0; };
static std::unordered_map<std::string, LastATR> g_LastATRBySym;

struct LastCorr { double cc=0.0; };
static std::unordered_map<std::string, LastCorr> g_LastCorrBySym;

// ========== COALESCE INTRABAR (Option C) + SEQ MODE (Option D) ==========
struct BufPayload {
  SCString json;
  int i = -1;
  double t = 0.0;
  SCString dataType; // Added to store dataType for flush
};

static std::unordered_map<std::string, BufPayload> g_CoalesceBufByKey; // key: sym|type
static std::unordered_map<std::string, uint32_t> g_SeqByKey;           // key: sym|type|i

// ========== MÉTRIQUES DE PERFORMANCE ==========
struct PerformanceMetrics {
    int total_bars_processed = 0;
    int studies_written = 0;
    int quotes_written = 0;
    int trades_written = 0;
    int depth_written = 0;
    double avg_processing_time = 0.0;
    int buffer_size = 0;
    time_t last_update = 0;
    time_t last_metrics_report = 0;
    time_t last_flush = 0;
    int bars_since_flush = 0;
};

static PerformanceMetrics g_metrics;

// ========== MÉTRIQUES DE QUALITÉ DES DONNÉES ==========
struct DataQualityMetrics {
    int duplicate_detected = 0;
    int invalid_values = 0;
    int missing_studies = 0;
    int timestamp_anomalies = 0;
};

static DataQualityMetrics g_quality;

static inline std::string MakeBufKey(int chart, const char* sym, const char* type) {
  return std::to_string(chart) + "|" + std::string(sym) + "|" + std::string(type);
}

static inline std::string MakeSeqKey(int chart, const char* sym, const char* type, int barIndex) {
  return std::to_string(chart) + "|" + std::string(sym) + "|" + std::string(type) + "|" + std::to_string(barIndex);
}

static inline SCString InjectSeqField(const SCString& line, uint32_t seq) {
  // Insère \"seq\":<n> avant la dernière '}'
  SCString out;
  int len = line.GetLength();
  if (len > 0) {
    out.Format("%.*s,\"seq\":%u}", len - 1, line.GetChars(), seq);
  } else {
    out.Format("{\"seq\":%u}", seq);
  }
  return out;
}

// ========== FONCTIONS DE FLUSH AUTOMATIQUE ==========
static void FlushAllBuffers(SCStudyInterfaceRef& sc, const char* reason) {
  if (ShouldLog(sc, LOG_KEY)) {
    SCString flushMsg;
    flushMsg.Format("FLUSH: %s - Flushing %d buffers", reason, (int)g_CoalesceBufByKey.size());
    DebugLog(sc, flushMsg.GetChars());
  }
  
  for (auto it = g_CoalesceBufByKey.begin(); it != g_CoalesceBufByKey.end(); ) {
    WriteToSpecializedFile(sc.ChartNumber, it->second.dataType.GetChars(), it->second.json);
    it = g_CoalesceBufByKey.erase(it);
  }
  g_metrics.bars_since_flush = 0;
}

static void UpdateMetrics(SCStudyInterfaceRef& sc, const char* operation) {
  g_metrics.total_bars_processed++;
  g_metrics.buffer_size = g_CoalesceBufByKey.size();
  g_metrics.last_update = time(NULL);
  
  if (strcmp(operation, "study") == 0) g_metrics.studies_written++;
  else if (strcmp(operation, "quote") == 0) g_metrics.quotes_written++;
  else if (strcmp(operation, "trade") == 0) g_metrics.trades_written++;
  else if (strcmp(operation, "depth") == 0) g_metrics.depth_written++;
}

static void CheckAutoFlush(SCStudyInterfaceRef& sc) {
  time_t now = time(NULL);
  
  // Flush temporel (toutes les 30 secondes)
  if (now - g_metrics.last_flush > 30) {
    FlushAllBuffers(sc, "AUTO-TIME");
    g_metrics.last_flush = now;
  }
  
  // Flush par nombre de barres (toutes les 10 barres)
  g_metrics.bars_since_flush++;
  if (g_metrics.bars_since_flush >= 10) {
    FlushAllBuffers(sc, "AUTO-BAR");
    g_metrics.bars_since_flush = 0;
  }
  
  // Rapport de performance (toutes les 5 minutes)
  if (ShouldLog(sc, LOG_KEY) && (now - g_metrics.last_metrics_report > 300)) {
    SCString perfMsg1;
    perfMsg1.Format("PERF: Bars=%d, Studies=%d, Quotes=%d, Trades=%d, Depth=%d", 
                   g_metrics.total_bars_processed,
                   g_metrics.studies_written,
                   g_metrics.quotes_written,
                   g_metrics.trades_written,
                   g_metrics.depth_written);
    DebugLog(sc, perfMsg1.GetChars());
    
    SCString perfMsg2;
    perfMsg2.Format("PERF: BufferSize=%d, Quality: Invalid=%d, Missing=%d", 
                   g_metrics.buffer_size,
                   g_quality.invalid_values,
                   g_quality.missing_studies);
    DebugLog(sc, perfMsg2.GetChars());
    
    g_metrics.last_metrics_report = now;
  }
}

// ========== FILTRAGE DES VOLUMES ==========
static double CapVolume(double volume, double median, double iqr, double multiplier) {
  if (multiplier <= 1.0) return volume; // Pas de filtrage
  
  double threshold = median + (multiplier * iqr);
  if (volume > threshold) {
    return threshold; // Cap à la limite
  }
  return volume;
}

// ========== DÉTECTION DE CHANGEMENT ==========
static inline bool has_changed(double a, double b, double eps=1e-9) {
  return fabs(a-b) > eps;
}

// Fonction de déduplication améliorée
static bool ShouldWriteData(const char* symbol, double timestamp, double barIndex) {
  std::string symKey = std::string(symbol);
  LastKey& lk = g_LastKeyBySym[symKey];
  
  // Vérifier si (sym, t, i) identique
  bool same_ti = (fabs(lk.t - timestamp) < 1e-9) && (fabs(lk.i - barIndex) < 1e-9);
  
  // Mettre à jour la clé
  lk.t = timestamp;
  lk.i = barIndex;
  
  return !same_ti; // Écrire si différent
}

// --- AJOUTER : déduplication par (sym|type, t, i)
static bool ShouldWriteDataWithType(const char* symbol, const char* dataType, double timestamp, double barIndex) {
  static std::unordered_map<std::string, LastKey> s_LastKeyBySymType;
  std::string key = std::string(symbol) + "|" + std::string(dataType);
  LastKey& lk = s_LastKeyBySymType[key];
  bool same_ti = (fabs(lk.t - timestamp) < 1e-9) && (fabs(lk.i - barIndex) < 1e-9);
  lk.t = timestamp;
  lk.i = barIndex;
  return !same_ti; // Écrire si différent
}

// Anti-duplication simple par (chart, type, key)
static void WriteIfChanged(int chartNumber, const char* dataType, const std::string& key, const SCString& line) {
  static std::unordered_map<std::string, std::string> s_last_by_key;
  auto it = s_last_by_key.find(key);
  const std::string current = std::string(line.GetChars());
  if (it != s_last_by_key.end() && it->second == current) {
    return; // identique, on n'écrit pas
  }
  WriteToSpecializedFile(chartNumber, dataType, line);
  s_last_by_key[key] = current;
}

// ========== NORMALISATION DES PRIX ==========
inline double NormalizePx(const SCStudyInterfaceRef& sc, double raw)
{
  // 1) Dé-multiplier si besoin
  const double mult = (sc.RealTimePriceMultiplier != 0.0 ? sc.RealTimePriceMultiplier : 1.0);
  double px = raw / mult;

  // 2) Correction d'échelle avant arrondi (certains flux arrivent x100)
  if (px > 10000.0) px /= 100.0;

  // 3) Arrondi au tick
  px = sc.RoundToTickSize(px, sc.TickSize);

  // 4) Correction d'échelle résiduelle puis arrondi final (sécurité)
  if (px > 10000.0) px /= 100.0;
  px = sc.RoundToTickSize(px, sc.TickSize);
  return px;
}

// ========== HELPERS D'ACCÈS AUX STUDIES ==========

// Helper pour résoudre automatiquement un Study ID par nom
static int ResolveStudyID(SCStudyInterfaceRef& sc, int chartNumber, const char* studyName, int fallbackID = 0) {
  int id = sc.GetStudyIDByName(chartNumber, studyName, 0);
  if (id <= 0 && fallbackID > 0) {
    id = fallbackID;
  }
  return id;
}

// Helper pour lire un subgraph avec validation
static bool ReadSubgraph(SCStudyInterfaceRef& sc, int studyID, int subgraphIndex, SCFloatArray& array, int chartNumber = -1) {
  if (chartNumber > 0) {
    sc.GetStudyArrayFromChartUsingID(chartNumber, studyID, subgraphIndex, array);
    return array.GetArraySize() > 0;
  } else {
    sc.GetStudyArrayUsingID(studyID, subgraphIndex, array);
    return array.GetArraySize() > 0;
  }
}

// Helper pour valider qu'une étude a des données valides
static bool ValidateStudyData(const SCFloatArray& array, int index) {
  return array.GetArraySize() > index && !std::isnan(array[index]) && !std::isinf(array[index]);
}

// Helper pour déboguer les Study IDs et subgraphs
static void DebugStudyInfo(SCStudyInterfaceRef& sc, int studyID, const char* studyName, int subgraphIndex, const char* subgraphName) {
  if (studyID <= 0) {
    SCString msg;
    msg.Format("DEBUG: %s - Study ID %d INVALID", studyName, studyID);
    sc.AddMessageToLog(msg, 1);
    return;
  }
  
  SCFloatArray testArray;
  bool success = ReadSubgraph(sc, studyID, subgraphIndex, testArray);
  
  SCString msg;
  msg.Format("DEBUG: %s - ID=%d, SG%d(%s) - Success=%d, Size=%d", 
             studyName, studyID, subgraphIndex, subgraphName, success, testArray.GetArraySize());
  sc.AddMessageToLog(msg, 1);
  
  if (success && testArray.GetArraySize() > 0) {
    int lastIndex = testArray.GetArraySize() - 1;
    double lastValue = testArray[lastIndex];
    SCString valMsg;
    valMsg.Format("DEBUG: %s - Last value[%d]=%.6f, Valid=%d", 
                  studyName, lastIndex, lastValue, ValidateStudyData(testArray, lastIndex));
    sc.AddMessageToLog(valMsg, 1);
  }
}

// ========== DÉTECTION DE SUPPORT SEQUENCE ==========
static void DetectSequenceSupport(const c_SCTimeAndSalesArray& TnS, bool& g_UseSeq)
{
    // Cherche un enregistrement avec Sequence > 0 (du plus récent au plus ancien)
    for (int i = (int)TnS.Size() - 1; i >= 0 && i >= (int)TnS.Size() - 50; --i)
    {
        if (TnS[i].Sequence > 0)
        {
            g_UseSeq = true;
            break;
        }
    }
}

// ========== CONSTANTES DE MAPPING ==========

// VWAP Subgraphs (selon le mapping standard)
#define VWAP_SG_MAIN 1
#define VWAP_SG_UP1  2
#define VWAP_SG_DN1  3
#define VWAP_SG_UP2  4
#define VWAP_SG_DN2  5
#define VWAP_SG_UP3  6
#define VWAP_SG_DN3  7

// VVA Subgraphs (Volume Value Area) — indexation 0-based
#define VVA_SG_POC 0
#define VVA_SG_VAH 1
#define VVA_SG_VAL 2

// NBCV Subgraphs (Numbers Bars Calculated Values) — mapping confirmé
// (Ask=5, Bid=6, Delta=0, Trades=11, CumDelta=9, TotalVol=12, Delta%=10, Ask%=16, Bid%=17)
#define NBCV_SG_DELTA         0
#define NBCV_SG_ASK_VOLUME    5
#define NBCV_SG_BID_VOLUME    6
#define NBCV_SG_TRADES        11
#define NBCV_SG_CUMULATIVE     9
#define NBCV_SG_TOTAL_VOLUME  12
#define NBCV_SG_DELTA_PCT     10
#define NBCV_SG_ASK_PCT       16
#define NBCV_SG_BID_PCT       17

// VIX Subgraph
#define VIX_SG_LAST 4

// MenthorQ Subgraphs
#define MENTHORQ_GAMMA_SG_COUNT 19
#define MENTHORQ_BLIND_SG_COUNT 9
#define MENTHORQ_SWING_SG_COUNT 9

// =======================================================================
// ===============    STUDY ENTRYPOINT (G3 CORE)    =======================
// =======================================================================

SCDLLName("MIA_Dumper_G3_Core")

// Dumper spécialisé pour Chart 3 (1 minute)
// Collecte UNIQUEMENT les données natives du Chart 3
// Sorties spécialisées : basedata, depth, quote, trade, vwap, vva, pvwap, nbcv

SCSFExport scsf_MIA_Dumper_G3_Core(SCStudyInterfaceRef sc)
{
  if (sc.SetDefaults)
  {
    sc.GraphName = "MIA Dumper G3 Core";
    sc.StudyDescription = "Collecte spécialisée Chart 3 - Données natives uniquement";
    sc.AutoLoop = 0;
    sc.UpdateAlways = 1;
    sc.UsesMarketDepthData = 1;
    sc.MaintainVolumeAtPriceData = 1;
    sc.MaintainAdditionalChartDataArrays = 1;
    sc.CalculationPrecedence = LOW_PREC_LEVEL;

    // --- Inputs BaseData + DOM + T&S ---
    sc.Input[0].Name = "Max DOM Levels";
    sc.Input[0].SetInt(20);
    sc.Input[1].Name = "Max T&S Entries";
    sc.Input[1].SetInt(10);

    // --- Inputs VWAP ---
    sc.Input[2].Name = "Export VWAP (0/1)";
    sc.Input[2].SetInt(1);
    sc.Input[3].Name = "VWAP Study ID (0=auto)";
    sc.Input[3].SetInt(22); // Study ID 22 pour Chart 3
    sc.Input[4].Name = "VWAP Bands Count (0..3)";
    sc.Input[4].SetInt(3); // 3 bandes par défaut

    // --- Inputs VVA ---
    sc.Input[5].Name = "Export VVA (0/1)";
    sc.Input[5].SetInt(1);
    sc.Input[6].Name = "VVA Current Study ID";
    sc.Input[6].SetInt(1); // Study ID 1 pour VVA Current
    sc.Input[7].Name = "VVA Previous Study ID";
    sc.Input[7].SetInt(8); // Study ID 8 pour VVA Previous (test)

    // --- Inputs PVWAP ---
    sc.Input[8].Name = "Export PVWAP (0/1)";
    sc.Input[8].SetInt(1);
    sc.Input[9].Name = "PVWAP Bands Count (0..2)";
    sc.Input[9].SetInt(2);

    // --- Inputs NBCV ---
    sc.Input[10].Name = "Export NBCV (0/1)";
    sc.Input[10].SetInt(1);
    sc.Input[11].Name = "NBCV Study ID";
    sc.Input[11].SetInt(33); // ID 33 pour Graph 3

    // --- Inputs Time & Sales ---
    sc.Input[12].Name = "Export T&S (0/1)";
    sc.Input[12].SetInt(1);
    sc.Input[13].Name = "Export Quotes (0/1)";
    sc.Input[13].SetInt(1);

    // --- Inputs Cumulative Delta ---
    sc.Input[14].Name = "Export Cumulative Delta (0/1)";
    sc.Input[14].SetInt(1);
    sc.Input[15].Name = "Cumulative Delta Study ID";
    sc.Input[15].SetInt(32);
    sc.Input[16].Name = "Cumulative Delta Subgraph Index";
    sc.Input[16].SetInt(3);

    // --- Inputs Volume Filtering ---
    sc.Input[17].Name = "Enable Volume Filtering (0/1)";
    sc.Input[17].SetInt(1);
    sc.Input[18].Name = "Volume Cap Multiplier (1.0=off, 6.0=IQR)";
    sc.Input[18].SetFloat(6.0);

    // ---- Inputs pour la pression OrderFlow (NBCV) ----
    sc.Input[19].Name = "OF: Min Total Volume";
    sc.Input[19].SetFloat(75.0);        // Optimisé pour intraday (75 contrats)

    sc.Input[20].Name = "OF: Min |Delta Ratio|";
    sc.Input[20].SetFloat(0.075);        // 7.5% (plus sensible)

    sc.Input[21].Name = "OF: Min Ask/Bid or Bid/Ask Ratio";
    sc.Input[21].SetFloat(1.25);         // 1.25x (plus sensible)

    // --- Inputs ATR ---
    sc.Input[22].Name = "Export ATR (0/1)";
    sc.Input[22].SetInt(1);
    sc.Input[23].Name = "ATR Study ID (0=auto)";
    sc.Input[23].SetInt(45);
    sc.Input[24].Name = "ATR Subgraph Index";
    sc.Input[24].SetInt(0);

    // --- Inputs Correlation ---
    sc.Input[25].Name = "Export Correlation (0/1)";
    sc.Input[25].SetInt(0);
    sc.Input[26].Name = "Correlation Study ID (0=auto)";
    sc.Input[26].SetInt(46);
    sc.Input[27].Name = "Correlation Subgraph Index";
    sc.Input[27].SetInt(0);

    // --- Inputs Prod/Debug ---
    sc.Input[28].Name = "Intrabar Seq Mode (0=Off,1=On)";
    sc.Input[28].SetInt(0);
    sc.Input[29].Name = "Prod Log Level (0=Errors,1=Key,2=Verbose)";
    sc.Input[29].SetInt(0);

    return;
  }

  if (sc.ServerConnectionState != SCS_CONNECTED) return;

  // DEBUG: Log startup
  static bool startup_logged = false;
  if (!startup_logged) {
    SCString startupMsg;
    startupMsg.Format("DEBUG G3: MIA_Dumper_G3_Core STARTED - Chart=%d, Symbol=%s, ArraySize=%d", 
                     sc.ChartNumber, sc.Symbol.GetChars(), sc.ArraySize);
    if (ShouldLog(sc, 1)) DebugLog(sc, startupMsg.GetChars());
    // Garantir l'existence des fichiers journaliers attendus
    TouchDailyFile(sc.ChartNumber, "basedata");
    TouchDailyFile(sc.ChartNumber, "depth");
    TouchDailyFile(sc.ChartNumber, "quote");
    TouchDailyFile(sc.ChartNumber, "trade");
    TouchDailyFile(sc.ChartNumber, "pvwap");
    TouchDailyFile(sc.ChartNumber, "vwap");
    TouchDailyFile(sc.ChartNumber, "vva");
    TouchDailyFile(sc.ChartNumber, "nbcv");
    TouchDailyFile(sc.ChartNumber, "cumulative_delta");
    TouchDailyFile(sc.ChartNumber, "atr");
    // Correlation désactivée par défaut sur G3: pas de fichier journalier
    // TouchDailyFile(sc.ChartNumber, "correlation");
    startup_logged = true;
  }

  const int max_levels = sc.Input[0].GetInt();
  const int max_ts = sc.Input[1].GetInt();

  // ========== VARIABLES STATIQUES ANTI-DOUBLONS T&S ==========
  static int      g_LastTsIndex = 0;
  static uint32_t g_LastSeq     = 0;
  static bool     g_UseSeq      = false;

  // ========== TRAITEMENT D'UN ENREGISTREMENT T&S ==========
  auto ProcessTS = [&](const s_TimeAndSales& ts) -> void
  {
      const double tsec = ts.DateTime.GetAsDouble();
      const int tt = (int)ts.Type;

      // Nouvelle classification:
      // - tt=6 (SC_TS_BIDASKVALUES) => quote uniquement
      // - tt=1 (SC_TS_BID) et tt=2 (SC_TS_ASK) => TRADE si price/volume valides
      const bool isQuote = (tt == SC_TS_BIDASKVALUES);

      if (isQuote)
      {
          // QUOTE (BBO) uniquement
          if (ts.Bid > 0 && ts.Ask > 0)
          {
              const double bid = NormalizePx(sc, ts.Bid);
              const double ask = NormalizePx(sc, ts.Ask);
              SCString j;
              j.Format(R"({"t":%.6f,"sym":"%s","type":"quote","kind":"BIDASK","bid":%.8f,"ask":%.8f,"bq":%d,"aq":%d,"seq":%u,"chart":%d})",
                       tsec, sc.Symbol.GetChars(), bid, ask, ts.BidSize, ts.AskSize, ts.Sequence, sc.ChartNumber);
              WriteToSpecializedFile(sc.ChartNumber, "quote", j);
          }
          // IMPORTANT: ne pas convertir les quotes en trades
          return;
      }

      // TRADE: pour tous les événements non-quote
      if (ts.Price > 0 && ts.Volume > 0)
      {
          const double px  = NormalizePx(sc, ts.Price);
          const double bid = NormalizePx(sc, sc.Bid);
          const double ask = NormalizePx(sc, sc.Ask);
          const double tol = sc.TickSize * 0.51; // tolérance demi-tick

          // Inférence de l'agresseur
          const char* aggr = "TRADE"; // par défaut
          if (tt == SC_TS_ASK)      aggr = "BUY";   // à l'ASK
          else if (tt == SC_TS_BID) aggr = "SELL";  // au BID
          else {
              // fallback par rapprochement au BBO courant
              if (fabs(px - ask) <= tol) aggr = "BUY";
              else if (fabs(px - bid) <= tol) aggr = "SELL";
          }

          // Ecriture trade détaillée
          SCString j;
          j.Format(R"({"t":%.6f,"sym":"%s","type":"trade","side":"%s","px":%.8f,"vol":%d,"seq":%u,"tt":%d,"chart":%d})",
                   tsec, sc.Symbol.GetChars(), aggr, px, ts.Volume, ts.Sequence, tt, sc.ChartNumber);
          WriteToSpecializedFile(sc.ChartNumber, "trade", j);

          // Résumé périodique BUY/SELL (cumulatif)
          static unsigned long long s_buyTrades = 0ULL, s_sellTrades = 0ULL;
          static unsigned long long s_buyVol = 0ULL,    s_sellVol  = 0ULL;
          if (aggr == std::string("BUY")) { s_buyTrades++; s_buyVol += (unsigned long long)ts.Volume; }
          else if (aggr == std::string("SELL")) { s_sellTrades++; s_sellVol += (unsigned long long)ts.Volume; }

          const unsigned long long totalTrades = s_buyTrades + s_sellTrades;
          if ((totalTrades % 256ULL) == 0ULL) {
              SCString s;
              s.Format(R"({"t":%.6f,"sym":"%s","type":"trade_summary","buy_trades":%llu,"sell_trades":%llu,"buy_vol":%llu,"sell_vol":%llu,"chart":%d})",
                       tsec, sc.Symbol.GetChars(), (unsigned long long)s_buyTrades, (unsigned long long)s_sellTrades,
                       (unsigned long long)s_buyVol, (unsigned long long)s_sellVol, sc.ChartNumber);
              WriteToSpecializedFile(sc.ChartNumber, "trade_summary", s);
          }
      }
  };

  // ---- BaseData (avec déduplication améliorée) ----
  if (sc.ArraySize > 0) {
    const int i = sc.ArraySize - 1;
    const double t = sc.BaseDateTimeIn[i].GetAsDouble();
    const double barIndex = (double)i;
    const char* symbol = sc.Symbol.GetChars();
    
    // Récupérer les valeurs actuelles
    const double o = sc.BaseDataIn[SC_OPEN][i];
    const double h = sc.BaseDataIn[SC_HIGH][i];
    const double l = sc.BaseDataIn[SC_LOW][i];
    const double c = sc.BaseDataIn[SC_LAST][i];
    double v = sc.BaseDataIn[SC_VOLUME][i];
    double bvol = sc.BaseDataIn[SC_BIDVOL][i];
    double avol = sc.BaseDataIn[SC_ASKVOL][i];

    // Appliquer le filtrage des volumes si activé
    if (sc.Input[17].GetInt() != 0) {
      // Recalcul dynamique des stats (fenêtre 100 barres)
      static double volume_median = 0.0;
      static double volume_iqr = 0.0;
      if (sc.ArraySize >= 10) {
        std::vector<double> volumes;
        int start = ((int)sc.ArraySize - 100 > 0) ? (int)sc.ArraySize - 100 : 0;
        volumes.reserve(sc.ArraySize - start);
        for (int j = start; j < sc.ArraySize; ++j) {
          volumes.push_back(sc.BaseDataIn[SC_VOLUME][j]);
        }
        std::sort(volumes.begin(), volumes.end());
        volume_median = volumes[volumes.size() / 2];
        double q1 = volumes[volumes.size() / 4];
        double q3 = volumes[3 * volumes.size() / 4];
        volume_iqr = q3 - q1;
      }

      if (volume_iqr > 0) {
        double multiplier = sc.Input[18].GetFloat();
        v = CapVolume(v, volume_median, volume_iqr, multiplier);
        bvol = CapVolume(bvol, volume_median, volume_iqr, multiplier);
        avol = CapVolume(avol, volume_median, volume_iqr, multiplier);
      }
    }

    // Détection de changement d'état
    std::string symKey = std::string(symbol);
    LastBasedata& lb = g_LastBaseBySym[symKey];
    bool payload_changed = 
      has_changed(c, lb.c) || has_changed(o, lb.o) || has_changed(h, lb.h) || has_changed(l, lb.l) ||
      has_changed(bvol, lb.bidvol) || has_changed(avol, lb.askvol) || has_changed(v, lb.v);

    // Vérifier clôture de barre
    int barStatus = sc.GetBarHasClosedStatus(i);
    bool bar_closed = (barStatus == BHCS_BAR_HAS_CLOSED);

    // Déduplication par type
    bool should_write_type = ShouldWriteDataWithType(symbol, "basedata", t, barIndex);

    // Écrire si : changement de payload OU clôture de barre OU nouvelle clé (typée)
    if (payload_changed || bar_closed || should_write_type) {
      SCString j;
      j.Format("{\"t\":%.6f,\"sym\":\"%s\",\"type\":\"basedata\",\"i\":%d,\"o\":%.8f,\"h\":%.8f,\"l\":%.8f,\"c\":%.8f,\"v\":%.0f,\"bidvol\":%.0f,\"askvol\":%.0f,\"chart\":%d}",
        t, symbol, i, o, h, l, c, v, bvol, avol, sc.ChartNumber);
      WriteToSpecializedFile(sc.ChartNumber, "basedata", j);
      
      // Mettre à jour les dernières valeurs
      lb.c = c; lb.o = o; lb.h = h; lb.l = l; 
      lb.bidvol = bvol; lb.askvol = avol; lb.v = v;
    }
  }

  // ---- VWAP export (avec déduplication améliorée) ----
  if (sc.Input[2].GetInt() != 0 && sc.ArraySize > 0) {
    static int vwapID = -2; // -2: à résoudre, -1: introuvable, >0: OK
    const int i = sc.ArraySize - 1;
    const double t = sc.BaseDateTimeIn[i].GetAsDouble();
    const double barIndex = (double)i;
    const char* symbol = sc.Symbol.GetChars();
    
    // DEBUG: Log VWAP attempt
    SCString debugMsg;
    debugMsg.Format("DEBUG G3: VWAP attempt - Input[2]=%d, ArraySize=%d, i=%d, vwapID=%d", 
                   sc.Input[2].GetInt(), sc.ArraySize, i, vwapID);
    if (ShouldLog(sc, 2)) DebugLog(sc, debugMsg.GetChars());
  
    if (vwapID == -2) {
      int cand[6]; // Augmenter le nombre de candidats
      cand[0] = sc.Input[3].GetInt(); // ID forcé
      cand[1] = ResolveStudyID(sc, sc.ChartNumber, "Volume Weighted Average Price", 0);
      cand[2] = ResolveStudyID(sc, sc.ChartNumber, "VWAP (Volume Weighted Average Price)", 0);
      cand[3] = ResolveStudyID(sc, sc.ChartNumber, "VWAP", 0);
      cand[4] = ResolveStudyID(sc, sc.ChartNumber, "Volume Weighted Average", 0);
      cand[5] = 22; // ID par défaut pour Chart 3
      
      // DEBUG: Log candidate IDs
      SCString debugMsg2;
      debugMsg2.Format("DEBUG G3: VWAP candidates - [0]=%d, [1]=%d, [2]=%d, [3]=%d, [4]=%d, [5]=%d", 
                      cand[0], cand[1], cand[2], cand[3], cand[4], cand[5]);
      if (ShouldLog(sc, 2)) DebugLog(sc, debugMsg2.GetChars());
      
      // DEBUG: Test each candidate in detail
      for (int k = 0; k < 6; k++) {
        if (cand[k] > 0) {
          SCString candName;
          candName.Format("VWAP_CAND_%d", k);
          if (ShouldLog(sc, 2)) DebugStudyInfo(sc, cand[k], candName.GetChars(), VWAP_SG_MAIN, "MAIN");
        }
      }
  
      vwapID = -1;
      for (int k = 0; k < 6; ++k) {
        if (cand[k] > 0) {
          SCFloatArray test;
          if (ReadSubgraph(sc, cand[k], VWAP_SG_MAIN, test)) {
            if (ValidateStudyData(test, i)) { 
              vwapID = cand[k];
              SCString debugMsg3;
              debugMsg3.Format("DEBUG G3: VWAP found - ID=%d, ArraySize=%d", vwapID, test.GetArraySize());
              if (ShouldLog(sc, 1)) DebugLog(sc, debugMsg3.GetChars());
              break;
            }
          }
        }
      }
      
      if (vwapID == -1) {
        if (ShouldLog(sc, 1)) DebugLog(sc, "DEBUG G3: VWAP NOT FOUND - No valid study data");
      }
    }
  
    if (vwapID > 0) {
      SCFloatArray VWAP, UP1, DN1, UP2, DN2, UP3, DN3;
      ReadSubgraph(sc, vwapID, VWAP_SG_MAIN, VWAP);
      
      // DEBUG: Log VWAP data reading
      SCString debugMsg4;
      debugMsg4.Format("DEBUG G3: VWAP data read - ArraySize=%d, Value[%d]=%.6f", 
                      VWAP.GetArraySize(), i, (VWAP.GetArraySize() > i) ? VWAP[i] : -999.0);
      if (ShouldLog(sc, LOG_VERBOSE)) DebugLog(sc, debugMsg4.GetChars());
      
      int bands = sc.Input[4].GetInt();
      if (bands >= 1) {
        ReadSubgraph(sc, vwapID, VWAP_SG_UP1, UP1);
        ReadSubgraph(sc, vwapID, VWAP_SG_DN1, DN1);
      }
      if (bands >= 2) {
        ReadSubgraph(sc, vwapID, VWAP_SG_UP2, UP2);
        ReadSubgraph(sc, vwapID, VWAP_SG_DN2, DN2);
      }
      if (bands >= 3) {
        ReadSubgraph(sc, vwapID, VWAP_SG_UP3, UP3);
        ReadSubgraph(sc, vwapID, VWAP_SG_DN3, DN3);
      }

      if (ValidateStudyData(VWAP, i)) {
        if (ShouldLog(sc, LOG_VERBOSE)) DebugLog(sc, "DEBUG G3: VWAP validation PASSED");
        // Récupérer les valeurs actuelles
        double v   = NormalizePx(sc, VWAP[i]);
        double up1 = (ValidateStudyData(UP1, i) ? NormalizePx(sc, UP1[i]) : 0);
        double dn1 = (ValidateStudyData(DN1, i) ? NormalizePx(sc, DN1[i]) : 0);
        double up2 = (ValidateStudyData(UP2, i) ? NormalizePx(sc, UP2[i]) : 0);
        double dn2 = (ValidateStudyData(DN2, i) ? NormalizePx(sc, DN2[i]) : 0);
        double up3 = (ValidateStudyData(UP3, i) ? NormalizePx(sc, UP3[i]) : 0);
        double dn3 = (ValidateStudyData(DN3, i) ? NormalizePx(sc, DN3[i]) : 0);

        // Garde-fou: corriger inversion éventuelle des bandes et forcer l'ordre
        auto fix_band = [&](double& up, double& dn, double base){
          if (up < base && dn > base) {
            double tmp = up; up = dn; dn = tmp;
          }
        };
        fix_band(up1, dn1, v);
        fix_band(up2, dn2, v);
        fix_band(up3, dn3, v);

        // Validation de qualité des données VWAP
        if (v < 0 || v > 10000) {
          g_quality.invalid_values++;
          if (ShouldLog(sc, LOG_ERROR)) {
            SCString qualityMsg;
            qualityMsg.Format("QUALITY: Invalid VWAP value: %.2f", v);
            DebugLog(sc, qualityMsg.GetChars());
          }
        }

        // Forcer ordre monotone: up1 <= up2 <= up3 et dn1 >= dn2 >= dn3
        if (up2 < up1) { double tmp = up1; up1 = up2; up2 = tmp; }
        if (up3 < up2) { double tmp = up2; up2 = up3; up3 = tmp; }
        if (dn2 > dn1) { double tmp = dn1; dn1 = dn2; dn2 = tmp; }
        if (dn3 > dn2) { double tmp = dn2; dn2 = dn3; dn3 = tmp; }

        // Détection de changement d'état
        std::string symKey = std::string(symbol);
        LastVWAP& lv = g_LastVWAPBySym[symKey];
        bool payload_changed = 
          has_changed(v, lv.vwap) || has_changed(up1, lv.up1) || has_changed(dn1, lv.dn1) ||
          has_changed(up2, lv.up2) || has_changed(dn2, lv.dn2) || has_changed(up3, lv.up3) || has_changed(dn3, lv.dn3);

        // Vérifier clôture de barre
        int barStatus = sc.GetBarHasClosedStatus(i);
        bool bar_closed = (barStatus == BHCS_BAR_HAS_CLOSED);

        // Déduplication par type
        bool should_write_type = ShouldWriteDataWithType(symbol, "vwap", t, barIndex);

        // Toujours bufferiser en mode coalesce (sinon seq)
        SCString j;
        j.Format("{\"t\":%.6f,\"sym\":\"%s\",\"type\":\"vwap\",\"src\":\"study\",\"i\":%d,\"v\":%.8f,\"up1\":%.8f,\"dn1\":%.8f,\"up2\":%.8f,\"dn2\":%.8f,\"up3\":%.8f,\"dn3\":%.8f,\"chart\":%d}",
                 t, symbol, i, v, up1, dn1, up2, dn2, up3, dn3, sc.ChartNumber);

        const int seqMode = sc.Input[28].GetInt();
        const char* dtype = "vwap";
        std::string key = MakeBufKey(sc.ChartNumber, symbol, dtype);

        if (seqMode == 1) {
          uint32_t seq = ++g_SeqByKey[MakeSeqKey(sc.ChartNumber, symbol, dtype, i)];
          SCString withSeq = InjectSeqField(j, seq);
          WriteToSpecializedFile(sc.ChartNumber, dtype, withSeq);
        } else {
          if (!bar_closed) {
            BufPayload& slot = g_CoalesceBufByKey[key];
            if (slot.i >= 0 && slot.i != i) {
              WriteToSpecializedFile(sc.ChartNumber, dtype, slot.json);
            }
            slot.json = j; slot.i = i; slot.t = t; slot.dataType = dtype; slot.dataType = dtype;
          } else {
            auto itbuf = g_CoalesceBufByKey.find(key);
            if (itbuf != g_CoalesceBufByKey.end()) {
              WriteToSpecializedFile(sc.ChartNumber, dtype, itbuf->second.json);
              g_CoalesceBufByKey.erase(itbuf);
            } else {
              WriteToSpecializedFile(sc.ChartNumber, dtype, j);
            }
          }
        }

        // Mettre à jour les dernières valeurs
        lv.vwap = v; lv.up1 = up1; lv.dn1 = dn1; lv.up2 = up2; lv.dn2 = dn2; lv.up3 = up3; lv.dn3 = dn3;
      }
    }
  }

  // ========== VVA (Volume Value Area Lines) - avec déduplication améliorée ==========
  if (sc.Input[5].GetInt() != 0 && sc.ArraySize > 0)
  {
    const int i = sc.ArraySize - 1;
    const double t = sc.BaseDateTimeIn[i].GetAsDouble();
    const double barIndex = (double)i;
    const char* symbol = sc.Symbol.GetChars();
    
    // DEBUG: Log VVA attempt
    SCString debugMsg;
    debugMsg.Format("DEBUG G3: VVA attempt - Input[5]=%d, ArraySize=%d, i=%d", 
                   sc.Input[5].GetInt(), sc.ArraySize, i);
    if (ShouldLog(sc, 2)) DebugLog(sc, debugMsg.GetChars());

    int id_curr = sc.Input[6].GetInt();
    int id_prev = sc.Input[7].GetInt();
    
    // AMÉLIORATION: Résolution automatique des Study IDs VVA
    if (id_curr <= 0) {
      // Essayer de résoudre automatiquement VVA Current
      int vva_candidates[] = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10};
      for (int k = 0; k < 10; k++) {
        if (vva_candidates[k] > 0) {
          SCFloatArray test;
          if (ReadSubgraph(sc, vva_candidates[k], VVA_SG_POC, test)) {
            if (ValidateStudyData(test, i)) {
              id_curr = vva_candidates[k];
              SCString debugMsg;
              debugMsg.Format("DEBUG G3: VVA Current auto-resolved to ID=%d", id_curr);
              if (ShouldLog(sc, 1)) DebugLog(sc, debugMsg.GetChars());
              break;
            }
          }
        }
      }
    }
    
    if (id_prev <= 0) {
      // Essayer de résoudre automatiquement VVA Previous
      int vva_prev_candidates[] = {8, 9, 10, 11, 12, 13, 14, 15, 16, 17};
      for (int k = 0; k < 10; k++) {
        if (vva_prev_candidates[k] > 0 && vva_prev_candidates[k] != id_curr) {
          SCFloatArray test;
          if (ReadSubgraph(sc, vva_prev_candidates[k], VVA_SG_POC, test)) {
            if (ValidateStudyData(test, i)) {
              id_prev = vva_prev_candidates[k];
              SCString debugMsg;
              if (ShouldLog(sc, LOG_KEY)) {
                debugMsg.Format("DEBUG G3: VVA Previous auto-resolved to ID=%d", id_prev);
                DebugLog(sc, debugMsg.GetChars());
              }
              break;
            }
          }
        }
      }
    }
    
    // DEBUG: Test VVA Study IDs
    DebugStudyInfo(sc, id_curr, "VVA_CURRENT", VVA_SG_POC, "POC");
    DebugStudyInfo(sc, id_prev, "VVA_PREVIOUS", VVA_SG_POC, "POC");

    auto read_vva = [&](int id, double& vah, double& val, double& vpoc)
    {
      vah = val = vpoc = 0.0;
      if (id <= 0) return;

      SCFloatArray SG1, SG2, SG3;  // 0=POC, 1=VAH, 2=VAL
      ReadSubgraph(sc, id, VVA_SG_POC, SG1);  // POC = SG 0
      ReadSubgraph(sc, id, VVA_SG_VAH, SG2);  // VAH = SG 1
      ReadSubgraph(sc, id, VVA_SG_VAL, SG3);  // VAL = SG 2

      if (ValidateStudyData(SG1, i)) vpoc = NormalizePx(sc, SG1[i]);
      if (ValidateStudyData(SG2, i)) vah  = NormalizePx(sc, SG2[i]);
      if (ValidateStudyData(SG3, i)) val  = NormalizePx(sc, SG3[i]);
    };

    double vah=0,val=0,vpoc=0, pvah=0,pval=0,ppoc=0;
    read_vva(id_curr, vah, val, vpoc);
    read_vva(id_prev, pvah, pval, ppoc);

    // Validation de qualité des données VVA
    if (val > vpoc || vpoc > vah) {
      g_quality.invalid_values++;
      if (ShouldLog(sc, LOG_ERROR)) {
        SCString qualityMsg;
        qualityMsg.Format("QUALITY: Invalid VVA order: val=%.2f, vpoc=%.2f, vah=%.2f", val, vpoc, vah);
        DebugLog(sc, qualityMsg.GetChars());
      }
    }

    // Détection de changement d'état
    std::string symKey = std::string(symbol);
    LastVVA& lv = g_LastVVABySym[symKey];
    bool payload_changed = 
      has_changed(vah, lv.vah) || has_changed(val, lv.val) || has_changed(vpoc, lv.vpoc) ||
      has_changed(pvah, lv.pvah) || has_changed(pval, lv.pval) || has_changed(ppoc, lv.ppoc);

    // Vérifier clôture de barre
    int barStatus = sc.GetBarHasClosedStatus(i);
    bool bar_closed = (barStatus == BHCS_BAR_HAS_CLOSED);

    // Déduplication par type
    bool should_write_type = ShouldWriteDataWithType(symbol, "vva", t, barIndex);

    // Écrire si : changement de payload OU clôture de barre OU nouvelle clé (typée)
    if (payload_changed || bar_closed || should_write_type) {
      SCString j;
      j.Format("{\"t\":%.6f,\"sym\":\"%s\",\"type\":\"vva\",\"i\":%d,\"vah\":%.8f,\"val\":%.8f,\"vpoc\":%.8f,\"pvah\":%.8f,\"pval\":%.8f,\"ppoc\":%.8f,\"id_curr\":%d,\"id_prev\":%d,\"chart\":%d}",
               t, symbol, i, vah, val, vpoc, pvah, pval, ppoc, id_curr, id_prev, sc.ChartNumber);

      const int seqMode = sc.Input[28].GetInt();
      const char* dtype = "vva";
      std::string key = MakeBufKey(sc.ChartNumber, symbol, dtype);

      if (seqMode == 1) {
        uint32_t seq = ++g_SeqByKey[MakeSeqKey(sc.ChartNumber, symbol, dtype, i)];
        SCString withSeq = InjectSeqField(j, seq);
        WriteToSpecializedFile(sc.ChartNumber, dtype, withSeq);
      } else {
        if (!bar_closed) {
          BufPayload& slot = g_CoalesceBufByKey[key];
          if (slot.i >= 0 && slot.i != i) {
            WriteToSpecializedFile(sc.ChartNumber, dtype, slot.json);
          }
          slot.json = j; slot.i = i; slot.t = t; slot.dataType = dtype;
        } else {
          auto itbuf = g_CoalesceBufByKey.find(key);
          if (itbuf != g_CoalesceBufByKey.end()) {
            WriteToSpecializedFile(sc.ChartNumber, dtype, itbuf->second.json);
            g_CoalesceBufByKey.erase(itbuf);
          } else {
            WriteToSpecializedFile(sc.ChartNumber, dtype, j);
          }
        }
      }

      // Mettre à jour les dernières valeurs
      lv.vah = vah; lv.val = val; lv.vpoc = vpoc;
      lv.pvah = pvah; lv.pval = pval; lv.ppoc = ppoc;
    } else {
      // DEBUG: Log pourquoi VVA n'est pas écrit
      SCString debugMsg;
      debugMsg.Format("DEBUG G3: VVA NOT WRITTEN - should_write_type=%d, payload_changed=%d, bar_closed=%d", 
                      should_write_type, payload_changed, bar_closed);
      if (ShouldLog(sc, 2)) DebugLog(sc, debugMsg.GetChars());
    }
  }

  // ========== PVWAP (Previous VWAP) ==========
  
  if (sc.Input[8].GetInt() != 0 && sc.ArraySize > 0 && sc.VolumeAtPriceForBars)
  {
    const int last = sc.ArraySize - 1;
    static int last_pvwap_bar = -1;


    // Force l'exécution au moins une fois par session
    static bool pvwap_executed_today = false;
    if (last != last_pvwap_bar || !pvwap_executed_today)
    {
      last_pvwap_bar = last;
      pvwap_executed_today = true;

      // Trouver le début de la session du jour - LOGIQUE ALTERNATIVE
      int currStart = last;
      int maxLookback = 1000; // Limiter la recherche
      int lookbackCount = 0;
      
      while (currStart > 0 && !sc.IsNewTradingDay(currStart) && lookbackCount < maxLookback) {
        currStart--;
        lookbackCount++;
      }
      
      // Si pas de session trouvée, utiliser une plage fixe (ex: 500 barres précédentes)
      if (currStart <= 0) {
        currStart = (last > 500) ? (last - 500) : 0;
      }


      if (currStart > 0) {
        // La veille = [prevStart .. currStart-1] - LOGIQUE SIMPLIFIÉE
        int prevEnd = currStart - 1;
        int prevStart = (prevEnd > 500) ? (prevEnd - 500) : 0; // Plage fixe de 500 barres
        

        // Accumuler VAP sur la veille
        double sumV  = 0.0;
        double sumPV = 0.0;
        double sumP2V = 0.0;

        int totalVAPElements = 0;
        for (int b = prevStart; b <= prevEnd; ++b) {
          int N = sc.VolumeAtPriceForBars->GetSizeAtBarIndex(b);
          for (int k = 0; k < N; ++k) {
            const s_VolumeAtPriceV2* v = nullptr;
            if (sc.VolumeAtPriceForBars->GetVAPElementAtIndex(b, k, &v) && v) {
              // Utiliser le VRAI prix du VAP element, pas le Close du bar
              double p = NormalizePx(sc, v->PriceInTicks * sc.TickSize);
              double vol = (double)v->Volume;
              sumV   += vol;
              sumPV  += p * vol;
              sumP2V += p * p * vol;
              totalVAPElements++;
            }
          }
        }
        

        if (sumV > 0.0) {
          double pvwap = sumPV / sumV;
          
          // Bandes ±kσ autour du PVWAP
          int nb = sc.Input[9].GetInt();
          double var = (sumP2V / sumV) - (pvwap * pvwap);
          if (var < 0) var = 0;
          double sigma = sqrt(var);

          double up1=0, dn1=0, up2=0, dn2=0;
          if (nb >= 1) { up1 = pvwap + 0.5 * sigma; dn1 = pvwap - 0.5 * sigma; }
          if (nb >= 2) { up2 = pvwap + 1.0 * sigma; dn2 = pvwap - 1.0 * sigma; }


          SCString j;
          j.Format("{\"t\":%.6f,\"sym\":\"%s\",\"type\":\"pvwap\",\"i\":%d,\"prev_start\":%d,\"prev_end\":%d,"
                   "\"pvwap\":%.8f,\"up1\":%.8f,\"dn1\":%.8f,\"up2\":%.8f,\"dn2\":%.8f,\"chart\":%d}",
                   sc.BaseDateTimeIn[last].GetAsDouble(), sc.Symbol.GetChars(), last,
                   prevStart, prevEnd, pvwap, up1, dn1, up2, dn2, sc.ChartNumber);
          WriteToSpecializedFile(sc.ChartNumber, "pvwap", j);
        }
      }
    }
  }

  // ===== NBCV FOOTPRINT (avec déduplication améliorée) =====
  if (sc.Input[10].GetInt() != 0 && sc.ArraySize > 0)
  {
    const int i = sc.ArraySize - 1;
    const double t = sc.BaseDateTimeIn[i].GetAsDouble();
    const double barIndex = (double)i;
    const char* symbol = sc.Symbol.GetChars();
    
    // DEBUG: Log NBCV attempt
    if (ShouldLog(sc, LOG_VERBOSE)) {
      SCString debugMsg;
      debugMsg.Format("DEBUG G3: NBCV attempt - Input[10]=%d, ArraySize=%d, i=%d", 
                     sc.Input[10].GetInt(), sc.ArraySize, i);
      DebugLog(sc, debugMsg.GetChars());
    }
    
    int nbcv_id = sc.Input[11].GetInt();
    
    // AMÉLIORATION: Résolution automatique du Study ID NBCV
    if (nbcv_id <= 0) {
      // Essayer de résoudre automatiquement NBCV
      int nbcv_candidates[] = {33, 34, 35, 36, 37, 38, 39, 40, 41, 42};
      for (int k = 0; k < 10; k++) {
        if (nbcv_candidates[k] > 0) {
          SCFloatArray test;
          if (ReadSubgraph(sc, nbcv_candidates[k], NBCV_SG_ASK_VOLUME, test)) {
            if (ValidateStudyData(test, i)) {
              nbcv_id = nbcv_candidates[k];
              SCString debugMsg;
              debugMsg.Format("DEBUG G3: NBCV auto-resolved to ID=%d", nbcv_id);
              DebugLog(sc, debugMsg.GetChars());
              break;
            }
          }
        }
      }
    }
    
    // DEBUG: Test NBCV Study ID
    DebugStudyInfo(sc, nbcv_id, "NBCV", 0, "ASK_VOL");
    
    if (nbcv_id > 0) {
      // ----------------- NBCV: lecture des subgraphs -----------------
      SCFloatArray askVolArr, bidVolArr, deltaArr, tradesArr, cumDeltaArr, totalVolArr;
      SCFloatArray deltaPercentArr, askPercentArr, bidPercentArr;
      
      // Base
      ReadSubgraph(sc, nbcv_id, NBCV_SG_ASK_VOLUME, askVolArr);        // Ask Volume
      ReadSubgraph(sc, nbcv_id, NBCV_SG_BID_VOLUME, bidVolArr);        // Bid Volume
      ReadSubgraph(sc, nbcv_id, NBCV_SG_DELTA,      deltaArr);         // Delta
      ReadSubgraph(sc, nbcv_id, NBCV_SG_TRADES,     tradesArr);        // Trades (optionnel)
      ReadSubgraph(sc, nbcv_id, NBCV_SG_CUMULATIVE, cumDeltaArr);      // Cum Delta (optionnel)
      ReadSubgraph(sc, nbcv_id, NBCV_SG_TOTAL_VOLUME, totalVolArr);      // Total Volume
      
      // Ratios pré-calculés Sierra
      ReadSubgraph(sc, nbcv_id, NBCV_SG_DELTA_PCT, deltaPercentArr);  // Delta %
      ReadSubgraph(sc, nbcv_id, NBCV_SG_ASK_PCT, askPercentArr);    // Ask %
      ReadSubgraph(sc, nbcv_id, NBCV_SG_BID_PCT, bidPercentArr);    // Bid %

      if (ValidateStudyData(askVolArr, i) && ValidateStudyData(bidVolArr, i)) {
        
        // Lecture sécurisée des données
        double askVolume     = ValidateStudyData(askVolArr, i)       ? askVolArr[i]       : 0.0;
        double bidVolume     = ValidateStudyData(bidVolArr, i)       ? bidVolArr[i]       : 0.0;
        double delta         = ValidateStudyData(deltaArr, i)        ? deltaArr[i]        : (askVolume - bidVolume);
        double totalVolume   = ValidateStudyData(totalVolArr, i)     ? totalVolArr[i]     : (askVolume + bidVolume);
        double numberOfTrades = ValidateStudyData(tradesArr, i)      ? tradesArr[i]       : 0.0;
        double cumulativeDelta = ValidateStudyData(cumDeltaArr, i)   ? cumDeltaArr[i]     : 0.0;

        // Pourcentages Sierra -> normalisés [0..1]
        double askPct = ValidateStudyData(askPercentArr, i)    ? (askPercentArr[i]   / 100.0) : 0.0;
        double bidPct = ValidateStudyData(bidPercentArr, i)    ? (bidPercentArr[i]   / 100.0) : 0.0;
        double dltPct = ValidateStudyData(deltaPercentArr, i)  ? (deltaPercentArr[i] / 100.0) : 0.0;

        // Fallback si SG 16/17/10 indispo (rare, mais safe)
        if (!ValidateStudyData(askPercentArr, i) || !ValidateStudyData(bidPercentArr, i)) {
          // Recalcule simples sur base des volumes
          if (totalVolume > 0.0) {
            askPct = (askVolume / totalVolume);
            bidPct = (bidVolume / totalVolume);
          }
        }
        if (!ValidateStudyData(deltaPercentArr, i) && totalVolume > 0.0) {
          dltPct = (delta / totalVolume);
        }

        // Validation de qualité des données NBCV
        if (totalVolume < (askVolume + bidVolume)) {
          g_quality.invalid_values++;
          if (ShouldLog(sc, LOG_ERROR)) {
            SCString qualityMsg;
            qualityMsg.Format("QUALITY: NBCV total < ask+bid: total=%.0f, ask=%.0f, bid=%.0f", 
                             totalVolume, askVolume, bidVolume);
            DebugLog(sc, qualityMsg.GetChars());
          }
        }

        // Ratios croisés
        const double bidAskRatio = (askPct > 0.0) ? (bidPct / askPct) : 0.0;
        const double askBidRatio = (bidPct > 0.0) ? (askPct / bidPct) : 0.0;

        // Seuils configurables
        const double min_vol   = sc.Input[19].GetFloat();  // Min Total Volume
        const double th_ratio  = sc.Input[20].GetFloat();  // Min |Delta Ratio|
        const double th_ratioR = sc.Input[21].GetFloat();  // Min Ask/Bid or Bid/Ask Ratio

        // ----------------- Logique Bull/Bear -----------------
        int pressure_bullish = 0;
        int pressure_bearish = 0;

        if (totalVolume >= min_vol) {
          // Signe du delta = côté dominant brut
          if (delta > 0.0) {
            // Acheteurs dominants
            if (fabs(dltPct) >= th_ratio || askBidRatio >= th_ratioR) {
              pressure_bullish = 1;
            }
          } else if (delta < 0.0) {
            // Vendeurs dominants
            if (fabs(dltPct) >= th_ratio || bidAskRatio >= th_ratioR) {
              pressure_bearish = 1;
            }
          }
        }

        // Drapeau unifié
        int of_pressure = 0; // 1=BULL, -1=BEAR, 0=NEUTRAL
        if (pressure_bullish) of_pressure = 1;
        else if (pressure_bearish) of_pressure = -1;

        // Détection de changement d'état
        std::string symKey = std::string(symbol);
        LastNBCV& ln = g_LastNBCVBySym[symKey];
        bool payload_changed = 
          has_changed(askVolume, ln.askVolume) || has_changed(bidVolume, ln.bidVolume) ||
          has_changed(delta, ln.delta) || has_changed(totalVolume, ln.totalVolume) ||
          has_changed(dltPct, ln.deltaPct) || has_changed(askPct, ln.askPct) || has_changed(bidPct, ln.bidPct) ||
          (of_pressure != ln.pressure);

        // Vérifier clôture de barre
        int barStatus = sc.GetBarHasClosedStatus(i);
        bool bar_closed = (barStatus == BHCS_BAR_HAS_CLOSED);

        // Déduplication par type
        bool should_write_type = ShouldWriteDataWithType(symbol, "nbcv", t, barIndex);

        // Écrire si : changement de payload OU clôture de barre OU nouvelle clé (typée)
        if (payload_changed || bar_closed || should_write_type) {
          SCString j;
          j.Format(R"({"t":%.6f,"sym":"%s","type":"nbcv","i":%d,"ask_volume":%.0f,"bid_volume":%.0f,"delta":%.0f,"trades":%.0f,"cumulative_delta":%.0f,"total_volume":%.0f,"delta_ratio":%.6f,"ask_percent":%.6f,"bid_percent":%.6f,"bid_ask_ratio":%.6f,"ask_bid_ratio":%.6f,"pressure_bullish":%d,"pressure_bearish":%d,"pressure":%d,"chart":%d})",
                   t, symbol, i, askVolume, bidVolume, delta, numberOfTrades, cumulativeDelta, totalVolume, dltPct, askPct, bidPct, bidAskRatio, askBidRatio, pressure_bullish, pressure_bearish, of_pressure, sc.ChartNumber);

          const int seqMode = sc.Input[28].GetInt();
          const char* dtype = "nbcv";
          std::string key = MakeBufKey(sc.ChartNumber, symbol, dtype);

          if (seqMode == 1) {
            uint32_t seq = ++g_SeqByKey[MakeSeqKey(sc.ChartNumber, symbol, dtype, i)];
            SCString withSeq = InjectSeqField(j, seq);
            WriteToSpecializedFile(sc.ChartNumber, dtype, withSeq);
          } else {
            if (!bar_closed) {
              BufPayload& slot = g_CoalesceBufByKey[key];
              if (slot.i >= 0 && slot.i != i) {
                WriteToSpecializedFile(sc.ChartNumber, dtype, slot.json);
              }
              slot.json = j; slot.i = i; slot.t = t; slot.dataType = dtype; slot.dataType = dtype;
            } else {
              auto itbuf = g_CoalesceBufByKey.find(key);
              if (itbuf != g_CoalesceBufByKey.end()) {
                WriteToSpecializedFile(sc.ChartNumber, dtype, itbuf->second.json);
                g_CoalesceBufByKey.erase(itbuf);
              } else {
                WriteToSpecializedFile(sc.ChartNumber, dtype, j);
              }
            }
          }

          // Mettre à jour les dernières valeurs
          ln.askVolume = askVolume; ln.bidVolume = bidVolume; ln.delta = delta; ln.totalVolume = totalVolume;
          ln.deltaPct = dltPct; ln.askPct = askPct; ln.bidPct = bidPct; ln.pressure = of_pressure;
        } else {
          // DEBUG: Log pourquoi NBCV n'est pas écrit
          SCString debugMsg;
          debugMsg.Format("DEBUG G3: NBCV NOT WRITTEN - should_write_type=%d, payload_changed=%d, bar_closed=%d", 
                          should_write_type, payload_changed, bar_closed);
          if (ShouldLog(sc, 2)) DebugLog(sc, debugMsg.GetChars());
        }
      }
    }
  }

  // ---- DOM live (niveaux 1..max_levels) ----
  if (sc.UsesMarketDepthData) {
    static double s_last_bid_price[256];
    static int    s_last_bid_size[256];
    static double s_last_ask_price[256];
    static int    s_last_ask_size[256];
    
    for (int lvl = 1; lvl <= max_levels && lvl < 256; ++lvl) {
      s_MarketDepthEntry eBid;
      bool gotB = sc.GetBidMarketDepthEntryAtLevel(eBid, lvl);
      if (gotB && eBid.Price != 0.0 && eBid.Quantity != 0) {
        const double t = sc.BaseDateTimeIn[sc.ArraySize - 1].GetAsDouble();
        double p = (lvl == 1 ? NormalizePx(sc, sc.Bid) : NormalizePx(sc, eBid.Price));
        const int q = (lvl == 1 ? sc.BidSize : (int)eBid.Quantity);
        if (!(p == s_last_bid_price[lvl] && q == s_last_bid_size[lvl])) {
          SCString j;
          j.Format("{\"t\":%.6f,\"sym\":\"%s\",\"type\":\"depth\",\"side\":\"BID\",\"lvl\":%d,\"price\":%.8f,\"size\":%d,\"chart\":%d}",
                   t, sc.Symbol.GetChars(), lvl, p, q, sc.ChartNumber);
          WriteToSpecializedFile(sc.ChartNumber, "depth", j);
          s_last_bid_price[lvl] = p; s_last_bid_size[lvl] = q;
        }
      }

      s_MarketDepthEntry eAsk;
      bool gotA = sc.GetAskMarketDepthEntryAtLevel(eAsk, lvl);
      if (gotA && eAsk.Price != 0.0 && eAsk.Quantity != 0) {
        const double t = sc.BaseDateTimeIn[sc.ArraySize - 1].GetAsDouble();
        double p = (lvl == 1 ? NormalizePx(sc, sc.Ask) : NormalizePx(sc, eAsk.Price));
        const int q = (lvl == 1 ? sc.AskSize : (int)eAsk.Quantity);
        if (!(p == s_last_ask_price[lvl] && q == s_last_ask_size[lvl])) {
          SCString j;
          j.Format("{\"t\":%.6f,\"sym\":\"%s\",\"type\":\"depth\",\"side\":\"ASK\",\"lvl\":%d,\"price\":%.8f,\"size\":%d,\"chart\":%d}",
                   t, sc.Symbol.GetChars(), lvl, p, q, sc.ChartNumber);
          WriteToSpecializedFile(sc.ChartNumber, "depth", j);
          s_last_ask_price[lvl] = p; s_last_ask_size[lvl] = q;
        }
      }
    }
  }

  // ========== T&S ANTI-DOUBLONS ==========
  if (sc.Input[12].GetInt() != 0 || sc.Input[13].GetInt() != 0) {
    c_SCTimeAndSalesArray TnS;
    sc.GetTimeAndSales(TnS);
    const int sz = (int)TnS.Size();

    // DEBUG: Log T&S status
    SCString debugMsg;
    debugMsg.Format("DEBUG G3: T&S - Export T&S=%d, Export Quotes=%d, TnS Size=%d, LastTsIndex=%d, UseSeq=%d", 
                   sc.Input[12].GetInt(), sc.Input[13].GetInt(), sz, g_LastTsIndex, g_UseSeq);
    DebugLog(sc, debugMsg.GetChars());

    // Reset si Sierra a purgé l'historique
    if (sz < g_LastTsIndex) g_LastTsIndex = 0;

    // Première détection du support du Sequence
    static bool seqChecked = false;
    if (!seqChecked) { DetectSequenceSupport(TnS, g_UseSeq); seqChecked = true; }

    bool processed_any = false;

    if (g_UseSeq) {
      // Mode Sequence robuste: ne traite que les enregistrements avec Sequence croissant
      for (int i = 0; i < sz; ++i) {
        const s_TimeAndSales& ts = TnS[i];
        if (ts.Sequence > 0) {
          if (ts.Sequence <= g_LastSeq) continue;
          ProcessTS(ts);
          g_LastSeq = ts.Sequence;
          processed_any = true;
        }
      }
    }

    // Fallback Index si pas de support séquence ou aucun record séquencé nouveau
    if (!g_UseSeq || !processed_any) {
      for (int i = g_LastTsIndex; i < sz; ++i) {
        const s_TimeAndSales& ts = TnS[i];
        if (ts.Sequence > g_LastSeq) g_LastSeq = ts.Sequence; // garde-fou
        ProcessTS(ts);
      }
      g_LastTsIndex = sz;
    }
  }

  // ========== CUMULATIVE DELTA EXPORT ==========
  if (sc.Input[14].GetInt() != 0 && sc.ArraySize > 0) {
    const int i = sc.ArraySize - 1;
    const double t = sc.BaseDateTimeIn[i].GetAsDouble();
    
    // DEBUG: Log Cumulative Delta attempt
    SCString debugMsg;
    debugMsg.Format("DEBUG G3: Cumulative Delta attempt - Input[14]=%d, ArraySize=%d, i=%d", 
                   sc.Input[14].GetInt(), sc.ArraySize, i);
    DebugLog(sc, debugMsg.GetChars());
    
    int deltaStudyID = sc.Input[15].GetInt();
    const int deltaSG = sc.Input[16].GetInt();
    
    // AMÉLIORATION: Résolution automatique du Study ID Cumulative Delta
    if (deltaStudyID <= 0) {
      // Essayer de résoudre automatiquement Cumulative Delta
      int delta_candidates[] = {32, 33, 34, 35, 36, 37, 38, 39, 40, 41};
      for (int k = 0; k < 10; k++) {
        if (delta_candidates[k] > 0) {
          SCFloatArray test;
          if (ReadSubgraph(sc, delta_candidates[k], deltaSG, test)) {
            if (ValidateStudyData(test, i)) {
              deltaStudyID = delta_candidates[k];
              SCString debugMsg;
              debugMsg.Format("DEBUG G3: Cumulative Delta auto-resolved to ID=%d", deltaStudyID);
              DebugLog(sc, debugMsg.GetChars());
              break;
            }
          }
        }
      }
    }
    
    if (deltaStudyID > 0) {
      SCFloatArray deltaData;
      ReadSubgraph(sc, deltaStudyID, deltaSG, deltaData);
      
      if (ValidateStudyData(deltaData, i)) {
        const double barIndex = (double)i;
        const char* symbol = sc.Symbol.GetChars();
        const double deltaClose = deltaData[i];

        // NEW: payload_changed vs dernière valeur
        std::string symKey = std::string(symbol);
        LastCD& lcd = g_LastCDBySym[symKey];
        bool payload_changed = has_changed(deltaClose, lcd.close);
        
        // Déduplication par type
        bool should_write_type = ShouldWriteDataWithType(symbol, "cumulative_delta", t, barIndex);
        
        // Vérifier clôture de barre
        int barStatus = sc.GetBarHasClosedStatus(i);
        bool bar_closed = (barStatus == BHCS_BAR_HAS_CLOSED);
        
        // Écrire si : payload changé OU clôture de barre OU nouvelle clé typée
        if (payload_changed || bar_closed || should_write_type) {
          SCString j;
          j.Format("{\"t\":%.6f,\"sym\":\"%s\",\"type\":\"cumulative_delta\",\"i\":%d,\"close\":%.6f,\"study\":%d,\"sg\":%d,\"chart\":%d}",
                   t, sc.Symbol.GetChars(), i, deltaClose, deltaStudyID, deltaSG, sc.ChartNumber);

          const int seqMode = sc.Input[28].GetInt();
          const char* dtype = "cumulative_delta";
          std::string key = MakeBufKey(sc.ChartNumber, sc.Symbol.GetChars(), dtype);

          if (seqMode == 1) {
            uint32_t seq = ++g_SeqByKey[MakeSeqKey(sc.ChartNumber, sc.Symbol.GetChars(), dtype, i)];
            SCString withSeq = InjectSeqField(j, seq);
            WriteToSpecializedFile(sc.ChartNumber, dtype, withSeq);
          } else {
            if (!bar_closed) {
              BufPayload& slot = g_CoalesceBufByKey[key];
              if (slot.i >= 0 && slot.i != i) {
                WriteToSpecializedFile(sc.ChartNumber, dtype, slot.json);
              }
              slot.json = j; slot.i = i; slot.t = t; slot.dataType = dtype; slot.dataType = dtype;
            } else {
              auto itbuf = g_CoalesceBufByKey.find(key);
              if (itbuf != g_CoalesceBufByKey.end()) {
                WriteToSpecializedFile(sc.ChartNumber, dtype, itbuf->second.json);
                g_CoalesceBufByKey.erase(itbuf);
              } else {
                WriteToSpecializedFile(sc.ChartNumber, dtype, j);
              }
            }
          }

          // update cache
          lcd.close = deltaClose;
        } else {
          // DEBUG: Log pourquoi Cumulative Delta n'est pas écrit
          SCString debugMsg;
          debugMsg.Format("DEBUG G3: Cumulative Delta NOT WRITTEN - should_write_type=%d, payload_changed=%d, bar_closed=%d", 
                          should_write_type, payload_changed, bar_closed);
          if (ShouldLog(sc, 2)) DebugLog(sc, debugMsg.GetChars());
        }
      }
    }
  }

  // ========== ATR EXPORT ==========
  if (sc.Input[22].GetInt() != 0 && sc.ArraySize > 0) {
    const int i = sc.ArraySize - 1;
    const double t = sc.BaseDateTimeIn[i].GetAsDouble();

    SCString dbg; dbg.Format("DEBUG G3: ATR attempt - Input[22]=%d, ArraySize=%d, i=%d",
                             sc.Input[22].GetInt(), sc.ArraySize, i);
    DebugLog(sc, dbg.GetChars());

    int atrStudyID = sc.Input[23].GetInt();
    const int atrSG = sc.Input[24].GetInt();

    if (atrStudyID <= 0) {
      int candidates[] = {45};
      for (int k = 0; k < 1; ++k) {
        SCFloatArray test;
        if (ReadSubgraph(sc, candidates[k], atrSG, test) && ValidateStudyData(test, i)) {
          atrStudyID = candidates[k];
          SCString m; m.Format("DEBUG G3: ATR auto-resolved ID=%d", atrStudyID); DebugLog(sc, m.GetChars());
          break;
        }
      }
    }

    if (atrStudyID > 0) {
      SCFloatArray atrArr; ReadSubgraph(sc, atrStudyID, atrSG, atrArr);
      if (ValidateStudyData(atrArr, i)) {
        const double val = atrArr[i];
        const double barIndex = (double)i;
        const char* symbol = sc.Symbol.GetChars();

        std::string symKey = std::string(symbol);
        LastATR& last = g_LastATRBySym[symKey];
        bool payload_changed = has_changed(val, last.atr);

        bool should_write_type = ShouldWriteDataWithType(symbol, "atr", t, barIndex);
        bool bar_closed = (sc.GetBarHasClosedStatus(i) == BHCS_BAR_HAS_CLOSED);

        if (payload_changed || bar_closed || should_write_type) {
          SCString j;
          j.Format("{\"t\":%.6f,\"sym\":\"%s\",\"type\":\"atr\",\"i\":%d,\"atr\":%.6f,\"study\":%d,\"sg\":%d,\"chart\":%d}",
                   t, symbol, i, val, atrStudyID, atrSG, sc.ChartNumber);

          const int seqMode = sc.Input[28].GetInt();
          const char* dtype = "atr";
          std::string key = MakeBufKey(sc.ChartNumber, symbol, dtype);

          if (seqMode == 1) {
            uint32_t seq = ++g_SeqByKey[MakeSeqKey(sc.ChartNumber, symbol, dtype, i)];
            SCString withSeq = InjectSeqField(j, seq);
            WriteToSpecializedFile(sc.ChartNumber, dtype, withSeq);
          } else {
            if (!bar_closed) {
              BufPayload& slot = g_CoalesceBufByKey[key];
              if (slot.i >= 0 && slot.i != i) {
                WriteToSpecializedFile(sc.ChartNumber, dtype, slot.json);
              }
              slot.json = j; slot.i = i; slot.t = t; slot.dataType = dtype; slot.dataType = dtype;
            } else {
              auto itbuf = g_CoalesceBufByKey.find(key);
              if (itbuf != g_CoalesceBufByKey.end()) {
                WriteToSpecializedFile(sc.ChartNumber, dtype, itbuf->second.json);
                g_CoalesceBufByKey.erase(itbuf);
              } else {
                WriteToSpecializedFile(sc.ChartNumber, dtype, j);
              }
            }
          }

          last.atr = val;
        }
      }
    }
  }

  // ========== MÉTRIQUES ET FLUSH AUTOMATIQUE ==========
  CheckAutoFlush(sc);
  UpdateMetrics(sc, "study");

  // ========== CORRELATION EXPORT ==========
  if (sc.Input[25].GetInt() != 0 && sc.ArraySize > 0) {
    const int i = sc.ArraySize - 1;
    const double t = sc.BaseDateTimeIn[i].GetAsDouble();

    if (ShouldLog(sc, LOG_VERBOSE)) {
      SCString dbg; dbg.Format("DEBUG G3: Correlation attempt - Input[25]=%d, ArraySize=%d, i=%d",
                               sc.Input[25].GetInt(), sc.ArraySize, i);
      DebugLog(sc, dbg.GetChars());
    }

    int corrStudyID = sc.Input[26].GetInt();
    const int corrSG = sc.Input[27].GetInt();

    if (corrStudyID <= 0) {
      int candidates[] = {46};
      for (int k = 0; k < 1; ++k) {
        SCFloatArray test;
        if (ReadSubgraph(sc, candidates[k], corrSG, test) && ValidateStudyData(test, i)) {
          corrStudyID = candidates[k];
          if (ShouldLog(sc, LOG_KEY)) {
            SCString m; m.Format("DEBUG G3: Correlation auto-resolved ID=%d", corrStudyID); 
            DebugLog(sc, m.GetChars());
          }
          break;
        }
      }
    }

    if (corrStudyID > 0) {
      SCFloatArray corrArr; ReadSubgraph(sc, corrStudyID, corrSG, corrArr);
      if (ValidateStudyData(corrArr, i)) {
        const double cc = corrArr[i];
        const double barIndex = (double)i;
        const char* symbol = sc.Symbol.GetChars();

        std::string symKey = std::string(symbol);
        LastCorr& last = g_LastCorrBySym[symKey];
        bool payload_changed = has_changed(cc, last.cc);

        bool should_write_type = ShouldWriteDataWithType(symbol, "correlation", t, barIndex);
        bool bar_closed = (sc.GetBarHasClosedStatus(i) == BHCS_BAR_HAS_CLOSED);

        if (payload_changed || bar_closed || should_write_type) {
          SCString j;
          j.Format("{\"t\":%.6f,\"sym\":\"%s\",\"type\":\"correlation\",\"i\":%d,\"cc\":%.6f,\"study\":%d,\"sg\":%d,\"chart\":%d}",
                   t, symbol, i, cc, corrStudyID, corrSG, sc.ChartNumber);
          WriteToSpecializedFile(sc.ChartNumber, "correlation", j);
          last.cc = cc;
        }
      }
    }
  }

  // ========== FLUSH FINAL DE SÉCURITÉ ==========
  if (sc.LastCallToFunction) {
    FlushAllBuffers(sc, "LAST_CALL");
    if (ShouldLog(sc, LOG_KEY)) {
      DebugLog(sc, "DEBUG G3: Study terminated - final flush completed");
    }
  }
}