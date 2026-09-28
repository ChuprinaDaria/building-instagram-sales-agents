# Failure mechanisms

Observed in real production agents. When reviewing or fixing, name the mechanism, not just the bug. The fix protocol is in [growth.md](growth.md).

| Code | Mechanism | Symptom | Fix |
|---|---|---|---|
| M1 | Rules argue: the same rule lives in prompt, tool description, injected hint and guard | fixing one place breaks another | one owner per rule, in code |
| M2 | Merge without a behaviour gate | regressions found by users | regression fixtures in CI on the merged branch |
| M3 | Guards share mutable turn state | a flag written in 5 places, read in 10+ | one source of truth per state |
| M4 | Regex over open language | endless dictionary rounds | strict schema; stop at the third regex round |
| M5 | Several outputs for one result | duplicated or contradicting messages | single exit point per turn |
| M6 | Several stores of truth | memory contradicts DB | one store per data kind ([memory.md](memory.md)) |
| M7 | One sample on another SHA | "it worked when I tried" | pass^k on the deployed SHA |
| M8 | Tests pinned to phrases | tests break on wording, miss real bugs | assert structure and facts |
| M9 | Merged ≠ deployed | fix "done" but not in prod | verify prod image SHA |

## Case catalogue

Real incidents, grouped by mechanism. Use them to recognise the pattern early.

### Post-generation guards (M1, M3, M5)
- A guard erased the reply text on every turn with an escalation. One conversation: 80 min, 11 escalations, 9 empty replies, 0 orders. Loop: irritation → "aggression → escalate" → erased text → empty message → more irritation. None of the erased texts was a transactional promise.
- Guards "made safety by silence": holding or dropping replies on approval and payment.
- A fact validator stayed in shadow mode for three months while invented numbers reached customers (14 in two days).

### Identity of items (M6)
- The LLM passed raw `productId`s; later it passed its own list numbering (3, 12, 2) as ids and the tool silently accepted them.
- Rejected recognition candidates stayed in context; the customer got another item's colour and a confident price.
- The LLM claimed to "see the customer's measurements" (none existed) and swapped the item; the whole size chart answered the wrong product. A DB number was presented as stock.
- Fix pattern: №N refs resolved by code, candidate lists cleared by code, facts only through slots.

### Prompt as the control surface (M1, M4)
- Prompt 30k → 48k → 50k characters. "The rule was already in the prompt, verbatim for this case, and lost."
- A fixed RU→UK word-replacement list after generation, regex PII filters, an injection filter that only logged: each a small regex layer, together the start of M4.
- Six to seven rounds of word lists (WHICH / NOT_WHICH / ASKING) to make the LLM follow a photo verdict; fixed only by a strict reply schema checked by code.

### Humans in the loop
- Handover designed as silence: 23 of 25 escalations in 30 days left the customer waiting with nobody notified.
- 281 escalations, none with an answer recorded; the learning loop was dead.
- `escalate` wrote only to the journal; managers received nothing.

### Photos
- LLM reranker: 22–25 s, timeouts, 14 % confident wrong item.
- "Confident" at raw 0.53 on a selfie without a calibrated threshold.
- Photo context lived one turn / in an expiring cache → "which one?" loops.
- See [vision.md](vision.md).

### Gate and process (M2, M7, M9)
- CI watched a branch nobody merged into; 5 PRs merged without approval; later "CI is down repo-wide" and deploys failed on billing.
- Scenario runs by hand, after merge, one sample.
- Direct pushes without PRs even after the rewrite: the gate is CI after the fact.

### Constants and observability
- `LLM_MAX_STEPS = 15` declared, never passed; the framework default applied.
- `strict` declared in comments, never enabled; one schema broke the convention.
- Cost tracker wrote 0 for every call; later `cost_usd` null in 113 of 113 replies.
- Masking history before extraction lost customers' phone numbers.

### Width over depth
- A skeleton generated in one day: six queues with DLQ, dual CRM, TDE, blind index, partitioning, for a shop with a few dozen dialogues a day. Generic CLIP for fashion. No evals in the plan.
