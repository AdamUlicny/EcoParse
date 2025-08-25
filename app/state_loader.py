"""
Session State Restoration from Reports

Utilities for loading application state from previously generated JSON reports,
enabling users to resume analysis or review past extraction results.
"""
      
import streamlit as st
import pandas as pd
import json
from typing import Optional

def load_state_from_report(report_content: str) -> Optional[str]:
    """
    Parse JSON report and restore session state for analysis continuation.
    
    Args:
        report_content: JSON report string from previous extraction run
        
    Returns:
        PDF filename if successful, None if loading failed
    """
    try:
        data = json.loads(report_content)
        
        # Reset session state to clean slate
        from .session import reset_session
        reset_session()

        # Mark session as loaded from report
        st.session_state.session_loaded_from_report = True
        
        # Load PDF information
        pdf_info = data.get("pdf_info", {})
        st.session_state.pdf_name = pdf_info.get("file_name", "N/A")
        
        # Load species identification results
        gnfinder_info = data.get("gnfinder_info", {})
        final_species_list = gnfinder_info.get("final_species_list")
        if final_species_list:
            st.session_state.species_df_final = pd.DataFrame(final_species_list)
        
        # Load extraction results and metrics
        llm_info = data.get("llm_extraction_info", {})
        st.session_state.extraction_results = llm_info.get("full_extraction_results", [])
        if not st.session_state.extraction_results:
            st.warning("Report loaded successfully, but it does not contain any extraction results. The 'full_extraction_results' list was either missing or empty in the JSON file.")
        st.session_state.extraction_runtime = llm_info.get("runtime_seconds", 0.0)
        st.session_state.total_input_tokens = llm_info.get("total_input_tokens", 0)
        st.session_state.total_output_tokens = llm_info.get("total_output_tokens", 0)
        
        # Load project configuration
        project_config = data.get("project_config_used", {})
        if project_config:
            import yaml
            st.session_state.project_config = project_config
            st.session_state.project_config_yaml = yaml.dump(project_config)
            
        return st.session_state.pdf_name

    except (json.JSONDecodeError, KeyError) as e:
        st.error(f"Failed to load report. The file may be corrupted or in an invalid format. Error: {e}")
        return None

    