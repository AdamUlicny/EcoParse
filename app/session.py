"""
Session State Management

Handles initialization and management of Streamlit session state variables
for maintaining application data across user interactions.
"""

import streamlit as st
import pandas as pd
import yaml
from pathlib import Path

def reset_session():
    """Reset all data-related session variables while preserving configuration."""
    # PDF and Text Data
    st.session_state.pdf_buffer = None
    st.session_state.pdf_name = ""
    st.session_state.full_text = ""
    st.session_state.last_uploaded_file_id = None
    
    # Species Data
    st.session_state.gnfinder_results_raw = None
    st.session_state.species_df_initial = pd.DataFrame()
    st.session_state.species_df_final = pd.DataFrame()
    
    # Extraction and Verification Results
    st.session_state.extraction_results = []
    st.session_state.verification_queue = []
    st.session_state.manual_verification_results = []
    st.session_state.automated_verification_results = []
    
    # Reporting and Metrics
    st.session_state.extraction_runtime = 0.0
    st.session_state.total_input_tokens = 0
    st.session_state.total_output_tokens = 0
    st.session_state.last_report_path = None
    
    # Session state management flag
    st.session_state.session_loaded_from_report = False

def initialize_session():
    """Initialize all session state variables on first application run."""
    if "session_initialized" in st.session_state:
        return
    
    # Initialize all data variables
    reset_session()
    
    # Set configuration defaults that persist across resets
    st.session_state.gnfinder_url = "http://localhost:4040/api/v1/find"
    st.session_state.llm_provider = "Google Gemini"
    st.session_state.google_api_key = ""
    st.session_state.google_model = "gemini-2.5-flash-lite"
    st.session_state.ollama_model = "gemma3:12b"
    st.session_state.ollama_url = "http://localhost:11434"
    
    # Load default project configuration
    default_config_path = Path(__file__).parent / "assets/default_project_config.yml"
    with open(default_config_path, 'r') as f:
        st.session_state.project_config_yaml = f.read()
    st.session_state.project_config = yaml.safe_load(st.session_state.project_config_yaml)
    
    # Extraction configuration defaults
    st.session_state.extraction_method = "Text-based"
    st.session_state.context_before = 0
    st.session_state.context_after = 250
    st.session_state.concurrent_requests = 5
    st.session_state.verification_concurrent_requests = 1
    st.session_state.prompt_examples = []
    
    # Verification settings
    st.session_state.verification_current_index = 0
    st.session_state.uploaded_gemini_file_id = None
    st.session_state.uploaded_gemini_file_display_name = None
    st.session_state.verification_gemini_model = "gemini-2.5-flash"
    st.session_state.verification_species_chunk_size = 5
    st.session_state.total_verification_input_tokens = 0
    st.session_state.total_verification_output_tokens = 0

    # Mark session as initialized
    st.session_state.session_initialized = True