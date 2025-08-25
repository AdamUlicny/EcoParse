import streamlit as st
import pandas as pd
import json
import yaml
from pathlib import Path

def load_models_list():
    """Load available models from the models_list.yml file."""
    models_file = Path(__file__).parent / "assets" / "models_list.yml"
    try:
        with open(models_file, 'r', encoding='utf-8') as f:
            models_data = yaml.safe_load(f)
        return models_data
    except FileNotFoundError:
        st.warning(f"Models list file not found: {models_file}")
        return {"ollama_models": [], "gemini_models": []}
    except Exception as e:
        st.error(f"Error loading models list: {e}")
        return {"ollama_models": [], "gemini_models": []}

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
    
    # Load available Gemini models
    models_data = load_models_list()
    gemini_models = models_data.get("gemini_models", [])
    
    # Create dropdown options for Gemini
    gemini_options = ["Select a model..."] + [model["name"] for model in gemini_models]
    
    # Gemini model selection dropdown
    selected_gemini = st.selectbox(
        "Select Gemini Model",
        options=gemini_options,
        key="gemini_model_dropdown",
        disabled=not is_gemini_selected,
        help="Choose from available Gemini models or use 'Custom Model' to enter your own."
    )
    
    # Custom Gemini model text input
    use_custom_gemini = st.checkbox(
        "Use custom Gemini model", 
        key="use_custom_gemini_model",
        disabled=not is_gemini_selected,
        help="Check this to enter a custom Gemini model name not in the dropdown list."
    )
    
    if use_custom_gemini:
        custom_gemini = st.text_input(
            "Custom Gemini Model Name",
            key="custom_gemini_model",
            disabled=not is_gemini_selected,
            help="Enter the name of a custom Gemini model (e.g., 'gemini-1.5-flash-002')."
        )
        # Use custom model if provided, otherwise fall back to dropdown selection
        final_gemini = custom_gemini if custom_gemini else selected_gemini
    else:
        final_gemini = selected_gemini
    
    # Store the final Gemini model selection in session state
    if final_gemini and final_gemini != "Select a model...":
        st.session_state.google_model = final_gemini
    elif "google_model" not in st.session_state:
        st.session_state.google_model = ""

    st.markdown("---")

    st.subheader("Ollama Settings")
    st.text_input(
        "Ollama Host URL",
        key="ollama_url",
        disabled=is_gemini_selected,
        help="The full URL of the Ollama server (e.g., http://192.168.1.10:11434)."
    )
    
    # Load available models
    models_data = load_models_list()
    ollama_models = models_data.get("ollama_models", [])
    
    # Create dropdown options
    model_options = ["Select a model..."] + [model["name"] for model in ollama_models]
    
    # Model selection dropdown
    selected_model = st.selectbox(
        "Select Ollama Model",
        options=model_options,
        key="ollama_model_dropdown",
        disabled=is_gemini_selected,
        help="Choose from Ollama models in /assets/models_list.yml or use 'Custom Model' to enter your own."
    )
    
    # Add "Custom Model" option
    if selected_model == "Select a model...":
        selected_model = None
    
    # Custom model text input
    use_custom = st.checkbox(
        "Use custom model", 
        key="use_custom_ollama_model",
        disabled=is_gemini_selected,
        help="Check this to enter a custom model name not in the dropdown list."
    )
    
    if use_custom:
        custom_model = st.text_input(
            "Custom Ollama Model Name",
            key="custom_ollama_model",
            disabled=is_gemini_selected,
            help="Enter the name of a custom Ollama model (e.g., 'custom-llama', 'fine-tuned-model')."
        )
        # Use custom model if provided, otherwise fall back to dropdown selection
        final_model = custom_model if custom_model else selected_model
    else:
        final_model = selected_model
    
    # Store the final model selection in session state
    if final_model and final_model != "Select a model...":
        st.session_state.ollama_model = final_model
    elif "ollama_model" not in st.session_state:
        st.session_state.ollama_model = ""
        
    st.info("Ensure the Ollama application is running and the specified model is downloaded if using Ollama.")

def display_df_and_download(df: pd.DataFrame, title: str, file_prefix: str, context:str):
    """
    Displays a DataFrame and provides download buttons for CSV and JSON.
    
    Args:
        df (pd.DataFrame): The DataFrame to display.
        title (str): The title for the subheader.
        file_prefix (str): A prefix for the download filenames.
        context (str): A unique string from the calling location to ensure widget keys are unique.
    """
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