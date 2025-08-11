import streamlit as st
import pandas as pd
from ecoparse.core.sourcetext import trim_pdf_pages, extract_text_from_pdf
from app.state_loader import load_state_from_report # Import our new function
import io

def display():
    st.header("Upload Document")

    uploaded_file = st.file_uploader(
        "Choose a PDF file to start a new session",
        type="pdf",
        help="Upload the document you want to analyze."
    )

    if uploaded_file:
        file_id = f"{uploaded_file.name}-{uploaded_file.size}"
        if file_id != st.session_state.get('last_uploaded_file_id'):
            st.session_state.pdf_buffer = uploaded_file.getvalue()
            st.session_state.pdf_name = uploaded_file.name
            st.session_state.last_uploaded_file_id = file_id
            # Reset subsequent steps
            st.session_state.full_text = ""
            st.session_state.gnfinder_results_raw = None
            st.session_state.species_df_initial = pd.DataFrame()
            st.session_state.species_df_final = pd.DataFrame()
            st.session_state.extraction_results = []
            st.success(f"Loaded '{uploaded_file.name}'. You can now process it below.")
            st.rerun()

    # --- NEW: Section to load from a report ---
    st.markdown("---")
    st.subheader("Or, Load a Previous Session")
    
    uploaded_report = st.file_uploader(
        "Choose a previously generated JSON report file",
        type="json",
        help="This will load all extracted and verified data from a past run."
    )
    
    if uploaded_report:
        with st.spinner("Loading report and populating session state..."):
            report_content = uploaded_report.read().decode("utf-8")
            required_pdf_name = load_state_from_report(report_content)
            
            if required_pdf_name:
                st.success(f"Successfully loaded data from report for '{required_pdf_name}'!")
                st.info("""
                **Session data has been restored.** You can now view results, continue manual verification, or download reports.
                
                **Note:** To use features that require the original document (like the context viewer in Manual Verification), please also upload the corresponding PDF file (`{}`) using the uploader at the top of the page.
                """.format(required_pdf_name))
                # Clear the uploader so it doesn't re-trigger on every action
                uploaded_report = None 
                st.rerun()
    
    st.markdown("---")
    # --- END OF NEW SECTION ---

    if st.session_state.pdf_buffer:
        st.info(f"**Current Document:** `{st.session_state.pdf_name}`")
        
        with st.expander("Process PDF and Extract Text", expanded=not st.session_state.full_text):
            st.markdown("Click the button below to extract text from the uploaded PDF.")
            
            # This part is simplified since trimming is less common. Can be re-added if needed.
            if st.button("Process Full Document", type="primary"):
                with st.spinner("Extracting text from PDF..."):
                    st.session_state.full_text = extract_text_from_pdf(io.BytesIO(st.session_state.pdf_buffer))
                    st.success(f"Extracted {len(st.session_state.full_text):,} characters.")
                    st.rerun()

    if st.session_state.full_text:
        st.subheader("Extracted Text Preview")
        st.text_area("Preview", st.session_state.full_text[:3000] + "...", height=300, disabled=True)
    elif not uploaded_report: # Don't show this message if we're loading a report
        st.info("Please upload a PDF to begin a new session, or upload a JSON report to load a previous one.")