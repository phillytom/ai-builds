// Two ways to find the chunks for a question.
//   vectorSearch: the naive version. Nearest neighbours by cosine distance, nothing else.
//   hybridSearch: vector search and keyword search side by side, merged with reciprocal rank fusion (RRF). The keyword
//                 side uses Postgres full-text parsing (stemming, stop words) with IDF weights, a cut-down BM25.
import { sql, embed, toVector } from "./shared.ts";

export type Hit = { id: string; title: string; text: string; vec_rank: number | null; kw_rank: number | null };
export type Retrieval = { hits: Hit[]; embed_tokens: number; ms: number };

export const TOP_K = 8; // chunks handed to the model
const POOL = 30; // candidates each method contributes before fusion
const RRF_K = 60; // the usual RRF constant: a rank r scores 1 / (60 + r)

export async function vectorSearch(question: string, k = TOP_K): Promise<Retrieval> {
  const started = performance.now();
  const { vectors, tokens } = await embed([question], "query");
  const v = toVector(vectors[0]);
  const rows = await sql`
    SELECT id, title, text, row_number() OVER (ORDER BY embedding <=> ${v}::vector)::int AS vec_rank, NULL AS kw_rank
    FROM chunks ORDER BY embedding <=> ${v}::vector LIMIT ${k}`;
  return { hits: rows as Hit[], embed_tokens: tokens, ms: Math.round(performance.now() - started) };
}

export async function hybridSearch(question: string, k = TOP_K): Promise<Retrieval> {
  const started = performance.now();
  const { vectors, tokens } = await embed([question], "query");
  const v = toVector(vectors[0]);
  // Keyword side: a chunk scores the summed IDF weight (see ingest.ts) of the question's words it contains, so one
  // rare word ("zester", "nakiri", "honolulu") outweighs several common ones ("order", "shipping", "bought").
  const rows = await sql`
    WITH qwords AS (SELECT unnest(tsvector_to_array(to_tsvector('english', ${question}))) AS word),
    vec AS (
      SELECT id, row_number() OVER (ORDER BY embedding <=> ${v}::vector) AS r
      FROM chunks ORDER BY embedding <=> ${v}::vector LIMIT ${POOL}
    ),
    kw AS (
      SELECT c.id, row_number() OVER (ORDER BY sum(t.idf) DESC, c.id) AS r
      FROM chunks c
      JOIN terms t ON t.word = ANY (tsvector_to_array(c.tsv))
      JOIN qwords q ON q.word = t.word
      GROUP BY c.id ORDER BY sum(t.idf) DESC, c.id LIMIT ${POOL}
    )
    SELECT c.id, c.title, c.text, vec.r::int AS vec_rank, kw.r::int AS kw_rank
    FROM vec FULL JOIN kw USING (id) JOIN chunks c USING (id)
    ORDER BY coalesce(1.0 / (${RRF_K} + vec.r), 0) + coalesce(1.0 / (${RRF_K} + kw.r), 0) DESC, c.id
    LIMIT ${k}`;
  return { hits: rows as Hit[], embed_tokens: tokens, ms: Math.round(performance.now() - started) };
}
