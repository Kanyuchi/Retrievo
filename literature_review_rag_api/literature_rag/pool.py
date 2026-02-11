"""Connection Pool Module for Literature RAG

Manages shared ChromaDB clients and embedding model instances.
Provides efficient resource sharing across requests and workers.
Supports OpenAI (API) embeddings only.
"""

import logging
import os
import threading
from dataclasses import dataclass
from typing import Optional, Dict, Any, Union
from weakref import WeakValueDictionary

import chromadb
from langchain_core.embeddings import Embeddings

logger = logging.getLogger(__name__)


@dataclass
class PoolConfig:
    """Configuration for the connection pool."""
    max_chroma_clients: int = 10  # Max ChromaDB client instances
    embedding_cache_size: int = 5  # Max embedding model instances
    # OpenAI settings
    default_openai_model: str = "text-embedding-3-small"


class EmbeddingPool:
    """Pool of embedding model instances.

    Supports OpenAI (API) embeddings only.
    This pool caches loaded models and shares them across requests.
    Thread-safe for concurrent access.
    """

    def __init__(
        self,
        max_size: int = 5,
        default_openai_model: str = "text-embedding-3-small"
    ):
        """Initialize embedding pool.

        Args:
            max_size: Maximum number of cached model instances
            default_openai_model: Default OpenAI model name
        """
        self._cache: Dict[str, Embeddings] = {}
        self._lock = threading.Lock()
        self._max_size = max_size
        self._access_order: list = []  # LRU tracking
        self._default_openai_model = default_openai_model

    def _make_cache_key(
        self,
        model_name: str
    ) -> str:
        """Create cache key for model instance."""
        return f"openai::{model_name}"

    def get_embeddings(
        self,
        openai_model: str = None,
        openai_api_key: str = None
    ) -> Embeddings:
        """Get or create an embedding model instance.

        Args:
            openai_model: OpenAI model name (default: text-embedding-3-small)
            openai_api_key: OpenAI API key (default: from environment)

        Returns:
            OpenAIEmbeddings instance
        """
        return self._get_openai_embeddings(openai_model, openai_api_key)

    def _get_openai_embeddings(
        self,
        model_name: str = None,
        api_key: str = None
    ) -> Embeddings:
        """Get or create an OpenAI embedding model instance."""
        model_name = model_name or self._default_openai_model
        cache_key = self._make_cache_key(model_name)

        # Get API key
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key required for embeddings.")

        with self._lock:
            # Check cache
            if cache_key in self._cache:
                # Update LRU order
                if cache_key in self._access_order:
                    self._access_order.remove(cache_key)
                self._access_order.append(cache_key)
                logger.debug(f"Embedding pool hit: {cache_key}")
                return self._cache[cache_key]

            # Evict LRU entry if at capacity
            if len(self._cache) >= self._max_size:
                lru_key = self._access_order.pop(0)
                del self._cache[lru_key]
                logger.info(f"Embedding pool eviction: {lru_key}")

            # Create new instance
            try:
                from langchain_openai import OpenAIEmbeddings

                logger.info(f"Initializing OpenAI embedding model: {model_name}")
                embeddings = OpenAIEmbeddings(
                    model=model_name,
                    openai_api_key=api_key
                )

                self._cache[cache_key] = embeddings
                self._access_order.append(cache_key)
                logger.info(f"OpenAI embedding model loaded. Pool size: {len(self._cache)}")

                return embeddings

            except ImportError as e:
                raise ImportError(
                    "langchain-openai required for OpenAI embeddings. "
                    "Install with: pip install langchain-openai"
                ) from e

    def clear(self):
        """Clear all cached embeddings."""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()
            logger.info("Embedding pool cleared")

    @property
    def size(self) -> int:
        """Current number of cached models."""
        return len(self._cache)

    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics."""
        with self._lock:
            return {
                "cached_models": len(self._cache),
                "max_size": self._max_size,
                "models": list(self._cache.keys()),
                "default_provider": "openai"
            }


class ChromaPool:
    """Pool of ChromaDB client connections.

    ChromaDB PersistentClient instances can be shared across requests.
    This pool manages client lifecycle and provides efficient reuse.
    """

    def __init__(self, max_clients: int = 10):
        """Initialize ChromaDB pool.

        Args:
            max_clients: Maximum number of client instances
        """
        self._clients: Dict[str, chromadb.PersistentClient] = {}
        self._lock = threading.Lock()
        self._max_clients = max_clients
        self._access_order: list = []

    def get_client(self, path: str) -> chromadb.PersistentClient:
        """Get or create a ChromaDB client for a path.

        Args:
            path: Path to ChromaDB persistence directory

        Returns:
            ChromaDB PersistentClient instance
        """
        with self._lock:
            # Check cache
            if path in self._clients:
                # Update LRU order
                if path in self._access_order:
                    self._access_order.remove(path)
                self._access_order.append(path)
                logger.debug(f"ChromaDB pool hit: {path}")
                return self._clients[path]

            # Evict LRU entry if at capacity
            if len(self._clients) >= self._max_clients:
                lru_path = self._access_order.pop(0)
                # ChromaDB doesn't require explicit close, but we remove reference
                del self._clients[lru_path]
                logger.info(f"ChromaDB pool eviction: {lru_path}")

            # Create new client
            logger.info(f"Creating ChromaDB client for: {path}")
            client = chromadb.PersistentClient(path=path)

            self._clients[path] = client
            self._access_order.append(path)
            logger.info(f"ChromaDB client created. Pool size: {len(self._clients)}")

            return client

    def clear(self):
        """Clear all cached clients."""
        with self._lock:
            self._clients.clear()
            self._access_order.clear()
            logger.info("ChromaDB pool cleared")

    @property
    def size(self) -> int:
        """Current number of cached clients."""
        return len(self._clients)

    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics."""
        with self._lock:
            return {
                "cached_clients": len(self._clients),
                "max_clients": self._max_clients,
                "paths": list(self._clients.keys())
            }


class ConnectionPool:
    """Unified connection pool for Literature RAG resources.

    Manages both embedding models and ChromaDB clients.
    Singleton pattern ensures single pool instance per process.
    """

    _instance: Optional["ConnectionPool"] = None
    _lock = threading.Lock()

    def __new__(cls, config: PoolConfig = None):
        """Singleton pattern for connection pool."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, config: PoolConfig = None):
        """Initialize connection pool.

        Args:
            config: Pool configuration
        """
        if self._initialized:
            return

        config = config or PoolConfig()

        self._embedding_pool = EmbeddingPool(
            max_size=config.embedding_cache_size,
            default_openai_model=config.default_openai_model
        )
        self._chroma_pool = ChromaPool(max_clients=config.max_chroma_clients)
        self._config = config
        self._initialized = True

        logger.info("Connection pool initialized")

    def get_embeddings(
        self,
        openai_model: str = None,
        openai_api_key: str = None
    ) -> Embeddings:
        """Get embedding model from pool."""
        return self._embedding_pool.get_embeddings(
            openai_model=openai_model or self._config.default_openai_model,
            openai_api_key=openai_api_key
        )

    def get_chroma_client(self, path: str) -> chromadb.PersistentClient:
        """Get ChromaDB client from pool."""
        return self._chroma_pool.get_client(path)

    def clear(self):
        """Clear all pools."""
        self._embedding_pool.clear()
        self._chroma_pool.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics."""
        return {
            "embeddings": self._embedding_pool.get_stats(),
            "chroma": self._chroma_pool.get_stats()
        }


# Global pool instance
_pool: Optional[ConnectionPool] = None


def get_pool(config: PoolConfig = None) -> ConnectionPool:
    """Get global connection pool instance.

    Args:
        config: Optional pool configuration (only used on first call)

    Returns:
        ConnectionPool singleton instance
    """
    global _pool
    if _pool is None:
        _pool = ConnectionPool(config)
    return _pool


def get_pooled_embeddings(
    openai_model: str = None,
    openai_api_key: str = None
) -> Embeddings:
    """Convenience function to get embeddings from global pool."""
    return get_pool().get_embeddings(
        openai_model=openai_model,
        openai_api_key=openai_api_key
    )


def get_pooled_chroma_client(path: str) -> chromadb.PersistentClient:
    """Convenience function to get ChromaDB client from global pool."""
    return get_pool().get_chroma_client(path)
