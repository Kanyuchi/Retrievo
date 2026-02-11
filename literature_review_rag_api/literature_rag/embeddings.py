"""Unified Embedding Provider Interface

Provides a consistent interface for OpenAI (API) embeddings only.

Usage:
    from literature_rag.embeddings import get_embeddings
    from literature_rag.config import load_config

    config = load_config()
    embeddings = get_embeddings(config.embedding)

    # Use for embedding queries
    query_vector = embeddings.embed_query("What is business formation?")

    # Use for embedding documents
    doc_vectors = embeddings.embed_documents(["doc1 text", "doc2 text"])
"""

import logging
import os
from typing import Union

from langchain_core.embeddings import Embeddings

from .config import EmbeddingConfig

logger = logging.getLogger(__name__)

# Embedding dimensions by model
EMBEDDING_DIMENSIONS = {
    # OpenAI models
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
}


def get_embedding_dimension(config: EmbeddingConfig) -> int:
    """Get the embedding dimension for the configured provider and model.

    Args:
        config: EmbeddingConfig with provider and model settings

    Returns:
        Embedding dimension as integer
    """
    return EMBEDDING_DIMENSIONS.get(config.openai_model, 1536)


def get_embeddings(
    config: Union[EmbeddingConfig, dict],
) -> Embeddings:
    """Get embedding model instance based on configuration.

    Uses OpenAI embeddings only.

    Args:
        config: EmbeddingConfig object or dict with embedding settings

    Returns:
        OpenAIEmbeddings instance

    Raises:
        ValueError: If required API key is missing
    """
    # Handle dict config (for backward compatibility)
    if isinstance(config, dict):
        config = _dict_to_embedding_config(config)

    return _get_openai_embeddings(config)


def _get_openai_embeddings(config: EmbeddingConfig) -> Embeddings:
    """Get OpenAI embeddings instance.

    Args:
        config: EmbeddingConfig with OpenAI settings

    Returns:
        OpenAIEmbeddings
    """
    # Check for API key
    api_key = config.openai_api_key or os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise ValueError(
            "OpenAI API key required for OpenAI embeddings. "
            "Set OPENAI_API_KEY environment variable or config.openai_api_key."
        )

    try:
        from langchain_openai import OpenAIEmbeddings

        model = config.openai_model or "text-embedding-3-small"
        dimension = EMBEDDING_DIMENSIONS.get(model, 1536)

        logger.info(f"Initializing OpenAI embeddings: {model} ({dimension} dimensions)")

        embeddings = OpenAIEmbeddings(
            model=model,
            openai_api_key=api_key,
            # OpenAI's embedding API handles batching internally
        )

        logger.info("OpenAI embeddings initialized successfully")
        return embeddings

    except ImportError as e:
        raise ImportError(
            "langchain-openai required for OpenAI embeddings. "
            "Install with: pip install langchain-openai"
        ) from e


def _dict_to_embedding_config(config_dict: dict) -> EmbeddingConfig:
    """Convert dict to EmbeddingConfig for backward compatibility.

    Args:
        config_dict: Dictionary with embedding configuration

    Returns:
        EmbeddingConfig object
    """
    return EmbeddingConfig(
        provider="openai",
        strict_provider=True,
        openai_model=config_dict.get("openai_model", "text-embedding-3-small"),
        openai_api_key=config_dict.get("openai_api_key"),
        batch_size=config_dict.get("batch_size", 32),
        cache_folder=None
    )


def get_embedding_info(embeddings: Embeddings) -> dict:
    """Get information about an embeddings instance.

    Args:
        embeddings: Embeddings instance

    Returns:
        Dict with provider, model, and dimension info
    """
    # Detect provider type
    class_name = embeddings.__class__.__name__

    if "OpenAI" in class_name:
        model = getattr(embeddings, "model", "text-embedding-3-small")
        return {
            "provider": "openai",
            "model": model,
            "dimension": EMBEDDING_DIMENSIONS.get(model, 1536)
        }
    model = getattr(embeddings, "model", "text-embedding-3-small")
    return {
        "provider": "openai",
        "model": model,
        "dimension": EMBEDDING_DIMENSIONS.get(model, 1536)
    }
