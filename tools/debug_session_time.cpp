#include <iostream>
#include <string>
#include <ctime>

// Simulation de la logique de session NY
std::string SessionNY_from(int hour, int minute) {
  // FORCER les valeurs correctes (même que dans le dumper)
  const int asia_h   = 18;   // 18:00 NY
  const int lon_h    = 3;    // 03:00 NY
  const int us_h     = 9;    // 09:00 NY
  const int us_m     = 30;   // 09:30 NY

  auto after = [&](int H, int M){ return (hour > H) || (hour == H && minute >= M); };

  if (after(us_h, us_m)) return "US";
  if (hour >= lon_h && hour < us_h) return "London";
  return "Asia";
}

int main() {
  std::cout << "=== DEBUG SESSION TIME NY ===" << std::endl;
  std::cout << "Configuration:" << std::endl;
  std::cout << "  Asia Start: 18:00 NY" << std::endl;
  std::cout << "  London Start: 03:00 NY" << std::endl;
  std::cout << "  US Start: 09:30 NY" << std::endl;
  std::cout << std::endl;

  // Test des heures critiques
  int test_hours[] = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23};
  int test_minutes[] = {0, 15, 30, 43, 45};

  std::cout << "Résultats par heure NY:" << std::endl;
  std::cout << "Heure | Session | Logique" << std::endl;
  std::cout << "------|---------|--------" << std::endl;

  for (int h : test_hours) {
    for (int m : test_minutes) {
      std::string session = SessionNY_from(h, m);
      
      // Logique détaillée
      std::string logic;
      if (h > 9 || (h == 9 && m >= 30)) {
        logic = "after(9,30) = true";
      } else if (h >= 3 && h < 9) {
        logic = "3 <= h < 9";
      } else {
        logic = "else (Asia)";
      }
      
      printf("%02d:%02d | %-7s | %s\n", h, m, session.c_str(), logic.c_str());
    }
  }

  std::cout << std::endl;
  std::cout << "=== CAS SPÉCIFIQUE 00:43 NY ===" << std::endl;
  int hour = 0, minute = 43;
  std::string session = SessionNY_from(hour, minute);
  
  std::cout << "Heure: " << hour << ":" << minute << std::endl;
  std::cout << "Session calculée: " << session << std::endl;
  
  // Détail du calcul
  std::cout << std::endl << "Détail du calcul:" << std::endl;
  std::cout << "  after(9, 30) = " << ((hour > 9) || (hour == 9 && minute >= 30)) << std::endl;
  std::cout << "  hour >= 3 && hour < 9 = " << (hour >= 3 && hour < 9) << std::endl;
  std::cout << "  → Session = " << session << std::endl;

  return 0;
}






