// Shared clients, model choices and prices for session 03.
import Anthropic from "@anthropic-ai/sdk";
import { GoogleGenAI } from "@google/genai";
import { neon } from "@neondatabase/serverless";

process.loadEnvFile(new URL("../.env.local", import.meta.url));
if (!process.env.DATABASE_URL) throw new Error("DATABASE_URL is empty in .env.local (see How to run it)");

export const sql = neon(process.env.DATABASE_URL);
export const anthropic = new Anthropic({ maxRetries: 4 });
export const gemini = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });

export const EMBED_MODEL = "gemini-embedding-001"; // cut to 1,536 dimensions (of 3,072)
export const EMBED_DIMS = 1536;
export const MODEL = "claude-haiku-5-5"; // answers, in every mode
export const JUDGE = "claude-haiku-4-5"; // same judge as session 02, so the scores compare

// USD per 1M tokens. TOM: confirm against anthropic.com/pricing and ai.google.dev/pricing before publishing.
// Haiku 5.5 is $0.10 / $0.50 up to 100k prompt tokens (every prompt here is under that), $0.50 / $2.50 above.
export const PRICES: Record<string, { input: number; output: number }> = {
  "claude-haiku-5-5": { input: 0.1, output: 0.5 },
  "claude-haiku-4-5": { input: 1.0, output: 5.0 },
  "gemini-embedding-001": { input: 0.15, output: 0 },
};

export type Usage = { input: number; output: number };
export const costOf = (model: string, u: Usage) => (u.input * PRICES[model].input + u.output * PRICES[model].output) / 1e6;

// Documents and questions are embedded differently: Gemini tunes the vector for which side of the search it is on.
// The SDK does not retry 429 / 503 on its own (learned in session 01), so this does, with backoff.
export async function embed(texts: string[], kind: "document" | "query"): Promise<{ vectors: number[][]; tokens: number }> {
  for (let attempt = 0; ; attempt++) {
    try {
      const res = await gemini.models.embedContent({
        model: EMBED_MODEL,
        contents: texts,
        config: { outputDimensionality: EMBED_DIMS, taskType: kind === "document" ? "RETRIEVAL_DOCUMENT" : "RETRIEVAL_QUERY" },
      });
      // The embed endpoint reports no token usage, so count it separately (free) for the cost table.
      const { totalTokens } = await gemini.models.countTokens({ model: EMBED_MODEL, contents: texts.join("\n") });
      return { vectors: res.embeddings!.map((e) => e.values!), tokens: totalTokens ?? 0 };
    } catch (e: any) {
      if (attempt >= 4 || ![429, 500, 503].includes(e.status)) throw e;
      await new Promise((r) => setTimeout(r, 1000 * 2 ** attempt));
    }
  }
}

// pgvector's text form: '[0.1,0.2,...]'
export const toVector = (v: number[]) => `[${v.join(",")}]`;
