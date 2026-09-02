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


def test_align_agent_models_xai_covers_all_roles():
    from literature_rag.llm import align_agent_models
    out = align_agent_models({"planning": {"temperature": 0.1}}, "xai-abc", "grok-4.20-non-reasoning")
    assert set(out) == {"planning", "evaluation", "validation", "generation"}
    assert all(v["model"] == "grok-4.20-non-reasoning" for v in out.values())
    assert out["planning"]["temperature"] == 0.1  # merged, not replaced


def test_align_agent_models_groq_untouched():
    from literature_rag.llm import align_agent_models
    src = {"generation": {"model": "llama-3.3-70b-versatile"}}
    assert align_agent_models(src, "gsk_abc", "llama-3.3-70b-versatile") == src
