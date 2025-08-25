"""
EcoParse: Automated Species Data Extraction System

EcoParse is a comprehensive Python package for automated extraction of species-specific
ecological and taxonomic data from biodiversity literature. The system integrates
multiple technologies including species name recognition, large language models,
and quality control mechanisms to enable large-scale processing of scientific documents.

Core Components:

ecoparse.core.models:
    Data structures and validation schemas for species extraction workflows

ecoparse.core.finders:
    Species name discovery and taxonomic filtering using GNfinder and GBIF

ecoparse.core.sourcetext:
    PDF processing, text extraction, and context retrieval functions

ecoparse.core.extractor:
    LLM-based data extraction engine supporting multiple providers

ecoparse.core.prompter:
    Prompt engineering templates for consistent LLM interactions

ecoparse.core.verifier:
    Automated verification and quality control mechanisms

ecoparse.core.reporter:
    Comprehensive reporting and performance analysis tools

Scientific Applications:
- Biodiversity data extraction from literature
- Conservation status compilation
- Ecological trait databases
- Systematic reviews and meta-analyses
- Species distribution modeling datasets

The package is designed for scientific reproducibility, providing detailed
documentation, error handling, and performance metrics suitable for
publication-quality research workflows.
"""

# Package metadata
__version__ = "1.0.0"
__author__ = "Adam Ulicny"
__email__ = "ulicny@fld.czu.cz"