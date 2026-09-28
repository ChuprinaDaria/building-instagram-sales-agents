# Agent context: small, rebuilt by code every turn

The context window is not the memory. Each turn, code **rebuilds** a small context from state, card and retrieved snippets; everything else lives in the DB, JSON cards or vectors and is fetched just in time through tools. Nothing accumulates by itself.

## Contents
1. What goes into a turn
2. What never goes into a turn
3. Budget and measurement
4. Failure modes seen in production

## 1. What goes into a turn

| Block | Built by | Size guide |
|---|---|---|
| System prompt: identity, tone, tools, how to write slots | static file | ≤ 8 000 characters |
| State block: refs №N with one-line labels, cart, open question, verdicts, missing fields | code, from DB/Redis | tens of lines |
| Client card: exact known values (size, city, name) | code | a few lines |
| Memory snippets | vector search with tenant filter + rerank | top 3–5 |
| Tone examples | retrieved real manager answers | 2–4 |
| Recent messages | code | last few turns, not 30 |
| Tool results of this turn | tools | small, only what is needed to decide, refs instead of ids |

Blocks are structured (JSON or clearly delimited lists), not prose, and each has a fixed place in the prompt, so the LLM always finds them where it expects.

## 2. What never goes into a turn

- The whole conversation history. It grows, it contains stale facts and rejected candidates, and the LLM treats everything in it as current.
- The catalogue or a category dump. Use tools that answer one question.
- Knowledge `.md` files injected every turn. Migrate them ([prompt-to-code.md](prompt-to-code.md)); retrieve policy text via a tool when asked.
- Raw ids, SKUs, internal URLs. Refs only; code maps them.
- Tool results from previous turns, especially rejected candidates. Their conclusions live in state; the raw results are gone.

## 3. Budget and measurement

- Journal input tokens per LLM call and per turn; report median and p90 in the daily digest.
- Reference numbers: a context built from state, card and snippets ran at a median of 5.7–8.0 k input tokens per turn; the prompt-and-history design it replaced ran at 52–73 k, with worse answers.
- A growing median is a stop sign: something started accumulating.
- Prompt caching helps cost, not correctness: a cached 50 k prompt is still 50 k characters of rules arguing with each other.

## 4. Failure modes seen in production

- **Facts from earlier turns treated as current.** A photo description lived in the history/cache; when it expired, the agent looped "which one do you mean?". Fix: verdicts and refs in state, rebuilt every turn.
- **Ids pinned into the context as text.** The LLM "remembered" ids from the chat and invented some; the fixes pinned more ids into the context instead of moving them into state. Fix: refs in state, ids never shown.
- **Rejected candidates left in context.** The customer heard the colour and price of an item that had been rejected. Fix: tool results do not outlive the turn.
- **Masking the history before extraction.** Phone numbers were masked in the history the LLM read, so it could not extract them. Fix: mask when writing the journal and indexes, not in the live turn input.
- **Prompt regrowth.** A prompt rewritten from 85 k to 30.5 k characters grew back to 50 k in three months, because every new problem was still solved with prose.
