# Vector search: stores, embedders, rerankers

Vectors answer fuzzy questions over text and images. They do not replace the database ([data-pipeline.md](data-pipeline.md) §6). This file is about choosing and running the three parts: the store, the embedder and the reranker, local or hosted.

## Contents
1. What to embed
2. Pipeline
3. Vector stores
4. Embedders
5. Rerankers
6. Hybrid search
7. Choosing: a decision procedure
8. Operations
9. Evaluation

## 1. What to embed

- Short curated text per unit (name + aliases + key attributes as words) for fuzzy name lookup.
- Descriptions for "something like this".
- Policies, FAQ, warranty and return terms, chunked by meaning (a section or a question-answer pair), with metadata: source, version, section, language.
- Manager answers and tone examples (PII masked).
- Customer memory snippets (tenant in payload).
- Images for recognition (separate collection, separate embedder).

Never embed prices, stock or statuses as the thing you answer from.

## 2. Pipeline

```
query ─► (LLM query rewrite: search terms + unknown terms, strict schema)
      ─► metadata filter (tenant, language, category, active)          code
      ─► dense search (+ sparse / BM25 in parallel)                    store
      ─► fuse (RRF or weighted)                                         code
      ─► rerank top 20–50 with a cross-encoder / rerank API            reranker
      ─► re-apply filters (tenant, active) after rerank                 code
      ─► top 3–5 with scores and ids → tool result                      code
      ─► journal: scores at every stage, model names and versions
```

Reranking is required for production answers; embedding similarity alone orders near-duplicates badly.

## 3. Vector stores

| Store | Runs | Licence | Pick when |
|---|---|---|---|
| pgvector (Postgres) | self-hosted / managed Postgres | PostgreSQL | you already run Postgres, up to a few million vectors, want SQL filters and joins in one place |
| Qdrant | self-hosted / Qdrant Cloud | Apache-2.0 | payload filters, named vectors (dense + sparse in one point), multitenancy (`is_tenant`), quantisation |
| Weaviate | self-hosted / Weaviate Cloud | BSD-3 | built-in hybrid search and modules |
| Milvus / Zilliz Cloud | self-hosted / hosted | Apache-2.0 | very large collections, GPU indexes |
| OpenSearch | self-hosted / managed | Apache-2.0 | you already need full-text search; kNN + BM25 in one engine |
| Elasticsearch | self-hosted / Elastic Cloud | check (AGPL / SSPL / Elastic License) | existing Elastic stack |
| Vespa | self-hosted / Vespa Cloud | Apache-2.0 | complex ranking at scale |
| LanceDB | embedded / cloud | Apache-2.0 | serverless or local files, multimodal data, no server to run |
| Chroma | embedded / server | Apache-2.0 | prototypes and small local projects |
| Redis (vector search) | self-hosted / Redis Cloud | check (licence changed across versions) | you already run Redis and need low latency on small sets |
| Pinecone, Turbopuffer, Vertex AI Vector Search, Azure AI Search | hosted only | proprietary | no ops capacity; data residency and cost reviewed |

Default for a shop agent: **the database you already run**, if it has vector support and your scale fits; otherwise Qdrant self-hosted. One collection per data kind, tenant in the payload, not one collection per customer.

## 4. Embedders

Check licence, languages, dimensions, max input length and whether it supports query/document instructions. Licences below are as published; re-check before delivery.

| Embedder | Where | Licence | Notes |
|---|---|---|---|
| BGE-M3 | local | MIT | multilingual; dense + sparse + multi-vector from one model; good hybrid default |
| multilingual-e5 (base, large) | local | MIT | solid multilingual baseline; needs "query:" / "passage:" prefixes |
| Qwen3-Embedding (0.6B / 4B / 8B) | local | Apache-2.0 | strong multilingual; instruction-aware; heavier |
| snowflake-arctic-embed2 | local | Apache-2.0 | multilingual, compact |
| mxbai-embed-large | local | Apache-2.0 | English-centred; check quality on your language |
| nomic-embed-text | local | Apache-2.0 | long inputs; English-centred |
| jina-embeddings-v3 | local weights / API | CC BY-NC 4.0 for weights | non-commercial weights: use the paid API or another model for client work |
| Cohere embed (multilingual v3, v4) | API | proprietary | strong multilingual; data leaves your infra |
| OpenAI text-embedding-3 (small, large) | API | proprietary | adjustable dimensions |
| Voyage, Google Gemini embeddings | API | proprietary | check languages and region |
| Image: SigLIP / CLIP / DINOv2 / domain fine-tunes | local | see [local-models.md](local-models.md) | separate collection from text |

Local vs hosted: local keeps client conversations inside your infrastructure and costs nothing per call; hosted saves ops. Choose on **your labelled queries**, not on public leaderboards: quality on your language, your product vocabulary and your slang is what matters. An embedder that runs on a GPU box on the LAN (e.g. via Ollama or text-embeddings-inference) is local too, but it is a dependency: log and degrade gracefully when it is down.

## 5. Rerankers

| Reranker | Where | Licence | Notes |
|---|---|---|---|
| bge-reranker-v2-m3 | local | Apache-2.0 | multilingual cross-encoder; default local choice |
| Qwen3-Reranker (0.6B / 4B / 8B) | local | Apache-2.0 | strong, heavier; the small one runs on CPU for top-20 |
| mxbai-rerank | local | Apache-2.0 | check your language |
| jina-reranker | local weights / API | check (some versions CC BY-NC) | non-commercial weights need the API for client work |
| Cohere Rerank | API | proprietary | strong multilingual |
| Voyage rerank | API | proprietary | — |

Rerank 20–50 candidates, not 1 000. Log rerank scores; a threshold on the rerank score (calibrated) decides "nothing relevant" → tool returns `not_found`.

## 6. Hybrid search

Dense embeddings miss exact tokens (model numbers, SKUs, brand spellings); lexical search misses paraphrases. Use both.
- Sparse or BM25 alongside dense: Qdrant named vectors (dense + sparse), BGE-M3 sparse output, Postgres `tsvector` + pgvector, OpenSearch/Elasticsearch BM25 + kNN.
- Fuse with reciprocal rank fusion; then rerank.
- Exact identifiers never rely on either: they go to SQL.

## 7. Choosing: a decision procedure

```
Vector setup:
- [ ] List the question types that really need fuzzy search (data-pipeline.md §5)
- [ ] Build 50–200 labelled queries from the journal / real chats, per type and language
- [ ] Baseline: store you already run + one local multilingual embedder + one local reranker
- [ ] Compare against one hosted embedder/reranker on the same queries (recall@5, MRR, latency, cost)
- [ ] Decide on numbers + privacy + ops; record in the decision card with licence
- [ ] Freeze model names and versions in the collection metadata
```

## 8. Operations

- **Model change = re-index.** Dimensions and vector spaces differ between embedders; store `embedder_name`, `version`, `dim` with the collection and refuse mixed collections.
- **Metadata on every point:** source id, unit id or document id, version, language, tenant, created_at. Facts are fetched by id from the source at answer time.
- **Freshness:** re-embed only changed documents; delete points for removed units in the same sync job.
- **Quantisation** (scalar / binary) when memory matters; measure recall after it.
- **Tenancy:** one collection per data kind, tenant from code, filter on every query, re-check after rerank.
- **Degradation:** if the store, embedder or reranker is down, the turn continues without retrieval and the journal records it; a silent empty result is a bug.

## 9. Evaluation

- Labelled queries from real conversations, per question type and per language: recall@k, MRR or nDCG, "nothing relevant" precision.
- Run in CI on a frozen snapshot of the index with recorded embeddings ($0); re-run live after any model change.
- Journal: dense, sparse, fused and rerank scores for the returned items; the digest reports empty-result rate and backend errors.
