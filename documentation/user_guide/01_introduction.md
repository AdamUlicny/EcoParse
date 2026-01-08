# 1. Introduction

## What is EcoParse?

EcoParse is a specialized tool designed to extract data from documents that lack structured tabular or list-based data. It addresses the challenge of manually extracting information from species redlists where data is scattered on a per-page basis. The app is capable of extracting data from other types of sources, but our team is concerned with redlists. This guide will focus on the redlist extraction process, but the workflow can be adapted for other biodiversity literature types. 

## The Problem

Extracting species information manually from large PDF documents is time-consuming and prone to errors, especially when the relevant data (such as threat codes and criteria) is embedded within unstructured text across hundreds of pages. EcoParse automates this workflow to save time and increase consistency.

## Prerequisites for Extraction

For EcoParse to function correctly, your documents must meet the following criteria:

1.  **Latin Names**: Species must be mentioned by their scientific (Latin) names. Common names are not supported for automatic discovery.
2.  **Machine-Readable Text**: The document must be machine-readable. If you are working with scanned PDFs, they must be OCR'd (Optical Character Recognition) beforehand to allow text extraction.
3.  **Proximity of Information**: The crucial information you wish to extract (e.g., Threat Code, Threat Criteria) must be located on the *same page* as the species mention.
4.  **LLM service access**: EcoParse requires access to a Large Language Model (LLM) service to function. You can use locally run LLMs through **Ollama** or cloud API's (**Google Cloud** or **OpenRouter**)
