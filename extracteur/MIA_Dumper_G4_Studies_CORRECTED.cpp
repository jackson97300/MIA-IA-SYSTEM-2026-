// MIA_Dumper_G4_Studies_CORRECTED.cpp
// ACSIL — Sierra Chart
// VERSION CORRIGÉE avec logique de déduplication du G3
// Dump JSONL: chart_4_*_YYYYMMDD.jsonl avec déduplication intelligente

#include "sierrachart.h"
SCDLLName("MIA Dumper G4 Studies CORRECTED")

#include <stdio.h>
#include <string>
#include <unordered_map>
#include <algorithm>

static SCString g_OutputDir;

// ========== FONCTIONS UTILITAIRES (COPIÉES DU G3) ==========
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
  const double mult = (sc.RealTimePriceMultiplier != 0.0 ? sc.RealTimePriceMultiplier : 1.0);
  double px = raw / mult;
  if (px > 10000.0) px /= 100.0;
  px = sc.RoundToTickSize(px, sc.TickSize);
  return px;
}

// ========== LOGIQUE DE DÉDUPLICATION DU G3 ==========
// Structure pour la déduplication par (sym, t, i)
struct LastKey { 
  double t = 0.0; // timestamp
  double i = -1;  // bar index
};

// Fonction de déduplication améliorée (COPIÉE DU G3)
static bool ShouldWriteDataWithType(const char* symbol, const char* dataType, double timestamp, double barIndex) {
  static std::unordered_map<std::string, LastKey> s_LastKeyBySymType;
  std::string key = std::string(symbol) + "|" + std::string(dataType);
  LastKey& lk = s_LastKeyBySymType[key];
  bool same_ti = (fabs(lk.t - timestamp) < 1e-9) && (fabs(lk.i - barIndex) < 1e-9);
  lk.t = timestamp;
  lk.i = barIndex;
  return !same_ti; // Écrire si différent
}

// Détection de changement
static inline bool has_changed(double a, double b, double eps=1e-9) {
  return fabs(a-b) > eps;
}

// ========== STRUCTURES DE CACHE (COPIÉES DU G3) ==========
struct LastOHLC { double c=0,o=0,h=0,l=0; };
struct LastProfile { double val=0, vpoc=0, vah=0, hvn=0, lvn=0; };
struct LastVWAP { double vwap=0, sd1=0, sd2=0, sd3=0, sd4=0, sd5=0, sd6=0; };
struct LastVVA { double poc=0, vah=0, val=0; };
struct LastVVA_Prev { double ppoc=0, pvah=0, pval=0; };
struct LastPrevVP { double pvpoc=0, pvah=0, pval=0, pvwap=0; };
struct LastPrevVWAP { double pvwap=0, psd1=0, psd2=0; };
struct LastCorrelation { double corr=0; };
struct LastATR { double atr=0; };
struct LastNBCV { double delta=0, askvol=0, bidvol=0, trades=0, totalvol=0; };
struct LastCumDelta { double cumdelta=0; };

// Maps de déduplication par symbole (COPIÉES DU G3)
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

// ========== FONCTIONS UTILITAIRES ==========
static void EnsureDir(const SCString& d) {
#ifdef _WIN32
  CreateDirectoryA(d.GetChars(), NULL);
#endif
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

// ========== MAPPING DES STUDY IDs (BASÉ SUR L'INVENTAIRE) ==========
// Study IDs identifiés dans l'inventaire
#define STUDY_ID_VWAP 1
#define STUDY_ID_PREV_VP 2
#define STUDY_ID_PREV_VWAP 3
#define STUDY_ID_ATR 5
#define STUDY_ID_CUM_DELTA 6
#define STUDY_ID_VVA 8
#define STUDY_ID_VVA_PREV 9
#define STUDY_ID_NBCV 14
#define STUDY_ID_CORRELATION 15
#define STUDY_ID_OHLC 16
#define STUDY_ID_VOLUME_PROFILE 13

// Subgraph mappings
#define VWAP_SG_MAIN 0
#define VWAP_SG_SD1 1
#define VWAP_SG_SD2 2
#define VWAP_SG_SD3 3
#define VWAP_SG_SD4 4
#define VWAP_SG_SD5 5
#define VWAP_SG_SD6 6

#define VVA_SG_POC 0
#define VVA_SG_VAH 1
#define VVA_SG_VAL 2

#define NBCV_SG_DELTA 0
#define NBCV_SG_ASK_VOL 5
#define NBCV_SG_BID_VOL 6
#define NBCV_SG_TRADES 11
#define NBCV_SG_TOTAL_VOL 12

// ========== FONCTION PRINCIPALE ==========
SCSFExport scsf_MIA_Dumper_G4_Studies_CORRECTED(SCStudyInterfaceRef sc)
{
  if (sc.SetDefaults)
  {
    sc.GraphName = "MIA Dumper G4 Studies CORRECTED";
    sc.StudyDescription = "Dumper Chart 4 avec déduplication corrigée";
    sc.AutoLoop = 0;
    sc.UpdateAlways = 1;
    sc.CalculationPrecedence = LOW_PREC_LEVEL;

    // Inputs pour les Study IDs
    sc.Input[0].Name = "Output Directory";
    sc.Input[0].SetString("D:\\MIA_IA_system");

    sc.Input[1].Name = "VWAP Study ID";
    sc.Input[1].SetInt(STUDY_ID_VWAP);

    sc.Input[2].Name = "VVA Study ID";
    sc.Input[2].SetInt(STUDY_ID_VVA);

    sc.Input[3].Name = "VVA Previous Study ID";
    sc.Input[3].SetInt(STUDY_ID_VVA_PREV);

    sc.Input[4].Name = "Previous VP Study ID";
    sc.Input[4].SetInt(STUDY_ID_PREV_VP);

    sc.Input[5].Name = "Previous VWAP Study ID";
    sc.Input[5].SetInt(STUDY_ID_PREV_VWAP);

    sc.Input[6].Name = "ATR Study ID";
    sc.Input[6].SetInt(STUDY_ID_ATR);

    sc.Input[7].Name = "NBCV Study ID";
    sc.Input[7].SetInt(STUDY_ID_NBCV);

    sc.Input[8].Name = "Cumulative Delta Study ID";
    sc.Input[8].SetInt(STUDY_ID_CUM_DELTA);

    sc.Input[9].Name = "Correlation Study ID";
    sc.Input[9].SetInt(STUDY_ID_CORRELATION);

    sc.Input[10].Name = "Volume Profile Study ID";
    sc.Input[10].SetInt(STUDY_ID_VOLUME_PROFILE);

    return;
  }

  if (sc.ServerConnectionState != SCS_CONNECTED) return;

  // Initialisation du répertoire de sortie
  g_OutputDir = sc.Input[0].GetString();
  EnsureDir(g_OutputDir);

  const SCString sym = sc.Symbol;
  const double t = sc.BaseDateTimeIn[sc.Index].GetAsDouble();
  const double i = (double)sc.Index;

  // ========== OHLC (Chart 4 view) ==========
  {
    const double c = NormalizePx(sc, sc.Close[sc.Index]);
    const double o = NormalizePx(sc, sc.Open[sc.Index]);
    const double h = NormalizePx(sc, sc.High[sc.Index]);
    const double l = NormalizePx(sc, sc.Low[sc.Index]);
    
    // Détection de changement d'état
    std::string symKey = std::string(sym.GetChars());
    LastOHLC& lo = g_LastOHLCBySym[symKey];
    bool payload_changed = has_changed(c, lo.c) || has_changed(o, lo.o) || has_changed(h, lo.h) || has_changed(l, lo.l);

    // Vérifier clôture de barre
    int barStatus = sc.GetBarHasClosedStatus(sc.Index);
    bool bar_closed = (barStatus == BHCS_BAR_HAS_CLOSED);

    // Déduplication par type
    bool should_write_type = ShouldWriteDataWithType(sym.GetChars(), "ohlc", t, i);

    // Écrire si : changement de payload OU clôture de barre OU nouvelle clé (typée)
    if (payload_changed || bar_closed || should_write_type) {
      SCString fn = TodayFileName("chart_4_ohlc");
      SCString line;
      line.Format("{\"sym\":\"%s\",\"t\":%.6f,\"i\":%.0f,\"c\":%.6f,\"o\":%.6f,\"h\":%.6f,\"l\":%.6f}",
                  sym.GetChars(), t, i, c, o, h, l);
      AppendJSONL(fn, line);
      
      // Mettre à jour les dernières valeurs
      lo.c = c; lo.o = o; lo.h = h; lo.l = l;
    }
  }

  // ========== VWAP ==========
  {
    int vwapID = sc.Input[1].GetInt();
    if (vwapID > 0) {
      SCFloatArray vwapData, sd1Data, sd2Data, sd3Data, sd4Data, sd5Data, sd6Data;
      
      if (ReadSubgraph(sc, vwapID, VWAP_SG_MAIN, vwapData) && ValidateStudyData(vwapData, sc.Index)) {
        ReadSubgraph(sc, vwapID, VWAP_SG_SD1, sd1Data);
        ReadSubgraph(sc, vwapID, VWAP_SG_SD2, sd2Data);
        ReadSubgraph(sc, vwapID, VWAP_SG_SD3, sd3Data);
        ReadSubgraph(sc, vwapID, VWAP_SG_SD4, sd4Data);
        ReadSubgraph(sc, vwapID, VWAP_SG_SD5, sd5Data);
        ReadSubgraph(sc, vwapID, VWAP_SG_SD6, sd6Data);

        double vwap = NormalizePx(sc, vwapData[sc.Index]);
        double sd1 = ValidateStudyData(sd1Data, sc.Index) ? NormalizePx(sc, sd1Data[sc.Index]) : 0.0;
        double sd2 = ValidateStudyData(sd2Data, sc.Index) ? NormalizePx(sc, sd2Data[sc.Index]) : 0.0;
        double sd3 = ValidateStudyData(sd3Data, sc.Index) ? NormalizePx(sc, sd3Data[sc.Index]) : 0.0;
        double sd4 = ValidateStudyData(sd4Data, sc.Index) ? NormalizePx(sc, sd4Data[sc.Index]) : 0.0;
        double sd5 = ValidateStudyData(sd5Data, sc.Index) ? NormalizePx(sc, sd5Data[sc.Index]) : 0.0;
        double sd6 = ValidateStudyData(sd6Data, sc.Index) ? NormalizePx(sc, sd6Data[sc.Index]) : 0.0;

        // Détection de changement d'état
        std::string symKey = std::string(sym.GetChars());
        LastVWAP& lv = g_LastVWAPBySym[symKey];
        bool payload_changed = has_changed(vwap, lv.vwap) || has_changed(sd1, lv.sd1) || has_changed(sd2, lv.sd2) ||
                              has_changed(sd3, lv.sd3) || has_changed(sd4, lv.sd4) || has_changed(sd5, lv.sd5) || has_changed(sd6, lv.sd6);

        // Vérifier clôture de barre
        int barStatus = sc.GetBarHasClosedStatus(sc.Index);
        bool bar_closed = (barStatus == BHCS_BAR_HAS_CLOSED);

        // Déduplication par type
        bool should_write_type = ShouldWriteDataWithType(sym.GetChars(), "vwap", t, i);

        // Écrire si : changement de payload OU clôture de barre OU nouvelle clé (typée)
        if (payload_changed || bar_closed || should_write_type) {
          SCString fn = TodayFileName("chart_4_vwap");
          SCString line;
          line.Format("{\"sym\":\"%s\",\"t\":%.6f,\"i\":%.0f,\"vwap\":%.6f,\"sd1\":%.6f,\"sd2\":%.6f,\"sd3\":%.6f,\"sd4\":%.6f,\"sd5\":%.6f,\"sd6\":%.6f}",
                      sym.GetChars(), t, i, vwap, sd1, sd2, sd3, sd4, sd5, sd6);
          AppendJSONL(fn, line);
          
          // Mettre à jour les dernières valeurs
          lv.vwap = vwap; lv.sd1 = sd1; lv.sd2 = sd2; lv.sd3 = sd3; lv.sd4 = sd4; lv.sd5 = sd5; lv.sd6 = sd6;
        }
      }
    }
  }

  // ========== VVA (Volume Value Area) ==========
  {
    int vvaID = sc.Input[2].GetInt();
    if (vvaID > 0) {
      SCFloatArray pocData, vahData, valData;
      
      if (ReadSubgraph(sc, vvaID, VVA_SG_POC, pocData) && ValidateStudyData(pocData, sc.Index)) {
        ReadSubgraph(sc, vvaID, VVA_SG_VAH, vahData);
        ReadSubgraph(sc, vvaID, VVA_SG_VAL, valData);

        double poc = NormalizePx(sc, pocData[sc.Index]);
        double vah = ValidateStudyData(vahData, sc.Index) ? NormalizePx(sc, vahData[sc.Index]) : 0.0;
        double val = ValidateStudyData(valData, sc.Index) ? NormalizePx(sc, valData[sc.Index]) : 0.0;

        // Détection de changement d'état
        std::string symKey = std::string(sym.GetChars());
        LastVVA& lv = g_LastVVABySym[symKey];
        bool payload_changed = has_changed(poc, lv.poc) || has_changed(vah, lv.vah) || has_changed(val, lv.val);

        // Vérifier clôture de barre
        int barStatus = sc.GetBarHasClosedStatus(sc.Index);
        bool bar_closed = (barStatus == BHCS_BAR_HAS_CLOSED);

        // Déduplication par type
        bool should_write_type = ShouldWriteDataWithType(sym.GetChars(), "vva", t, i);

        // Écrire si : changement de payload OU clôture de barre OU nouvelle clé (typée)
        if (payload_changed || bar_closed || should_write_type) {
          SCString fn = TodayFileName("chart_4_vva");
          SCString line;
          line.Format("{\"sym\":\"%s\",\"t\":%.6f,\"i\":%.0f,\"poc\":%.6f,\"vah\":%.6f,\"val\":%.6f}",
                      sym.GetChars(), t, i, poc, vah, val);
          AppendJSONL(fn, line);
          
          // Mettre à jour les dernières valeurs
          lv.poc = poc; lv.vah = vah; lv.val = val;
        }
      }
    }
  }

  // ========== ATR ==========
  {
    int atrID = sc.Input[6].GetInt();
    if (atrID > 0) {
      SCFloatArray atrData;
      
      if (ReadSubgraph(sc, atrID, 0, atrData) && ValidateStudyData(atrData, sc.Index)) {
        double atr = atrData[sc.Index];

        // Détection de changement d'état
        std::string symKey = std::string(sym.GetChars());
        LastATR& la = g_LastATRBySym[symKey];
        bool payload_changed = has_changed(atr, la.atr);

        // Vérifier clôture de barre
        int barStatus = sc.GetBarHasClosedStatus(sc.Index);
        bool bar_closed = (barStatus == BHCS_BAR_HAS_CLOSED);

        // Déduplication par type
        bool should_write_type = ShouldWriteDataWithType(sym.GetChars(), "atr", t, i);

        // Écrire si : changement de payload OU clôture de barre OU nouvelle clé (typée)
        if (payload_changed || bar_closed || should_write_type) {
          SCString fn = TodayFileName("chart_4_atr");
          SCString line;
          line.Format("{\"sym\":\"%s\",\"t\":%.6f,\"i\":%.0f,\"atr\":%.6f}",
                      sym.GetChars(), t, i, atr);
          AppendJSONL(fn, line);
          
          // Mettre à jour les dernières valeurs
          la.atr = atr;
        }
      }
    }
  }

  // ========== CORRELATION ==========
  {
    int corrID = sc.Input[9].GetInt();
    if (corrID > 0) {
      SCFloatArray corrData;
      
      if (ReadSubgraph(sc, corrID, 0, corrData) && ValidateStudyData(corrData, sc.Index)) {
        double corr = corrData[sc.Index];

        // Détection de changement d'état
        std::string symKey = std::string(sym.GetChars());
        LastCorrelation& lc = g_LastCorrBySym[symKey];
        bool payload_changed = has_changed(corr, lc.corr);

        // Vérifier clôture de barre
        int barStatus = sc.GetBarHasClosedStatus(sc.Index);
        bool bar_closed = (barStatus == BHCS_BAR_HAS_CLOSED);

        // Déduplication par type
        bool should_write_type = ShouldWriteDataWithType(sym.GetChars(), "correlation", t, i);

        // Écrire si : changement de payload OU clôture de barre OU nouvelle clé (typée)
        if (payload_changed || bar_closed || should_write_type) {
          SCString fn = TodayFileName("chart_4_correlation");
          SCString line;
          line.Format("{\"sym\":\"%s\",\"t\":%.6f,\"i\":%.0f,\"correlation\":%.6f}",
                      sym.GetChars(), t, i, corr);
          AppendJSONL(fn, line);
          
          // Mettre à jour les dernières valeurs
          lc.corr = corr;
        }
      }
    }
  }

  // ========== NBCV ==========
  {
    int nbcvID = sc.Input[7].GetInt();
    if (nbcvID > 0) {
      SCFloatArray deltaData, askVolData, bidVolData, tradesData, totalVolData;
      
      if (ReadSubgraph(sc, nbcvID, NBCV_SG_DELTA, deltaData) && ValidateStudyData(deltaData, sc.Index)) {
        ReadSubgraph(sc, nbcvID, NBCV_SG_ASK_VOL, askVolData);
        ReadSubgraph(sc, nbcvID, NBCV_SG_BID_VOL, bidVolData);
        ReadSubgraph(sc, nbcvID, NBCV_SG_TRADES, tradesData);
        ReadSubgraph(sc, nbcvID, NBCV_SG_TOTAL_VOL, totalVolData);

        double delta = deltaData[sc.Index];
        double askvol = ValidateStudyData(askVolData, sc.Index) ? askVolData[sc.Index] : 0.0;
        double bidvol = ValidateStudyData(bidVolData, sc.Index) ? bidVolData[sc.Index] : 0.0;
        double trades = ValidateStudyData(tradesData, sc.Index) ? tradesData[sc.Index] : 0.0;
        double totalvol = ValidateStudyData(totalVolData, sc.Index) ? totalVolData[sc.Index] : 0.0;

        // Détection de changement d'état
        std::string symKey = std::string(sym.GetChars());
        LastNBCV& ln = g_LastNBCVBySym[symKey];
        bool payload_changed = has_changed(delta, ln.delta) || has_changed(askvol, ln.askvol) || 
                              has_changed(bidvol, ln.bidvol) || has_changed(trades, ln.trades) || has_changed(totalvol, ln.totalvol);

        // Vérifier clôture de barre
        int barStatus = sc.GetBarHasClosedStatus(sc.Index);
        bool bar_closed = (barStatus == BHCS_BAR_HAS_CLOSED);

        // Déduplication par type
        bool should_write_type = ShouldWriteDataWithType(sym.GetChars(), "nbcv", t, i);

        // Écrire si : changement de payload OU clôture de barre OU nouvelle clé (typée)
        if (payload_changed || bar_closed || should_write_type) {
          SCString fn = TodayFileName("chart_4_nbcv");
          SCString line;
          line.Format("{\"sym\":\"%s\",\"t\":%.6f,\"i\":%.0f,\"delta\":%.0f,\"askvol\":%.0f,\"bidvol\":%.0f,\"trades\":%.0f,\"totalvol\":%.0f}",
                      sym.GetChars(), t, i, delta, askvol, bidvol, trades, totalvol);
          AppendJSONL(fn, line);
          
          // Mettre à jour les dernières valeurs
          ln.delta = delta; ln.askvol = askvol; ln.bidvol = bidvol; ln.trades = trades; ln.totalvol = totalvol;
        }
      }
    }
  }

  // ========== CUMULATIVE DELTA ==========
  {
    int cumDeltaID = sc.Input[8].GetInt();
    if (cumDeltaID > 0) {
      SCFloatArray cumDeltaData;
      
      if (ReadSubgraph(sc, cumDeltaID, 3, cumDeltaData) && ValidateStudyData(cumDeltaData, sc.Index)) {
        double cumdelta = cumDeltaData[sc.Index];

        // Détection de changement d'état
        std::string symKey = std::string(sym.GetChars());
        LastCumDelta& lcd = g_LastCumDeltaBySym[symKey];
        bool payload_changed = has_changed(cumdelta, lcd.cumdelta);

        // Vérifier clôture de barre
        int barStatus = sc.GetBarHasClosedStatus(sc.Index);
        bool bar_closed = (barStatus == BHCS_BAR_HAS_CLOSED);

        // Déduplication par type
        bool should_write_type = ShouldWriteDataWithType(sym.GetChars(), "cumulative_delta", t, i);

        // Écrire si : changement de payload OU clôture de barre OU nouvelle clé (typée)
        if (payload_changed || bar_closed || should_write_type) {
          SCString fn = TodayFileName("chart_4_cumulative_delta");
          SCString line;
          line.Format("{\"sym\":\"%s\",\"t\":%.6f,\"i\":%.0f,\"cumulative_delta\":%.0f}",
                      sym.GetChars(), t, i, cumdelta);
          AppendJSONL(fn, line);
          
          // Mettre à jour les dernières valeurs
          lcd.cumdelta = cumdelta;
        }
      }
    }
  }
}



