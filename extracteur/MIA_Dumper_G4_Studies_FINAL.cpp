// MIA_Dumper_G4_Studies_FINAL.cpp
// ACSIL — Sierra Chart
// VERSION FINALE avec mapping correct et déduplication du G3
// Dump JSONL: chart_4_*_YYYYMMDD.jsonl

#include "sierrachart.h"
SCDLLName("MIA Dumper G4 Studies FINAL")

#include <stdio.h>
#include <string>
#include <unordered_map>
#include <algorithm>

static SCString g_OutputDir;

// ========== STRUCTURES DE DÉDUPLICATION (COPIÉES DU G3) ==========
struct LastData {
  std::string payload;
  int lastIndex = -1;
  bool hasData = false;
};

static std::unordered_map<std::string, LastData> g_LastDataByKey;

// ========== FONCTIONS UTILITAIRES (COPIÉES DU G3) ==========
static bool ReadSubgraph(SCStudyInterfaceRef& sc, int studyID, int subgraphIndex, SCFloatArray& array, int chartNumber = -1) {
  if (chartNumber > 0) {
    sc.GetStudyArrayFromChartUsingID(chartNumber, studyID, subgraphIndex, array);
    return array.GetArraySize() > 0;
  } else {
    sc.GetStudyArrayUsingID(studyID, subgraphIndex, array);
    return array.GetArraySize() > 0;
  }
}

static bool ShouldWriteDataWithType(SCStudyInterfaceRef& sc, const std::string& dataType, const std::string& payload, int currentIndex) {
  std::string key = sc.Symbol + "|" + dataType;
  auto& lastData = g_LastDataByKey[key];
  
  bool shouldWrite = false;
  
  if (!lastData.hasData) {
    shouldWrite = true;
  } else if (payload != lastData.payload) {
    shouldWrite = true;
  } else if (currentIndex != lastData.lastIndex) {
    shouldWrite = true;
  }
  
  if (shouldWrite) {
    lastData.payload = payload;
    lastData.lastIndex = currentIndex;
    lastData.hasData = true;
  }
  
  return shouldWrite;
}

static void WriteToSpecializedFile(SCStudyInterfaceRef& sc, const std::string& dataType, const std::string& jsonData) {
  SCString filename;
  filename.Format("%s\\chart_4_%s_%04d%02d%02d.jsonl", 
    g_OutputDir.GetChars(), 
    dataType.c_str(),
    sc.GetCurrentDateTime().GetYear(),
    sc.GetCurrentDateTime().GetMonth(),
    sc.GetCurrentDateTime().GetDay()
  );
  
  FILE* file = fopen(filename.GetChars(), "a");
  if (file) {
    fprintf(file, "%s\n", jsonData.c_str());
    fclose(file);
  }
}

// ========== FONCTION PRINCIPALE ==========
SCSFExport scsf_MIA_Dumper_G4_Studies_FINAL(SCStudyInterfaceRef sc)
{
  SCInputRef OutDir = sc.Input[0];
  SCInputRef SymbolOverride = sc.Input[1];
  
  // Study IDs CORRECTS selon l'inventaire
  SCInputRef VWAP_ID = sc.Input[2];
  SCInputRef VVA_ID = sc.Input[3];
  SCInputRef VVA_PREV_ID = sc.Input[4];
  SCInputRef PREV_VP_ID = sc.Input[5];
  SCInputRef PREV_VWAP_ID = sc.Input[6];
  SCInputRef CORR_ID = sc.Input[7];
  SCInputRef ATR_ID = sc.Input[8];
  SCInputRef NBCV_ID = sc.Input[9];
  SCInputRef CUM_DELTA_ID = sc.Input[10];
  SCInputRef VOL_PROFILE_ID = sc.Input[11];
  SCInputRef OHLC_ID = sc.Input[12];

  if (sc.SetDefaults)
  {
    sc.GraphName = "MIA Dumper G4 Studies FINAL";
    sc.StudyDescription = "Dumper Chart 4 avec mapping correct et déduplication";
    sc.AutoLoop = 0;
    sc.UpdateAlways = 1;
    sc.CalculationPrecedence = LOW_PREC_LEVEL;

    OutDir.Name = "Output Directory";
    OutDir.SetString("D:\\MIA_IA_system");

    SymbolOverride.Name = "Symbol Override (optional)";
    SymbolOverride.SetString("");

    // MAPPING CORRECT selon l'inventaire des études
    VWAP_ID.Name = "VWAP Study ID";
    VWAP_ID.SetInt(1);        // Study ID 1: VWAP

    VVA_ID.Name = "VVA Study ID";
    VVA_ID.SetInt(8);         // Study ID 8: Volume Value Area Lines

    VVA_PREV_ID.Name = "VVA Previous Study ID";
    VVA_PREV_ID.SetInt(9);    // Study ID 9: Volume Value Area Previous

    PREV_VP_ID.Name = "Previous VP Study ID";
    PREV_VP_ID.SetInt(2);     // Study ID 2: PREVIOUS VPOC VAH VAL

    PREV_VWAP_ID.Name = "Previous VWAP Study ID";
    PREV_VWAP_ID.SetInt(3);   // Study ID 3: PREVIOUS VWAP SD+1 SD-1

    CORR_ID.Name = "Correlation Study ID";
    CORR_ID.SetInt(15);       // Study ID 15: Correlation Coefficient

    ATR_ID.Name = "ATR Study ID";
    ATR_ID.SetInt(5);         // Study ID 5: Average True Range

    NBCV_ID.Name = "NBCV Study ID";
    NBCV_ID.SetInt(14);       // Study ID 14: Numbers Bars Calculated Values

    CUM_DELTA_ID.Name = "Cumulative Delta Study ID";
    CUM_DELTA_ID.SetInt(6);   // Study ID 6: Cumulative Delta Bars

    VOL_PROFILE_ID.Name = "Volume Profile Study ID";
    VOL_PROFILE_ID.SetInt(13); // Study ID 13: MULTIPLE VOLUME PROFILE

    OHLC_ID.Name = "OHLC Study ID";
    OHLC_ID.SetInt(16);       // Study ID 16: Overlay OHLC

    return;
  }

  // ========== TRAITEMENT PRINCIPAL ==========
  g_OutputDir = OutDir.GetString();
  
  SCString symbol = SymbolOverride.GetString();
  if (symbol.GetLength() == 0) {
    symbol = sc.Symbol;
  }

  int currentIndex = sc.Index;
  double currentTime = sc.CurrentDateTimeAsDouble();

  // ========== 1. VWAP (Study ID 1) ==========
  SCFloatArray vwapArray, sd1Array, sd2Array, sd3Array, sd4Array, sd5Array, sd6Array;
  if (ReadSubgraph(sc, VWAP_ID.GetInt(), 0, vwapArray, 4) &&
      ReadSubgraph(sc, VWAP_ID.GetInt(), 1, sd1Array, 4) &&
      ReadSubgraph(sc, VWAP_ID.GetInt(), 2, sd2Array, 4) &&
      ReadSubgraph(sc, VWAP_ID.GetInt(), 3, sd3Array, 4) &&
      ReadSubgraph(sc, VWAP_ID.GetInt(), 4, sd4Array, 4) &&
      ReadSubgraph(sc, VWAP_ID.GetInt(), 5, sd5Array, 4) &&
      ReadSubgraph(sc, VWAP_ID.GetInt(), 6, sd6Array, 4)) {
    
    if (currentIndex < vwapArray.GetArraySize()) {
      std::string payload = std::to_string(vwapArray[currentIndex]) + "|" +
                           std::to_string(sd1Array[currentIndex]) + "|" +
                           std::to_string(sd2Array[currentIndex]) + "|" +
                           std::to_string(sd3Array[currentIndex]) + "|" +
                           std::to_string(sd4Array[currentIndex]) + "|" +
                           std::to_string(sd5Array[currentIndex]) + "|" +
                           std::to_string(sd6Array[currentIndex]);
      
      if (ShouldWriteDataWithType(sc, "vwap", payload, currentIndex)) {
        char jsonBuffer[1024];
        sprintf(jsonBuffer, 
          "{\"sym\":\"%s\",\"t\":%.6f,\"i\":%d,\"vwap\":%.6f,\"sd1\":%.6f,\"sd2\":%.6f,\"sd3\":%.6f,\"sd4\":%.6f,\"sd5\":%.6f,\"sd6\":%.6f}",
          symbol.GetChars(), currentTime, currentIndex,
          vwapArray[currentIndex], sd1Array[currentIndex], sd2Array[currentIndex],
          sd3Array[currentIndex], sd4Array[currentIndex], sd5Array[currentIndex], sd6Array[currentIndex]
        );
        WriteToSpecializedFile(sc, "vwap", jsonBuffer);
      }
    }
  }

  // ========== 2. ATR (Study ID 5) ==========
  SCFloatArray atrArray;
  if (ReadSubgraph(sc, ATR_ID.GetInt(), 0, atrArray, 4)) {
    if (currentIndex < atrArray.GetArraySize()) {
      std::string payload = std::to_string(atrArray[currentIndex]);
      
      if (ShouldWriteDataWithType(sc, "atr", payload, currentIndex)) {
        char jsonBuffer[512];
        sprintf(jsonBuffer, 
          "{\"sym\":\"%s\",\"t\":%.6f,\"i\":%d,\"atr\":%.6f}",
          symbol.GetChars(), currentTime, currentIndex, atrArray[currentIndex]
        );
        WriteToSpecializedFile(sc, "atr", jsonBuffer);
      }
    }
  }

  // ========== 3. VOLUME PROFILE (Study ID 13) - MAPPING CORRECT ==========
  SCFloatArray vpocArray, vahArray, valArray, hvnArray, lvnArray;
  if (ReadSubgraph(sc, VOL_PROFILE_ID.GetInt(), 1, vpocArray, 4) &&  // SG1: VPOC
      ReadSubgraph(sc, VOL_PROFILE_ID.GetInt(), 2, vahArray, 4) &&   // SG2: VAH
      ReadSubgraph(sc, VOL_PROFILE_ID.GetInt(), 3, valArray, 4) &&   // SG3: VAL
      ReadSubgraph(sc, VOL_PROFILE_ID.GetInt(), 17, hvnArray, 4) &&  // SG17: HVN
      ReadSubgraph(sc, VOL_PROFILE_ID.GetInt(), 18, lvnArray, 4)) {  // SG18: LVN
    
    if (currentIndex < vpocArray.GetArraySize()) {
      std::string payload = std::to_string(vpocArray[currentIndex]) + "|" +
                           std::to_string(vahArray[currentIndex]) + "|" +
                           std::to_string(valArray[currentIndex]) + "|" +
                           std::to_string(hvnArray[currentIndex]) + "|" +
                           std::to_string(lvnArray[currentIndex]);
      
      if (ShouldWriteDataWithType(sc, "volume_profile", payload, currentIndex)) {
        char jsonBuffer[1024];
        sprintf(jsonBuffer, 
          "{\"sym\":\"%s\",\"t\":%.6f,\"i\":%d,\"val\":%.6f,\"vpoc\":%.6f,\"vah\":%.6f,\"hvn\":%.6f,\"lvn\":%.6f}",
          symbol.GetChars(), currentTime, currentIndex,
          valArray[currentIndex], vpocArray[currentIndex], vahArray[currentIndex],
          hvnArray[currentIndex], lvnArray[currentIndex]
        );
        WriteToSpecializedFile(sc, "volume_profile", jsonBuffer);
      }
    }
  }

  // ========== 4. CORRELATION (Study ID 15) ==========
  SCFloatArray corrArray;
  if (ReadSubgraph(sc, CORR_ID.GetInt(), 0, corrArray, 4)) {
    if (currentIndex < corrArray.GetArraySize()) {
      std::string payload = std::to_string(corrArray[currentIndex]);
      
      if (ShouldWriteDataWithType(sc, "correlation", payload, currentIndex)) {
        char jsonBuffer[512];
        sprintf(jsonBuffer, 
          "{\"sym\":\"%s\",\"t\":%.6f,\"i\":%d,\"correlation\":%.6f}",
          symbol.GetChars(), currentTime, currentIndex, corrArray[currentIndex]
        );
        WriteToSpecializedFile(sc, "correlation", jsonBuffer);
      }
    }
  }

  // ========== 5. OHLC (Study ID 16) ==========
  SCFloatArray openArray, highArray, lowArray, closeArray;
  if (ReadSubgraph(sc, OHLC_ID.GetInt(), 0, openArray, 4) &&
      ReadSubgraph(sc, OHLC_ID.GetInt(), 1, highArray, 4) &&
      ReadSubgraph(sc, OHLC_ID.GetInt(), 2, lowArray, 4) &&
      ReadSubgraph(sc, OHLC_ID.GetInt(), 3, closeArray, 4)) {
    
    if (currentIndex < openArray.GetArraySize()) {
      std::string payload = std::to_string(openArray[currentIndex]) + "|" +
                           std::to_string(highArray[currentIndex]) + "|" +
                           std::to_string(lowArray[currentIndex]) + "|" +
                           std::to_string(closeArray[currentIndex]);
      
      if (ShouldWriteDataWithType(sc, "ohlc", payload, currentIndex)) {
        char jsonBuffer[1024];
        sprintf(jsonBuffer, 
          "{\"sym\":\"%s\",\"t\":%.6f,\"i\":%d,\"c\":%.6f,\"o\":%.6f,\"h\":%.6f,\"l\":%.6f}",
          symbol.GetChars(), currentTime, currentIndex,
          closeArray[currentIndex], openArray[currentIndex], highArray[currentIndex], lowArray[currentIndex]
        );
        WriteToSpecializedFile(sc, "ohlc", jsonBuffer);
      }
    }
  }

  // ========== 6. NBCV (Study ID 14) ==========
  SCFloatArray deltaArray, askVolArray, bidVolArray, tradesArray, totalVolArray;
  if (ReadSubgraph(sc, NBCV_ID.GetInt(), 0, deltaArray, 4) &&
      ReadSubgraph(sc, NBCV_ID.GetInt(), 5, askVolArray, 4) &&
      ReadSubgraph(sc, NBCV_ID.GetInt(), 6, bidVolArray, 4) &&
      ReadSubgraph(sc, NBCV_ID.GetInt(), 11, tradesArray, 4) &&
      ReadSubgraph(sc, NBCV_ID.GetInt(), 12, totalVolArray, 4)) {
    
    if (currentIndex < deltaArray.GetArraySize()) {
      std::string payload = std::to_string(deltaArray[currentIndex]) + "|" +
                           std::to_string(askVolArray[currentIndex]) + "|" +
                           std::to_string(bidVolArray[currentIndex]) + "|" +
                           std::to_string(tradesArray[currentIndex]) + "|" +
                           std::to_string(totalVolArray[currentIndex]);
      
      if (ShouldWriteDataWithType(sc, "nbcv", payload, currentIndex)) {
        char jsonBuffer[1024];
        sprintf(jsonBuffer, 
          "{\"sym\":\"%s\",\"t\":%.6f,\"i\":%d,\"delta\":%.6f,\"ask_vol\":%.6f,\"bid_vol\":%.6f,\"trades\":%.6f,\"total_vol\":%.6f}",
          symbol.GetChars(), currentTime, currentIndex,
          deltaArray[currentIndex], askVolArray[currentIndex], bidVolArray[currentIndex],
          tradesArray[currentIndex], totalVolArray[currentIndex]
        );
        WriteToSpecializedFile(sc, "nbcv", jsonBuffer);
      }
    }
  }

  // ========== 7. CUMULATIVE DELTA (Study ID 6) ==========
  SCFloatArray cdOpenArray, cdHighArray, cdLowArray, cdCloseArray, cdVolArray;
  if (ReadSubgraph(sc, CUM_DELTA_ID.GetInt(), 0, cdOpenArray, 4) &&
      ReadSubgraph(sc, CUM_DELTA_ID.GetInt(), 1, cdHighArray, 4) &&
      ReadSubgraph(sc, CUM_DELTA_ID.GetInt(), 2, cdLowArray, 4) &&
      ReadSubgraph(sc, CUM_DELTA_ID.GetInt(), 3, cdCloseArray, 4) &&
      ReadSubgraph(sc, CUM_DELTA_ID.GetInt(), 4, cdVolArray, 4)) {
    
    if (currentIndex < cdOpenArray.GetArraySize()) {
      std::string payload = std::to_string(cdOpenArray[currentIndex]) + "|" +
                           std::to_string(cdHighArray[currentIndex]) + "|" +
                           std::to_string(cdLowArray[currentIndex]) + "|" +
                           std::to_string(cdCloseArray[currentIndex]) + "|" +
                           std::to_string(cdVolArray[currentIndex]);
      
      if (ShouldWriteDataWithType(sc, "cumulative_delta", payload, currentIndex)) {
        char jsonBuffer[1024];
        sprintf(jsonBuffer, 
          "{\"sym\":\"%s\",\"t\":%.6f,\"i\":%d,\"o\":%.6f,\"h\":%.6f,\"l\":%.6f,\"c\":%.6f,\"vol\":%.6f}",
          symbol.GetChars(), currentTime, currentIndex,
          cdOpenArray[currentIndex], cdHighArray[currentIndex], cdLowArray[currentIndex],
          cdCloseArray[currentIndex], cdVolArray[currentIndex]
        );
        WriteToSpecializedFile(sc, "cumulative_delta", jsonBuffer);
      }
    }
  }

  // ========== 8. VVA (Study ID 8) ==========
  SCFloatArray vvaPocArray, vvaVahArray, vvaValArray;
  if (ReadSubgraph(sc, VVA_ID.GetInt(), 0, vvaPocArray, 4) &&
      ReadSubgraph(sc, VVA_ID.GetInt(), 1, vvaVahArray, 4) &&
      ReadSubgraph(sc, VVA_ID.GetInt(), 2, vvaValArray, 4)) {
    
    if (currentIndex < vvaPocArray.GetArraySize()) {
      std::string payload = std::to_string(vvaPocArray[currentIndex]) + "|" +
                           std::to_string(vvaVahArray[currentIndex]) + "|" +
                           std::to_string(vvaValArray[currentIndex]);
      
      if (ShouldWriteDataWithType(sc, "vva", payload, currentIndex)) {
        char jsonBuffer[1024];
        sprintf(jsonBuffer, 
          "{\"sym\":\"%s\",\"t\":%.6f,\"i\":%d,\"vpoc\":%.6f,\"vah\":%.6f,\"val\":%.6f}",
          symbol.GetChars(), currentTime, currentIndex,
          vvaPocArray[currentIndex], vvaVahArray[currentIndex], vvaValArray[currentIndex]
        );
        WriteToSpecializedFile(sc, "vva", jsonBuffer);
      }
    }
  }

  // ========== 9. VVA PREVIOUS (Study ID 9) ==========
  SCFloatArray vvaPrevPocArray, vvaPrevVahArray, vvaPrevValArray;
  if (ReadSubgraph(sc, VVA_PREV_ID.GetInt(), 0, vvaPrevPocArray, 4) &&
      ReadSubgraph(sc, VVA_PREV_ID.GetInt(), 1, vvaPrevVahArray, 4) &&
      ReadSubgraph(sc, VVA_PREV_ID.GetInt(), 2, vvaPrevValArray, 4)) {
    
    if (currentIndex < vvaPrevPocArray.GetArraySize()) {
      std::string payload = std::to_string(vvaPrevPocArray[currentIndex]) + "|" +
                           std::to_string(vvaPrevVahArray[currentIndex]) + "|" +
                           std::to_string(vvaPrevValArray[currentIndex]);
      
      if (ShouldWriteDataWithType(sc, "vva_previous", payload, currentIndex)) {
        char jsonBuffer[1024];
        sprintf(jsonBuffer, 
          "{\"sym\":\"%s\",\"t\":%.6f,\"i\":%d,\"ppoc\":%.6f,\"pvah\":%.6f,\"pval\":%.6f}",
          symbol.GetChars(), currentTime, currentIndex,
          vvaPrevPocArray[currentIndex], vvaPrevVahArray[currentIndex], vvaPrevValArray[currentIndex]
        );
        WriteToSpecializedFile(sc, "vva_previous", jsonBuffer);
      }
    }
  }

  // ========== 10. PREVIOUS VP (Study ID 2) ==========
  SCFloatArray prevVpPocArray, prevVpVahArray, prevVpValArray;
  if (ReadSubgraph(sc, PREV_VP_ID.GetInt(), 1, prevVpPocArray, 4) &&
      ReadSubgraph(sc, PREV_VP_ID.GetInt(), 2, prevVpVahArray, 4) &&
      ReadSubgraph(sc, PREV_VP_ID.GetInt(), 3, prevVpValArray, 4)) {
    
    if (currentIndex < prevVpPocArray.GetArraySize()) {
      std::string payload = std::to_string(prevVpPocArray[currentIndex]) + "|" +
                           std::to_string(prevVpVahArray[currentIndex]) + "|" +
                           std::to_string(prevVpValArray[currentIndex]);
      
      if (ShouldWriteDataWithType(sc, "previous_vp", payload, currentIndex)) {
        char jsonBuffer[1024];
        sprintf(jsonBuffer, 
          "{\"sym\":\"%s\",\"t\":%.6f,\"i\":%d,\"pvpoc\":%.6f,\"pvah\":%.6f,\"pval\":%.6f}",
          symbol.GetChars(), currentTime, currentIndex,
          prevVpPocArray[currentIndex], prevVpVahArray[currentIndex], prevVpValArray[currentIndex]
        );
        WriteToSpecializedFile(sc, "previous_vp", jsonBuffer);
      }
    }
  }

  // ========== 11. PREVIOUS VWAP (Study ID 3) ==========
  SCFloatArray prevVwapArray, prevVwapSd1Array, prevVwapSd2Array;
  if (ReadSubgraph(sc, PREV_VWAP_ID.GetInt(), 4, prevVwapArray, 4) &&
      ReadSubgraph(sc, PREV_VWAP_ID.GetInt(), 12, prevVwapSd1Array, 4) &&
      ReadSubgraph(sc, PREV_VWAP_ID.GetInt(), 13, prevVwapSd2Array, 4)) {
    
    if (currentIndex < prevVwapArray.GetArraySize()) {
      std::string payload = std::to_string(prevVwapArray[currentIndex]) + "|" +
                           std::to_string(prevVwapSd1Array[currentIndex]) + "|" +
                           std::to_string(prevVwapSd2Array[currentIndex]);
      
      if (ShouldWriteDataWithType(sc, "previous_vwap", payload, currentIndex)) {
        char jsonBuffer[1024];
        sprintf(jsonBuffer, 
          "{\"sym\":\"%s\",\"t\":%.6f,\"i\":%d,\"pvwap\":%.6f,\"psd1\":%.6f,\"psd2\":%.6f}",
          symbol.GetChars(), currentTime, currentIndex,
          prevVwapArray[currentIndex], prevVwapSd1Array[currentIndex], prevVwapSd2Array[currentIndex]
        );
        WriteToSpecializedFile(sc, "previous_vwap", jsonBuffer);
      }
    }
  }
}



