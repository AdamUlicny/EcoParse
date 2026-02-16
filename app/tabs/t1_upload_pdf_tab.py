"""
Tab 1: PDF Upload and Processing

Handles document upload, page range selection, and text extraction.
"""

import streamlit as st
import pandas as pd
import json
import glob
import os
from ecoparse.core.sourcetext import trim_pdf_pages, extract_text_from_pdf
from app.session import reset_session 
from app.ui_messages import show_loaded_session_complete, show_method_change_success
from app.ui_helpers import create_extraction_method_selector
import io
from PyPDF2 import PdfReader

def display():
    """Main display function for the PDF upload tab."""
    st.header("1. Upload and Process Document")

    if st.session_state.get("session_loaded_from_report", False):
        display_loaded_session_view()
    else:
        display_new_session_view()

def display_loaded_session_view():
    """Display interface when session is loaded from a previous report."""
    st.success(f"✅ **Session Loaded** for: **{st.session_state.pdf_name}**")
    st.info("Proceed to other tabs to view results or continue verification.")
    
    if st.button("🔄 Start New Session", type="primary"):
        reset_session()
        st.rerun()

    st.markdown("---")
    st.subheader("Upload PDF for Context Features (Optional)")
    st.markdown("Upload the original PDF to enable image context viewer in verification tabs.")
    
    uploaded_file = st.file_uploader("Upload PDF for context", type="pdf", key="pdf_for_loaded_session")
    if uploaded_file:
        # Check if we should auto-trim
        trim_start = st.session_state.get('trim_start_page')
        trim_end = st.session_state.get('trim_end_page')
        
        if trim_start and trim_end:
             try:
                with st.spinner(f"Auto-trimming PDF to pages {trim_start}-{trim_end} as per log..."):
                    dataset_buffer = io.BytesIO(uploaded_file.getvalue())
                    trimmed = trim_pdf_pages(dataset_buffer, int(trim_start), int(trim_end))
                    if trimmed:
                        st.session_state.pdf_buffer = trimmed.getvalue()
                        # Extract text for page mapping
                        st.session_state.full_text = extract_text_from_pdf(trimmed, method=st.session_state.get('extraction_method_used', 'standard'))
                        st.success(f"PDF '{uploaded_file.name}' loaded, trimmed, and text extracted.")
                    else:
                        st.session_state.pdf_buffer = uploaded_file.getvalue()
                        # Extract text for page mapping
                        st.session_state.full_text = extract_text_from_pdf(io.BytesIO(uploaded_file.getvalue()), method=st.session_state.get('extraction_method_used', 'standard'))
                        st.warning(f"Failed to auto-trim PDF. Loaded full document '{uploaded_file.name}'.")
             except Exception as e:
                 st.session_state.pdf_buffer = uploaded_file.getvalue()
                 st.session_state.full_text = extract_text_from_pdf(io.BytesIO(uploaded_file.getvalue()), method=st.session_state.get('extraction_method_used', 'standard'))
                 st.error(f"Error during auto-trim: {e}. Loaded full document.")
        else:
            st.session_state.pdf_buffer = uploaded_file.getvalue()
            st.session_state.full_text = extract_text_from_pdf(io.BytesIO(uploaded_file.getvalue()), method=st.session_state.get('extraction_method_used', 'standard'))
            st.success(f"PDF '{uploaded_file.name}' loaded for context features (Full Document).")

def display_new_session_view():
    """Display interface for starting a new extraction session with PDF upload."""
    
    # --- LOAD FROM LOG SECTION ---
    with st.expander("📂 Load Previous Session from Log", expanded=False):
        st.markdown("Restore extraction results and settings from a saved execution log.")
        
        log_files = glob.glob("logs/ecoparse_report_*.json")
        # Sort by modification time, newest first
        log_files.sort(key=os.path.getmtime, reverse=True)
        
        if not log_files:
            st.info("No log files found.")
        else:
            selected_log = st.selectbox("Select Log File", log_files, format_func=lambda x: os.path.basename(x))
            
            if st.button("Load Selected Session"):
                try:
                    with open(selected_log, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Reset current session
                    reset_session()
                    
                    # Restore Data
                    # Restore Data
                    st.session_state.extraction_results = data.get("llm_extraction_info", {}).get("full_extraction_results", [])
                    st.session_state.project_config = data.get("project_config_used", {})
                    st.session_state.prompt_examples = data.get("llm_extraction_info", {}).get("examples_used", [])
                    st.session_state.pdf_name = data.get("pdf_info", {}).get("file_name", "Unknown PDF")
                    
                    # Restore Species Lists (Fix for Tab 2)
                    gnfinder_info = data.get("gnfinder_info", {})
                    if "final_species_list" in gnfinder_info:
                        species_list = gnfinder_info["final_species_list"]
                        st.session_state.species_df_final = pd.DataFrame(species_list)
                        st.session_state.species_df_initial = st.session_state.species_df_final.copy()
                        st.session_state.gnfinder_results_raw = {"names": []} # Dummy to prevent errors if checked
                    
                    # Restore Trim Info if available
                    pdf_info = data.get("pdf_info", {})
                    st.session_state.trim_start_page = pdf_info.get("trim_start_page")
                    st.session_state.trim_end_page = pdf_info.get("trim_end_page")

                    # Set Flag
                    st.session_state.session_loaded_from_report = True
                    st.success(f"Session loaded from {os.path.basename(selected_log)}")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Error loading session: {e}")

    st.divider()

    st.subheader("Start a New Session by Uploading a PDF")
    
    def on_pdf_upload():
        """Handle new PDF upload and reset session state."""
        uploaded_file = st.session_state.new_pdf_uploader
        if uploaded_file is not None:
            # Clear previous session data
            reset_session()
            st.session_state.pdf_buffer = uploaded_file.getvalue()
            st.session_state.pdf_name = uploaded_file.name
    
    # PDF file uploader with change callback
    st.file_uploader(
        "Choose a PDF file",
        type="pdf",
        key="new_pdf_uploader",
        on_change=on_pdf_upload
    )
    if st.session_state.get('pdf_buffer'):
        st.info(f"**Current Document:** `{st.session_state.pdf_name}`")
        with st.expander("Process PDF and Extract Text", expanded=not st.session_state.full_text):
            st.markdown("Select a page range to focus the analysis, then click the button to extract text.")
            
            try:
                reader = PdfReader(io.BytesIO(st.session_state.pdf_buffer))
                num_pages = len(reader.pages)

                col1, col2 = st.columns(2)
                with col1:
                    start_page = st.number_input("Start Page", 1, num_pages, 1)
                with col2:
                    end_page = st.number_input("End Page", 1, num_pages, num_pages)

                # Text extraction method selection
                st.subheader("Text Extraction Method")
                extraction_method = create_extraction_method_selector(key_suffix="pdf_upload")

                if st.button("Trim PDF & Extract Text", type="primary"):
                    if start_page > end_page:
                        st.error("Start page must not be after end page.")
                    else:
                        with st.spinner("Processing PDF..."):
                            original_buffer = io.BytesIO(st.session_state.pdf_buffer)
                            trimmed_buffer = trim_pdf_pages(original_buffer, start_page, end_page)
                            if trimmed_buffer:
                                st.session_state.pdf_buffer = trimmed_buffer.getvalue() 
                                st.session_state.full_text = extract_text_from_pdf(trimmed_buffer, method=extraction_method)
                                st.session_state.extraction_method_used = extraction_method
                                # Save trim info for reporting
                                st.session_state.trim_start_page = start_page
                                st.session_state.trim_end_page = end_page
                                show_method_change_success(extraction_method, len(st.session_state.full_text))
                                st.rerun()
                            else:
                                st.error("Failed to trim PDF.")
            except Exception as e:
                st.error(f"Could not read the uploaded PDF. It may be corrupted. Error: {e}")
    
    if st.session_state.get('full_text'):
        st.subheader("Extracted Text Preview")
        st.text_area("Preview", st.session_state.full_text[:3000000] + "...", height=300, disabled=True)
