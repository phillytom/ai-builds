# Shared demo data

Every build works on the same fictional online store, so later builds can reuse earlier ones.

Planned files (seeded small in session 01, extended as later sessions need them):

| Path | Contents |
|---|---|
| `products.json` | id, title, description, price, category, inventory |
| `orders.json` | id, customer first name, items, status, carrier, tracking, dates |
| `support-emails.json` | messy inbound customer emails with hand-labeled intent, order id and urgency |
| `policies/` | returns, shipping, warranty and FAQ pages as Markdown (the RAG corpus) |
| `reviews.json` | product reviews (one carries the planted injection for session 18) |
| `invoices/` | synthetic supplier invoices as PDF (session 12) |

**Rules:** synthetic only. No real names, emails, phone numbers or addresses. Anything sensitive goes in `data/private/`, which is gitignored.
