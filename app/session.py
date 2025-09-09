"""
Session State Management

Streamlit session state initialization and management.
"""

import streamlit as st
import pandas as pd
import yaml
from pathlib import Path

def reset_session():
    """Reset data-related session variables, preserving configuration."""
    # Initialize data variables to None/empty values
    data_defaults = {
        'pdf_buffer': None,
        'pdf_name': "",
        'full_text': "",
        'gnfinder_results_raw': None,
        'species_df_initial': pd.DataFrame(),
        'species_df_final': pd.DataFrame(),
        'extraction_results': [],
        'last_report_path': None,
        'verification_queue': [],
        'manual_verification_results': [],
        'automated_verification_results': [],
        'uploaded_gemini_file_id': None,
        'uploaded_gemini_file_display_name': None,
        'session_loaded_from_report': False,
        'extraction_method_used': 'standard',
        # Extraction control variables
        'extraction_running': False,
        'extraction_paused': False,
        'extraction_progress': 0,
        'extraction_total': 0,
        'extraction_runtime': 0,
        'total_input_tokens': 0,
        'total_output_tokens': 0,
        'species_to_process': [],
        'extractor': None,
        'source_context': {}
    }
    
    for var, default_value in data_defaults.items():
        st.session_state[var] = default_value

def initialize_session():
    """Initialize session state variables on first run."""
    if getattr(st.session_state, 'session_initialized', False):
        return
    
    reset_session()
    
    # Configuration defaults
    defaults = {
        'gnfinder_url': "http://localhost:4040/api/v1/find",
        'llm_provider': "Google Gemini", 
        'google_api_key': "",
        'google_model': "gemini-2.5-flash-lite",
        'ollama_model': "mistral:instruct",
        'ollama_url': "http://localhost:11434",
        'extraction_method': "Text-based",
        'context_before': 0,
        'context_after': 500,
        'concurrent_requests': 5,
        'verification_concurrent_requests': 1,
        'prompt_examples': [],
        'verification_current_index': 0,
        'verification_gemini_model': "gemini-2.5-flash",
        'verification_species_chunk_size': 5,
        'total_verification_input_tokens': 0,
        'total_verification_output_tokens': 0
    }
    
    for key, value in defaults.items():
        st.session_state[key] = value

    
    # Load default project configuration
    default_config_path = Path(__file__).parent / "assets/default_project_config.yml"
    with open(default_config_path, 'r') as f:
        st.session_state.project_config_yaml = f.read()
    st.session_state.project_config = yaml.safe_load(st.session_state.project_config_yaml)

    st.session_state.session_initialized = True