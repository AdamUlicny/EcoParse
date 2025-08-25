"""
Tab 3: Extraction Configuration

Configure data fields, validation rules, and extraction parameters.
Defines what specific information to extract for each species.
"""

import streamlit as st
import yaml
import json

def display():
    """Main display function for extraction configuration tab."""
    st.header("Configure Data Extraction")
    st.markdown("""
    Define what data you want to extract for each species using YAML. This configuration
    tells the LLM exactly what to look for.
    """)
    if st.session_state.session_loaded_from_report:
        st.success("✅ This step was completed in the loaded session.")
        st.markdown("Below is the final list of species that was used for extraction.")
    elif not st.session_state.full_text:
        st.warning("Please upload and process a PDF in the '1. Upload PDF' tab first.")
    else:
        # Configuration editor
        edited_yaml = st.text_area(
            "Project Configuration (YAML)",
            value=st.session_state.project_config_yaml,
            height=300,
            key="yaml_editor"
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