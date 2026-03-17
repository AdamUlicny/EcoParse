"""
EcoParse Main Application Entry Point

Streamlit-based web interface for species data extraction from PDF documents.
Provides a tabbed workflow interface guiding users through the complete
extraction pipeline from document upload to results analysis.
"""
      
import sys
from pathlib import Path
# Add project root to Python path for module imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import streamlit as st
from app.session import initialize_session
from app.ui_components import setup_sidebar
from app.tabs import (
    t1_upload_pdf_tab,
    t2_species_id_tab,
    t3_configure_extraction_tab,
    t4_run_extraction_tab,
    t5_results_tab,
    t6_manual_verification_tab,
    t7_reports_tab,
    t8_automated_verification_tab,
)

# Configure Streamlit page settings
st.set_page_config(page_title="EcoParse", page_icon="🦎", layout="wide")
initialize_session()

st.title("EcoParse")
st.markdown("A configurable tool for extracting species-level data from documents.")

# Setup global configuration sidebar
with st.sidebar:
    setup_sidebar()

# Create tabbed workflow interface
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "1. Upload PDF",
    "2. Identify Species", 
    "3. Configure Extraction",
    "4. Run Extraction",
    "5. View Results",
    "6. Manual Verification",
    "7. Automated Verification",  
    "8. Reports" 
])

# Display each workflow tab
with tab1: t1_upload_pdf_tab.display()
with tab2: t2_species_id_tab.display()
with tab3: t3_configure_extraction_tab.display()
with tab4: t4_run_extraction_tab.display()
with tab5: t5_results_tab.display()
with tab6: t6_manual_verification_tab.display()
with tab7: t8_automated_verification_tab.display()
with tab8: t7_reports_tab.display()

    