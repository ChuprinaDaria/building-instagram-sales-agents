# Evals and merge gate

## Layer 1: regression fixtures ($0, every push)

- Source: real turns from the journal, especially failures. Start with 20–50.
- Each fixture: input message, state, **recorded tool results**, recorded LLM output → expected rendered text properties / expected decision.
- Tests deterministic parts only: renderer, decide(), tools on recorded data, state transitions, escalation delivery.
- No LLM calls. Runs in seconds. Required status check in CI on the branch that is actually merged and deployed.
- Assert on structure and facts (kind, refs, slots filled, no typed digits), never on exact phrasing.

## Layer 2: LLM runs (on demand, budget-capped)

- Same scenarios, live LLM, `--max-usd` cap.
- Contested turns: k samples, report pass^k (all k pass), not one lucky sample.
- If an LLM judge is used, calibrate it against human labels first.

## Layer 3: ML components

- Split by session/source, not randomly (no leakage between train and test).
- Held-out test is used once per decision. Negative results are written down and not deployed.
- Report precision at the "confident" threshold and the share of cases that reach it, per domain (studio photos vs phone photos are different domains).

## Gate

- Merge and deploy only a green SHA. Image by digest.
- Every fixed prod failure adds a fixture.
