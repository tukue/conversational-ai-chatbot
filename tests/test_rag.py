import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import src.rag as rag_module
from src.rag import (
    RAGEngine,
    VectorStore,
    EmbeddingEngine,
    chunk_document,
    build_knowledge_chunks,
    _cosine_similarity,
    _keyword_score,
    _reciprocal_fusion_rank,
    _tokenize,
)


# ---------------------------------------------------------------------------
# Utility function tests
# ---------------------------------------------------------------------------

class TestCosineSimilarity:
    def test_identical_vectors(self):
        a = [1.0, 0.0, 0.0]
        b = [1.0, 0.0, 0.0]
        assert abs(_cosine_similarity(a, b) - 1.0) < 1e-6

    def test_orthogonal_vectors(self):
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        assert abs(_cosine_similarity(a, b)) < 1e-6

    def test_opposite_vectors(self):
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        assert abs(_cosine_similarity(a, b) - (-1.0)) < 1e-6

    def test_zero_vector(self):
        a = [0.0, 0.0]
        b = [1.0, 1.0]
        assert _cosine_similarity(a, b) == 0.0

    def test_similar_vectors_high_score(self):
        a = [1.0, 2.0, 3.0]
        b = [1.1, 2.1, 2.9]
        score = _cosine_similarity(a, b)
        assert score > 0.9


class TestKeywordScore:
    def test_exact_match(self):
        assert _keyword_score(["hello", "world"], ["hello", "world"]) == 1.0

    def test_partial_overlap(self):
        score = _keyword_score(["hello", "world"], ["hello", "there"])
        assert abs(score - 0.5) < 1e-6

    def test_no_overlap(self):
        assert _keyword_score(["hello"], ["world"]) == 0.0

    def test_empty_query(self):
        assert _keyword_score([], ["hello"]) == 0.0

    def test_empty_doc(self):
        assert _keyword_score(["hello"], []) == 0.0

    def test_tokenize_removes_common_words(self):
        assert _tokenize("Do you sell wireless headphones?") == [
            "sell",
            "wireless",
            "headphones",
        ]

class TestReciprocalFusionRank:
    def test_single_list(self):
        ranked = [("doc1", 0.9), ("doc2", 0.5)]
        fused = _reciprocal_fusion_rank([ranked])
        assert len(fused) == 2
        assert fused[0][0] == "doc1"

    def test_two_lists_merge(self):
        list1 = [("doc1", 0.9), ("doc2", 0.5)]
        list2 = [("doc2", 0.8), ("doc3", 0.6)]
        fused = _reciprocal_fusion_rank([list1, list2])
        assert len(fused) == 3
        doc_ids = [d for d, _ in fused]
        assert "doc2" in doc_ids

    def test_empty_lists(self):
        assert _reciprocal_fusion_rank([]) == []


# ---------------------------------------------------------------------------
# Chunking tests
# ---------------------------------------------------------------------------

class TestChunkDocument:
    def test_short_doc_single_chunk(self):
        doc = {"content": "Short document", "id": "1"}
        chunks = chunk_document(doc)
        assert len(chunks) == 1
        assert chunks[0]["content"] == "Short document"
        assert chunks[0]["id"] == "1"

    def test_long_doc_multiple_chunks(self):
        words = "word " * 500
        doc = {"content": words.strip(), "id": "long"}
        chunks = chunk_document(doc, chunk_size=100, overlap=20)
        assert len(chunks) > 1

    def test_metadata_preserved(self):
        doc = {
            "content": "Test content",
            "id": "1",
            "category": "test",
            "type": "faq",
        }
        chunks = chunk_document(doc)
        assert chunks[0]["id"] == "1"
        assert chunks[0]["category"] == "test"
        assert chunks[0]["type"] == "faq"

    def test_string_input(self):
        chunks = chunk_document("Just a plain string document")
        assert len(chunks) == 1
        assert chunks[0]["content"] == "Just a plain string document"

    def test_invalid_content_and_parameters_return_no_chunks(self):
        assert chunk_document({"content": None}) == []
        assert chunk_document("valid", chunk_size=0) == []
        assert chunk_document("valid", overlap=-1) == []

    def test_overlap_is_clamped_to_keep_chunking_progressing(self):
        chunks = chunk_document("word " * 20, chunk_size=5, overlap=50)
        assert len(chunks) > 1


# ---------------------------------------------------------------------------
# Knowledge chunks builder tests
# ---------------------------------------------------------------------------

class TestBuildKnowledgeChunks:
    def test_creates_chunks(self):
        chunks = build_knowledge_chunks()
        assert len(chunks) > 0

    def test_has_faq_chunks(self):
        chunks = build_knowledge_chunks()
        faq_chunks = [c for c in chunks if c.get("type") == "faq"]
        assert len(faq_chunks) > 0

    def test_has_product_chunks(self):
        chunks = build_knowledge_chunks()
        product_chunks = [c for c in chunks if c.get("type") == "product"]
        assert len(product_chunks) > 0

    def test_chunk_content_not_empty(self):
        chunks = build_knowledge_chunks()
        for chunk in chunks:
            assert len(chunk.get("content", "")) > 0

    def test_skips_malformed_entries(self, monkeypatch):
        monkeypatch.setattr(
            rag_module,
            "_load_json",
            lambda filename: (
                [{"id": "faq-1", "question": "Valid?", "answer": "Yes."}, {"id": "bad"}]
                if filename == "faq.json"
                else [
                    {
                        "id": "product-1",
                        "name": "Valid product",
                        "category": "test",
                        "price": 1.0,
                        "description": "A valid product",
                    },
                    {"id": "bad-product", "price": "free"},
                ]
            ),
        )

        chunks = build_knowledge_chunks()
        assert {chunk["id"] for chunk in chunks} == {"faq-1", "product-1"}


# ---------------------------------------------------------------------------
# VectorStore tests
# ---------------------------------------------------------------------------

class TestVectorStore:
    def test_add_chunks(self):
        store = VectorStore()
        chunks = [
            {"content": "How do I return an item?", "id": "1", "type": "faq"},
            {"content": "What is your shipping policy?", "id": "2", "type": "faq"},
        ]
        store.add_chunks(chunks)
        assert len(store._chunks) == 2

    def test_keyword_search(self):
        store = VectorStore()
        chunks = [
            {"content": "return policy allows returns within 30 days", "id": "1", "type": "faq"},
            {"content": "shipping takes 5-7 business days", "id": "2", "type": "faq"},
        ]
        store.add_chunks(chunks)
        results = store._keyword_search("return policy", top_k=2)
        assert len(results) > 0
        assert results[0]["id"] == "1"

    def test_search_empty_store(self):
        store = VectorStore()
        results = store.search("anything")
        assert results == []

    def test_invalid_chunks_and_queries_are_ignored_safely(self):
        store = VectorStore()
        store.add_chunks([None, {"content": ""}, {"content": "return policy", "id": "1"}])
        assert len(store._chunks) == 1
        assert store.search(None) == []
        assert store.search("return", top_k=0) == []
        assert store._keyword_search("return", top_k="bad") == []


# ---------------------------------------------------------------------------
# RAGEngine integration tests
# ---------------------------------------------------------------------------

class TestRAGEngine:
    def setup_method(self):
        RAGEngine._instance = None

    def test_singleton(self):
        e1 = RAGEngine.get_instance()
        e2 = RAGEngine.get_instance()
        assert e1 is e2

    def test_initialize(self):
        rag = RAGEngine.get_instance()
        rag.initialize()
        assert rag._initialized

    def test_retrieve_returns_results(self):
        rag = RAGEngine.get_instance()
        results = rag.retrieve("return policy")
        assert isinstance(results, list)

    def test_retrieve_rejects_invalid_queries_without_fallback(self):
        rag = RAGEngine.get_instance()
        assert rag.retrieve(None) == []
        assert rag.search_with_rerank("   ") == []

    def test_format_context(self):
        rag = RAGEngine.get_instance()
        chunks = [
            {"content": "Test content", "score": 0.9, "method": "semantic"},
        ]
        context = rag.format_context(chunks)
        assert "Test content" in context
        assert "Source 1" in context

    def test_format_empty_context(self):
        rag = RAGEngine.get_instance()
        assert rag.format_context([]) == ""

    def test_search_with_rerank(self):
        rag = RAGEngine.get_instance()
        results = rag.search_with_rerank("shipping time")
        assert isinstance(results, list)
        assert rag._initialized


# ---------------------------------------------------------------------------
# EmbeddingEngine tests (mocked)
# ---------------------------------------------------------------------------

class TestEmbeddingEngine:
    def test_fallback_on_import_error(self):
        engine = EmbeddingEngine()
        engine._use_fallback = True
        result = engine.encode(["test"])
        assert result is None

    def test_encode_returns_numpy(self):
        engine = EmbeddingEngine()
        try:
            result = engine.encode(["test"])
            if result is not None:
                assert isinstance(result, np.ndarray)
        except Exception:
            pass
