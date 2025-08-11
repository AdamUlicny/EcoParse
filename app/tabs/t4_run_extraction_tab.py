import streamlit as st
import pandas as pd
from ecoparse.core.extractor import Extractor
from ecoparse.core.sourcetext import get_species_context_chunks
from ecoparse.core.reporter import generate_report
import io
import time

def display():
    st.header("Run Data Extraction")

    if st.session_state.species_df_final.empty:
        st.warning("No species identified. Please complete the 'Identify Species' step.")
        return

    st.info(f"Ready to extract data for **{len(st.session_state.species_df_final)}** species.")
    
    st.subheader("Extraction Settings")
    col1, col2 = st.columns(2)
    with col1:
        st.selectbox("Extraction Method", ["Text-based", "Image-based"], key="extraction_method")
    with col2:
        st.number_input("Max Concurrent LLM Requests", 10, 50, key="concurrent_requests")

    if st.session_state.extraction_method == "Text-based":
        col3, col4 = st.columns(2)
        with col3:
            st.number_input("Characters Before Mention", 0, 2000, key="context_before")
        with col4:
            st.number_input("Characters After Mention", 250, 2000, key="context_after")

        with st.expander("Preview Text Chunk"):
            # ... (Chunk preview logic is unchanged)
            species_list = st.session_state.species_df_final["Name"].tolist()
            if species_list:
                species_to_preview = st.selectbox("Select species to preview", options=species_list)
                if st.button("Generate Preview"):
                    with st.spinner("Generating chunk..."):
                        chunks = get_species_context_chunks(
                            st.session_state.full_text,
                            st.session_state.species_df_final[st.session_state.species_df_final["Name"] == species_to_preview],
                            st.session_state.context_before,
                            st.session_state.context_after
                        ).get(species_to_preview, [])
                        
                        if chunks:
                            st.text_area("Generated Chunk", "\n---\n".join(chunks), height=250)
                        else:
                            st.warning("No text chunk found for this species with current settings.")
            else:
                st.info("No species available to preview.")

    if st.button("Start Extraction", type="primary", disabled=st.session_state.species_df_final.empty):
        examples_text = "\n\n".join(
            [f"Input:\n{ex['input']}\nOutput:\n{ex['output']}" for ex in st.session_state.prompt_examples]
        )
        
        llm_config = {
            "provider": st.session_state.llm_provider,
            "api_key": st.session_state.google_api_key,
            "model": st.session_state.google_model if st.session_state.llm_provider == "Google Gemini" else st.session_state.ollama_model,
            "ollama_url": st.session_state.ollama_url, 
            "concurrent_requests": st.session_state.concurrent_requests
        }
        source_context = {
            "extraction_method": st.session_state.extraction_method,
            "species_df": st.session_state.species_df_final,
            "full_text": st.session_state.full_text,
            "pdf_buffer": io.BytesIO(st.session_state.pdf_buffer),
            "context_before": st.session_state.context_before,
            "context_after": st.session_state.context_after,
            "examples_text": examples_text
        }
        
        st.session_state.extraction_results = []
        st.session_state.verification_queue = []
        st.session_state.manual_verification_results = []
        
        extractor = Extractor(st.session_state.project_config, llm_config)
        species_to_process = st.session_state.species_df_final["Name"].tolist()
        
        progress_bar = st.progress(0, "Starting extraction...")
        def update_progress(completed, total):
            progress_bar.progress(completed / total, f"Processed {completed}/{total} species...")

        with st.spinner("LLM is processing..."):
            results, runtime, in_tokens, out_tokens = extractor.run_extraction(
                species_to_process, source_context, update_progress
            )
        
        st.session_state.extraction_results = results
        st.session_state.extraction_runtime = runtime
        st.session_state.total_input_tokens = in_tokens
        st.session_state.total_output_tokens = out_tokens
        
        report_context = {
            "pdf_name": st.session_state.pdf_name,
            "full_text": st.session_state.full_text,
            "gnfinder_url": st.session_state.gnfinder_url,
            "gnfinder_results_raw": st.session_state.gnfinder_results_raw,
            "species_df_initial": st.session_state.species_df_initial,
            "species_df_final": st.session_state.species_df_final,
            "extraction_method": st.session_state.extraction_method,
            "llm_provider": st.session_state.llm_provider,
            "llm_model": llm_config["model"],
            "context_before": source_context["context_before"] if source_context["extraction_method"] == "Text-based" else "N/A",
            "context_after": source_context["context_after"] if source_context["extraction_method"] == "Text-based" else "N/A",
            "prompt_examples": st.session_state.prompt_examples,
            "concurrent_requests": st.session_state.concurrent_requests,
            "extraction_results": st.session_state.extraction_results,
            "extraction_runtime": st.session_state.extraction_runtime,
            "total_input_tokens": st.session_state.total_input_tokens,
            "total_output_tokens": st.session_state.total_output_tokens,
            "project_config": st.session_state.project_config,
            "manual_verification_results": st.session_state.manual_verification_results
        }
        
        report_path = generate_report(report_context)
        
        st.session_state.last_report_path = report_path
        
        progress_bar.empty()
        st.success(f"Extraction complete! Report saved to `{report_path}`.")
        st.info("Proceed to the 'View Results' or 'Reports' tab.")