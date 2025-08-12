import streamlit as st
import pandas as pd
from ecoparse.core.sourcetext import trim_pdf_pages, extract_text_from_pdf
from app.state_loader import load_state_from_report
from app.session import reset_session # Import the centralized reset function
import io
from PyPDF2 import PdfReader

def display():
    st.header("1. Upload and Process Document")

    # This is the main control switch for the tab's appearance.
    # If a session is loaded from a report, show the "loaded" view.
    if st.session_state.get("session_loaded_from_report", False):
        display_loaded_session_view()
    else:
        # Otherwise, show the default "new session" workflow.
        display_new_session_view()

def display_loaded_session_view():
    """
    Renders the UI for when a user has loaded a session from a report.
    This view is primarily informational and provides a way to start over.
    """
    st.success(f"✅ **Session Loaded from Report** for document: **{st.session_state.pdf_name}**")
    st.info("You can now proceed to the other tabs to view results or continue verification.")
    
    if st.button("🔄 Start a New Session", type="primary"):
        reset_session()
        st.rerun()

    st.markdown("---")
    st.subheader("Upload Corresponding PDF (Optional)")
    st.markdown("To use features that require the original document (like the image context viewer in the verification tabs), please upload the PDF file below.")
    
    uploaded_file = st.file_uploader(
        "Upload PDF for loaded session",
        type="pdf",
        key="pdf_for_loaded_session"
    )
    if uploaded_file:
        st.session_state.pdf_buffer = uploaded_file.getvalue()
        st.success(f"PDF '{uploaded_file.name}' has been loaded and is available for context-aware features.")

def display_new_session_view():
    """
    Renders the default UI for starting a new session from a PDF.
    """
    st.subheader("Start a New Session by Uploading a PDF")
    
    def on_pdf_upload():
        """This callback runs ONLY when the user uploads a new PDF."""
        uploaded_file = st.session_state.new_pdf_uploader
        if uploaded_file is not None:
            # Ensure any old data is cleared before loading the new file
            reset_session()
            st.session_state.pdf_buffer = uploaded_file.getvalue()
            st.session_state.pdf_name = uploaded_file.name
    
    # The primary PDF uploader now uses the on_change callback.
    st.file_uploader(
        "Choose a PDF file",
        type="pdf",
        key="new_pdf_uploader",
        on_change=on_pdf_upload
    )
    if st.session_state.pdf_buffer:
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

                if st.button("Trim PDF & Extract Text", type="primary"):
                    if start_page > end_page:
                        st.error("Start page must not be after the end page.")
                    else:
                        with st.spinner("Trimming PDF and extracting text..."):
                            original_buffer = io.BytesIO(st.session_state.pdf_buffer)
                            trimmed_buffer = trim_pdf_pages(original_buffer, start_page, end_page)
                            if trimmed_buffer:
                                st.session_state.pdf_buffer = trimmed_buffer.getvalue() 
                                st.session_state.full_text = extract_text_from_pdf(trimmed_buffer)
                                st.success(f"Trimmed to pages {start_page}-{end_page} and extracted {len(st.session_state.full_text):,} characters.")
                                st.rerun()
                            else:
                                st.error("Failed to trim PDF.")
            except Exception as e:
                st.error(f"Could not read the uploaded PDF. It may be corrupted. Error: {e}")
    
    if st.session_state.full_text:
        st.subheader("Extracted Text Preview")
        st.text_area("Preview", st.session_state.full_text[:3000] + "...", height=300, disabled=True)

    # --- Secondary Option: Load Session ---
    st.markdown("---")
    st.subheader("Or, Load a Previous Session")
    
    def on_report_upload():
        uploaded_report = st.session_state.report_uploader
        if uploaded_report is not None:
            report_content = uploaded_report.read().decode("utf-8")
            load_state_from_report(report_content)
            # No need to set flags, the main rerun will check the session_loaded_from_report state
    
    st.file_uploader(
        "Choose a previously generated JSON report file",
        type="json",
        key="report_uploader",
        on_change=on_report_upload
    )