from typing import Protocol, Set, Any
from ..core.models import CanonicalDocument

class ParseResult:
    def __init__(self, raw_output: dict[str, Any], page_count: int):
        self.raw_output = raw_output
        self.page_count = page_count

class BaseParser(Protocol):
    """Protocol that all parser adapters must implement."""
    
    async def parse(self, file_bytes: bytes, filename: str, metadata: dict[str, Any]) -> ParseResult:
        """Parse the raw file bytes and return a structured parse result.
        
        This result will later be transformed by the normalizer into a CanonicalDocument.
        """
        ...
        
    @property
    def supported_formats(self) -> Set[str]:
        """Returns the set of file extensions (e.g. '.pdf', '.docx') supported by this parser."""
        ...
        
    @property
    def name(self) -> str:
        """The identifier of the parser."""
        ...
        
    @property
    def version(self) -> str:
        """The version of the parser used."""
        ...
