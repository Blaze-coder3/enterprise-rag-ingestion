import hashlib
import tiktoken
from typing import List
from .base import BaseChunker, ChunkConfig
from ..core.models import CanonicalDocument, Chunk, ContentNode, NodeType

class SemanticChunker(BaseChunker):
    """
    Structure-aware semantic chunker with token-limit windows.
    Splits long paragraphs into overlapping chunks while preserving table integrity
    and section hierarchy.
    """
    
    def __init__(self):
        self.encoder = tiktoken.get_encoding("cl100k_base")
        
    def _count_tokens(self, text: str) -> int:
        return len(self.encoder.encode(text))
        
    def chunk(self, doc: CanonicalDocument, config: ChunkConfig) -> List[Chunk]:
        chunks: List[Chunk] = []
        chunk_idx = 0
        
        current_hierarchy: List[str] = []
        
        for node in doc.content_tree:
            if node.node_type == NodeType.HEADING:
                if current_hierarchy:
                    current_hierarchy[-1] = node.content
                else:
                    current_hierarchy.append(node.content)
                continue
                
            if node.node_type == NodeType.TABLE:
                # Find the corresponding TableNode for sticky-row chunking
                table_node = next((t for t in doc.tables if t.section_id == node.section_id), None)
                
                if table_node and len(table_node.rows) > 1:
                    headers = table_node.rows[0]
                    # Create a chunk for each row using sticky-row logic
                    for row_idx, row in enumerate(table_node.rows[1:], start=1):
                        row_dict = dict(zip(headers, row))
                        row_text = ", ".join(f"{k}: {v}" for k, v in row_dict.items())
                        
                        text_to_embed = f"Row {row_idx}: {row_text}"
                        if current_hierarchy:
                            text_to_embed = " > ".join(current_hierarchy) + "\n\n" + text_to_embed
                            
                        token_count = self._count_tokens(text_to_embed)
                        content_hash = hashlib.sha256(text_to_embed.encode()).hexdigest()
                        
                        chunk_id = hashlib.sha256(
                            f"{doc.tenant_id}_{doc.document_id}_{doc.version_id}_table_{node.section_id}_row_{row_idx}_{chunk_idx}".encode()
                        ).hexdigest()
                        
                        chunks.append(Chunk(
                            chunk_id=chunk_id,
                            document_id=doc.document_id,
                            version_id=doc.version_id,
                            tenant_id=doc.tenant_id,
                            collection_id=doc.collection_id,
                            content=text_to_embed,
                            content_hash=content_hash,
                            chunk_index=chunk_idx,
                            token_count=token_count,
                            page_numbers=[node.page_number],
                            bounding_boxes=[node.bounding_box] if node.bounding_box else [],
                            node_type="table_row",
                            section_hierarchy=list(current_hierarchy),
                            section_id=node.section_id,
                            access_groups=doc.access_groups,
                            embedding_model="",
                            embedding_version="",
                            document_domain=doc.document_domain,
                            effective_date=doc.effective_date,
                            expiration_date=doc.expiration_date,
                            jurisdiction=doc.jurisdiction,
                            compliance_tier=doc.compliance_tier,
                            contains_tables=doc.contains_tables,
                            unverified_structures=doc.parse_quality.unverified_structures,
                            is_malformed_flag=doc.is_malformed_flag
                        ))
                        chunk_idx += 1
                else:
                    # Fallback if no table node found or only headers
                    text_to_embed = node.content
                    if current_hierarchy:
                        text_to_embed = " > ".join(current_hierarchy) + "\n\n" + text_to_embed
                        
                    token_count = self._count_tokens(text_to_embed)
                    content_hash = hashlib.sha256(text_to_embed.encode()).hexdigest()
                    
                    chunk_id = hashlib.sha256(
                        f"{doc.tenant_id}_{doc.document_id}_{doc.version_id}_{chunk_idx}".encode()
                    ).hexdigest()
                    
                    chunks.append(Chunk(
                        chunk_id=chunk_id,
                        document_id=doc.document_id,
                        version_id=doc.version_id,
                        tenant_id=doc.tenant_id,
                        collection_id=doc.collection_id,
                        content=text_to_embed,
                        content_hash=content_hash,
                        chunk_index=chunk_idx,
                        token_count=token_count,
                        page_numbers=[node.page_number],
                        bounding_boxes=[node.bounding_box] if node.bounding_box else [],
                        node_type="table",
                        section_hierarchy=list(current_hierarchy),
                        section_id=node.section_id,
                        access_groups=doc.access_groups,
                        embedding_model="",
                        embedding_version="",
                        document_domain=doc.document_domain,
                        effective_date=doc.effective_date,
                        expiration_date=doc.expiration_date,
                        jurisdiction=doc.jurisdiction,
                        compliance_tier=doc.compliance_tier,
                        contains_tables=doc.contains_tables,
                        unverified_structures=doc.parse_quality.unverified_structures,
                        is_malformed_flag=doc.is_malformed_flag
                    ))
                    chunk_idx += 1
                continue
                
            # Paragraph handling
            text_to_embed = node.content
            if current_hierarchy:
                text_to_embed = " > ".join(current_hierarchy) + "\n\n" + text_to_embed
                
            # Token limit splitting
            tokens = self.encoder.encode(text_to_embed)
            
            if len(tokens) <= config.target_tokens:
                sub_chunks = [tokens]
            else:
                sub_chunks = []
                step = config.target_tokens - config.overlap_tokens
                if step <= 0:
                    step = 1
                for i in range(0, len(tokens), step):
                    sub_chunks.append(tokens[i:i + config.target_tokens])
            
            for sub_tokens in sub_chunks:
                sub_text = self.encoder.decode(sub_tokens)
                content_hash = hashlib.sha256(sub_text.encode()).hexdigest()
                chunk_id = hashlib.sha256(
                    f"{doc.tenant_id}_{doc.document_id}_{doc.version_id}_{chunk_idx}".encode()
                ).hexdigest()
                
                chunks.append(Chunk(
                    chunk_id=chunk_id,
                    document_id=doc.document_id,
                    version_id=doc.version_id,
                    tenant_id=doc.tenant_id,
                    collection_id=doc.collection_id,
                    content=sub_text,
                    content_hash=content_hash,
                    chunk_index=chunk_idx,
                    token_count=len(sub_tokens),
                    page_numbers=[node.page_number],
                    bounding_boxes=[node.bounding_box] if node.bounding_box else [],
                    node_type="paragraph",
                    section_hierarchy=list(current_hierarchy),
                    section_id=node.section_id,
                    access_groups=doc.access_groups,
                    embedding_model="",
                    embedding_version="",
                    document_domain=doc.document_domain,
                    effective_date=doc.effective_date,
                    expiration_date=doc.expiration_date,
                    jurisdiction=doc.jurisdiction,
                    compliance_tier=doc.compliance_tier,
                    contains_tables=doc.contains_tables,
                    unverified_structures=doc.parse_quality.unverified_structures,
                    is_malformed_flag=doc.is_malformed_flag
                ))
                chunk_idx += 1
            
        return chunks
