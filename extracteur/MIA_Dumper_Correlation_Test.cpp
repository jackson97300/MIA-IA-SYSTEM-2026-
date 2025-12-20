// === MIA_Dumper_Correlation_Test.cpp ===
// Dumper dédié pour tester et capter la corrélation (Coefficient CC)
// Sortie: D:\\MIA_IA_system\\chart_<chart>_correlation_test_YYYYMMDD.jsonl

#include "sierrachart.h"
SCDLLName("MIA_Dumper_Correlation_Test");
#ifdef _WIN32
  #include <windows.h>
#endif
#include <time.h>
#include <cmath>
#include <unordered_map>
#include <string>
using std::fabs;

// ========== UTILITAIRES SORTIE ==========
static void EnsureOutDir(const char* baseDir = "D:\\MIA_IA_system") {
#ifdef _WIN32
  CreateDirectoryA(baseDir, NULL);
#endif
}

static SCString DailyFilenameForChartType(int chartNumber, const char* dataType, const char* baseDir = "D:\\MIA_IA_system") {
  time_t now = time(NULL);
  struct tm* lt = localtime(&now);
  int y = lt ? (lt->tm_year + 1900) : 1970;
  int m = lt ? (lt->tm_mon + 1) : 1;
  int d = lt ? lt->tm_mday : 1;
  SCString filename;
  filename.Format("%s\\chart_%d_%s_%04d%02d%02d.jsonl", baseDir, chartNumber, dataType, y, m, d);
  return filename;
}

static void WriteToSpecializedFile(int chartNumber, const char* dataType, const SCString& line, const char* baseDir = "D:\\MIA_IA_system") {
  EnsureOutDir(baseDir);
  const SCString filename = DailyFilenameForChartType(chartNumber, dataType, baseDir);
  FILE* f = fopen(filename.GetChars(), "a");
  if (f) { fprintf(f, "%s\n", line.GetChars()); fclose(f); }
}

// Ecriture debug locale dédiée
static inline void WriteDebugLine(int chartNumber, const SCString& msg) {
  SCString line;
  line.Format("%s", msg.GetChars());
  WriteToSpecializedFile(chartNumber, "correlation_test_debug", line);
}

// ========== DEBUG ==========
enum LogLevel { LOG_ERROR = 0, LOG_KEY = 1, LOG_VERBOSE = 2 };

static void DebugLog(SCStudyInterfaceRef& sc, const char* message) {
  sc.AddMessageToLog(message, 1);
}

static inline bool ShouldLog(const SCStudyInterfaceRef& sc, int level) {
  return sc.Input[5].GetInt() >= level;
}

// ========== DÉDUP ==========
struct LastKey { double t = 0.0; double i = -1.0; double cc = 2.0; };
static std::unordered_map<std::string, LastKey> g_LastBySym;

static bool ShouldWriteCC(const SCStudyInterfaceRef& sc, const char* symbol, double t, double i, double cc) {
  std::string key = std::string(symbol) + "|" + std::to_string(sc.ChartNumber);
  LastKey& lk = g_LastBySym[key];
  bool same_ti = (fabs(lk.t - t) < 1e-9) && (fabs(lk.i - i) < 1e-9);
  bool same_cc = (fabs(lk.cc - cc) < 1e-9);
  lk.t = t; lk.i = i; lk.cc = cc;
  return !(same_ti && same_cc);
}

// ========== STUDY ==========
SCSFExport scsf_MIA_Dumper_Correlation_Test(SCStudyInterfaceRef sc)
{
  if (sc.SetDefaults) {
    sc.GraphName = "MIA - Correlation Dumper (Test)";
    sc.AutoLoop = 0;
    sc.FreeDLL = 0;
    sc.UpdateAlways = 1; // appeler même sans nouveau tick/barre

    // Inputs
    sc.Input[1].Name = "Correlation Study ID (0=off)"; sc.Input[1].SetInt(4);
    sc.Input[2].Name = "Correlation Subgraph Index";  sc.Input[2].SetInt(0);
    sc.Input[3].Name = "Emit Interval (minutes; 0=every bar)"; sc.Input[3].SetInt(1);
    sc.Input[4].Name = "On New Bar Only (0/1)"; sc.Input[4].SetInt(0);
    sc.Input[5].Name = "Debug Log Level (0=Off,1=Key,2=Verbose)"; sc.Input[5].SetInt(1);

    return;
  }

  // Ne pas bloquer en mode historique/replay
  // if (sc.ServerConnectionState != SCS_CONNECTED) return;
  if (sc.ArraySize <= 0) return;

  const int i = sc.ArraySize - 1;
  const SCDateTime cur_time = sc.BaseDateTimeIn[i];
  const SCDateTime now_time = sc.CurrentSystemDateTime;
  const double tsec_bar = cur_time.GetAsDouble();
  const double tsec_now = now_time.GetAsDouble();
  const double barIndex = (double)i;
  const char* symbol = sc.Symbol.GetChars();

  const int study_id = sc.Input[1].GetInt();
  const int sg_index = sc.Input[2].GetInt();
  const int emit_min  = sc.Input[3].GetInt();
  const bool on_new_bar = (sc.Input[4].GetInt() != 0);

  static SCDateTime s_last_emit_time(0.0);
  static SCDateTime s_last_bar_time(0.0);
  static bool s_debug_inited = false;

  if (!s_debug_inited && ShouldLog(sc, LOG_KEY)) {
    SCString m; m.Format("G10-CT: init chart=%d study_id=%d sg=%d emit_min=%d on_new_bar=%d",
                         sc.ChartNumber, study_id, sg_index, emit_min, (int)on_new_bar);
    DebugLog(sc, m.GetChars());
    WriteDebugLine(sc.ChartNumber, m);
    s_debug_inited = true;
  }

  // Gate new bar
  if (on_new_bar) {
    if (cur_time == s_last_bar_time) return;
    s_last_bar_time = cur_time;
  }

  // Gate interval (minutes) basé sur l'horloge système (conversion jours -> secondes)
  if (emit_min > 0) {
    const double dt_sec = (tsec_now - s_last_emit_time.GetAsDouble()) * (double)SECONDS_PER_DAY;
    if (dt_sec < emit_min * 60.0) return;
  }

  if (study_id <= 0) return;

  SCFloatArray arr;
  // Lire l'étude par ID explicite (évite les tableaux vides)
  sc.GetStudyArrayUsingID(study_id, sg_index, arr);
  if (arr.GetArraySize() <= i) {
    if (ShouldLog(sc, LOG_KEY)) {
      SCString m; m.Format("G10-CT: study_id=%d sg=%d introuvable ou trop court (arr=%d, i=%d)",
                           study_id, sg_index, arr.GetArraySize(), i);
      DebugLog(sc, m.GetChars());
      WriteDebugLine(sc.ChartNumber, m);
    }
    return;
  }

  const double cc = arr[i];
  if (!std::isfinite(cc)) {
    if (ShouldLog(sc, LOG_KEY)) {
      SCString m; m.Format("G10-CT: invalid CC (NaN/Inf) at i=%d", i);
      DebugLog(sc, m.GetChars());
      WriteDebugLine(sc.ChartNumber, m);
    }
    return;
  }

  // Clamp facultatif dans [-1,1]
  double cc_clamped = cc;
  if (cc_clamped < -1.0) cc_clamped = -1.0;
  if (cc_clamped >  1.0) cc_clamped =  1.0;

  // Choisir le timestamp: si intervalle actif, on utilise l'heure système
  const double t_emit = (emit_min > 0 ? tsec_now : tsec_bar);
  if (!ShouldWriteCC(sc, symbol, t_emit, barIndex, cc_clamped)) return;

  // Émission
  SCString j;
  j.Format("{\"t\":%.6f,\"sym\":\"%s\",\"type\":\"correlation\",\"cc\":%.6f,\"study_id\":%d,\"sg\":%d,\"i\":%.0f,\"chart\":%d}",
           t_emit, symbol, cc_clamped, study_id, sg_index, barIndex, sc.ChartNumber);
  WriteToSpecializedFile(sc.ChartNumber, "correlation_test", j);

  s_last_emit_time = (emit_min > 0 ? now_time : cur_time);

  if (ShouldLog(sc, LOG_KEY)) {
    SCString m; m.Format("G10-CT: CC=%.6f (study=%d, sg=%d, i=%.0f)", cc_clamped, study_id, sg_index, barIndex);
    DebugLog(sc, m.GetChars());
    WriteDebugLine(sc.ChartNumber, m);
  }
}


