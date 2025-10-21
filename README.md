# EcoParse 

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**EcoParse** is a flexible tool designed to extract species-level data from PDFs. Using a combination of scientific name recognition [(GNfinder)](https://github.com/gnames/gnfinder), taxonomic verification [(GBIF)](https://github.com/gbif/pygbif), and Large Language Models (LLMs), EcoParse automates the data collection process for ecological research.

Unlike rigid scraping scripts, EcoParse is fully configurable. You can define exactly what data fields you want to extract. Whether it's conservation status, habitat type, elevation range, or any other piece of information present in the text.

## Key Features

-   **Configurable Data Extraction**: Define any data field you need (e.g., "Habitat", "Diet", "Wingspan") in a simple YAML configuration file.
-   **Multiple LLM Backends**: Supports Google Gemini via API (paid tier) and local models via Ollama.
-   **Advanced Species Identification**: Integrates with GNfinder and uses robust filtering to accurately identify species and subspecies, resolving nested names (e.g., preferring "Falco peregrinus pelegrinoides" over "Falco peregrinus" when both are found and nested).
-   **Interactive UI**: An easy-to-use web interface built with Streamlit to manage the entire workflow, from PDF upload to result analysis.
-   **Context-Aware Analysis**: Provides the LLM with either surrounding text chunks or full-page images for context.
-   **Manual Verification**: A dedicated tab to step through results one-by-one, view page context, and confirm or correct the LLM's output.
-   **Detailed Reporting**: Automatically generates a detailed JSON report for each extraction run, ensuring your work is reproducible and ready for further analysis.

---

## Installation

### Docker Installation (Recommended)

The easiest way to run EcoParse is using Docker, which handles all crucial dependencies automatically:

**Prerequisites:**
- [Docker](https://docs.docker.com/get-docker/) installed on your system
- [Git](https://git-scm.com/downloads) to clone the repository

**Quick Start:**
```bash
# Clone the repository
git clone https://github.com/AdamUlicny/EcoParse.git
cd EcoParse

# Build and run with our convenient script
./build_docker.sh
```

The `build_docker.sh` script will:
- Build the Docker image with all dependencies (Python, GNfinder, etc.)
- Automatically start the container
- Launch the application on `http://localhost:8501`
- Start GNfinder service in the background

That's it! The script handles everything for you.

**Alternative:** After the initial build, you can also start the container directly with:
```bash
docker run -p 8501:8501 -p 4040:4040 ecoparse-app
```

**Setting up LLMs:**

For **Gemini API** (recommended for most users):
- Get your API key at [Google AI Studio](https://aistudio.google.com/)
- Enter the key in the EcoParse interface
- Note: Paid tier recommended for fast extractions (free tier has heavy rate limiting)

For **Ollama** (local LLMs):
- Install Ollama on your host system: [ollama.ai](https://ollama.ai/)
- Pull your desired model: `ollama pull <model_name>`
- EcoParse will connect to Ollama running on your host machine

**Need help?** See the [Docker installation guide](documentation/docker-guide.md) for detailed instructions and troubleshooting.

### 📋 Manual Installation

For development or if you prefer manual setup, see our [detailed installation guide](documentation/manual-installation.md).

---

## Getting Started

Once EcoParse is running (via Docker or manual installation), open your browser to `http://localhost:8501` to access the web interface.

## Workflow Overview

The application is organized into tabs to guide you through the process:

1.  **Upload PDF**: Load your source document. Trim pages (remove sources or introduction to avoid uneccessary species mentions)
2.  **Identify Species**: Run GNfinder to find all scientific names and apply optional taxonomic filters.
3.  **Configure Extraction**: Define the data fields you want the LLM to find using a simple YAML editor. Add examples to guide the model.
4.  **Run Extraction**: Configure LLM settings and execute the main data extraction process.
5.  **View Results**: See the extracted data in a table and view summary charts.
6.  **Manual Verification**: Step through each result, view the page context, and confirm or correct the data.
7.  **Reports**: View a summary of your last run and download the complete, detailed JSON report for your records.

## Project Configuration

The power of EcoParse lies in its YAML configuration. In the "Configure Extraction" tab, you can define your project and the data you need.

**Example `project_config.yml`:**
```yaml
project_name: "Avian Habitat and Status in Montane Forests"
project_description: "Extracts conservation status and primary habitat for bird species."

# Define the specific pieces of data you want to extract for each species.
data_fields:
  - name: "conservation_status"
    description: "The regional conservation status code."
    # Providing validation values greatly improves accuracy. "NF" is for "Not Found".
    validation_values: ["RE", "CR", "EN", "VU", "NT", "LC", "DD", "NF"]
  
  - name: "primary_habitat"
    description: "A brief description of the species' primary habitat."
    # An empty list means free text is allowed.
    validation_values: []
```

## More information

See the poster made for the [**LivingData 2025 Conference**](https://www.livingdata2025.com/) to quickly grasp the core idea of the pipeline.
![poster](/poster/POSTER_web.png) 

---
## Disclaimer

The author of this software is not a computer scientist or professional programmer! Because of that, most of the code in this repository was created with the help of various AI systems (commonly known as [vibe-coding](https://www.ibm.com/think/topics/vibe-coding)). If you spot any mistakes, please inform us.

## Contributing

Bug reports, feature requests, and pull requests are welcome! Please open an issue in the [issue tracker](https://github.com/AdamUlicny/EcoParse/issues) to discuss any changes.

## License

This project is licensed under the **MIT License**. See the `LICENSE` file for details.