from src.rag_pipeline.parsers.router import ParserRouter
from src.rag_pipeline.parsers.pandas_adapter import PandasAdapter
from src.rag_pipeline.parsers.bs4_adapter import BS4Adapter
from src.rag_pipeline.parsers.docling_adapter import DoclingAdapter

def test_router_selects_pandas_for_spreadsheet():
    router = ParserRouter()
    parser, signals = router.select_parser("financials.xlsx", b"dummy_bytes")
    
    assert isinstance(parser, PandasAdapter)
    assert signals["decision"] == "pandas"
    assert signals["reason"] == "spreadsheet format detected"

def test_router_selects_bs4_for_html():
    router = ParserRouter()
    parser, signals = router.select_parser("index.html", b"dummy_bytes")
    
    assert isinstance(parser, BS4Adapter)
    assert signals["decision"] == "bs4"
    assert signals["reason"] == "html format detected"

def test_router_selects_docling_for_pdf_by_default():
    router = ParserRouter()
    parser, signals = router.select_parser("policy.pdf", b"dummy_bytes")
    
    assert isinstance(parser, DoclingAdapter)
    assert signals["decision"] == "docling"
    assert signals["reason"] == "default parser for .pdf"
