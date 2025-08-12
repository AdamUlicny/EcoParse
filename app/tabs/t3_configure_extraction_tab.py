import streamlit as st
import yaml

def display():
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
        
        # --- NEW: Prompt Examples Section ---
        st.subheader("Add Prompt Examples (Optional)")
        st.markdown("Provide few-shot examples to guide the LLM. Give it a sample sentence and the exact JSON `data` object you expect as output.")

        with st.form("new_example_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                example_input = st.text_area("Example Input Sentence(s)", placeholder="e.g., The conservation status of a species (F. p. peregrinus) is EN.")
            with col2:
                example_output = st.text_area("Expected JSON 'data' block", placeholder='e.g., {"conservation_status": "EN"}')
            
            submitted = st.form_submit_button("Add Example")
            if submitted and example_input and example_output:
                st.session_state.prompt_examples.append({"input": example_input, "output": example_output})
                st.success("Example added!")

        if st.session_state.prompt_examples:
            st.markdown("**Current Examples:**")
            for i, example in enumerate(st.session_state.prompt_examples):
                with st.container(border=True):
                    st.markdown(f"**Input:**\n```\n{example['input']}\n```")
                    st.markdown(f"**Expected Output:**\n```json\n{example['output']}\n```")
                    if st.button("Delete", key=f"del_ex_{i}"):
                        st.session_state.prompt_examples.pop(i)
                        st.rerun()