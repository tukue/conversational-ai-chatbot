import json
import os
import re
import logging
import numpy as np

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
STOP_WORDS = {
    "a", "an", "and", "are", "can", "could", "do", "does", "for", "have",
    "how", "i", "is", "it", "me", "my", "of", "please", "the", "to", "what",
    "with", "would", "you", "your",
}
EMBEDDING_MODEL = os.getenv(
    "RAG_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
)


def _get_positive_int_env(name, default):
    """Read a positive integer setting without preventing application startup."""
    try:
        value = int(os.getenv(name, str(default)))
        return value if value > 0 else default
    except (TypeError, ValueError):
        logger.warning("Invalid %s value; using default %d", name, default)
        return default


def _get_float_env(name, default):
    """Read a float setting without preventing application startup."""
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        logger.warning("Invalid %s value; using default %s", name, default)
        return default


TOP_K_RESULTS = _get_positive_int_env("RAG_TOP_K", 5)
SIMILARITY_THRESHOLD = _get_float_env("RAG_SIMILARITY_THRESHOLD", 0.3)
RRF_K = _get_positive_int_env("RAG_RRF_K", 60)


def _load_json(filename):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return []
    with open(path, "r") as f:
        return json.load(f)


def _tokenize(text):
    if not isinstance(text, str):
        return []
    return [
        token
        for token in re.findall(r"[a-z0-9]+", text.lower())
        if token not in STOP_WORDS
    ]


def _normalise_query(query):
    """Return a safe query string, preserving normal user input unchanged."""
    return query.strip() if isinstance(query, str) else ""


def _safe_top_k(top_k):
    """Convert a public search limit to a safe non-negative integer."""
    try:
        return max(0, int(top_k))
    except (TypeError, ValueError):
        return 0


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
    denominator = max(len(query_set), len(doc_set))
    return len(intersection) / denominator if denominator else 0.0


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
        try:
            return self._model.encode(
                texts, show_progress_bar=False, normalize_embeddings=True
            )
        except Exception as exc:
            logger.warning(
                "Embedding inference failed: %s. Falling back to keyword retrieval.",
                exc.__class__.__name__,
            )
            self._use_fallback = True
            return None


class VectorStore:
    """In-memory vector store with cosine similarity search."""

    def __init__(self):
        self._chunks = []
        self._embeddings = None
        self._embedding_engine = EmbeddingEngine()

    def add_chunks(self, chunks):
        if not chunks:
            return

        valid_chunks = []
        for chunk in chunks:
            if not isinstance(chunk, dict):
                logger.warning("Skipping non-dictionary RAG chunk")
                continue
            content = chunk.get("content")
            if not isinstance(content, str) or not content.strip():
                logger.warning("Skipping RAG chunk with empty or invalid content")
                continue
            valid_chunks.append(dict(chunk))

        self._chunks.extend(valid_chunks)
        self._embeddings = None

    def build_index(self):
        if not self._chunks:
            return
        texts = [c["content"] for c in self._chunks]
        embeddings = self._embedding_engine.encode(texts)
        if embeddings is not None:
            self._embeddings = np.array(embeddings, dtype=np.float32)

    def search(self, query, top_k=5):
        query = _normalise_query(query)
        top_k = _safe_top_k(top_k)
        if not query or not top_k or not self._chunks:
            return []

        if self._embeddings is None:
            self.build_index()

        if self._embeddings is not None:
            return self._semantic_search(query, top_k)
        return self._keyword_search(query, top_k)

    def _semantic_search(self, query, top_k):
        query = _normalise_query(query)
        if not query or not top_k:
            return []
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
        query_tokens = _tokenize(_normalise_query(query))
        top_k = _safe_top_k(top_k)
        if not query_tokens or not top_k:
            return []
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

    if not isinstance(content, str) or not content.strip():
        return []

    try:
        chunk_size = int(chunk_size)
        overlap = int(overlap)
    except (TypeError, ValueError):
        return []
    if chunk_size <= 0 or overlap < 0:
        return []
    overlap = min(overlap, chunk_size - 1)

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
        if not isinstance(faq, dict) or not {"id", "question", "answer"} <= faq.keys():
            logger.warning("Skipping malformed FAQ entry")
            continue
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
        required_fields = {"id", "name", "category", "price", "description"}
        if not isinstance(product, dict) or not required_fields <= product.keys():
            logger.warning("Skipping malformed product entry")
            continue
        if not isinstance(product["price"], (int, float)):
            logger.warning("Skipping product with a non-numeric price: %s", product["id"])
            continue
        variants = product.get("variants", [])
        if not isinstance(variants, list) or not all(isinstance(v, str) for v in variants):
            logger.warning("Skipping product with invalid variants: %s", product["id"])
            continue
        product_chunks = chunk_document(
            {
                "content": (
                    f"Product: {product['name']}\n"
                    f"Category: {product['category']}\n"
                    f"Price: ${product['price']:.2f}\n"
                    f"Description: {product['description']}\n"
                f"In Stock: {'Yes' if product.get('in_stock', True) else 'No'}\n"
                f"Variants: {', '.join(variants)}"
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

        query = _normalise_query(query)
        top_k = _safe_top_k(top_k)
        if not query or not top_k:
            return []

        results = self._store.search(query, top_k=top_k)

        if not results:
            return self._fallback_keyword_search(query)

        return results

    def _fallback_keyword_search(self, query):
        """Fallback to the original keyword search if RAG returns nothing."""
        try:
            from src.knowledge_base import FAQSearch
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
        if not self._initialized:
            self.initialize()

        query = _normalise_query(query)
        top_k = _safe_top_k(top_k)
        if not query or not top_k:
            return []

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
