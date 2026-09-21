// One provider-agnostic entry point: classify(provider, model, email).
// Each provider uses its own native structured-output mechanism with the same Zod schema:
//   Anthropic  messages.create  + output_config.format (zodOutputFormat)
//   OpenAI     responses.create + text.format          (zodTextFormat)
//   Gemini     generateContent  + responseJsonSchema   (z.toJSONSchema)
import { readFileSync } from "node:fs";
import Anthropic from "@anthropic-ai/sdk";
import { zodOutputFormat } from "@anthropic-ai/sdk/helpers/zod";
import OpenAI from "openai";
import { zodTextFormat } from "openai/helpers/zod";
import { GoogleGenAI, ThinkingLevel } from "@google/genai";
import { z } from "zod";

process.loadEnvFile(new URL("../.env.local", import.meta.url));

export const MAX_RETRIES = 2; // on invalid JSON / schema mismatch only
const MAX_API_RETRIES = 3; // on 429 / 5xx, with backoff. Separate budget: an overloaded API is not a model failure.

export const Triage = z.object({
  intent: z.enum([
    "order_status", "return_request", "defect_warranty", "how_to",
    "damaged_in_shipping", "wrong_item", "cancel_order", "other",
  ]),
  order_id: z.string().nullable(),
  product_sku: z.string().nullable(),
  sentiment: z.enum(["positive", "neutral", "negative"]),
  urgency: z.enum(["low", "medium", "high"]),
  suggested_action: z.enum(["send_tracking", "refund", "replace", "answer_question", "cancel", "escalate"]),
  product_issue: z.string().nullable(),
});
export type Triage = z.infer<typeof Triage>;

export type Provider = "anthropic" | "openai" | "gemini";
export type Email = { id: string; from_first_name: string; subject: string; body: string };

// Reasoning is set to the lowest level each model accepts. Haiku 4.5 has thinking off unless asked.
export type ModelOptions = { openaiEffort?: "none" | "minimal" | "low"; geminiThinking?: ThinkingLevel };

export type Classification = {
  result: Triage | null; // null = still invalid after MAX_RETRIES
  latency_ms: number; // time spent inside model calls, JSON retries included, backoff sleeps excluded
  input_tokens: number; // summed over attempts, because every attempt is billed
  output_tokens: number; // includes reasoning/thinking tokens where the provider bills them
  attempts: number;
  api_retries: number;
  error?: string;
};

type Product = { sku: string; name: string };
const products: Product[] = JSON.parse(readFileSync(new URL("../data/products.json", import.meta.url), "utf8"));

export const SYSTEM = `You triage inbound customer emails for Tom's Kitchen, an online store for small kitchen appliances and cookware. Classify the email into the given JSON schema.

Rules:
- intent: the one request that needs an action from us. Missing items count as wrong_item. Billing disputes are other.
- order_id: the order number exactly as the customer gave it, normalised to the form TK-12345. Use null if the email contains no order number. Never guess or invent one. Tracking numbers are not order numbers.
- product_sku: the SKU from the catalog below for the one product the email is mainly about. For wrong_item, use the product that was ordered. Use null if the email does not identify a product.
- urgency: high = safety issue, money dispute, or a time window closing within about a day. medium = the customer is blocked or waiting on us. low = no time pressure.
- suggested_action: escalate always wins when there is an injury, a safety risk, or a legal or chargeback threat. A return for money back is refund. cancel covers cancelling or editing an unshipped order.
- product_issue: a few words describing the product problem, or null if there is none.

Catalog:
${products.map((p) => `${p.sku}  ${p.name}`).join("\n")}`;

const userText = (e: Email) => `From: ${e.from_first_name}\nSubject: ${e.subject}\n\n${e.body}`;

type Raw = { text: string; input_tokens: number; output_tokens: number };

let anthropic: Anthropic | undefined, openai: OpenAI | undefined, gemini: GoogleGenAI | undefined;

async function callAnthropic(model: string, email: Email): Promise<Raw> {
  anthropic ??= new Anthropic();
  const res = await anthropic.messages.create({
    model,
    max_tokens: 1024,
    system: SYSTEM,
    messages: [{ role: "user", content: userText(email) }],
    output_config: { format: zodOutputFormat(Triage) },
  });
  const text = res.content.flatMap((b) => (b.type === "text" ? [b.text] : [])).join("");
  return { text, input_tokens: res.usage.input_tokens, output_tokens: res.usage.output_tokens };
}

async function callOpenAI(model: string, email: Email, opts: ModelOptions): Promise<Raw> {
  openai ??= new OpenAI();
  const res = await openai.responses.create({
    model,
    max_output_tokens: 2048,
    instructions: SYSTEM,
    input: userText(email),
    reasoning: { effort: opts.openaiEffort ?? "none" },
    text: { format: zodTextFormat(Triage, "email_triage") },
  });
  return {
    text: res.output_text,
    input_tokens: res.usage?.input_tokens ?? 0,
    output_tokens: res.usage?.output_tokens ?? 0, // already includes reasoning tokens
  };
}

async function callGemini(model: string, email: Email, opts: ModelOptions): Promise<Raw> {
  gemini ??= new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });
  const res = await gemini.models.generateContent({
    model,
    contents: userText(email),
    config: {
      systemInstruction: SYSTEM,
      maxOutputTokens: 2048,
      responseMimeType: "application/json",
      responseJsonSchema: z.toJSONSchema(Triage),
      thinkingConfig: { thinkingLevel: opts.geminiThinking ?? ThinkingLevel.LOW },
    },
  });
  const u = res.usageMetadata;
  return {
    text: res.text ?? "",
    input_tokens: u?.promptTokenCount ?? 0,
    output_tokens: (u?.candidatesTokenCount ?? 0) + (u?.thoughtsTokenCount ?? 0), // thoughts are billed as output
  };
}

export async function classify(
  provider: Provider,
  model: string,
  email: Email,
  opts: ModelOptions = {},
): Promise<Classification> {
  const call = { anthropic: callAnthropic, openai: callOpenAI, gemini: callGemini }[provider];
  const out: Classification = { result: null, latency_ms: 0, input_tokens: 0, output_tokens: 0, attempts: 0, api_retries: 0 };
  let ms = 0;
  while (out.attempts <= MAX_RETRIES && !out.result) {
    const t0 = performance.now();
    let raw: Raw;
    try {
      raw = await call(model, email, opts);
    } catch (err) {
      // Never throw: one bad call must not take down a 90-call run.
      const status = (err as { status?: number }).status;
      const transient = status === 429 || (status !== undefined && status >= 500);
      out.error = `API error ${status ?? ""}: ${String((err as Error).message ?? err).slice(0, 200)}`;
      if (!transient || out.api_retries >= MAX_API_RETRIES) break;
      out.api_retries++;
      await new Promise((r) => setTimeout(r, 2000 * 2 ** (out.api_retries - 1)));
      continue;
    }
    ms += performance.now() - t0;
    out.attempts++;
    out.input_tokens += raw.input_tokens;
    out.output_tokens += raw.output_tokens;
    try {
      out.result = Triage.parse(JSON.parse(raw.text));
      delete out.error;
    } catch (err) {
      out.error = `invalid JSON on attempt ${out.attempts}: ${String(err).slice(0, 200)}`;
    }
  }
  out.latency_ms = Math.round(ms);
  return out;
}
