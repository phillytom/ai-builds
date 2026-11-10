# 03 · RAG support bot with pgvector

> **Status:** Shipped Nov 10 · **Target:** Fri Sep 25 · **Timebox:** 2 hours

| Claude Haiku 5.5, same 10 questions as session 02 | quality (of 20) | all-correct answers | needed chunks retrieved | citations that point at a retrieved chunk | prompt tokens per question | median time | cost per question | cost per day at 1,000 questions |
|---|---|---|---|---|---|---|---|---|
| Whole handbook in the prompt (no retrieval, cached) | 18 (20 \*) | 9/10 | all | n/a | 50,783 | 6.2 s | $0.0017 | $1.68 |
| RAG, vector search, top 8 (the naive version) | 15 | 6/10 | 71% | 42/42 | 2,764 | 6.6 s | $0.0009 | $0.89 |
| RAG, hybrid search, top 8 | 15 | 5/10 | 74% | 42/42 | 2,927 | 7.1 s | $0.0009 | $0.93 |
| **RAG, vector search, top 16** | 16 (18 \*) | 7/10 | **95%** | 50/50 | 4,948 | 6.5 s | $0.0012 | $1.20 |

10 customer questions × 4 modes, 40 answers, run on 2026-11-10, graded 0–2 per question by Claude Haiku 4.5 against session 02's hand-written answer keys. \* Two of the zeros are the judge's mistake, not the bot's (Q08, below). The scores in the table are as graded; the grades were not edited after the run. Every answer, retrieved chunk, citation, timing and judge reason is in [results.json](results.json).

**Retrieval alone** (no model answering, `npm start -- --retrieval`): the share of the chunks a correct answer needs that make it into the top k.

| Search | top 4 | top 8 | top 12 | top 16 | top 24 |
|---|---|---|---|---|---|
| Vector | 44% | 71% | 82% | **95%** | 95% |
| Hybrid (vector + IDF-weighted keywords) | 51% | 74% | 85% | 87% | 95% |

**What the numbers say**

- **Every point RAG lost traces to a chunk retrieval missed.** Apart from the judge's two mistakes, no RAG answer went wrong when it had the right chunks. The model stayed inside its sources: all 134 citations point at a chunk it was actually given, and when a needed fact was missing it usually said so instead of guessing.
- **How many chunks you pass matters more than how you search.** Going from 8 to 16 chunks lifted retrieval from 71% to 95% and quality from 15 to 16 (18 counting the judge's error). It costs about 2,200 more prompt tokens a question: $0.0003 more per question on Haiku 5.5.
- **Hybrid search didn't pay here, on average.** It wins where a rare word is the clue. On Q10 (WELCOME10), it fetched §4.3, the section that says promo codes don't apply to bundles. Vector search missed it, and that bot applied 10% to the bundle (0 of 2; hybrid scored 2). It loses where the question is in everyday words: the Honolulu shipping question (Q02) and the final-sale price question (Q04), where it dropped a section vector search had found. At 8 chunks the two cancel out: 15 points each.
- **The first hybrid version made retrieval worse (68% vs 73% at top 8 before the Q10 relabel).** It used Postgres's built-in full-text ranking, which doesn't know how rare a word is. A customer question matched 170–222 of the 230 chunks on words like "order" and "bought", and that noise pushed good chunks out of the top 8. Adding an IDF weight per word (the core of BM25, from `ts_stat`) brought it level.
- **Some facts can't be found by searching for the question.** Q01 asks for the refund on one piece of a bundle. The formula needs the list prices of all three pieces, but the customer only names the bundle and the saucepan. No search finds the two skillets' prices, so every RAG mode got the rule right but couldn't give the $43.30. The whole-handbook prompt has no such blind spot. Cross-references hurt in the same way: §4.4 says "all the rules in 4.3 apply", and retrieval fetched 4.4 without 4.3.
- **The whole handbook still wins at this size.** With caching, 51k tokens on Haiku 5.5 cost $0.0017 a question: $1.68 a day at 1,000 questions, against $1.20 for the best RAG mode. Speed was the same; Haiku's thinking time dominates, and retrieval adds about 0.6 s (one Gemini embedding call plus one Postgres query). RAG's cost advantage only shows once the content stops fitting comfortably in a prompt.

**Q08, the judge's mistake.** The customer wants to return an engraved knife. The answer key's forbidden claim is "says it can be returned *because* the catalog's final_sale column says no". Two correct answers (whole handbook and vector top 16) said no return, final sale, warranty still covers defects, and also pointed out that the catalog column reads "no" while the description says engraved items are final sale. The judge read that mention as the forbidden claim and gave 0. Better judging is session 04's job.

## The brief

A support bot that answers only from the store's help center and catalog, and cites what it used. Get the naive version working first. Then add a reranker (or hybrid search) and record what changes.

- **Touch:** Embeddings, pgvector on Neon Postgres, a reranker or hybrid search
- **Reuses:** `data/policies`, `data/catalog-export.csv`, session 02's questions, answer keys, judge and whole-handbook prompt
- **Done when:** 10 sample questions answered with citations, before and after reranking.

## What I built

**Chunks.** [chunks.ts](chunks.ts) cuts the shared data into 230 pieces:

- 73 policy chunks, one per `##` section of the nine handbook pages. Each chunk's id is its section number (`§1.8`), or `faq-orders` and so on for the unnumbered FAQ sections. Each starts with "page › heading" so it makes sense on its own.
- 157 product chunks, one per SKU (`KT-2027`). The 217 variant rows of the catalog export are folded together: shared fields once, then one line per color or size with its stock.

**The database.** [ingest.ts](ingest.ts) rebuilds one Postgres table on Neon: id, source, title, text, a generated `tsvector` column for keyword search, and a `vector(1536)` embedding, with an HNSW index for cosine distance and a GIN index for full text. It also builds a `terms` table of IDF weights (`ln((N − n + 0.5) / (n + 0.5) + 1)`, the BM25 formula) from Postgres's own word counts. Embedding all 230 chunks takes 38,452 tokens and costs half a cent.

**Search.** [search.ts](search.ts) has the two retrievers:

- `vectorSearch`: embed the question, then `ORDER BY embedding <=> question LIMIT k`. That's it.
- `hybridSearch`: the top 30 by vector distance and the top 30 by keyword score (the summed IDF of the question's words each chunk contains), merged with reciprocal rank fusion (each list contributes `1 / (60 + rank)`), then the top k. All in one SQL query.

**The bot.** [bot.ts](bot.ts) has four modes. All use Claude Haiku 5.5 with adaptive thinking at effort medium:

| Mode | What the model sees |
|---|---|
| `full` | Session 02's system prompt: instructions plus the whole handbook and catalog (51k tokens), with `cache_control`. The baseline. |
| `vector-8` | The top 8 chunks by vector search, wrapped as `<source id="§1.8">…</source>`, plus the question |
| `hybrid-8` | The top 8 chunks by hybrid search |
| `vector-16` | The top 16 chunks by vector search |

The RAG prompt is session 02's instructions plus two rules: answer only from the sources, and cite the id of the source after each fact, like `[§1.8]`. The harness pulls the cited ids out of the answer and checks each against the retrieved list.

**Scoring.** [run.ts](run.ts) asks all 10 questions in every mode and grades each answer with session 02's judge (Claude Haiku 4.5, same prompt, same answer keys). Retrieval is scored separately against [gold.json](gold.json): for each question, the chunks a correct answer needs, labelled by hand from the answer keys. One label was fixed after the first run (Q10 also needs §4.3) and the file says so.

**One change from the plan:** the embeddings are Google's `gemini-embedding-001`, cut to 1,536 dimensions, with separate document and query modes. The plan was OpenAI's `text-embedding-3-small`, but the OpenAI key on file had been revoked. Google lists a newer `gemini-embedding-2`. I didn't use it because sources disagree on whether it supports the document and query modes.

Versions: `@anthropic-ai/sdk` 1.7.0, `@google/genai` 3.0.0, `@neondatabase/serverless` 1.2.0 (HTTP queries), pgvector 0.8.6 on Neon (Postgres 17), `zod` 4.6.7, Node 26. Models: `claude-haiku-5-5` (answers), `claude-haiku-4-5` (judge), `gemini-embedding-001` (embeddings).

## How to run it

You need Node 22 or newer, a Neon Postgres database (the free plan is plenty), an Anthropic API key and a Gemini API key.

```bash
cd ai-builds
cp .env.example .env.local        # then fill in ANTHROPIC_API_KEY, GEMINI_API_KEY and DATABASE_URL
cd 03-rag-pgvector
npm install
npm run ingest                    # builds the tables and embeds 230 chunks, about 8 seconds and half a cent
npm start -- --retrieval          # retrieval-only table, embeddings only, a fraction of a cent
npm run ask -- "Can I ship to Canada?"            # one question, vector top 16 by default
npm run ask -- --mode=hybrid-8 "Can I ship to Canada?"
npm start                         # 40 answers plus 40 judge calls, about 6 minutes and 10 cents
```

`DATABASE_URL` is the connection string from the Neon console's **Connect** button. `npm run ingest` turns on the `vector` extension itself. `npm start` writes every answer to `results.json` as it goes. `npm start -- --report` reprints the tables without calling any API, and `npm start -- --rescore` re-runs only the judge (about 5 cents).

To change how many chunks a mode passes, edit `MODES` in [bot.ts](bot.ts) (`vector-12` and `hybrid-24` work as written). Model names and prices are at the top of [shared.ts](shared.ts).

## What surprised me

_TODO (Tom writes this, not the agent)_

## What it cost

| Item | Amount |
|---|---|
| Time spent | TOM: fill in |
| API / credits | $0.10 for the full run (answers $0.047, judge $0.051), plus about 2 cents of embeddings across development and test runs. Neon free plan. |
| Would cost at 1,000 requests a day | $0.89 (vector top 8) to $1.20 (vector top 16) a day on Haiku 5.5, retrieval included. The whole-handbook prompt with caching: $1.68. |

Prices used: Haiku 5.5 $0.10 / $0.50 per 1M input / output tokens (prompts under 100k tokens), cache reads 0.1×, writes 1.25×; Haiku 4.5 $1 / $5; `gemini-embedding-001` $0.15 per 1M tokens. TOM: confirm against anthropic.com/pricing and ai.google.dev/pricing before publishing.

## When I'd use this in production, and when I wouldn't

_TODO (Tom writes this, not the agent)_

## Links

- Docs I actually used: [pgvector](https://github.com/pgvector/pgvector) (operators, HNSW), [Neon serverless driver](https://neon.com/docs/serverless/serverless-driver), [Gemini embeddings](https://ai.google.dev/gemini-api/docs/embeddings), [Postgres text search: ts_stat](https://www.postgresql.org/docs/current/textsearch-features.html#TEXTSEARCH-STATISTICS), [Claude prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)
- Post:
