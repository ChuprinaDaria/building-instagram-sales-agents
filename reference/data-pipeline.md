# From raw data to what the LLM sees

Domain-agnostic guide: fashion, electronics, cosmetics, furniture, spare parts. Principle: **the LLM sees the answer to one question, never the database.** Each kind of question has its own access path, chosen by code.

## Contents
1. Inventory the sources
2. Define the sellable unit and its identifiers
3. Typed attributes per category
4. Clean and sort
5. Route each question type to an access path
6. Why "the whole DB in vectors" fails
7. Retrieval order
8. What reaches the LLM
9. Measure retrieval
10. Keep it fresh

## 1. Inventory the sources

One row per source: owner, what it is the truth for, freshness, access. Shop DB, CRM, payment system, docs (warranty, delivery, returns), social media, manager chats, customer DMs. Details and rules: [data-sources.md](data-sources.md).

## 2. Define the sellable unit and its identifiers

Everything the agent says about a product refers to one unit, and №N in the conversation maps to it.

| Domain | Sellable unit | Identifiers | Stock lives at |
|---|---|---|---|
| Fashion | model × colour | SKU, product_id, photo set | size |
| Electronics | model × storage/RAM × colour × version/region × condition (new, refurbished) | EAN/GTIN, MPN, SKU | unit |
| Cosmetics | product × shade/volume | EAN, SKU | unit |
| Spare parts | part number × compatibility list | OEM/MPN, cross-references | unit |

If the shop DB has no clean unit (colour inside the name, variants as separate products, one photo shared by several products), fix it in the catalogue module, not in the prompt.

## 3. Typed attributes per category

Attributes become columns or typed JSON with enums and units, never free text the LLM must read.

- Electronics: brand, model, generation, storage_gb, ram_gb, screen_in, battery_mah, colour, connectivity, condition, warranty_months, compatible_with[].
- Fashion: garment type, model, colour swatch (Lab), sizes in stock, composition, length.
- Units normalised once: "256Gb", "256 GB", "256GB" (and the same in local scripts) → `storage_gb=256`; "6,1''" → `screen_in=6.1`.
- Compatibility is a table (`case_for`, `charger_for`, `part_fits`), not a sentence in a description.

## 4. Clean and sort

In a catalogue module with its own tests; the source DB stays read-only.
- Deduplicate variants and merged products; map shared photos to a set of units.
- Normalise names: strip "Sale"/promo prefixes, HTML entities, colour or storage glued into the name.
- Aliases and synonyms table: transliteration and slang (local spellings of "iPhone" and "Samsung Galaxy", "earphones" ↔ "headset"), category synonyms (category ≠ type is common).
- Mark inactive units; never show them; keep them for history.
- Sort by what the business wants shown first (in stock, margin, novelty) as an explicit rule in code.

## 5. Route each question type to an access path

The LLM extracts **what is asked** into a strict schema (`{intent, category, constraints:{brand, storage_gb, price_max, ...}, refs}`); code picks the path.

| Question | Example | Path |
|---|---|---|
| Exact unit | "Do you have iPhone 15 Pro 256 black?" | constraints → SQL filters → exact match; unknown value returned, not guessed |
| Filter / compare | "Laptop under 30k with 16 GB", "which is better, S23 or S24" | SQL filters + sort; comparison rendered from attributes by code |
| Compatibility | "Will this case fit an S23 FE?" | compatibility table lookup |
| Fuzzy name | typos, transliteration, partial model | lexical search (trigram / BM25) over names + aliases, then vectors over a short name field |
| "Something like this", gift, style | "something similar but cheaper" | vectors over curated descriptions → structured filters (in stock, price) |
| Policy, warranty, delivery, returns | "How long is the warranty on refurbished?" | chunked docs in vectors + rerank; numbers inside answered by slots from config |
| Price, stock, order status | "How much is it?", "where is my order" | live query at answer time, never from an index |
| Photo | customer sends a picture | [vision.md](vision.md) identification ladder |

## 6. Why "the whole DB in vectors" fails

Common shortcut: dump every product row (with price and stock) into a vector store and let similarity answer. It breaks on exactly what a shop sells on.
- **Identifiers blur.** Embeddings put 128 GB next to 256 GB, iPhone 15 next to 15 Pro and 15 Pro Max, S23 next to S24. The customer asked for one of them.
- **Numbers go stale.** Price and stock embedded today are wrong tomorrow; re-embedding on every change is waste, and a stale chunk still ranks high.
- **Filters are not similarity.** "Under 30 000", "in stock", "16 GB" are predicates; top-k does not honour them.
- **No provenance.** A slot must be filled from a record with an id; a text chunk is not a record.
- **Near-duplicates crowd top-k.** Hundreds of variant rows push the right unit out.
- **Tenant and leakage risks grow** with every field you embed.

What does belong in vectors: short curated text per unit (name + aliases + key attributes as words) for fuzzy name lookup; descriptions for "similar to"; docs, FAQ, policies, manager answers, reviews; images for recognition. The payload carries the unit id only; facts are fetched live by id.

## 7. Retrieval order

structured filters → lexical → vectors → rerank → **re-apply filters after rerank** → small result with refs №N and `unknown_terms`. Log scores at every stage.

## 8. What reaches the LLM

At most a handful of units, as №N with only the fields needed to decide (not prices: those go through slots at render time), plus what was not understood. Never raw rows, never ids, never the whole category.

## 9. Measure retrieval

A labelled set of real questions from the journal, per question type: right unit first, recall@k, share of `unknown_terms`. Run it in CI on recorded indexes ($0). Log retrieval and rerank scores in the journal.

## 10. Keep it fresh

A sync job in code pulls the shop DB, re-normalises, and re-indexes only changed units; prices and stock are never cached in the index. Alert on sync failures and on units that disappear while referenced in open conversations.
