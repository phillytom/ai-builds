// Ask one question: npm run ask -- "Can I return just the saucepan from the bundle?" [--vector | --full]
// Defaults to hybrid search. Prints what was retrieved, then the answer.
import { ask, type Mode } from "./bot.ts";

const args = process.argv.slice(2);
const mode: Mode = args.includes("--vector") ? "vector" : args.includes("--full") ? "full" : "hybrid";
const question = args.filter((a) => !a.startsWith("--")).join(" ");
if (!question) throw new Error('Usage: npm run ask -- "your question" [--vector | --full]');

const r = await ask(question, mode);
if (r.retrieved.length) console.log(`Retrieved (${mode}): ${r.retrieved.join(", ")}\n`);
console.log(r.answer);
const stray = r.cited.filter((id) => !r.retrieved.includes(id));
console.log(
  `\n${r.total_ms} ms (${r.retrieval_ms} ms retrieval), $${r.cost_usd.toFixed(5)}` +
    (mode !== "full" ? `, ${r.cited.length} sources cited${stray.length ? `, NOT retrieved: ${stray.join(", ")}` : ""}` : ""),
);
