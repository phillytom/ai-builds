// Session 02 harness: 10 questions x 4 configs (prompt caching off/on x effort low/high) against one ~51k-token prompt.
//   npm run tokens            count the prompt's tokens (free)
//   npm run smoke             one question, cache off, effort low (about 11 cents: 51k input tokens)
//   npm start                 all 40 calls, then the judge, then the 2x2 table
//   npm start -- --rescore    re-judge the answers already in results.json (judge calls only)
//   npm start -- --report     print the table from results.json (no API calls)
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import Anthropic from "@anthropic-ai/sdk";
import { zodOutputFormat } from "@anthropic-ai/sdk/helpers/zod";
import { z } from "zod";
import { buildSystemPrompt } from "./context.ts";

process.loadEnvFile(new URL("../.env.local", import.meta.url));

const MODEL = "claude-sonnet-5";
const JUDGE = "claude-haiku-4-5";
// Stop cleanly once this much has been spent in one run. Tom's API balance was $4.85 at the start of the session.
const SPEND_CAP_USD = 4.0;

// USD per 1M tokens. Cache writes (5-minute TTL) are 1.25x input, cache reads 0.1x input.
// TOM: confirm against anthropic.com/pricing before publishing.
const PRICES: Record<string, { input: number; output: number }> = {
  "claude-sonnet-5": { input: 2.0, output: 10.0 },
  "claude-haiku-4-5": { input: 1.0, output: 5.0 },
};

type Effort = "low" | "high";
type Config = { cache: boolean; effort: Effort };
// Each effort level runs as its own block: changing effort invalidates the cache, so interleaving would force a
// fresh cache write on almost every call.
const CONFIGS: Config[] = [
  { cache: false, effort: "low" },
  { cache: false, effort: "high" },
  { cache: true, effort: "low" },
  { cache: true, effort: "high" },
];
const label = (c: Config) => `cache ${c.cache ? "on" : "off"}, effort ${c.effort}`;

type Question = { id: string; kind: string; question: string; must: string[]; must_not: string };
type Usage = { input: number; cache_write: number; cache_read: number; output: number };
type Row = Config & {
  question_id: string;
  answer: string;
  stop_reason: string | null;
  usage: Usage;
  first_text_ms: number; // request sent -> first visible answer text (after any thinking)
  total_ms: number;
  cost_usd: number;
  score?: 0 | 1 | 2;
  judge_reason?: string;
  judge_cost_usd?: number;
};

const questions: Question[] = JSON.parse(readFileSync(new URL("./questions.json", import.meta.url), "utf8")).questions;
const RESULTS = new URL("./results.json", import.meta.url);
const client = new Anthropic({ maxRetries: 4 }); // SDK retries 429 / 5xx / connection errors with backoff
const system = buildSystemPrompt();

const costOf = (model: string, u: Usage) =>
  ((u.input + u.cache_write * 1.25 + u.cache_read * 0.1) * PRICES[model].input + u.output * PRICES[model].output) / 1e6;

const usageOf = (u: Anthropic.Usage): Usage => ({
  input: u.input_tokens,
  cache_write: u.cache_creation_input_tokens ?? 0,
  cache_read: u.cache_read_input_tokens ?? 0,
  output: u.output_tokens,
});

async function ask(q: Question, c: Config): Promise<Row> {
  const started = performance.now();
  let firstText = 0;
  const stream = client.messages.stream({
    model: MODEL,
    max_tokens: 16000,
    thinking: { type: "adaptive" },
    output_config: { effort: c.effort },
    // The only difference between cache off and on is this one marker on the system block.
    system: [{ type: "text", text: system, ...(c.cache ? { cache_control: { type: "ephemeral" as const } } : {}) }],
    messages: [{ role: "user", content: q.question }],
  });
  stream.on("text", () => {
    firstText ||= performance.now() - started;
  });
  const msg = await stream.finalMessage();
  const total = performance.now() - started;
  const usage = usageOf(msg.usage);
  return {
    ...c,
    question_id: q.id,
    answer: msg.content.flatMap((b) => (b.type === "text" ? [b.text] : [])).join("").trim(),
    stop_reason: msg.stop_reason,
    usage,
    first_text_ms: Math.round(firstText || total),
    total_ms: Math.round(total),
    cost_usd: costOf(MODEL, usage),
  };
}

// ---------------------------------------------------------------- judge
const Verdict = z.object({
  reason: z.string().describe("One or two sentences: which required facts are present, missing or wrong."),
  score: z.number().int().min(0).max(2).describe("2 = every required fact present and correct; 1 = some; 0 = none, or the forbidden claim is made"),
});

const JUDGE_SYSTEM = `You grade a customer-support answer against an answer key. You are strict about numbers, SKUs and yes/no conclusions and relaxed about wording.
- 2: every required fact is present and correct. Extra correct detail is fine.
- 1: at least one required fact is present and correct, but at least one is missing or wrong.
- 0: no required fact is present, or the answer makes the forbidden claim.
A fact counts as present if the answer states it or clearly implies it (for example, the right final amount implies the right calculation).`;

async function judge(q: Question, answer: string) {
  const res = await client.messages.create({
    model: JUDGE,
    max_tokens: 400,
    system: JUDGE_SYSTEM,
    messages: [
      {
        role: "user",
        content: `Question: ${q.question}\n\nRequired facts:\n${q.must.map((m) => `- ${m}`).join("\n")}\n\nForbidden claim: ${q.must_not}\n\nAnswer to grade:\n${answer}`,
      },
    ],
    output_config: { format: zodOutputFormat(Verdict) },
  });
  const text = res.content.flatMap((b) => (b.type === "text" ? [b.text] : [])).join("");
  const v = Verdict.parse(JSON.parse(text));
  return { score: v.score as 0 | 1 | 2, reason: v.reason, cost: costOf(JUDGE, usageOf(res.usage)) };
}

// ---------------------------------------------------------------- report
const median = (xs: number[]) => {
  const s = [...xs].sort((a, b) => a - b);
  return s.length % 2 ? s[(s.length - 1) / 2] : (s[s.length / 2 - 1] + s[s.length / 2]) / 2;
};
const ms = (x: number) => `${Math.round(x).toLocaleString("en-US")} ms`;
const usd = (x: number, dp = 4) => `$${x.toFixed(dp)}`;

function report(rows: Row[]) {
  const lines = [
    "| Config | quality (of 20) | all-correct answers | median time to first text | median total time | cost per question | cost per day at 1,000 questions | avg output tokens | avg cache read / write tokens |",
    "|---|---|---|---|---|---|---|---|---|",
  ];
  for (const c of CONFIGS) {
    const rs = rows.filter((r) => r.cache === c.cache && r.effort === c.effort);
    if (!rs.length) continue;
    const scored = rs.filter((r) => r.score !== undefined);
    const avg = (f: (r: Row) => number) => rs.reduce((s, r) => s + f(r), 0) / rs.length;
    lines.push(
      `| ${label(c)} | ${scored.reduce((s, r) => s + r.score!, 0)} | ${scored.filter((r) => r.score === 2).length}/${scored.length} | ${ms(median(rs.map((r) => r.first_text_ms)))} | ${ms(median(rs.map((r) => r.total_ms)))} | ${usd(avg((r) => r.cost_usd))} | $${(avg((r) => r.cost_usd) * 1000).toFixed(2)} | ${Math.round(avg((r) => r.usage.output)).toLocaleString("en-US")} | ${Math.round(avg((r) => r.usage.cache_read)).toLocaleString("en-US")} / ${Math.round(avg((r) => r.usage.cache_write)).toLocaleString("en-US")} |`,
    );
  }
  lines.push("", "| Question | kind | " + CONFIGS.map(label).join(" | ") + " |", "|---|---|" + CONFIGS.map(() => "---").join("|") + "|");
  for (const q of questions) {
    const cell = (c: Config) => {
      const r = rows.find((x) => x.question_id === q.id && x.cache === c.cache && x.effort === c.effort);
      return r?.score === undefined ? "–" : String(r.score);
    };
    lines.push(`| ${q.id} | ${q.kind} | ${CONFIGS.map(cell).join(" | ")} |`);
  }
  const spent = rows.reduce((s, r) => s + r.cost_usd + (r.judge_cost_usd ?? 0), 0);
  lines.push("", `${rows.length} answers, answer cost ${usd(rows.reduce((s, r) => s + r.cost_usd, 0), 3)}, judge cost ${usd(rows.reduce((s, r) => s + (r.judge_cost_usd ?? 0), 0), 3)}, total ${usd(spent, 3)}.`);
  console.log(lines.join("\n"));
}

// ---------------------------------------------------------------- main
const args = process.argv.slice(2);

if (args.includes("--tokens")) {
  for (const model of [MODEL, JUDGE]) {
    const r = await client.messages.countTokens({ model, system, messages: [{ role: "user", content: questions[0].question }] });
    console.log(`${model}: ${r.input_tokens.toLocaleString("en-US")} input tokens (${system.length.toLocaleString("en-US")} characters)`);
  }
  process.exit(0);
}

if (args.includes("--smoke")) {
  // Cache off, so the smoke test can't leave a cache entry that a following full run would read.
  const r = await ask(questions[0], { cache: false, effort: "low" });
  const j = await judge(questions[0], r.answer);
  console.log(JSON.stringify({ ...r, score: j.score, judge_reason: j.reason, judge_cost_usd: j.cost }, null, 2));
  process.exit(r.stop_reason === "end_turn" ? 0 : 1);
}

const saved = () => (existsSync(RESULTS) ? (JSON.parse(readFileSync(RESULTS, "utf8")) as { rows: Row[] }) : undefined);
const write = (rows: Row[], extra: object = {}) =>
  writeFileSync(RESULTS, JSON.stringify({ model: MODEL, judge: JUDGE, run_at: new Date().toISOString(), ...extra, rows }, null, 2) + "\n");

if (args.includes("--report")) {
  report(saved()!.rows);
  process.exit(0);
}

let rows: Row[] = [];
let spent = 0;
const startedAt = Date.now();

let keep = {};
if (args.includes("--rescore")) {
  const prev = saved()! as { rows: Row[]; run_at: string; wall_clock_s: number };
  rows = prev.rows;
  keep = { run_at: prev.run_at, wall_clock_s: prev.wall_clock_s, rescored_at: new Date().toISOString() };
} else {
  let stopped = false;
  for (const c of CONFIGS) {
    for (const q of questions) {
      if (spent >= SPEND_CAP_USD) {
        stopped = true;
        break;
      }
      const r = await ask(q, c);
      rows.push(r);
      spent += r.cost_usd;
      write(rows, { partial: true });
      const u = r.usage;
      console.log(
        `${label(c).padEnd(24)} ${q.id}  first text ${ms(r.first_text_ms).padStart(9)}  total ${ms(r.total_ms).padStart(9)}  in ${u.input} / write ${u.cache_write} / read ${u.cache_read} / out ${u.output}  ${usd(r.cost_usd)}  spent ${usd(spent, 3)}`,
      );
      // Sanity checks: caching must do exactly what the config says, or the comparison is meaningless.
      if (!c.cache && (u.cache_read || u.cache_write)) console.warn(`  !! cache activity with caching off`);
      if (c.cache && q !== questions[0] && !u.cache_read) console.warn(`  !! expected a cache read`);
      if (r.stop_reason !== "end_turn") console.warn(`  !! stop_reason ${r.stop_reason}`);
    }
    if (stopped) {
      console.warn(`Spend cap of $${SPEND_CAP_USD} reached; stopping. Results so far are in results.json.`);
      break;
    }
  }
}

console.log("\nJudging...");
for (const r of rows) {
  const j = await judge(questions.find((q) => q.id === r.question_id)!, r.answer);
  Object.assign(r, { score: j.score, judge_reason: j.reason, judge_cost_usd: j.cost });
}
write(rows, { wall_clock_s: Math.round((Date.now() - startedAt) / 1000), ...keep });
console.log();
report(rows);
