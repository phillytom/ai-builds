// Session 03 harness: session 02's 10 questions x 4 modes (see bot.ts), all answered by Haiku 5.5.
//   npm start                    all 40 answers, then the judge, then the tables (about 15 cents)
//   npm start -- --retrieval     retrieval only: share of needed chunks found at several top-k sizes (embeddings only, no Claude)
//   npm start -- --rescore       re-judge the answers already in results.json
//   npm start -- --report        print the tables from results.json (no API calls)
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { zodOutputFormat } from "@anthropic-ai/sdk/helpers/zod";
import { z } from "zod";
import { anthropic, MODEL, JUDGE, EMBED_MODEL, costOf } from "./shared.ts";
import { ask, MODES, type Mode, type Answer } from "./bot.ts";
import { vectorSearch, hybridSearch } from "./search.ts";

const SPEND_CAP_USD = 1.0; // stop cleanly past this; the whole run should cost well under it

type Question = { id: string; kind: string; question: string; must: string[]; must_not: string };
const questions: Question[] = JSON.parse(readFileSync(new URL("../02-context-engineering/questions.json", import.meta.url), "utf8")).questions;
const gold: Record<string, string[]> = JSON.parse(readFileSync(new URL("./gold.json", import.meta.url), "utf8")).needs;
const RESULTS = new URL("./results.json", import.meta.url);

type Row = Answer & { question_id: string; score?: 0 | 1 | 2; judge_reason?: string; judge_cost_usd?: number };

// Share of the chunks a correct answer needs that made it into the top k.
const recall = (qid: string, retrieved: string[]) => gold[qid].filter((id) => retrieved.includes(id)).length / gold[qid].length;
const missing = (qid: string, retrieved: string[]) => gold[qid].filter((id) => !retrieved.includes(id));

// ---------------------------------------------------------------- judge (same prompt and model as session 02)
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
  const res = await anthropic.messages.create({
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
  return { score: v.score as 0 | 1 | 2, reason: v.reason, cost: costOf(JUDGE, { input: res.usage.input_tokens, output: res.usage.output_tokens }) };
}

// ---------------------------------------------------------------- report
const median = (xs: number[]) => {
  const s = [...xs].sort((a, b) => a - b);
  return s.length % 2 ? s[(s.length - 1) / 2] : (s[s.length / 2 - 1] + s[s.length / 2]) / 2;
};
const pct = (x: number) => `${Math.round(x * 100)}%`;
const LABEL: Record<Mode, string> = {
  full: "Whole handbook in the prompt (no retrieval)",
  "vector-8": "RAG, vector search, top 8",
  "hybrid-8": "RAG, hybrid search, top 8",
  "vector-16": "RAG, vector search, top 16",
};

function report(rows: Row[]) {
  const lines = [
    `| Mode | quality (of 20) | all-correct answers | needed chunks retrieved | citations that point at a retrieved chunk | median time | prompt tokens per question | cost per question | cost per day at 1,000 questions |`,
    "|---|---|---|---|---|---|---|---|---|",
  ];
  for (const mode of MODES) {
    const rs = rows.filter((r) => r.mode === mode);
    if (!rs.length) continue;
    const avg = (f: (r: Row) => number) => rs.reduce((s, r) => s + f(r), 0) / rs.length;
    const rag = mode !== "full";
    const cites = rs.flatMap((r) => r.cited.map((id) => r.retrieved.includes(id)));
    lines.push(
      `| ${LABEL[mode]} | ${rs.reduce((s, r) => s + (r.score ?? 0), 0)} | ${rs.filter((r) => r.score === 2).length}/${rs.length} | ` +
        `${rag ? pct(avg((r) => recall(r.question_id, r.retrieved))) : "all (100%)"} | ` +
        `${rag ? `${cites.filter(Boolean).length}/${cites.length}` : "n/a"} | ` +
        `${(median(rs.map((r) => r.total_ms)) / 1000).toFixed(1)} s | ` +
        `${Math.round(avg((r) => r.usage.input + r.usage.cache_read + r.usage.cache_write)).toLocaleString("en-US")} | ` +
        `$${avg((r) => r.cost_usd).toFixed(4)} | $${(avg((r) => r.cost_usd) * 1000).toFixed(2)} |`,
    );
  }
  const RAG = MODES.filter((m) => m !== "full");
  lines.push(
    "",
    "| Question | kind | " + MODES.map((m) => `${m} score`).join(" | ") + " | " + RAG.map((m) => `${m}: needed chunks missed`).join(" | ") + " |",
    "|---|---|" + [...MODES, ...RAG].map(() => "---").join("|") + "|",
  );
  for (const q of questions) {
    const r = (m: Mode) => rows.find((x) => x.question_id === q.id && x.mode === m);
    const miss = (m: Mode) => (r(m) ? missing(q.id, r(m)!.retrieved).join(", ") || "none" : "–");
    lines.push(`| ${q.id} | ${q.kind} | ${MODES.map((m) => r(m)?.score ?? "–").join(" | ")} | ${RAG.map(miss).join(" | ")} |`);
  }
  const answers = rows.reduce((s, r) => s + r.cost_usd, 0);
  const judging = rows.reduce((s, r) => s + (r.judge_cost_usd ?? 0), 0);
  lines.push("", `${rows.length} answers by ${MODEL}. Answer cost $${answers.toFixed(4)}, judge (${JUDGE}) $${judging.toFixed(4)}, total $${(answers + judging).toFixed(4)}.`);
  console.log(lines.join("\n"));
}

// ---------------------------------------------------------------- main
const args = process.argv.slice(2);
const saved = () => JSON.parse(readFileSync(RESULTS, "utf8")) as { rows: Row[]; run_at: string; wall_clock_s: number };
const write = (rows: Row[], extra: object = {}) =>
  writeFileSync(RESULTS, JSON.stringify({ model: MODEL, judge: JUDGE, embed_model: EMBED_MODEL, run_at: new Date().toISOString(), ...extra, rows }, null, 2) + "\n");

if (args.includes("--retrieval")) {
  const KS = [4, 8, 12, 16, 24];
  const searches = { vector: vectorSearch, hybrid: hybridSearch };
  console.log(`| Share of needed chunks retrieved | ${KS.map((k) => `top ${k}`).join(" | ")} |\n|---|${KS.map(() => "---").join("|")}|`);
  for (const [name, search] of Object.entries(searches)) {
    const ranked = await Promise.all(questions.map(async (q) => (await search(q.question, Math.max(...KS))).hits.map((h) => h.id)));
    const at = (k: number) => ranked.reduce((s, ids, i) => s + recall(questions[i].id, ids.slice(0, k)), 0) / questions.length;
    console.log(`| ${name} search | ${KS.map((k) => pct(at(k))).join(" | ")} |`);
  }
  process.exit(0);
}

if (args.includes("--report")) {
  report(saved().rows);
  process.exit(0);
}

let rows: Row[] = [];
let keep = {};
const startedAt = Date.now();

if (args.includes("--rescore")) {
  const prev = saved();
  rows = prev.rows;
  keep = { run_at: prev.run_at, wall_clock_s: prev.wall_clock_s, rescored_at: new Date().toISOString() };
} else {
  let spent = 0;
  outer: for (const mode of MODES) {
    for (const q of questions) {
      if (spent >= SPEND_CAP_USD) {
        console.warn(`Spend cap of $${SPEND_CAP_USD} reached; stopping. Results so far are in results.json.`);
        break outer;
      }
      const r: Row = { ...(await ask(q.question, mode)), question_id: q.id };
      rows.push(r);
      spent += r.cost_usd;
      write(rows, { partial: true });
      const stray = r.cited.filter((id) => !r.retrieved.includes(id));
      console.log(
        `${mode.padEnd(6)} ${q.id}  ${String(r.total_ms).padStart(6)} ms  in ${r.usage.input} / cache read ${r.usage.cache_read} / out ${r.usage.output}` +
          `  $${r.cost_usd.toFixed(5)}` +
          (mode !== "full" ? `  recall ${pct(recall(q.id, r.retrieved))}  cited ${r.cited.length}${stray.length ? ` (not retrieved: ${stray})` : ""}` : ""),
      );
      if (r.stop_reason !== "end_turn") console.warn(`  !! stop_reason ${r.stop_reason}`);
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
