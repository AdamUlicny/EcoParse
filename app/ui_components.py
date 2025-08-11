import streamlit as st
import pandas as pd
import json

def setup_sidebar():
    """Sets up the sidebar for global configuration."""
    st.header("⚙️ Global Configuration")

    st.text_input("GNfinder URL", key="gnfinder_url")

    st.selectbox(
        "LLM Provider",
        ["Google Gemini", "Ollama"],
        key="llm_provider"
    )

    st.markdown("---")

    is_gemini_selected = st.session_state.llm_provider == "Google Gemini"

    st.subheader("Google Gemini Settings")
    st.text_input(
        "Google API Key",
        type="password",
        key="google_api_key",
        disabled=not is_gemini_selected,
        help="Required only when using Google Gemini."
    )
    st.text_input(
        "Gemini Model Name",
        key="google_model",
        disabled=not is_gemini_selected,
        help="The Gemini model to use (e.g., 'gemini-1.5-flash-latest')."
    )

    st.markdown("---")

    st.subheader("Ollama Settings")
    st.text_input(
        "Ollama Host URL",
        key="ollama_url",
        disabled=is_gemini_selected,
        help="The full URL of the Ollama server (e.g., http://192.168.1.10:11434)."
    )
    
    st.text_input(
        "Ollama Model Name",
        key="ollama_model",
        disabled=is_gemini_selected,
        help="The local Ollama model to use (e.g., 'llama3')."
    )
    st.info("Ensure the Ollama application is running and the specified model is downloaded if using Ollama.")

def display_df_and_download(df: pd.DataFrame, title: str, file_prefix: str):
    """Displays a DataFrame and provides download buttons for CSV and JSON."""
    st.subheader(title)
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        
        csv_data = df.to_csv(index=False).encode('utf-8')
        json_data = df.to_json(orient='records', indent=2)

        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="📥 Download as CSV",
                data=csv_data,
                file_name=f"{file_prefix}.csv",
                mime="text/csv",
            )
        with col2:
            st.download_button(
                label="📥 Download as JSON",
                data=json_data,
                file_name=f"{file_prefix}.json",
                mime="application/json",
            )
    else:
        st.info("No data to display.")