"""
Tab 3: Extraction Configuration

YAML-based configuration for extraction fields and examples.
"""

import streamlit as st
import yaml
import json
import os
import glob
from datetime import datetime
from app.ui_messages import show_loaded_session_complete, show_prerequisite_warning

def display():
    """Main display function for extraction configuration tab."""
    st.header("Configure Data Extraction")
    st.markdown("Define data fields for extraction using YAML configuration.")
    
    if st.session_state.session_loaded_from_report:
        show_loaded_session_complete("Configuration")
        st.markdown("Species list from loaded session:")
    elif not st.session_state.get('full_text'):
        show_prerequisite_warning("1. Upload PDF")
    else:
        # Configuration editor in an expander
        with st.expander("⚙️ Define Data Fields (YAML Configuration)", expanded=False):
            st.info("💡 **Tip:** You can also edit the default configuration by modifying `/app/assets/default_project_config.yml` in your EcoParse installation.")
            
            edited_yaml = st.text_area(
                "Project Configuration (YAML)",
                value=st.session_state.project_config_yaml,
                height=300,
                key="yaml_editor",
                help="Define the data fields you want to extract from each species. The YAML format allows you to specify field names, types, and validation rules."
            )
            
            if st.button("Update and Validate Configuration", type="primary"):
                try:
                    parsed_config = yaml.safe_load(edited_yaml)
                    if "project_name" not in parsed_config or "data_fields" not in parsed_config:
                        st.error("Configuration must contain 'project_name' and 'data_fields' keys.")
                    elif not isinstance(parsed_config["data_fields"], list):
                        st.error("'data_fields' must be a list of objects.")
                    else:
                        st.session_state.project_config_yaml = edited_yaml
                        st.session_state.project_config = parsed_config
                        st.success("Project configuration updated successfully!")
                except yaml.YAMLError as e:
                    st.error(f"Invalid YAML format: {e}")

        st.markdown("---")

        st.subheader("Add Prompt Examples (Optional)")
        st.markdown("Provide few-shot examples to guide the LLM. The output fields below are generated directly from your YAML configuration.")
        
        # Add "Load Examples from Past Log" functionality
        with st.expander("📂 Load Examples from Past Log", expanded=False):
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
                    key="log_selector"
                )
                
                if selected_log:
                    try:
                        with open(selected_log, 'r') as f:
                            log_data = json.load(f)
                        
                        # Find examples in the log
                        examples = None
                        if 'llm_extraction_info' in log_data and 'examples_used' in log_data['llm_extraction_info']:
                            examples = log_data['llm_extraction_info']['examples_used']
                        
                        if examples:
                            st.success(f"Found {len(examples)} examples in the selected log.")
                            
                            # Show preview of examples
                            st.markdown("**Preview of examples:**")
                            for i, example in enumerate(examples[:3]):  # Show first 3
                                with st.container(border=True):
                                    st.markdown(f"**Example {i+1} - INPUT:**")
                                    st.code(example['input'][:200] + ("..." if len(example['input']) > 200 else ""))
                                    st.markdown("**OUTPUT:**")
                                    st.code(json.dumps(example['output'], indent=2), language='json')
                                    if example.get('explainer'):
                                        st.markdown("**EXPLAINER:**")
                                        st.code(example['explainer'][:100] + ("..." if len(example['explainer']) > 100 else ""))
                            
                            if len(examples) > 3:
                                st.info(f"...and {len(examples) - 3} more examples.")
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("Load All Examples", type="primary", key="load_all_examples"):
                                    # Replace current examples with loaded ones
                                    st.session_state.prompt_examples = examples
                                    st.success(f"Loaded {len(examples)} examples successfully!")
                                    st.rerun()
                            
                            with col2:
                                if st.button("Add to Current Examples", key="add_to_examples"):
                                    # Add to existing examples (avoid duplicates)
                                    existing_inputs = {ex['input'] for ex in st.session_state.prompt_examples}
                                    new_examples = [ex for ex in examples if ex['input'] not in existing_inputs]
                                    st.session_state.prompt_examples.extend(new_examples)
                                    if new_examples:
                                        st.success(f"Added {len(new_examples)} new examples (duplicates skipped)!")
                                    else:
                                        st.info("No new examples to add (all were duplicates).")
                                    st.rerun()
                        else:
                            st.warning("No examples found in the selected log file.")
                    
                    except Exception as e:
                        st.error(f"Error reading log file: {str(e)}")

    with st.form("new_example_form", clear_on_submit=True):
        st.markdown("**INPUT:**")
        example_input = st.text_area("The sample sentence or text chunk from a document.", key="example_input_text")
        
        st.markdown("**OUTPUT:**")
        # Dynamically create input fields based on the YAML config
        data_fields = st.session_state.project_config.get('data_fields', [])
        if not data_fields:
            st.warning("No 'data_fields' defined in YAML config above. Please define at least one field to add an example.")
        
        output_values = {}
        for field in data_fields:
            field_name = field.get('name')
            # Create a user-friendly label from the field name
            label = field_name.replace('_', ' ').replace('-', ' ').title()
            output_values[field_name] = st.text_input(label, key=f"example_output_{field_name}")

        st.markdown("**EXPLAINER (Optional):**")
        example_explainer = st.text_area(
            "Add extra context or reasoning for the LLM. (e.g., 'The code 'VU D1' should be simplified to just 'VU'').",
            key="example_explainer_text"
        )
        
        submitted = st.form_submit_button("Add Example")
        if submitted and example_input and any(output_values.values()):
            # Create a structured dictionary for the example
            new_example = {
                "input": example_input,
                "output": output_values, # This is now a dictionary
                "explainer": example_explainer if example_explainer else None
            }
            st.session_state.prompt_examples.append(new_example)
            st.success("Example added!")

    if st.session_state.prompt_examples:
        st.markdown("**Current Examples:**")
        for i, example in enumerate(st.session_state.prompt_examples):
            with st.container(border=True):
                st.markdown(f"**INPUT:**\n```\n{example['input']}\n```")
                # Display the output dictionary as a formatted JSON string
                st.markdown("**OUTPUT:**")
                st.code(json.dumps(example['output'], indent=2), language='json')
                # Display the explainer only if it exists
                if example.get('explainer'):
                    st.markdown(f"**EXPLAINER:**\n```\n{example['explainer']}\n```")
                
                if st.button("Delete", key=f"del_ex_{i}"):
                    st.session_state.prompt_examples.pop(i)
                    st.rerun()