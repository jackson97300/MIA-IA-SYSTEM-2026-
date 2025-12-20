\
    // MIA_TnS_Dumper.cpp
    // ACSIL study — Generic Time&Sales dumper (Trades + optional Quotes)
    // Compatible with Sierra Chart (64-bit). Uses only standard C/C++ + WinAPI for FS.
    //
    #include "sierrachart.h"
    #include <windows.h>
    #include <cstdio>
    #include <cstring>
    #include <string>

    SCDLLName("MIA • TnS Dumper (Generic)")

    struct MIA_FilePaths {
        SCString trades_path;
        SCString quotes_path;
        int y=0,m=0,d=0;
    };

    // -------- Debug file helpers --------
    static void MIA_EnsureDirWin(const char* dir) {
        CreateDirectoryA(dir, NULL);
    }

    static SCString MIA_DebugPathForNow() {
        SYSTEMTIME st; GetLocalTime(&st);
        char buf[64];
        std::snprintf(buf, sizeof(buf), "debug_tns_%04d%02d%02d.log", (int)st.wYear, (int)st.wMonth, (int)st.wDay);
        SCString path = "D\\:MIA_IA_system"; // placeholder to keep length
        path = "D:\\MIA_IA_system\\"; path += buf; return path;
    }

    static void MIA_AppendDebug(const SCString& line) {
        MIA_EnsureDirWin("D:\\MIA_IA_system");
        const SCString path = MIA_DebugPathForNow();
        FILE* f = nullptr;
        #ifdef _MSC_VER
            fopen_s(&f, path.GetChars(), "ab");
        #else
            f = std::fopen(path.GetChars(), "ab");
        #endif
        if (!f) return;
        const char* data = line.GetChars();
        std::fwrite(data, 1, std::strlen(data), f);
        std::fwrite("\n", 1, 1, f);
        std::fclose(f);
    }

    static void MIA_GetDateYMD(SCDateTime dt, int& y, int& m, int& d) {
        y = dt.GetYear();
        m = dt.GetMonth();
        d = dt.GetDay();
    }

    // (kept above)

    static SCString MIA_MakeDailyPath(const SCString& baseDir, int chartNum, const char* kind, int y, int m, int d) {
        std::string out(baseDir.GetChars());
        if (!out.empty()) {
            char last = out[out.size()-1];
            if (last != '\\' && last != '/')
                out.push_back('\\');
        }
        char buf[128];
        std::snprintf(buf, sizeof(buf), "chart_%d_%s_%04d%02d%02d.jsonl", chartNum, kind, y, m, d);
        out += buf;
        return SCString(out.c_str());
    }

    static double MIA_ToSecondsOfDay(SCDateTime t) {
        int h = t.GetHour();
        int mn = t.GetMinute();
        int s = t.GetSecond();
        int ms = (int)(t.GetMillisecond());
        return (double)h*3600.0 + (double)mn*60.0 + (double)s + (double)ms/1000.0;
    }

    static void MIA_AppendJSONL_C(const SCString& path, const SCString& line) {
        FILE* f = nullptr;
        #ifdef _MSC_VER
            fopen_s(&f, path.GetChars(), "ab");
        #else
            f = std::fopen(path.GetChars(), "ab");
        #endif
        if (!f) return;
        const char* data = line.GetChars();
        std::fwrite(data, 1, std::strlen(data), f);
        std::fclose(f);
    }

    static bool MIA_IsQuoteEvent(int type) {
        // Sur ce flux/SDK, seuls les BIDASKVALUES (tt=6) doivent être traités comme quotes.
        // Les tt=1/2 (Bid/Ask Trade) sont considérés comme non-quote afin d'être exportés en trades.
        return type == SC_TS_BIDASKVALUES;
    }

    SCSFExport scsf_MIA_TnS_Dumper_Generic(SCStudyInterfaceRef sc) {
        SCInputRef inExportTrades        = sc.Input[0];
        SCInputRef inExportQuotes        = sc.Input[1];
        SCInputRef inOutputDir           = sc.Input[2];
        SCInputRef inTouchAtStartup      = sc.Input[3];
        SCInputRef inDebugThrottle       = sc.Input[4];
        SCInputRef inStrictTradeTypes    = sc.Input[5];
        SCInputRef inAllowTT1            = sc.Input[6];
        SCInputRef inAllowTT2            = sc.Input[7];
        SCInputRef inAllowTT3            = sc.Input[8];
        SCInputRef inConvertQuotesToTrades = sc.Input[9];
        SCInputRef inDebugTypesPeriod    = sc.Input[10];
        SCInputRef inWriteDebugFile      = sc.Input[11];

        if (sc.SetDefaults) {
            sc.GraphName = "MIA • TnS Dumper (Generic)";
            sc.AutoLoop = 0;
            sc.UpdateAlways = 1;

            inExportTrades.Name = "Export Trades";
            inExportTrades.SetYesNo(true);

            inExportQuotes.Name = "Export Quotes (Bid/Ask changes)";
            inExportQuotes.SetYesNo(false);

            inOutputDir.Name = "Output Directory";
            inOutputDir.SetString("D:\\MIA_IA_system");

            inTouchAtStartup.Name = "Touch files at startup";
            inTouchAtStartup.SetYesNo(true);

            inDebugThrottle.Name = "Debug throttle (iterations)";
            inDebugThrottle.SetInt(60);

            inStrictTradeTypes.Name = "Strict Trade Types Only";
            inStrictTradeTypes.SetYesNo(true);

            inAllowTT1.Name = "Allow tt=1 (Bid Trade)";
            inAllowTT1.SetYesNo(true);

            inAllowTT2.Name = "Allow tt=2 (Ask Trade)";
            inAllowTT2.SetYesNo(true);

            inAllowTT3.Name = "Allow tt=3 (Generic Trade)";
            inAllowTT3.SetYesNo(false);

            inConvertQuotesToTrades.Name = "Convert Quotes To Trades (diagnostic)";
            inConvertQuotesToTrades.SetYesNo(false);

            inDebugTypesPeriod.Name = "Debug Types Period (0=off)";
            inDebugTypesPeriod.SetInt(300);

            inWriteDebugFile.Name = "Write Debug File (Yes/No)";
            inWriteDebugFile.SetYesNo(true);

            return;
        }

        // Persistent state
        int& initiated          = sc.GetPersistentInt(0);
        uint32_t& lastSeq       = (uint32_t&)sc.GetPersistentIntFast(1);
        int& lastIdx            = sc.GetPersistentIntFast(2);
        int& seenQuotes         = sc.GetPersistentIntFast(3);
        int& seenTrades         = sc.GetPersistentIntFast(4);
        int& writtenTrades      = sc.GetPersistentIntFast(5);
        int& writtenQuotes      = sc.GetPersistentIntFast(6);
        int& dbgCounter         = sc.GetPersistentIntFast(7);
        int& useSeq             = sc.GetPersistentIntFast(8);

        // Store file paths (use study persistent pointer)
        MIA_FilePaths* fp = (MIA_FilePaths*)sc.GetPersistentPointer(0);
        if (fp == nullptr) {
            fp = new MIA_FilePaths();
            sc.SetPersistentPointer(0, fp);
        }

        const bool doTrades           = inExportTrades.GetYesNo();
        const bool doQuotes           = inExportQuotes.GetYesNo();
        const SCString baseDir        = inOutputDir.GetString();
        const bool touchStartup       = inTouchAtStartup.GetYesNo();
        const int debugEvery          = inDebugThrottle.GetInt() <= 0 ? 60 : inDebugThrottle.GetInt();
        const bool strictTradeTypes   = inStrictTradeTypes.GetYesNo();
        const bool allowTT1           = inAllowTT1.GetYesNo();
        const bool allowTT2           = inAllowTT2.GetYesNo();
        const bool allowTT3           = inAllowTT3.GetYesNo();
        const bool convertQToTrades   = inConvertQuotesToTrades.GetYesNo();
        const int debugTypesPeriod    = inDebugTypesPeriod.GetInt();
        const bool writeDebugFile     = inWriteDebugFile.GetYesNo();

        if (!initiated) {
            initiated = 1;
            lastSeq = 0;
            lastIdx = 0;
            seenQuotes = 0;
            seenTrades = 0;
            writtenTrades = 0;
            writtenQuotes = 0;
            dbgCounter = 0;
            useSeq = 0;

            // Ensure base directory exists (single-level create)
            MIA_EnsureDirWin(baseDir.GetChars());

            int y,m,d;
            MIA_GetDateYMD(sc.CurrentSystemDateTime, y,m,d);
            fp->y=y; fp->m=m; fp->d=d;
            fp->trades_path = MIA_MakeDailyPath(baseDir, sc.ChartNumber, "trade", y,m,d);
            fp->quotes_path = MIA_MakeDailyPath(baseDir, sc.ChartNumber, "quote", y,m,d);

            if (touchStartup) {
                MIA_AppendJSONL_C(fp->trades_path, "");
                MIA_AppendJSONL_C(fp->quotes_path, "");
            }

            SCString startMsg;
            startMsg.Format(
                "TnS Dumper START — chart=%d dir=%s | Trades=%d Quotes=%d Strict=%d AllowTT1=%d AllowTT2=%d AllowTT3=%d ConvertQ2T=%d DebugEvery=%d DebugTypes=%d",
                sc.ChartNumber,
                baseDir.GetChars(),
                (int)doTrades,
                (int)doQuotes,
                (int)strictTradeTypes,
                (int)allowTT1,
                (int)allowTT2,
                (int)allowTT3,
                (int)convertQToTrades,
                debugEvery,
                debugTypesPeriod
            );
            sc.AddMessageToLog(startMsg, 0);
            if (writeDebugFile) MIA_AppendDebug(startMsg);
        }

        // Roll files when day changes
        int y,m,d;
        MIA_GetDateYMD(sc.CurrentSystemDateTime, y,m,d);
        if (y!=fp->y || m!=fp->m || d!=fp->d) {
            fp->y=y; fp->m=m; fp->d=d;
            fp->trades_path = MIA_MakeDailyPath(baseDir, sc.ChartNumber, "trade", y,m,d);
            fp->quotes_path = MIA_MakeDailyPath(baseDir, sc.ChartNumber, "quote", y,m,d);
        }

        // Read Time & Sales
        c_SCTimeAndSalesArray TnS;
        sc.GetTimeAndSales(TnS);
        const int sz = (int)TnS.Size();
        if (lastIdx > sz) lastIdx = 0; // purge protection

        // Detect Sequence availability (any recent record with non-zero Sequence)
        if (useSeq == 0) {
            int start = sz > 64 ? (sz - 64) : 0;
            for (int i = start; i < sz; ++i) {
                if (TnS[i].Sequence != 0) { useSeq = 1; break; }
            }
        }

        int processed = 0;
        // Debug: compteurs de rejets (strict)
        static int rejectedStrictTotal = 0;
        static int rejectedStrictByTT[16] = {0}; // pour tt 0..15, sinon agrégé dans [15]

        auto write_trade = [&](const s_TimeAndSales& ts) {
            double tsec = MIA_ToSecondsOfDay(ts.DateTime);
            SCString line;
            line.Format("{\"type\":\"trade\",\"t\":%.3f,\"price\":%.10g,\"vol\":%u,\"bid\":%.10g,\"ask\":%.10g,\"tt\":%d,\"seq\":%u}\n",
                        tsec, ts.Price, ts.Volume, ts.Bid, ts.Ask, (int)ts.Type, (unsigned)ts.Sequence);
            MIA_AppendJSONL_C(fp->trades_path, line);
            ++writtenTrades;
        };

        auto write_quote = [&](const s_TimeAndSales& ts) {
            double tsec = MIA_ToSecondsOfDay(ts.DateTime);
            SCString line;
            line.Format("{\"type\":\"quote\",\"t\":%.3f,\"bid\":%.10g,\"ask\":%.10g,\"bidsz\":%u,\"asksz\":%u}\n",
                        tsec, ts.Bid, ts.Ask, ts.BidSize, ts.AskSize);
            MIA_AppendJSONL_C(fp->quotes_path, line);
            ++writtenQuotes;
        };

        if (useSeq == 1) {
            // Sequence-driven
            int start = sz > 512 ? (sz - 512) : 0;
            for (int i = start; i < sz; ++i) {
                const s_TimeAndSales& ts = TnS[i];
                if (ts.Sequence <= (uint32_t)lastSeq) continue;
                lastSeq = ts.Sequence;

                const int tt = (int)ts.Type;
                const bool isQuote = MIA_IsQuoteEvent(tt);
                if (isQuote) {
                    ++seenQuotes;
                    if (doQuotes) write_quote(ts);
                } else {
                    bool allowed = true;
                    if (strictTradeTypes) {
                        allowed = ( (tt==1 && allowTT1) || (tt==2 && allowTT2) || (tt==3 && allowTT3) );
                    }
                    if (allowed && ts.Price > 0 && ts.Volume > 0) {
                        ++seenTrades;
                        if (doTrades) write_trade(ts);
                    } else if (strictTradeTypes) {
                        // Rejeté par filtre strict: on compte et on loggue périodiquement
                        ++rejectedStrictTotal;
                        const int idx = (tt >=0 && tt < 15) ? tt : 15;
                        ++rejectedStrictByTT[idx];
                        if ((rejectedStrictTotal % 200) == 0) {
                            SCString m;
                            m.Format("TnS DEBUG REJECT(strict): total=%d tt=%d price=%.10g vol=%u seq=%u",
                                     rejectedStrictTotal, tt, ts.Price, ts.Volume, (unsigned)ts.Sequence);
                            sc.AddMessageToLog(m, 0);
                            if (writeDebugFile) MIA_AppendDebug(m);
                        }
                    }
                }
                ++processed;
            }
        } else {
            // Index fallback
            for (int i = lastIdx; i < sz; ++i) {
                const s_TimeAndSales& ts = TnS[i];
                const int tt = (int)ts.Type;
                const bool isQuote = MIA_IsQuoteEvent(tt);
                if (isQuote) {
                    ++seenQuotes;
                    if (doQuotes) write_quote(ts);
                } else {
                    bool allowed = true;
                    if (strictTradeTypes) {
                        allowed = ( (tt==1 && allowTT1) || (tt==2 && allowTT2) || (tt==3 && allowTT3) );
                    }
                    if (allowed && ts.Price > 0 && ts.Volume > 0) {
                        ++seenTrades;
                        if (doTrades) write_trade(ts);
                    } else if (strictTradeTypes) {
                        ++rejectedStrictTotal;
                        const int idx = (tt >=0 && tt < 15) ? tt : 15;
                        ++rejectedStrictByTT[idx];
                        if ((rejectedStrictTotal % 200) == 0) {
                            SCString m;
                            m.Format("TnS DEBUG REJECT(strict): total=%d tt=%d price=%.10g vol=%u seq=%u",
                                     rejectedStrictTotal, tt, ts.Price, ts.Volume, (unsigned)ts.Sequence);
                            sc.AddMessageToLog(m, 0);
                        }
                    }
                }
                ++processed;
            }
            lastIdx = sz;
        }

        // DEBUG (throttled)
        if (++dbgCounter >= debugEvery) {
            dbgCounter = 0;
            SCString msg;
            msg.Format("TnS DEBUG: sz=%d, processed=%d, lastIdx=%d, useSeq=%d, lastSeq=%u, seenQuotes=%d, seenTrades=%d, writtenTrades=%d, writtenQuotes=%d",
                       sz, processed, lastIdx, useSeq, (unsigned)lastSeq, seenQuotes, seenTrades, writtenTrades, writtenQuotes);
            sc.AddMessageToLog(msg, 0);
            if (writeDebugFile) MIA_AppendDebug(msg);
            // Récap des rejets stricts
            if (strictTradeTypes && rejectedStrictTotal > 0) {
                SCString m3;
                m3.Format("TnS DEBUG REJECT(strict) SUMMARY: total=%d | tt0=%d tt1=%d tt2=%d tt3=%d tt4=%d tt5=%d tt6=%d tt7=%d tt8=%d tt9=%d tt10=%d tt11=%d tt12=%d tt13=%d tt14=%d tt15+=%d",
                          rejectedStrictTotal,
                          rejectedStrictByTT[0], rejectedStrictByTT[1], rejectedStrictByTT[2], rejectedStrictByTT[3],
                          rejectedStrictByTT[4], rejectedStrictByTT[5], rejectedStrictByTT[6], rejectedStrictByTT[7],
                          rejectedStrictByTT[8], rejectedStrictByTT[9], rejectedStrictByTT[10], rejectedStrictByTT[11],
                          rejectedStrictByTT[12], rejectedStrictByTT[13], rejectedStrictByTT[14], rejectedStrictByTT[15]);
                sc.AddMessageToLog(m3, 0);
                if (writeDebugFile) MIA_AppendDebug(m3);
            }
            // Optionnel: dump périodique des distributions de tt (léger)
            if (debugTypesPeriod > 0) {
                static int tick=0; if ((++tick % debugTypesPeriod)==0) {
                    // Compter sur la fenêtre récente
                    int c1=0,c2=0,c3=0,c6=0,cOther=0;
                    int start = sz > 256 ? (sz-256) : 0;
                    for (int i=start;i<sz;++i){int tti=(int)TnS[i].Type; if (tti==1) ++c1; else if (tti==2) ++c2; else if (tti==3) ++c3; else if (tti==6) ++c6; else ++cOther;}
                    SCString m2; m2.Format("TnS TYPES: last256 tt1=%d tt2=%d tt3=%d tt6=%d other=%d", c1,c2,c3,c6,cOther);
                    sc.AddMessageToLog(m2,0);
                    if (writeDebugFile) MIA_AppendDebug(m2);
                }
            }
        }

        return;
    }
