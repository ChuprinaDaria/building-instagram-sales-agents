# Moving agent behaviour out of prompts and .md files into code

A rule in prose is read probabilistically, tested by nobody and argued with by every other rule (M1). Knowledge `.md` files injected into the context are a long prompt in disguise: they grow the same way (30k → 50k characters in the reference project) and lose the same way. This guide migrates them into code, data, schemas and tools, one statement at a time.

## Step 1. Inventory

Collect every piece of text that reaches the LLM: system prompt, tool descriptions, injected hints, knowledge `.md` files, few-shot examples. Split into single statements, one row each.

## Step 2. Classify each statement

| Type | Example | Goes to |
|---|---|---|
| Fact | "Refurbished warranty is 6 months", "delivery takes 1–2 days", address, hours | data (DB / config / JSON) + tool + slot |
| Procedure | "First ask for storage, then colour" | state machine: code says what is missing next; the LLM asks it in words |
| Branch | "If she asks for a discount …", "if the item is out of stock, offer a similar one" | code decision, or an enum field in the answer schema that code acts on |
| Schedule | "Remind about payment after a day" | window-aware scheduler |
| Format | "A list of items with prices" | renderer template |
| Prohibition | "Never promise a delivery date", "never quote a price without checking" | schema + renderer reject → retry → fallback |
| Mapping | "Status 'thinking' = lead 'warm' in CRM" | enum → table in code |
| Long knowledge | warranty terms, return policy, care instructions | chunked docs retrieved via a tool with rerank; numbers inside go through slots |
| Identity, tone | who the agent is, how it talks | stays in the prompt (short) + retrieved real manager examples |
| Tool usage | when to call which tool | the tool's own description |

## Step 3. Migrate one statement at a time

1. Fixture from the journal that shows the current behaviour (or the failure).
2. Implement at the target (data, code, schema, tool, renderer).
3. **Delete the prose.** Keeping both is M1: the next change edits one and they diverge.
4. Full regression green; audit shows the prompt shorter and fewer conditional phrases.

## Step 4. What remains in the prompt

Who the agent is, tone, the list of tools, how to write slots, how to act on verdicts and state blocks. Target ≤ 8 000 characters, no "if … then" branches.

## Examples

| Before (prose) | After |
|---|---|
| "If the customer asks whether a case fits, check the phone model" | `compatibility` tool over a table; answer schema field `asks: compatibility`; renderer fills result |
| "Quote the discounted price, promo ends Sunday" | promo in data with dates; price tool returns final price; `{price:N}` slot |
| "Do not offer items that are out of stock" | filter in the search tool; inactive units never returned |
| "When she sends a photo, recognise it first" | code runs vision before the LLM when the turn has an image; verdict in state |
| "After checkout ask for phone and city" | order state machine lists missing fields; the LLM asks; code validates the extracted values |
| Knowledge file `delivery.md` injected every turn | delivery terms in config + `get_policy` tool; numbers by slots |
