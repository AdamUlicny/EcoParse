import streamlit as st
import pandas as pd
import yaml
from pathlib import Path

def initialize_session():
    """Initializes all session state variables."""
    if "session_initialized" in st.session_state:
        return
    # Initialize session state variables
    st.session_state.pdf_buffer = None
    st.session_state.pdf_name = ""
    st.session_state.full_text = ""
    st.session_state.last_uploaded_file_id = None
    st.session_state.gnfinder_results_raw = None
    st.session_state.species_df_initial = pd.DataFrame()
    st.session_state.species_df_final = pd.DataFrame()
    st.session_state.gnfinder_url = "http://localhost:4040/api/v1/find"
    st.session_state.llm_provider = "Google Gemini"
    st.session_state.google_api_key = ""
    st.session_state.google_model = "gemini-1.5-flash-latest"
    st.session_state.ollama_model = "llama3"
    default_config_path = Path(__file__).parent / "assets/default_project_config.yml"
    with open(default_config_path, 'r') as f:
        st.session_state.project_config_yaml = f.read()
    st.session_state.project_config = yaml.safe_load(st.session_state.project_config_yaml)
    st.session_state.extraction_method = "Text-based"
    st.session_state.context_before = 300
    st.session_state.context_after = 300
    st.session_state.concurrent_requests = 5
    st.session_state.extraction_results = []
    st.session_state.prompt_examples = []
    st.session_state.verification_queue = []
    st.session_state.verification_current_index = 0
    st.session_state.manual_verification_results = []

    # State for Reporting ---
    st.session_state.extraction_runtime = 0.0
    st.session_state.total_input_tokens = 0
    st.session_state.total_output_tokens = 0
    st.session_state.last_report_path = None
    
    st.session_state.session_initialized = True