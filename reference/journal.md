# Journal

Written from the first commit, not after the first incident. Goal: after a failure you can see what the agent consulted, what it skipped and where every fact came from, without reproducing it.

## One event per step

```json
{
  "ts": "2026-09-27T11:49:02Z",
  "turn_id": "t_0142",
  "tenant": "ig:1784…",
  "step": 2,
  "type": "tool_call | tool_result | llm_call | render | render_error | escalation | fallback",
  "name": "find_products",
  "args": {"query": "khaki dress"},
  "result_summary": {"count": 3, "refs": [1, 2, 3]},
  "not_called": ["vision.identify: no photo in turn"],
  "facts": [{"slot": "price:1", "value": "2450", "source": "catalogue:product/8812"}],
  "model": "…",
  "tokens_in": 5712, "tokens_out": 214,
  "cost_usd": 0.0041,
  "ms": 1380,
  "error": null
}
```

- `not_called` makes "why didn't it check X" answerable.
- `facts[].source` is the provenance of every value that reached the user.
- PII (phone, name, address) masked before writing.
- `cost_usd` computed from a price table in config; if the LLM is not in the table, write `null` **and** count it as unpriced. Never write `0`.

## Format

Plain JSON lines are enough to start. If you need traces and dashboards, map the same fields to OpenTelemetry GenAI semantic conventions instead of inventing a new schema.

## Daily digest (code, not LLM)

turns, escalations / 100 turns, render errors / 100, "ask again" share, fallback share, p50/p90 reply length in characters, cost per turn, unpriced calls, memory backend errors.

Alerts: no reply to a user for N minutes, escalation spike, render error spike.
