# Photo recognition

Customer sends a photo, screenshot or story reply; the agent must say which sellable unit it is, or honestly ask. This file is about the architecture around the models and is domain-agnostic; fashion and electronics are the two worked examples. Training recipes: [local-models.md](local-models.md). The sellable unit and its identifiers: [data-pipeline.md](data-pipeline.md) §2.

## Identification ladder

Code climbs from the most exact evidence to the least, and stops at the first rung that gives a unit. Every rung is code or a local model; the LLM only writes words for the result.

| Rung | Evidence | How | Typical domains |
|---|---|---|---|
| 1. Our own media | story reply, shared post, screenshot of our product page | media id / permalink / URL → unit table | all |
| 2. Printed identifiers | barcode / QR / EAN on box, model number on label, serial sticker, "About phone" screenshot | barcode decoder, OCR → identifier lookup | electronics, cosmetics, spare parts |
| 3. Read attributes | brand logo, text on device, category, colour | local classifiers / detector classes / OCR / Lab colour | all |
| 4. Visual similarity | appearance | detector/segmentation → domain embedder → nearest catalogue images | fashion, furniture, decor |
| 5. Ask | nothing above is decisive | verdict `UNSURE` with candidates, or a targeted question | all |

Then `decide()` in code turns the evidence into a verdict with a calibrated threshold.

**Why the ladder matters per domain.**
- Fashion: rung 4 is strong (appearance is the product), colour decides the unit, so rung 3 colour distance in Lab is part of `decide()`.
- Electronics: generations look alike (iPhone 14 vs 15, S23 vs S24), and storage, RAM, region and condition are **invisible**. Rung 4 can at most narrow to a model family; the unit needs rung 2 (box label, EAN, settings screenshot) or a question. Never infer storage or condition from a photo.
- Spare parts: rung 2 (part number) or a compatibility question; similarity alone sells the wrong part.

## Verdict contract

Example set: `CLOSE` (one unit, confident), `FAMILY` (model family known, variant not: ask the variant), `UNSURE` (ask with candidates), `COLOUR` (model right, colour differs), `OTHER_CLASS` (not something we sell), `WIDE` (several items in frame), `LOW` (quality too low). The verdict and candidate refs go into turn state; the reply schema carries `kind`/`options`, and code rejects a reply that names one unit on anything but `CLOSE`.

## Rules

1. **No LLM as the recogniser or verifier.** Measured: an LLM reranker over top-5 took 22–25 s per call (timeouts), picked a confident wrong item 14 % of the time and let rejected candidates leak into context, so the customer heard another item's colour and price. The local pipeline: ~1.4 s median, $0 per call, higher precision at "confident".
2. **Calibrated threshold, not a raw score.** A "confident" verdict at raw similarity 0.53 on a selfie matched a random jacket. Calibrate on held-out data (temperature scaling as a baseline, isotonic with enough data); a handful of buckets on under 200 examples is too few to trust.
3. **"Ask again" is a product feature.** Precision at "confident" 54 % → 88.5 % came from the confident share 204 → 26 of 305. Report both numbers together. Raise the share with data, not by lowering the threshold.
4. **Per-domain metrics.** Studio photos 96 % → phone photos 73 % on the same chain. Build a test set from real DMs (≥ 300) before claiming accuracy. A test whose images are in the index (self-match 1.0) is a greenhouse; say so.
5. **The verdict is state.** Persist verdict + candidates with the turn's №N. A photo description kept only in an expiring cache produced "which one do you mean?" loops, and none of 114 photo escalations could be recovered.
6. **The LLM follows the verdict, enforced by code**, not by prompt rules (six rounds of word lists did not work; a strict reply schema did).
7. **Index hygiene.** One image linked to several units eats the top-k. Deduplicate by perceptual hash + embedding, map image → set of units, drop inactive units.
8. **Licences before handover.** Detector weights trained on non-commercial data and AGPL runtimes block delivery to a client. Check in the decision card; permissive open-vocabulary detectors exist, and a detector often adds little (+1.3 p.p. measured), so replacement is cheap.
9. **Isolation.** The vision service gets no secrets and no outbound network; customer photos never leave it.

## Checks

- Held-out test split by photo session / source, used once per decision.
- Report per domain and per rung: share resolved at each rung, top-1, precision at confident, confident share.
- Regression fixtures: recorded OCR/barcode/embedding outputs → expected verdict, $0.
- Journal: rung reached, verdict, latency, candidates shown.
