import streamlit as st
import pandas as pd
from app.session import get_llm_config
from app.ui_components import display_df_and_download
from app.agent.core import run_agent_pipeline
import yaml

def config_to_yaml_str(config):
    return yaml.dump(config, sort_keys=False)

def display():
    """Main display function for the Agent Workflow tab."""
    st.header("0. Agent Workflow")
    st.markdown("Automated species extraction for Tetrapods based on a dropped PDF and context description.")
    
    st.info("This agent uses **OpenRouter** to construct a configuration based on your context, and **Gemini 2.5 Flash** to analyze the PDF pages and extract data using Image-based chunking.")

    # Requirements check
    gemini_key = st.secrets.get("model_api_keys", {}).get("Google Gemini")
    openrouter_key = st.secrets.get("model_api_keys", {}).get("OpenRouter")
    
    if not gemini_key or not openrouter_key:
        st.warning("Please ensure both Google Gemini and OpenRouter API keys are set in `secrets.toml` or the Settings sidebar to use the Agent Flow.")
        
    # Inputs
    uploaded_file = st.file_uploader("Upload PDF Document", type="pdf", key="agent_pdf_upload")
    
    user_context = st.text_area(
        "Extraction Context", 
        placeholder="e.g. Please extract the red list categories and IUCN assessments...",
        height=100
    )
    
    if st.button("Run automated extraction", type="primary", disabled=not (uploaded_file and user_context)):
        if not (gemini_key and openrouter_key):
            st.error("Missing API keys for Agent Flow.")
            return
            
        st.session_state.agent_running = True
        progress_bar = st.progress(0, text="Starting Agent Pipeline...")
        
        def ui_progress_callback(msg, val):
            progress_bar.progress(val / 100.0, text=msg)
            
        try:
            gnfinder_url = st.session_state.get("gnfinder_url", "http://localhost:4040/api/v1/find")
            
            with st.spinner("Agent is working..."):
                config, results = run_agent_pipeline(
                    pdf_buffer=uploaded_file.getvalue(),
                    context=user_context,
                    openrouter_key=openrouter_key,
                    gemini_key=gemini_key,
                    gnfinder_url=gnfinder_url,
                    progress_callback=ui_progress_callback
                )
                
            st.success("Agent Pipeline Completed!")
            
            # Show created Config
            with st.expander("Generated Configurations", expanded=False):
                st.code(config_to_yaml_str(config), language="yaml")
                
            # Show Extracted Results
            if results:
                st.subheader("Extraction Results")
                
                # Flatten results for DataFrame
                flat_data = []
                for entry in results:
                    flat_data.append({
                        "Species": entry.get("species", "Unknown"),
                        **entry.get("data", {}),
                        "Notes": entry.get("notes", "")
                    })
                    
                df = pd.DataFrame(flat_data)
                
                st.dataframe(df, use_container_width=True)
                
                # Allow download
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download Results as CSV",
                    data=csv,
                    file_name="agent_extraction_results.csv",
                    mime="text/csv",
                )
            else:
                st.warning("No species data extracted.")
                
        except Exception as e:
            st.error(f"Agent Pipeline failed: {str(e)}")
            import traceback
            st.code(traceback.format_exc())
            
        finally:
            st.session_state.agent_running = False
