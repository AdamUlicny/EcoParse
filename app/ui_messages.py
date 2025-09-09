"""
Common UI message utilities for streamlined interface consistency.
"""

import streamlit as st

# Status message helpers
def show_loaded_session_complete(step_name: str):
    """Show standard completion message for loaded sessions."""
    st.success(f"✅ {step_name} completed in loaded session.")

def show_prerequisite_warning(step_required: str):
    """Show standard prerequisite warning.""" 
    st.warning(f"Complete '{step_required}' step first.")

def show_extraction_status(completed: int, total: int, is_paused: bool = False):
    """Show extraction progress status."""
    status = "⏸️ Paused" if is_paused else "🔄 In progress"
    st.info(f"{status}: {completed}/{total} species completed")

def show_method_change_success(method: str, char_count: int):
    """Show text extraction method change success."""
    st.success(f"✅ Text re-extracted using **{method}** method ({char_count:,} characters)")

def show_species_chunks_found(count: int, species: str):
    """Show species chunk discovery success."""
    st.success(f"✅ Found **{count}** context chunk(s) for '{species}'")

def show_no_chunks_error():
    """Show no chunks found error with solutions."""
    st.error("❌ No text chunk found with current settings.")
    st.markdown("""
    **Solutions:**
    - Increase context window size
    - Try different text extraction method
    - Check species name spelling
    """)

# Common extraction method help text
EXTRACTION_METHOD_HELP = """
- **Standard**: Basic PyMuPDF extraction (fast, works with most PDFs) - **DEFAULT**
- **Adaptive**: Intelligent column detection with PyMuPDF (best for multi-column documents)
- **Plumber**: Advanced PDFplumber extraction - best for tables/forms (comprehensive but slower)
- **Reading-order**: PyPDF2 reading order extraction - respects logical document flow and header positioning
"""
