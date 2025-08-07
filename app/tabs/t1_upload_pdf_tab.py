import streamlit as st
import pandas as pd
from ecoparse.core.sourcetext import trim_pdf_pages, extract_text_from_pdf

def display():
    st.header("Upload Document")

    uploaded_file = st.file_uploader(
        "Choose a PDF file",
        type="pdf",
        help="Upload the document you want to analyze."
    )

    if uploaded_file:
        # Generate a unique ID for the uploaded file to detect changes
        file_id = f"{uploaded_file.name}-{uploaded_file.size}"

        # If a new file is uploaded, reset downstream data
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
            st.success(f"Loaded '{uploaded_file.name}'. Proceed to the next step.")
            st.rerun()

    if st.session_state.pdf_buffer:
        st.info(f"**Current Document:** `{st.session_state.pdf_name}`")
        
        with st.expander("Trim PDF and Extract Text", expanded=not st.session_state.full_text):
            st.markdown("""
            You can process the entire document or trim it to a specific page range. 
            Text will be extracted from the selected pages.
            """)
            
            from PyPDF2 import PdfReader
            import io
            reader = PdfReader(io.BytesIO(st.session_state.pdf_buffer))
            num_pages = len(reader.pages)

            col1, col2 = st.columns(2)
            with col1:
                start_page = st.number_input("Start Page", 1, num_pages, 1)
            with col2:
                end_page = st.number_input("End Page", 1, num_pages, num_pages)

            if st.button("Process Document", type="primary"):
                if start_page > end_page:
                    st.error("Start page must not be after end page.")
                else:
                    with st.spinner("Trimming PDF and extracting text..."):
                        trimmed_buffer = trim_pdf_pages(
                            io.BytesIO(st.session_state.pdf_buffer), start_page, end_page
                        )
                        if trimmed_buffer:
                            st.session_state.pdf_buffer = trimmed_buffer.getvalue() # Update buffer to trimmed version
                            st.session_state.full_text = extract_text_from_pdf(trimmed_buffer)
                            st.success(f"Text extracted from {len(st.session_state.full_text):,} characters.")
                            st.rerun()
                        else:
                            st.error("Failed to trim PDF.")

    if st.session_state.full_text:
        st.subheader("Extracted Text Preview")
        st.text_area("Preview", st.session_state.full_text[:3000] + "...", height=300, disabled=True)
    else:
        st.info("Please upload a PDF to begin.")