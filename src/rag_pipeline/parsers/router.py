import os
from typing import Tuple
from .base import BaseParser, ParseResult
from .docling_adapter import DoclingAdapter
from .adi_adapter import ADIAdapter
from .pandas_adapter import PandasAdapter
from .bs4_adapter import BS4Adapter
from ..core.models import QualityVerdict, ParseQualityMetrics

class ParserRouter:
    """Selects the appropriate parser and validates its output."""
    
    def __init__(self):
        self.docling = DoclingAdapter()
        self.adi = ADIAdapter() # Kept dormant for future use
        self.pandas_adapter = PandasAdapter()
        self.bs4_adapter = BS4Adapter()
        
    def select_parser(self, filename: str, file_bytes: bytes, metadata: dict = None) -> Tuple[BaseParser, dict]:
        """
        Selects a parser based on file characteristics or metadata overrides.
        Returns the parser and the signals used for the decision.
        """
        if metadata is None:
            metadata = {}
            
        _, ext = os.path.splitext(filename.lower())
        
        primary_override = metadata.get("primary_parser")
        if primary_override == "azure":
            parser = self.adi
            decision = "azure"
            reason = "metadata primary_parser override to azure"
        elif primary_override == "docling":
            parser = self.docling
            decision = "docling"
            reason = "metadata primary_parser override to docling"
        elif ext in self.pandas_adapter.supported_formats:
            parser = self.pandas_adapter
            decision = "pandas"
            reason = "spreadsheet format detected"
        elif ext in self.bs4_adapter.supported_formats:
            parser = self.bs4_adapter
            decision = "bs4"
            reason = "html format detected"
        else:
            parser = self.docling
            decision = "docling"
            reason = f"default parser for {ext}"
        
        signals = {
            "extension": ext,
            "size_bytes": len(file_bytes),
            "primary_parser_override": primary_override
        }
        
        return parser, {"decision": decision, "reason": reason, "signals": signals}
        
    def quality_gate(self, result: ParseResult, parser_name: str, metadata: dict = None) -> Tuple[QualityVerdict, ParseQualityMetrics, str]:
        """
        Evaluates the parse result to determine if it meets quality standards.
        """
        if metadata is None:
            metadata = {}
            
        raw = result.raw_output
        metrics = ParseQualityMetrics()
        
        if parser_name == "docling":
            texts = raw.get("texts", [])
            total_chars = sum(len(t.get("text", "")) for t in texts)
            metrics.text_density = total_chars / max(1, result.page_count)
            
            tables = raw.get("tables", [])
            metrics.table_count = len(tables)
            
        elif parser_name == "azure_di":
            paragraphs = raw.get("paragraphs", [])
            total_chars = sum(len(p.get("content", "")) for p in paragraphs)
            metrics.text_density = total_chars / max(1, result.page_count)
            
            tables = raw.get("tables", [])
            metrics.table_count = len(tables)
            
        elif parser_name in ("pandas", "bs4"):
            tables = raw.get("tables", [])
            metrics.table_count = len(tables)
            texts = raw.get("texts", [])
            total_chars = sum(len(t.get("text", "")) for t in texts)
            metrics.text_density = total_chars / max(1, result.page_count)
            if parser_name == "pandas":
                metrics.text_density = max(metrics.text_density, 100)
 
        # Collect full text to check for quality issues
        full_text = ""
        if parser_name == "docling":
            texts = raw.get("texts", [])
            full_text = " ".join(t.get("text", "") for t in texts)
        elif parser_name == "azure_di":
            paragraphs = raw.get("paragraphs", [])
            full_text = " ".join(p.get("content", "") for p in paragraphs)
        elif parser_name in ("pandas", "bs4"):
            texts = raw.get("texts", [])
            full_text = " ".join(t.get("text", "") for t in texts)

        # Check for font encoding corruption issues
        import re
        math_count = len(re.findall(r"[\U0001D400-\U0001D7FF]", full_text))
        repeated_placeholders = len(re.findall(r"([A-Za-z\U0001D400-\U0001D7FF])\1{4,}", full_text))
        
        is_corrupted = False
        if math_count > 50 or repeated_placeholders > 3:
            is_corrupted = True
            metrics.unverified_structures.append("corrupted_font_encoding")
            metrics.extraction_confidence_score = 0.3

        # Verdict logic
        reason = "metrics_ok"
        verdict = QualityVerdict.PASS
        
        # Override threshold if passed
        threshold = float(metadata.get("quality_gate_threshold", 50))
        if threshold <= 1.0:
            threshold = threshold * 100.0  # scale slider from 0.0-1.0
            
        if (metrics.text_density < threshold or is_corrupted) and parser_name != "pandas":
            if parser_name == "docling":
                verdict = QualityVerdict.FALLBACK
                if is_corrupted:
                    reason = "corrupted_font_encoding_detected_triggering_fallback"
                else:
                    reason = f"low_text_density_{metrics.text_density:.2f}_below_threshold_{threshold:.2f}_triggering_fallback"
            else:
                verdict = QualityVerdict.NEEDS_REVIEW
                if is_corrupted:
                    reason = "corrupted_font_encoding_detected_flagged_for_review"
                else:
                    reason = f"low_text_density_{metrics.text_density:.2f}_below_threshold_{threshold:.2f}_flagged_for_review"
            
            if "low_confidence_extraction" not in metrics.unverified_structures:
                metrics.unverified_structures.append("low_confidence_extraction")
            metrics.extraction_confidence_score = 0.3
            
        return verdict, metrics, reason
