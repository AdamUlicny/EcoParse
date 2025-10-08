"""
Tab 2: Species Identification

Species name discovery using GNfinder with taxonomic filtering options.
"""

import streamlit as st
import pandas as pd
import os
import glob
import json
from datetime import datetime
from ecoparse.core.finders import (
    send_text_to_gnfinder, 
    parse_gnfinder_results,
    filter_initial_species,
    filter_by_taxonomy,
    filter_by_gbif_verification,
    test_gnfinder_connection
)
from app.ui_components import display_df_and_download
from app.ui_messages import show_loaded_session_complete, show_prerequisite_warning

def display():
    """Main display function for species identification tab."""
    st.header("2. Identify Species Names")

    if st.session_state.session_loaded_from_report:
        show_loaded_session_complete("Species identification")
        st.markdown("Species list used for extraction:")
        display_df_and_download(st.session_state.species_df_final, "Final Species List", "final_species_list", "species_id_loaded")
    elif not st.session_state.get('full_text'):
        show_prerequisite_warning("1. Upload PDF")
    else:
        # New session workflow
        # GNfinder configuration options
        col1, col2 = st.columns([3, 1])
        with col1:
            gnfinder_offline = st.checkbox(
                "Use GNfinder CLI (offline mode)", 
                value=False,
                help="When checked, uses GNfinder command-line interface instead of the web API. "
                     "Equivalent to running 'gnfinder -U filename.txt' directly. "
                     "Useful when the GNfinder web service is down or having issues. "
                     "Results are the same quality, just using a different processing method."
            )
        
        if st.button("Find Species with GNfinder", type="primary"):
            with st.spinner("Sending text to GNfinder... This may take a moment."):
                gnfinder_url = st.session_state.gnfinder_url
                results = send_text_to_gnfinder(st.session_state.full_text, gnfinder_url, offline_mode=gnfinder_offline)
                if results:
                    st.session_state.gnfinder_results_raw = results
                    df_raw = parse_gnfinder_results(results)
                    st.session_state.species_df_initial = filter_initial_species(df_raw)
                    st.session_state.species_df_final = st.session_state.species_df_initial.copy()
                    st.success(f"GNfinder found {len(st.session_state.species_df_initial)} potential species names.")
                else:
                    st.error("Failed to get results from GNfinder. Check the URL and ensure the service is running.")

        # Add "Load Species List from Past Log" functionality
        with st.expander("📂 Load Species List from Past Log", expanded=False):
            log_files = glob.glob("/home/adam/EcoParse/logs/ecoparse_report_*.json")
            log_files.sort(reverse=True)  # Most recent first
            
            if not log_files:
                st.info("No log files found.")
            else:
                # Create a selectbox with formatted log names
                log_options = []
                for log_file in log_files[:20]:  # Show only the 20 most recent
                    filename = os.path.basename(log_file)
                    # Extract timestamp from filename
                    timestamp_str = filename.replace("ecoparse_report_", "").replace(".json", "")
                    try:
                        timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                        formatted_time = timestamp.strftime("%Y-%m-%d %H:%M:%S")
                        log_options.append((log_file, f"{formatted_time} - {filename}"))
                    except ValueError:
                        log_options.append((log_file, filename))
                
                selected_log = st.selectbox(
                    "Choose a log file:",
                    options=[None] + [opt[0] for opt in log_options],
                    format_func=lambda x: "Select a log file..." if x is None else 
                        next(opt[1] for opt in log_options if opt[0] == x),
                    key="species_log_selector"
                )
                
                if selected_log:
                    try:
                        with open(selected_log, 'r') as f:
                            log_data = json.load(f)
                        
                        # Find species list in the log
                        species_list = None
                        if 'gnfinder_info' in log_data and 'final_species_list' in log_data['gnfinder_info']:
                            species_list = log_data['gnfinder_info']['final_species_list']
                        
                        if species_list:
                            st.success(f"Found {len(species_list)} species in the selected log.")
                            
                            # Show preview of species
                            st.markdown("**Preview of species (first 10):**")
                            preview_species = species_list[:10]
                            preview_df = pd.DataFrame(preview_species)
                            if not preview_df.empty:
                                # Show only key columns for preview
                                display_cols = ['Name', 'MatchType']
                                if 'MatchType' in preview_df.columns:
                                    st.dataframe(preview_df[display_cols], use_container_width=True)
                                else:
                                    st.dataframe(preview_df[['Name']], use_container_width=True)
                            
                            if len(species_list) > 10:
                                st.info(f"...and {len(species_list) - 10} more species.")
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("Load Species List", type="primary", key="load_species_list"):
                                    # Convert to DataFrame matching the expected structure
                                    species_df = pd.DataFrame(species_list)
                                    
                                    # Set the session state variables
                                    st.session_state.gnfinder_results_raw = species_list  # Store raw data
                                    st.session_state.species_df_initial = species_df
                                    st.session_state.species_df_final = species_df.copy()
                                    
                                    st.success(f"Loaded {len(species_df)} species successfully!")
                                    st.rerun()
                            
                            with col2:
                                if st.button("Add to Current Species", key="add_to_species"):
                                    # Add to existing species (avoid duplicates based on Name)
                                    current_species = getattr(st.session_state, 'species_df_final', pd.DataFrame())
                                    if not current_species.empty:
                                        existing_names = set(current_species['Name'].tolist())
                                        new_species = [sp for sp in species_list if sp.get('Name') not in existing_names]
                                        
                                        if new_species:
                                            new_df = pd.DataFrame(new_species)
                                            combined_df = pd.concat([current_species, new_df], ignore_index=True)
                                            st.session_state.species_df_final = combined_df
                                            st.session_state.species_df_initial = combined_df.copy()
                                            st.success(f"Added {len(new_species)} new species (duplicates skipped)!")
                                        else:
                                            st.info("No new species to add (all were duplicates).")
                                    else:
                                        # No existing species, just load them
                                        species_df = pd.DataFrame(species_list)
                                        st.session_state.species_df_initial = species_df
                                        st.session_state.species_df_final = species_df.copy()
                                        st.success(f"Added {len(species_df)} species!")
                                    st.rerun()
                        else:
                            st.warning("No species list found in the selected log file.")
                    
                    except Exception as e:
                        st.error(f"Error reading log file: {str(e)}")

        if not st.session_state.species_df_initial.empty:
            st.subheader("Taxonomic Filtering (Configurable)")
            st.markdown("Apply taxonomic filters to focus on specific biological groups and configure quality thresholds.")
            
            # Taxonomic Group Filter with configurable options
            with st.expander("🏷️ Taxonomic Group Filter", expanded=True):
                st.markdown("Filter by a specific taxonomic group with configurable GBIF verification strictness.")


                # Basic taxonomic filter settings
                col1, col2 = st.columns(2)
                with col1:
                    rank = st.selectbox("Taxonomic Rank", ["kingdom", "phylum", "class", "order", "family"], key="tax_rank")
                with col2:
                    # Provide helpful examples based on selected rank
                    examples = {
                        "kingdom": "e.g., 'Plantae', 'Animalia', 'Fungi'",
                        "phylum": "e.g., 'Chordata' (vertebrates), 'Tracheophyta' (vascular plants), 'Arthropoda' (insects/spiders)",
                        "class": "e.g., 'Aves' (birds), 'Mammalia' (mammals), 'Magnoliopsida' (flowering plants)",
                        "order": "e.g., 'Primates', 'Carnivora', 'Passeriformes'", 
                        "family": "e.g., 'Felidae' (cats), 'Rosaceae' (roses)"
                    }
                    placeholder_text = examples.get(rank, "Enter taxon name")
                    name = st.text_input(f"Taxon Name ({placeholder_text})", "Any", key="tax_name")

                # GBIF verification options
                st.markdown("**GBIF Verification Options:**")
                verification_col1, verification_col2, verification_col3 = st.columns(3)
                
                with verification_col1:
                    tax_include_fuzzy = st.checkbox(
                        "Include Fuzzy Matches", 
                        value=True, 
                        key="tax_include_fuzzy",
                        help="Include species with approximate/fuzzy GBIF matches (e.g., slight spelling variants)"
                    )
                with verification_col2:
                    tax_include_higherrank = st.checkbox(
                        "Include Higher Rank", 
                        value=False, 
                        key="tax_include_higherrank",
                        help="Include matches at genus/family level (less specific but broader coverage)"
                    )
                with verification_col3:
                    tax_include_unverified = st.checkbox(
                        "Include Unverified", 
                        value=False, 
                        key="tax_include_unverified",
                        help="Include species with no GBIF verification"
                    )



                # Apply filter button
                if st.button("Apply Taxonomic Filter", type="primary"):
                    if name and name.lower() != 'any':
                        with st.spinner("Applying taxonomic filter..."):
                            st.session_state.species_df_final = filter_by_taxonomy(
                                st.session_state.species_df_initial, 
                                rank, name,
                                include_fuzzy=st.session_state.tax_include_fuzzy,
                                include_higherrank=st.session_state.tax_include_higherrank,
                                include_unverified=st.session_state.tax_include_unverified
                            )
                            filtered_count = len(st.session_state.species_df_final)
                            initial_count = len(st.session_state.species_df_initial)
                            removed_count = initial_count - filtered_count
                            st.success(f"✅ Taxonomic filter applied! Kept {filtered_count} species from {rank}: {name} (removed {removed_count} species)")
                    else:
                        # No taxonomic group specified - apply general quality filter
                        if not (st.session_state.tax_include_fuzzy and st.session_state.tax_include_higherrank and st.session_state.tax_include_unverified):
                            with st.spinner("Applying quality filter..."):
                                # Use filter_by_taxonomy with no taxonomic constraint but with quality settings
                                st.session_state.species_df_final = filter_by_taxonomy(
                                    st.session_state.species_df_initial, 
                                    "kingdom", "any",  # No taxonomic constraint
                                    include_fuzzy=st.session_state.tax_include_fuzzy,
                                    include_higherrank=st.session_state.tax_include_higherrank,
                                    include_unverified=st.session_state.tax_include_unverified
                                )
                                filtered_count = len(st.session_state.species_df_final)
                                initial_count = len(st.session_state.species_df_initial)
                                removed_count = initial_count - filtered_count
                                st.success(f"✅ Quality filter applied! Kept {filtered_count} verified species (removed {removed_count} unverified)")
                        else:
                            st.session_state.species_df_final = st.session_state.species_df_initial.copy()
                            st.info("No filters applied - keeping all species")
            
            st.markdown("---")
            display_df_and_download(
                st.session_state.species_df_final,
                "Final Species List for Extraction",
                "final_species_list",
                context="species_id_final"
            )
            
            with st.expander("Show initial unfiltered species list"):
                # --- START OF DEFINITIVE FIX ---
                # Use the correct variable name: species_df_initial
                display_df_and_download(
                    st.session_state.species_df_initial,
                    "Initially Identified Species (Pre-Taxonomic Filter)",
                    "initial_species_list",
                    context="species_id_initial"
                )