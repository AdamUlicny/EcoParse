from pydantic import BaseModel, Field, RootModel
from typing import List, Dict, Any, Optional

class SpeciesData(BaseModel):
    """
    A flexible model to hold any number of extracted data fields for a single species.
    The 'data' field is a dictionary where keys are the names of the data fields
    defined in the project configuration (e.g., 'conservation_status', 'habitat').
    """
    species: str = Field(
        ..., 
        description="The full scientific name of the species."
    )
    data: Dict[str, Any] = Field(
        ..., 
        description="A dictionary of extracted data fields and their corresponding values."
    )
    notes: Optional[str] = Field(
        None, 
        description="Any notes or issues from the LLM regarding this extraction (e.g., if data was ambiguous or not found)."
    )
    
class ExtractionResultList(RootModel):
    """
    A root model for a list of SpeciesData objects. This is used for robustly
    parsing JSON output from an LLM, which should return a list of results.
    """
    root: List[SpeciesData]

class VerificationData(BaseModel):
    """
    Model for verifying a single data point for a species. This can be used
    if a verification workflow is added in the future.
    """
    species: str = Field(
        ..., 
        description="The scientific name of the species being verified."
    )
    field_name: str = Field(
        ..., 
        description="The name of the data field being verified."
    )
    expected_value: Any = Field(
        ..., 
        description="The value that was previously extracted and is expected."
    )
    found_value: Any = Field(
        ..., 
        description="The new value found in the document during the verification pass."
    )
    is_match: bool = Field(
        ..., 
        description="True if the found value matches the expected value."
    )
    status: str = Field(
        ..., 
        description="A summary status of the verification (e.g., 'Match', 'Mismatch', 'Not Found')."
    )

class VerificationResultList(RootModel):
    """A root model for a list of verification results."""
    root: List[VerificationData]