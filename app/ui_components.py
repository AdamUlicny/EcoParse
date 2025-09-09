"""
UI Components and Configuration Interface

Streamlit UI components for global application configuration.
"""

import streamlit as st
import pandas as pd
import json
from app.ui_helpers import load_models_config, create_model_selector

def setup_sidebar():
    """Configure the main application sidebar with global settings."""
    st.header("⚙️ Global Configuration")

    st.text_input("GNfinder URL", key="gnfinder_url")
    st.selectbox("LLM Provider", ["Google Gemini", "Ollama"], key="llm_provider")
    st.markdown("---")

    is_gemini = st.session_state.llm_provider == "Google Gemini"

    # Gemini Settings
    st.subheader("Google Gemini Settings")
    st.text_input(
        "Google API Key",
        type="password",
        key="google_api_key",
        disabled=not is_gemini,
        help="Required for Google Gemini."
    )
    
    models_data = load_models_config()
    gemini_models = models_data.get("gemini_models", [])
    
    final_gemini = create_model_selector("Gemini", gemini_models, not is_gemini)
    if final_gemini:
        st.session_state.google_model = final_gemini
    elif "google_model" not in st.session_state:
        st.session_state.google_model = ""

    st.markdown("---")

    # Ollama Settings
    st.subheader("Ollama Settings")
    st.text_input(
        "Ollama Host URL",
        key="ollama_url",
        disabled=is_gemini,
        help="Full URL of Ollama server (e.g., http://192.168.1.10:11434)."
    )
    
    ollama_models = models_data.get("ollama_models", [])
    final_ollama = create_model_selector("Ollama", ollama_models, is_gemini)
    
    if final_ollama:
        st.session_state.ollama_model = final_ollama
    elif "ollama_model" not in st.session_state:
        st.session_state.ollama_model = ""
        
    st.info("Ensure Ollama is running and model is downloaded when using Ollama.")

def display_df_and_download(df: pd.DataFrame, title: str, file_prefix: str, context: str):
    """
    Display DataFrame with download options for CSV and JSON formats.
    
    Args:
        df: DataFrame to display and make downloadable
        title: Section title for the data display
        file_prefix: Filename prefix for downloaded files
        context: Unique identifier to prevent Streamlit widget key conflicts
    """
    st.subheader(title)
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        
        # Prepare download data
        csv_data = df.to_csv(index=False).encode('utf-8')
        json_data = df.to_json(orient='records', indent=2)

        # Create download buttons
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="📥 Download as CSV",
                data=csv_data,
                file_name=f"{file_prefix}.csv",
                mime="text/csv",
                key=f"csv_{context}_{file_prefix}" 
            )
        with col2:
            st.download_button(
                label="📥 Download as JSON",
                data=json_data,
                file_name=f"{file_prefix}.json",
                mime="application/json",
                key=f"json_{context}_{file_prefix}"
            )
            
    else:
        st.info("No data to display.")