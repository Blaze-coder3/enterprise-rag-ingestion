import tempfile
import os
import asyncio
from typing import Set, Any
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.datamodel.base_models import InputFormat
from .base import BaseParser, ParseResult

class DoclingAdapter(BaseParser):
    """Adapter for Docling v2 using DocumentConverter with OCR and Formula options."""
    
    def __init__(self):
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = True
        
        self._converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )
    
    async def parse(self, file_bytes: bytes, filename: str, metadata: dict[str, Any]) -> ParseResult:
        # Docling currently requires a file path, so we write bytes to a temp file
        _, ext = os.path.splitext(filename)
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as temp_file:
            temp_file.write(file_bytes)
            temp_path = temp_file.name
            
        try:
            # Offload CPU-heavy PyTorch conversion to thread pool so Uvicorn event loop remains responsive
            result = await asyncio.to_thread(self._converter.convert, temp_path)
            
            # Export to the standard structured dictionary format
            raw_output = result.document.export_to_dict()
            
            # Extract page count if available, otherwise default to 1
            # Note: docling usually puts pages in the exported dict depending on the format
            page_count = 1
            if "pages" in raw_output:
                page_count = len(raw_output["pages"])
                
            return ParseResult(raw_output=raw_output, page_count=page_count)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    @property
    def supported_formats(self) -> Set[str]:
        return {".pdf", ".docx", ".pptx", ".xlsx", ".html", ".png", ".jpg"}
        
    @property
    def name(self) -> str:
        return "docling"
        
    @property
    def version(self) -> str:
        import docling
        return getattr(docling, "__version__", "2.115.0")
