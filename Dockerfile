# Use a Python base image
FROM python:3.9-slim

# System requirements
RUN apt-get update && apt-get install -y git curl

# Install EcoParse dependencies
COPY . /app
WORKDIR /app
RUN pip install --upgrade pip
RUN pip install -e .

# GNfinder: Download and install binary
RUN curl -L https://github.com/gnames/gnfinder/releases/download/v1.1.6/gnfinder-v1.1.6-linux.tar.gz -o /tmp/gnfinder.tar.gz \
    && tar -xzf /tmp/gnfinder.tar.gz -C /usr/local/bin \
    && chmod +x /usr/local/bin/gnfinder

# Expose EcoParse default port (Streamlit app) and GNfinder port
EXPOSE 8501 4040

# Entry point: run GNfinder in background and launch EcoParse
CMD gnfinder -p 4040 rest & ecoparse
