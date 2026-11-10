// Ask one question: npm run ask -- "Can I return just the saucepan from the bundle?" [--mode=vector-16]
// Modes: full, vector-8, hybrid-8, vector-16 (the default). Prints what was retrieved, then the answer.
import { ask, MODES, type Mode } from "./bot.ts";

const args = process.argv.slice(2);
const mode = (args.find((a) => a.startsWith("--mode="))?.slice(7) ?? "vector-16") as Mode;
if (!MODES.includes(mode)) throw new Error(`Unknown mode ${mode}; use one of ${MODES.join(", ")}`);
const question = args.filter((a) => !a.startsWith("--")).join(" ");
if (!question) throw new Error('Usage: npm run ask -- "your question" [--mode=full|vector-8|hybrid-8|vector-16]');

const r = await ask(question, mode);
if (r.retrieved.length) console.log(`Retrieved (${mode}): ${r.retrieved.join(", ")}\n`);
console.log(r.answer);
const stray = r.cited.filter((id) => !r.retrieved.includes(id));
console.log(
  `\n${r.total_ms} ms (${r.retrieval_ms} ms retrieval), $${r.cost_usd.toFixed(5)}` +
    (mode !== "full" ? `, ${r.cited.length} sources cited${stray.length ? `, NOT retrieved: ${stray.join(", ")}` : ""}` : ""),
);
