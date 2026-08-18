import pytest
from src.rag_pipeline.parsers.normalizer import DocumentNormalizer
from src.rag_pipeline.parsers.base import ParseResult
from src.rag_pipeline.core.models import ParseQualityMetrics, NodeType

def test_normalize_docling():
    normalizer = DocumentNormalizer()
    raw = {
        "texts": [
            {"label": "header", "text": "Title"},
            {"label": "paragraph", "text": "Some content"}
        ],
        "tables": []
    }
    parse_result = ParseResult(raw_output=raw, page_count=1)
    metrics = ParseQualityMetrics()
    
    doc = normalizer.normalize(
        document_id="d1", tenant_id="t1", version_id="v1", title="test",
        parse_result=parse_result, parser_name="docling", parser_version="1",
        quality_metrics=metrics, content_hash="hash", access_groups=[]
    )
    
    assert doc.document_id == "d1"
    assert len(doc.content_tree) == 2
    assert doc.content_tree[0].node_type == NodeType.HEADING
    assert doc.content_tree[1].node_type == NodeType.PARAGRAPH

def test_normalize_adi():
    normalizer = DocumentNormalizer()
    raw = {
        "paragraphs": [
            {"role": "title", "content": "Title"},
            {"role": "pageHeader", "content": "Skip this"},
            {"role": "paragraph", "content": "Some content"}
        ],
        "tables": []
    }
    parse_result = ParseResult(raw_output=raw, page_count=1)
    metrics = ParseQualityMetrics()
    
    doc = normalizer.normalize(
        document_id="d1", tenant_id="t1", version_id="v1", title="test",
        parse_result=parse_result, parser_name="azure_di", parser_version="1",
        quality_metrics=metrics, content_hash="hash", access_groups=[]
    )
    
    # pageHeader is skipped, so only 2 nodes should be present
    assert len(doc.content_tree) == 2
    assert doc.content_tree[0].node_type == NodeType.HEADING
    assert doc.content_tree[1].node_type == NodeType.PARAGRAPH
