"""
Comprehensive Reporting and Analysis Module

This module generates detailed JSON reports documenting the complete extraction
workflow, performance metrics, and results. These reports are essential for
scientific reproducibility, performance analysis, and quality assessment of
automated biodiversity data extraction.

Scientific Purpose:
- Documents complete methodology and parameters for reproducibility
- Tracks performance metrics for algorithm optimization
- Provides structured output for downstream analysis and publication
- Enables systematic comparison of different extraction approaches

Report Components:
- Document processing statistics
- Species identification pipeline results  
- LLM extraction performance and costs
- Verification workflow outcomes
- Project configuration documentation

Output Format:
- Structured JSON for programmatic analysis
- Human-readable organization for manual review
- Timestamped for tracking extraction runs
- Comprehensive metadata for scientific documentation
"""

import json
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

def generate_report(report_context: Dict[str, Any]) -> Optional[str]:
    """
    Compiles comprehensive extraction workflow report with performance metrics.
    
    Generates a detailed JSON report documenting all aspects of the species
    data extraction process, from initial document processing through final
    results validation. This report is essential for scientific reproducibility
    and system performance assessment.
    
    Args:
        report_context: Dictionary containing all workflow data and metadata
        
    Returns:
        Path to generated report file, or None if generation failed
        
    Report Structure:
    
    1. PDF Processing Metrics:
       - Document identification and character counts
       - Page range processing information
       - Text extraction quality indicators
    
    2. Species Identification Results:
       - GNfinder service performance statistics
       - Taxonomic filtering effectiveness
       - Final species list with metadata
    
    3. LLM Extraction Performance:
       - Model configuration and parameters
       - Token usage and cost tracking
       - Runtime performance metrics
       - Extraction success/failure rates
    
    4. Quality Control Results:
       - Manual verification outcomes
       - Accuracy assessment data
       - Error analysis and patterns
    
    5. Reproducibility Documentation:
       - Complete project configuration
       - Version information and timestamps
       - Parameter settings and examples used
    
    Scientific Applications:
    - Method documentation for publication
    - Performance comparison across configurations
    - Cost-benefit analysis of different approaches
    - Quality control and accuracy assessment
    - Debugging and system optimization
    """
    # Ensure logs directory exists for report storage
    Path("logs").mkdir(exist_ok=True)

    # --- EXTRACTION RESULTS ANALYSIS ---
    # Analyze extraction outcomes for summary statistics
    results_summary = {}
    extraction_results = report_context.get('extraction_results', [])
    if extraction_results:
        # Flatten nested extraction results for analysis
        flat_results = []
        for res in extraction_results:
            row = {'species': res.get('species')}
            if isinstance(res.get('data'), dict):
                row.update(res['data'])
            flat_results.append(row)
        
        df = pd.DataFrame(flat_results)
        
        # Generate value count summary for primary data field
        project_config = report_context.get('project_config', {})
        if project_config.get('data_fields'):
            first_field = project_config['data_fields'][0]['name']
            if first_field in df.columns:
                results_summary = df[first_field].value_counts().to_dict()

    # --- SPECIES IDENTIFICATION PIPELINE METRICS ---
    # Compile statistics from GNfinder and filtering stages
    gnfinder_raw = report_context.get('gnfinder_results_raw')
    species_df_initial = report_context.get('species_df_initial', pd.DataFrame())
    species_df_final = report_context.get('species_df_final', pd.DataFrame())
    final_species_list_for_json = species_df_final.to_dict(orient='records') if not species_df_final.empty else []

    # --- COMPREHENSIVE REPORT ASSEMBLY ---
    # Combine all workflow components into structured report
    report_data = {
        # Report metadata
        "report_timestamp": datetime.now().isoformat(),
        
        # Document processing information
        "pdf_info": {
            "file_name": report_context.get('pdf_name', 'N/A'),
            "extracted_text_char_count": len(report_context.get('full_text', ''))
        },
        
        # Species identification pipeline results
        "gnfinder_info": {
            "url_used": report_context.get('gnfinder_url'),
            "total_names_identified_raw": len(gnfinder_raw['names']) if gnfinder_raw else 0,
            "total_species_identified_initial_filter": len(species_df_initial),
            "taxonomic_filter_applied": bool(len(species_df_initial) != len(species_df_final)),
            "total_species_identified_final_filter": len(species_df_final),
            "final_species_list": final_species_list_for_json
        },
        
        # LLM extraction performance and configuration
        "llm_extraction_info": {
            "method": report_context.get('extraction_method'),
            "provider": report_context.get('llm_provider'),
            "model": report_context.get('llm_model'),
            "context_chars_before": report_context.get('context_before', "N/A"),
            "context_chars_after": report_context.get('context_after', "N/A"),
            "total_examples_provided": len(report_context.get('prompt_examples', [])),
            "examples_used": report_context.get('prompt_examples', []),
            "concurrent_requests_used": report_context.get('concurrent_requests'),
            "total_species_assessed": len(extraction_results),
            "runtime_seconds": report_context.get('extraction_runtime', 0.0),
            "total_input_tokens": report_context.get('total_input_tokens', 0),
            "total_output_tokens": report_context.get('total_output_tokens', 0),
            "extraction_results_summary": results_summary,
            "full_extraction_results": extraction_results
        },
        
        # Project configuration for reproducibility
        "project_config_used": report_context.get('project_config', {}),
        
        # Quality control and verification results
        "manual_verification_info": {
            "run": bool(report_context.get('manual_verification_results')),
            "full_results": report_context.get('manual_verification_results', [])
        }
    }
    
    # --- REPORT PERSISTENCE ---
    # Save report with timestamp for unique identification
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