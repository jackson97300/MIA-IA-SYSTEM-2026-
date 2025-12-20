// MIA_Dumper_G4_VolumeProfile_TEST.cpp
// ACSIL — Sierra Chart
// VERSION TEST pour tester TOUS les Volume Profiles
// Test de tous les Study IDs possibles pour le Volume Profile

#include "sierrachart.h"
SCDLLName("MIA Dumper G4 VolumeProfile TEST")

#include <stdio.h>
#include <string>

static SCString g_OutputDir;

// ========== FONCTION PRINCIPALE ==========
SCSFExport scsf_MIA_Dumper_G4_VolumeProfile_TEST(SCStudyInterfaceRef sc)
{
  SCInputRef OutDir = sc.Input[0];
  SCInputRef SymbolOverride = sc.Input[1];

  if (sc.SetDefaults)
  {
    sc.GraphName = "MIA Dumper G4 VolumeProfile TEST";
    sc.StudyDescription = "Test de tous les Volume Profiles disponibles";
    sc.AutoLoop = 0;
    sc.UpdateAlways = 1;
    sc.CalculationPrecedence = LOW_PREC_LEVEL;

    OutDir.Name = "Output Directory";
    OutDir.SetString("D:\\MIA_IA_system");

    SymbolOverride.Name = "Symbol Override (optional)";
    SymbolOverride.SetString("");

    return;
  }

  // ========== TRAITEMENT PRINCIPAL ==========
  g_OutputDir = OutDir.GetString();
  
  SCString symbol = SymbolOverride.GetString();
  if (symbol.GetLength() == 0) {
    symbol = sc.Symbol;
  }

  int currentIndex = sc.Index;
  SCDateTime currentDateTime = sc.CurrentDateTimeForReplay;
  double currentTime = currentDateTime.GetAsDouble();

  // ========== TEST 1: Study ID 13 - MULTIPLE VOLUME PROFILE ==========
  SCFloatArray vpoc13, vah13, val13, hvn13, lvn13;
  sc.GetStudyArrayFromChartUsingID(4, 13, 1, vpoc13);
  sc.GetStudyArrayFromChartUsingID(4, 13, 2, vah13);
  sc.GetStudyArrayFromChartUsingID(4, 13, 3, val13);
  sc.GetStudyArrayFromChartUsingID(4, 13, 17, hvn13);
  sc.GetStudyArrayFromChartUsingID(4, 13, 18, lvn13);
  
  if (vpoc13.GetArraySize() > 0 && vah13.GetArraySize() > 0 && val13.GetArraySize() > 0) {
    
    if (currentIndex < vpoc13.GetArraySize()) {
      char jsonBuffer[1024];
      sprintf(jsonBuffer, 
        "{\"test\":\"study_13\",\"sym\":\"%s\",\"t\":%.6f,\"i\":%d,\"vpoc\":%.6f,\"vah\":%.6f,\"val\":%.6f,\"hvn\":%.6f,\"lvn\":%.6f}",
        symbol.GetChars(), currentTime, currentIndex,
        vpoc13[currentIndex], vah13[currentIndex], val13[currentIndex],
        hvn13[currentIndex], lvn13[currentIndex]
      );
      
      SCString filename;
      filename.Format("%s\\chart_4_volume_profile_test_%04d%02d%02d.jsonl", 
        g_OutputDir.GetChars(),
        sc.GetCurrentDateTime().GetYear(),
        sc.GetCurrentDateTime().GetMonth(),
        sc.GetCurrentDateTime().GetDay()
      );
      
      FILE* file = fopen(filename.GetChars(), "a");
      if (file) {
        fprintf(file, "%s\n", jsonBuffer);
        fclose(file);
      }
    }
  }

  // ========== TEST 2: Study ID 8 - Volume Value Area Lines ==========
  SCFloatArray vpoc8, vah8, val8;
  sc.GetStudyArrayFromChartUsingID(4, 8, 0, vpoc8);
  sc.GetStudyArrayFromChartUsingID(4, 8, 1, vah8);
  sc.GetStudyArrayFromChartUsingID(4, 8, 2, val8);
  
  if (vpoc8.GetArraySize() > 0 && vah8.GetArraySize() > 0 && val8.GetArraySize() > 0) {
    
    if (currentIndex < vpoc8.GetArraySize()) {
      char jsonBuffer[1024];
      sprintf(jsonBuffer, 
        "{\"test\":\"study_8\",\"sym\":\"%s\",\"t\":%.6f,\"i\":%d,\"vpoc\":%.6f,\"vah\":%.6f,\"val\":%.6f}",
        symbol.GetChars(), currentTime, currentIndex,
        vpoc8[currentIndex], vah8[currentIndex], val8[currentIndex]
      );
      
      SCString filename;
      filename.Format("%s\\chart_4_volume_profile_test_%04d%02d%02d.jsonl", 
        g_OutputDir.GetChars(),
        sc.GetCurrentDateTime().GetYear(),
        sc.GetCurrentDateTime().GetMonth(),
        sc.GetCurrentDateTime().GetDay()
      );
      
      FILE* file = fopen(filename.GetChars(), "a");
      if (file) {
        fprintf(file, "%s\n", jsonBuffer);
        fclose(file);
      }
    }
  }

  // ========== TEST 3: Study ID 9 - Volume Value Area Previous ==========
  SCFloatArray vpoc9, vah9, val9;
  sc.GetStudyArrayFromChartUsingID(4, 9, 0, vpoc9);
  sc.GetStudyArrayFromChartUsingID(4, 9, 1, vah9);
  sc.GetStudyArrayFromChartUsingID(4, 9, 2, val9);
  
  if (vpoc9.GetArraySize() > 0 && vah9.GetArraySize() > 0 && val9.GetArraySize() > 0) {
    
    if (currentIndex < vpoc9.GetArraySize()) {
      char jsonBuffer[1024];
      sprintf(jsonBuffer, 
        "{\"test\":\"study_9_previous\",\"sym\":\"%s\",\"t\":%.6f,\"i\":%d,\"ppoc\":%.6f,\"pvah\":%.6f,\"pval\":%.6f}",
        symbol.GetChars(), currentTime, currentIndex,
        vpoc9[currentIndex], vah9[currentIndex], val9[currentIndex]
      );
      
      SCString filename;
      filename.Format("%s\\chart_4_volume_profile_test_%04d%02d%02d.jsonl", 
        g_OutputDir.GetChars(),
        sc.GetCurrentDateTime().GetYear(),
        sc.GetCurrentDateTime().GetMonth(),
        sc.GetCurrentDateTime().GetDay()
      );
      
      FILE* file = fopen(filename.GetChars(), "a");
      if (file) {
        fprintf(file, "%s\n", jsonBuffer);
        fclose(file);
      }
    }
  }

  // ========== TEST 4: Study ID 2 - PREVIOUS VPOC VAH VAL ==========
  SCFloatArray vpoc2, vah2, val2, hvn2, lvn2;
  sc.GetStudyArrayFromChartUsingID(4, 2, 1, vpoc2);
  sc.GetStudyArrayFromChartUsingID(4, 2, 2, vah2);
  sc.GetStudyArrayFromChartUsingID(4, 2, 3, val2);
  sc.GetStudyArrayFromChartUsingID(4, 2, 17, hvn2);
  sc.GetStudyArrayFromChartUsingID(4, 2, 18, lvn2);
  
  if (vpoc2.GetArraySize() > 0 && vah2.GetArraySize() > 0 && val2.GetArraySize() > 0) {
    
    if (currentIndex < vpoc2.GetArraySize()) {
      char jsonBuffer[1024];
      sprintf(jsonBuffer, 
        "{\"test\":\"study_2_previous\",\"sym\":\"%s\",\"t\":%.6f,\"i\":%d,\"pvpoc\":%.6f,\"pvah\":%.6f,\"pval\":%.6f,\"hvn\":%.6f,\"lvn\":%.6f}",
        symbol.GetChars(), currentTime, currentIndex,
        vpoc2[currentIndex], vah2[currentIndex], val2[currentIndex],
        hvn2[currentIndex], lvn2[currentIndex]
      );
      
      SCString filename;
      filename.Format("%s\\chart_4_volume_profile_test_%04d%02d%02d.jsonl", 
        g_OutputDir.GetChars(),
        sc.GetCurrentDateTime().GetYear(),
        sc.GetCurrentDateTime().GetMonth(),
        sc.GetCurrentDateTime().GetDay()
      );
      
      FILE* file = fopen(filename.GetChars(), "a");
      if (file) {
        fprintf(file, "%s\n", jsonBuffer);
        fclose(file);
      }
    }
  }

  // ========== TEST 5: Study ID 3 - PREVIOUS VWAP SD+1 SD-1 ==========
  SCFloatArray vpoc3, vah3, val3, hvn3, lvn3;
  sc.GetStudyArrayFromChartUsingID(4, 3, 1, vpoc3);
  sc.GetStudyArrayFromChartUsingID(4, 3, 2, vah3);
  sc.GetStudyArrayFromChartUsingID(4, 3, 3, val3);
  sc.GetStudyArrayFromChartUsingID(4, 3, 17, hvn3);
  sc.GetStudyArrayFromChartUsingID(4, 3, 18, lvn3);
  
  if (vpoc3.GetArraySize() > 0 && vah3.GetArraySize() > 0 && val3.GetArraySize() > 0) {
    
    if (currentIndex < vpoc3.GetArraySize()) {
      char jsonBuffer[1024];
      sprintf(jsonBuffer, 
        "{\"test\":\"study_3_previous\",\"sym\":\"%s\",\"t\":%.6f,\"i\":%d,\"pvpoc\":%.6f,\"pvah\":%.6f,\"pval\":%.6f,\"hvn\":%.6f,\"lvn\":%.6f}",
        symbol.GetChars(), currentTime, currentIndex,
        vpoc3[currentIndex], vah3[currentIndex], val3[currentIndex],
        hvn3[currentIndex], lvn3[currentIndex]
      );
      
      SCString filename;
      filename.Format("%s\\chart_4_volume_profile_test_%04d%02d%02d.jsonl", 
        g_OutputDir.GetChars(),
        sc.GetCurrentDateTime().GetYear(),
        sc.GetCurrentDateTime().GetMonth(),
        sc.GetCurrentDateTime().GetDay()
      );
      
      FILE* file = fopen(filename.GetChars(), "a");
      if (file) {
        fprintf(file, "%s\n", jsonBuffer);
        fclose(file);
      }
    }
  }

  // ========== TEST 6: Study ID 8 - Volume Value Area Lines (tous subgraphs) ==========
  SCFloatArray vpoc8_all, vah8_all, val8_all;
  sc.GetStudyArrayFromChartUsingID(4, 8, 0, vpoc8_all);
  sc.GetStudyArrayFromChartUsingID(4, 8, 1, vah8_all);
  sc.GetStudyArrayFromChartUsingID(4, 8, 2, val8_all);
  
  if (vpoc8_all.GetArraySize() > 0 && vah8_all.GetArraySize() > 0 && val8_all.GetArraySize() > 0) {
    
    if (currentIndex < vpoc8_all.GetArraySize()) {
      char jsonBuffer[1024];
      sprintf(jsonBuffer, 
        "{\"test\":\"study_8_all\",\"sym\":\"%s\",\"t\":%.6f,\"i\":%d,\"vol_poc\":%.6f,\"vol_vah\":%.6f,\"vol_val\":%.6f}",
        symbol.GetChars(), currentTime, currentIndex,
        vpoc8_all[currentIndex], vah8_all[currentIndex], val8_all[currentIndex]
      );
      
      SCString filename;
      filename.Format("%s\\chart_4_volume_profile_test_%04d%02d%02d.jsonl", 
        g_OutputDir.GetChars(),
        sc.GetCurrentDateTime().GetYear(),
        sc.GetCurrentDateTime().GetMonth(),
        sc.GetCurrentDateTime().GetDay()
      );
      
      FILE* file = fopen(filename.GetChars(), "a");
      if (file) {
        fprintf(file, "%s\n", jsonBuffer);
        fclose(file);
      }
    }
  }
}
