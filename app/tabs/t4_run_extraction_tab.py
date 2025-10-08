"""
Tab 4: Extraction Execution

Orchestrates LLM-based data extraction with progress tracking and report generation.
"""

import streamlit as st
import pandas as pd
from ecoparse.core.extractor import Extractor
from ecoparse.core.sourcetext import get_species_context_chunks, extract_text_from_pdf
from ecoparse.core.reporter import generate_report
from app.ui_components import display_df_and_download
from app.ui_messages import (
    show_loaded_session_complete, show_prerequisite_warning, show_extraction_status,
    show_method_change_success, show_species_chunks_found, show_no_chunks_error
)
from app.ui_helpers import create_extraction_method_selector, create_context_controls, preload_highlighted_images
from app.chunk_preview import show_chunk_preview, generate_chunk_summary, show_chunking_method_selector
import io
import time
import json
import json

def display():
    """Main display function for extraction execution tab."""
    st.header("4. Run Data Extraction")

    if st.session_state.session_loaded_from_report:
        show_loaded_session_complete("Extraction")
        st.info("View results in 'View Results' tab or start new session.")
        st.subheader("Species Processed")
        display_df_and_download(st.session_state.species_df_final, "Final Species List", "final_species_list", "run_extraction_loaded")
        return

    if st.session_state.species_df_final.empty:
        show_prerequisite_warning("2. Identify Species")
        return

    st.info(f"Ready to extract data for **{len(st.session_state.species_df_final)}** species.")
    
    st.subheader("Extraction Settings")
    col1, col2 = st.columns(2)
    with col1:
        st.selectbox("Extraction Method", ["Text-based", "Image-based"], key="extraction_method")
    with col2:
        st.number_input("Max Concurrent LLM Requests", 1, 50, key="concurrent_requests")

    if st.session_state.extraction_method == "Text-based":
        create_context_controls()

        with st.expander("Preview Text Chunk", expanded=True):
            st.markdown("Preview context chunks sent to LLM.")
            
            # Chunking method selector
            chunking_result = show_chunking_method_selector()
            if len(chunking_result) == 3:
                chunking_method, chars_from_top, chars_from_bottom = chunking_result
            else:
                chunking_method = chunking_result
                chars_from_top, chars_from_bottom = None, None
            
            species_list = st.session_state.species_df_final["Name"].tolist()
            if species_list:
                col_species, col_settings = st.columns([2, 1])
                
                with col_species:
                    species_to_preview = st.selectbox("Select species", species_list, key="preview_species_select")
                
                with col_settings:
                    st.markdown("**Settings**")
                    if chunking_method == "Context Window (default)":
                        st.caption(f"Before: {st.session_state.context_before} chars")
                        st.caption(f"After: {st.session_state.context_after} chars")
                    elif chunking_method == "Full Page":
                        st.caption("Mode: Full page content")
                    else:  # Partial Page
                        st.caption(f"Top: {chars_from_top or 500} chars")
                        st.caption(f"Bottom: {chars_from_bottom or 500} chars")
                    st.caption(f"Method: {getattr(st.session_state, 'extraction_method_used', 'standard')}")
                
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    generate_single = st.button("Generate Preview", type="primary")
                with col_btn2:
                    generate_all = st.button("Test All Species")
                
                if generate_single:
                    with st.spinner("Generating..."):
                        if chunking_method == "Full Page":
                            # Use full page chunking
                            from ecoparse.core.sourcetext import get_species_full_page_chunks
                            chunks = get_species_full_page_chunks(
                                st.session_state.full_text, 
                                st.session_state.species_df_final
                            ).get(species_to_preview, [])
                        elif chunking_method == "Partial Page (Top + Bottom)":
                            # Use partial page chunking
                            from ecoparse.core.sourcetext import get_species_partial_page_chunks
                            chunks = get_species_partial_page_chunks(
                                st.session_state.full_text,
                                st.session_state.species_df_final,
                                chars_from_top or 500,
                                chars_from_bottom or 500
                            ).get(species_to_preview, [])
                        else:
                            # Use context-based chunking (original method)
                            species_filter = st.session_state.species_df_final["Name"] == species_to_preview
                            filtered_df = st.session_state.species_df_final[species_filter]
                            chunks = get_species_context_chunks(
                                st.session_state.full_text, filtered_df,
                                st.session_state.context_before, st.session_state.context_after
                            ).get(species_to_preview, [])
                        
                        show_chunk_preview(species_to_preview, chunks, chunking_method, chars_from_top, chars_from_bottom)
                
                if generate_all:
                    with st.spinner("Testing all species..."):
                        generate_chunk_summary(
                            species_list, 
                            st.session_state.full_text, 
                            st.session_state.context_before, 
                            st.session_state.context_after,
                            chunking_method,
                            chars_from_top,
                            chars_from_bottom
                        )
            else:
                st.info("No species available. Complete step 2 first.")

    # Check if extraction is already running
    extraction_in_progress = getattr(st.session_state, 'extraction_running', False)
    
    # Show simple extraction control panel if extraction is running
    if extraction_in_progress:
        st.markdown("---")
        st.subheader("⚡ Extraction Control")
        
        # Show current status
        progress = getattr(st.session_state, 'extraction_progress', 0)
        total = getattr(st.session_state, 'extraction_total', 0)
        
        st.info(f"🔄 Extraction in progress: {progress}/{total} species completed")
        
        # Simple stop button
        if st.button("⏹️ Stop Extraction", type="secondary"):
            st.session_state.extraction_running = False
            st.warning("Stopping extraction... Partial results will be saved.")
            st.rerun()
    
    if st.button("Start Extraction", type="primary", disabled=st.session_state.species_df_final.empty or extraction_in_progress):
        # Initialize extraction control flags and reset metrics
        st.session_state.extraction_running = True
        st.session_state.extraction_paused = False
        st.session_state.extraction_progress = 0
        st.session_state.extraction_total = len(st.session_state.species_df_final)
        st.session_state.extraction_runtime = 0
        st.session_state.total_input_tokens = 0
        st.session_state.total_output_tokens = 0
        
        # Prepare extraction configuration
        formatted_examples = []
        for ex in st.session_state.prompt_examples:
            output_json_string = json.dumps(ex['output'], indent=2)
            
            example_parts = [
                f"Input:\n{ex['input']}",
                f"Output:\n{output_json_string}"
            ]

            if ex.get('explainer'):
                example_parts.append(f"Explainer:\n{ex['explainer']}")
            
            formatted_examples.append("\n".join(example_parts))

        examples_text = "\n\n---\n\n".join(formatted_examples)
        llm_config = {
            "provider": st.session_state.llm_provider,
            "api_key": st.session_state.google_api_key,
            "model": st.session_state.google_model if st.session_state.llm_provider == "Google Gemini" else st.session_state.ollama_model,
            "ollama_url": st.session_state.ollama_url,
            "concurrent_requests": st.session_state.concurrent_requests
        }
        # Get chunking method and parameters from session state
        chunking_method = getattr(st.session_state, 'chunking_method', 'Context Window')
        chars_from_top = getattr(st.session_state, 'chars_from_top', 500)
        chars_from_bottom = getattr(st.session_state, 'chars_from_bottom', 500)
        
        source_context = {
            "extraction_method": st.session_state.extraction_method,
            "species_df": st.session_state.species_df_final,
            "full_text": st.session_state.full_text,
            "pdf_buffer": io.BytesIO(st.session_state.pdf_buffer),
            "context_before": st.session_state.context_before,
            "context_after": st.session_state.context_after,
            "examples_text": examples_text,
            "chunking_method": chunking_method,
            "chars_from_top": chars_from_top,
            "chars_from_bottom": chars_from_bottom
        }
        
        # Always clear previous results when starting a new extraction
        st.session_state.extraction_results = []
        st.session_state.verification_queue = []
        st.session_state.manual_verification_results = []
        
        extractor = Extractor(st.session_state.project_config, llm_config)
        species_to_process = st.session_state.species_df_final["Name"].tolist()
        
        # Store configuration for potential resume functionality
        st.session_state.species_to_process = species_to_process
        st.session_state.extractor = extractor
        st.session_state.source_context = source_context
        st.session_state.llm_config = llm_config
        
        # Immediately rerun to show control panel
        st.rerun()
    
    # Run extraction automatically if extraction_running is True
    if getattr(st.session_state, 'extraction_running', False):
        # Check if we have the required state for extraction
        if hasattr(st.session_state, 'extractor') and hasattr(st.session_state, 'source_context'):
            progress_bar = st.progress(0, "Starting extraction...")
            status_text = st.empty()
            
            def update_progress(completed, total):
                st.session_state.extraction_progress = completed
                progress_bar.progress(completed / total, f"Processed {completed}/{total} species...")
                status_text.text(f"Progress: {completed}/{total} species completed")
            
            # Start extraction
            with st.spinner("LLM is processing..."):
                try:
                    extractor = st.session_state.extractor
                    source_context = st.session_state.source_context
                    species_to_process = st.session_state.species_to_process
                    
                    # Get list of already completed species for resume functionality
                    completed_species = []
                    if hasattr(st.session_state, 'extraction_results') and st.session_state.extraction_results:
                        completed_species = [result.get('species', '') for result in st.session_state.extraction_results]
                    
                    results, runtime, in_tokens, out_tokens = extractor.run_resumable_extraction(
                        species_to_process, source_context, update_progress, completed_species
                    )
                    
                    # Merge with any existing results
                    if hasattr(st.session_state, 'extraction_results') and st.session_state.extraction_results:
                        # Combine existing and new results
                        all_results = st.session_state.extraction_results + results
                    else:
                        all_results = results
                    
                    # Update session state
                    st.session_state.extraction_results = all_results
                    
                    # Update runtime and token counts (accumulate if resuming)
                    existing_runtime = getattr(st.session_state, 'extraction_runtime', 0)
                    existing_in_tokens = getattr(st.session_state, 'total_input_tokens', 0)
                    existing_out_tokens = getattr(st.session_state, 'total_output_tokens', 0)
                    
                    st.session_state.extraction_runtime = existing_runtime + runtime
                    st.session_state.total_input_tokens = existing_in_tokens + in_tokens
                    st.session_state.total_output_tokens = existing_out_tokens + out_tokens
                    
                    # Create final_results_df from extraction_results for compatibility with verification tab
                    if all_results:
                        flat_results = []
                        for res in all_results:
                            row = {'Species Name': res.get('species'), 'Mentioned In': res.get('notes', '')}
                            if isinstance(res.get('data'), dict):
                                row.update(res['data'])
                            flat_results.append(row)
                        
                        st.session_state.final_results_df = pd.DataFrame(flat_results)
                        
                        # --- Preload highlighted images for verification ---
                        with st.spinner("Pre-loading context images for verification..."):
                            preload_highlighted_images(st.session_state.final_results_df)
                        # ----------------------------------------------------
                    
                    # Check if extraction was completed or stopped
                    extraction_completed = len(all_results) >= len(species_to_process)
                    extraction_stopped = not st.session_state.extraction_running
                    
                    if extraction_completed:
                        # Extraction completed successfully - clear all flags
                        st.session_state.extraction_running = False
                        st.session_state.extraction_paused = False
                        
                        report_context = {
                            "pdf_name": st.session_state.pdf_name,
                            "full_text": st.session_state.full_text,
                            "text_extraction_method": getattr(st.session_state, 'extraction_method_used', 'standard'),
                            "gnfinder_url": st.session_state.gnfinder_url,
                            "gnfinder_results_raw": st.session_state.gnfinder_results_raw,
                            "species_df_initial": st.session_state.species_df_initial,
                            "species_df_final": st.session_state.species_df_final,
                            "extraction_method": st.session_state.extraction_method,
                            "llm_provider": st.session_state.llm_provider,
                            "llm_model": st.session_state.llm_config["model"],
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
                        status_text.empty()
                        st.success(f"Extraction complete! Report saved to `{report_path}`.")
                        st.info("Proceed to the 'View Results' or 'Reports' tab.")
                    
                    elif extraction_stopped and all_results:
                        # Extraction was stopped but we have partial results - save them
                        st.session_state.extraction_running = False
                        st.session_state.extraction_paused = False
                        
                        progress_bar.empty()
                        status_text.empty()
                        st.warning(f"Extraction stopped. Partial results saved ({len(all_results)} species processed).")
                        st.info("Partial results are available in the 'View Results' tab.")
                    
                    elif extraction_stopped:
                        # Extraction was stopped with no results
                        st.session_state.extraction_running = False
                        st.session_state.extraction_paused = False
                        
                        progress_bar.empty()
                        status_text.empty()
                        st.warning("Extraction stopped. No results were generated.")
                    
                except Exception as e:
                    st.session_state.extraction_running = False
                    progress_bar.empty()
                    status_text.empty()
                    st.error(f"Extraction failed: {str(e)}")
            
            st.rerun()  # Refresh to show updated state