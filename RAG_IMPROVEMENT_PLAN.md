# RAG Improvement Plan

## Goal

Improve retrieval quality, resilience, and observability without changing the
chatbot's existing public interfaces or fallback behavior.

## Current baseline

- The RAG engine loads FAQ and product JSON into an in-memory vector store.
- Semantic retrieval uses `sentence-transformers` when available.
- Keyword retrieval remains the dependency-free fallback.
- Reciprocal Rank Fusion (RRF) combines semantic and keyword rankings when
  reranking is enabled.
- The existing test suite passes: `247 passed, 1 skipped`.

## Improvements

1. **Input validation and safe configuration**
   - Reject non-string or empty queries consistently.
   - Clamp invalid `top_k` values and chunking parameters to safe values.
   - Make malformed documents harmless rather than allowing retrieval-time
     exceptions.

2. **Stronger lexical retrieval**
   - Normalize common word variants before scoring.
   - Incorporate FAQ keywords and selected metadata into the lexical document
     representation.
   - Prefer exact phrase/name matches while retaining the current keyword
     fallback contract.

3. **True hybrid retrieval**
   - Obtain semantic and lexical candidate lists independently.
   - Fuse them with RRF using a stable, unique per-chunk identity, so chunks
     from the same source cannot overwrite one another.
   - Preserve the existing `retrieve`, `search_with_rerank`, and result fields.

4. **Diversity and context quality**
   - Avoid returning duplicate or heavily overlapping chunks before formatting
     LLM context.
   - Enforce a bounded, configurable context length while keeping source labels
     intact.

5. **Operational resilience and observability**
   - Cache normalized lexical representations when chunks are added.
   - Handle embedding failures per request by falling back to lexical search.
   - Log only safe aggregate retrieval diagnostics (method, candidate/result
     counts), never user content.

6. **Regression coverage**
   - Add tests for invalid inputs, metadata-aware retrieval, chunk identity,
     deduplication, and context limits.
   - Run the entire existing test suite after implementation.

## Compatibility guardrails

- Do not remove or rename public classes, methods, constants, or result keys.
- Keep `sentence-transformers` optional.
- Keep `FAQSearch` as the final fallback when RAG produces no result.
- Preserve default environment-variable behavior unless a new optional setting
  is explicitly introduced.
