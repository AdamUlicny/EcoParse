# Manual Installation Guide

This guide provides detailed instructions for installing EcoParse manually on your system. For most users, we recommend using the [Docker installation method](../README.md#installation) instead.

## Prerequisites

Before installing EcoParse manually, you must have the following software installed and running.

### **Python (version 3.9 or newer)**
First, check if you have a compatible version of Python installed.

```bash
python3 --version
```
If not, install it from the [official Python website](https://www.python.org/downloads/).

### **Git**
You will need Git to clone the project repository.
```bash
git --version
```
If not installed, get it from the [official Git website](https://git-scm.com/downloads).

### **GNfinder (Required)**
EcoParse relies on the GNfinder service to find scientific names in documents.
1.  Go to the [GNfinder GitHub Repository](https://github.com/gnames/gnfinder/) and install the program.
2.  **Start the GNfinder web service.** Open a **new, dedicated terminal window** and run the following command. The service must remain running while you use EcoParse.
    ```bash
    gnfinder -p 4040 rest
    ```
    *Keep this terminal open and running in the background.*

### **Gemini Paid Tier (Optional)**
Google provides a free tier of their Gemini LLM API, but due to heavy rate limiting (15 requests per minute with Gemini 2.5 Flash Lite), using the **paid tier** is needed for fast extractions. 
For testing, Google currently offers a free **3 month trial period**.
Obtain an API key at https://aistudio.google.com/.
The EcoParse app currently does not accommodate for using the free tier API, or support other LLM service providers such as OpenAI or Anthropic. Support could be added if requested.
At the time of development, Google Gemini (especially the Flash-Lite variants) offers the best price/performance service for this type of workload.

### **Ollama (Optional)**
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

## Manual Installation Steps

### 1. Clone the Repository
Open your terminal, navigate to where you want to store the project, and clone it.
```bash
git clone https://github.com/AdamUlicny/EcoParse.git
cd EcoParse
```

### 2. Create and Activate a Virtual Environment

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

### 3. Install EcoParse and Dependencies
While inside the activated virtual environment, use pip to install the package in "editable" mode (`-e`).
```bash
pip install -e .
```

## Running the Application

Make sure your **GNfinder service** (and Ollama, if you're using it) is running in its separate terminal.

Then, to launch the EcoParse web interface, in your virtual environment simply run:
```bash
ecoparse
```
This will start the Streamlit web server. Your terminal will display a local URL, which you can open in your web browser to begin.

To stop the app, return to the terminal where you ran the `ecoparse` command and press `Ctrl+C`.

## Troubleshooting

### Common Issues

1. **Python version conflicts**: Make sure you're using Python 3.9 or newer
2. **Virtual environment not activated**: Check that `(venv)` appears in your terminal prompt
3. **GNfinder not running**: Ensure the GNfinder service is running on port 4040
4. **Permission errors**: On some systems, you may need to use `pip3` instead of `pip`

### Getting Help

If you encounter issues with manual installation:
- Check our [GitHub Issues](https://github.com/AdamUlicny/EcoParse/issues) for known problems
- Consider using the [Docker installation method](../README.md#installation) instead
- Open a new issue if you can't find a solution