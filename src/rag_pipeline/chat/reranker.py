from typing import List, Dict, Any
from sentence_transformers import CrossEncoder

class CrossEncoderReranker:
    """
    Locally executed cross-encoder for reranking retrieval results.
    Much more accurate than bi-encoders because it performs full self-attention 
    across the query and the chunk simultaneously.
    """
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        # We load this lazily or in init depending on startup speed requirements.
        # For this demo, it's fine to load synchronously on init.
        self.model = CrossEncoder(model_name, max_length=512)
        
    def rerank(self, query: str, results: List[Dict[str, Any]], top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Takes hybrid search results from Qdrant, rescores them, and returns top_k.
        
        Args:
            query: The user's query
            results: List of Qdrant ScoredPoint dictionaries or similar structs
            top_k: How many to return after rescoring
        """
        if not results:
            return []
            
        # Prepare pairs for the CrossEncoder
        # We assume results is a list of dicts with a 'payload' containing 'content'
        pairs = []
        for res in results:
            content = res.get("payload", {}).get("content", "")
            pairs.append([query, content])
            
        # Predict scores
        scores = self.model.predict(pairs)
        
        # Attach scores and sort
        for i, res in enumerate(results):
            res["rerank_score"] = float(scores[i])
            
        # Sort descending by rerank_score
        reranked = sorted(results, key=lambda x: x["rerank_score"], reverse=True)
        
        return reranked[:top_k]
