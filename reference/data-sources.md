# Data sources: catalogue, Instagram, manager chats

The agent is only as right as its sources. Each source has an owner, a freshness, and a rule for what it may be used for.

| Source | Truth for | Not truth for | Access |
|---|---|---|---|
| Shop DB (OpenCart etc.) | price now, stock per size, active items, photos | — | read-only, normalised once in a catalogue module |
| CRM / payment system | order status, payment | product facts | one writer module, webhooks |
| Instagram posts / captions | history: which items were shown together (outfits), tone of the brand, historic prices, popularity | current price, current stock | brand's own export or Instagram Login API |
| Instagram comments | FAQ, complaints per item, brand's answers in threads | facts about the item | same; raffles and emoji-only removed by code, nicks hashed |
| Manager chats | tone examples, real answers to real questions | policy (write policy in data, not from examples) | PII-masked before indexing |
| Customer DMs (journal) | eval fixtures, phone-photo test set | — | PII-masked, consent per jurisdiction |

## Rules

1. **Social media is history.** In the reference shop 173 of 250 prices in captions differed from the current catalogue. Captions can say "this was worn with that" and "this cost X in March"; the agent quotes prices only from the shop DB via slots.
2. **Captions rarely identify a sellable unit.** Product = model × colour; captions name the model and omit colour (39 % of posts matched a model by name, 0 % reached product id without the photo). Colour comes from the vision pipeline, and code checks the model on the photo is among the items parsed from the caption.
3. **Legal access first.** Prefer the brand's own data export or the Instagram Login API with the brand's consent. Browser scraping of Instagram is against Meta's terms and gets rate-limited (HTTP 429, often for hours); a scraper must stop on 429 and resume later. Never work around blocks with proxies, extra accounts or checkpoint bypasses.
4. **Parse with strict schemas, validate with code.** Caption → `{post_kind, items:[{type_word, model_name, price_uah}]}`; comment → `{kind, topic, items, summary}`. Code checks every item exists in the catalogue dictionary, else `unmatched`; invalid JSON → one retry → `unparsed`.
5. **Normalise the catalogue once.** Prefixes like "Sale", HTML entities, colour inside the name, duplicate photos across products, category ≠ garment type: fix in the catalogue module, never in prompts.
6. **Mask at write, not before use.** Mask PII when writing the journal and indexes. Masking history before extraction lost customers' phone numbers in the reference agent.
7. **No fake data.** Evals, examples and test sets come from real journal and real photos; synthetic data is labelled as such and never reported as a production metric.
