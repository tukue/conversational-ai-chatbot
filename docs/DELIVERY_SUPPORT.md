# Delivery platform support

The default chat experience focuses on delivery support. Specific delivery routes in
`src/delivery.py` handle late orders, missing/wrong items, courier contact, coverage,
delivery estimates and fees, cart/checkout, address changes, cancellation, payment
methods, groceries/meals, pharmacy navigation, and refunds. Explicit human-agent
or supervisor requests take precedence. The Gradio header reflects these workflows. The chat UI has no sample-question buttons.

Responses guide customers to Orders, Track delivery, secure checkout, and Help.
There is no authenticated delivery backend, so the assistant cannot confirm live
status, change an address, contact a courier, transfer a chat, or approve refunds.
No placeholder platform links, universal refund windows, delivery prices, or
payment-method availability are presented as verified delivery policy. The legacy
retail FAQ and product files remain retrieval fixtures; product responses identify
the catalog as sample data. Generative fallback remains disabled by default.

## Basic monitoring

`src.monitoring.get_monitoring_metrics()` returns a thread-safe snapshot for trusted
operator integrations. It includes:

- `requests`, `outcome_completed`, `outcome_input_blocked`,
  `outcome_rate_limited`, `outcome_output_blocked`, and `outcome_error`.
- `input_allowed`, `input_blocked`, `rate_limited`, `route_<delivery topic>`,
  `intent_<intent>`, and `generative_fallback` counters.
- `input_chars_total`, `output_chars_total`, `latency_ms_total`, and `latency_ms_mean`.

Every chat invocation records one outcome, including early returns and exceptions.
Input rejection is counted separately from output rejection. The final output is
screened once, after routing and response construction. Counters and the INFO log
in `src.monitoring` contain counts, fixed outcome labels, and timing only: no raw
input/output, order IDs, session IDs, credentials, or exception messages.

Metrics are process-local and reset on restart. They are not exposed in the public
chat UI. Multiworker aggregation, persistence, alerting, and a monitoring dashboard
are outside this basic implementation. Enable INFO logging in the hosting process
to collect request-summary logs. Existing `get_security_metrics()` provides output
block categories; proxy `/analytics` remains protected by a separate admin key.

## PR #11 review reference

Reference: https://github.com/tukue/conversational-ai-chatbot/pull/11

- Proxy admission now uses an AnyIO capacity limiter with immediate 503 rejection;
  release occurs in `finally`, including cancellation and policy-error paths.
- An AnyIO lock protects rate-window reset, limit checking, and increment together.
  The original code had no await within its admission block, so the review's claim
  of coroutine interleaving between individual integer statements was inaccurate;
  the explicit primitives make the guarantees clearer and robust to future awaits.
- Proxy settings reject empty/whitespace credentials. The chatbot also rejects an
  unconfigured client key before sending a request. The original server already
  rejected empty credentials, so the review's empty-key authentication bypass was
  not reproducible with valid Settings.
- Both workflow dependency blocks already use consistent indentation.
- `actions/checkout@v6` exists: https://github.com/actions/checkout/releases/tag/v6.0.0
  The deploy version is retained; the review's nonexistent-version claim is stale.

Regression tests cover parallel rate-limit bursts across a window reset, existing
concurrency/cancellation/deadline paths, blank credentials, delivery routing,
privacy, output screening, error accounting, and concurrent monitoring updates.
