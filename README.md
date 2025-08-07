# EcoParse 🦎

**EcoParse** is a powerful and flexible tool designed to extract specific, species-level data from large documents like PDFs. Using a combination of scientific name recognition (GNfinder), taxonomic verification (GBIF), and Large Language Models (LLMs), EcoParse can automate the data collection process for ecological research.

Unlike rigid scripts, EcoParse is fully configurable. You can define exactly what data fields you want to extract for each species—whether it's conservation status, habitat type, elevation range, or any other piece of information present in the text.

## Features

- **Configurable Data Extraction**: Don't just find threat codes. Define any data field you need (e.g., "Habitat", "Diet", "Max Size") in a simple YAML configuration file.
- **Multiple LLM Backends**: Supports Google Gemini and local models via Ollama.
- **Species Identification**: Integrates with GNfinder to find all scientific names in a document.
- **Taxonomic Filtering**: Optionally filter the found species list by a specific taxonomic group (e.g., only include species from the class "Aves").
- **Text and Image-based Extraction**: Can provide the LLM with either surrounding text chunks or full-page images for context.
- **Interactive Streamlit UI**: An easy-to-use web interface to upload documents, configure projects, run extractions, and review results.

## Installation

1.  **Prerequisites**:
    *   Python 3.9+
    *   [GNfinder](https://github.com/gnames/gnfinder) installed and running as a web service.
    *   (Optional) [Ollama](https://ollama.ai/) installed and running for local LLM inference.

2.  **Clone and Install**:
    ```bash
    git clone https://github.com/yourusername/ecoparse.git
    cd ecoparse
    pip install -e .
    ```
    This installs the project in editable mode.

## Usage

1.  **Start GNfinder**: Ensure the GNfinder API server is running. By default, EcoParse looks for it at `http://localhost:4040/api/v1/find`.

2.  **Run the Streamlit App**:
    ```bash
    streamlit run app/main.py
    ```

3.  **Using the App**:
    *   Navigate to the "Upload PDF" tab to load your document.
    *   Go to "Species ID" to find all scientific names.
    *   In the "Configure Extraction" tab, define the data fields you want to extract.
    *   Run the extraction process in the "Run Extraction" tab.
    *   View and download your data from the "Results" tab.

## Project Configuration

The power of EcoParse lies in its project configuration file (`project_config.yml`). Here, you define the data you want to extract.

**Example: Extracting Conservation Status and Habitat**
```yaml
project_name: "Amphibian Status and Habitat"
project_description: "Extracts IUCN status and primary habitat for amphibian species."

data_fields:
  - name: "conservation_status"
    description: "The IUCN conservation status code (e.g., LC, NT, VU, EN, CR)."
    validation_values: ["LC", "NT", "VU", "EN", "CR", "DD", "RE", "NF"]
  - name: "primary_habitat"
    description: "A brief description of the species' primary habitat (e.g., 'Aquatic', 'Forest Floor', 'Arboreal')."
    validation_values: [] # No strict validation, free text is okay

# You can also customize prompts here if needed
prompts:
  text_based: "..."
  image_based: "..."