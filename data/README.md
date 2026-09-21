# Shared demo data

Every build works on the same fictional online store (**Tom's Kitchen**, a DTC brand for small kitchen appliances and cookware), so later builds can reuse earlier ones.

Planned files (seeded small in session 01, extended as later sessions need them):

| Path | Contents |
|---|---|
| `products.json` | 30 products: sku (`KT-1001`…), name, category, description, price, variants, attributes, inventory, plus flags, shipping_surcharge_usd, bundle_skus, known_issues |
| `orders.json` | 30 orders: id (`TK-10201`…), customer first name, items (sku + variant), totals, status, carrier, tracking, dates |
| `support-emails.json` | 10 messy inbound emails with hand labels (intent, order id, sentiment, urgency, suggested action) and the label guide |
| `seed_store.py` | regenerates the three files above; deterministic |
| `policies/` | returns, shipping, warranty and FAQ pages as Markdown (the RAG corpus) |
| `reviews.json` | product reviews (one carries the planted injection for session 18) |
| `invoices/` | synthetic supplier invoices as PDF (session 12) |

**Rules:** synthetic only. No real names, emails, phone numbers or addresses. Anything sensitive goes in `data/private/`, which is gitignored.
