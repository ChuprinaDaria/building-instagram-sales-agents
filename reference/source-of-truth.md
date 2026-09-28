# Making the source of truth true, not a hallucination

A hallucination reaches a customer only through a path where text from the LLM is treated as a fact. Close every such path, and make the true path the only one.

## Contents
1. The fact chain
2. Precedence of sources
3. Writes: what the LLM may put into storage
4. Unknown is a valid answer
5. Checks

## 1. The fact chain

```
source (shop DB, CRM, config)            read-only for the agent
  → normalised record (unit id, version, fetched_at)   catalogue module
  → tool result with refs №N                            this turn only
  → slot in the LLM draft {price:N}                     the LLM never types the value
  → renderer resolves from the records of this turn     RenderError if missing or typed
  → journal: facts[] with source = "catalogue:unit/8812@version"
  → daily digest: facts without source = 0
```

Every value the customer sees can be traced to a record and a moment. If it cannot, it must not be sent.

## 2. Precedence of sources

Write the order down; code applies it when sources disagree.

| Kind of fact | Truth | Never from |
|---|---|---|
| Price, stock, active units | shop DB (live query) | index, captions, memory, the LLM |
| Order and payment status | CRM / payment system webhooks | screenshots, customer claims, the LLM |
| Delivery, warranty, return terms | config / policy docs with version | examples, the prompt |
| Customer values (size, city, phone) | client card written by code from a verbatim quote | summaries, guesses |
| Taste, past topics | vector memory (derived, marked as such) | treated as fact |
| Outfits, historic prices, tone | social media (history) | current price or stock |

Derived data (summaries, memory cards, captions parsed by the LLM) carries a `derived_from` link to its source turns or posts and never overrides primary data.

## 3. Writes: what the LLM may put into storage

- Nothing directly. The LLM proposes values in a schema; code writes them after validation.
- Customer values: stored only if the verbatim quote they came from is in the message.
- Summaries and cards: each field keeps its quote; fields without a found quote are dropped.
- Catalogue enrichment from the LLM (attributes, aliases): goes through human review before it becomes searchable.
- The shop DB is never written by the agent.

## 4. Unknown is a valid answer

Hallucinations fill gaps. Give the gap a legal exit instead:
- tools return `unknown_terms` and `not_found` rather than the nearest guess;
- the renderer falls back to "I'll check and get back to you" plus a card to a human when a slot cannot be filled;
- the photo pipeline returns `UNSURE` / `FAMILY` and the reply asks;
- the digest counts fallbacks; a rising share is a data problem to fix at the source, not a prompt to strengthen.

## 5. Checks

- Test: a draft with a typed price, size, phone or ref raises `RenderError`.
- Test: a caption or memory value never fills a price or stock slot.
- Test: a customer value without its quote is not written to the card.
- Journal: `facts[].source` present for 100 % of rendered facts; alert otherwise.
