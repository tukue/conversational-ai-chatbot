# LLM proxy implementation backlog

Updated: 2026-10-26. Scope: a service that monitors LLM inputs and outputs,
enforces security policies, and provides usage analytics.

Status: the standalone buffered text proxy is implemented. Chatbot integration and
production rollout are pending. Checked items describe implemented behavior, not a
claim that the service is production-ready.

## Completed

- [x] **DONE-01 — Architecture and setup.** Compare wrappers, dedicated gateways,
  and existing gateway hooks; document trust boundaries, configuration and limitations.
  Evidence: [design guide](LLM_PROXY.md).
- [x] **DONE-02 — Text completion gateway.** Strict message schema, model allowlist,
  fixed HTTPS upstream, rebuilt responses, and rejection of unsupported request types.
  Evidence: [proxy](../src/llm_proxy.py), [validation tests](../tests/test_llm_proxy.py).
- [x] **DONE-03 — Authentication.** Separate client and administrator bearer keys;
  provider credentials stay on the proxy; analytics require administrator access.
  Evidence: proxy and authentication tests.
- [x] **DONE-04 — Baseline input/output policies.** Unicode normalization and
  pattern checks for PII, secrets, unsafe markup and injection; inspect history;
  buffer output until screened; return generic failures when policy evaluation fails.
  Evidence: proxy and policy tests. Pattern detection has false positives and gaps.
- [x] **DONE-05 — Resource controls.** Body/message/token bounds, process-local
  request quota, concurrency cap, upload/upstream deadlines and Retry-After headers.
  Evidence: proxy and validation, concurrency, cancellation and timeout tests.
- [x] **DONE-06 — Connection lifecycle and health.** Pooled HTTP client with shutdown
  cleanup; liveness and local readiness endpoints; no automatic generation retries.
  Evidence: proxy and lifecycle tests.
- [x] **DONE-07 — Process analytics.** Outcomes, block categories, token totals,
  cumulative latency, cancellation and persistence-error counts without conversation text.
  Evidence: proxy and usage-accounting tests.
- [x] **DONE-08 — Persistent daily analytics.** Optional SQLite WAL aggregates,
  atomic updates, configurable retention, admin history endpoint and generic storage errors.
  Evidence: [store](../src/proxy_analytics.py), [persistence tests](../tests/test_proxy_analytics.py).
- [x] **DONE-09 — Regression tests and CI dependencies.** Mock upstream calls;
  test blocked delivery with usage counted, malformed providers, persistence across
  restarts, concurrent updates and storage failure. Both workflows install proxy dependencies.
  Latest completed validation: 325 passed, 1 skipped; Ruff passed.

## Pending implementation

P0 = integration/release foundation; P1 = production hardening and scaling;
P2 = extended capabilities. These are priorities, not delivery dates.

| ID | Priority | Status | Deliverable | Acceptance criteria and tests | Dependencies |
| --- | --- | --- | --- | --- | --- |
| PROXY-01 | P0 | Pending | Integrate chatbot generation with proxy | Configured generation calls traverse the proxy; no silent direct-provider fallback on rejection; policy denials and outages render safe UI responses. End-to-end tests verify forwarding and blocked delivery. Decide how the existing local DialoGPT fallback fits the upstream contract. | DONE-02 |
| PROXY-02 | P0 | Pending | Tenant identities and credential lifecycle | Resolve identity from credentials; reject revoked/expired credentials; enforce per-tenant model permissions; support rotation without logging secrets. Test cross-tenant isolation and client/admin separation. | DONE-03 |
| PROXY-03 | P0 | Pending | Shared quotas and concurrency accounting | Atomic per-tenant limits across workers, explicit store-outage behavior and bounded token-budget reservations. Test concurrent workers, quota-window boundaries, cancellation and reservation release. | PROXY-02 |
| PROXY-04 | P0 | Pending | Dedicated deployment configuration | Reproducible proxy container, ingress TLS/body/time limits, secret injection, persistent volume permissions, health probes and egress restrictions. Smoke-test restart and approved upstream connectivity; verify applications cannot bypass proxy enforcement. | PROXY-01 |
| PROXY-05 | P1 | Pending | Configurable, versioned policies | Validate policy configuration at startup; select tenant policy; expose the applied version in aggregate reporting; support controlled rollback. Test invalid configuration and policy changes. Current policy version is only a fixed label. | PROXY-02 |
| PROXY-06 | P1 | Pending | Stronger PII/moderation and adversarial evaluation | Add selected detectors with deadlines and defined failure behavior; evaluate direct/indirect injection, obfuscation, cross-message attacks and benign prompts. Document detection and false-positive results without claiming complete prevention. | PROXY-05 |
| PROXY-07 | P1 | Pending | Circuit breaker | Bound calls during repeated provider failures; configurable recovery probe behavior; no blind retries of billable requests. Test open, half-open and recovered states with concurrent requests. | DONE-06 |
| PROXY-08 | P1 | Pending | Operational telemetry and alerts | Export request rates, latency histograms, blocks, capacity, provider failures and persistence errors; add actionable alerts. Test label cardinality and absence of credentials/conversation text in logs and traces. | DONE-07 |
| PROXY-09 | P1 | Pending | Tenant/model analytics and cost estimates | Aggregate by trusted tenant/model identifiers; version pricing and distinguish estimates from billing; preserve usage from blocked outputs; enforce report isolation. Test attribution, missing usage and rate changes. | PROXY-02, DONE-08 |
| PROXY-10 | P1 | Pending | Multi-host analytics storage | Add a centralized store/collector with explicit delivery, deduplication, retention and outage semantics. Test concurrent hosts, restart recovery and duplicate writes. SQLite remains suitable only for local-host aggregation. | PROXY-09 |
| PROXY-11 | P1 | Pending | Load and resilience qualification | Establish latency/throughput targets; run sustained overload, slow-upload/provider, cancellation and database-contention tests. Verify bounded memory/connections, shutdown behavior and recovery against those targets. | PROXY-03, PROXY-04, PROXY-07 |
| PROXY-12 | P2 | Pending | Streaming | Define a release policy before sending tokens; enforce screening, cancellation and usage accounting throughout the stream. Tests demonstrate that blocked content cannot escape before a decision. | PROXY-05 |
| PROXY-13 | P2 | Pending | Tool/function calls | Validate tool names and arguments, authorize each action against tenant permissions, inspect tool results and prevent execution of unapproved calls. Test forged calls, indirect injection and unauthorized side effects. | PROXY-02, PROXY-05 |
| PROXY-14 | P2 | Pending | Multimodal inputs | Define supported media, size/type restrictions, URL-fetch boundaries and modality-specific screening. Test malformed media, resource exhaustion and unsafe fetch destinations. | PROXY-05, PROXY-06 |

## Suggested delivery order

1. Integrate the chatbot (PROXY-01) and prepare deployment (PROXY-04).
2. Add tenant identities and shared quotas (PROXY-02, PROXY-03).
3. Version policies, strengthen detection, add resilience and alerts (PROXY-05–08).
4. Extend analytics and qualify under load (PROXY-09–11).
5. Implement streaming, tools and multimodal support only when required (PROXY-12–14).

## Completion rule

Mark an item complete only when its acceptance criteria are implemented, relevant
tests pass, and setup/limitations are documented. Link code and test evidence when
moving it to Completed. Keep partial work Pending and describe the remaining scope.
