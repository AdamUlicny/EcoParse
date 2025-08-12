import json
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

def generate_report(report_context: Dict[str, Any]) -> Optional[str]:
    """
    Compiles a detailed JSON report from a context dictionary and saves it to a file.
    This function is framework-agnostic.
    """
    Path("logs").mkdir(exist_ok=True)

    results_summary = {}
    extraction_results = report_context.get('extraction_results', [])
    if extraction_results:
        flat_results = []
        for res in extraction_results:
            row = {'species': res.get('species')}
            if isinstance(res.get('data'), dict):
                row.update(res['data'])
            flat_results.append(row)
        
        df = pd.DataFrame(flat_results)
        
        project_config = report_context.get('project_config', {})
        if project_config.get('data_fields'):
            first_field = project_config['data_fields'][0]['name']
            if first_field in df.columns:
                results_summary = df[first_field].value_counts().to_dict()

    gnfinder_raw = report_context.get('gnfinder_results_raw')
    species_df_final = report_context.get('species_df_final', pd.DataFrame())
    final_species_list_for_json = species_df_final.to_dict(orient='records') if not species_df_final.empty else []

    report_data = {
        "report_timestamp": datetime.now().isoformat(),
        "pdf_info": { 
        },
        "gnfinder_info": {
            "url_used": report_context.get('gnfinder_url'),
            "total_names_identified_raw": len(gnfinder_raw['names']) if gnfinder_raw else 0,
            "total_species_identified_initial_filter": len(report_context.get('species_df_initial', [])),
            "taxonomic_filter_applied": bool(len(report_context.get('species_df_initial', [])) != len(species_df_final)),
            "total_species_identified_final_filter": len(species_df_final),
            "final_species_list": final_species_list_for_json 
        },
        "llm_extraction_info": { 
        },
        "project_config_used": report_context.get('project_config', {}),
        "manual_verification_info": { 
        }
    }
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_path = Path("logs") / f"ecoparse_report_{timestamp}.json"
    
    try:
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=4)
        
        print(f"Report saved to {report_path}")
        return str(report_path)
    except Exception as e:
        print(f"Failed to save report: {e}")
        return None