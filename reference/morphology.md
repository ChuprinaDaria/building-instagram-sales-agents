# Names in inflected languages (Ukrainian and similar)

**Problem.** In Ukrainian, Polish, Czech and other inflected languages a noun changes its ending after prepositions and verbs ("photo of the dress" puts "dress" in the genitive). A slot `{name:N}` fills the catalogue name in the nominative, so a draft like "for {name:1} we have…" renders as "for Dress-cape-viscose we have…" with the wrong case: the reply reads broken. Asking the LLM to inflect the name itself brings back facts typed by the LLM (rule 1).

## Solution: frozen forms table

1. **Offline build, dev dependency only.** `pymorphy3` + `pymorphy3-dicts-uk` (the VESUM dictionary) read the catalogue dump and write `forms.json`: `{unit_id: {"nom": …, "gen": …, "dat": …, "acc": …, "loc": …}}`. Production reads the JSON and never imports pymorphy3.
2. **Head rule.** Inflect only the head of the name: adjectives before the head noun, the head noun, and adjectives after it that agree with it. The tail stays as is: prepositional phrases ("made of viscose"), Latin brand names, colour words.
3. **Colours** are separated using the catalogue swatch list and inflected by the same rule.
4. **Refuse instead of guessing** and send the name to human review: word unknown to the dictionary, two nouns in a row, capitalised model name, compound of different genders, indeclinable words, a head adjective found in the tail.
5. **Slots with case:** `{name.gen:N}`, `{name.dat:N}`, `{name.acc:N}`, `{name.loc:N}`; the same for `colour`.
6. **Fallback when no form exists:** a carrier word in the needed case + the name in quotes in the nominative (the equivalent of "the model «Dress-cape viscose»"). It is always grammatical.
7. **Prompt rule (the only one):** no agreeing word (demonstrative, adjective, "model", "colour") right before a cased slot, so the fallback carrier never clashes with it.

Measured on a 3 319-name fashion catalogue: 1 809 names got at least one form, 1 595 all four; the rest go to the fallback; 1 008 rows went to human review.

## Checks

- Coverage stats from the build script: names with all cases, any case, refused.
- Guard test: no head adjective stays in the nominative in the table.
- Live metric: 0 grammar violations on N rendered turns in the regression set.

Do not use per-word inflection scripts made for search (they inflect prepositional tails, brands and colours), and do not send a client catalogue to remote inflection services.
