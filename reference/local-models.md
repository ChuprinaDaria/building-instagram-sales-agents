# Local models: task type, model families, architectures

When a local model beats or matches the LLM on held-out domain data, it owns the function: faster, $0 per call, data stays in your infrastructure, calibratable. Code then decides from its score ([vision.md](vision.md)). Dataset, labelling, Hugging Face, RunPod and training recipes: [datasets-and-training.md](datasets-and-training.md).

## Contents
1. Choose the task type first
2. Model families and licences
3. Reference architectures by domain
4. Small local LLMs
5. Shipping

## 1. Choose the task type first

The task type follows from the question the agent must answer, not from a favourite model.

| Question | Task type | Output | Pick when | Do not pick when |
|---|---|---|---|---|
| "What kind of image is this?" (garment / our post screenshot / order document / unrelated) | **Classification** | one label per image | a small, stable set of classes | classes change weekly (every new SKU) |
| "Where are the items and what are they?" | **Detection** | boxes + class | several objects per image, crops needed for the next step | one centred object per image (classification or retrieval is enough) |
| "Exactly which pixels?" | **Segmentation** | masks | background must be removed (colour measurement, clean crop) | a box crop is good enough |
| "Which catalogue unit is this?" | **Retrieval** (embedding + nearest neighbours, metric learning) | ranked units + scores | hundreds to thousands of units, catalogue changes; new units added by indexing, no retraining | a handful of fixed classes |
| "What is written on it?" | **OCR / barcode** | text, EAN, model number | identifiers are printed (electronics, cosmetics, parts) | appearance is the product (fashion) |
| "Is there any X in the image?" with no training data yet | **Open-vocabulary detection** | boxes for text prompts | zero-shot start, pseudo-labelling a dataset | latency matters in production (distil into a small detector) |

Rule of thumb: **never train a classifier with one class per SKU.** It breaks on every catalogue update. Use retrieval for identity, classification for coarse type, detection or segmentation to produce crops.

## 2. Model families and licences

Check the licence of **both code and weights** and record it in the decision card. Licences below are as published by the projects; re-check before a client delivery.

| Family | Task | Licence | Notes |
|---|---|---|---|
| Ultralytics YOLO (detect, segment, classify) | detection, segmentation, classification | AGPL-3.0 or paid Enterprise | fast, easy to train; AGPL obliges you to open the whole service or buy a licence |
| RF-DETR (Roboflow) | detection, segmentation | Apache-2.0 | transformer detector designed for fine-tuning; commercially free |
| RT-DETR (Hugging Face `transformers`) | detection | Apache-2.0 | good default when AGPL is not acceptable |
| YOLO-World | open-vocabulary detection | GPL-3.0 | copyleft; avoid in a delivered product |
| OWLv2 | open-vocabulary detection | Apache-2.0 | zero-shot boxes; pseudo-labelling |
| Grounding DINO | open-vocabulary detection | Apache-2.0 | strong zero-shot; pair with SAM 2 for masks |
| Florence-2 | detection, captioning, OCR, grounding | MIT | one small model for several vision tasks |
| SAM 2 | promptable segmentation | Apache-2.0 | masks from a box or a point |
| SAM 3 | segmentation by concept prompts | SAM License (custom, Meta) | read the terms before commercial use |
| DINOv2 | general visual features (backbone) | Apache-2.0 | kNN / linear-probe baseline for retrieval and classification |
| DINOv3 | general visual features | DINOv3 License (custom, Meta) | commercial use allowed under its terms; redistribution must carry the licence |
| CLIP / SigLIP / SigLIP 2 | image–text embeddings | MIT / Apache-2.0 | text search over images, zero-shot classes |
| Marqo-FashionSigLIP | fashion embeddings | Apache-2.0 | strong base for fashion retrieval |
| PaddleOCR | OCR | Apache-2.0 | text and model numbers on labels and screens |
| zxing / pyzbar | barcodes, QR | Apache-2.0 / MIT | EAN on boxes; deterministic |

Datasets carry licences too: a detector fine-tuned on a non-commercial dataset (e.g. DeepFashion2) inherits the restriction.

## 3. Reference architectures by domain

**Fashion (appearance is the product)**
```
image → classifier (garment / screenshot / document / other)
      → detector or segmenter (RF-DETR, YOLO-seg, or Grounding DINO + SAM 2) → crops
      → FashionSigLIP fine-tuned with ArcFace on unit id → kNN over catalogue crops
      → Lab colour ΔE vs swatches → decide(): CLOSE / COLOUR / UNSURE / WIDE / OTHER_CLASS
```
Measured in the reference shop: right unit first in 59 % vs 21 % for an LLM-verifier path; precision at "confident" 88.5 % at a small confident share; ~1.4 s median on CPU; the detector added only +1.3 p.p., so it is the cheapest part to replace for licensing.

**Electronics (identifiers decide, appearance only narrows)**
```
image → own-media lookup (story/post id) → barcode (zxing) → OCR (PaddleOCR or Florence-2) on labels, box, "About phone" screens
      → brand/logo + device-type classifier (linear probe on DINOv2 features)
      → DINOv2/SigLIP kNN to a model family → decide(): CLOSE (identifier found) / FAMILY (ask storage, condition) / UNSURE
```
Storage, RAM, region and condition are invisible; the verdict never claims them.

**Cosmetics and shades**: barcode → OCR of the product name → colour measured on a segmented swatch (SAM 2 mask, Lab ΔE, white-balance check) → `UNSURE` when lighting is unreliable.

**Spare parts and accessories**: OCR of the part number → cross-reference table → compatibility table; similarity only proposes candidates.

**Screenshots and documents** (order confirmations, payment screenshots, delivery notes): a classifier routes them away from product recognition; OCR extracts references for a human or a system check, never as payment confirmation.

## 4. Small local LLMs

For classification, extraction and summaries where hosted cost or privacy matters.
- Strict JSON output + code validation, same contract as for the hosted LLM.
- Measure per model **generation**, not size: a translate-answer-translate trick helped an older 3B model (+62 clean answers of 200) and hurt newer 4B+ models (−11 to −14) while adding calques.
- Check the chat template: some local builds always open a thinking block; up to 29 % of answers were reasoning instead of text until a no-think template and a leak detector were added.

## 5. Shipping

- Export to ONNX (or TorchScript) for CPU inference; pin CPU/GPU wheels; measure latency on the target machine.
- Vision service as a separate container: no secrets, no outbound network, customer images never leave it.
- Dev-only dependencies (training libraries, labelling tools, morphology dictionaries) stay out of the runtime image; ship frozen artefacts (weights, indexes, tables) with a version and a source line.
- Recalibrate the decision threshold after every weight change.
