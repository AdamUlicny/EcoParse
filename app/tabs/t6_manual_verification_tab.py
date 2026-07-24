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
import os
import json
from pathlib import Path

def save_verification_progress():
    """Update the persistent JSON report file with current manual verification results."""
    last_report_path = st.session_state.get('last_report_path')
    if last_report_path and os.path.exists(last_report_path):
        try:
            with open(last_report_path, 'r', encoding='utf-8') as f:
                report_data = json.load(f)
            
            # Update the manual verification info
            report_data["manual_verification_info"] = {
                "run": bool(st.session_state.manual_verification_results),
                "full_results": st.session_state.manual_verification_results
            }
            
            # Write back
            with open(last_report_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=4)
        except Exception as e:
            print(f"Error auto-saving verification progress: {e}")

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
        # Sort by review_flag priority: CHECK first, then NF, then OK
        flag_priority = {'CHECK': 0, 'NF': 1, 'OK': 2}
        sorted_results = sorted(
            extraction_results, 
            key=lambda x: flag_priority.get(x.get('review_flag', 'CHECK'), 0)
        )
        st.session_state.verification_queue = sorted_results.copy()
        st.session_state.verification_current_index = 0
        st.session_state.manual_verification_results = []

    # --- Flag Filter ---
    filter_col1, filter_col2, filter_col3 = st.columns([1, 1, 2])
    with filter_col1:
        flag_filter = st.selectbox(
            "Filter by Flag",
            ["All", "CHECK", "NF", "OK"],
            index=0,
            key="flag_filter"
        )
    
    # Apply filter to queue
    full_queue = getattr(st.session_state, 'verification_queue', [])
    if flag_filter != "All":
        filtered_queue = [item for item in full_queue if item.get('review_flag', 'CHECK') == flag_filter]
    else:
        filtered_queue = full_queue
    
    with filter_col2:
        # Show counts
        check_count = sum(1 for item in full_queue if item.get('review_flag', 'CHECK') == 'CHECK')
        nf_count = sum(1 for item in full_queue if item.get('review_flag') == 'NF')
        ok_count = sum(1 for item in full_queue if item.get('review_flag') == 'OK')
        st.markdown(f"**Flags:** 🔍 CHECK: {check_count} | ❌ NF: {nf_count} | ✅ OK: {ok_count}")

    total_items = len(filtered_queue)
    index = st.session_state.verification_current_index

    # Ensure index is valid for filtered queue
    if index >= total_items:
        if total_items == 0:
            st.info(f"No items match the '{flag_filter}' filter.")
            return
        st.success("All filtered items have been verified!")
        st.balloons()
        if st.session_state.manual_verification_results:
            # Flatten the results before displaying
            flattened_results = []
            for result in st.session_state.manual_verification_results:
                flat_record = {
                    'species': result.get('species'),
                    'review_flag': result.get('review_flag', 'CHECK'),
                    'status': result.get('status')
                }
                # Unpack the 'data' dictionary into top-level keys
                if isinstance(result.get('data'), dict):
                    flat_record.update(result['data'])
                
                flat_record['notes'] = result.get('notes')
                flattened_results.append(flat_record)

            final_df = pd.DataFrame(flattened_results)
            
            # Reorder columns to a more logical sequence if desired
            if not final_df.empty:
                cols = final_df.columns.tolist()
                # Move species and review_flag to the front
                if 'species' in cols:
                    cols.insert(0, cols.pop(cols.index('species')))
                if 'review_flag' in cols:
                    cols.insert(1, cols.pop(cols.index('review_flag')))
                if 'status' in cols:
                    cols.insert(2, cols.pop(cols.index('status')))
                # Move notes to the end
                if 'notes' in cols:
                    cols.append(cols.pop(cols.index('notes')))
                final_df = final_df[cols]

            display_df_and_download(
                final_df, 
                "Manually Verified Results", 
                "manual_verification_results",
                context="manual_verify_main"
            )
        return


    st.progress((index + 1) / total_items, text=f"Verifying item {index + 1} of {total_items}")
    
    current_item = filtered_queue[index]
    species_name = current_item.get('species', 'N/A')
    review_flag = current_item.get('review_flag', 'CHECK')
    
    # Flag badge styling
    flag_colors = {'OK': '🟢', 'CHECK': '🟡', 'NF': '🔴'}
    flag_badge = flag_colors.get(review_flag, '⚪')
    
    st.subheader(f"{flag_badge} Species: `{species_name}`")
    
    # Warning for subspecies
    # Check if the current species is a binomial (2 words) and if there are trinomials starting with it.
    current_words = species_name.split()
    if len(current_words) == 2:
        subspecies_present = []
        for other_item in full_queue:
            other_name = other_item.get('species', '')
            if other_name != species_name and other_name.startswith(species_name + ' '):
                subspecies_present.append(other_name)
        
        if subspecies_present:
            subspecies_present = sorted(list(set(subspecies_present)))
            count = len(subspecies_present)
            subspecies_list_str = ', '.join(subspecies_present)
            st.warning(f"⚠️ **Warning:** This species has {count} subspecies in the results! **{subspecies_list_str}**")
    
    col1, col2 = st.columns([2, 1])

    with col1:
        # Determine extraction type to set smart default
        context_chunks = current_item.get('context_chunks', [])
        is_image_based = (
            len(context_chunks) == 1 and 
            "Image-based extraction does not use text chunks" in context_chunks[0]
        )
        
        # Default to Images (index 1) if image-based, otherwise Text (index 0)
        default_index = 1 if is_image_based else 0

        # Context View Selector
        view_mode = st.radio(
            "Context View", 
            ["Text Context", "Document Images"], 
            index=default_index,
            horizontal=True,
            label_visibility="collapsed",
            key=f"view_mode_{index}"
        )

        if view_mode == "Text Context":
            st.markdown("**Text Context**")
            with st.container(height=500, border=False):
                context_chunks = current_item.get('context_chunks', [])
                if not context_chunks:
                    st.warning("No text context is available for this item. It might have been an image-based extraction or an error occurred.")
                else:
                    # Get all dynamic field values for highlighting
                    terms_to_find = [species_name] + [str(v) for v in current_item.get('data', {}).values() if v]
                    
                    total_found_count = 0
                    
                    for i, chunk in enumerate(context_chunks):
                        st.markdown(f"--- **Context Chunk {i+1}** ---")
                        from app.ui_helpers import highlight_text_in_chunk
                        highlighted_chunk, found_count = highlight_text_in_chunk(chunk, terms_to_find)
                        
                        st.markdown(highlighted_chunk, unsafe_allow_html=True)
                        total_found_count += found_count
                    
                    if total_found_count == 0:
                        st.info("None of the extracted data fields could be highlighted in the provided text chunks.")
        
        else:
            # Document Images View
            st.markdown("**Document Images**")
            pdf_file = getattr(st.session_state, 'pdf_buffer', None)
            if not pdf_file:
                st.error("PDF file not found in session. Please upload the PDF again.")
            else:
                # Generate/Fetch images on the fly
                # We create a temporary single-row DataFrame for this species
                temp_df = pd.DataFrame([{"Name": species_name}])
                
                with st.spinner(f"Generating page images for {species_name}..."):
                    try:
                        # Use our optimized function
                        # Note: Function expects io.BytesIO, so we wrap the bytes if needed
                        # But st.session_state.pdf_file is usually UploadedFile which behaves like BytesIO, 
                        # or we might need to seek(0).
                        # Let's ensure we work with a copy or handle it carefully.
                        
                        # Create a fresh buffer to avoid messing with the main file pointer if used elsewhere concurrently?
                        # Actually, get_species_page_images does seek(0) anyway.
                        # But let's check if pdf_file is bytes or file-like.
                        if isinstance(pdf_file, bytes):
                            buffer_to_use = io.BytesIO(pdf_file)
                        else:
                            buffer_to_use = pdf_file
                            
                        images_dict = get_species_page_images(
                            buffer_to_use, 
                            temp_df, 
                            full_text=st.session_state.get('full_text')
                        )
                        images = images_dict.get(species_name, [])
                        
                        if not images:
                            st.warning(f"No pages found containing '{species_name}'.")
                        else:
                            st.success(f"Found {len(images)} page(s) with '{species_name}'.")
                            
                            # Display images using tabs if multiple to prevent squeezing/miniatures
                            if len(images) == 1:
                                st.image(images[0], caption="Page Image", use_container_width=True)
                            else:
                                tabs = st.tabs([f"Page {i+1}" for i in range(len(images))])
                                for i, img_bytes in enumerate(images):
                                    with tabs[i]:
                                        st.image(img_bytes, caption=f"Page Image {i+1}", use_container_width=True)
                                        
                    except Exception as e:
                        st.error(f"Error generating images: {e}")



    with col2:
        st.markdown("**Extracted Data**")
        
        edited_data = {}
        
        # Always display all fields defined in the project configuration
        data_fields = st.session_state.project_config.get('data_fields', [])
        if not data_fields:
            # Fallback to default project configuration if the loaded config lacks data_fields
            import yaml
            from pathlib import Path
            try:
                default_config_path = Path(__file__).parent.parent / "assets/default_project_config.yml"
                with open(default_config_path, 'r', encoding='utf-8') as f:
                    fallback_config = yaml.safe_load(f)
                data_fields = fallback_config.get('data_fields', [])
            except Exception as e:
                print(f"Error loading fallback project config: {e}")
                
        extracted_data = current_item.get('data', {})
        
        for field_config in data_fields:
            field = field_config['name']
            value = extracted_data.get(field, None)
            
            if field_config.get('validation_values'):
                options = list(field_config['validation_values'])
                try:
                    current_index = options.index(value)
                except (ValueError, TypeError):
                    if value is not None and str(value).strip() != "":
                        options.append(value)
                        current_index = len(options) - 1
                        st.warning(f"⚠️ **Note:** The extracted value `{value}` for `{field}` is not in your configured validation list. It has been temporarily added as an option to prevent data loss.")
                    else:
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
                    value=value if value is not None else "",
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
            "review_flag": review_flag,
            "data": edited_data,
            "notes": edited_notes,
            "status": "Verified"
        }
        if index < len(st.session_state.manual_verification_results):
            st.session_state.manual_verification_results[index] = result_to_save
        else:
            st.session_state.manual_verification_results.append(result_to_save)
        
        save_verification_progress()
        st.session_state.verification_current_index += 1
        st.rerun()

    if nav_cols[2].button("⏩ Skip", use_container_width=True):
        result_to_save = {**current_item, "status": "Skipped"}
        if index < len(st.session_state.manual_verification_results):
            st.session_state.manual_verification_results[index] = result_to_save
        else:
            st.session_state.manual_verification_results.append(result_to_save)
            
        save_verification_progress()
        st.session_state.verification_current_index += 1
        st.rerun()