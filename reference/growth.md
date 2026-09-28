# Growth without spaghetti

The failure this file exists to prevent: a repo where every fix is a new layer on top of the last one, each layer reads or edits what the previous one produced, and fixing one place breaks another. In the reference project this took five months: prompt 30k → 50k characters, 26 regression chains, and a rewrite. The rewrite worked because it changed who decides what, not because the code was cleaner.

## Contents
1. Build order
2. Change protocol (every bug, every "small" request)
3. Stop signs
4. Complexity budget
5. Merge and deploy discipline

## 1. Build order

Build the skeleton that makes failures visible **before** any intelligence. Each phase ends with its decision-card rows filled, fixtures in `tests/regression/`, and one metric in the daily digest. The next phase starts only then.

| Phase | Contents | Done when |
|---|---|---|
| 0. Skeleton | webhook + HMAC, inbox debounce + ceiling, turn lock, own tool loop with wired `max_steps`, strict `Answer`, renderer with `RenderError`, journal with cost, CI running regression on the merged branch | a turn with a typed price is rejected in a test; journal shows cost ≠ 0 |
| 1. Catalogue | read-only catalogue module, normalisation, 2–4 tools, №N refs, slots for price/sizes/stock | fixtures from real questions pass; unknown words returned, not guessed |
| 2. Memory | client card (code-written), conversation state, vectors with tenant | cross-tenant test; memory hits in digest |
| 3. Photo | local pipeline + calibrated `decide()`; verdict persisted in state ([vision.md](vision.md)) | precision at "confident" and its share, per domain |
| 4. Humans | manager bot, cards, first-wins, TTL, takeover by echo, ban | escalation-without-delivery test fails the build |
| 5. Orders | cart state, rendered form, approval, one CRM writer, payment by webhook | idempotency test; screenshot does not change status |

Do not build breadth first. A day-one skeleton with six queues, dual CRM, TDE and partitioning for a shop with a few dozen dialogues a day is width over depth; none of it survived.

Before a phase, check it is needed: run the cheapest measurement that could show it is not (e.g. a 200-case benchmark cancelled a month of fine-tuning that would have made results worse).

## 2. Change protocol

Applies to every bug report and every "just add X". Follow in order; skipping a step is how patches pile up.

1. **Reproduce as a fixture.** Take the failing turn from the journal (input, state, recorded tool results, LLM output). Add it to `tests/regression/` failing. No journal record → the first fix is the journal.
2. **Name the mechanism.** M1–M9 from [antipatterns.md](antipatterns.md), or a new one written down. "Model is dumb" is not a mechanism.
3. **Find the owner.** The decision-card row that owns this function. The fix goes there and only there.
4. **Forbidden fixes** (each one is how the reference repo died):
   - a guard that edits, erases or rewrites text after generation;
   - a new prompt rule for something a slot, schema field, tool or code can hold;
   - a new regex over customer or LLM language (third round on the same thing = stop, move to schema);
   - a new writer of an existing state flag;
   - a second exit point that can send a message;
   - a hint injected into history that restates a rule already in the prompt or a tool description.
5. **Smallest fix at the owner.** If the owner cannot express it, the owner is wrong: change the schema, the tool contract or the decision card row, not a layer above it.
6. **Green.** The new fixture and the full regression pass; audit shows no new violations.
7. **One change per commit/PR, independent review.** Reviewer checks the protocol, not only the diff: fixture exists, mechanism named, fix at owner, nothing from the forbidden list.
8. **Deploy the exact SHA** and verify the prod image label. Merged is not deployed.

## 3. Stop signs

When any fires, stop patching that area. Write a redesign of the owning module (decision-card row, schema, tool contract) and get it approved before the next commit there.

| Sign | Threshold | How to see it |
|---|---|---|
| Fix of a fix | a commit adjusting a commit < 7 days old in the same function | git log / blame |
| Prompt grows | +20 % in a month, or over the budget | audit, prompt chars |
| Regex count grows | any growth in modules that read language | audit, `re.compile` per file |
| Shadow mode lingers | a validator/guard in "log only" > 14 days | config + journal |
| Dictionary rounds | 3rd round of word lists for one intent | commit subjects |
| Tests pinned to phrases | asserts on exact wording | review of tests |
| "Works on my run" | one sample on a non-deployed SHA quoted as proof | PR text |
| Escalation spike or silence | digest: escalations/100 turns up, or unanswered escalations > 0 | journal digest |

## 4. Complexity budget

Numbers enforced in CI by `audit_agent.py --ci` (see [../templates/agent-audit.yml](../templates/agent-audit.yml)). Raising a limit needs a decision-card row with the reason.

- System prompt ≤ 8 000 characters (reference: 50 445 at collapse, 8 071 after rewrite).
- No framework without a card row.
- `strict` on the answer schema and on every tool whose output code acts on.
- `re.compile` over language: tracked per file, growth reviewed.
- Every constant reaches the code it controls.

## 5. Merge and deploy discipline

- CI runs on the branch that is actually merged and deployed. A gate on another branch is no gate (5 PRs merged without approval while CI watched the wrong branch).
- Direct pushes to the deploy branch: only green SHAs, and still one change per commit with a named mechanism in the message.
- Deploy by exact SHA, image by digest; record the SHA in the deploy log and check it on the server.
- A lane reports its state in files next to the work, not only in chat: if a message is lost, the state survives.
