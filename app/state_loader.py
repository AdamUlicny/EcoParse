import streamlit as st
import pandas as pd
import json
from typing import Optional

def load_state_from_report(report_content: str) -> Optional[str]:
    """
    Parses a JSON report and populates the Streamlit session state.

    Args:
        report_content: The string content of the JSON report file.

    Returns:
        The name of the PDF file associated with the report if successful, otherwise None.
    """
    try:
        data = json.loads(report_content)

        # Clear existing results to ensure a clean load
        st.session_state.extraction_results = []
        st.session_state.manual_verification_results = []
        st.session_state.automated_verification_results = []

        # --- Load PDF Info ---
        pdf_info = data.get("pdf_info", {})
        st.session_state.pdf_name = pdf_info.get("file_name", "N/A")
        st.session_state.full_text = "Text loaded from report, not extracted." if st.session_state.pdf_name != "N/A" else ""

        # --- Load GNfinder Info ---
        gnfinder_info = data.get("gnfinder_info", {})
        # We can't reconstruct the DataFrames perfectly without the raw results,
        # but we can load the most important one: the final list of species.
        # For simplicity, we assume the full_extraction_results contains all species.
        llm_info = data.get("llm_extraction_info", {})
        extraction_results = llm_info.get("full_extraction_results", [])
        if extraction_results:
            species_names = [res.get("species") for res in extraction_results]
            st.session_state.species_df_final = pd.DataFrame(species_names, columns=["Name"])
        
        # --- Load LLM Extraction Info ---
        st.session_state.extraction_results = extraction_results
        st.session_state.extraction_runtime = llm_info.get("runtime_seconds", 0.0)
        st.session_state.total_input_tokens = llm_info.get("total_input_tokens", 0)
        st.session_state.total_output_tokens = llm_info.get("total_output_tokens", 0)
        
        # --- Load Project Configuration ---
        project_config = data.get("project_config_used", {})
        if project_config:
            import yaml
            st.session_state.project_config = project_config
            st.session_state.project_config_yaml = yaml.dump(project_config)
        
        # --- Load Manual Verification Info ---
        manual_info = data.get("manual_verification_info", {})
        if manual_info.get("run"):
            st.session_state.manual_verification_results = manual_info.get("full_results", [])
            
        # --- (Optional) Load Automated Verification Info ---
        # This part can be expanded if you add automated verification to the report
        
        return st.session_state.pdf_name

    except (json.JSONDecodeError, KeyError) as e:
        st.error(f"Failed to load report. The file may be corrupted or in an invalid format. Error: {e}")
        return None