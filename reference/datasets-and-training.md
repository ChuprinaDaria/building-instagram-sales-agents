# Datasets, labelling, Hugging Face, RunPod, training

How to get from "we have a catalogue and some customer photos" to weights that pass a deploy gate. Task type and model family: [local-models.md](local-models.md).

## Contents
1. Workflow checklist
2. Collect data
3. Taxonomy and labelling
4. Clean, deduplicate, split
5. Hugging Face: storage and versioning
6. RunPod: compute
7. Training recipes
8. Evaluation and deploy gate
9. Cost control

## 1. Workflow checklist

```
Local model progress:
- [ ] Question → task type chosen (local-models.md §1)
- [ ] Baseline measured with an off-the-shelf model on a held-out set
- [ ] Data collected with consent and provenance; taxonomy written
- [ ] Pseudo-labels generated, human-verified sample ≥ 10 % (all of val/test)
- [ ] Deduplicated; split by source/session; test frozen
- [ ] Dataset versioned on Hugging Face (private)
- [ ] Deploy gate thresholds written before training
- [ ] Training run on RunPod with cost estimate and cap; weights pushed to Hugging Face
- [ ] Evaluated once on test; per domain; negative result recorded if it fails
- [ ] Threshold recalibrated; licence recorded; exported; shipped behind the gate
```

## 2. Collect data

| Source | Gives | Caveats |
|---|---|---|
| Shop catalogue photos | clean images per unit, all angles | studio domain; must not be the only test domain |
| Customer DMs (journal) | real phone photos, screenshots, bad light | consent and PII; mask faces/names where not needed; the most valuable test set |
| Brand's Instagram (export or API) | worn items, outfits, reels frames | legal access only; reels frames deduplicated; posts ≠ current catalogue |
| Manager-confirmed answers | labels for customer photos ("it was №1234") | the cheapest high-quality labels; log them from day one |
| Synthetic renders (e.g. Blender) | rare angles, controlled light, exact labels | supplement only; never report metrics on synthetic data as production metrics |

Target: a phone-domain test set of ≥ 300 real customer photos before claiming accuracy.

## 3. Taxonomy and labelling

- Write the class list and the unit definition first (data-pipeline.md §2); every label maps to it.
- Pseudo-label, then verify: open-vocabulary detector (Grounding DINO or OWLv2) → boxes, SAM 2 → masks, current embedder → candidate units. Humans only confirm or correct.
- Tools: Label Studio (Apache-2.0) as default; CVAT (MIT) for heavy box/mask work.
- Record who labelled what, when, with which pre-label model; disagreements go to a second reviewer.
- Imbalance is normal (few photos of rare items); report per-class metrics, do not hide the tail in an average.

## 4. Clean, deduplicate, split

- Deduplicate before splitting: perceptual hash for exact/near copies, embedding similarity for re-compressed Instagram images and consecutive reel frames.
- Split by **source**: photo session, shoot, post, customer. Random splits leak near-duplicates into test and inflate metrics.
- Two evaluation modes for retrieval: leave-one-out (other photos of the unit are in the index) and strict (none are).
- A test whose images are in the production index (self-match 1.0) is a greenhouse test; label it as such.
- Freeze the test split; iterate on validation only.

## 5. Hugging Face: storage and versioning

- **Datasets and weights in private repos** on the Hub (`huggingface_hub`); one repo per dataset, one per model; a commit per version; the SHA goes into the training report and the decision card.
- Dataset card: sources, consent, taxonomy, split rule, licence, known gaps. Model card: base model and licence, data version, metrics per domain, threshold, intended use.
- Load with `datasets` for training; push checkpoints from the training machine, not from a laptop.
- A private **Space** is a good place for a human review viewer (side-by-side: customer photo, predicted unit, catalogue photo) shared with the team.
- Never upload customer photos to public repos; access tokens with the narrowest scope, stored as secrets on the training machine.

## 6. RunPod: compute

- **Pods** for training: pick a GPU by VRAM need (retrieval fine-tuning of a base-size embedder fits on 24 GB; large detectors and ViT-L need more), attach a **network volume** for datasets and checkpoints so a stopped pod loses nothing.
- Start from a PyTorch template image, install pinned requirements from the repo, pull data from Hugging Face, push checkpoints back.
- Stop the pod when the run ends; a script that trains, evaluates, pushes and then shuts the pod down is part of the recipe.
- **Serverless endpoints** only for bursty batch jobs (bulk embedding of a new catalogue, pseudo-labelling); production inference of small models usually runs on CPU next to the agent.
- Check current GPU prices before estimating; they change.

## 7. Training recipes

**Retrieval (unit identity)**
1. Baseline: off-the-shelf embedder (FashionSigLIP for fashion, DINOv2/SigLIP otherwise), kNN over catalogue crops.
2. Fine-tune with an angular-margin loss (ArcFace) on unit id; balanced sampling per unit; augmentations that mimic phones (blur, JPEG, perspective, colour cast) but keep colour when colour defines the unit.
3. Evaluate r@1, r@5, "right unit first", both modes, per domain.

**Coarse classification** (image type, device type): linear probe on frozen DINOv2/SigLIP features first; full fine-tuning only if the probe misses the gate.

**Detection/segmentation**: fine-tune a permissive detector (RF-DETR / RT-DETR) on verified pseudo-labels; distil from an open-vocabulary teacher when latency matters.

**Calibration**: on a held-out calibration split, map raw scores to probabilities (temperature scaling as baseline, isotonic with enough data); a few buckets on under 200 examples are not a calibration.

## 8. Evaluation and deploy gate

- Gate thresholds written before training: e.g. r@1, precision at "confident", confident share, per domain, latency on target CPU.
- Test used once per decision. If the run fails the gate, write the negative result down and do not deploy: fine-tuning on customer feedback photos once made strict r@5 worse (0.815 → 0.772) for $2.36; the method caught it.
- Weights ship only through the gate and the owner's yes; the threshold is recalibrated on the new weights.
- Regression fixtures store recorded scores/embeddings for fixed images, so `decide()` stays tested at $0 after every change.

## 9. Cost control

- Estimate before running: GPU hours × price, API calls × price; set a hard cap (`--max-usd`) in scripts that call paid APIs.
- Log the actual cost next to the results in the training report.
- Batch LLM work (caption and comment parsing) in strict-schema batches with code validation; spread it over days when a subscription limit, not money, is the constraint.
