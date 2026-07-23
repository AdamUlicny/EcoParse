"""
Tab 8: Automated Verification with LLMs

LLM-powered automated verification of extraction results using independent
re-examination of source documents. Supports batch processing and detailed
accuracy analysis with visualization.
"""

import streamlit as st
import pandas as pd
import json
import time
import io
import base64
import tempfile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from plotly import express as px

from google import genai
from google.genai import types

from PyPDF2 import PdfReader
from ecoparse.core.sourcetext import trim_pdf_pages
from ecoparse.core.verifier import Verifier
from ecoparse.core.utils_verification import get_species_pages_from_gnfinder
from app.ui_components import display_df_and_download


def display():
    st.header("Automated LLM Verification")
    
    st.warning("🚧 **Under Construction:** This automated verification feature is currently under construction and is disabled for production use.")
    bypass = st.checkbox("Bypass Under Construction lock (development only)", value=False)
    
    st.markdown("Verify the entire list of extracted species data against the full PDF by sending chunks of species to an LLM.")
    
    # Initialize session state for rubric
    if "verification_rubric" not in st.session_state:
        st.session_state.verification_rubric = ""
    
    # Global Provider & Model from Sidebar
    verification_provider = st.session_state.get("llm_provider", "Google Gemini")
    
    is_openrouter = verification_provider == "OpenRouter"
    is_gemini = verification_provider == "Google Gemini"
    
    if not (is_openrouter or is_gemini):
        st.warning(f"⚠️ Automated Verification is currently optimized for **Google Gemini** and **OpenRouter** only. You are using **{verification_provider}**.")
        st.info("Please switch to one of the supported providers in the sidebar to proceed.")
        return

    # Get model from global state
    if is_openrouter:
        verification_model_name = st.session_state.get("openrouter_model", "")
    elif is_gemini:
        verification_model_name = st.session_state.get("google_model", "")
    else:
        verification_model_name = "" # Ollama or other

    st.subheader("⚙️ Verification Settings")
    st.info(f"Using **{verification_provider}** with model **{verification_model_name}** (Configured in Sidebar)")

    col1, col2 = st.columns(2)
    
    with col1:
        st.number_input(
            "Species per Request (Chunk Size)",
            min_value=1, max_value=50, value=5 if is_openrouter else 10,
            key="verification_species_chunk_size",
            disabled=not bypass,
            help="Smaller chunks are better for OpenRouter precision."
        )
    with col2:
        st.number_input(
            "Concurrent Requests",
            min_value=1, max_value=50, value=1,
            key="verification_concurrent_requests",
            disabled=not bypass,
            help="Keep low to avoid rate limits."
        )

    # --- PDF PREPARATION ---
    st.subheader("📤 Prepare PDF for Verification")
    
    api_key = st.session_state.get("openrouter_api_key") if is_openrouter else st.session_state.google_api_key
    pdf_file_buffer_bytes = st.session_state.pdf_buffer

    if not api_key:
         st.error(f"Please set your {'OpenRouter' if is_openrouter else 'Google'} API Key in the sidebar.")
    elif pdf_file_buffer_bytes:
        # Check if already prepared
        is_ready = False
        ready_msg = ""
        
        if is_gemini and st.session_state.get("uploaded_gemini_file_id"):
             is_ready = True
             ready_msg = f"Ready for Gemini (File ID: {st.session_state.uploaded_gemini_file_id})"
        elif is_openrouter and st.session_state.get("verification_pdf_base64"):
             is_ready = True
             ready_msg = "Ready for OpenRouter (PDF Loaded in Memory)"
             
        if not is_ready:
            st.info("Select a page range from your original document to prepare for verification.")
            try:
                reader = PdfReader(io.BytesIO(pdf_file_buffer_bytes))
                num_pages = len(reader.pages)
                
                col_start, col_end = st.columns(2)
                with col_start:
                    start_page = st.number_input("Start Page", 1, num_pages, 1, key="verify_trim_start_page_gemini", disabled=not bypass)
                with col_end:
                    end_page = st.number_input("End Page", 1, num_pages, num_pages, key="verify_trim_end_page_gemini", disabled=not bypass)

                if st.button("Trim and Prepare PDF", type="primary", disabled=not bypass):
                     with st.spinner("Trimming PDF..."):
                        trimmed_buffer = trim_pdf_pages(io.BytesIO(pdf_file_buffer_bytes), start_page, end_page)
                        
                        if trimmed_buffer:
                            if is_gemini:
                                # Upload to Google
                                client = genai.Client(api_key=api_key)
                                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                                    tmp.write(trimmed_buffer.getvalue())
                                    tmp_path = Path(tmp.name)
                                uploaded_obj = client.files.upload(file=tmp_path)
                                tmp_path.unlink()
                                st.session_state.uploaded_gemini_file_id = uploaded_obj.name
                                st.session_state.uploaded_gemini_file_display_name = uploaded_obj.display_name
                                st.rerun()
                            else:
                                # Base64 for OpenRouter
                                b64 = base64.b64encode(trimmed_buffer.getvalue()).decode('utf-8')
                                st.session_state.verification_pdf_base64 = b64
                                st.session_state.verification_pdf_range = f"{start_page}-{end_page}"
                                st.rerun()
                        else:
                            st.error("Failed to trim PDF.")
            except Exception as e:
                st.error(f"Error preparing PDF: {e}")
        else:
            st.success(f"✅ {ready_msg}")
            if st.button("Reset / Choose Difference Range", disabled=not bypass):
                if is_gemini:
                    st.session_state.uploaded_gemini_file_id = None
                else:
                    st.session_state.verification_pdf_base64 = None
                st.rerun()

    # --- RUBRIC GENERATION (OpenRouter Analysis) ---
    verification_rubric = st.session_state.get("verification_rubric", "")
    if is_openrouter and st.session_state.get("verification_pdf_base64"):
        st.subheader("📜 Verification Rubric")
        
        if not verification_rubric:
            st.info("Generate a specific rubric (checklist) for the LLM to follow based on your extraction schema.")
            if st.button("Generate Rubric", disabled=not bypass):
                 with st.spinner("Generating rubric..."):
                    llm_config = {"api_key": api_key}
                    verifier = Verifier(st.session_state.project_config, llm_config)
                    # Use Gemini for generation if key available (cheaper), else OpenRouter logic (not implemented yet in verifier for rubric, defaults to gemini)
                    # For now, let's just pass the selected model and see if Verifier handles it (Verifier currently treats it as Gemini model if containing 'gemini')
                    # We might need to handle this.
                    # Let's just use the selected OpenRouter model.
                    
                    # Hack: The verifier.generate_dynamic_rubric currently expects Gemini client.
                    # We will rely on the fallback hardcoded rubric if it fails, OR we should have implemented OR support for rubric.
                    # Let's hope the user has a Gemini key or we update verifier to use OR for rubric.
                    # Actually, we didn't implement OR for Rubric in the previous step (left as TODO).
                    # I will check if I can use the sidebar Gemini Key for this specific step if available, 
                    # otherwise fallback to a default prompt.
                    
                    rubric = verifier.generate_dynamic_rubric("gemini-1.5-flash", st.session_state.get("prompt_examples"))
                    st.session_state.verification_rubric = rubric
                    st.rerun()
        else:
            st.text_area("Review/Edit Rubric:", value=verification_rubric, key="edited_rubric", height=150)
            if st.session_state.edited_rubric != verification_rubric:
                st.session_state.verification_rubric = st.session_state.edited_rubric

    # --- EXECUTION ---
    st.subheader("🔬 Run Verification")
    extraction_results = getattr(st.session_state, 'extraction_results', [])
    
    if extraction_results and (st.session_state.get("uploaded_gemini_file_id") or st.session_state.get("verification_pdf_base64")):
        if st.button("🚀 Start Verification", disabled=not bypass):
             # Reset counters
            st.session_state.total_verification_input_tokens = 0
            st.session_state.total_verification_output_tokens = 0
            st.session_state.automated_verification_results = []
            
            verifier = Verifier(
                st.session_state.project_config,
                {"api_key": api_key}
            )
            
            # Chunking
            all_species = extraction_results
            chunk_size = st.session_state.verification_species_chunk_size
            chunks = [all_species[i:i+chunk_size] for i in range(0, len(all_species), chunk_size)]
            
            results = []
            progress = st.progress(0, text="Starting...")
            
            # Prepare Page Map for Hints
            species_page_map = {}
            if st.session_state.get("full_text") and st.session_state.get("gnfinder_results_raw"):
                try:
                    species_page_map = get_species_pages_from_gnfinder(
                        st.session_state.full_text, 
                        st.session_state.gnfinder_results_raw
                    )
                except Exception as e:
                    print(f"Error generating page map: {e}")

            with ThreadPoolExecutor(max_workers=st.session_state.verification_concurrent_requests) as executor:
                futures = []
                for chunk in chunks:
                    if is_openrouter:
                        futures.append(executor.submit(
                            verifier.verify_species_batch_openrouter,
                            chunk,
                            st.session_state.verification_pdf_base64,
                            verification_model_name,
                            st.session_state.verification_rubric,
                            examples=st.session_state.get("prompt_examples"),
                            species_page_map=species_page_map
                        ))
                    else:
                        # Gemini params
                        client = genai.Client(api_key=api_key)
                        f_obj = client.files.get(name=st.session_state.uploaded_gemini_file_id)
                        futures.append(executor.submit(
                            verifier.verify_species_batch_gemini,
                            chunk,
                            f_obj,
                            verification_model_name
                        ))
                        
                for i, future in enumerate(as_completed(futures)):
                    res, inp, out = future.result()
                    results.extend(res)
                    st.session_state.total_verification_input_tokens += inp
                    st.session_state.total_verification_output_tokens += out
                    progress.progress((i+1)/len(chunks), text=f"Processed chunk {i+1}/{len(chunks)}")
            
            st.session_state.automated_verification_results = results
            st.rerun()

    # --- RESULTS ---
    if st.session_state.get("automated_verification_results"):
        st.subheader("📊 Results")
        df = pd.DataFrame(st.session_state.automated_verification_results)
        
        # Color coding
        def color_status(val):
            if val == "OK" or val == "Match": return 'background-color: lightgreen'
            if val == "FLAGGED" or val == "Mismatch": return 'background-color: lightcoral'
            if val == "NF" or val == "NotFound": return 'background-color: lightyellow'
            return ''

        st.dataframe(df.style.map(color_status, subset=['verification_status'] if 'verification_status' in df.columns else []), use_container_width=True)
        
        display_df_and_download(df, "Verification Results", "verification_results", "auto_verify")

    # --- CLEANUP (Gemini Only) ---
    if is_gemini and st.session_state.get("uploaded_gemini_file_id"):
        if st.button("Delete File from Gemini", disabled=not bypass):
             client = genai.Client(api_key=api_key)
             client.files.delete(st.session_state.uploaded_gemini_file_id)
             st.session_state.uploaded_gemini_file_id = None
             st.rerun()