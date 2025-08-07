import streamlit as st
import pandas as pd
import plotly.express as px
from app.ui_components import display_df_and_download

def display():
    st.header("Extraction Results")

    if not st.session_state.extraction_results:
        st.info("No extraction has been run yet.")
        return

    # Normalize the nested dictionary into a flat DataFrame
    flat_results = []
    for res in st.session_state.extraction_results:
        row = {'species': res.get('species'), 'notes': res.get('notes')}
        # Unpack the 'data' dictionary into top-level columns
        if isinstance(res.get('data'), dict):
            row.update(res['data'])
        flat_results.append(row)
    
    results_df = pd.DataFrame(flat_results)
    
    # Ensure all defined fields are columns, even if none were found
    defined_fields = [field['name'] for field in st.session_state.project_config.get('data_fields', [])]
    for field in defined_fields:
        if field not in results_df.columns:
            results_df[field] = "NF" # Not Found

    # Reorder columns to have species, then defined fields, then notes
    column_order = ['species'] + defined_fields + ['notes']
    results_df = results_df[column_order]

    display_df_and_download(results_df, "Detailed Extraction Results", "ecoparse_results")

    st.subheader("Results Analysis")
    
    # Allow user to select a data field to visualize
    if defined_fields:
        field_to_analyze = st.selectbox(
            "Select data field to visualize:",
            options=defined_fields
        )

        if field_to_analyze in results_df.columns:
            st.write(f"### Distribution for '{field_to_analyze}'")
            counts = results_df[field_to_analyze].value_counts().reset_index()
            counts.columns = [field_to_analyze, 'count']
            
            fig = px.bar(
                counts,
                x=field_to_analyze,
                y='count',
                title=f"Distribution of '{field_to_analyze}'",
                color=field_to_analyze
            )
            st.plotly_chart(fig, use_container_width=True)