# Docker Installation Guide

This guide provides detailed information about running EcoParse using Docker.

## Quick Start

```bash
# Clone the repository
git clone https://github.com/AdamUlicny/EcoParse.git
cd EcoParse

# Build and run with Docker
bash build_docker.sh
```

## What the Docker Setup Includes

The Docker container automatically handles:
- **Python 3.9** runtime environment
- **GNfinder** binary installation and configuration  
- **All Python dependencies** from `pyproject.toml`
- **Port configuration** for both EcoParse (8501) and GNfinder (4040)
- **Background services** - GNfinder starts automatically

## Manual Docker Commands

If you prefer to run Docker commands manually:

```bash
# Build the Docker image
docker build -t ecoparse-app .

# Run the container with port forwarding
docker run -p 8501:8501 -p 4040:4040 ecoparse-app

# Run in detached mode (background)
docker run -d -p 8501:8501 -p 4040:4040 ecoparse-app

# View running containers
docker ps

# Stop the container
docker stop <container_id>
```

## LLM Configuration with Docker

### Using Gemini API
- No additional setup required
- Enter your API key in the EcoParse web interface
- Get your key at: https://aistudio.google.com/

### Using Ollama (Local LLMs)
When using Docker, Ollama must run on your **host machine** (not in the container):

```bash
# On your host machine (outside Docker):
# 1. Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# 2. Pull a model
ollama pull llama3

# 3. Start Ollama service
ollama serve
```

EcoParse in Docker will connect to Ollama on your host machine via `host.docker.internal` (automatic).

## Troubleshooting

### Common Issues

**Port conflicts:**
```bash
# Check if ports are in use
lsof -i :8501
lsof -i :4040

# Use different ports if needed
docker run -p 8502:8501 -p 4041:4040 ecoparse-app
```

**Container won't start:**
```bash
# Check Docker logs
docker logs <container_id>

# Rebuild the image
docker build --no-cache -t ecoparse-app .
```

**Can't access the application:**
- Ensure Docker is running: `docker --version`
- Check container status: `docker ps`
- Verify ports are correctly mapped: `docker port <container_id>`
- Try accessing `http://127.0.0.1:8501` instead of `localhost:8501`

**Ollama connection issues:**
- Ensure Ollama is running on host: `ollama list`
- Check Ollama is accessible: `curl http://localhost:11434/api/tags`
- On Linux, you may need to configure Ollama to bind to all interfaces:
  ```bash
  # Set environment variable before starting Ollama
  export OLLAMA_HOST=0.0.0.0:11434
  ollama serve
  ```

## Updating EcoParse

To update to the latest version:

```bash
# Pull latest changes
git pull origin main

# Rebuild Docker image
docker build --no-cache -t ecoparse-app .

# Run updated container
docker run -p 8501:8501 -p 4040:4040 ecoparse-app
``` 