# AI Development Process

## Objective

Improve the chatbot safely while preserving its deterministic support flows,
local knowledge sources, optional generation, and safe fallback responses.

## Change workflow

1. Create a focused feature branch from `main`; do not mix unrelated fixes.
2. Record the user-facing behavior that must remain unchanged before editing.
3. Add or update a test that demonstrates the intended behavior and relevant
   failure path.
4. Implement the smallest compatible change. Keep public module APIs and
   fallback messages stable unless the change explicitly requires otherwise.
5. Run linting, the complete suite, and the 90% branch-coverage gate locally.
6. Review the diff for sensitive data, unsafe logs, new dependencies, and
   accidental changes to knowledge data or deployment configuration.
7. Open a PR with the behavior change, safety impact, evaluation evidence, and
   rollback approach.

## AI-specific review checklist

- **Routing:** verify representative messages still map to the intended intent
  and template/RAG/generative path.
- **RAG:** test relevant retrieval, no-result fallback, malformed knowledge
  entries, and grounded-answer validation.
- **Safety:** test both adversarial and legitimate prompts. Guardrail telemetry
  may contain aggregate rule outcomes only—never user messages, responses, PII,
  credentials, or prompts.
- **Generation:** keep it opt-in; test model-unavailable fallback behavior.
- **Observability:** use event categories and counts, with no raw conversation
  logging. Alert on sustained blocks, retrieval fallback increases, or error
  spikes.

## Release and rollback

Deploy only after CI passes. Use feature flags for behavior-changing AI paths,
monitor aggregate guardrail and retrieval outcomes after release, and revert the
release or disable the affected flag if safety, relevance, or error-rate signals
degrade.
