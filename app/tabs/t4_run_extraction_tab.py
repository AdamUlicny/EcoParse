"""
Tab 4: Extraction Execution

Orchestrates the LLM-based data extraction process, including context preparation,
concurrent processing, progress tracking, and automatic report generation.
"""

import streamlit as st
import pandas as pd
from ecoparse.core.extractor import Extractor
from ecoparse.core.sourcetext import get_species_context_chunks, extract_text_from_pdf
from ecoparse.core.reporter import generate_report
from app.ui_components import display_df_and_download 
import io
import time
import json

def display():
    """Main display function for extraction execution tab."""
    st.header("4. Run Data Extraction")

    if st.session_state.session_loaded_from_report:
        # Show completion status for loaded sessions
        st.success("✅ This step was completed in the loaded session.")
        st.info("The extraction has already been run. You can view the results in the 'View Results' tab or start a new session.")

        st.subheader("Species Processed in Loaded Report")
        display_df_and_download(
            st.session_state.species_df_final,
            "Final Species List",
            "final_species_list",
            context="run_extraction_loaded" 
        )
        return

    if st.session_state.species_df_final.empty:
        st.warning("No species identified. Please complete the '2. Identify Species' step.")
        return

    st.info(f"Ready to extract data for **{len(st.session_state.species_df_final)}** species.")
    
    st.subheader("Extraction Settings")
    col1, col2 = st.columns(2)
    with col1:
        st.selectbox("Extraction Method", ["Text-based", "Image-based"], key="extraction_method")
    with col2:
        st.number_input("Max Concurrent LLM Requests", 1, 50, key="concurrent_requests")

    if st.session_state.extraction_method == "Text-based":
        col3, col4 = st.columns(2)
        with col3:
            st.number_input("Characters Before Mention", 0, 2000, key="context_before")
        with col4:
            st.number_input("Characters After Mention", 0, 2000, key="context_after")

        # Text extraction method override section
        st.subheader("Text Extraction Method")
        
        current_method = getattr(st.session_state, 'extraction_method_used', 'adaptive')
        st.info(f"📄 Current text was extracted using: **{current_method}** method")
        
        col_method, col_reextract = st.columns([2, 1])
        with col_method:
            new_extraction_method = st.selectbox(
                "Change extraction method if needed",
                ["standard", "adaptive", "plumber"],
                index=["standard", "adaptive", "plumber"].index(current_method) if current_method in ["standard", "adaptive", "plumber"] else 1,  # Default to adaptive
                key="text_extraction_override",
                help="""
                Change this if you're missing species information in context chunks:
                - **Standard**: Basic extraction, fastest, good for simple single-column layouts
                - **Adaptive**: Intelligent column detection - automatically analyzes layout and extracts columns optimally (recommended)
                - **Plumber**: Advanced extraction with table detection - best for complex structured documents, forms, and tables (comprehensive but slower)
                """
            )
        
        with col_reextract:
            st.markdown("<br>", unsafe_allow_html=True)  # Align button
            if st.button("🔄 Re-extract Text", help="Re-extract text using the selected method"):
                if new_extraction_method != current_method:
                    with st.spinner(f"Re-extracting text using {new_extraction_method} method..."):
                        pdf_buffer = io.BytesIO(st.session_state.pdf_buffer)
                        st.session_state.full_text = extract_text_from_pdf(pdf_buffer, method=new_extraction_method)
                        st.session_state.extraction_method_used = new_extraction_method
                        st.success(f"✅ Text re-extracted using **{new_extraction_method}** method ({len(st.session_state.full_text):,} characters)")
                        st.rerun()
                else:
                    st.info("Selected method is the same as current method.")

        with st.expander("Preview Text Chunk", expanded=True):
            st.markdown("Preview the context chunks that will be sent to the LLM for data extraction.")
            
            species_list = st.session_state.species_df_final["Name"].tolist()
            if species_list:
                col_species, col_settings = st.columns([2, 1])
                
                with col_species:
                    species_to_preview = st.selectbox(
                        "Select species to preview", 
                        options=species_list,
                        key="preview_species_select"
                    )
                
                with col_settings:
                    st.markdown("**Context Settings**")
                    st.caption(f"Before: {st.session_state.context_before} chars")
                    st.caption(f"After: {st.session_state.context_after} chars")
                    st.caption(f"Method: {getattr(st.session_state, 'extraction_method_used', 'standard')}")
                
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    generate_single = st.button("Generate Preview", type="primary")
                with col_btn2:
                    generate_all = st.button("Quick Test All Species", help="Check if all species have context chunks")
                
                if generate_single:
                    with st.spinner("Generating chunk..."):
                        # Filter species dataframe for the selected species
                        species_filter = st.session_state.species_df_final["Name"] == species_to_preview
                        filtered_df = st.session_state.species_df_final[species_filter]
                        
                        chunks = get_species_context_chunks(
                            st.session_state.full_text,
                            filtered_df,
                            st.session_state.context_before,
                            st.session_state.context_after
                        ).get(species_to_preview, [])
                        
                        if chunks:
                            st.success(f"✅ Found **{len(chunks)}** context chunk(s) for '{species_to_preview}'")
                            
                            for i, chunk in enumerate(chunks):
                                st.markdown(f"**Chunk {i+1} of {len(chunks)}**")
                                
                                # Show chunk statistics
                                col_stats1, col_stats2, col_stats3 = st.columns(3)
                                with col_stats1:
                                    st.metric("Characters", len(chunk))
                                with col_stats2:
                                    st.metric("Words", len(chunk.split()))
                                with col_stats3:
                                    st.metric("Lines", chunk.count('\n') + 1)
                                
                                # Show the actual chunk
                                st.text_area(
                                    f"Chunk {i+1} Content", 
                                    chunk, 
                                    height=200,
                                    key=f"chunk_preview_{i}",
                                    help="This is the exact text that will be sent to the LLM"
                                )
                                
                                # Highlight species mention in chunk
                                if species_to_preview.lower() in chunk.lower():
                                    st.success("✅ Species name found in chunk")
                                else:
                                    st.warning("⚠️ Species name not clearly visible in chunk")
                                
                                if i < len(chunks) - 1:
                                    st.markdown("---")
                        else:
                            st.error("❌ No text chunk found for this species with current settings.")
                            st.markdown("**Possible solutions:**")
                            st.markdown("- Increase context window size (characters before/after)")
                            st.markdown("- Try a different text extraction method above")
                            st.markdown("- Check if the species name is correctly spelled")
                
                if generate_all:
                    with st.spinner("Testing chunk generation for all species..."):
                        all_chunks = get_species_context_chunks(
                            st.session_state.full_text,
                            st.session_state.species_df_final,
                            st.session_state.context_before,
                            st.session_state.context_after
                        )
                        
                        st.subheader("Chunk Generation Summary")
                        
                        species_with_chunks = []
                        species_without_chunks = []
                        
                        for species in species_list:
                            if species in all_chunks and all_chunks[species]:
                                species_with_chunks.append(species)
                            else:
                                species_without_chunks.append(species)
                        
                        # Summary metrics
                        col_summary1, col_summary2, col_summary3 = st.columns(3)
                        with col_summary1:
                            st.metric("Total Species", len(species_list))
                        with col_summary2:
                            st.metric("With Chunks", len(species_with_chunks))
                        with col_summary3:
                            st.metric("Without Chunks", len(species_without_chunks))
                        
                        # Detailed results
                        if species_with_chunks:
                            st.success(f"✅ **{len(species_with_chunks)} species** have context chunks:")
                            for species in species_with_chunks:
                                chunk_count = len(all_chunks.get(species, []))
                                st.write(f"• {species} ({chunk_count} chunk{'s' if chunk_count != 1 else ''})")
                        
                        if species_without_chunks:
                            st.error(f"❌ **{len(species_without_chunks)} species** have no context chunks:")
                            for species in species_without_chunks:
                                st.write(f"• {species}")
                            
                            st.markdown("**Recommendations for missing chunks:**")
                            st.markdown("- Try increasing context window size")
                            st.markdown("- Try the 'adaptive' extraction method above for better column handling")
                            st.markdown("- Check if species names are spelled correctly in the document")
            else:
                st.info("No species available to preview. Complete step 2 first.")

    if st.button("Start Extraction", type="primary", disabled=st.session_state.species_df_final.empty):
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
            "text_extraction_method": getattr(st.session_state, 'extraction_method_used', 'adaptive'),
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