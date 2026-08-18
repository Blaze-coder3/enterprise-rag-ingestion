from src.rag_pipeline.parsers.router import ParserRouter
from src.rag_pipeline.parsers.base import ParseResult
from src.rag_pipeline.core.models import QualityVerdict

def test_low_confidence_triggers_needs_review():
    # 1. Arrange: Setup router and a mocked parse result with low text density
    router = ParserRouter()
    
    # Mocking a parser output that has no text (0 density)
    mock_raw_output = {
        "paragraphs": [{"content": ""}], # empty text
        "tables": [],
        "source": "azure_di"
    }
    mock_result = ParseResult(raw_output=mock_raw_output, page_count=1)
    
    # 2. Act: Pass it through the quality gate
    verdict, metrics, reason = router.quality_gate(mock_result, "azure_di")
    
    # 3. Assert: Verify it flagged for review and appended the unverified tag
    assert verdict == QualityVerdict.NEEDS_REVIEW
    assert "flagged_for_review" in reason
    assert "low_confidence_extraction" in metrics.unverified_structures
    assert metrics.extraction_confidence_score == 0.3

def test_high_confidence_passes_gate():
    # 1. Arrange: Setup high density text
    router = ParserRouter()
    mock_raw_output = {
        "texts": [{"text": "A" * 500}], # high density
        "tables": [],
        "source": "docling"
    }
    mock_result = ParseResult(raw_output=mock_raw_output, page_count=1)
    
    # 2. Act
    verdict, metrics, reason = router.quality_gate(mock_result, "docling")
    
    # 3. Assert
    assert verdict == QualityVerdict.PASS
    assert reason == "metrics_ok"

def test_corrupted_font_triggers_fallback():
    # 1. Arrange: Setup router and docling output with repeating placeholders (e.g. TTTTTTTT)
    router = ParserRouter()
    mock_raw_output = {
        "texts": [
            {"text": "Normal text that has a high density, but then contains corrupted math symbols and repeats:"},
            {"text": "Column L Allocation Share 𝐴𝐴𝐴𝐴𝐴𝐴𝐴𝐴𝐴𝐴𝐴𝐴 𝑈𝑈𝑈𝑈𝑈𝑈𝑈 = 𝑇𝑇𝑇𝑇 2 𝑈𝑈𝑈𝑈 + ( 𝐷𝐷𝐷𝐷𝐷 - 𝑇𝑇𝑇𝑇 2 𝑇𝑇𝑇𝑇 ) ∗ 𝑃𝑃𝑃𝑃𝑃"}
        ],
        "tables": [],
        "source": "docling"
    }
    mock_result = ParseResult(raw_output=mock_raw_output, page_count=1)
    
    # 2. Act: Pass it through the quality gate
    verdict, metrics, reason = router.quality_gate(mock_result, "docling")
    
    # 3. Assert: Verify it triggers fallback due to corrupted font detection
    assert verdict == QualityVerdict.FALLBACK
    assert reason == "corrupted_font_encoding_detected_triggering_fallback"
    assert "corrupted_font_encoding" in metrics.unverified_structures
    assert metrics.extraction_confidence_score == 0.3
