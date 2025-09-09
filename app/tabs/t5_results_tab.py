"""
Tab 5: Results Visualization and Analysis

Displays extraction results in tabular and graphical formats with download options.
Provides overview statistics and data distribution analysis.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from app.ui_components import display_df_and_download

def display():
    """Main display function for results viewing tab."""
    st.header("5. View Results")
    
    # Check if extraction results exist
    extraction_results = getattr(st.session_state, 'extraction_results', [])
    if not extraction_results:
        st.info("No extraction has been run or loaded yet. Please run an extraction in Tab 4 or load a report in Tab 1.")
        return
    
    # Flatten extraction results for analysis
    flat_results = []
    for res in extraction_results:
        row = {'species': res.get('species'), 'notes': res.get('notes')}
        if isinstance(res.get('data'), dict):
            row.update(res['data'])
        flat_results.append(row)

    results_df = pd.DataFrame(flat_results)

    # Get configured data fields for analysis
    project_config = getattr(st.session_state, 'project_config', {})
    defined_fields = [field['name'] for field in project_config.get('data_fields', [])]
    for field in defined_fields:
        if field not in results_df.columns:
            results_df[field] = "NF" # Default to "Not Found"

    existing_cols_in_order = ['species'] + [col for col in defined_fields if col in results_df.columns] + ['notes']
    results_df = results_df[existing_cols_in_order]

    session_loaded_from_report = getattr(st.session_state, 'session_loaded_from_report', False)
    if session_loaded_from_report:
        st.success("✅ Displaying results from the loaded session report.")
    
    display_df_and_download(
        results_df, 
        "Detailed Extraction Results", 
        "ecoparse_results",
        context="results_main"
    )

    st.subheader("Results Analysis")
    
    if defined_fields:
        field_to_analyze = st.selectbox(
            "Select data field to visualize:",
            options=defined_fields
        )

        if field_to_analyze and field_to_analyze in results_df.columns:
            st.write(f"### Distribution for '{field_to_analyze}'")
            counts = results_df[field_to_analyze].value_counts().reset_index()
            counts.columns = [field_to_analyze, 'Count']
            
            fig = px.bar(
                counts,
                x=field_to_analyze,
                y='Count',
                title=f"Distribution of '{field_to_analyze}'",
                color=field_to_analyze
            )
            st.plotly_chart(fig, use_container_width=True)