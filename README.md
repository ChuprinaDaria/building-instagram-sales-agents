# Building Instagram sales agents

A [Claude skill](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview) for designing, reviewing, fixing and growing LLM sales and support agents that work in Instagram DM (also Viber and WhatsApp) for shops of any product domain: clothing, electronics, cosmetics, spare parts and so on.

The skill enforces one architecture:

> **Code is fact, the LLM is interpretation.**
> Code produces facts (price, stock, identity of a unit), decisions (verdicts, statuses, escalations) and state (cart, refs, client card). The LLM reads the customer, fills a strict schema with what it understood, picks a tool and writes words with slots. Everything the LLM returns is a proposal that code accepts or rejects.

With this split the repo grows without patch-on-patch regressions. Without it, a sales agent tends to follow the same path: the prompt grows from 1 k to 85 k characters, post-generation guards start editing replies, most commits are fixes, and after a few months the whole thing is rewritten. The skill contains the history of one such production agent in numbers (732 commits, three architectures) and the protocol that prevents that path.

## Contents

- [What the skill does](#what-the-skill-does)
- [When Claude uses it](#when-claude-uses-it)
- [Installation](#installation)
- [Usage examples](#usage-examples)
- [The 25 rules](#the-25-rules)
- [Audit script](#audit-script)
- [CI template](#ci-template)
- [Evals](#evals)
- [Repository layout](#repository-layout)
- [Reference map](#reference-map)
- [Design of the skill](#design-of-the-skill)
- [Contributing](#contributing)
- [Author](#author)
- [License](#license)

## What the skill does

- **New agent.** Walks through a six-step setup: data sources and access paths, a decision card with an owner for every function, pydantic contracts for tools and answers, a skeleton (webhook with HMAC, inbox, turn lock, own tool loop, renderer, journal, CI), a regression runner with fixtures from the real journal, then capabilities one per phase (catalogue, memory, photo, humans, orders).
- **Review of an existing agent.** Runs a static audit, maps every finding to a rule and a failure mechanism, and proposes the smallest fix first.
- **Bug or regression.** Fixture first, mechanism named, fix at the owner of the decision, never a new layer downstream. Stop signs freeze patching in an area until a redesign is approved.
- **"Add this to the prompt".** Classifies prompt rules and knowledge `.md` files and migrates them into code. Only identity, tone and tool usage stay in the prompt.
- **Photo recognition and local models.** Identification ladder in code, calibrated verdicts persisted in state, choice of task type (detection, classification, retrieval) and model family (YOLO, SAM, DINO and others) with licences, datasets, labelling, Hugging Face, RunPod, training and quality gates.
- **Data and retrieval.** The shop DB is queried, not embedded. Vectors only for fuzzy text and images, with metadata filters, hybrid lexical and dense search, and a reranker. Store, embedder and reranker are chosen on your own labelled queries.

## When Claude uses it

Claude loads the skill when the conversation is about building or changing such an agent: fixing a bug in it, adding a rule to its prompt, choosing a framework, a vector store, an embedder, a reranker or a vision model for it, or reviewing its repo. You can also ask for it by name.

## Installation

The skill is a plain folder with `SKILL.md` at the root. Any Claude surface that supports skills can use it.

**Claude Code, personal (all projects):**

```bash
git clone https://github.com/ChuprinaDaria/building-instagram-sales-agents \
  ~/.claude/skills/building-instagram-sales-agents
```

**Claude Code, one project (shared with the team through git):**

```bash
cd your-agent-repo
git clone https://github.com/ChuprinaDaria/building-instagram-sales-agents \
  .claude/skills/building-instagram-sales-agents
rm -rf .claude/skills/building-instagram-sales-agents/.git   # or add it as a git submodule
```

**Claude apps and the API:** zip the folder (with `SKILL.md` at the top level of the archive) and upload it as a custom skill. See the [Agent Skills documentation](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview).

Requirements: Python 3.10+ for the audit script, standard library only. Nothing else is installed.

## Usage examples

Prompts that trigger the skill, and what it does with them:

| You write | The skill makes Claude |
|---|---|
| "Build a support bot for my shop on LangGraph, describe all rules in the system prompt." | Start with a decision card, name the rules against a framework by default and branching prose in the prompt, offer an own tool loop, design escalation with delivery confirmation |
| "Review this agent repo." | Run `audit_agent.py`, report the numbers, map findings to rules and mechanisms, check by hand what a script cannot see |
| "The bot told a customer the wrong price. Add a line to the prompt so it double-checks." | Refuse the prompt patch, record a failing fixture, find the owner of the price, move the price into a slot filled by the renderer |
| "Customers send photos, recognise the product with GPT." | Propose an identification ladder in code with a local model, a calibrated `decide()` and a persisted verdict; the LLM only phrases the reply |
| "Put the whole catalogue into a vector DB." | Route structured questions to SQL, keep vectors for fuzzy text and images with filters and a reranker, pick the store on your own queries |

If you insist on a prose rule, a framework or a long prompt, the skill states the rule it breaks and the measurable risk once, then does what you decide and records the deviation in the decision card.

## The 25 rules

Every rule has a check; a rule without a check is a wish. Full wording and checks are in [SKILL.md](SKILL.md).

1. Facts via slots: numbers, sizes, phones and ids typed by the LLM are rejected.
2. Customer values are extracted by the LLM and verified by code against the verbatim message.
3. Strict structured output for the answer and every tool code acts on.
4. Prompt = identity + tools + how to write slots; no branching prose.
5. Tools: one job, strict schema, structured errors, refs instead of raw ids.
6. Risky decisions by code with a calibrated threshold; "ask again" is a valid output.
7. Local model before LLM for recognition and classification when it matches or beats it; licences resolved.
8. Memory without chat logs in context: card and state by code, vectors with a tenant filter.
9. One writer per state field.
10. No framework by default: own tool loop over the provider SDK.
11. Escalation is never silence: delivery confirmed, first responder wins, TTL, customer informed.
12. Journal from day one with provenance, tokens, cost and latency; PII masked at write.
13. Wired or deleted: every limit, budget and flag reaches the code it controls.
14. Evals gate merges: fixtures from the real journal, in CI on the merged branch; deploy only a green SHA.
15. Modules with explicit interfaces: transport, state, tools, renderer, memory, journal.
16. Channel rules are code: messaging window, takeover by echo, rate limits.
17. Money is confirmed by systems, never by a screenshot or LLM text.
18. Checks reject, never rewrite: raise, retry, fallback.
19. Photo verdict is state; no LLM as the recogniser.
20. Social media is history, the shop DB is truth; stop on HTTP 429, never bypass blocks.
21. Change at the owner, fixture first.
22. The DB is queried, not embedded.
23. Prompt rules and knowledge files migrate to code, then the prose is deleted.
24. Small context rebuilt by code every turn.
25. Every fact the customer sees has a source record; unknown is a legal answer.

## Audit script

`scripts/audit_agent.py` is a static audit of an agent repo. It prints numbers to look at, not a verdict.

```bash
python scripts/audit_agent.py path/to/agent-repo \
  [--prompt FILE ...] \
  [--journal events.jsonl] \
  [--max-prompt-chars 8000] \
  [--allow-framework NAME ...] \
  [--ci]
```

What it reports:

| Section | Rule |
|---|---|
| Prompt size in characters and branching phrases (English and Ukrainian) | 4 |
| Agent framework imports (LangChain, LangGraph, CrewAI, LlamaIndex, AutoGen, Haystack, Semantic Kernel) | 10 |
| Disabled `strict` flags and the number of regex compiles per file | 3 |
| Upper-case constants that are defined and never referenced | 13 |
| Dependencies with licence obligations (for example Ultralytics, AGPL-3.0) | 7 |
| GitHub workflows and the branches they run on | 14 |
| Journal: share of events with empty cost, latency, tokens or model | 12 |
| Manual checks the script cannot see (raw ids, escalation delivery, one writer per field and others) | 5, 9, 11, 18, 19, 20 |

With `--ci` the exit code is 1 when a hard limit is crossed: prompt over the size limit, a framework without `--allow-framework`, `strict` disabled, no CI workflow, or journal fields empty in more than 10 % of events. Prompt files are found by name (`.md` or `.txt` with "prompt" in the file name); pass `--prompt` when the prompt lives elsewhere. `.git`, `node_modules`, virtual environments, build folders and `.claude/` are skipped.

## CI template

[templates/agent-audit.yml](templates/agent-audit.yml) runs the audit on every push and pull request, whether or not Claude loaded the skill. Copy it to `.github/workflows/agent-audit.yml` in the agent repo and set the branch you actually merge and deploy from. The template expects the skill at `.claude/skills/building-instagram-sales-agents/`; change the path if you vendored it elsewhere.

## Evals

[evals/evals.json](evals/evals.json) holds 19 evaluation queries in the format from Anthropic's [skill authoring best practices](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/best-practices). Each has a user query and a list of expected behaviours:

```json
{
  "skills": ["building-instagram-sales-agents"],
  "query": "Build a support bot for an online shop on LangGraph; describe all rules in the system prompt so it decides on its own when to escalate.",
  "expected_behavior": [
    "Does not start by writing a LangGraph agent or a long prompt",
    "Produces or asks to fill a decision card first",
    "Names rules 4 and 10 (prompt without branching, no framework by default) and offers an own tool loop",
    "Escalation designed with delivery confirmation and human approval, not a prompt rule"
  ]
}
```

Run each query with and without the skill on Haiku, Sonnet and Opus. A query passes when every expected behaviour is met.

## Repository layout

```
SKILL.md                  entry point: principle, terms, getting started, 25 rules, workflows, reference map
reference/                detailed guides, loaded only when a task needs them (one level deep from SKILL.md)
scripts/audit_agent.py    static audit of an agent repo, stdlib only
templates/agent-audit.yml GitHub Actions workflow that runs the audit
evals/evals.json          19 evaluation queries with expected behaviour
```

## Reference map

| Topic | File |
|---|---|
| Why code decides, where the boundary is | [principles.md](reference/principles.md) |
| What the LLM is for: online and batch roles, each with a schema | [llm-roles.md](reference/llm-roles.md) |
| What goes into a turn's context, what never does, token budget | [context.md](reference/context.md) |
| Source of truth: fact chain, precedence, writes, unknown as an answer | [source-of-truth.md](reference/source-of-truth.md) |
| Lessons from one production agent's history | [lessons.md](reference/lessons.md) |
| Architecture, turn pipeline, Instagram channel rules, module layout | [blueprint.md](reference/blueprint.md) |
| Build order, change protocol, stop signs, complexity budget | [growth.md](reference/growth.md) |
| Failure mechanisms M1-M9 and real incidents | [antipatterns.md](reference/antipatterns.md) |
| Data from source to what the LLM sees | [data-pipeline.md](reference/data-pipeline.md) |
| Sources: shop DB, CRM, Instagram, manager chats | [data-sources.md](reference/data-sources.md) |
| Moving prompt rules and knowledge files into code | [prompt-to-code.md](reference/prompt-to-code.md) |
| Decision card template and examples | [decision-card.md](reference/decision-card.md) |
| Answer schema, slots, renderer, turn loop | [slots-renderer.md](reference/slots-renderer.md) |
| Tools, MCP servers, own tool loop | [tools.md](reference/tools.md) |
| Memory: card, state, vectors, tenants | [memory.md](reference/memory.md) |
| Vector stores, embedders and rerankers, hybrid search, operations | [vectors.md](reference/vectors.md) |
| Journal schema and daily digest | [journal.md](reference/journal.md) |
| Evals and merge gate | [evals.md](reference/evals.md) |
| Photo recognition: identification ladder, verdicts | [vision.md](reference/vision.md) |
| Local models: task type, model families, licences, architectures | [local-models.md](reference/local-models.md) |
| Datasets, labelling, Hugging Face, RunPod, training, gates | [datasets-and-training.md](reference/datasets-and-training.md) |
| Names in inflected languages (Ukrainian) | [morphology.md](reference/morphology.md) |

## Design of the skill

The skill follows Anthropic's authoring guidance:

- **Progressive disclosure.** Only the name and description (under 1024 characters) are always in context. `SKILL.md` stays under 500 lines (134 now) and links to reference files one level deep; reference files over 100 lines start with a table of contents.
- **One term, one meaning.** LLM, local model, unit, ref, slot, verdict, decision card, journal and fixture are defined once in `SKILL.md` and used the same way everywhere.
- **Checks over advice.** Every rule names a test, a measurement or an audit line. Deterministic checks live in a script, so they run the same way with or without the model.
- **Domain-independent.** Examples cover clothing, electronics, cosmetics and spare parts; nothing is tied to one shop.

## Contributing

Issues and pull requests are welcome. A new rule needs a check and an eval query; a new reference file needs a line in the reference map of `SKILL.md` and must stay one level deep. Keep the whole skill in English.

## Author

**Daria Chuprina**, AI engineer, CV Embedded. **MILFTECH**

- GitHub: [@ChuprinaDaria](https://github.com/ChuprinaDaria)
- Website: [lazysoft.pl](https://lazysoft.pl)
- Email: [chuprina.dariia@gmail.com](mailto:chuprina.dariia@gmail.com)
- Instagram: [@dormouse.weirdo](https://www.instagram.com/dormouse.weirdo)

## License

**[The Chuprina Glory License 1.0](LICENSE): do whatever you want, just make the author famous.**

<p align="center"><img src=".github/glory.gif" width="180" alt="The author, on learning that someone credited her properly"><br><sub><i>The author, on learning that someone credited her properly.</i></sub></p>

Use it, fork it, change it, translate it, sell it, build a product on it. Commercial or not, free. The price is glory: keep the licence file with every copy, and in anything built on this skill name the author where people actually look (README, docs, credits page):

> Based on "Building Instagram sales agents" by Daria Chuprina (https://github.com/ChuprinaDaria/building-instagram-sales-agents).

Do not pretend you wrote it. No warranty: if your agent sells the wrong size, take it up with your decision card.
