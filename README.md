# EcoParse 🦎

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**EcoParse** is a powerful and flexible tool designed to extract species-level data from PDFs. Using a combination of scientific name recognition (GNfinder), taxonomic verification (GBIF), and Large Language Models (LLMs), EcoParse automates the data collection process for ecological research.

Unlike rigid scripts, EcoParse is fully configurable. You can define exactly what data fields you want to extract for each species—whether it's conservation status, habitat type, elevation range, or any other piece of information present in the text.

## Key Features

-   **Configurable Data Extraction**: Define any data field you need (e.g., "Habitat", "Diet", "Max Size") in a simple YAML configuration file.
-   **Multiple LLM Backends**: Supports Google Gemini via API (paid tier) and local models via Ollama.
-   **Advanced Species Identification**: Integrates with GNfinder and uses robust filtering to accurately identify species and subspecies, resolving nested names (e.g., preferring "Falco peregrinus pelegrinoides" over "Falco peregrinus" when both are found and nested).
-   **Interactive UI**: An easy-to-use web interface built with Streamlit to manage the entire workflow, from PDF upload to result analysis.
-   **Context-Aware Analysis**: Provides the LLM with either surrounding text chunks or full-page images for context.
-   **Manual Verification**: A dedicated tab to step through results one-by-one, view page context, and confirm or correct the LLM's output.
-   **Detailed Reporting**: Automatically generates a detailed JSON report for each extraction run, ensuring your work is reproducible and ready for further analysis.

---

## Installation Guide

Follow these steps to set up and run EcoParse on your local machine. This guide is intended for Linux, macOS, or Windows using WSL (Windows Subsystem for Linux).

### 1. Prerequisites

Before installing EcoParse, you must have the following software installed and running.

#### **Python (version 3.9 or newer)**
First, check if you have a compatible version of Python installed.

```bash
python3 --version
```
If not, install it from the [official Python website](https://www.python.org/downloads/).

#### **Git**
You will need Git to clone the project repository.
```bash
git --version
```
If not installed, get it from the [official Git website](https://git-scm.com/downloads).

#### **GNfinder (Required)**
EcoParse relies on the GNfinder service to find scientific names in documents.
1.  Go to the [GNfinder Releases page](https://github.com/gnames/gnfinder/releases) and download the correct version for your operating system.
2.  Unzip the file and move the `gnfinder` executable to a location in your system's PATH (e.g., `/usr/local/bin` on Linux/macOS).
3.  **Start the GNfinder web service.** Open a **new, dedicated terminal window** and run the following command. The service must remain running while you use EcoParse.
    ```bash
    gnfinder -p 4040 rest
    ```
    *Keep this terminal open and running in the background.*

#### **Gemini Paid Tier (Optional)**
Google provides a free tier of their Gemini LLM API, but due to heavy rate limiting (15 requests per minute with Gemini 2.5 Flash Lite), using the paid tier is needed for fast extractions. 
For testing, Google currently offers a free 3 month trial period.
Obtain an API key at https://aistudio.google.com/.
The EcoParse app currently does not accomodate for using the free tier API, or support other LLM service providers such as OpenAI or Anthropic. Support could be added if requested.
At the time of development, Google Gemini (especially the Flash-Lite variants) offers the best price/performance service for this type of workload.

#### **Ollama (Optional)**
If you wish to use local LLMs instead of the Google Gemini API, you must install Ollama.
1.  Download and install Ollama from the [official Ollama website](https://ollama.ai/).
2.  After installing, pull the model you want to use from the command line. For example, to get Llama 3:
    ```bash
    ollama pull llama3
    ```
3.  Ensure the Ollama application is running in the background before starting EcoParse.

For running local LLM's efficiently, a powerful graphics card is required.
NVIDIA graphics cards currently have better support for AI related workloads (due to CUDA support).
Newer AMD cards can work too after installing [ROCm](https://www.amd.com/en/products/software/rocm.html). Tested on RX 7900 XTX.
For text-based data extraction, we currently use 8-20b parameter models.

### 2. Setting Up EcoParse

With the prerequisites ready, you can now install the application.

**Step 1: Clone the Repository**
Open your terminal, navigate to where you want to store the project, and clone it.
```bash
git clone https://github.com/AdamUlicny/EcoParse.git
cd EcoParse
```

**Step 2: Create and Activate a Virtual Environment**

```bash
# Create the virtual environment folder named 'venv'
python3 -m venv venv

# Activate the environment (the command differs by operating system)

# On Linux or macOS:
source venv/bin/activate

# On Windows (in Command Prompt or PowerShell):
.\venv\Scripts\activate
```
You will know the environment is active because your terminal prompt will change to show `(venv)` at the beginning.

**Step 3: Install EcoParse and Dependencies**
While inside the activated virtual environment, use pip to install the package in "editable" mode (`-e`).
```bash
pip install -e .
```

### 3. Running the Application

Make sure your **GNfinder service** (and Ollama, if you're using it) is running in its separate terminal.

Then, to launch the EcoParse web interface, in your virtual environment simply run:
```bash
ecoparse
```
This will start the Streamlit web server. Your terminal will display a local URL, which you can open in your web browser to begin.

To stop the app, return to the terminal where you ran the `ecoparse` command and press `Ctrl+C`.

---

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

---

## Contributing

Bug reports, feature requests, and pull requests are welcome! Please open an issue in the [issue tracker](https://github.com/your-username/EcoParse/issues) to discuss any changes.

## License

This project is licensed under the **MIT License**. See the `LICENSE` file for details.