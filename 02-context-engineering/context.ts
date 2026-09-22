// Builds the one big, byte-stable system prompt: instructions + the whole policy handbook + the whole catalog export.
// Nothing in here may vary between calls (no dates from the clock, no random order), or the cache never hits.
import { readdirSync, readFileSync } from "node:fs";

const data = (p: string) => new URL(`../data/${p}`, import.meta.url);

// Fixed "today" so date questions have one right answer. Kept in the cached prefix on purpose: it never changes.
export const TODAY = "2026-09-23";

const INSTRUCTIONS = `You are the customer support assistant for Tom's Kitchen, an online store for kitchen appliances and cookware.
Today is ${TODAY}.

Answer the customer's question using only the policy handbook and the catalog export below. When a policy and a product's
catalog row both matter, check both. Quote exact prices, dates, fees and SKUs. If the answer depends on something the
customer hasn't told you, say what it depends on and give the answer for each case. If the handbook and catalog don't
cover it, say so rather than guessing.

Write a direct answer in plain text, 150 words or fewer. No greeting and no sign-off.`;

const POLICY_ORDER = [
  "returns-and-exchanges.md",
  "shipping-and-delivery.md",
  "warranty.md",
  "prices-and-promotions.md",
  "payments-and-gift-cards.md",
  "pantry-club.md",
  "care-and-use.md",
  "faq.md",
  "support-playbook.md",
];

export function buildSystemPrompt(): string {
  const found = readdirSync(data("policies")).filter((f) => f.endsWith(".md")).sort();
  const missing = POLICY_ORDER.filter((f) => !found.includes(f));
  const extra = found.filter((f) => !POLICY_ORDER.includes(f));
  if (missing.length || extra.length) throw new Error(`policy files changed: missing ${missing}, unlisted ${extra}`);

  const handbook = POLICY_ORDER.map((f) => readFileSync(data(`policies/${f}`), "utf8").trim()).join("\n\n---\n\n");
  const catalog = readFileSync(data("catalog-export.csv"), "utf8").trim();
  return `${INSTRUCTIONS}

<policy_handbook>
${handbook}
</policy_handbook>

<catalog_export format="csv">
${catalog}
</catalog_export>`;
}
