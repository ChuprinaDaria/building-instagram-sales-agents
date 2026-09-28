# Blueprint: Instagram sales agent

## Contents
1. Turn pipeline
2. Channel rules (Instagram)
3. Catalogue and photos
4. Humans in the loop
5. Orders, payments, CRM
6. Module layout

## 1. Turn pipeline

```
IG webhook ─► gateway: verify HMAC, drop duplicates by message id, 200 fast
          ─► inbox (per customer): debounce ~3 s, hard ceiling ~12 s
          ─► turn lock: one turn per customer at a time
          ─► ban check (code)                        ── banned → stop, log
          ─► takeover check (manager active?)        ── yes → stop, log
          ─► load: state (items №N, cart), client card, memory snippets
          ─► photo in turn? → vision pipeline → verdict (code)
          ─► LLM: strict Answer{extracted, reply} + tool calls
          ─► verify extracted against message text (code)
          ─► renderer: slots → facts; RenderError → 1 retry → fallback + card
          ─► ban + takeover check again (state may have changed while thinking)
          ─► sender: window check, send, attach catalogue photos by ref
          ─► journal every step
```

Debounce and ceiling values come from the prod journal, not from intuition. Log both.

## 2. Channel rules (Instagram)

Verify against Meta's current docs for your app before relying on these (the official policy pages require login):
- Standard messaging window: a business can reply within 24 h of the customer's last message.
- `HUMAN_AGENT` tag extends to 7 days and is for replies written by a human, not by the bot.
- Consequence: a "payment reminder after 1 day" or "follow-up after silence" must be sent **inside** the window (e.g. at 20–23 h) or handed to a manager. The sender module checks the window; the prompt does not know about it.
- Story replies and post shares arrive with media context (story/media id, permalink). Map media → product by code (a table maintained from the shop's posts), never ask the LLM to guess.
- Messages the manager sends from the Instagram app come back as echo events. Treat a manager echo as takeover for that customer: the agent stops until release or TTL, and logs it.
- Automation disclosure: if the jurisdiction requires it, disclose that the customer talks to an automated assistant.

Viber/WhatsApp via an aggregator: same pipeline, different adapter; each adapter owns its own window and template rules.

## 3. Catalogue and photos

- Shop database is **read-only** for the agent. Normalise it once in a catalogue module (sellable unit, typed attributes, units, aliases, category synonyms, compatibility tables, real stock) and expose tools on top. Step by step: [data-pipeline.md](data-pipeline.md).
- Each question type has its own access path (SQL filters, lexical, vectors for fuzzy text, live lookup for price and stock). Not the whole DB in vectors.
- Search returns unknown words instead of guessing.
- Customer photo: identification ladder in code (own media id → barcode/OCR identifiers → read attributes → visual similarity → ask), then `decide()` with a calibrated threshold → verdict. The LLM receives the verdict and candidate refs and must follow it. See [vision.md](vision.md).
- Measure per domain: studio vs phone photos, and per rung of the ladder. Build the test set from real DMs.
- The agent sends catalogue photos by ref (`№2`); code resolves the image URL.

## 4. Humans in the loop

- Manager bot (Telegram or similar) receives cards: customer, reason, last messages, draft, buttons.
- Card goes to all managers; first answer wins; others see "resolved by X"; TTL (e.g. 24 h) then the customer gets a fallback and the case is logged.
- The customer is always told that an answer is coming. Escalation never equals silence.
- Kinds of escalation: `question` (manager answers, agent relays in its voice), `takeover` (manager writes directly), `approval` (order, payment entity).
- Ban and release are set only by a manager, never by the LLM.
- Every manager answer is stored as an example (PII masked) for tone retrieval.

## 5. Orders, payments, CRM

- Cart is state in code. Items reference `№N`; totals are computed by code.
- Order form text is rendered from the cart and the client card, not written by the LLM.
- Collection of name, phone, city, delivery point: the LLM extracts, code verifies against the message and validates format.
- Order → manager approval (choice of legal entity/payment account, corrections) → customer confirms the rendered form → CRM write.
- CRM writes: one writer module, idempotency key per order, retry with backoff, failed writes visible to managers. Dual CRM = one primary write + sync, not two independent writers.
- Status/lead reason: the LLM returns an enum in the strict schema; code maps enum → CRM status via a table; an unmapped value becomes "needs review", not a guess.
- Payment link from the CRM/payment API; payment confirmed by the system's webhook or status poll. A screenshot only triggers "we'll check".
- Order status questions: tool reads CRM, slots render the status.

## 6. Module layout

```
channels/      adapters: instagram, echat; HMAC, echo, window, sender
queue/         inbox (debounce), turn lock, scheduler (window-aware)
agent/         loop, schemas (Answer, Reply), prompt, renderer, forms.json
tools/ or MCP  catalogue, vision, crm, memory, escalation
state/         items №N, cart, takeover, bans   (one writer per field)
memory/        card, vectors (tenant), examples
hitl/          manager bot, cards, TTL
journal/       events, masking, digest
tests/regression/  fixtures from prod journal
```
