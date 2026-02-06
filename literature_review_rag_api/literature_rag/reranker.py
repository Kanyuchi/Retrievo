"""Cross-encoder reranker utilities."""

from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


class CrossEncoderReranker:
    """Optional cross-encoder reranker for retrieval results."""

    def __init__(
        self,
        model_name: str = "BAAI/bge-reranker-base",
        device: Optional[str] = None,
        max_length: int = 512,
        batch_size: int = 32
    ):
        from sentence_transformers import CrossEncoder

        self.model_name = model_name
        self.device = device
        self.max_length = max_length
        self.batch_size = batch_size

        self._model = CrossEncoder(
            model_name,
            device=device,
            max_length=max_length
        )

        logger.info(f"Reranker initialized: {model_name} on {device or 'auto'}")

    def score(self, query: str, documents: List[str]) -> List[float]:
        """Score documents for a given query."""
        if not documents:
            return []
        pairs = [(query, doc) for doc in documents]
        return self._model.predict(pairs, batch_size=self.batch_size).tolist()
