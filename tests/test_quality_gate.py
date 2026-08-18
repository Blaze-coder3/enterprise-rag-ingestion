import pytest
from src.rag_pipeline.parsers.router import ParserRouter
from src.rag_pipeline.parsers.base import ParseResult
from src.rag_pipeline.core.models import QualityVerdict

def test_quality_gate_pass():
    router = ParserRouter()
    # High text density
    raw = {"texts": [{"text": "A" * 100}]}
    result = ParseResult(raw_output=raw, page_count=1)
    
    verdict, metrics, reason = router.quality_gate(result, "docling")
    assert verdict == QualityVerdict.PASS
    assert metrics.text_density == 100.0

def test_quality_gate_fallback():
    router = ParserRouter()
    # Low text density for Docling triggers fallback
    raw = {"texts": [{"text": "A" * 10}]}
    result = ParseResult(raw_output=raw, page_count=1)
    
    verdict, metrics, reason = router.quality_gate(result, "docling")
    assert verdict == QualityVerdict.FALLBACK

def test_quality_gate_needs_review():
    router = ParserRouter()
    # Low text density for ADI (fallback parser) triggers needs_review
    raw = {"paragraphs": [{"content": "A" * 10}]}
    result = ParseResult(raw_output=raw, page_count=1)
    
    verdict, metrics, reason = router.quality_gate(result, "azure_di")
    assert verdict == QualityVerdict.NEEDS_REVIEW
