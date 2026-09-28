# Memory

Never keep the raw conversation as the agent's memory. Split by precision.

| Kind | Store | Written by | Reaches the LLM as |
|---|---|---|---|
| Exact client data (name, phone, sizes, address, orders) | DB table or JSON card | code only, with the verbatim quote it came from | structured block every turn |
| Conversation state (items shown with №N, cart, open question, last checkpoint, photo verdicts with candidates) | DB / Redis | code | structured block every turn |
| Fuzzy history (what she liked, past topics, manager answers, tone examples) | vector store | code, after PII masking | top-k snippets via a tool or auto-injection |

Recent messages: only the last few turns, not 30.

- A photo's verdict never lives in a temporary cache: when the cache expired, the agent lost what the photo was and looped "which one do you mean?".
- Mask PII when writing the journal and the vector store, not in the history the extractor reads: masking before extraction lost customers' phone numbers.
- Six places holding "the truth" about a customer (summary, measurements scan, shown-items ledger, order state, pending clarification, history) is M6; one card + one state per customer.

## Vectors

- One collection per data kind, **not** one per client. Tenant id in the payload, indexed as tenant (Qdrant: `is_tenant=true`).
- Tenant id comes from code (`platform:user_id`), never from the LLM.
- Filter by tenant on every query, then rerank, then **re-check tenant** on the reranked list.
- Embedder, reranker and store: choose on your own labelled queries, local first when quality is within tolerance, so client conversations never leave your infrastructure. Options, licences, hybrid search and operations: see vectors.md.
- If the memory backend is down, the turn continues without memory **and logs it**. Silent degradation is a bug.

## Checks

- Test: a query with tenant A never returns tenant B, including after rerank.
- Journal: memory hits per turn, empty-result rate, backend errors.
