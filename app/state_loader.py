      
import streamlit as st
import pandas as pd
import json
from typing import Optional

def load_state_from_report(report_content: str) -> Optional[str]:
    """
    Parses a JSON report and populates the Streamlit session state.
    """
    try:
        data = json.loads(report_content)
        
        # Call the centralized reset function to ensure a clean slate
        from .session import reset_session
        reset_session()

        # Set the global flag to indicate we are in a "loaded" state
        st.session_state.session_loaded_from_report = True
        
        # --- Now, load the data ---
        pdf_info = data.get("pdf_info", {})
        st.session_state.pdf_name = pdf_info.get("file_name", "N/A")
        
        gnfinder_info = data.get("gnfinder_info", {})
        final_species_list = gnfinder_info.get("final_species_list")
        if final_species_list:
            st.session_state.species_df_final = pd.DataFrame(final_species_list)
        
        llm_info = data.get("llm_extraction_info", {})
        st.session_state.extraction_results = llm_info.get("full_extraction_results", [])
        if not st.session_state.extraction_results:
            st.warning("Report loaded successfully, but it does not contain any extraction results. The 'full_extraction_results' list was either missing or empty in the JSON file.")
        st.session_state.extraction_runtime = llm_info.get("runtime_seconds", 0.0)
        st.session_state.total_input_tokens = llm_info.get("total_input_tokens", 0)
        st.session_state.total_output_tokens = llm_info.get("total_output_tokens", 0)
        
        project_config = data.get("project_config_used", {})
        if project_config:
            import yaml
            st.session_state.project_config = project_config
            st.session_state.project_config_yaml = yaml.dump(project_config)
            
        return st.session_state.pdf_name

    except (json.JSONDecodeError, KeyError) as e:
        st.error(f"Failed to load report. The file may be corrupted or in an invalid format. Error: {e}")
        return None

    