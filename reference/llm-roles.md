# What the LLM is for (much more than talking)

"Code is fact, the LLM is interpretation" does not reduce the LLM to a text generator. It is the best tool you have for turning messy language into structure and structure into language. Every role below follows one contract: **the LLM proposes in a strict schema, code validates against a source, then accepts, retries with the reason, or escalates.**

## Contents
1. Online roles (inside a turn)
2. Offline roles (batch, before or after the conversation)
3. Not the LLM's job
4. Contract checklist for a new LLM role

## 1. Online roles (inside a turn)

| Role | LLM output (strict schema) | Code validates / acts |
|---|---|---|
| Intent | `intent: Literal["ask_price", "select", "reject", "order", "complaint", …]` | routes the turn; unknown value → ask |
| Constraint extraction | `{category, brand, storage_gb, size, colour, price_max, …}` | builds the query; values checked against the attribute vocabulary |
| Reference resolution | "the second one", "that green one", "the one from the story" → `refs: ["№2"]` | every ref must exist in the conversation state |
| Customer values | phone, city, delivery point, size, name | must match the verbatim message; format validated; written to the card by code |
| Query rewriting | customer words → search terms + `unknown_terms` | search runs in code; unknown terms returned to the customer, not guessed |
| Tool choice and order | tool calls with strict arguments | step limit wired; each call journaled |
| Signal detection | `sentiment`, `urgency`, `complaint: bool`, `wants_human: bool` | escalation rules in code decide what happens; the LLM does not escalate by mood |
| Clarifying question | picks which missing field to ask from a list code provides | the list comes from state (what is missing), not from the LLM |
| Reply draft | `Reply{text with slots, kind, mentioned, options}` | renderer fills facts; `kind` checked against verdicts |
| Manager card summary | short summary + the exact question for the manager | quoted customer lines attached verbatim by code |
| Language handling | reply in the customer's language / register | tone from retrieved real manager answers |

## 2. Offline roles (batch, before or after the conversation)

| Role | Output | Validation |
|---|---|---|
| Catalogue normalisation | messy names/descriptions → typed attributes | enums and units checked; conflicts → human review queue |
| Aliases and synonyms | candidate aliases per unit/category | a human approves before they enter the search table |
| Social media parsing | captions → `{post_kind, items[{type, model, price}]}`; comments → `{kind, topic, items, summary}` | every item must exist in the catalogue; invalid JSON → one retry → `unparsed` |
| FAQ mining | clusters of real questions with the brand's real answers | answers quoted, not invented; human approves the FAQ |
| Memory cards | session → card fields with verbatim quotes | code keeps a field only if its quote is found in the transcript |
| Labelling help | pseudo-labels, captions for images | humans verify; verified share recorded |
| Eval generation | scenario variants from real failures | labelled as synthetic; never reported as production metrics |
| Judging | tone, politeness, rubric scores | calibrated against human labels (e.g. Cohen's kappa) before its scores gate anything |
| Description variants | social-media copy per unit | facts inserted by slots; human review before publishing |

## 3. Not the LLM's job

- Being the source of a fact: price, stock, sizes, ids, URLs, dates, delivery terms.
- Arithmetic: totals, discounts, prepayment amounts.
- Deciding anything with money, bans, statuses or irreversible effects.
- Recognising or verifying a product from a photo (see [vision.md](vision.md)).
- Being the memory: remembering ids or facts "from earlier in the chat" instead of reading state.
- Judging its own output without calibration.

## 4. Contract checklist for a new LLM role

```
New LLM role:
- [ ] Strict output schema written first (enums, nullable fields, no free-form where code acts)
- [ ] Source code validates against named (message text, state, catalogue, transcript)
- [ ] Reject path: one retry with the reason, then fallback or human
- [ ] Journal event with input size, output, validation result, cost
- [ ] Fixture set from real cases; accuracy measured before it gates anything
```
