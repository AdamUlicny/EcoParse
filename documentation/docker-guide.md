# Docker Installation Guide

This guide helps you run EcoParse easily using Docker. Docker allows you to run the application without installing Python or complex dependencies on your computer.

## Prerequisites

Before you begin, you need two things:

1.  **Docker Desktop**: Download and install it from [docker.com](https://www.docker.com/products/docker-desktop/).
    *   *Note: After installing, open "Docker Desktop" to make sure it is running.*
2.  **EcoParse Code**: You should have this folder on your computer.

---

## Option 1: The Easy Way (Windows)

We have created a simple script to handle everything for you.

1.  Open the **EcoParse** folder in File Explorer.
2.  Double-click the file named `run_docker.bat`.
3.  Terminal will open. It will:
    *   Build the application (this takes a few minutes the first time).
    *   Start the server.
4.  Once you see a message saying the server is running, open your web browser and go to:
    *   [http://localhost:8501](http://localhost:8501)

To stop the application, just close the terminal window.

---

## Option 2: The Manual Way (Mac/Linux/Windows)

If you prefer using the command line or are on Mac/Linux, follow these steps.

### 1. Open a Terminal
*   **Windows**: Right-click inside the EcoParse folder and select "Open in Terminal" (or use PowerShell/Command Prompt).
*   **Mac/Linux**: Open your terminal and navigate to the EcoParse folder.

### 2. Build the Application
Type this command and press Enter:

```bash
docker build -t ecoparse-app .
```

### 3. Run the Application
Type this command and press Enter:

```bash
docker run -p 8501:8501 -p 4040:4040 ecoparse-app
```

You can now access the app at [http://localhost:8501](http://localhost:8501).

---

## AI Model Setup (Optional)

EcoParse uses AI to analyze data. You have three choices:

### A. Use Google Gemini (Easiest)
1.  Get a free API key from [Google AI Studio](https://aistudio.google.com/).
2.  Enter this key in the EcoParse settings on the web page.
3.  No extra installation is needed!

### B. Use OpenRouter (Access to many models)
1.  Get an API key from [OpenRouter](https://openrouter.ai/).
2.  Enter this key in the EcoParse settings on the web page.
3.  This gives you access to models like GPT-4, Claude 3, Llama 3, etc.

### C. Use Local Models (Ollama)
If you want to run AI models on your own computer (free, but requires a powerful computer):

1.  Download and install **Ollama** from [ollama.com](https://ollama.com).
2.  Open your terminal/command prompt and run:
    ```bash
    ollama pull llama3
    ollama serve
    ```
3.  EcoParse will automatically connect to it.

---

## Troubleshooting

**"Docker is not running" error**
*   Make sure you have opened the **Docker Desktop** application. Look for the little whale icon in your taskbar.

**The web page won't load**
*   Wait a few seconds. The first time it starts, it might take a moment.
*   Check the black terminal window for any error messages.

**Port already in use**
*   If you see an error about "port 8501", it means EcoParse might already be running in another window. Close other Docker windows and try again.

**Updating the App**
*   If you download a new version of EcoParse, just run the `run_docker.bat` script again. It will automatically update the system.