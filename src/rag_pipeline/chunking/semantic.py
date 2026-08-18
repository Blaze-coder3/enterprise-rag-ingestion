import hashlib
import tiktoken
from typing import List
from .base import BaseChunker, ChunkConfig
from ..core.models import CanonicalDocument, Chunk, ContentNode, NodeType

class SemanticChunker(BaseChunker):
    """Structure-aware semantic chunker."""
    
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
                # In a real impl, we'd check heading level to manage the hierarchy stack
                # For this demo, just replace the last item or append
                if current_hierarchy:
                    current_hierarchy[-1] = node.content
                else:
                    current_hierarchy.append(node.content)
                continue
                
            if node.node_type == NodeType.TABLE:
                # Handled by table chunker or simplified here
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
                    embedding_model="", # populated later
                    embedding_version="" # populated later
                ))
                chunk_idx += 1
                continue
                
            # Paragraph handling
            text_to_embed = node.content
            if current_hierarchy:
                text_to_embed = " > ".join(current_hierarchy) + "\n\n" + text_to_embed
                
            token_count = self._count_tokens(text_to_embed)
            
            # If a single paragraph is too long, we should split it.
            # Simplified for demo: just make it one chunk.
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
                node_type="paragraph",
                section_hierarchy=list(current_hierarchy),
                section_id=node.section_id,
                embedding_model="", # populated later
                embedding_version="" # populated later
            ))
            chunk_idx += 1
            
        return chunks
