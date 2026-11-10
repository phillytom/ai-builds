// The support bot. Four modes, one model:
//   full       no retrieval: the whole handbook and catalog in the prompt (session 02's prompt, cached), as the baseline
//   vector-8   top 8 chunks by vector search (the naive version)
//   hybrid-8   top 8 chunks by vector + keyword search, fused
//   vector-16  top 16 chunks by vector search
import type Anthropic from "@anthropic-ai/sdk";
import { buildSystemPrompt, TODAY } from "../02-context-engineering/context.ts";
import { anthropic, MODEL, EMBED_MODEL, costOf } from "./shared.ts";
import { vectorSearch, hybridSearch, type Retrieval } from "./search.ts";

export const MODES = ["full", "vector-8", "hybrid-8", "vector-16"] as const;
export type Mode = (typeof MODES)[number];

const RAG_SYSTEM = `You are the customer support assistant for Tom's Kitchen, an online store for kitchen appliances and cookware.
Today is ${TODAY}.

Answer the customer's question using only the sources in the message: sections of the policy handbook (ids like §2.2)
and catalog entries (ids like KT-2027). When a policy and a product both matter, check both. Quote exact prices, dates,
fees and SKUs. If the answer depends on something the customer hasn't told you, say what it depends on and give the
answer for each case. If the sources don't cover it, say so rather than guessing.

Cite your sources: after each fact, put the id of the source it came from in square brackets, like [§1.8] or [KT-2006].
Only cite ids that appear in the sources.

Write a direct answer in plain text, 150 words or fewer. No greeting and no sign-off.`;

const FULL_SYSTEM = buildSystemPrompt();

export type Answer = {
  mode: Mode;
  answer: string;
  stop_reason: string | null;
  retrieved: string[]; // chunk ids, best first
  cited: string[]; // ids the answer cites
  usage: { input: number; cache_read: number; cache_write: number; output: number; embed: number };
  retrieval_ms: number;
  total_ms: number;
  cost_usd: number;
};

const CITATION = /\[([^\]]+)\]/g;
const ID = /^(§\d+\.\d+|KT-\d{4}|faq-[a-z-]+)$/;
export const citationsIn = (text: string) =>
  [...new Set([...text.matchAll(CITATION)].flatMap((m) => m[1].split(/[,;]\s*/).map((s) => s.trim())).filter((s) => ID.test(s)))];

export async function ask(question: string, mode: Mode): Promise<Answer> {
  const started = performance.now();
  let retrieval: Retrieval = { hits: [], embed_tokens: 0, ms: 0 };
  let system: Anthropic.TextBlockParam[];
  let content: string;

  if (mode === "full") {
    system = [{ type: "text", text: FULL_SYSTEM, cache_control: { type: "ephemeral" } }];
    content = question;
  } else {
    const [method, k] = mode.split("-");
    retrieval = await (method === "vector" ? vectorSearch : hybridSearch)(question, Number(k));
    system = [{ type: "text", text: RAG_SYSTEM }];
    const sources = retrieval.hits.map((h) => `<source id="${h.id}">\n${h.text}\n</source>`).join("\n");
    content = `<sources>\n${sources}\n</sources>\n\nCustomer question: ${question}`;
  }

  const msg = await anthropic.messages.create({
    model: MODEL,
    max_tokens: 16000,
    thinking: { type: "adaptive" },
    output_config: { effort: "medium" }, // Haiku 5.5's default, set explicitly
    system,
    messages: [{ role: "user", content }],
  });

  const answer = msg.content.flatMap((b) => (b.type === "text" ? [b.text] : [])).join("").trim();
  const u = msg.usage;
  const usage = {
    input: u.input_tokens,
    cache_read: u.cache_read_input_tokens ?? 0,
    cache_write: u.cache_creation_input_tokens ?? 0,
    output: u.output_tokens,
    embed: retrieval.embed_tokens,
  };
  // Cache reads bill at 0.1x input, 5-minute cache writes at 1.25x.
  const cost =
    costOf(MODEL, { input: usage.input + usage.cache_read * 0.1 + usage.cache_write * 1.25, output: usage.output }) +
    costOf(EMBED_MODEL, { input: usage.embed, output: 0 });

  return {
    mode,
    answer,
    stop_reason: msg.stop_reason,
    retrieved: retrieval.hits.map((h) => h.id),
    cited: citationsIn(answer),
    usage,
    retrieval_ms: retrieval.ms,
    total_ms: Math.round(performance.now() - started),
    cost_usd: cost,
  };
}
