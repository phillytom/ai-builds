// Two ways to find the chunks for a question.
//   vectorSearch: the naive version. Nearest neighbours by cosine distance, nothing else.
//   hybridSearch: vector search and Postgres full-text search side by side, merged with reciprocal rank fusion (RRF).
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
  // plainto_tsquery ANDs every word, so a long customer question would match nothing. Swapping & for | makes it
  // "any of these words", and ts_rank_cd puts chunks matching more of them (and closer together) first.
  const rows = await sql`
    WITH q AS (SELECT replace(plainto_tsquery('english', ${question})::text, '&', '|')::tsquery AS query),
    vec AS (
      SELECT id, row_number() OVER (ORDER BY embedding <=> ${v}::vector) AS r
      FROM chunks ORDER BY embedding <=> ${v}::vector LIMIT ${POOL}
    ),
    kw AS (
      SELECT id, row_number() OVER (ORDER BY ts_rank_cd(tsv, q.query) DESC) AS r
      FROM chunks, q WHERE tsv @@ q.query
      ORDER BY ts_rank_cd(tsv, q.query) DESC LIMIT ${POOL}
    )
    SELECT c.id, c.title, c.text, vec.r::int AS vec_rank, kw.r::int AS kw_rank
    FROM vec FULL JOIN kw USING (id) JOIN chunks c USING (id)
    ORDER BY coalesce(1.0 / (${RRF_K} + vec.r), 0) + coalesce(1.0 / (${RRF_K} + kw.r), 0) DESC, c.id
    LIMIT ${k}`;
  return { hits: rows as Hit[], embed_tokens: tokens, ms: Math.round(performance.now() - started) };
}
