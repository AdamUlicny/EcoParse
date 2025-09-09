"""
Tab 6: Manual Verification Interface

Interactive interface for human verification of extraction results with
document context viewing and species-by-species validation workflow.
"""

import streamlit as st
import pandas as pd
from ecoparse.core.sourcetext import get_species_page_images
from app.ui_components import display_df_and_download
import io

def display():
    """Main display function for manual verification tab."""
    st.header("6. Manual Verification")

    # Validate extraction results exist
    extraction_results = getattr(st.session_state, 'extraction_results', [])
    if not extraction_results:
        st.info("No extraction results to verify. Please run an extraction in Tab 4 or load a report in Tab 1.")
        return

    # Reconstruct species DataFrame if missing (e.g., from loaded session)
    species_df_final = getattr(st.session_state, 'species_df_final', pd.DataFrame())
    if species_df_final.empty and extraction_results:
        st.info("Reconstructing species list from loaded results for context viewer...")
        species_names = [res.get('species') for res in extraction_results if res.get('species')]
        st.session_state.species_df_final = pd.DataFrame(species_names, columns=["Name"])

    # --- END OF DEFINITIVE FIX ---

    # Initialize the verification queue from extraction results if it's empty
    verification_queue = getattr(st.session_state, 'verification_queue', [])
    if extraction_results and not verification_queue:
        st.session_state.verification_queue = extraction_results.copy()
        st.session_state.verification_current_index = 0
        st.session_state.manual_verification_results = []

    total_items = len(st.session_state.verification_queue)
    index = st.session_state.verification_current_index

    if index >= total_items:
        st.success("All items have been verified!")
        st.balloons()
        if st.session_state.manual_verification_results:
            final_df = pd.DataFrame(st.session_state.manual_verification_results)
            display_df_and_download(
                final_df, 
                "Manually Verified Results", 
                "manual_verification_results",
                context="manual_verify_main"
            )
        return


    st.progress((index + 1) / total_items, text=f"Verifying item {index + 1} of {total_items}")
    
    current_item = st.session_state.verification_queue[index]
    species_name = current_item.get('species', 'N/A')
    
    st.subheader(f"Species: `{species_name}`")
    
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("**Page Context**")
        with st.container(height=500, border=False):
            if st.session_state.pdf_buffer:
                images = get_species_page_images(
                    io.BytesIO(st.session_state.pdf_buffer),
                    st.session_state.species_df_final[st.session_state.species_df_final["Name"] == species_name]
                ).get(species_name, [])
                if images:
                    for img in images:
                        st.image(img, use_container_width=True)
                else:
                    st.warning("No context image found for this species.")
            else:
                st.info("Upload the original PDF document in the '1. Upload PDF' tab to view page context images here.")


    with col2:
        st.markdown("**Extracted Data**")
        
        edited_data = {}
        
        for field, value in current_item.get('data', {}).items():
            field_config = next((f for f in st.session_state.project_config.get('data_fields', []) if f['name'] == field), None)
            
            if field_config and field_config.get('validation_values'):
                options = field_config['validation_values']
                try:
                    current_index = options.index(value)
                except (ValueError, TypeError):
                    current_index = 0
                edited_data[field] = st.selectbox(
                    label=f"**{field.replace('_', ' ').title()}**",
                    options=options,
                    index=current_index,
                    key=f"verify_{index}_{field}"
                )
            else:
                edited_data[field] = st.text_input(
                    label=f"**{field.replace('_', ' ').title()}**",
                    value=value,
                    key=f"verify_{index}_{field}"
                )

        edited_notes = st.text_area(
            "Notes", 
            value=current_item.get('notes', ''),
            key=f"verify_{index}_notes"
        )

    st.markdown("---")
    nav_cols = st.columns(6)
    
    if nav_cols[0].button("⬅️ Back", disabled=index == 0):
        st.session_state.verification_current_index -= 1
        st.rerun()

    if nav_cols[1].button("✅ Confirm", type="primary", use_container_width=True):
        result_to_save = {
            "species": species_name,
            "data": edited_data,
            "notes": edited_notes,
            "status": "Verified"
        }
        if index < len(st.session_state.manual_verification_results):
            st.session_state.manual_verification_results[index] = result_to_save
        else:
            st.session_state.manual_verification_results.append(result_to_save)
        
        st.session_state.verification_current_index += 1
        st.rerun()

    if nav_cols[2].button("⏩ Skip", use_container_width=True):
        result_to_save = {**current_item, "status": "Skipped"}
        if index < len(st.session_state.manual_verification_results):
            st.session_state.manual_verification_results[index] = result_to_save
        else:
            st.session_state.manual_verification_results.append(result_to_save)
            
        st.session_state.verification_current_index += 1
        st.rerun()