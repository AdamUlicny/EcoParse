import streamlit as st
import pandas as pd
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
    provider = st.session_state.get("llm_provider", "OpenRouter")
    
    if provider == "Google Gemini":
        api_key = st.session_state.get("google_api_key")
        model = st.session_state.get("google_model", "gemini-2.5-flash")
    elif provider == "OpenRouter":
        api_key = st.session_state.get("openrouter_api_key")
        model = st.session_state.get("openrouter_model", "anthropic/claude-3.5-sonnet")
    elif provider == "Ollama":
        api_key = st.session_state.get("ollama_url", "http://localhost:11434")
        model = st.session_state.get("ollama_model", "mistral:instruct")
    
    if not api_key:
        st.warning(f"Please ensure the API key (or URL) for {provider} is set in the Settings sidebar to use the Agent Flow.")
        
    # Inputs
    uploaded_file = st.file_uploader("Upload PDF Document", type="pdf", key="agent_pdf_upload")
    
    user_context = st.text_area(
        "Extraction Context", 
        placeholder="e.g. Please extract the red list categories and IUCN assessments...",
        height=100
    )
    
    if st.button("Run automated extraction", type="primary", disabled=not (uploaded_file and user_context)):
        if not api_key:
            st.error(f"Missing configuration for {provider}.")
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
                    provider=provider,
                    api_key=api_key,
                    model=model,
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
