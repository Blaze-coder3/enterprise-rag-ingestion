import pytest
from src.rag_pipeline.chunking.semantic import SemanticChunker
from src.rag_pipeline.chunking.base import ChunkConfig
from src.rag_pipeline.core.models import CanonicalDocument, ContentNode, NodeType

def test_semantic_chunker_splitting():
    chunker = SemanticChunker()
    # A chunk config that forces splitting
    config = ChunkConfig(target_tokens=10, overlap_tokens=2)
    
    # 25 words -> probably ~30 tokens
    long_text = "This is a very long paragraph that will definitely exceed the ten token limit we just set for this specific unit test case to ensure the chunker works."
    
    doc = CanonicalDocument(
        document_id="d1", tenant_id="t1", version_id="v1", title="test", page_count=1,
        parser_name="test", parser_version="1", content_hash="hash", access_groups=[]
    )
    doc.content_tree.append(ContentNode(
        node_type=NodeType.PARAGRAPH, content=long_text, page_number=1, section_id="s1"
    ))
    
    chunks = chunker.chunk(doc, config)
    
    assert len(chunks) > 1
    # Check that each chunk respects target_tokens (roughly)
    for c in chunks:
        assert c.token_count <= 10

def test_semantic_chunker_hierarchy():
    chunker = SemanticChunker()
    config = ChunkConfig()
    
    doc = CanonicalDocument(
        document_id="d1", tenant_id="t1", version_id="v1", title="test", page_count=1,
        parser_name="test", parser_version="1", content_hash="hash", access_groups=[]
    )
    doc.content_tree.extend([
        ContentNode(node_type=NodeType.HEADING, content="H1 Title", page_number=1, section_id="s1"),
        ContentNode(node_type=NodeType.PARAGRAPH, content="Content under H1", page_number=1, section_id="s2")
    ])
    
    chunks = chunker.chunk(doc, config)
    assert len(chunks) == 1
    assert chunks[0].section_hierarchy == ["H1 Title"]
    assert "H1 Title" in chunks[0].content

from src.rag_pipeline.core.models import TableNode

def test_spreadsheet_sticky_row_header_injection():
    chunker = SemanticChunker()
    config = ChunkConfig()
    
    doc = CanonicalDocument(
        document_id="d_tab", tenant_id="t1", version_id="v1", title="test", page_count=1,
        parser_name="test", parser_version="1", content_hash="hash", access_groups=[]
    )
    
    # 1. Arrange: Construct a table node with a header row and data row
    table_node = TableNode(
        section_id="s_tab",
        page_number=1,
        markdown="| Service | CopayThreshold |\n| --- | --- |\n| Primary Care | $20 |",
        rows=[
            ["Service", "CopayThreshold"],
            ["Primary Care", "$20"]
        ]
    )
    doc.tables.append(table_node)
    doc.content_tree.append(ContentNode(node_type=NodeType.TABLE, content="Raw table", page_number=1, section_id="s_tab"))
    
    # 2. Act: Generate smart chunks
    chunks = chunker.chunk(doc, config)
    
    # 3. Assert: Verify sticky row injection
    assert len(chunks) == 1
    assert "Service: Primary Care" in chunks[0].content
    assert "CopayThreshold: $20" in chunks[0].content
    assert chunks[0].node_type == "table_row"
