import streamlit as st
import json
from pathlib import Path

def display():
    st.header("Logs & Reports")
    st.markdown("Download the detailed JSON report from your most recent extraction run.")
    
    report_path = st.session_state.get('last_report_path')

    if report_path and Path(report_path).exists():
        with open(report_path, 'r', encoding='utf-8') as f:
            report_data = json.load(f)
            
        st.subheader("Latest Report Summary")
        
        pdf_info = report_data.get('pdf_info', {})
        llm_info = report_data.get('llm_extraction_info', {})
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("PDF Name", pdf_info.get('file_name', 'N/A'))
            st.metric("Species Assessed", llm_info.get('total_species_assessed', 0))
        with col2:
            st.metric("LLM Provider", llm_info.get('provider', 'N/A'))
            st.metric("LLM Model", llm_info.get('model', 'N/A'))
        with col3:
            st.metric("Runtime", f"{llm_info.get('runtime_seconds', 0.0):.2f} s")
            st.metric("Total Tokens", f"{llm_info.get('total_input_tokens', 0) + llm_info.get('total_output_tokens', 0):,}")
            
        st.markdown("---")
        
        with open(report_path, 'rb') as f_bytes:
            st.download_button(
                label="📥 Download Full Report (JSON)",
                data=f_bytes,
                file_name=Path(report_path).name,
                mime="application/json"
            )
            
        with st.expander("Show Full Report JSON"):
            st.json(report_data)

    else:
        st.info("No report has been generated yet. Please run an extraction to create a report.")