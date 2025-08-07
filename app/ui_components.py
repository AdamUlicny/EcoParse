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

    if st.session_state.llm_provider == "Google Gemini":
        st.text_input("Google API Key", type="password", key="google_api_key")
        st.text_input("Gemini Model Name", key="google_model")
    else:
        st.text_input("Ollama Model Name", key="ollama_model")
        st.info("Ensure the Ollama application is running and the specified model is downloaded.")
        
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