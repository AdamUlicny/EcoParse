import streamlit as st
from ecoparse.core.finders import (
    send_text_to_gnfinder,
    parse_gnfinder_results,
    filter_initial_species,
    filter_by_taxonomy
)
from app.ui_components import display_df_and_download

def display():
    st.header("Identify Species Names")

    if not st.session_state.full_text:
        st.warning("Please upload and process a PDF in the 'Upload PDF' tab first.")
        return

    if st.button("Find Species with GNfinder", type="primary"):
        with st.spinner("Sending text to GNfinder... This may take a moment."):
            gnfinder_url = st.session_state.gnfinder_url
            results = send_text_to_gnfinder(st.session_state.full_text, gnfinder_url)
            if results:
                st.session_state.gnfinder_results_raw = results
                df_raw = parse_gnfinder_results(results)
                st.session_state.species_df_initial = filter_initial_species(df_raw)
                st.session_state.species_df_final = st.session_state.species_df_initial.copy()
                st.success(f"GNfinder found {len(st.session_state.species_df_initial)} potential species names.")
            else:
                st.error("Failed to get results from GNfinder. Check the URL and ensure the service is running.")

    if not st.session_state.species_df_initial.empty:
        st.subheader("Taxonomic Filtering (Optional)")
        st.markdown("Refine the species list by a higher taxonomic group (e.g., class, order). This uses the [GBIF API](https://www.gbif.org/).")

        col1, col2 = st.columns(2)
        with col1:
            rank = st.selectbox("Taxonomic Rank", ["class", "order", "family", "phylum"])
        with col2:
            name = st.text_input("Taxon Name (e.g., 'Aves' or 'Mammalia')", "Any")

        if st.button("Apply Taxonomic Filter"):
            if name and name.lower() != 'any':
                st.session_state.species_df_final = filter_by_taxonomy(
                    st.session_state.species_df_initial, rank, name
                )
            else:
                # If filter is cleared, reset to the initial list
                st.session_state.species_df_final = st.session_state.species_df_initial.copy()
        
        st.markdown("---")
        display_df_and_download(
            st.session_state.species_df_final,
            "Final Species List for Extraction",
            "final_species_list"
        )
        
        with st.expander("Show initial unfiltered species list"):
            display_df_and_download(
                st.session_state.species_df_initial,
                "Initially Identified Species (Pre-Taxonomic Filter)",
                "initial_species_list"
            )