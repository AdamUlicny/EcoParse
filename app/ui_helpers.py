"""
Common UI component helpers for streamlined interface building.
"""

import streamlit as st
from pathlib import Path
import yaml

def create_model_selector(provider: str, models_list: list, is_disabled: bool = False):
    """Create standardized model selector with custom option."""
    options = ["Select a model..."] + [m["name"] for m in models_list]
    
    selected = st.selectbox(
        f"Select {provider} Model",
        options=options,
        disabled=is_disabled,
        help=f"Choose from {provider} models or use custom option below."
    )
    
    use_custom = st.checkbox(
        f"Use custom {provider.lower()} model",
        disabled=is_disabled,
        help="Enter custom model name not in dropdown."
    )
    
    if use_custom:
        custom = st.text_input(
            f"Custom {provider} Model Name",
            disabled=is_disabled,
            help="Enter custom model name (e.g., 'custom-model')."
        )
        return custom if custom else selected
    
    return selected if selected != "Select a model..." else None

def create_extraction_method_selector(current_method: str = "standard", key_suffix: str = ""):
    """Create standardized extraction method selector."""
    from app.ui_messages import EXTRACTION_METHOD_HELP
    
    methods = ["standard", "adaptive", "plumber", "reading-order"]
    default_index = methods.index(current_method) if current_method in methods else 0
    
    return st.selectbox(
        "Extraction Method",
        methods,
        index=default_index,
        key=f"extraction_method_{key_suffix}",
        help=EXTRACTION_METHOD_HELP
    )

def create_context_controls():
    """Create standardized context window controls."""
    col1, col2 = st.columns(2)
    with col1:
        st.number_input("Characters Before", 0, 50000, key="context_before")
    with col2:
        st.number_input("Characters After", 0, 50000, key="context_after")

def load_models_config():
    """Load models configuration with error handling."""
    models_file = Path(__file__).parent / "assets" / "models_list.yml"
    try:
        with open(models_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        st.warning(f"Models config not found: {models_file}")
        return {"ollama_models": [], "gemini_models": []}
    except Exception as e:
        st.error(f"Error loading models config: {e}")
        return {"ollama_models": [], "gemini_models": []}
