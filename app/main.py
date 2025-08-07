import sys
from pathlib import Path
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
    t7_reports_tab
)

st.set_page_config(page_title="EcoParse", page_icon="🦎", layout="wide")
initialize_session()

st.title("EcoParse 🦎")
# ...

with st.sidebar:
    setup_sidebar()

# Add the new tab title
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "1. Upload PDF",
    "2. Identify Species",
    "3. Configure Extraction",
    "4. Run Extraction",
    "5. View Results",
    "6. Manual Verification",
    "7. Reports"
])

with tab1: t1_upload_pdf_tab.display()
with tab2: t2_species_id_tab.display()
with tab3: t3_configure_extraction_tab.display()
with tab4: t4_run_extraction_tab.display()
with tab5: t5_results_tab.display()
with tab6: t6_manual_verification_tab.display()
with tab7: t7_reports_tab.display() # Add the new tab display