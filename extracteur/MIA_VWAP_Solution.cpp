// MIA_VWAP_Solution.cpp
// Module autonome pour exporter un VWAP fiable (alignement temps robuste)
// - Ne touche PAS au dumper principal
// - Objectif: écrire un fichier JSONL propre: chart_{chart}_vwap_solution_{YYYYMMDD}.jsonl
// - Stratégie: bucket par minute + nearest-time (tolérance ms) pour appairer au temps des barres

#include <cstdio>
#include <cstdlib>
#include <cmath>
#include <cstring>
#include <string>
#include <vector>
#include <algorithm>

// --- ACSIL (Sierra Chart) ---
// Pour une compilation en Custom Study, inclure l'en-tête Sierra et déclarer SCDLLName
#ifdef _WIN32
#include "sierrachart.h"
SCDLLName("MIA_VWAP_Solution")
#endif

// NOTE: Ce fichier est un squelette. Il suppose un environnement ACSIL (Sierra Chart).
// Adaptez les includes Sierra (scstudyfunctions.h, sierrachart.h) et le linkage à votre projet d'études personnalisées.
// Les appels à ReadSubgraph / WriteToSpecializedFile doivent être reliés à vos helpers existants si disponibles.

// ------------------------
// Helpers simples JSON
// ------------------------
static inline void json_write_kv(std::string& s, const char* k, const std::string& v, bool last=false) {
    s += '"'; s += k; s += '"'; s += ':'; s += '"'; s += v; s += '"'; if (!last) s += ',';
}
static inline void json_write_kv(std::string& s, const char* k, double v, bool last=false, int prec=8) {
    char buf[64]; std::snprintf(buf, sizeof(buf), "%.*f", prec, v);
    s += '"'; s += k; s += '"'; s += ':'; s += buf; if (!last) s += ',';
}
static inline void json_write_kv(std::string& s, const char* k, int v, bool last=false) {
    char buf[32]; std::snprintf(buf, sizeof(buf), "%d", v);
    s += '"'; s += k; s += '"'; s += ':'; s += buf; if (!last) s += ',';
}

// ------------------------
// Configuration (à relier aux Inputs Sierra)
// ------------------------
struct VwapSolutionConfig {
    int chartNumber = 9;           // CHART_9 par défaut
    int vwapStudyId = 51;          // Nouveau study VWAP à tester
    int vwapSgIndex = 0;           // Subgraph principal VWAP
    int tolMs = 2000;              // Tolérance nearest-time ±ms
    bool bucketPerMinute = true;   // Appariement minute d'abord, puis nearest-time
    std::string symbol;            // ex: "NQZ25_FUT_CME"
    std::string yyyymmdd;          // ex: "20250929"
};

// ------------------------
// Représentation d'un point VWAP (study)
// ------------------------
struct VwapPoint {
    double t;    // secondes style JSON déjà (aligner à votre format)
    double v;    // valeur VWAP
    double up1;  // bandes optionnelles
    double dn1;
    double up2;
    double dn2;
    double up3;
    double dn3;
};

// ------------------------
// PLACEHOLDERS d'accès aux données ACSIL
// A remplacer par vos helpers/ACSIL réels (ReadSubgraph, lecture basedata, etc.)
// ------------------------
static bool load_study_vwap_series(const VwapSolutionConfig& cfg, std::vector<VwapPoint>& out) {
    // TODO: Lire depuis ACSIL: Subgraphs du study cfg.vwapStudyId (sg index cfg.vwapSgIndex et bandes)
    // Remplir out avec (t, v, up1,dn1, up2,dn2, up3,dn3)
    // Retourner true si OK
    (void)cfg; (void)out;
    return false; // squelette
}

static bool load_bar_times_seconds(const VwapSolutionConfig& cfg, std::vector<double>& t_bars) {
    // TODO: Lire la série des barres (basedata) pour ce chart et retourner t en secondes flottantes
    (void)cfg; (void)t_bars;
    return false; // squelette
}

static bool write_jsonl_line(FILE* f, const VwapSolutionConfig& cfg, const VwapPoint& p, double t_bar, int i_bar) {
    std::string s; s.reserve(256);
    s.push_back('{');
    json_write_kv(s, "t", t_bar, false, 6);
    json_write_kv(s, "sym", cfg.symbol, false);
    json_write_kv(s, "type", std::string("vwap"), false);
    json_write_kv(s, "src", std::string("solution"), false);
    json_write_kv(s, "i", i_bar, false);
    json_write_kv(s, "v", p.v, false, 8);
    json_write_kv(s, "up1", p.up1, false, 8);
    json_write_kv(s, "dn1", p.dn1, false, 8);
    json_write_kv(s, "up2", p.up2, false, 8);
    json_write_kv(s, "dn2", p.dn2, false, 8);
    json_write_kv(s, "up3", p.up3, false, 8);
    json_write_kv(s, "dn3", p.dn3, false, 8);
    json_write_kv(s, "study", cfg.vwapStudyId, false);
    json_write_kv(s, "sg", cfg.vwapSgIndex, false);
    json_write_kv(s, "chart", cfg.chartNumber, true);
    s.push_back('}'); s.push_back('\n');
    if (std::fwrite(s.data(), 1, s.size(), f) != s.size()) return false;
    return true;
}

// ------------------------
// Appariements
// ------------------------
static void build_minute_index(const std::vector<VwapPoint>& pts, std::vector<int>& minute_keys, std::vector<int>& idx_by_minute) {
    minute_keys.clear(); idx_by_minute.clear();
    if (pts.empty()) return;
    int last_min = -1; int last_idx = -1;
    for (int i = 0; i < (int)pts.size(); ++i) {
        int m = (int)std::floor(pts[i].t / 60.0);
        if (m != last_min) {
            minute_keys.push_back(m);
            idx_by_minute.push_back(i);
            last_min = m; last_idx = i;
        } else {
            // garder la dernière valeur de la minute
            idx_by_minute.back() = i;
        }
    }
}

static int find_by_minute(const std::vector<int>& minute_keys, const std::vector<int>& idx_by_minute, int minute_key) {
    if (minute_keys.empty()) return -1;
    auto it = std::lower_bound(minute_keys.begin(), minute_keys.end(), minute_key);
    if (it == minute_keys.end()) return -1;
    if (*it != minute_key) return -1;
    int j = (int)std::distance(minute_keys.begin(), it);
    return idx_by_minute[j];
}

static int find_nearest_time(const std::vector<VwapPoint>& pts, double t_bar, int tol_ms) {
    if (pts.empty()) return -1;
    auto cmp = [](const VwapPoint& a, const VwapPoint& b){ return a.t < b.t; };
    auto it = std::lower_bound(pts.begin(), pts.end(), VwapPoint{t_bar,0,0,0,0,0,0,0}, cmp);
    double best_dt = 1e300; int best = -1; auto check=[&](int k){ if (k<0||k>=(int)pts.size()) return; double dt=fabs(pts[k].t - t_bar); if (dt<best_dt){best_dt=dt;best=k;}};
    if (it != pts.end()) check((int)std::distance(pts.begin(), it));
    if (it != pts.begin()) check((int)std::distance(pts.begin(), it-1));
    if (best < 0) return -1;
    if (best_dt*1000.0 > (double)tol_ms) return -1;
    return best;
}

// ------------------------
// Entrée principale (squelette)
// ------------------------
#ifdef STANDALONE_CLI
int main(int argc, char** argv) {
    // Paramètres minimaux via argv (pour tests)
    // Usage: MIA_VWAP_Solution <chart> <symbol> <yyyymmdd> [studyId] [sg] [tolMs]
    VwapSolutionConfig cfg;
    if (argc >= 4) {
        cfg.chartNumber = std::atoi(argv[1]);
        cfg.symbol = argv[2];
        cfg.yyyymmdd = argv[3];
    }
    if (argc >= 5) cfg.vwapStudyId = std::atoi(argv[4]);
    if (argc >= 6) cfg.vwapSgIndex = std::atoi(argv[5]);
    if (argc >= 7) cfg.tolMs = std::atoi(argv[6]);

    std::vector<VwapPoint> study_pts;
    std::vector<double>   bar_times;

    if (!load_study_vwap_series(cfg, study_pts)) {
        std::fprintf(stderr, "[ERR] load_study_vwap_series failed. Configurez le study VWAP.\n");
        return 1;
    }
    if (!load_bar_times_seconds(cfg, bar_times)) {
        std::fprintf(stderr, "[ERR] load_bar_times_seconds failed.\n");
        return 1;
    }
    if (study_pts.empty() || bar_times.empty()) {
        std::fprintf(stderr, "[ERR] empty inputs.\n");
        return 1;
    }

    // Tri par temps
    std::sort(study_pts.begin(), study_pts.end(), [](const VwapPoint& a, const VwapPoint& b){return a.t < b.t;});

    // Index minute
    std::vector<int> minute_keys, idx_by_minute;
    if (cfg.bucketPerMinute) {
        build_minute_index(study_pts, minute_keys, idx_by_minute);
    }

    // Fichier sortie
    std::string out_dir = "DATA_SIERRA_CHART/DATA_"; // ajustez si besoin
    // NB: Dans votre environnement dumper, utilisez votre helper WriteToSpecializedFile.
    char out_path[512];
    std::snprintf(out_path, sizeof(out_path), "CHART_%d/chart_%d_vwap_solution_%s.jsonl", cfg.chartNumber, cfg.chartNumber, cfg.yyyymmdd.c_str());
    FILE* f = std::fopen(out_path, "wb");
    if (!f) { std::perror("fopen"); return 1; }

    int written = 0;
    for (int i = 0; i < (int)bar_times.size(); ++i) {
        double t_bar = bar_times[i];
        int idx = -1;
        if (cfg.bucketPerMinute) {
            int mk = (int)std::floor(t_bar / 60.0);
            idx = find_by_minute(minute_keys, idx_by_minute, mk);
        }
        if (idx < 0) {
            idx = find_nearest_time(study_pts, t_bar, cfg.tolMs);
        }
        if (idx < 0) continue; // pas de match
        if (!write_jsonl_line(f, cfg, study_pts[idx], t_bar, i)) { std::fclose(f); return 1; }
        written++;
    }
    std::fclose(f);
    std::fprintf(stdout, "[OK] VWAP solution ecrite: %s | lignes=%d\n", out_path, written);
    return 0;
}
#endif

// --- Entrée ACSIL (Custom Study) ---
#ifdef _WIN32
SCSFExport scsf_MIA_VWAP_Solution(SCStudyInterfaceRef sc)
{
    // Inputs simples (ID, SG, tol, minute-bucket)
    SCInputRef InStudyID      = sc.Input[0];
    SCInputRef InSubgraph     = sc.Input[1];
    SCInputRef InTolMs        = sc.Input[2];
    SCInputRef InMinuteBucket = sc.Input[3];

    if (sc.SetDefaults)
    {
        sc.GraphName = "MIA_VWAP_Solution";
        sc.AutoLoop = 0; // gestion manuelle
        sc.GraphRegion = 0;
        sc.HideStudy = true; // étude utilitaire (pas d'affichage)

        InStudyID.Name = "VWAP Study ID";
        InStudyID.SetInt(51);

        InSubgraph.Name = "VWAP Subgraph Index";
        InSubgraph.SetInt(0);

        InTolMs.Name = "Nearest-Time Tolerance (ms)";
        InTolMs.SetInt(2000);

        InMinuteBucket.Name = "Use Minute Bucket";
        InMinuteBucket.SetYesNo(1);

        return;
    }

    // Config à partir des inputs
    VwapSolutionConfig cfg;
    cfg.chartNumber    = sc.ChartNumber;
    cfg.symbol         = sc.Symbol.GetChars();
    // yyyymmdd best-effort depuis la date de session courante
    SCDateTime dt = sc.BaseDateTimeIn[sc.ArraySize-1];
    int y = dt.GetYear(); int m = dt.GetMonth(); int d = dt.GetDay();
    char buf[16]; std::snprintf(buf, sizeof(buf), "%04d%02d%02d", y, m, d);
    cfg.yyyymmdd       = buf;
    cfg.vwapStudyId    = InStudyID.GetInt();
    cfg.vwapSgIndex    = InSubgraph.GetInt();
    cfg.tolMs          = InTolMs.GetInt();
    cfg.bucketPerMinute= InMinuteBucket.GetYesNo() != 0;

    // Charger données depuis ACSIL
    std::vector<VwapPoint> study_pts;
    std::vector<double> bar_times;

    // Bar times (secondes depuis minuit, cohérent avec l'unifier)
    bar_times.reserve(sc.ArraySize);
    for (int i = 0; i < sc.ArraySize; ++i)
    {
        double t_sec  = (double)sc.BaseDateTimeIn[i].GetTimeInSeconds();
        bar_times.push_back(t_sec);
    }
    if (bar_times.empty())
    {
        sc.AddMessageToLog("MIA_VWAP_Solution: aucune barre (BaseDateTimeIn vide)", 1);
        return;
    }

    // Lecture study arrays
    SCFloatArray vArr, up1Arr, dn1Arr, up2Arr, dn2Arr, up3Arr, dn3Arr;
    bool okV = sc.GetStudyArrayUsingID(cfg.vwapStudyId, cfg.vwapSgIndex, vArr) != 0;
    // Bandes (indices usuels 1..6). Si indisponibles, elles resteront à 0
    sc.GetStudyArrayUsingID(cfg.vwapStudyId, cfg.vwapSgIndex + 1, up1Arr);
    sc.GetStudyArrayUsingID(cfg.vwapStudyId, cfg.vwapSgIndex + 2, dn1Arr);
    sc.GetStudyArrayUsingID(cfg.vwapStudyId, cfg.vwapSgIndex + 3, up2Arr);
    sc.GetStudyArrayUsingID(cfg.vwapStudyId, cfg.vwapSgIndex + 4, dn2Arr);
    sc.GetStudyArrayUsingID(cfg.vwapStudyId, cfg.vwapSgIndex + 5, up3Arr);
    sc.GetStudyArrayUsingID(cfg.vwapStudyId, cfg.vwapSgIndex + 6, dn3Arr);

    if (!okV || vArr.GetArraySize() == 0)
    {
        sc.AddMessageToLog("MIA_VWAP_Solution: impossible de lire le subgraph VWAP (vArr)", 1);
        return;
    }

    study_pts.reserve(sc.ArraySize);
    for (int i = 0; i < sc.ArraySize; ++i)
    {
        double t_sec  = (double)sc.BaseDateTimeIn[i].GetTimeInSeconds();
        double v  = vArr[i];
        double u1 = (up1Arr.GetArraySize() == vArr.GetArraySize()) ? (double)up1Arr[i] : 0.0;
        double d1 = (dn1Arr.GetArraySize() == vArr.GetArraySize()) ? (double)dn1Arr[i] : 0.0;
        double u2 = (up2Arr.GetArraySize() == vArr.GetArraySize()) ? (double)up2Arr[i] : 0.0;
        double d2 = (dn2Arr.GetArraySize() == vArr.GetArraySize()) ? (double)dn2Arr[i] : 0.0;
        double u3 = (up3Arr.GetArraySize() == vArr.GetArraySize()) ? (double)up3Arr[i] : 0.0;
        double d3 = (dn3Arr.GetArraySize() == vArr.GetArraySize()) ? (double)dn3Arr[i] : 0.0;
        VwapPoint p{t_sec, v, u1, d1, u2, d2, u3, d3};
        study_pts.push_back(p);
    }
    if (study_pts.empty())
    {
        sc.AddMessageToLog("MIA_VWAP_Solution: aucune donnée study VWAP", 1);
        return;
    }

    std::sort(study_pts.begin(), study_pts.end(), [](const VwapPoint& a, const VwapPoint& b){return a.t < b.t;});

    std::vector<int> minute_keys, idx_by_minute;
    if (cfg.bucketPerMinute)
        build_minute_index(study_pts, minute_keys, idx_by_minute);

    // Throttling: écrire UNE seule ligne par changement de minute
    static int s_last_written_minute = -1;
    static int s_last_written_index  = -1;

    // Prendre uniquement la dernière barre
    const int i = sc.ArraySize - 1;
    if (i < 0) return;
    double t_bar = bar_times[i];
    int minute_key = (int)std::floor(t_bar / 60.0);
    if (minute_key == s_last_written_minute && s_last_written_index == i)
        return; // déjà écrit pour cette minute/barre

    int idx = -1;
    if (cfg.bucketPerMinute)
    {
        idx = find_by_minute(minute_keys, idx_by_minute, minute_key);
    }
    if (idx < 0)
        idx = find_nearest_time(study_pts, t_bar, cfg.tolMs);
    if (idx < 0)
        return;

    // Ecriture JSONL (utiliser votre helper WriteToSpecializedFile si dispo)
    char out_path[1024];
    std::snprintf(out_path, sizeof(out_path),
        "D:/MIA_IA_system/DATA_SIERRA_CHART/DATA_%04d/SEPTEMBRE/%s/CHART_%d/chart_%d_vwap_solution_%s.jsonl",
        y, cfg.yyyymmdd.c_str(), cfg.chartNumber, cfg.chartNumber, cfg.yyyymmdd.c_str());
    FILE* f = std::fopen(out_path, "ab");
    if (!f)
    {
        sc.AddMessageToLog("MIA_VWAP_Solution: fopen sortie echoue", 1);
        return;
    }
    if (write_jsonl_line(f, cfg, study_pts[idx], t_bar, i))
    {
        s_last_written_minute = minute_key;
        s_last_written_index  = i;
    }
    std::fclose(f);
}
#endif


