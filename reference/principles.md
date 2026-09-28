# Principles: code is fact, the LLM is interpretation

## Contents
1. The boundary
2. Why code decides
3. What the LLM is for
4. The contract between them
5. How to split a function
6. Objections and answers

## 1. The boundary

| Code owns | The LLM owns |
|---|---|
| Facts: price, stock, sizes, identity of a unit, delivery terms, order status | Understanding what the customer means, in her words, with typos and slang |
| Decisions: photo verdict, escalation delivery, CRM status, ban, takeover | Filling a strict schema with that understanding (intent, constraints, refs, extracted values) |
| State: refs №N, cart, client card, open question, verdicts | Choosing which tool to call next |
| Channel rules: messaging window, rate limits, echo takeover | Writing the reply in the brand's voice, with slots for every fact |
| Validation of everything the LLM returns | Asking a clarifying question when code says the information is missing |

The LLM never produces a fact and never makes a decision code can make. It produces **proposals** in a schema; code accepts, rejects (retry with the reason) or escalates.

## 2. Why code decides

- **Deterministic.** Same input, same output. A decision you cannot reproduce cannot be debugged; an LLM decision changes between samples and model versions.
- **Testable at $0.** A code decision is covered by a fixture that runs in milliseconds in CI. An LLM decision needs paid runs with several samples to say anything.
- **Local fix.** A code bug is fixed in one function. An LLM "bug" is fixed by prose that argues with other prose (M1) and is lost again later.
- **Auditable.** Every fact has a source record; every decision has a line of code and a journal event. "Why did it say that?" has an answer.
- **Cheap and fast.** A lookup costs nothing and takes milliseconds; an LLM verifier took 22–25 s per photo and timed out.
- **Safe against injection.** A customer message cannot talk code out of a price, a ban or a payment status.
- **Stable under model upgrades.** Switching LLM versions changes wording, not prices or verdicts.

The reference project proved it by contrast: five months of steering an LLM with a 50 000-character prompt and post-generation guards produced 26 regression chains; moving facts and decisions into code cut the prompt to 8 000 characters and made failures reproducible.

## 3. What the LLM is for

Open language. Customers write "same as this but darker, in my size" or "the one from the story, but in 256", with typos, transliteration and slang. No parser handles the long tail of phrasing; the LLM does, as long as its job ends at "here is what she means, in this schema" and "here are the words, with slots". Style comes from retrieved real manager answers, not from rules. The full list of LLM roles, online and batch, with the schema and validation for each: [llm-roles.md](llm-roles.md).

## 4. The contract between them

```
customer text ─► LLM ─► Answer{extracted, reply{text with slots, kind, mentioned refs, options}}
                          │
                          ▼
code: extracted values match the message? refs exist in state? kind consistent with verdicts?
      slots resolvable? no typed facts?  ──no──► RenderError → one retry → fallback + card
                          │yes
                          ▼
renderer fills slots from records ─► sender checks window/takeover/ban ─► send ─► journal
```

## 5. How to split a function

For each function of the agent ask in order; the first "yes" is the owner.

1. Is the answer a lookup, a rule, a mapping, a schedule or arithmetic? → **code**
2. Is it recognition or classification on domain data, measurable on a held-out set? → **local model** (then code decides from its score)
3. Is it understanding free text or writing words? → **LLM**, output in a strict schema
4. Is it money, irreversible, a conflict, or still uncertain after one retry? → **human**

Write the answer into the decision card ([decision-card.md](decision-card.md)).

## 6. Objections and answers

| Objection | Answer |
|---|---|
| "The LLM is smart enough to just follow the rule" | It followed it until it did not: "the rule was already in the prompt, verbatim for this case, and lost". A rule you cannot test is a wish. |
| "Writing code for every case is slower" | Only for the first week. After that every prose rule costs a regression chain; code costs one fixture. |
| "A framework gives us agents and memory out of the box" | It hides the loop, the step limit and the state you must own. An own loop is about 100 lines; a framework needs a decision-card row with a measured reason. |
| "Let the LLM recognise the product from the photo" | Measured: slow, 14 % confident wrong answers, leaks rejected candidates into the reply. A local model + calibrated `decide()` is faster, free per call and more precise at "confident". |
| "Put the whole catalogue in vectors, the LLM will figure it out" | Identifiers blur, numbers go stale, filters are not similarity. See [data-pipeline.md](data-pipeline.md) §6. |
