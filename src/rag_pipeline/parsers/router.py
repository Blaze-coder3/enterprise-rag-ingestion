import os
from typing import Tuple
from .base import BaseParser, ParseResult
from .docling_adapter import DoclingAdapter
from .adi_adapter import ADIAdapter
from ..core.models import QualityVerdict, ParseQualityMetrics

class ParserRouter:
    """Selects the appropriate parser and validates its output."""
    
    def __init__(self):
        self.docling = DoclingAdapter()
        self.adi = ADIAdapter()
        
    def select_parser(self, filename: str, file_bytes: bytes) -> Tuple[BaseParser, dict]:
        """
        Selects a parser based on file characteristics.
        Returns the parser and the signals used for the decision.
        """
        _, ext = os.path.splitext(filename.lower())
        
        # Default to docling for almost everything
        parser = self.docling
        decision = "docling"
        reason = f"default parser for {ext}"
        
        # We might route to ADI for specific formats if we want
        # but for the demo, Docling is our robust default.
        
        signals = {
            "extension": ext,
            "size_bytes": len(file_bytes)
        }
        
        return parser, {"decision": decision, "reason": reason, "signals": signals}
        
    def quality_gate(self, result: ParseResult, parser_name: str) -> Tuple[QualityVerdict, ParseQualityMetrics, str]:
        """
        Evaluates the parse result to determine if it meets quality standards.
        """
        # This is a simplified quality gate. In reality, we'd analyze the structure.
        raw = result.raw_output
        
        # Calculate some basic metrics
        metrics = ParseQualityMetrics()
        
        if parser_name == "docling":
            # For Docling, check texts length
            texts = raw.get("texts", [])
            total_chars = sum(len(t.get("text", "")) for t in texts)
            metrics.text_density = total_chars / max(1, result.page_count)
            
            tables = raw.get("tables", [])
            metrics.table_count = len(tables)
            
        elif parser_name == "azure_di":
            # For ADI
            paragraphs = raw.get("paragraphs", [])
            total_chars = sum(len(p.get("content", "")) for p in paragraphs)
            metrics.text_density = total_chars / max(1, result.page_count)
            
            tables = raw.get("tables", [])
            metrics.table_count = len(tables)

        # Verdict logic
        reason = "metrics_ok"
        verdict = QualityVerdict.PASS
        
        # If very low text density, it might be an un-OCRed image or bad parse
        if metrics.text_density < 50:
            if parser_name == "docling":
                verdict = QualityVerdict.FALLBACK
                reason = "low_text_density_try_fallback"
            else:
                verdict = QualityVerdict.NEEDS_REVIEW
                reason = "low_text_density_all_parsers_failed"
                
        return verdict, metrics, reason
