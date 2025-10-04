#!/usr/bin/env python3
"""
Validateur de données enrichi pour le système MIA IA
Vérifie non seulement la présence des fichiers mais aussi la structure des données par type
"""

import os
import json
import datetime
from typing import Dict, List, Optional, Tuple, Any
import logging

logger = logging.getLogger(__name__)

class EnhancedDataValidator:
    """Validateur de données enrichi pour le système MIA IA"""
    
    def __init__(self, base_dir: str = "."):
        self.base_dir = base_dir
        
    def get_month_name(self, month_num: str) -> str:
        """Convertit le numéro de mois en nom français"""
        month_names = {
            "01": "JANVIER", "02": "FEVRIER", "03": "MARS", "04": "AVRIL",
            "05": "MAI", "06": "JUIN", "07": "JUILLET", "08": "AOUT",
            "09": "SEPTEMBRE", "10": "OCTOBRE", "11": "NOVEMBRE", "12": "DECEMBRE"
        }
        return month_names.get(month_num, "INCONNU")
    
    def get_organized_data_path(self, ymd: str) -> str:
        """Génère le chemin organisé pour les données"""
        year = ymd[:4]
        month_num = ymd[4:6]
        month_name = self.get_month_name(month_num)
        
        return os.path.join(self.base_dir, "DATA_SIERRA_CHART", f"DATA_{year}", month_name, ymd)
    
    def validate_vva_structure(self, file_path: str) -> Dict[str, Any]:
        """Valide la structure VVA (actuel et précédent)"""
        result = {
            "valid": False,
            "has_current": False,
            "has_previous": False,
            "current_fields": [],
            "previous_fields": [],
            "errors": []
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines_checked = 0
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        data = json.loads(line)
                        lines_checked += 1
                        
                        # Vérifier les champs VVA actuels
                        if 'vah' in data or 'val' in data or 'vpoc' in data:
                            result["has_current"] = True
                            result["current_fields"] = [k for k in data.keys() if k in ['vah', 'val', 'vpoc', 'vah_prev', 'val_prev', 'vpoc_prev']]
                        
                        # VVA previous
                        if "pvah" in data and "pval" in data and "ppoc" in data:
                            try:
                                pvah = float(data["pvah"])
                                pval = float(data["pval"])
                                ppoc = float(data["ppoc"])
                                if not (pval < ppoc < pvah):
                                    errors.append(f"Invalid VVA previous order: pval={pval}, ppoc={ppoc}, pvah={pvah}")
                            except (ValueError, TypeError):
                                errors.append("Invalid VVA previous values")
                        
                        if lines_checked >= 5:  # Vérifier les 5 premières lignes
                            break
                            
                    except json.JSONDecodeError as e:
                        result["errors"].append(f"JSON invalide ligne {lines_checked + 1}: {e}")
                
                result["valid"] = result["has_current"] and len(result["errors"]) == 0
                
        except Exception as e:
            result["errors"].append(f"Erreur lecture: {e}")
        
        return result
    
    def validate_menthorq_structure(self, file_path: str) -> Dict[str, Any]:
        """Valide la structure MenthorQ (gamma, blind spots, correlation)"""
        result = {
            "valid": False,
            "has_gamma": False,
            "has_blind_spots": False,
            "has_correlation": False,
            "has_hvl": False,
            "has_gex": False,
            "has_call_put": False,
            "has_min_max": False,
            "gamma_types": [],
            "blind_types": [],
            "gex_types": [],
            "correlation_pairs": [],
            "errors": []
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines_checked = 0
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        data = json.loads(line)
                        lines_checked += 1
                        
                        # Vérifier le type de données MenthorQ
                        if data.get('type') == 'menthorq_level':
                            level_type = data.get('level_type', '')
                            
                            # Vérifier les niveaux gamma (call/put resistance/support)
                            if 'call' in level_type or 'put' in level_type:
                                result["has_gamma"] = True
                                if level_type not in result["gamma_types"]:
                                    result["gamma_types"].append(level_type)
                            
                            # Vérifier les blind spots
                            if 'blind_spot' in level_type:
                                result["has_blind_spots"] = True
                                if level_type not in result["blind_types"]:
                                    result["blind_types"].append(level_type)
                            
                            # Vérifier HVL
                            if 'hvl' in level_type:
                                result["has_hvl"] = True
                            
                            # Vérifier GEX
                            if 'gex' in level_type:
                                result["has_gex"] = True
                                if level_type not in result["gex_types"]:
                                    result["gex_types"].append(level_type)
                            
                            # Vérifier call/put
                            if 'call' in level_type or 'put' in level_type:
                                result["has_call_put"] = True
                            
                            # Vérifier min/max
                            if 'min' in level_type or 'max' in level_type:
                                result["has_min_max"] = True
                        
                        # Vérifier la correlation
                        if data.get('type') == 'correlation':
                            result["has_correlation"] = True
                            if 'cc' in data:  # correlation coefficient
                                result["correlation_pairs"].append(f"cc={data['cc']}")
                        
                        # Debug: afficher le type détecté (dans un champ séparé, pas dans errors)
                        if lines_checked <= 5:  # Afficher les 5 premiers types pour debug
                            if "debug_info" not in result:
                                result["debug_info"] = []
                            result["debug_info"].append(f"ligne {lines_checked}: type={data.get('type')}, level_type={data.get('level_type', 'N/A')}")
                        
                        if lines_checked >= 50:  # Vérifier plus de lignes pour MenthorQ
                            break
                            
                    except json.JSONDecodeError as e:
                        result["errors"].append(f"JSON invalide ligne {lines_checked + 1}: {e}")
                
                result["valid"] = (result["has_gamma"] or result["has_blind_spots"] or result["has_correlation"] or result["has_hvl"] or result["has_gex"]) and len(result["errors"]) == 0
                
        except Exception as e:
            result["errors"].append(f"Erreur lecture: {e}")
        
        return result
    
    def validate_orderflow_structure(self, file_path: str) -> Dict[str, Any]:
        """Valide la structure Order Flow (NBCV)"""
        result = {
            "valid": False,
            "has_delta": False,
            "has_volume": False,
            "has_pressure": False,
            "delta_fields": [],
            "volume_fields": [],
            "errors": []
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines_checked = 0
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        data = json.loads(line)
                        lines_checked += 1
                        
                        # Vérifier les champs delta
                        delta_fields = [k for k in data.keys() if 'delta' in k.lower()]
                        if delta_fields:
                            result["has_delta"] = True
                            result["delta_fields"] = delta_fields
                        
                        # Vérifier les champs volume
                        volume_fields = [k for k in data.keys() if 'volume' in k.lower() or 'vol' in k.lower()]
                        if volume_fields:
                            result["has_volume"] = True
                            result["volume_fields"] = volume_fields
                        
                        # Vérifier la pression
                        if 'pressure' in data or 'ask_volume' in data or 'bid_volume' in data:
                            result["has_pressure"] = True
                        
                        if lines_checked >= 5:
                            break
                            
                    except json.JSONDecodeError as e:
                        result["errors"].append(f"JSON invalide ligne {lines_checked + 1}: {e}")
                
                result["valid"] = (result["has_delta"] or result["has_volume"]) and len(result["errors"]) == 0
                
        except Exception as e:
            result["errors"].append(f"Erreur lecture: {e}")
        
        return result
    
    def validate_vix_structure(self, file_path: str) -> Dict[str, Any]:
        """Valide la structure VIX"""
        result = {
            "valid": False,
            "has_value": False,
            "has_timestamp": False,
            "value_range": {"min": None, "max": None},
            "errors": []
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines_checked = 0
                values = []
                
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        data = json.loads(line)
                        lines_checked += 1
                        
                        # Vérifier la valeur VIX
                        if 'value' in data or 'vix' in data:
                            result["has_value"] = True
                            vix_value = data.get('value') or data.get('vix')
                            if isinstance(vix_value, (int, float)):
                                values.append(vix_value)
                        
                        # Vérifier le timestamp
                        if 't' in data or 'timestamp' in data:
                            result["has_timestamp"] = True
                        
                        if lines_checked >= 10:
                            break
                            
                    except json.JSONDecodeError as e:
                        result["errors"].append(f"JSON invalide ligne {lines_checked + 1}: {e}")
                
                if values:
                    result["value_range"]["min"] = min(values)
                    result["value_range"]["max"] = max(values)
                
                result["valid"] = result["has_value"] and len(result["errors"]) == 0
                
        except Exception as e:
            result["errors"].append(f"Erreur lecture: {e}")
        
        return result
    
    def validate_unified_structure(self, file_path: str) -> Dict[str, Any]:
        """Valide la structure du fichier unifié"""
        result = {
            "valid": False,
            "has_basedata": False,
            "has_menthorq": False,
            "has_alerts": False,
            "has_mia": False,
            "has_vix": False,
            "has_vwap": False,
            "has_vva": False,
            "has_orderflow": False,
            "errors": []
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines_checked = 0
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        data = json.loads(line)
                        lines_checked += 1
                        
                        # Vérifier les sections principales
                        if 'basedata' in data:
                            result["has_basedata"] = True
                        
                        if 'menthorq_levels' in data or 'menthorq' in data:
                            result["has_menthorq"] = True
                        
                        if 'alerts' in data:
                            result["has_alerts"] = True
                        
                        if 'mia' in data:
                            result["has_mia"] = True
                        
                        if 'vix' in data:
                            result["has_vix"] = True
                        
                        if 'vwap' in data:
                            result["has_vwap"] = True
                        
                        if 'vva' in data:
                            result["has_vva"] = True
                        
                        if 'nbcv' in data or 'orderflow' in data:
                            result["has_orderflow"] = True
                        
                        if lines_checked >= 5:
                            break
                            
                    except json.JSONDecodeError as e:
                        result["errors"].append(f"JSON invalide ligne {lines_checked + 1}: {e}")
                
                # Pour le fichier unifié, basedata et menthorq sont requis, mais alerts et mia sont optionnels (générés par unifier)
                result["valid"] = (result["has_basedata"] and result["has_menthorq"]) and len(result["errors"]) == 0
                
        except Exception as e:
            result["errors"].append(f"Erreur lecture: {e}")
        
        return result
    
    def validate_all_files_enhanced(self, ymd: str) -> Dict[str, Any]:
        """Valide tous les fichiers avec vérification de structure"""
        organized_path = self.get_organized_data_path(ymd)
        
        results = {
            "valid": True,
            "date": ymd,
            "organized_path": organized_path,
            "file_validation": {},
            "structure_validation": {},
            "summary": {
                "files_ok": 0,
                "files_total": 0,
                "structures_ok": 0,
                "structures_total": 0,
                "critical_issues": []
            }
        }
        
        # Fichiers à valider avec leurs validateurs spécifiques
        files_to_validate = {
            "CHART_3/chart_3_vva_20250918.jsonl": ("vva", self.validate_vva_structure),
            "CHART_3/chart_3_nbcv_20250918.jsonl": ("orderflow", self.validate_orderflow_structure),
            "CHART_3/chart_3_vix_20250918.jsonl": ("vix", self.validate_vix_structure),
            "CHART_10/chart_10_menthorq_20250918.jsonl": ("menthorq", self.validate_menthorq_structure),
            "unified_20250918.jsonl": ("unified", self.validate_unified_structure)
        }
        
        for file_path, (data_type, validator_func) in files_to_validate.items():
            full_path = os.path.join(organized_path, file_path)
            results["summary"]["files_total"] += 1
            
            # Vérifier existence du fichier
            if not os.path.exists(full_path):
                results["file_validation"][file_path] = {
                    "exists": False,
                    "message": "Fichier manquant"
                }
                results["summary"]["critical_issues"].append(f"Fichier manquant: {file_path}")
                continue
            
            results["file_validation"][file_path] = {
                "exists": True,
                "message": "Fichier présent"
            }
            results["summary"]["files_ok"] += 1
            
            # Valider la structure des données
            results["summary"]["structures_total"] += 1
            structure_result = validator_func(full_path)
            results["structure_validation"][data_type] = structure_result
            
            if structure_result["valid"]:
                results["summary"]["structures_ok"] += 1
            else:
                results["summary"]["critical_issues"].extend(structure_result.get("errors", []))
                results["valid"] = False
        
        return results
    
    def print_enhanced_validation_report(self, results: Dict[str, Any]) -> None:
        """Affiche un rapport de validation enrichi"""
        print(f"\n=== RAPPORT DE VALIDATION ENRICHI ===")
        print(f"Date: {results['date']}")
        print(f"Chemin organisé: {results['organized_path']}")
        print(f"Statut global: {'[OK] VALIDE' if results['valid'] else '[ERREUR] INVALIDE'}")
        print()
        
        print(f"[INFO] RÉSUMÉ FICHIERS:")
        print(f"  - Fichiers présents: {results['summary']['files_ok']}/{results['summary']['files_total']}")
        print(f"  - Structures valides: {results['summary']['structures_ok']}/{results['summary']['structures_total']}")
        
        if results['summary']['critical_issues']:
            print(f"\n[ALERTE] PROBLÈMES CRITIQUES:")
            for issue in results['summary']['critical_issues']:
                print(f"    [ERREUR] {issue}")
        
        print(f"\n[INFO] VALIDATION DES STRUCTURES:")
        for data_type, validation in results['structure_validation'].items():
            status = "[OK]" if validation['valid'] else "[ERREUR]"
            print(f"\n  {status} {data_type.upper()}:")
            
            if data_type == "vva":
                print(f"    - VVA Actuel: {'[OK]' if validation['has_current'] else '[ERREUR]'}")
                print(f"    - VVA Précédent: {'[OK]' if validation['has_previous'] else '[ERREUR]'}")
                if validation['current_fields']:
                    print(f"    - Champs actuels: {', '.join(validation['current_fields'])}")
                if validation['previous_fields']:
                    print(f"    - Champs précédents: {', '.join(validation['previous_fields'])}")
            
            elif data_type == "menthorq":
                print(f"    - Gamma Levels (Call/Put): {'[OK]' if validation['has_gamma'] else '[ERREUR]'}")
                print(f"    - Blind Spots: {'[OK]' if validation['has_blind_spots'] else '[ERREUR]'}")
                print(f"    - Correlation: {'[OK]' if validation['has_correlation'] else '[ERREUR]'}")
                print(f"    - HVL: {'[OK]' if validation['has_hvl'] else '[ERREUR]'}")
                print(f"    - GEX: {'[OK]' if validation['has_gex'] else '[ERREUR]'}")
                print(f"    - Call/Put: {'[OK]' if validation['has_call_put'] else '[ERREUR]'}")
                print(f"    - Min/Max: {'[OK]' if validation['has_min_max'] else '[ERREUR]'}")
                if validation['gamma_types']:
                    print(f"    - Types Gamma: {', '.join(validation['gamma_types'][:5])}{'...' if len(validation['gamma_types']) > 5 else ''}")
                if validation['blind_types']:
                    print(f"    - Types Blind Spots: {', '.join(validation['blind_types'][:5])}{'...' if len(validation['blind_types']) > 5 else ''}")
                if validation['gex_types']:
                    print(f"    - Types GEX: {', '.join(validation['gex_types'][:5])}{'...' if len(validation['gex_types']) > 5 else ''}")
                if validation['correlation_pairs']:
                    print(f"    - Correlation: {', '.join(validation['correlation_pairs'])}")
                if validation.get('debug_info'):
                    print(f"    - Debug (5 premières lignes): {', '.join(validation['debug_info'])}")
            
            elif data_type == "orderflow":
                print(f"    - Delta: {'[OK]' if validation['has_delta'] else '[ERREUR]'}")
                print(f"    - Volume: {'[OK]' if validation['has_volume'] else '[ERREUR]'}")
                print(f"    - Pression: {'[OK]' if validation['has_pressure'] else '[ERREUR]'}")
                if validation['delta_fields']:
                    print(f"    - Champs Delta: {', '.join(validation['delta_fields'])}")
            
            elif data_type == "vix":
                print(f"    - Valeur VIX: {'[OK]' if validation['has_value'] else '[ERREUR]'}")
                print(f"    - Timestamp: {'[OK]' if validation['has_timestamp'] else '[ERREUR]'}")
                if validation['value_range']['min'] is not None:
                    print(f"    - Plage VIX: {validation['value_range']['min']:.2f} - {validation['value_range']['max']:.2f}")
            
            elif data_type == "unified":
                print(f"    - Basedata: {'[OK]' if validation['has_basedata'] else '[ERREUR]'}")
                print(f"    - MenthorQ: {'[OK]' if validation['has_menthorq'] else '[ERREUR]'}")
                print(f"    - Alerts: {'[OK]' if validation['has_alerts'] else '[INFO] Généré par unifier'}")
                print(f"    - MIA: {'[OK]' if validation['has_mia'] else '[INFO] Généré par unifier'}")
                print(f"    - VIX: {'[OK]' if validation['has_vix'] else '[ERREUR]'}")
                print(f"    - VWAP: {'[OK]' if validation['has_vwap'] else '[ERREUR]'}")
                print(f"    - VVA: {'[OK]' if validation['has_vva'] else '[ERREUR]'}")
                print(f"    - OrderFlow: {'[OK]' if validation['has_orderflow'] else '[ERREUR]'}")
            
            if validation.get('errors'):
                print(f"    - Erreurs: {', '.join(validation['errors'])}")

def main():
    """Fonction principale pour tester le validateur enrichi"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Validateur de données enrichi MIA IA")
    parser.add_argument("--date", type=str, default="today", help="Date à valider (YYYYMMDD ou 'today')")
    parser.add_argument("--base-dir", type=str, default=".", help="Répertoire de base")
    
    args = parser.parse_args()
    
    # Résoudre la date
    if args.date.lower() == "today":
        ymd = datetime.datetime.now().strftime("%Y%m%d")
    else:
        ymd = args.date
    
    # Valider
    validator = EnhancedDataValidator(args.base_dir)
    results = validator.validate_all_files_enhanced(ymd)
    
    # Afficher le rapport
    validator.print_enhanced_validation_report(results)
    
    # Code de sortie
    import sys
    sys.exit(0 if results['valid'] else 1)

if __name__ == "__main__":
    main()
