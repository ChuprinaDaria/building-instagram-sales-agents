# Decision card

Fill before writing code. One row per function of the agent. Keep it in the repo as `docs/decision-card.md` and update it when a decision changes.

## Preference order

`code` > `local model` > `LLM` > `human`, except high-risk actions, which always end with `human`.

| Executor | Use when | Examples |
|---|---|---|
| code | the answer is deterministic, a lookup, a rule, a schedule, a mapping | price, stock, ban check, status mapping, reminders by timer, CRM write |
| local model | recognition or classification on domain data, measurable on a held-out set | product from photo (detector + embedder + calibrated decision), intent classifier, NER on domain |
| LLM | understanding free user text, choosing a tool, writing words with slots | "is this about sizes or delivery", reply text |
| human | money, irreversible actions, conflicts, anything the agent is not sure about after one retry | payment link, order approval, returns, complaints |

## Template

| Function | Executor | Input | Output (schema) | Source of truth | How measured | Fallback | Licence / notes |
|---|---|---|---|---|---|---|---|
| | | | | | | | |

## Example (fashion sales agent in Instagram DM)

| Function | Executor | Output | Source of truth | Measured | Fallback |
|---|---|---|---|---|---|
| Ban check | code, before LLM and again before sending | skip turn | DB `bans` | unit test | — |
| Intent → CRM status (37 statuses) | LLM extracts enum via strict schema; code maps enum → CRM status and writes | `intent: Literal[...]` | CRM | labelled set, accuracy | status "needs review" |
| Price, sizes, stock | code (catalogue tool) + slots | `{price:N}` | shop DB, read-only | fixture tests | "I'll check and get back" |
| Product from photo | local model: segmentation → embedder → calibrated decide() | `CLOSE / UNSURE / OTHER_CLASS …` | catalogue index | held-out photos, precision at "confident" | ask the client |
| Payment reminder after 24 h | code scheduler | message template | order state | unit test | — |
| Order approval, payment entity | human in manager bot | approve/reject | manager | delivery log | TTL + tell client |
| Reply text | LLM with slots | `Reply{text, kind, mentioned, options}` | — | regression fixtures, length p90 | renderer fallback |

## Example (electronics shop in Instagram DM)

| Function | Executor | Output | Source of truth | Measured | Fallback |
|---|---|---|---|---|---|
| "Do you have iPhone 15 Pro 256 black?" | LLM extracts constraints to schema; code runs SQL on typed attributes | units as №N | shop DB | labelled queries, right unit first | ask the missing attribute |
| "Will this case fit an S23 FE?" | code: compatibility table | yes / no / unknown | compatibility table | fixture tests | manager card |
| Photo of a phone | code ladder: own media → EAN/OCR → brand/model family → ask variant | `CLOSE / FAMILY / UNSURE …` | catalogue identifiers | per-rung share, precision at confident | ask storage/condition |
| Storage, condition, warranty | code from the unit's attributes + slots | `{storage:N}`, `{warranty:N}` | shop DB, config | fixture tests | "I'll check" |
| Warranty and return policy text | tool over chunked docs + rerank; numbers by slots | snippet + slots | policy docs, config | retrieval eval | manager card |
| Trade-in estimate | human | price offer | manager | delivery log | TTL + tell client |

## Framework or extra service?

Allowed only with a row here: what it gives, what the own-code alternative costs, how it will be measured.
