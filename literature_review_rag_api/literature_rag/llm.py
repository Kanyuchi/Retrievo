"""Chat-LLM client factory.

The app historically speaks to Groq; Shaun's key is xAI (Grok). Both are
OpenAI-compatible, and the agentic pipeline only needs an object exposing
`.chat.completions.create`, so we pick the client by key prefix:
  xai-…  -> openai.OpenAI against https://api.x.ai/v1 (model overridden)
  else   -> groq.Groq (native)
"""
import logging
import os

logger = logging.getLogger(__name__)

XAI_BASE_URL = "https://api.x.ai/v1"
XAI_DEFAULT_MODEL = "grok-4.20-non-reasoning"


def is_xai_key(api_key: str) -> bool:
    return bool(api_key) and api_key.startswith("xai-")


def resolve_chat_model(api_key: str, configured_model: str) -> str:
    """The model that matches the key's provider."""
    if is_xai_key(api_key):
        return os.getenv("LLM_MODEL", XAI_DEFAULT_MODEL)
    return configured_model


def get_chat_client(api_key: str):
    """OpenAI-compatible chat client for the given key's provider."""
    if is_xai_key(api_key):
        from openai import OpenAI
        logger.info("Chat LLM provider: xAI (Grok)")
        return OpenAI(api_key=api_key, base_url=XAI_BASE_URL)
    from groq import Groq
    logger.info("Chat LLM provider: Groq")
    return Groq(api_key=api_key)
