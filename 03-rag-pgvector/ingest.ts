// Rebuilds the chunks table from scratch: npm run ingest
// Safe to re-run; the table is dropped and reloaded every time (230 chunks, under a cent to embed).
import { buildChunks } from "./chunks.ts";
import { sql, embed, toVector, EMBED_DIMS, EMBED_MODEL, costOf } from "./shared.ts";

const chunks = buildChunks();
const started = performance.now();

await sql`CREATE EXTENSION IF NOT EXISTS vector`;
await sql`DROP TABLE IF EXISTS chunks`;
await sql.query(`
  CREATE TABLE chunks (
    id        text PRIMARY KEY,
    source    text NOT NULL,
    title     text NOT NULL,
    text      text NOT NULL,
    tsv       tsvector GENERATED ALWAYS AS (to_tsvector('english', text)) STORED,
    embedding vector(${EMBED_DIMS}) NOT NULL
  )`);

// One embeddings request per 100 chunks.
let tokens = 0;
for (let i = 0; i < chunks.length; i += 100) {
  const batch = chunks.slice(i, i + 100);
  const { vectors, tokens: t } = await embed(batch.map((c) => c.text), "document");
  tokens += t;
  await sql.transaction(
    batch.map((c, j) => sql`INSERT INTO chunks (id, source, title, text, embedding)
                            VALUES (${c.id}, ${c.source}, ${c.title}, ${c.text}, ${toVector(vectors[j])})`),
  );
}

// HNSW for cosine distance, and GIN for full-text. At 230 rows Postgres may still scan; at 230,000 it wouldn't.
await sql`CREATE INDEX ON chunks USING hnsw (embedding vector_cosine_ops)`;
await sql`CREATE INDEX ON chunks USING gin (tsv)`;

const [{ n, version }] = await sql`SELECT count(*)::int AS n, (SELECT extversion FROM pg_extension WHERE extname = 'vector') AS version FROM chunks`;
console.log(
  `Loaded ${n} chunks (pgvector ${version}). Embedded ${tokens.toLocaleString("en-US")} tokens with ${EMBED_MODEL}: ` +
    `$${costOf(EMBED_MODEL, { input: tokens, output: 0 }).toFixed(5)}. ${Math.round(performance.now() - started)} ms.`,
);
