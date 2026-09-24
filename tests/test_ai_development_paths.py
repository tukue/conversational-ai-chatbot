"""Regression coverage for AI routing, retrieval, and model operational paths."""

from types import SimpleNamespace
from unittest.mock import MagicMock
import sys

import numpy as np

from src import chatbot
from src import model as model_module
from src.rag import EmbeddingEngine, RAGEngine, VectorStore
from src.intent import _fuzzy_match, _levenshtein, _word_boundary_match, classify_intent


def test_chatbot_helpers_cover_cached_services_and_history(monkeypatch):
    chatbot._faq = chatbot._products = chatbot._rag = None
    assert chatbot._history_pairs([]) == []
    assert chatbot._history_pairs([
        {"role": "user", "content": "one"},
        {"role": "assistant", "content": "two"},
    ]) == [("one", "two")]
    assert chatbot._extract_order_number("Order AB-12345") == "AB-12345"
    assert chatbot._find_order_in_history([("Order 12345", "ok")]) == "12345"
    assert chatbot._suggestion("unknown") is None


def test_rag_retrieve_and_response_building_paths(monkeypatch):
    fake_rag = MagicMock()
    monkeypatch.setattr(chatbot, "_rag", fake_rag)
    monkeypatch.setattr(chatbot.config, "ENABLE_RAG", True)
    monkeypatch.setattr(chatbot.config, "RAG_RERANK", True)
    chatbot._rag_retrieve("shipping")
    fake_rag.search_with_rerank.assert_called_once()
    monkeypatch.setattr(chatbot.config, "RAG_RERANK", False)
    chatbot._rag_retrieve("shipping")
    fake_rag.retrieve.assert_called_once()
    monkeypatch.setattr(chatbot.config, "ENABLE_RAG", False)
    assert chatbot._rag_retrieve("shipping") == []

    assert chatbot._build_rag_response("q", []) is None
    assert chatbot._build_rag_response("q", [{"type": "faq", "content": "Answer: Yes"}]) == "Yes"
    assert "Product ID: P1" in chatbot._build_rag_response(
        "q", [{"type": "product", "id": "P1", "content": "Product"}]
    )
    assert chatbot._build_rag_response("q", [{"content": "other"}]) == "other"


def test_conversation_and_dialogpt_failure_paths(monkeypatch):
    chatbot.tokenizer = SimpleNamespace(eos_token="<eos>")
    monkeypatch.setattr(chatbot.config, "ENABLE_SANDWICH_DEFENSE", False)
    assert chatbot.build_conversation("now", [("before", "reply")]) == "before<eos>reply<eos>now<eos>"
    monkeypatch.setattr(chatbot.config, "ENABLE_SANDWICH_DEFENSE", True)
    monkeypatch.setattr(chatbot, "wrap_with_sandwich_defense", lambda value: "wrapped:" + value)
    assert chatbot.build_conversation("now", []).startswith("wrapped:now")
    monkeypatch.setattr(chatbot, "ensure_model_loaded", lambda: (_ for _ in ()).throw(RuntimeError()))
    assert "Could you share" in chatbot.respond_with_dialogpt("help", [])


def test_chat_routes_rag_rejection_and_product_catalog_fallback(monkeypatch):
    monkeypatch.setattr(chatbot.config, "ENABLE_RATE_LIMITING", False)
    monkeypatch.setattr(chatbot, "sanitize_input", lambda value: value)
    monkeypatch.setattr(chatbot, "check_input", lambda value: (True, ""))
    monkeypatch.setattr(chatbot, "is_on_topic", lambda value: True)
    monkeypatch.setattr(chatbot, "classify_intent", lambda value: "return_request")
    monkeypatch.setattr(chatbot, "_rag_retrieve", lambda value: [{"type": "faq", "content": "Answer: safe"}])
    monkeypatch.setattr(chatbot, "check_output", lambda response, message: (False, response))
    assert chatbot.chat("return", []) == chatbot.get_template("escalate")

    monkeypatch.setattr(chatbot, "classify_intent", lambda value: "product_inquiry")
    monkeypatch.setattr(chatbot, "_rag_retrieve", lambda value: [])
    monkeypatch.setattr(chatbot, "_products", SimpleNamespace(search=lambda value: [{
        "name": "Widget", "price": 1.0, "description": "Useful", "in_stock": False, "id": "P1"
    }]))
    monkeypatch.setattr(chatbot, "check_output", lambda response, message: (True, response))
    assert "Currently out of stock" in chatbot.chat("product", [])


def test_vector_store_semantic_and_keyword_fallback_paths():
    store = VectorStore()
    store.add_chunks([{"id": "one", "content": "returns"}, {"id": "two", "content": "shipping"}])
    store._embedding_engine = SimpleNamespace(encode=lambda texts: np.array([[1.0, 0.0], [0.0, 1.0]]) if isinstance(texts, list) else np.array([1.0, 0.0]))
    store.build_index()
    assert store.search("returns", 1)[0]["method"] == "semantic"
    store._embedding_engine = SimpleNamespace(encode=lambda texts: None)
    assert store._semantic_search("returns", 1)[0]["method"] == "keyword"


def test_rag_fallback_and_rerank_paths(monkeypatch):
    rag = RAGEngine()
    rag._initialized = True
    rag._store = SimpleNamespace(
        search=lambda query, top_k: [],
        _keyword_search=lambda query, top_k: [],
    )
    assert isinstance(rag.retrieve("return"), list)
    rag._store = SimpleNamespace(
        search=lambda query, top_k: [{"id": "a", "content": "A", "score": 1}],
        _keyword_search=lambda query, top_k: [{"id": "b", "content": "B", "score": 1}],
    )
    assert len(rag.search_with_rerank("query", 2)) == 2


def test_embedding_engine_uses_preloaded_model():
    engine = EmbeddingEngine()
    engine._model = MagicMock()
    engine._model.encode.return_value = np.array([[1.0]])
    assert engine.encode("query").shape == (1, 1)


def test_model_load_model_cpu_and_cuda_paths(monkeypatch):
    tokenizer = SimpleNamespace(pad_token=None, eos_token="</s>")
    model = MagicMock()
    tokenizer_cls = MagicMock(from_pretrained=MagicMock(return_value=tokenizer))
    model_cls = MagicMock(from_pretrained=MagicMock(return_value=model))
    monkeypatch.setattr(model_module, "AutoTokenizer", tokenizer_cls)
    monkeypatch.setattr(model_module, "AutoModelForCausalLM", model_cls)
    monkeypatch.setattr(model_module.config, "DEVICE", "cpu")
    loaded_tokenizer, loaded_model = model_module.load_model()
    assert loaded_tokenizer.pad_token == "</s>"
    assert loaded_model is model


def test_model_loads_dependencies_and_cuda_options(monkeypatch):
    tokenizer = SimpleNamespace(pad_token="pad", eos_token="</s>")
    model = MagicMock()
    tokenizer_cls = MagicMock(from_pretrained=MagicMock(return_value=tokenizer))
    model_cls = MagicMock(from_pretrained=MagicMock(return_value=model))
    monkeypatch.setattr(model_module, "AutoTokenizer", None)
    monkeypatch.setattr(model_module, "AutoModelForCausalLM", None)
    monkeypatch.setitem(sys.modules, "transformers", SimpleNamespace(
        AutoTokenizer=tokenizer_cls, AutoModelForCausalLM=model_cls
    ))
    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace(float16="fp16"))
    monkeypatch.setattr(model_module.config, "DEVICE", "cuda")
    model_module.load_model()
    assert model_cls.from_pretrained.call_args.kwargs["torch_dtype"] == "fp16"


def test_intent_helper_edge_cases_are_covered():
    assert not _word_boundary_match("", "hello")
    assert _levenshtein("a", "abc") == 2
    assert not _fuzzy_match("shipping", "", 0.8)
    assert classify_intent("") == "general"
    assert classify_intent("shippng time") == "shipping_info"


def test_chat_operational_and_fallback_routes(monkeypatch):
    monkeypatch.setattr(chatbot, "sanitize_input", lambda value: value)
    monkeypatch.setattr(chatbot, "check_input", lambda value: (True, ""))
    monkeypatch.setattr(chatbot, "is_on_topic", lambda value: True)
    monkeypatch.setattr(chatbot, "check_output", lambda response, message: (True, response))
    monkeypatch.setattr(chatbot.config, "ENABLE_RATE_LIMITING", True)
    monkeypatch.setattr(chatbot, "check_rate_limit", lambda history: (False, 3))
    assert "wait 3" in chatbot.chat("help", [])
    monkeypatch.setattr(chatbot.config, "ENABLE_RATE_LIMITING", False)

    monkeypatch.setattr(chatbot, "classify_intent", lambda value: "payment_issue")
    assert chatbot.chat("payment", []) == chatbot.get_template("payment_issue")
    monkeypatch.setattr(chatbot, "classify_intent", lambda value: "order_status")
    assert "order number" in chatbot.chat("order", [])
    monkeypatch.setattr(chatbot, "classify_intent", lambda value: "general")
    monkeypatch.setattr(chatbot.config, "ENABLE_GENERATIVE_FALLBACK", False)
    assert chatbot.chat("general", []) == chatbot.get_template("general")
    monkeypatch.setattr(chatbot.config, "ENABLE_GENERATIVE_FALLBACK", True)
    monkeypatch.setattr(chatbot, "respond_with_dialogpt", lambda message, history: "generated")
    assert chatbot.chat("general", []) == "generated"
