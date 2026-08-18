import json
import os
from typing import Set, Any
from .base import BaseParser, ParseResult
from ..config import settings

class ADIAdapter(BaseParser):
    """Azure Document Intelligence adapter (Mock implementation).
    
    For the take-home, this loads from a fixture to demonstrate the adapter pattern
    without requiring API keys or hitting the F0 tier limits.
    """
    
    def __init__(self, use_mock: bool = True):
        self.use_mock = use_mock
        # Real implementation would initialize AzureClient here if not use_mock
        
    async def parse(self, file_bytes: bytes, filename: str, metadata: dict[str, Any]) -> ParseResult:
        if not self.use_mock and settings.azure_di_endpoint and settings.azure_di_key:
            # Placeholder for real Azure DI SDK call
            pass
            
        # Mock mode: load from fixture
        # Resolve path relative to this file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        fixture_path = os.path.join(current_dir, "..", "..", "..", "tests", "fixtures", "adi_sample.json")
        
        # If running from a different working directory, try an absolute fallback or just load an empty structure
        if not os.path.exists(fixture_path):
            # Try from root
            fixture_path = os.path.join(os.getcwd(), "tests", "fixtures", "adi_sample.json")
            
        if os.path.exists(fixture_path):
            with open(fixture_path, "r", encoding="utf-8") as f:
                raw_output = json.load(f)
        else:
            # Fallback if fixture not found
            raw_output = {"pages": [{"pageNumber": 1}], "paragraphs": []}
            
        page_count = len(raw_output.get("pages", []))
        return ParseResult(raw_output=raw_output, page_count=page_count)

    @property
    def supported_formats(self) -> Set[str]:
        return {".pdf", ".jpeg", ".jpg", ".png", ".tiff", ".bmp", ".docx", ".xlsx", ".pptx", ".html"}
        
    @property
    def name(self) -> str:
        return "azure_di"
        
    @property
    def version(self) -> str:
        return "2024-02-29-preview" # Typical API version for ADI
