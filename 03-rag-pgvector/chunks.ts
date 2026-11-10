// Turns the shared store data into retrievable chunks:
//   - one chunk per "## " section of each policy page (id = section number, e.g. "§1.8", or "faq-orders")
//   - one chunk per product, with its variant rows folded together (id = SKU, e.g. "KT-2027")
import { readdirSync, readFileSync } from "node:fs";

export type Chunk = { id: string; source: string; title: string; text: string };

const data = (p: string) => new URL(`../data/${p}`, import.meta.url);

function policyChunks(): Chunk[] {
  const chunks: Chunk[] = [];
  for (const file of readdirSync(data("policies")).filter((f) => f.endsWith(".md")).sort()) {
    const md = readFileSync(data(`policies/${file}`), "utf8");
    const page = md.match(/^# (.+)$/m)![1];
    // Everything before the first "## " is the page intro; it stays out (it only summarises the sections).
    for (const section of md.split(/^## /m).slice(1)) {
      const [heading, ...body] = section.split("\n");
      const num = heading.match(/^(\d+\.\d+)\s/)?.[1];
      const id = num ? `§${num}` : `faq-${heading.toLowerCase().replace(/[^a-z]+/g, "-").replace(/-$/, "")}`;
      const title = `${page} › ${heading.trim()}`;
      chunks.push({ id, source: `policies/${file}`, title, text: `${title}\n\n${body.join("\n").trim()}` });
    }
  }
  return chunks;
}

// Minimal CSV parser: quoted fields may hold commas, newlines and doubled quotes.
function parseCsv(text: string): Record<string, string>[] {
  const rows: string[][] = [];
  let row: string[] = [], field = "", quoted = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (quoted) {
      if (c === '"' && text[i + 1] === '"') (field += '"'), i++;
      else if (c === '"') quoted = false;
      else field += c;
    } else if (c === '"') quoted = true;
    else if (c === ",") row.push(field), (field = "");
    else if (c === "\n") row.push(field), rows.push(row), (row = []), (field = "");
    else if (c !== "\r") field += c;
  }
  if (field || row.length) row.push(field), rows.push(row);
  const [header, ...body] = rows;
  return body.map((r) => Object.fromEntries(header.map((h, i) => [h, r[i] ?? ""])));
}

// Fields that differ between variants of one product; everything else is the same on every row.
const PER_VARIANT = ["variant_id", "color", "variant_stock", "restock_date"];
const SKIP = new Set(["upc", "sku", "name", "description", "care", ...PER_VARIANT]);

function productChunks(): Chunk[] {
  const rows = parseCsv(readFileSync(data("catalog-export.csv"), "utf8"));
  const bySku = new Map<string, Record<string, string>[]>();
  for (const r of rows) bySku.set(r.sku, [...(bySku.get(r.sku) ?? []), r]);
  return [...bySku].map(([sku, variants]) => {
    const p = variants[0];
    const title = `Product ${sku}: ${p.name}`;
    const facts = Object.entries(p)
      .filter(([k, v]) => !SKIP.has(k) && v !== "")
      .map(([k, v]) => `${k}: ${v}`);
    const vlines = variants.map((v) =>
      `- ${v.variant_id}${v.color ? ` (${v.color})` : ""}: ${v.variant_stock} in stock${v.restock_date ? `, restock ${v.restock_date}` : ""}`,
    );
    const text = [title, facts.join("\n"), `description: ${p.description}`, p.care && `care: ${p.care}`, `variants:\n${vlines.join("\n")}`]
      .filter(Boolean)
      .join("\n");
    return { id: sku, source: "catalog-export.csv", title, text };
  });
}

export function buildChunks(): Chunk[] {
  const chunks = [...policyChunks(), ...productChunks()];
  const dupes = chunks.map((c) => c.id).filter((id, i, all) => all.indexOf(id) !== i);
  if (dupes.length) throw new Error(`duplicate chunk ids: ${dupes}`);
  return chunks;
}
