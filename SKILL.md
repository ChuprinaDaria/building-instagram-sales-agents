---
name: building-instagram-sales-agents
description: Designs, reviews, fixes and grows LLM sales and support agents in Instagram DM (also Viber, WhatsApp) for shops of any product domain - catalogue database, customer photos, memory, human managers in the loop, orders, payments, CRM. Enforces one architecture - code produces facts, decisions and state, the LLM only interprets the customer and writes words - so the repo grows without patch-on-patch regressions. Covers data preparation and retrieval routing, moving prompt rules and knowledge files into code, photo recognition with local models (dataset collection, Hugging Face, RunPod, YOLO, SAM, DINO, detection vs classification vs retrieval), LLM roles beyond chat, small per-turn context, a traceable source of truth, slots and renderer, evals and merge gates. Use when building or changing such an agent, fixing a bug or regression in it, adding a rule to its prompt, choosing a framework, a vector store, an embedder or reranker, or a vision model for it, or reviewing its repo.
license: The Chuprina Glory License 1.0 - do anything, credit the author visibly (see LICENSE)
---

# Building Instagram sales agents

## Principle

**Code is fact, the LLM is interpretation.** Code produces facts (price, stock, identity of a unit), decisions (verdicts, statuses, escalations) and state (cart, refs, client card). The LLM reads the customer, fills a strict schema with what it understood, picks a tool and writes words with slots. Everything the LLM returns is a proposal that code accepts or rejects. Why, and where the boundary lies: [reference/principles.md](reference/principles.md). The LLM does far more than talk (intent, extraction, reference resolution, query rewriting, summaries, batch parsing, labelling help), always through a schema: [reference/llm-roles.md](reference/llm-roles.md).

**Every change goes to its owner.** A bug is fixed where the decision is made, never by a new layer downstream. This separates a system that grows from one that must be rewritten: [reference/growth.md](reference/growth.md).

Default to the smallest thing that works; add only what a measurement shows is needed.

## Terms

Used with one meaning throughout the skill.

- **LLM**: the language model that talks to the customer. **Local model**: any model you run yourself (detector, embedder, classifier, small LLM).
- **Unit**: the sellable unit (fashion: model × colour; electronics: model × storage × colour × condition). **Ref**: `№N`, the conversation's reference to a unit; code maps it to the unit id.
- **Slot**: `{price:N}` in an LLM draft; the **renderer** fills it from the unit's record.
- **Verdict**: a code decision the reply must follow (photo `CLOSE / FAMILY / UNSURE …`, order status).
- **Decision card**: one row per agent function with its **owner** (`code | local model | LLM | human`).
- **Journal**: per-step event log. **Fixture**: a recorded turn from the journal used as a regression test.

## Getting started

Copy this checklist into the conversation and track it:

```
Agent setup:
- [ ] 1. Data: sources, unit + identifiers, typed attributes, question → access path   (reference/data-pipeline.md)
- [ ] 2. Decision card: every function with an owner                                   (reference/decision-card.md)
- [ ] 3. Contracts: pydantic schemas for tools and for the answer                       (reference/slots-renderer.md)
- [ ] 4. Skeleton: webhook+HMAC, inbox, turn lock, own tool loop, renderer, journal, CI (reference/blueprint.md)
- [ ] 5. Regression runner with the first fixtures, running in CI on the merged branch  (reference/evals.md)
- [ ] 6. Capabilities one per phase: catalogue → memory → photo → humans → orders      (reference/growth.md)
```

Show the decision card to the user before writing code. Before each phase, run the cheapest measurement that could show it is not needed.

## Rules

Each rule has a check. A rule without a check is a wish.

| # | Rule | Check |
|---|------|-------|
| 1 | **Facts via slots.** A number, size, phone or id typed by the LLM → `RenderError` → one retry with the reason → fixed fallback + card to a human | test: typed digits are rejected |
| 2 | **Customer values are extracted by the LLM, verified by code** against the verbatim message | test: extracted value matches the input |
| 3 | **Strict structured output** for the answer and every tool code acts on. Optional field = union with null. Third round of regex over free text → stop, move it into the schema | `audit_agent.py`: strict flags, regex count |
| 4 | **Prompt = identity + tools + how to write slots.** No branching prose; measure size in characters | `audit_agent.py`: prompt chars, conditional phrases |
| 5 | **Tools:** one job, strict schema, structured errors, refs instead of raw ids; one MCP server per domain | [reference/tools.md](reference/tools.md) |
| 6 | **Risky decisions by code** with a calibrated threshold; "ask again" is a valid output | calibration on held-out data |
| 7 | **Local model before LLM** for recognition and classification, when it matches or beats the LLM on held-out domain data; licences of code and weights resolved before handover | eval report + licence in the decision card |
| 8 | **Memory without chat logs in context:** card by code, state by code, vectors with tenant filter | test: cross-tenant query returns nothing |
| 9 | **One writer per state field** | grep writers per field |
| 10 | **No framework by default.** Own tool loop over the provider SDK; a framework needs a decision-card row | `audit_agent.py`: framework imports |
| 11 | **Escalation is never silence:** delivery confirmed, first responder wins, TTL, customer informed; high-risk actions need human approval | test: escalation without delivery fails |
| 12 | **Journal from day one** with provenance, tokens, cost, ms; PII masked at write; a cost of 0 is a bug | `audit_agent.py --journal` |
| 13 | **Wired or deleted:** every limit, budget, flag reaches the code it controls | `audit_agent.py`: unused constants |
| 14 | **Evals gate merges:** fixtures from the real journal, $0, in CI on the merged branch; deploy only a green SHA | CI config |
| 15 | **Modules with explicit interfaces:** transport, state, tools, renderer, memory, journal | import graph without cycles |
| 16 | **Channel rules are code:** messaging window, takeover by echo, rate limits in the sender | test: send outside window is blocked |
| 17 | **Money is confirmed by systems,** never by a screenshot or LLM text | test: screenshot does not change status |
| 18 | **Checks reject, never rewrite.** A post-generation check may only raise → retry → fallback; editing, erasing or silently holding text is forbidden | test: no empty reply is ever sent |
| 19 | **Photo verdict is state:** identification ladder in code, calibrated `decide()`, verdict persisted with refs, reply checked against it; no LLM as recogniser | per-domain precision at "confident" + confident share |
| 20 | **Social media is history, the shop DB is truth.** Legal access only; stop on HTTP 429, never bypass blocks | test: a caption price never reaches a slot |
| 21 | **Change at the owner, fixture first;** stop signs freeze patching until a redesign is approved | review: each fix has a fixture and a named mechanism |
| 22 | **The DB is queried, not embedded.** Structured queries for units, filters, compatibility, price, stock; vectors only for fuzzy text and images, always with metadata filters, hybrid lexical + dense and a reranker; store, embedder and reranker chosen on your own labelled queries ([reference/vectors.md](reference/vectors.md)) | retrieval eval per question type; scores logged at every stage |
| 23 | **Prompt rules and knowledge files migrate to code,** then the prose is deleted | prompt chars and conditional phrases go down |
| 24 | **Small context rebuilt by code every turn:** prompt, state block, card, a few snippets and recent turns; no full history, no catalogue, no knowledge files, no old tool results. See [reference/context.md](reference/context.md) | journal: input tokens per turn, median and p90 |
| 25 | **Every fact the customer sees has a source record;** the LLM writes nothing into storage without validation; unknown is a legal answer. See [reference/source-of-truth.md](reference/source-of-truth.md) | journal: `facts[].source` present for 100 % of rendered facts |

## Workflows

**A. New agent.** Follow "Getting started". Architecture: [reference/blueprint.md](reference/blueprint.md).

**B. Review an existing agent.** Run `python scripts/audit_agent.py <repo> [--journal dump.jsonl] [--prompt path]`, report the numbers, map each finding to a rule and a mechanism from [reference/antipatterns.md](reference/antipatterns.md), propose the smallest fix first. Then check by hand what the script cannot: raw ids visible to the LLM, prose that duplicates code, escalation delivery, one writer per field.

**C. "Add this to the prompt", or an existing long prompt / knowledge `.md` files.** Classify and migrate: [reference/prompt-to-code.md](reference/prompt-to-code.md). Only identity, tone and tool usage stay in the prompt.

**D. Bug, regression, "it does X wrong".**

```
Fix progress:
- [ ] Fixture from the journal, failing
- [ ] Mechanism named (M1–M9 or new)
- [ ] Owner found in the decision card
- [ ] Fix at the owner; nothing from the forbidden list (growth.md §2)
- [ ] Fixture + full regression green; audit without new violations
- [ ] One change per commit; deploy the exact SHA; check the prod image
```

If a stop sign fires in that area, stop and propose a redesign of the owning module ([reference/growth.md](reference/growth.md) §3).

**E. Photo recognition or another local model.** Architecture and verdicts: [reference/vision.md](reference/vision.md). Which task type and which model family: [reference/local-models.md](reference/local-models.md). Dataset, labelling, Hugging Face, RunPod, training and gates: [reference/datasets-and-training.md](reference/datasets-and-training.md).

**F. Before merge.** Tests and regression green, audit without new violations, deploy the exact SHA. For a new repo copy [templates/agent-audit.yml](templates/agent-audit.yml) into `.github/workflows/`.

## Reference map

| Topic | File |
|---|---|
| Why code decides, where the boundary is | [reference/principles.md](reference/principles.md) |
| What the LLM is for: online and batch roles, each with a schema | [reference/llm-roles.md](reference/llm-roles.md) |
| Agent context: what goes into a turn, what never does, token budget | [reference/context.md](reference/context.md) |
| Source of truth: fact chain, precedence, writes, unknown as an answer | [reference/source-of-truth.md](reference/source-of-truth.md) |
| Lessons from one production agent's history: timeline, laws, LLM misconceptions | [reference/lessons.md](reference/lessons.md) |
| Architecture, turn pipeline, Instagram channel rules, module layout | [reference/blueprint.md](reference/blueprint.md) |
| Build order, change protocol, stop signs, complexity budget | [reference/growth.md](reference/growth.md) |
| Failure mechanisms and real incidents | [reference/antipatterns.md](reference/antipatterns.md) |
| Data from source to what the LLM sees; why not the whole DB in vectors | [reference/data-pipeline.md](reference/data-pipeline.md) |
| Sources: shop DB, CRM, Instagram, manager chats | [reference/data-sources.md](reference/data-sources.md) |
| Moving prompt rules and knowledge files into code | [reference/prompt-to-code.md](reference/prompt-to-code.md) |
| Decision card template and examples | [reference/decision-card.md](reference/decision-card.md) |
| Answer schema, slots, renderer, turn loop | [reference/slots-renderer.md](reference/slots-renderer.md) |
| Tools, MCP servers, own tool loop | [reference/tools.md](reference/tools.md) |
| Memory: card, state, vectors, tenants | [reference/memory.md](reference/memory.md) |
| Vector search: stores (pgvector, Qdrant, Weaviate, Milvus, OpenSearch, LanceDB, hosted), embedders and rerankers local vs API, hybrid search, operations | [reference/vectors.md](reference/vectors.md) |
| Journal schema and daily digest | [reference/journal.md](reference/journal.md) |
| Evals and merge gate | [reference/evals.md](reference/evals.md) |
| Photo recognition: identification ladder, verdicts | [reference/vision.md](reference/vision.md) |
| Local models: task type, model families, licences, architectures | [reference/local-models.md](reference/local-models.md) |
| Datasets, labelling, Hugging Face, RunPod, training, gates | [reference/datasets-and-training.md](reference/datasets-and-training.md) |
| Names in inflected languages (Ukrainian) | [reference/morphology.md](reference/morphology.md) |

## Scripts

- Run `python scripts/audit_agent.py <repo> [--prompt FILE] [--journal FILE.jsonl] [--ci]`: prompt size and branching phrases, frameworks, `strict` flags, regex count, unused constants, licence flags, CI branches, journal null rates. Python 3.10+, stdlib only. `--ci` exits 1 when a hard limit is crossed.

## When the user pushes back

If the user insists on a prose rule, a framework or a long prompt: state the rule it breaks and the measurable risk once, then do what they decide and record the deviation in the decision card.
