"""
Data Models for EcoParse Species Extraction System

This module defines Pydantic data models used throughout the EcoParse system for 
structured data handling and validation. These models ensure type safety and 
consistent data formats for species extraction, verification, and reporting.

Scientific Context:
- Enables standardized data extraction from biodiversity literature
- Supports flexible data schema for various ecological datasets
- Provides validation for species nomenclature and associated data
"""

from pydantic import BaseModel, Field, RootModel
from typing import List, Dict, Any, Optional

class SpeciesData(BaseModel):
    """
    Core data structure for extracted species information.
    
    This model represents the primary output of the extraction process, containing
    a species name and associated ecological/taxonomic data. The flexible 'data'
    field allows for project-specific information (e.g., conservation status,
    habitat preferences, geographic distribution).
    
    Scientific Purpose:
    - Standardizes species data across different extraction contexts
    - Supports variable data schemas for diverse research applications
    - Maintains data integrity through type validation
    """
    species: str = Field(..., description="The full scientific name of the species.")
    data: Dict[str, Any] = Field(..., description="A dictionary of extracted data fields and their corresponding values.")
    notes: Optional[str] = Field(None, description="Any notes or issues from the LLM regarding this extraction (e.g., if data was ambiguous or not found).")
    
class ExtractionResultList(RootModel):
    """
    Container for multiple species extraction results.
    
    Pydantic root model that enables robust JSON parsing and validation
    of extraction results from language models. Ensures that LLM outputs
    conform to expected data structures.
    """
    root: List[SpeciesData]

class VerificationData(BaseModel):
    """
    Model for manual verification of extracted species data.
    
    Used in quality control workflows where human experts validate
    the accuracy of automated extractions. Supports comparative analysis
    between expected and found values.
    
    Scientific Application:
    - Enables assessment of extraction accuracy
    - Supports iterative improvement of extraction methods
    - Facilitates creation of ground truth datasets
    """
    species: str = Field(..., description="The scientific name of the species being verified.")
    field_name: str = Field(..., description="The name of the data field being verified.")
    expected_value: Any = Field(..., description="The value that was previously extracted.")
    found_value: Any = Field(..., description="The new value found in the document during verification.")
    is_match: bool = Field(..., description="True if the found value matches the expected value.")
    status: str = Field(..., description="A summary status of the verification (e.g., 'Match', 'Mismatch', 'Not Found').")

class VerificationResultList(RootModel):
    """A root model for a list of verification results."""
    root: List[VerificationData]

# --- Automated Verification Models ---
# These models support automated quality control workflows using LLMs

class AutomatedVerificationItem(BaseModel):
    """
    LLM-generated verification result for species data validation.
    
    Represents the output of automated verification where an LLM
    cross-references extracted data against source documents to
    identify potential inconsistencies or errors.
    
    Workflow Integration:
    - Input: Previously extracted species data + source document
    - Process: LLM re-examines document for specified data fields
    - Output: Verification status and found values
    """
    species: str = Field(..., description="The species name.")
    # Use a dictionary to hold verification for multiple data fields
    verified_data: Dict[str, Any] = Field(..., description="A dictionary of verified fields. Key=field_name, Value={expected, found, verified, status}")
    notes: Optional[str] = Field(None, description="Any general notes from the LLM about this species' verification.")

class AutomatedVerificationResponseList(RootModel):
    """Container for multiple automated verification results."""
    root: List[AutomatedVerificationItem]

class SimplifiedVerificationItem(BaseModel):
    """
    Simplified LLM verification focused on data discovery rather than comparison.
    
    In this approach, the LLM's role is purely extractive - finding data
    in the document without making judgments about accuracy. The comparison
    and verification logic is handled by separate validation functions.
    
    Benefits:
    - Reduces LLM bias in verification decisions
    - Separates data extraction from validation logic
    - Enables more consistent verification outcomes
    """
    species: str = Field(..., description="The species name.")
    expected_data: Dict[str, Any] = Field(..., description="The expected data provided for context.")
    found_data: Dict[str, Any] = Field(..., description="The data the LLM actually found in the document.")
    notes: Optional[str] = Field(None, description="Any general notes from the LLM.")

class SimplifiedVerificationResponseList(RootModel):
    """Root model for a list of SimplifiedVerificationItem objects."""
    root: List[SimplifiedVerificationItem]