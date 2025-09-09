"""
Chunk preview utilities for extraction tab.
"""

import streamlit as st
from ecoparse.core.sourcetext import get_species_context_chunks, get_species_full_page_chunks, get_species_partial_page_chunks
from app.ui_messages import show_species_chunks_found, show_no_chunks_error

def show_chunking_method_selector():
    """Display chunking method selection."""
    st.subheader("Chunking Method")
    
    method = st.radio(
        "How to select text chunks for species extraction:",
        ["Context Window", "Full Page", "Partial Page (Top + Bottom)"],
        help="""
        • **Context Window**: Extract text around each species mention (customizable before/after window)
        • **Full Page**: Extract complete page content where species are mentioned (maximum context)
        • **Partial Page**: Extract top and bottom portions of pages with species mentions (skip middle body text)
        """,
        key="chunking_method"
    )
    
    # Show configuration for Partial Page method
    if method == "Partial Page (Top + Bottom)":
        st.subheader("📐 Partial Page Configuration")
        col1, col2 = st.columns(2)
        
        with col1:
            chars_from_top = st.number_input(
                "Characters from Top",
                min_value=100,
                max_value=2000,
                value=500,
                step=100,
                key="chars_from_top",
                help="Number of characters to extract from the beginning of each page"
            )
        
        with col2:
            chars_from_bottom = st.number_input(
                "Characters from Bottom", 
                min_value=100,
                max_value=2000,
                value=500,
                step=100,
                key="chars_from_bottom",
                help="Number of characters to extract from the end of each page"
            )
        
        return method, chars_from_top, chars_from_bottom
    
    return method, None, None

def show_chunk_preview(species_name: str, chunks: list, chunking_method: str = "Context Window", chars_from_top: int = None, chars_from_bottom: int = None):
    """Display preview of text chunks for a species."""
    if not chunks:
        show_no_chunks_error()
        return
        
    if chunking_method == "Full Page":
        st.success(f"📄 Using **Full Page** extraction for '{species_name}' (complete page context)")
    elif chunking_method == "Partial Page (Top + Bottom)":
        st.success(f"📑 Using **Partial Page** extraction for '{species_name}' (top {chars_from_top} + bottom {chars_from_bottom} chars)")
    
    show_species_chunks_found(len(chunks), species_name)
    
    for i, chunk in enumerate(chunks):
        if chunking_method == "Full Page":
            # Extract page number from chunk if it starts with page marker
            page_marker = chunk.split('\n')[0] if chunk.startswith('=== PAGE') else f"Page {i+1}"
            st.markdown(f"**{page_marker} - Full Content**")
        elif chunking_method == "Partial Page (Top + Bottom)":
            # Extract page number from partial chunk
            page_marker = chunk.split('\n')[0] if chunk.startswith('=== PAGE') else f"Page {i+1}"
            st.markdown(f"**{page_marker}**")
        else:
            st.markdown(f"**Chunk {i+1}/{len(chunks)}**")
        
        # Stats
        col1, col2, col3 = st.columns(3)
        col1.metric("Characters", len(chunk))
        col2.metric("Words", len(chunk.split()))
        col3.metric("Lines", chunk.count('\n') + 1)
        
        # For page-based methods, show species mention count
        if chunking_method in ["Full Page", "Partial Page (Top + Bottom)"]:
            mentions = chunk.lower().count(species_name.lower())
            col1, col2 = st.columns(2)
            col1.metric("Species Mentions", mentions)
            if mentions > 0:
                col2.success(f"✅ '{species_name}' found {mentions} times")
        
        # Content display
        display_chunk = chunk
        height = 250
        
        # Truncate very long content for display
        if len(chunk) > 4000:
            if chunking_method == "Partial Page (Top + Bottom)":
                # For partial pages, show more since they're already truncated
                display_chunk = chunk[:2000] + "\n\n... [Display truncated - full content will be sent to LLM] ...\n\n" + chunk[-2000:]
                st.info("📝 Showing truncated view. Full partial page content will be used for extraction.")
            else:
                display_chunk = chunk[:1500] + "\n\n... [Content truncated for display - full content will be sent to LLM] ...\n\n" + chunk[-1500:]
                st.info("📝 Showing first/last 1500 characters. Full content will be used for extraction.")
            height = 300
        
        st.text_area(f"Content {i+1}", display_chunk, height=height, key=f"chunk_{species_name}_{i}_{chunking_method}_{chars_from_top}_{chars_from_bottom}")
        
        # Species mention check
        if species_name.lower() in chunk.lower():
            st.success("✅ Species name found")
        else:
            st.warning("⚠️ Species name not visible in displayed content")
        
        if i < len(chunks) - 1:
            st.markdown("---")

def generate_chunk_summary(species_list: list, full_text: str, context_before: int, context_after: int, chunking_method: str = "Context Window", chars_from_top: int = None, chars_from_bottom: int = None):
    """Generate summary of chunk availability for all species."""
    st.subheader("Chunk Generation Summary")
    
    if chunking_method == "Full Page":
        # Full page analysis
        all_chunks = get_species_full_page_chunks(full_text, st.session_state.species_df_final)
        
        with_chunks = [s for s in species_list if s in all_chunks and all_chunks[s]]
        without_chunks = [s for s in species_list if s not in with_chunks]
        
        if with_chunks:
            st.success(f"✅ **{len(with_chunks)} species** found on document pages")
            with st.expander("Species with full page chunks"):
                for species in with_chunks:
                    page_count = len(all_chunks[species])
                    st.write(f"• {species} → {page_count} page(s)")
        
        if without_chunks:
            st.warning(f"⚠️ **{len(without_chunks)} species** not found on any page")
            with st.expander("Species not found"):
                st.write(", ".join(without_chunks))
            st.info("💡 These species may need context-based method or check spelling.")
    
    elif chunking_method == "Partial Page (Top + Bottom)":
        # Partial page analysis
        all_chunks = get_species_partial_page_chunks(
            full_text, 
            st.session_state.species_df_final, 
            chars_from_top or 500, 
            chars_from_bottom or 500
        )
        
        with_chunks = [s for s in species_list if s in all_chunks and all_chunks[s]]
        without_chunks = [s for s in species_list if s not in with_chunks]
        
        if with_chunks:
            st.success(f"✅ **{len(with_chunks)} species** found on document pages")
            with st.expander("Species with partial page chunks"):
                for species in with_chunks:
                    page_count = len(all_chunks[species])
                    st.write(f"• {species} → {page_count} page(s) (top {chars_from_top} + bottom {chars_from_bottom} chars each)")
        
        if without_chunks:
            st.warning(f"⚠️ **{len(without_chunks)} species** not found on any page")
            with st.expander("Species not found"):
                st.write(", ".join(without_chunks))
            st.info("💡 These species may need context-based method or check spelling.")
    
    else:
        # Context-based analysis (original method)
        all_chunks = get_species_context_chunks(full_text, st.session_state.species_df_final, context_before, context_after)
        
        with_chunks = [s for s in species_list if s in all_chunks and all_chunks[s]]
        without_chunks = [s for s in species_list if s not in with_chunks]
        
        if with_chunks:
            st.success(f"✅ **{len(with_chunks)} species** have context chunks")
            with st.expander("Species with chunks"):
                st.write(", ".join(with_chunks))
        
        if without_chunks:
            st.error(f"❌ **{len(without_chunks)} species** lack context chunks")
            with st.expander("Species without chunks"):
                st.write(", ".join(without_chunks))
            st.markdown("**Solutions:** Increase context window, try different extraction method, check spelling")
