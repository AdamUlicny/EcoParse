from pydantic import BaseModel, Field, RootModel
from typing import List, Dict, Any, Optional

class SpeciesData(BaseModel):
    """
    A flexible model to hold any number of extracted data fields for a single species.
    The 'data' field is a dictionary where keys are the names of the data fields
    defined in the project configuration (e.g., 'conservation_status', 'habitat').
    """
    species: str = Field(..., description="The full scientific name of the species.")
    data: Dict[str, Any] = Field(..., description="A dictionary of extracted data fields and their corresponding values.")
    notes: Optional[str] = Field(None, description="Any notes or issues from the LLM regarding this extraction (e.g., if data was ambiguous or not found).")
    
class ExtractionResultList(RootModel):
    """A root model for a list of SpeciesData objects, for robust JSON parsing."""
    root: List[SpeciesData]

class VerificationData(BaseModel):
    """
    Model for verifying a single data point for a species. This can be used
    if a verification workflow is added in the future.
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

# Models for Automated Verification ---
class AutomatedVerificationItem(BaseModel):
    """
    Represents the LLM's verification result for a single species and its fields.
    This is what the LLM should output per species in the verification prompt.
    """
    species: str = Field(..., description="The species name.")
    # Use a dictionary to hold verification for multiple data fields
    verified_data: Dict[str, Any] = Field(..., description="A dictionary of verified fields. Key=field_name, Value={expected, found, verified, status}")
    notes: Optional[str] = Field(None, description="Any general notes from the LLM about this species' verification.")

class AutomatedVerificationResponseList(RootModel):
    """Root model for a list of AutomatedVerificationItem objects."""
    root: List[AutomatedVerificationItem]

class SimplifiedVerificationItem(BaseModel):
    """
    Represents the LLM's simplified verification output for a single species.
    The LLM's only job is to find data, not compare it.
    """
    species: str = Field(..., description="The species name.")
    expected_data: Dict[str, Any] = Field(..., description="The expected data provided for context.")
    found_data: Dict[str, Any] = Field(..., description="The data the LLM actually found in the document.")
    notes: Optional[str] = Field(None, description="Any general notes from the LLM.")

class SimplifiedVerificationResponseList(RootModel):
    """Root model for a list of SimplifiedVerificationItem objects."""
    root: List[SimplifiedVerificationItem]