import streamlit as st
import pandas as pd
import plotly.express as px
from app.ui_components import display_df_and_download

def display():
    st.header("5. View Results")

    # This is the single source of truth. If there are no results, exit early.
    if not st.session_state.extraction_results:
        st.info("No extraction has been run or loaded yet. Please run an extraction in Tab 4 or load a report in Tab 1.")
        return

    # --- START OF DEFINITIVE FIX ---
    # This block is now the first thing that runs if results exist.
    # It robustly converts the list of dictionaries into a clean DataFrame.

    # 1. Flatten the nested dictionary into a list of flat dictionaries.
    flat_results = []
    for res in st.session_state.extraction_results:
        row = {'species': res.get('species'), 'notes': res.get('notes')}
        # Unpack the 'data' dictionary into top-level columns
        if isinstance(res.get('data'), dict):
            row.update(res['data'])
        flat_results.append(row)
    
    # 2. Create the DataFrame from the flattened list.
    results_df = pd.DataFrame(flat_results)
    
    # 3. Ensure all columns defined in the project config exist, even if the LLM missed them.
    defined_fields = [field['name'] for field in st.session_state.project_config.get('data_fields', [])]
    for field in defined_fields:
        if field not in results_df.columns:
            results_df[field] = "NF" # Default to "Not Found"

    # 4. Reorder columns for a clean presentation: species, data fields, then notes.
    # We filter the list to only include columns that actually exist in the DataFrame.
    existing_cols_in_order = ['species'] + [col for col in defined_fields if col in results_df.columns] + ['notes']
    results_df = results_df[existing_cols_in_order]

    # --- END OF DEFINITIVE FIX ---

    # Now, we use the guaranteed DataFrame for all downstream UI elements.
    # It doesn't matter if the data came from a live run or a loaded report.
    if st.session_state.session_loaded_from_report:
        st.success("✅ Displaying results from the loaded session report.")
    
    display_df_and_download(
        results_df, 
        "Detailed Extraction Results", 
        "ecoparse_results",
        context="results_main"
    )

    st.subheader("Results Analysis")
    
    if defined_fields:
        # Allow user to select a data field to visualize from the config.
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