import os
from typing import List, Optional
from pydantic import BaseModel
from ..observability.logging import get_logger

logger = get_logger("ragas_eval")

class RagasEvaluator:
    """Asynchronously evaluates chat turns using RAGAS."""
    
    async def evaluate_turn(self, tenant_id: str, conversation_id: str, message_id: str, question: str, answer: str, context_chunks: List[str], latency_ms: float):
        """Runs RAGAS metrics on the turn asynchronously."""
        # Only run if OpenAI API key is set (RAGAS requires an LLM-as-a-judge)
        if not os.getenv("OPENAI_API_KEY"):
            logger.info("Skipping RAGAS evaluation, OPENAI_API_KEY not set.")
            return

        try:
            from ragas.metrics import faithfulness, context_precision, answer_relevancy
            from ragas import evaluate
            from datasets import Dataset

            # Prepare dataset for RAGAS
            data = {
                "question": [question],
                "answer": [answer],
                "contexts": [context_chunks],
                "ground_truth": [""] # Optional, not always available in live RAG
            }
            dataset = Dataset.from_dict(data)

            # Evaluate
            result = evaluate(
                dataset,
                metrics=[
                    faithfulness,
                    answer_relevancy,
                    context_precision
                ],
                raise_exceptions=False
            )
            
            eval_metrics = result.to_pandas().to_dict(orient="records")[0]
            
            logger.info(
                "RAGAS Evaluation Complete",
                tenant_id=tenant_id,
                conversation_id=conversation_id,
                message_id=message_id,
                faithfulness=eval_metrics.get("faithfulness", 0),
                answer_relevancy=eval_metrics.get("answer_relevancy", 0),
                context_precision=eval_metrics.get("context_precision", 0)
            )
            
            # In a full implementation, you would save these metrics back to the SQLite State Ledger or a specialized metrics DB.
            
        except Exception as e:
            logger.error(f"RAGAS evaluation failed for {message_id}: {str(e)}")
