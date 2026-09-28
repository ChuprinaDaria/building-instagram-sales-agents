# Lessons from one production agent's history

A real Instagram sales agent, 732 commits over seven months, three architectures. Read it to recognise the trajectory early. Mechanisms (M1–M9) are in [antipatterns.md](antipatterns.md); the protocol that prevents them is in [growth.md](growth.md).

## Contents
1. Timeline
2. Laws that hold in any domain
3. Mistakes made without understanding how an LLM works
4. Where it arrived

## 1. Timeline

| Period | Architecture | What was trusted | What broke |
|---|---|---|---|
| Month 1 | Skeleton generated in one day: six queues, dual CRM, a framework agent, generic CLIP | the LLM to decide everything; breadth of infrastructure | no evals in the plan; handover designed as silence |
| Months 1–5 | Framework ReAct agent in production; prompt as the control surface | prose rules; post-generation guards; an LLM verifier for photos; an LLM-graded QA agent | prompt 1 k → 85 k characters; 138 commits to the prompt; a guard erased replies (9 empty messages, 11 escalations, 0 orders in one conversation) |
| Month 3 | Prompt "v2" rewrite: 85 k → 30.5 k | that consolidation fixes behaviour | regrew to 50 k in about three months |
| Months 3–6 | More guards, enforced instead of logged | guards editing text | a guard mangled sizes already agreed with the customer; a fact validator in shadow for three months |
| Month 5 | First step-by-step trace of tool calls | — | four months of production debugged without knowing which tools ran |
| Month 7 | Rewrite: code produces facts and decisions, LLM writes words with slots, local vision, journal with provenance | code, schemas, fixtures | the old reflex returned once: seven rounds of word lists in one lane, stopped by a strict reply schema |

In total 327 of 732 commit subjects start with "fix". Most fixes of the first architecture add a sentence to the prompt or a guard after generation; almost none move a decision into code.

## 2. Laws that hold in any domain

1. **Prose does not converge.** Every prompt fix adds a rule that can argue with an older one. Rewriting the prompt resets the size, not the mechanism: it grows back.
2. **A correct fix needs the right foundation.** A check that images may only come from URLs returned by tools in this turn was correct, and it was reverted after 90 minutes: without cross-turn state of shown items it broke legitimate follow-ups. The fix stuck only after refs №N became state.
3. **If you cannot see the tool calls, you are guessing.** Observability without per-step tool, arguments and results is not observability. Build the journal before the first user.
4. **Removing the cost tracker hides the problem it measured.** One was removed entirely in month 3; cost per turn was unknown until the rewrite.
5. **Guards that edit text create new bugs in text.** Every mutating guard produced a class of broken replies (empty messages, mangled sizes, lost promises).
6. **Shadow mode is a place where validators go to die.** Three months in "log only" while invented numbers reached customers.
7. **An LLM grading an LLM needs a human calibration.** The early QA agent's evaluator itself needed fixes (language detection) and gated nothing.
8. **Breadth first buys nothing.** None of the day-one infrastructure (queues, dual CRM, encryption layers) survived; the lack of evals cost months.
9. **Merged is not deployed; one sample is not a result.** Fixes were "done" in the repo and absent in production; scenario runs were single samples on other SHAs.
10. **The reflex to patch survives a rewrite.** Even with the right architecture, the first hard problem got word lists; only a written rule ("third round → schema") and a schema stopped it.

## 3. Mistakes made without understanding how an LLM works

These do not depend on the product domain.

| Belief | Reality | What to do instead |
|---|---|---|
| "If the rule is in the prompt, the LLM will follow it" | Instruction following is probabilistic and degrades with prompt length and competing rules | Put the rule in code or a schema; keep the prompt to identity and tools |
| "The LLM remembers what it said earlier" | It re-reads the context; it confabulates ids, URLs and facts from fragments | State in code, refs instead of ids, facts via slots |
| "Tell it to ground facts in tool data" | It still stitches plausible values (a real URL assembled from two products) | Renderer fills facts; typed facts rejected |
| "Temperature 0 makes it deterministic" | Same input, different outputs across calls and versions | Decide in code; evaluate with pass^k |
| "A bigger model will stop hallucinating" | Fewer, more convincing hallucinations | Close the paths, not the probability |
| "More context helps" | Old tool results and stale facts in context are read as current | Rebuild a small context every turn ([context.md](context.md)) |
| "The LLM can verify the LLM" | Same failure modes, slower, uncalibrated | Code checks against sources; calibrated judges only for style |
| "It said 'I'll check', so it will" | Nothing happens after the turn ends | Promises are tool calls with delivery (escalation card, scheduler) |

## 4. Where it arrived

- Prompt 8 000 characters; facts through slots; one retry then fallback + card.
- Strict answer schema with extracted values checked against the message; reply kind checked against verdicts.
- Local vision: identification in code with calibrated thresholds, $0 per call, ~1.4 s.
- Journal with provenance and cost; regression fixtures from the journal in CI; deploy by exact SHA.
- Input tokens per turn 5.7–8.0 k (median) instead of 52–73 k.
- Still open at the time of writing: calibration on phone photos, a detector with a commercial licence, orders and payments (stage 4), metrics and alerts, PR discipline.
