import json
import os
import re
import logging
import numpy as np

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
EMBEDDING_MODEL = os.getenv(
    "RAG_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
)
TOP_K_RESULTS = int(os.getenv("RAG_TOP_K", "5"))
SIMILARITY_THRESHOLD = float(os.getenv("RAG_SIMILARITY_THRESHOLD", "0.3"))
RRF_K = int(os.getenv("RAG_RRF_K", "60"))


def _load_json(filename):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return []
    with open(path, "r") as f:
        return json.load(f)


def _tokenize(text):
    return re.findall(r"[a-z0-9]+", text.lower())


def _cosine_similarity(a, b):
    a = np.asarray(a, dtype=np.float32)
    b = np.asarray(b, dtype=np.float32)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def _keyword_score(query_tokens, doc_tokens):
    if not query_tokens or not doc_tokens:
        return 0.0
    query_set = set(query_tokens)
    doc_set = set(doc_tokens)
    intersection = query_set & doc_set
    return len(intersection) / max(len(query_set), len(doc_set))


def _reciprocal_fusion_rank(scores, k=60):
    """Reciprocal Rank Fusion: combine multiple score lists into a single ranking."""
    fused = {}
    for rank_list in scores:
        for rank, (doc_id, score) in enumerate(rank_list, start=1):
            if doc_id not in fused:
                fused[doc_id] = 0.0
            fused[doc_id] += 1.0 / (k + rank)
    return sorted(fused.items(), key=lambda x: x[1], reverse=True)


class EmbeddingEngine:
    """Lazy-loading sentence transformer for RAG embeddings."""

    def __init__(self):
        self._model = None
        self._use_fallback = False

    def _load_model(self):
        if self._model is not None:
            return
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(EMBEDDING_MODEL)
            logger.info("Loaded embedding model: %s", EMBEDDING_MODEL)
        except ImportError:
            logger.warning(
                "sentence-transformers not installed. "
                "Falling back to keyword-based retrieval."
            )
            self._use_fallback = True
        except Exception as e:
            logger.warning(
                "Failed to load embedding model: %s. "
                "Falling back to keyword-based retrieval.",
                e,
            )
            self._use_fallback = True

    def encode(self, texts):
        self._load_model()
        if self._use_fallback:
            return None
        if isinstance(texts, str):
            texts = [texts]
        embeddings = self._model.encode(
            texts, show_progress_bar=False, normalize_embeddings=True
        )
        return embeddings


class VectorStore:
    """In-memory vector store with cosine similarity search."""

    def __init__(self):
        self._chunks = []
        self._embeddings = None
        self._embedding_engine = EmbeddingEngine()

    def add_chunks(self, chunks):
        self._chunks.extend(chunks)
        self._embeddings = None

    def build_index(self):
        if not self._chunks:
            return
        texts = [c["content"] for c in self._chunks]
        embeddings = self._embedding_engine.encode(texts)
        if embeddings is not None:
            self._embeddings = np.array(embeddings, dtype=np.float32)

    def search(self, query, top_k=5):
        if not self._chunks:
            return []

        if self._embeddings is None:
            self.build_index()

        if self._embeddings is not None:
            return self._semantic_search(query, top_k)
        return self._keyword_search(query, top_k)

    def _semantic_search(self, query, top_k):
        query_embedding = self._embedding_engine.encode(query)
        if query_embedding is None:
            return self._keyword_search(query, top_k)

        query_vec = np.asarray(query_embedding, dtype=np.float32).flatten()
        if query_vec.ndim > 1:
            query_vec = query_vec[0]

        scores = np.dot(self._embeddings, query_vec).tolist()
        scored = list(enumerate(scores))
        scored.sort(key=lambda x: x[1], reverse=True)

        results = []
        for idx, score in scored[:top_k]:
            if score < SIMILARITY_THRESHOLD:
                break
            chunk = dict(self._chunks[idx])
            chunk["score"] = round(score, 4)
            chunk["method"] = "semantic"
            results.append(chunk)
        return results

    def _keyword_search(self, query, top_k):
        query_tokens = _tokenize(query)
        scored = []
        for i, chunk in enumerate(self._chunks):
            doc_tokens = _tokenize(chunk["content"])
            score = _keyword_score(query_tokens, doc_tokens)
            scored.append((i, score))
        scored.sort(key=lambda x: x[1], reverse=True)

        results = []
        for idx, score in scored[:top_k]:
            if score <= 0:
                break
            chunk = dict(self._chunks[idx])
            chunk["score"] = round(score, 4)
            chunk["method"] = "keyword"
            results.append(chunk)
        return results


def chunk_document(doc, chunk_size=200, overlap=50):
    """Split a document into overlapping word-level chunks."""
    if isinstance(doc, str):
        content = doc
        metadata = {}
    elif isinstance(doc, dict):
        content = doc.get("content", doc.get("answer", doc.get("description", "")))
        metadata = {
            k: v
            for k, v in doc.items()
            if k not in ("content", "answer", "description")
        }
    else:
        return []

    words = content.split()
    if len(words) <= chunk_size:
        return [{"content": content, **metadata}]

    chunks = []
    for start in range(0, len(words), chunk_size - overlap):
        chunk_words = words[start : start + chunk_size]
        chunks.append({"content": " ".join(chunk_words), **metadata})
    return chunks


def build_knowledge_chunks():
    """Build chunked knowledge base from FAQ and product data."""
    faqs = _load_json("faq.json")
    products = _load_json("products.json")

    chunks = []

    for faq in faqs:
        faq_chunks = chunk_document(
            {
                "content": f"Question: {faq['question']}\nAnswer: {faq['answer']}",
                "id": faq["id"],
                "category": faq.get("category", ""),
                "type": "faq",
                "keywords": faq.get("keywords", []),
            }
        )
        chunks.extend(faq_chunks)

    for product in products:
        product_chunks = chunk_document(
            {
                "content": (
                    f"Product: {product['name']}\n"
                    f"Category: {product['category']}\n"
                    f"Price: ${product['price']:.2f}\n"
                    f"Description: {product['description']}\n"
                    f"In Stock: {'Yes' if product['in_stock'] else 'No'}\n"
                    f"Variants: {', '.join(product.get('variants', []))}"
                ),
                "id": product["id"],
                "name": product["name"],
                "category": product.get("category", ""),
                "type": "product",
                "in_stock": product.get("in_stock", True),
            }
        )
        chunks.extend(product_chunks)

    return chunks


class RAGEngine:
    """Retrieval-Augmented Generation engine for the chatbot."""

    _instance = None

    def __init__(self):
        self._store = VectorStore()
        self._initialized = False

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def initialize(self):
        if self._initialized:
            return
        chunks = build_knowledge_chunks()
        if chunks:
            self._store.add_chunks(chunks)
            self._store.build_index()
        self._initialized = True
        logger.info("RAG engine initialized with %d chunks", len(chunks))

    def retrieve(self, query, top_k=TOP_K_RESULTS):
        if not self._initialized:
            self.initialize()

        results = self._store.search(query, top_k=top_k)

        if not results:
            return self._fallback_keyword_search(query)

        return results

    def _fallback_keyword_search(self, query):
        """Fallback to the original keyword search if RAG returns nothing."""
        try:
            from src.knowledge_base import FAQSearch, ProductSearch
            faq = FAQSearch()
            faq_results = faq.search(query, top_k=3)
            chunks = []
            for r in faq_results:
                chunks.append({
                    "content": f"Question: {r['question']}\nAnswer: {r['answer']}",
                    "id": r["id"],
                    "type": "faq",
                    "score": 0.5,
                    "method": "fallback",
                })
            return chunks
        except Exception:
            return []

    def format_context(self, chunks):
        """Format retrieved chunks into a context string for LLM prompt injection."""
        if not chunks:
            return ""
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            score = chunk.get("score", 0)
            method = chunk.get("method", "unknown")
            content = chunk.get("content", "")
            context_parts.append(
                f"[Source {i} | relevance: {score:.2f} | method: {method}]\n{content}"
            )
        return "\n\n---\n\n".join(context_parts)

    def search_with_rerank(self, query, top_k=TOP_K_RESULTS):
        """Search with keyword reranking for improved precision."""
        semantic_results = self._store.search(query, top_k=top_k * 2)
        keyword_results = self._store._keyword_search(query, top_k=top_k * 2)

        semantic_ranked = [
            (r["id"], r.get("score", 0)) for r in semantic_results
        ]
        keyword_ranked = [
            (r["id"], r.get("score", 0)) for r in keyword_results
        ]

        fused = _reciprocal_fusion_rank(
            [semantic_ranked, keyword_ranked], k=RRF_K
        )

        chunk_map = {}
        for r in semantic_results:
            chunk_map[r["id"]] = r
        for r in keyword_results:
            if r["id"] not in chunk_map:
                chunk_map[r["id"]] = r

        results = []
        for doc_id, rrf_score in fused[:top_k]:
            if doc_id in chunk_map:
                chunk = dict(chunk_map[doc_id])
                chunk["rrf_score"] = round(rrf_score, 6)
                results.append(chunk)
        return results
