// MIA_Dumper_G4_Studies.cpp - VERSION CORRIGEE
// ACSIL — Sierra Chart
// Dump JSONL: chart_4_ohlc_YYYYMMDD.jsonl, chart_4_volume_profile_YYYYMMDD.jsonl
// Features: de-dup (sym,t,i), write on change or bar close, VAL/VPOC/VAH guard (val ≤ vpoc ≤ vah), configurable output dir.

#include "sierrachart.h"
SCDLLName("MIA Dumper G4 Studies")

#include <stdio.h>
#include <string>
#include <unordered_map>
#include <algorithm>

static SCString g_OutputDir;

// ========== FONCTIONS UTILITAIRES ==========
// Helper pour lire les données d'une étude
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

// Helper pour normaliser les prix
inline double NormalizePx(const SCStudyInterfaceRef& sc, double raw) {
  // 1) Dé-multiplier si besoin
  const double mult = (sc.RealTimePriceMultiplier != 0.0 ? sc.RealTimePriceMultiplier : 1.0);
  double px = raw / mult;

  // 2) Correction d'échelle avant arrondi (certains flux arrivent x100)
  if (px > 10000.0) px /= 100.0;

  // 3) Arrondi au tick
  px = sc.RoundToTickSize(px, sc.TickSize);
  return px;
}

// --- helpers ----------------------------------------------------------------
static void EnsureDir(const SCString& d) {
#ifdef _WIN32
  CreateDirectoryA(d.GetChars(), NULL);
#endif
}

// Fonction de debug combinée (Sierra + fichier local)
static void DebugLog(SCStudyInterfaceRef& sc, const char* message) {
  // Log dans Sierra Chart
  sc.AddMessageToLog(message, 1);
  
  // Log dans fichier local avec timestamp
  time_t now = time(NULL);
  struct tm* lt = localtime(&now);
  if (lt) {
    SCString filename;
    filename.Format("D:\\MIA_IA_system\\debug_g4_%04d%02d%02d.log", 
                   lt->tm_year + 1900, lt->tm_mon + 1, lt->tm_mday);
    FILE* f = fopen(filename.GetChars(), "a");
    if (f) {
      fprintf(f, "[%02d:%02d:%02d] %s\n", 
              lt->tm_hour, lt->tm_min, lt->tm_sec, message);
      fclose(f);
    }
  }
}

static SCString TodayFileName(const char* stem) {
  time_t now = time(NULL);
  struct tm* lt = localtime(&now);
  int y = lt ? (lt->tm_year + 1900) : 1970;
  int m = lt ? (lt->tm_mon + 1) : 1;
  int d = lt ? lt->tm_mday : 1;
  SCString fn; fn.Format("%s\\%s_%04d%02d%02d.jsonl", g_OutputDir.GetChars(), stem, y, m, d);
  return fn;
}

static void AppendJSONL(const SCString& path, const SCString& line) {
  FILE* f = fopen(path.GetChars(), "ab");
  if (!f) return;
  fwrite(line.GetChars(), 1, strlen(line.GetChars()), f);
  fwrite("\n", 1, 1, f);
  fflush(f);
    fclose(f); 
}

static inline bool has_changed(double a, double b, double eps=1e-9) {
  return fabs(a-b) > eps;
}

// --- state ------------------------------------------------------------------
struct LastKey { double t=0.0; double i=-1; };

// --- AJOUTER : déduplication par (sym|type, t, i)
static bool ShouldWriteDataWithType(const char* symbol, const char* dataType, double timestamp, double barIndex) {
  static std::unordered_map<std::string, LastKey> s_LastKeyBySymType;
  std::string key = std::string(symbol) + "|" + std::string(dataType);
  LastKey& lk = s_LastKeyBySymType[key];
  bool same_ti = (fabs(lk.t - timestamp) < 1e-9) && (fabs(lk.i - barIndex) < 1e-9);
  
  // Mettre à jour APRÈS avoir calculé same_ti
  lk.t = timestamp;
  lk.i = barIndex;
  
  return !same_ti; // Écrire si différent
}
struct LastOHLC { double c=0,o=0,h=0,l=0; };
struct LastProfile { double val=0, vpoc=0, vah=0, hvn=0, lvn=0; };
struct LastVWAP { double vwap=0, sd1=0, sd2=0, sd3=0; };
struct LastVVA { double poc=0, vah=0, val=0; };
struct LastVVA_Prev { double ppoc=0, pvah=0, pval=0; };
struct LastPrevVP { double pvpoc=0, pvah=0, pval=0, pvwap=0; };
struct LastPrevVWAP { double pvpoc=0, pvah=0, pval=0, pvwap=0, psd1=0, psd2=0; };
struct LastCorrelation { double corr=0; };
struct LastATR { double atr=0; };
struct LastNBCV { double delta=0, askvol=0, bidvol=0, trades=0, totalvol=0; };
struct LastCumDelta { double cumdelta=0; };

static std::unordered_map<std::string, LastKey> g_LastKeyBySym;
static std::unordered_map<std::string, LastOHLC> g_LastOHLCBySym;
static std::unordered_map<std::string, LastProfile> g_LastProfBySym;
static std::unordered_map<std::string, LastVWAP> g_LastVWAPBySym;
static std::unordered_map<std::string, LastVVA> g_LastVVABySym;
static std::unordered_map<std::string, LastVVA_Prev> g_LastVVAPrevBySym;
static std::unordered_map<std::string, LastPrevVP> g_LastPrevVPBySym;
static std::unordered_map<std::string, LastPrevVWAP> g_LastPrevVWAPBySym;
static std::unordered_map<std::string, LastCorrelation> g_LastCorrBySym;
static std::unordered_map<std::string, LastATR> g_LastATRBySym;
static std::unordered_map<std::string, LastNBCV> g_LastNBCVBySym;
static std::unordered_map<std::string, LastCumDelta> g_LastCumDeltaBySym;

// --- Study entry -------------------------------------------------------------
SCSFExport scsf_MIA_Dumper_G4_Studies(SCStudyInterfaceRef sc)
{
  SCInputRef OutDir  = sc.Input[0];
  SCInputRef SymbolOverride = sc.Input[1];

  // Subgraph indices for Volume Profile study on Chart 4
  SCInputRef VAL_Idx  = sc.Input[2];
  SCInputRef VPOC_Idx = sc.Input[3];
  SCInputRef VAH_Idx  = sc.Input[4];
  SCInputRef HVN_Idx  = sc.Input[14];
  SCInputRef LVN_Idx  = sc.Input[15];
  
  // Study IDs for Chart 4
  SCInputRef VWAP_ID = sc.Input[5];
  SCInputRef VVA_ID = sc.Input[6];
  SCInputRef VVA_PREV_ID = sc.Input[7];
  SCInputRef PREV_VP_ID = sc.Input[8];
  SCInputRef PREV_VWAP_ID = sc.Input[9];
  SCInputRef CORR_ID = sc.Input[10];
  SCInputRef ATR_ID = sc.Input[11];
  SCInputRef NBCV_ID = sc.Input[12];
  SCInputRef CUM_DELTA_ID = sc.Input[13];
  
  // Debug startup
  static bool first_run = true;
  if (first_run) {
    SCString startupMsg;
    startupMsg.Format("DEBUG G4: MIA_Dumper_G4_Studies STARTED - Chart=%d, Symbol=%s, ArraySize=%d", 
                     sc.ChartNumber, sc.Symbol.GetChars(), sc.ArraySize);
    DebugLog(sc, startupMsg.GetChars());
    
    // Debug Study IDs
    SCString studyIdsMsg;
    studyIdsMsg.Format("DEBUG G4: Study IDs - VWAP=%d, VVA=%d, VVA_PREV=%d, PREV_VP=%d, PREV_VWAP=%d, CORR=%d, ATR=%d, NBCV=%d, CUM_DELTA=%d", 
                      VWAP_ID.GetInt(), VVA_ID.GetInt(), VVA_PREV_ID.GetInt(), PREV_VP_ID.GetInt(), 
                      PREV_VWAP_ID.GetInt(), CORR_ID.GetInt(), ATR_ID.GetInt(), NBCV_ID.GetInt(), CUM_DELTA_ID.GetInt());
    DebugLog(sc, studyIdsMsg.GetChars());
    
    first_run = false;
  }

  if (sc.SetDefaults)
  {
    sc.GraphName = "MIA Dumper G4 Studies";
    sc.AutoLoop = 1;

    OutDir.Name = "Output Directory";
    OutDir.SetString("D:\\MIA_IA_system");

    SymbolOverride.Name = "Symbol Override (optional)";
    SymbolOverride.SetString("");

    VAL_Idx.Name  = "VAL Subgraph Index";
    VPOC_Idx.Name = "VPOC Subgraph Index";
    VAH_Idx.Name  = "VAH Subgraph Index";
    HVN_Idx.Name  = "HVN Subgraph Index";
    LVN_Idx.Name  = "LVN Subgraph Index";
    // Mapping correct selon l'inventaire : Study ID 8 (Volume Value Area Lines)
    VAL_Idx.SetInt(2);   // SG2: VAL
    VPOC_Idx.SetInt(0);  // SG0: VPOC  
    VAH_Idx.SetInt(1);   // SG1: VAH
    HVN_Idx.SetInt(-1);  // Pas de HVN dans Study ID 8
    LVN_Idx.SetInt(-1);  // Pas de LVN dans Study ID 8

    // Study IDs configuration
    VWAP_ID.Name = "VWAP Study ID";
    VWAP_ID.SetInt(1);  // Study ID 1: VWAP
    
    VVA_ID.Name = "VVA Study ID";
    VVA_ID.SetInt(8);   // Study ID 8: Volume Value Area Lines
    
    VVA_PREV_ID.Name = "VVA Previous Study ID";
    VVA_PREV_ID.SetInt(9);  // Study ID 9: Volume Value Area Previous
    
    PREV_VP_ID.Name = "Previous VP Study ID";
    PREV_VP_ID.SetInt(2);   // Study ID 2: PREVIOUS VPOC VAH VAL
    
    PREV_VWAP_ID.Name = "Previous VWAP Study ID";
    PREV_VWAP_ID.SetInt(3); // Study ID 3: PREVIOUS VWAP SD+1 SD-1
    
    CORR_ID.Name = "Correlation Study ID";
    CORR_ID.SetInt(15);     // Study ID 15: Correlation Coefficient
    
    ATR_ID.Name = "ATR Study ID";
    ATR_ID.SetInt(5);       // Study ID 5: Average True Range
    
    NBCV_ID.Name = "NBCV Study ID";
    NBCV_ID.SetInt(14);     // Study ID 14: Numbers Bars Calculated Values
    
    CUM_DELTA_ID.Name = "Cumulative Delta Study ID";
    CUM_DELTA_ID.SetInt(6); // Study ID 6: Cumulative Delta Bars

    return;
  }

  if (sc.Index == 0) {
    g_OutputDir = OutDir.GetString();
    if (g_OutputDir.IsEmpty()) g_OutputDir = "D:\\MIA_IA_system";
    EnsureDir(g_OutputDir);
  }

  const SCString sym = SymbolOverride.GetString()[0] ? SymbolOverride.GetString() : sc.Symbol.GetChars();
  const double t = sc.BaseDateTimeIn[sc.Index].GetTimeInSeconds();
  const double i = (double)sc.Index;

  // Déduplication intelligente (sym, t, i)
  LastKey& lk = g_LastKeyBySym[std::string(sym.GetChars())];
  bool same_ti = (fabs(lk.t - t) < 1e-9) && (fabs(lk.i - i) < 1e-9);
  
  // Mettre à jour la clé pour la prochaine vérification
  lk.t = t;
  lk.i = i;

  // ---------------- OHLC (Chart 4 view) ----------------
  {
    const double c = sc.Close[sc.Index];
    const double o = sc.Open[sc.Index];
    const double h = sc.High[sc.Index];
    const double l = sc.Low[sc.Index];
    
    // DEBUG: Log OHLC attempt
    SCString debugMsg;
    debugMsg.Format("DEBUG G4: OHLC attempt - Index=%d, OHLC=%.2f/%.2f/%.2f/%.2f", 
                   sc.Index, o, h, l, c);
    sc.AddMessageToLog(debugMsg, 1);

    LastOHLC& lo = g_LastOHLCBySym[std::string(sym.GetChars())];
    bool payload_changed =
      has_changed(c, lo.c) || has_changed(o, lo.o) || has_changed(h, lo.h) || has_changed(l, lo.l);

    int barStatus = sc.GetBarHasClosedStatus(sc.Index);
    bool bar_closed = (barStatus == BHCS_BAR_HAS_CLOSED);

    // Déduplication par type
    bool should_write_type = ShouldWriteDataWithType(sym.GetChars(), "ohlc", t, i);
    
    // Écrire si : changement de payload OU clôture de barre OU nouvelle clé (typée)
    if (payload_changed || bar_closed || should_write_type) {
      SCString debugMsgOHLC;
      debugMsgOHLC.Format("DEBUG G4: OHLC WRITING - same_ti=%d, payload_changed=%d, bar_closed=%d", 
                          same_ti, payload_changed, bar_closed);
      sc.AddMessageToLog(debugMsgOHLC, 1);
      
      SCString fn = TodayFileName("chart_4_ohlc");
      SCString line;
      line.Format("{\"sym\":\"%s\",\"t\":%.6f,\"i\":%.0f,\"c\":%.6f,\"o\":%.6f,\"h\":%.6f,\"l\":%.6f}",
                  sym.GetChars(), t, i, c, o, h, l);
      AppendJSONL(fn, line);
      sc.AddMessageToLog("DEBUG G4: OHLC FILE WRITTEN", 1);
      lo.c=c; lo.o=o; lo.h=h; lo.l=l;
    }
  }

    // ---------------- Volume Profile (Study ID 8 - Volume Value Area Lines) ----------------
    {
      const int volProfileID = 8; // Study ID 8: Volume Value Area Lines
      
      SCString debugMsg;
      debugMsg.Format("DEBUG G4: Volume Profile attempt - ID=%d, ArraySize=%d, i=%d", 
                     volProfileID, sc.ArraySize, i);
      DebugLog(sc, debugMsg.GetChars());
      
      if (volProfileID > 0) {
      SCFloatArray vpocArray, vahArray, valArray;
      
      if (ReadSubgraph(sc, volProfileID, 0, vpocArray) && 
          ReadSubgraph(sc, volProfileID, 1, vahArray) && 
          ReadSubgraph(sc, volProfileID, 2, valArray) &&
          ValidateStudyData(vpocArray, sc.Index) &&
          ValidateStudyData(vahArray, sc.Index) &&
          ValidateStudyData(valArray, sc.Index)) {
        
        double vpoc = NormalizePx(sc, vpocArray[sc.Index]);
        double vah = NormalizePx(sc, vahArray[sc.Index]);
        double val = NormalizePx(sc, valArray[sc.Index]);
        
        // HVN/LVN pas disponibles dans Study ID 8
        double hvn = 0.0;
        double lvn = 0.0;

      // auto-correct safety: enforce val ≤ vah ordering before check
      if (val > vah) std::swap(val, vah);

      // guard: require val ≤ vpoc ≤ vah
      if (!(val <= vpoc && vpoc <= vah)) {
        // DEBUG: Log validation failure
        SCString debugMsg2;
        debugMsg2.Format("DEBUG G4: Volume Profile validation FAILED - val=%.6f, vpoc=%.6f, vah=%.6f", val, vpoc, vah);
        sc.AddMessageToLog(debugMsg2, 1);
        // skip writing corrupted sample
      } else {
        sc.AddMessageToLog("DEBUG G4: Volume Profile validation PASSED", 1);
        LastProfile& lp = g_LastProfBySym[std::string(sym.GetChars())];
        bool changed = has_changed(val, lp.val) || has_changed(vpoc, lp.vpoc) || has_changed(vah, lp.vah) ||
                      has_changed(hvn, lp.hvn) || has_changed(lvn, lp.lvn);

        int barStatus = sc.GetBarHasClosedStatus(sc.Index);
        bool bar_closed = (barStatus == BHCS_BAR_HAS_CLOSED);

        // Déduplication par type
        bool should_write_type = ShouldWriteDataWithType(sym.GetChars(), "volume_profile", t, i);
        
        // Écrire si : changement de payload OU clôture de barre OU nouvelle clé (typée)
        if (changed || bar_closed || should_write_type) {
          SCString debugMsg3;
          debugMsg3.Format("DEBUG G4: Volume Profile WRITING - same_ti=%d, changed=%d, bar_closed=%d", 
                          same_ti, changed, bar_closed);
          sc.AddMessageToLog(debugMsg3, 1);
          
          SCString fn = TodayFileName("chart_4_volume_profile");
          SCString line;
          line.Format("{\"sym\":\"%s\",\"t\":%.6f,\"i\":%.0f,\"val\":%.6f,\"vpoc\":%.6f,\"vah\":%.6f,\"hvn\":%.6f,\"lvn\":%.6f}",
                      sym.GetChars(), t, i, val, vpoc, vah, hvn, lvn);
          AppendJSONL(fn, line);
          sc.AddMessageToLog("DEBUG G4: Volume Profile FILE WRITTEN", 1);
          lp.val=val; lp.vpoc=vpoc; lp.vah=vah; lp.hvn=hvn; lp.lvn=lvn;
        }
      }
    }
  }

  // ---------------- VWAP (Study ID 1) ----------------
  {
    const int vwapID = VWAP_ID.GetInt();
    
    SCString debugMsg;
    debugMsg.Format("DEBUG G4: VWAP attempt - ID=%d, ArraySize=%d, i=%d", 
                   vwapID, sc.ArraySize, i);
    DebugLog(sc, debugMsg.GetChars());
  
    if (vwapID > 0) {
      // Utiliser ReadSubgraph comme le G3
      SCFloatArray vwapArray, sd1Array, sd2Array, sd3Array, sd4Array, sd5Array, sd6Array;
      
      if (ReadSubgraph(sc, vwapID, 0, vwapArray) && ValidateStudyData(vwapArray, sc.Index)) {
        double vwap = NormalizePx(sc, vwapArray[sc.Index]);
        double sd1 = 0, sd2 = 0, sd3 = 0, sd4 = 0, sd5 = 0, sd6 = 0;
        
        if (ReadSubgraph(sc, vwapID, 1, sd1Array) && ValidateStudyData(sd1Array, sc.Index)) sd1 = NormalizePx(sc, sd1Array[sc.Index]);
        if (ReadSubgraph(sc, vwapID, 2, sd2Array) && ValidateStudyData(sd2Array, sc.Index)) sd2 = NormalizePx(sc, sd2Array[sc.Index]);
        if (ReadSubgraph(sc, vwapID, 3, sd3Array) && ValidateStudyData(sd3Array, sc.Index)) sd3 = NormalizePx(sc, sd3Array[sc.Index]);
        if (ReadSubgraph(sc, vwapID, 4, sd4Array) && ValidateStudyData(sd4Array, sc.Index)) sd4 = NormalizePx(sc, sd4Array[sc.Index]);
        if (ReadSubgraph(sc, vwapID, 5, sd5Array) && ValidateStudyData(sd5Array, sc.Index)) sd5 = NormalizePx(sc, sd5Array[sc.Index]);
        if (ReadSubgraph(sc, vwapID, 6, sd6Array) && ValidateStudyData(sd6Array, sc.Index)) sd6 = NormalizePx(sc, sd6Array[sc.Index]);

        if (vwap != 0) {
        std::string symKey = std::string(sym.GetChars());
        LastVWAP& lv = g_LastVWAPBySym[symKey];
        
        // DEBUG: Log les valeurs VWAP
        SCString debugMsg;
        debugMsg.Format("DEBUG G4: VWAP values - vwap=%.6f, sd1=%.6f, sd2=%.6f, sd3=%.6f, last_vwap=%.6f", 
                       vwap, sd1, sd2, sd3, lv.vwap);
        DebugLog(sc, debugMsg.GetChars());
        
        bool payload_changed = 
          has_changed(vwap, lv.vwap) || has_changed(sd1, lv.sd1) || 
          has_changed(sd2, lv.sd2) || has_changed(sd3, lv.sd3);

        int barStatus = sc.GetBarHasClosedStatus(sc.Index);
        bool bar_closed = (barStatus == BHCS_BAR_HAS_CLOSED);

        // Déduplication par type
        bool should_write_type = ShouldWriteDataWithType(sym.GetChars(), "vwap", t, i);
        
        // Écrire si : données valides (pas de déduplication pour VWAP)
        if (vwap != 0) {
          SCString debugMsg;
          debugMsg.Format("DEBUG G4: VWAP WRITING - payload_changed=%d, bar_closed=%d, should_write_type=%d", 
                         payload_changed, bar_closed, should_write_type);
          DebugLog(sc, debugMsg.GetChars());
          
          SCString fn = TodayFileName("chart_4_vwap");
          SCString line;
          line.Format("{\"sym\":\"%s\",\"t\":%.6f,\"i\":%.0f,\"vwap\":%.6f,\"sd1\":%.6f,\"sd2\":%.6f,\"sd3\":%.6f,\"sd4\":%.6f,\"sd5\":%.6f,\"sd6\":%.6f}",
                      sym.GetChars(), t, i, vwap, sd1, sd2, sd3, sd4, sd5, sd6);
          AppendJSONL(fn, line);
          DebugLog(sc, "DEBUG G4: VWAP FILE WRITTEN");
          lv.vwap = vwap; lv.sd1 = sd1; lv.sd2 = sd2; lv.sd3 = sd3;
        } else {
          SCString debugMsg;
          debugMsg.Format("DEBUG G4: VWAP NOT WRITTEN - payload_changed=%d, bar_closed=%d, should_write_type=%d", 
                         payload_changed, bar_closed, should_write_type);
          DebugLog(sc, debugMsg.GetChars());
        }
      }
    }
    }
  }

  // ---------------- VVA (Volume Value Area Lines - Study ID 8) ----------------
  {
    const int vvaID = VVA_ID.GetInt();
    
    SCString debugMsg;
    debugMsg.Format("DEBUG G4: VVA attempt - ID=%d, ArraySize=%d, i=%d", 
                   vvaID, sc.ArraySize, i);
    DebugLog(sc, debugMsg.GetChars());
    
    if (vvaID > 0) {
      // Utiliser ReadSubgraph comme les autres sections
      SCFloatArray pocArray, vahArray, valArray;
      double poc = 0, vah = 0, val = 0;
      
      if (ReadSubgraph(sc, vvaID, 0, pocArray) && ValidateStudyData(pocArray, sc.Index)) {
        poc = NormalizePx(sc, pocArray[sc.Index]);
      }
      if (ReadSubgraph(sc, vvaID, 1, vahArray) && ValidateStudyData(vahArray, sc.Index)) {
        vah = NormalizePx(sc, vahArray[sc.Index]);
      }
      if (ReadSubgraph(sc, vvaID, 2, valArray) && ValidateStudyData(valArray, sc.Index)) {
        val = NormalizePx(sc, valArray[sc.Index]);
      }

      if (poc != 0 && vah != 0 && val != 0) {
        std::string symKey = std::string(sym.GetChars());
        LastVVA& lv = g_LastVVABySym[symKey];
        
        // DEBUG: Log les valeurs VVA
        SCString debugMsg;
        debugMsg.Format("DEBUG G4: VVA values - poc=%.6f, vah=%.6f, val=%.6f, last_poc=%.6f", 
                       poc, vah, val, lv.poc);
        DebugLog(sc, debugMsg.GetChars());
        
        bool payload_changed = 
          has_changed(poc, lv.poc) || has_changed(vah, lv.vah) || has_changed(val, lv.val);

        int barStatus = sc.GetBarHasClosedStatus(sc.Index);
        bool bar_closed = (barStatus == BHCS_BAR_HAS_CLOSED);

        // Déduplication par type
        bool should_write_type = ShouldWriteDataWithType(sym.GetChars(), "vva", t, i);
        
        // Écrire si : données valides (pas de déduplication pour VVA)
        if (poc != 0 && vah != 0 && val != 0) {
          SCString debugMsg;
          debugMsg.Format("DEBUG G4: VVA WRITING - poc=%.6f, vah=%.6f, val=%.6f", poc, vah, val);
          DebugLog(sc, debugMsg.GetChars());
          
          SCString fn = TodayFileName("chart_4_vva");
          SCString line;
          line.Format("{\"sym\":\"%s\",\"t\":%.6f,\"i\":%.0f,\"poc\":%.6f,\"vah\":%.6f,\"val\":%.6f}",
                      sym.GetChars(), t, i, poc, vah, val);
          AppendJSONL(fn, line);
          DebugLog(sc, "DEBUG G4: VVA FILE WRITTEN");
          lv.poc = poc; lv.vah = vah; lv.val = val;
        } else {
          SCString debugMsg;
          debugMsg.Format("DEBUG G4: VVA NOT WRITTEN - poc=%.6f, vah=%.6f, val=%.6f", poc, vah, val);
          DebugLog(sc, debugMsg.GetChars());
        }
      }
    }
  }

  // ---------------- VVA Previous (Study ID 9) ----------------
  {
    const int vvaPrevID = VVA_PREV_ID.GetInt();
    if (vvaPrevID > 0) {
      // Utiliser ReadSubgraph comme les autres sections
      SCFloatArray ppocArray, pvahArray, pvalArray;
      double ppoc = 0, pvah = 0, pval = 0;
      
      if (ReadSubgraph(sc, vvaPrevID, 0, ppocArray) && ValidateStudyData(ppocArray, sc.Index)) {
        ppoc = NormalizePx(sc, ppocArray[sc.Index]);
      }
      if (ReadSubgraph(sc, vvaPrevID, 1, pvahArray) && ValidateStudyData(pvahArray, sc.Index)) {
        pvah = NormalizePx(sc, pvahArray[sc.Index]);
      }
      if (ReadSubgraph(sc, vvaPrevID, 2, pvalArray) && ValidateStudyData(pvalArray, sc.Index)) {
        pval = NormalizePx(sc, pvalArray[sc.Index]);
      }

      if (ppoc != 0 && pvah != 0 && pval != 0) {
        std::string symKey = std::string(sym.GetChars());
        LastVVA_Prev& lv = g_LastVVAPrevBySym[symKey];
        bool payload_changed = 
          has_changed(ppoc, lv.ppoc) || has_changed(pvah, lv.pvah) || has_changed(pval, lv.pval);

        int barStatus = sc.GetBarHasClosedStatus(sc.Index);
        bool bar_closed = (barStatus == BHCS_BAR_HAS_CLOSED);

        // Déduplication par type
        bool should_write_type = ShouldWriteDataWithType(sym.GetChars(), "vva_previous", t, i);
        
        // Écrire si : données valides (pas de déduplication pour VVA Previous)
        if (ppoc != 0 && pvah != 0 && pval != 0) {
          SCString fn = TodayFileName("chart_4_vva_previous");
          SCString line;
          line.Format("{\"sym\":\"%s\",\"t\":%.6f,\"i\":%.0f,\"ppoc\":%.6f,\"pvah\":%.6f,\"pval\":%.6f}",
                      sym.GetChars(), t, i, ppoc, pvah, pval);
          AppendJSONL(fn, line);
          lv.ppoc = ppoc; lv.pvah = pvah; lv.pval = pval;
        }
      }
    }
  }

  // ---------------- Previous VP (Study ID 2) ----------------
  {
    const int prevVPID = PREV_VP_ID.GetInt();
    if (prevVPID > 0) {
      // Utiliser ReadSubgraph comme les autres sections
      SCFloatArray pvpocArray, pvahArray, pvalArray, pvwapArray;
      double pvpoc = 0, pvah = 0, pval = 0, pvwap = 0;
      
      if (ReadSubgraph(sc, prevVPID, 1, pvpocArray) && ValidateStudyData(pvpocArray, sc.Index)) {
        pvpoc = NormalizePx(sc, pvpocArray[sc.Index]);
      }
      if (ReadSubgraph(sc, prevVPID, 2, pvahArray) && ValidateStudyData(pvahArray, sc.Index)) {
        pvah = NormalizePx(sc, pvahArray[sc.Index]);
      }
      if (ReadSubgraph(sc, prevVPID, 3, pvalArray) && ValidateStudyData(pvalArray, sc.Index)) {
        pval = NormalizePx(sc, pvalArray[sc.Index]);
      }
      if (ReadSubgraph(sc, prevVPID, 4, pvwapArray) && ValidateStudyData(pvwapArray, sc.Index)) {
        pvwap = NormalizePx(sc, pvwapArray[sc.Index]);
      }

      if (pvpoc != 0 && pvah != 0 && pval != 0) {
        std::string symKey = std::string(sym.GetChars());
        LastPrevVP& lv = g_LastPrevVPBySym[symKey];
        bool payload_changed = 
          has_changed(pvpoc, lv.pvpoc) || has_changed(pvah, lv.pvah) || 
          has_changed(pval, lv.pval) || has_changed(pvwap, lv.pvwap);

        int barStatus = sc.GetBarHasClosedStatus(sc.Index);
        bool bar_closed = (barStatus == BHCS_BAR_HAS_CLOSED);

        // Déduplication par type
        bool should_write_type = ShouldWriteDataWithType(sym.GetChars(), "previous_vp", t, i);
        
        // Écrire si : données valides (pas de déduplication pour Previous VP)
        if (pvpoc != 0 && pvah != 0 && pval != 0 && pvwap != 0) {
          SCString fn = TodayFileName("chart_4_previous_vp");
          SCString line;
          line.Format("{\"sym\":\"%s\",\"t\":%.6f,\"i\":%.0f,\"pvpoc\":%.6f,\"pvah\":%.6f,\"pval\":%.6f,\"pvwap\":%.6f}",
                      sym.GetChars(), t, i, pvpoc, pvah, pval, pvwap);
          AppendJSONL(fn, line);
          lv.pvpoc = pvpoc; lv.pvah = pvah; lv.pval = pval; lv.pvwap = pvwap;
        }
      }
    }
  }

  // ---------------- Previous VWAP (Study ID 3) ----------------
  {
    const int prevVWAPID = PREV_VWAP_ID.GetInt();
    if (prevVWAPID > 0) {
      // Utiliser ReadSubgraph comme les autres sections
      SCFloatArray pvwapArray, psd1Array, psd2Array;
      double pvwap = 0, psd1 = 0, psd2 = 0;
      
      if (ReadSubgraph(sc, prevVWAPID, 4, pvwapArray) && ValidateStudyData(pvwapArray, sc.Index)) {
        pvwap = NormalizePx(sc, pvwapArray[sc.Index]);
      }
      if (ReadSubgraph(sc, prevVWAPID, 12, psd1Array) && ValidateStudyData(psd1Array, sc.Index)) {
        psd1 = NormalizePx(sc, psd1Array[sc.Index]);
      }
      if (ReadSubgraph(sc, prevVWAPID, 13, psd2Array) && ValidateStudyData(psd2Array, sc.Index)) {
        psd2 = NormalizePx(sc, psd2Array[sc.Index]);
      }

      if (pvwap != 0) {
        std::string symKey = std::string(sym.GetChars());
        LastPrevVWAP& lv = g_LastPrevVWAPBySym[symKey];
        bool payload_changed = 
          has_changed(pvwap, lv.pvwap) || has_changed(psd1, lv.psd1) || has_changed(psd2, lv.psd2);

        int barStatus = sc.GetBarHasClosedStatus(sc.Index);
        bool bar_closed = (barStatus == BHCS_BAR_HAS_CLOSED);

        // Déduplication par type
        bool should_write_type = ShouldWriteDataWithType(sym.GetChars(), "previous_vwap", t, i);
        
        // Écrire si : données valides (pas de déduplication pour Previous VWAP)
        if (pvwap != 0) {
          SCString fn = TodayFileName("chart_4_previous_vwap");
          SCString line;
          line.Format("{\"sym\":\"%s\",\"t\":%.6f,\"i\":%.0f,\"pvwap\":%.6f,\"psd1\":%.6f,\"psd2\":%.6f}",
                      sym.GetChars(), t, i, pvwap, psd1, psd2);
          AppendJSONL(fn, line);
          lv.pvwap = pvwap; lv.psd1 = psd1; lv.psd2 = psd2;
        }
      }
    }
  }

  // ---------------- Correlation (Study ID 15) ----------------
  {
    const int corrID = CORR_ID.GetInt();
    if (corrID > 0) {
      // Utiliser ReadSubgraph comme les autres sections
      SCFloatArray corrArray;
      double corr = 0;
      
      if (ReadSubgraph(sc, corrID, 0, corrArray) && ValidateStudyData(corrArray, sc.Index)) {
        corr = corrArray[sc.Index]; // Pas de normalisation pour la corrélation
      }

      if (corr != 0) {
        std::string symKey = std::string(sym.GetChars());
        LastCorrelation& lc = g_LastCorrBySym[symKey];
        bool payload_changed = has_changed(corr, lc.corr);

        int barStatus = sc.GetBarHasClosedStatus(sc.Index);
        bool bar_closed = (barStatus == BHCS_BAR_HAS_CLOSED);

        // Déduplication par type
        bool should_write_type = ShouldWriteDataWithType(sym.GetChars(), "correlation", t, i);
        
        // Écrire si : données valides (pas de déduplication pour Correlation)
        if (corr != 0) {
          SCString fn = TodayFileName("chart_4_correlation");
          SCString line;
          line.Format("{\"sym\":\"%s\",\"t\":%.6f,\"i\":%.0f,\"correlation\":%.6f}",
                      sym.GetChars(), t, i, corr);
          AppendJSONL(fn, line);
          lc.corr = corr;
        }
      }
    }
  }

  // ---------------- ATR (Study ID 5) ----------------
  {
    const int atrID = ATR_ID.GetInt();
    
    SCString debugMsg;
    debugMsg.Format("DEBUG G4: ATR attempt - ID=%d, ArraySize=%d, i=%d", 
                   atrID, sc.ArraySize, i);
    DebugLog(sc, debugMsg.GetChars());
    
    if (atrID > 0) {
      // Utiliser ReadSubgraph comme les autres sections
      SCFloatArray atrArray;
      double atr = 0;
      
      if (ReadSubgraph(sc, atrID, 0, atrArray) && ValidateStudyData(atrArray, sc.Index)) {
        atr = NormalizePx(sc, atrArray[sc.Index]);
      }

      if (atr != 0) {
        std::string symKey = std::string(sym.GetChars());
        LastATR& la = g_LastATRBySym[symKey];
        
        // DEBUG: Log les valeurs ATR
        SCString debugMsg;
        debugMsg.Format("DEBUG G4: ATR values - atr=%.6f, last_atr=%.6f", atr, la.atr);
        DebugLog(sc, debugMsg.GetChars());
        
        bool payload_changed = has_changed(atr, la.atr);

        int barStatus = sc.GetBarHasClosedStatus(sc.Index);
        bool bar_closed = (barStatus == BHCS_BAR_HAS_CLOSED);

        // Déduplication par type
        bool should_write_type = ShouldWriteDataWithType(sym.GetChars(), "atr", t, i);
        
        // Écrire si : données valides (pas de déduplication pour ATR)
        if (atr != 0) {
          SCString debugMsg;
          debugMsg.Format("DEBUG G4: ATR WRITING - atr=%.6f", atr);
          DebugLog(sc, debugMsg.GetChars());
          
          SCString fn = TodayFileName("chart_4_atr");
          SCString line;
          line.Format("{\"sym\":\"%s\",\"t\":%.6f,\"i\":%.0f,\"atr\":%.6f}",
                      sym.GetChars(), t, i, atr);
          AppendJSONL(fn, line);
          DebugLog(sc, "DEBUG G4: ATR FILE WRITTEN");
          la.atr = atr;
        } else {
          SCString debugMsg;
          debugMsg.Format("DEBUG G4: ATR NOT WRITTEN - atr=%.6f", atr);
          DebugLog(sc, debugMsg.GetChars());
        }
      }
    }
  }

  // ---------------- NBCV (Study ID 14) ----------------
  {
    const int nbcvID = NBCV_ID.GetInt();
    
    SCString debugMsg;
    debugMsg.Format("DEBUG G4: NBCV attempt - ID=%d, ArraySize=%d, i=%d", 
                   nbcvID, sc.ArraySize, i);
    DebugLog(sc, debugMsg.GetChars());
    
    if (nbcvID > 0) {
      // Utiliser ReadSubgraph comme les autres sections
      SCFloatArray deltaArray;
      double delta = 0;
      
      if (ReadSubgraph(sc, nbcvID, 0, deltaArray) && ValidateStudyData(deltaArray, sc.Index)) {
        delta = deltaArray[sc.Index]; // Pas de normalisation pour le delta
      }
      SCFloatArray askvolArray, bidvolArray, tradesArray, totalvolArray;
      double askvol = 0, bidvol = 0, trades = 0, totalvol = 0;
      
      if (ReadSubgraph(sc, nbcvID, 5, askvolArray) && ValidateStudyData(askvolArray, sc.Index)) {
        askvol = askvolArray[sc.Index];
      }
      if (ReadSubgraph(sc, nbcvID, 6, bidvolArray) && ValidateStudyData(bidvolArray, sc.Index)) {
        bidvol = bidvolArray[sc.Index];
      }
      if (ReadSubgraph(sc, nbcvID, 11, tradesArray) && ValidateStudyData(tradesArray, sc.Index)) {
        trades = tradesArray[sc.Index];
      }
      if (ReadSubgraph(sc, nbcvID, 12, totalvolArray) && ValidateStudyData(totalvolArray, sc.Index)) {
        totalvol = totalvolArray[sc.Index];
      }

      if (askvol != 0 && bidvol != 0) {
        std::string symKey = std::string(sym.GetChars());
        LastNBCV& ln = g_LastNBCVBySym[symKey];
        bool payload_changed = 
          has_changed(delta, ln.delta) || has_changed(askvol, ln.askvol) || 
          has_changed(bidvol, ln.bidvol) || has_changed(trades, ln.trades) || 
          has_changed(totalvol, ln.totalvol);

        int barStatus = sc.GetBarHasClosedStatus(sc.Index);
        bool bar_closed = (barStatus == BHCS_BAR_HAS_CLOSED);

        // Déduplication par type
        bool should_write_type = ShouldWriteDataWithType(sym.GetChars(), "nbcv", t, i);
        
        // Écrire si : données valides (pas de déduplication pour NBCV)
        if (delta != 0 || askvol != 0 || bidvol != 0 || trades != 0 || totalvol != 0) {
          SCString debugMsg;
          debugMsg.Format("DEBUG G4: NBCV WRITING - delta=%.0f, askvol=%.0f, bidvol=%.0f, trades=%.0f, totalvol=%.0f", 
                         delta, askvol, bidvol, trades, totalvol);
          DebugLog(sc, debugMsg.GetChars());
          
          SCString fn = TodayFileName("chart_4_nbcv");
          SCString line;
          line.Format("{\"sym\":\"%s\",\"t\":%.6f,\"i\":%.0f,\"delta\":%.0f,\"askvol\":%.0f,\"bidvol\":%.0f,\"trades\":%.0f,\"totalvol\":%.0f}",
                      sym.GetChars(), t, i, delta, askvol, bidvol, trades, totalvol);
          AppendJSONL(fn, line);
          DebugLog(sc, "DEBUG G4: NBCV FILE WRITTEN");
          ln.delta = delta; ln.askvol = askvol; ln.bidvol = bidvol; ln.trades = trades; ln.totalvol = totalvol;
        } else {
          SCString debugMsg;
          debugMsg.Format("DEBUG G4: NBCV NOT WRITTEN - delta=%.0f, askvol=%.0f, bidvol=%.0f, trades=%.0f, totalvol=%.0f", 
                         delta, askvol, bidvol, trades, totalvol);
          DebugLog(sc, debugMsg.GetChars());
        }
      }
    }
  }

  // ---------------- Cumulative Delta (Study ID 6) ----------------
  {
    const int cumDeltaID = CUM_DELTA_ID.GetInt();
    
    SCString debugMsg;
    debugMsg.Format("DEBUG G4: Cumulative Delta attempt - ID=%d, ArraySize=%d, i=%d", 
                   cumDeltaID, sc.ArraySize, i);
    DebugLog(sc, debugMsg.GetChars());
    
    if (cumDeltaID > 0) {
      // Utiliser ReadSubgraph comme les autres sections
      SCFloatArray cumdeltaArray;
      double cumdelta = 0;
      
      if (ReadSubgraph(sc, cumDeltaID, 3, cumdeltaArray) && ValidateStudyData(cumdeltaArray, sc.Index)) {
        cumdelta = cumdeltaArray[sc.Index]; // Pas de normalisation pour le delta cumulatif
      }

      if (cumdelta != 0) {
        std::string symKey = std::string(sym.GetChars());
        LastCumDelta& lcd = g_LastCumDeltaBySym[symKey];
        bool payload_changed = has_changed(cumdelta, lcd.cumdelta);

        int barStatus = sc.GetBarHasClosedStatus(sc.Index);
        bool bar_closed = (barStatus == BHCS_BAR_HAS_CLOSED);

        // Déduplication par type
        bool should_write_type = ShouldWriteDataWithType(sym.GetChars(), "cumulative_delta", t, i);
        
        // Écrire si : données valides (pas de déduplication pour Cumulative Delta)
        if (cumdelta != 0) {
          SCString debugMsg;
          debugMsg.Format("DEBUG G4: Cumulative Delta WRITING - cumdelta=%.0f", cumdelta);
          DebugLog(sc, debugMsg.GetChars());
          
          SCString fn = TodayFileName("chart_4_cumulative_delta");
          SCString line;
          line.Format("{\"sym\":\"%s\",\"t\":%.6f,\"i\":%.0f,\"cumulative_delta\":%.0f}",
                      sym.GetChars(), t, i, cumdelta);
          AppendJSONL(fn, line);
          DebugLog(sc, "DEBUG G4: Cumulative Delta FILE WRITTEN");
          lcd.cumdelta = cumdelta;
        } else {
          SCString debugMsg;
          debugMsg.Format("DEBUG G4: Cumulative Delta NOT WRITTEN - cumdelta=%.0f", cumdelta);
          DebugLog(sc, debugMsg.GetChars());
        }
      }
    }
  }
}
}