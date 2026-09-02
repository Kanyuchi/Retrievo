"""Chat LLM factory picks the provider by key prefix."""


def test_xai_key_gets_openai_client_with_xai_base():
    from literature_rag.llm import get_chat_client, resolve_chat_model, XAI_BASE_URL
    client = get_chat_client("xai-" + "k" * 40)
    assert XAI_BASE_URL in str(client.base_url)
    assert hasattr(client.chat.completions, "create")
    assert resolve_chat_model("xai-abc", "llama-3.3-70b").startswith("grok")


def test_gsk_key_gets_groq_client():
    from literature_rag.llm import get_chat_client, resolve_chat_model
    client = get_chat_client("gsk_" + "k" * 40)
    assert type(client).__module__.startswith("groq")
    assert hasattr(client.chat.completions, "create")
    assert resolve_chat_model("gsk_abc", "llama-3.3-70b") == "llama-3.3-70b"
