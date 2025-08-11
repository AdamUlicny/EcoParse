import streamlit as st
import pandas as pd
import json
import time
import io
import tempfile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from plotly import express as px

from google import genai
from google.genai import types

from ecoparse.core.verifier import Verifier
from app.ui_components import display_df_and_download


def display():
    st.header("🔍 Automated LLM Verification")
    st.markdown("Verify the entire list of extracted species data against the full PDF by sending chunks of species to Gemini.")
    st.warning("⚠️ **Warning:** This method sends the full PDF with each request, which can incur very high token costs, especially for large PDFs. Adjust 'Species per Request' to manage cost and latency!")

    st.subheader("⚙️ Verification Settings")

    col1, col2 = st.columns(2)
    with col1:
        st.selectbox(
            "Gemini Model for Verification",
            ["gemini-1.5-flash-latest", "gemini-1.5-pro-latest", "gemini-pro"],
            key="verification_gemini_model"
        )
    with col2:
        st.number_input(
            "Species per Request (Chunk Size)",
            min_value=1, max_value=50, value=st.session_state.get("verification_species_chunk_size", 5), step=1,
            help="Number of species to verify in each API call. Smaller chunks reduce per-request cost/latency but increase total calls.",
            key="verification_species_chunk_size"
        )

    st.subheader("📤 Upload PDF to Gemini File Manager")
    st.info("The entire PDF document needs to be uploaded to Gemini's File Manager once. This file will be sent with each chunked verification request.")

    api_key = st.session_state.google_api_key
    pdf_file_buffer_bytes = st.session_state.pdf_buffer # The raw bytes of the processed PDF

    if pdf_file_buffer_bytes and api_key:
        if not st.session_state.get("uploaded_gemini_file_id"): 
            if st.button("Upload Full PDF to Gemini File Manager"):
                if not api_key:
                    st.error("Please provide your Google API key in the sidebar configuration.")
                    st.stop()
                
                try:
                    with st.spinner("Uploading entire PDF to Gemini... This might take a while and incur cost for storage."):
                        client = genai.Client(api_key=api_key)
                        
                        # Write buffer to a temporary file for upload
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                            tmp_file.write(pdf_file_buffer_bytes)
                            tmp_pdf_path = Path(tmp_file.name)
                        
                        uploaded_gemini_file_obj = client.files.upload(file=tmp_pdf_path)
                        tmp_pdf_path.unlink() # Clean up temp file
                        
                        st.session_state.uploaded_gemini_file_id = uploaded_gemini_file_obj.name
                        st.session_state.uploaded_gemini_file_display_name = uploaded_gemini_file_obj.display_name or uploaded_gemini_file_obj.name
                        
                        st.success(f"✅ Full PDF uploaded to Gemini successfully! File ID: {uploaded_gemini_file_obj.name}")
                        st.caption("This file will be automatically deleted from Gemini after 48 hours or when manually deleted.")
                        time.sleep(2)
                        st.rerun() # Rerun to update button state
                except Exception as e:
                    st.error(f"❌ Error uploading full PDF to Gemini: {str(e)}")
        else:
            st.success(f"Full PDF '{st.session_state.uploaded_gemini_file_display_name}' (ID: {st.session_state.uploaded_gemini_file_id}) is already uploaded to Gemini.")
            st.info("Proceed to 'Run Verification' below.")
            
    elif pdf_file_buffer_bytes is None:
        st.warning("Please upload and process a PDF in the '1. Upload PDF' tab first.")
    else:
        st.warning("Please provide your Google API key in the sidebar configuration to upload files.")


    st.subheader("🔬 Run Verification")

    if st.session_state.get("uploaded_gemini_file_id") and st.session_state.extraction_results:
        st.write("**Data to verify (from '4. Run Extraction' tab):**")
        verification_df_input = pd.DataFrame(st.session_state.extraction_results)
        st.dataframe(verification_df_input, use_container_width=True)

        st.metric("Estimated Input Tokens (Verification)", st.session_state.total_verification_input_tokens)
        st.metric("Estimated Output Tokens (Verification)", st.session_state.total_verification_output_tokens)


        if st.button("🚀 Start Full List Verification"):
            if not st.session_state.google_api_key:
                st.error("Google API key is required for Gemini verification. Please set it in the sidebar.")
                st.stop()
            if not st.session_state.uploaded_gemini_file_id:
                st.error("Please upload the PDF to Gemini File Manager first.")
                st.stop()

            # Reset token counters for this run
            st.session_state.total_verification_input_tokens = 0
            st.session_state.total_verification_output_tokens = 0
            st.session_state.automated_verification_results = [] # Clear previous results

            # Re-initialize Gemini client and get the File object
            try:
                gemini_client_for_run = genai.Client(api_key=api_key)
                uploaded_file_obj_for_llm = gemini_client_for_run.files.get(st.session_state.uploaded_gemini_file_id)
            except Exception as e:
                st.error(f"Failed to retrieve uploaded Gemini file: {e}. Please try re-uploading the PDF.")
                st.stop()

            verifier = Verifier(
                st.session_state.project_config,
                {"api_key": api_key, "model": st.session_state.verification_gemini_model}
            )

            # Prepare chunks
            all_species_results = st.session_state.extraction_results
            chunk_size = st.session_state.verification_species_chunk_size
            species_chunks = [
                all_species_results[i:i + chunk_size]
                for i in range(0, len(all_species_results), chunk_size)
            ]
            
            all_verification_results_flattened = []
            
            progress_bar = st.progress(0, text="Processing verification chunks: 0% complete")
            status_text = st.empty()

            start_time = time.time()
            
            # Using ThreadPoolExecutor for concurrency
            max_workers = st.session_state.concurrent_requests # Reuse general concurrent requests setting

            futures = []
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                for i, chunk in enumerate(species_chunks):
                    futures.append(executor.submit(
                        verifier.verify_species_batch_gemini,
                        chunk,
                        uploaded_file_obj_for_llm, # Pass the File object
                        st.session_state.verification_gemini_model
                    ))
                
                for i, future in enumerate(as_completed(futures)):
                    chunk_res, input_t, output_t = future.result()
                    all_verification_results_flattened.extend(chunk_res)
                    
                    st.session_state.total_verification_input_tokens += input_t
                    st.session_state.total_verification_output_tokens += output_t

                    progress_percent = (i + 1) / len(species_chunks)
                    progress_bar.progress(progress_percent, text=f"Processing verification chunks: {i + 1}/{len(species_chunks)} complete")
                    status_text.text(f"Processed chunk {i+1} for {len(chunk_res)} species.")

            elapsed_time = time.time() - start_time
            st.session_state.automated_verification_results = all_verification_results_flattened
            
            status_text.text(f"✅ Completed verification for {len(all_verification_results_flattened)} species in {elapsed_time:.2f} seconds.")
            progress_bar.progress(1.0, text="Verification complete!")
            st.rerun() # Rerun to display results clearly
            
    elif st.session_state.pdf_buffer is None:
        st.info("Please upload and process a PDF in the '1. Upload PDF' tab first.")
    elif not st.session_state.extraction_results:
        st.info("Please run species extraction in the '4. Run Extraction' tab first to get data for verification.")
    elif not st.session_state.get("uploaded_gemini_file_id"):
        st.info("Please upload the full PDF to Gemini's File Manager above before running verification.")

    if st.session_state.automated_verification_results:
        st.subheader("📊 Verification Results")
        results_df = pd.DataFrame(st.session_state.automated_verification_results)

        # Highlight function for overall_match
        def highlight_overall_match(row):
            if not row['overall_match']:
                return ['background-color: #f8d7da'] * len(row) # Light red for mismatch
            return [''] * len(row) # No highlighting for match

        st.dataframe(results_df.style.apply(highlight_overall_match, axis=1), use_container_width=True)

        st.markdown("""
        **Table Legend:**
        -   Rows highlighted in <span style="background-color: #f8d7da; padding: 2px 5px; border-radius: 3px;">🔴 Light Red</span>: Indicates at least one data field for that species did not match or had an error during verification.
        """, unsafe_allow_html=True)
        
        display_df_and_download(
            results_df,
            "Automated Verification Detailed Results",
            "automated_verification_results"
        )
        
        st.subheader("Summary Statistics")
        col1, col2, col3 = st.columns(3)

        total_verified_species = len(results_df)
        overall_matches_count = results_df['overall_match'].sum()
        overall_mismatches_count = total_verified_species - overall_matches_count

        with col1: st.metric("Total Species Verified", total_verified_species)
        with col2: st.metric("Overall Matches (all fields)", overall_matches_count)
        with col3: st.metric("Overall Mismatches", overall_mismatches_count)

        if total_verified_species > 0:
            match_distribution = pd.DataFrame({
                'Category': ['Overall Match', 'Overall Mismatch'],
                'Count': [overall_matches_count, overall_mismatches_count]
            })
            fig_overall = px.pie(
                match_distribution,
                values='Count',
                names='Category',
                title='Overall Verification Status',
                color_discrete_map={'Overall Match': 'lightgreen', 'Overall Mismatch': 'lightcoral'}
            )
            st.plotly_chart(fig_overall, use_container_width=True)
        else:
            st.info("No species were successfully verified.")

    if st.session_state.get("uploaded_gemini_file_id"):
        st.subheader("🧹 Cleanup Gemini File")
        if st.button(f"🗑️ Delete Full PDF '{st.session_state.uploaded_gemini_file_display_name}' from Gemini"):
            try:
                client = genai.Client(api_key=api_key)
                client.files.delete(st.session_state.uploaded_gemini_file_id)
                st.session_state.uploaded_gemini_file_id = None
                st.session_state.uploaded_gemini_file_display_name = None
                st.success("Full PDF deleted from Gemini successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Error deleting Full PDF from Gemini: {str(e)}")
        st.caption("Note: Uploaded files are automatically deleted from Gemini after 48 hours. Manual deletion is recommended for cost control.")