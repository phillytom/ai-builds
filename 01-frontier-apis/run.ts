// Session 01 harness: same 10 emails x RUNS to every model, scored against the hand labels.
//   npm start                 all models
//   npm start -- --only openai
//   npm run smoke             Anthropic, one email, one call
import { readFileSync, writeFileSync } from "node:fs";
import { ThinkingLevel } from "@google/genai";
import { classify, type Classification, type Email, type ModelOptions, type Provider, type Triage } from "./classify.ts";

// USD per 1M tokens. TOM: confirm against each pricing page before publishing.
// Pre-filled from the pages as fetched on 2026-09-21.
const PRICES: Record<string, { input: number; output: number }> = {
  "claude-haiku-4-5": { input: 1.0, output: 5.0 }, // anthropic.com/pricing
  "gpt-5.4-mini": { input: 0.75, output: 4.5 }, // developers.openai.com/api/docs/pricing
  "gemini-3.8-flash": { input: 0.75, output: 3.75 }, // ai.google.dev/gemini-api/docs/pricing
};

const MODELS: { provider: Provider; model: string; opts?: ModelOptions }[] = [
  { provider: "anthropic", model: "claude-haiku-4-5" }, // thinking is off unless requested
  { provider: "openai", model: "gpt-5.4-mini", opts: { openaiEffort: "none" } },
  { provider: "gemini", model: "gemini-3.8-flash", opts: { geminiThinking: ThinkingLevel.LOW } }, // MINIMAL returns 400 on this model; LOW is its floor
];

const RUNS = 3;
const SCORED = ["intent", "order_id", "product_sku", "sentiment", "urgency", "suggested_action"] as const;
type Field = (typeof SCORED)[number];
type Labeled = Email & { labels: Pick<Triage, Field> };
type Row = Classification & { provider: Provider; model: string; email_id: string; run: number; correct: Record<Field, boolean> };

const args = process.argv.slice(2);
const smoke = args.includes("--smoke");
const only = args.includes("--only") ? args[args.indexOf("--only") + 1] : smoke ? "anthropic" : undefined;

const emails: Labeled[] = JSON.parse(readFileSync(new URL("../data/support-emails.json", import.meta.url), "utf8")).emails;
const models = MODELS.filter((m) => !only || m.provider === only);

const costOf = (model: string, r: { input_tokens: number; output_tokens: number }) =>
  (r.input_tokens * PRICES[model].input + r.output_tokens * PRICES[model].output) / 1e6;

// nearest-rank percentile
const pct = (xs: number[], p: number) => [...xs].sort((a, b) => a - b)[Math.max(0, Math.ceil((p / 100) * xs.length) - 1)];

if (smoke) {
  const { provider, model, opts } = models[0];
  const email = emails[0];
  const out = await classify(provider, model, email, opts);
  console.log(JSON.stringify({ model, email: email.id, ...out, expected: email.labels, cost_usd: costOf(model, out) }, null, 2));
  process.exit(out.result ? 0 : 1);
}

const rows: Row[] = [];
const started = Date.now();
for (const { provider, model, opts } of models) {
  for (const email of emails) {
    for (let run = 1; run <= RUNS; run++) {
      // sequential on purpose, so latency is not distorted by our own concurrency
      const out = await classify(provider, model, email, opts);
      const correct = Object.fromEntries(
        SCORED.map((f) => [f, out.result !== null && out.result[f] === email.labels[f]]),
      ) as Record<Field, boolean>;
      rows.push({ provider, model, email_id: email.id, run, ...out, correct });
      process.stderr.write(`${model} ${email.id} #${run} ${out.latency_ms}ms ${out.error ?? (SCORED.filter((f) => !correct[f]).join(",") || "ok")}\n`);
    }
  }
}

const summary = models.map(({ provider, model }) => {
  // Calls the API refused (quota, outage) are not model answers: keep them out of accuracy, latency and cost,
  // and report them loudly instead. Invalid JSON after retries IS a model failure and stays in.
  const all = rows.filter((r) => r.model === model);
  const mine = all.filter((r) => r.attempts > 0);
  const acc = (f: Field) => mine.filter((r) => r.correct[f]).length / mine.length;
  const costPerCall = mine.reduce((s, r) => s + costOf(model, r), 0) / mine.length;
  return {
    provider,
    model,
    calls: mine.length,
    api_failed: all.length - mine.length,
    accuracy: Object.fromEntries(SCORED.map((f) => [f, acc(f)])) as Record<Field, number>,
    all_fields_correct: mine.filter((r) => SCORED.every((f) => r.correct[f])).length / mine.length,
    invalid_after_retries: mine.filter((r) => !r.result).length,
    json_retries: mine.reduce((s, r) => s + Math.max(0, r.attempts - 1), 0),
    api_retries: mine.reduce((s, r) => s + r.api_retries, 0),
    latency_ms: { median: pct(mine.map((r) => r.latency_ms), 50), p95: pct(mine.map((r) => r.latency_ms), 95) },
    avg_tokens: {
      input: Math.round(mine.reduce((s, r) => s + r.input_tokens, 0) / mine.length),
      output: Math.round(mine.reduce((s, r) => s + r.output_tokens, 0) / mine.length),
    },
    cost_per_call_usd: costPerCall,
    cost_per_1000_emails_per_day_usd: costPerCall * 1000,
  };
});

writeFileSync(
  new URL("./results.json", import.meta.url),
  JSON.stringify({ ran_at: new Date(started).toISOString(), wall_clock_s: Math.round((Date.now() - started) / 1000), runs_per_email: RUNS, prices_usd_per_mtok: PRICES, summary, rows }, null, 2) + "\n",
);

const pc = (x: number) => `${Math.round(x * 100)}%`;
const head = ["Model", ...SCORED, "all 6", "median ms", "p95 ms", "$ / call", "$ / day at 1,000 emails", "scored calls"];
console.log(`| ${head.join(" | ")} |\n|${head.map(() => "---").join("|")}|`);
for (const s of summary) {
  const cells = [
    s.model, ...SCORED.map((f) => pc(s.accuracy[f])), pc(s.all_fields_correct),
    s.latency_ms.median, s.latency_ms.p95, `$${s.cost_per_call_usd.toFixed(5)}`, `$${s.cost_per_1000_emails_per_day_usd.toFixed(2)}`,
    s.api_failed ? `**${s.calls} of ${s.calls + s.api_failed}: INCOMPLETE**` : s.calls,
  ];
  console.log(`| ${cells.join(" | ")} |`);
}
for (const s of summary.filter((s) => s.api_failed))
  console.log(`\nWARNING: ${s.model} had ${s.api_failed} calls refused by the API. Its row is not comparable. See results.json.`);
console.log(`\n${RUNS} runs x ${emails.length} emails per model. Exact match per field against data/support-emails.json.`);
