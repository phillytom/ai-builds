"""Seed the shared Tom's Kitchen demo data. Synthetic only.

Run from the repo root:  python3 data/seed_store.py
Writes data/products.json, data/orders.json, data/support-emails.json.
Deterministic (fixed random seed), so re-running gives the same files.
"""
import json
import random
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).parent
random.seed(1001)

FREE_SHIPPING_OVER = 75
FLAT_SHIPPING = 6.95

# ---------------------------------------------------------------- products


def A(capacity=None, wattage=None, material=None, induction=None, dishwasher=None, warranty=12):
    return {
        "capacity": capacity,
        "wattage": wattage,
        "material": material,
        "induction_compatible": induction,
        "dishwasher_safe": dishwasher,
        "warranty_months": warranty,
    }


def V(sku, key, options):
    return [{"id": f"{sku}-{code}", key: label} for code, label in options]


def P(sku, name, category, description, price, variants, attributes, inventory, **extra):
    product = {
        "sku": sku,
        "name": name,
        "category": category,
        "description": description,
        "price": price,
        "variants": variants,
        "attributes": attributes,
        "inventory": inventory,
        "flags": [],
        "shipping_surcharge_usd": 0,
        "bundle_skus": [],
        "known_issues": [],
    }
    product.update(extra)
    return product


SA, CW, KP, ST, CG = "small appliances", "cookware", "knives & prep", "storage", "coffee gear"

PRODUCTS = [
    # small appliances
    P("KT-1001", "Rapid-Boil Electric Kettle 1.7L", SA,
      "Boils a full 1.7 litres in under five minutes and shuts off automatically. The push-button lid opens one-handed for easy filling.",
      59, V("KT-1001", "color", [("BLK", "Matte Black"), ("WHT", "White"), ("RED", "Tomato Red")]),
      A("1.7 L", 1500, "stainless steel", None, False, 24), 140,
      flags=["known_defect"],
      known_issues=[{
          "id": "KI-001",
          "summary": "Lid latch may not fully engage, so the lid can pop open while pouring.",
          "affects": "units shipped before 2026-09-01",
          "remedy": "free replacement lid assembly, or a full replacement on request",
      }]),
    P("KT-1002", "Wide-Slot 2-Slice Toaster", SA,
      "Extra-wide slots take bagels and thick sourdough without squashing them. Seven browning levels plus defrost and reheat.",
      49, V("KT-1002", "color", [("BLK", "Matte Black"), ("CRM", "Cream")]),
      A("2 slices", 900, "stainless steel", None, False, 12), 85),
    P("KT-1003", "Personal Blender 600W", SA,
      "Blends a smoothie straight into its own travel cup in about thirty seconds. Comes with two 20 oz cups and sip lids.",
      79, V("KT-1003", "color", [("GRY", "Slate Grey"), ("GRN", "Sage Green")]),
      A("20 oz", 600, "BPA-free Tritan", None, True, 12), 64),
    P("KT-1004", "Compact Air Fryer 4 Qt", SA,
      "Crisps fries, wings and vegetables with little or no oil. The nonstick basket lifts out and fits in a standard dishwasher rack.",
      129, [], A("4 qt", 1500, "steel with nonstick basket", None, True, 12), 37),
    P("KT-1005", "5-Speed Hand Mixer", SA,
      "Five speeds and a slow start so flour stays in the bowl. Beaters and dough hooks store in the snap-on case.",
      45, V("KT-1005", "color", [("WHT", "White"), ("RED", "Tomato Red")]),
      A(None, 250, "ABS plastic, stainless beaters", None, False, 12), 58),
    P("KT-1006", "Fuzzy-Logic Rice Cooker 6-Cup", SA,
      "Adjusts time and temperature on its own for white, brown and sushi rice. Keeps rice warm for up to twelve hours.",
      89, [], A("6 cups uncooked", 500, "aluminium inner pot, nonstick", None, False, 12), 41),

    # cookware
    P("KT-2001", "Everyday Nonstick Skillet 8\"", CW,
      "A small skillet for eggs, a single fillet or toasting spices. Three-layer PFOA-free nonstick on a hard-anodised body.",
      34, [], A("8 in", None, "hard-anodised aluminium", False, True, 24), 120),
    P("KT-2002", "Everyday Nonstick Skillet 10\"", CW,
      "The pan for weeknight dinners, big enough for two chicken breasts or a four-egg omelette. Three-layer PFOA-free nonstick on a hard-anodised body.",
      44, [], A("10 in", None, "hard-anodised aluminium", False, True, 24), 96),
    P("KT-2003", "Tri-Ply Stainless Saucepan 3 Qt", CW,
      "Aluminium core clad in stainless steel heats evenly all the way up the sides. Includes a tight-fitting lid and interior measuring marks.",
      59, [], A("3 qt", None, "tri-ply stainless steel", True, True, 120), 73),
    P("KT-2004", "Enameled Cast Iron Dutch Oven 7 Qt", CW,
      "Holds heat for slow braises, soups and no-knead bread. Weighs 15 lb (6.9 kg), so a heavy-item shipping surcharge applies.",
      189, V("KT-2004", "color", [("BLU", "Deep Blue"), ("CRM", "Cream"), ("RED", "Tomato Red")]),
      A("7 qt", None, "enameled cast iron", True, False, 120), 22,
      flags=["heavy_item_surcharge"], shipping_surcharge_usd=15, weight_kg=6.9),
    P("KT-2005", "Carbon Steel Wok 12\"", CW,
      "Heats fast and builds a natural nonstick patina the more you cook. Flat bottom sits steady on gas, electric and induction hobs.",
      69, [], A("12 in", None, "carbon steel", True, False, 24), 48),
    P("KT-2006", "Everyday Cookware Bundle (3-Piece)", CW,
      "The 8\" skillet, 10\" skillet and 3 qt saucepan in one box for less than buying them separately. A good first set for a new kitchen.",
      119, [], A("3 pieces", None, "see component products", None, None, 24), 30,
      flags=["bundle"], bundle_skus=["KT-2001", "KT-2002", "KT-2003"]),

    # knives & prep
    P("KT-3001", "Chef's Knife 8\"", KP,
      "A full-tang all-rounder for chopping, slicing and mincing. Ground to a 15-degree edge and balanced at the bolster.",
      89, [], A("8 in blade", None, "high-carbon stainless steel", None, False, 120), 66),
    P("KT-3002", "Paring Knife 3.5\"", KP,
      "For peeling, trimming and any job too fiddly for a big knife. Same steel and handle as the 8\" chef's knife.",
      29, [], A("3.5 in blade", None, "high-carbon stainless steel", None, False, 120), 110),
    P("KT-3003", "Serrated Bread Knife 9\"", KP,
      "Long scalloped serrations cut crusty loaves without crushing the crumb. Also handy for tomatoes and layer cakes.",
      49, [], A("9 in blade", None, "high-carbon stainless steel", None, False, 120), 52),
    P("KT-3004", "Acacia Cutting Board", KP,
      "End-grain acacia is kind to knife edges and heavy enough to stay put. Juice groove on one side, flat on the other.",
      45, V("KT-3004", "size", [("M", "Medium 14 x 10 in"), ("L", "Large 18 x 12 in")]),
      A(None, None, "acacia wood", None, False, 12), 77),
    P("KT-3005", "Adjustable Mandoline Slicer", KP,
      "A dial sets slice thickness from paper-thin to 9 mm, with julienne blades built in. Ships with a hand guard and a cut-resistant glove.",
      39, [], A(None, None, "stainless steel blade, ABS body", None, True, 12), 45),
    P("KT-3006", "Dual-Grit Whetstone 1000/6000", KP,
      "The 1000 grit side restores a dull edge and the 6000 side polishes it. Comes with a non-slip bamboo base and an angle guide.",
      35, [], A(None, None, "corundum", None, False, 12), 60),

    # storage
    P("KT-4001", "Glass Food Storage Set (10-Piece)", ST,
      "Five borosilicate glass containers with five snap-lock lids, safe from freezer to oven. The glass will not stain or hold smells.",
      42, [], A("1 to 6 cups", None, "borosilicate glass, BPA-free lids", None, True, 12), 88),
    P("KT-4002", "Airtight Pantry Canisters (Set of 3)", ST,
      "One-press lids seal out air and moisture to keep flour, pasta and cereal fresh. Clear sides show what is running low.",
      36, [], A("0.8 / 1.4 / 2.0 qt", None, "BPA-free plastic", None, True, 12), 92),
    P("KT-4003", "Reusable Silicone Bags (4-Pack)", ST,
      "Leakproof zip-top bags that replace single-use plastic for snacks, marinades and sous vide. Two sandwich and two half-gallon sizes.",
      18, [], A("2 x 15 oz, 2 x 64 oz", None, "food-grade silicone", None, True, 12), 150),
    P("KT-4004", "Silicone Stretch Lids (6-Pack)", ST,
      "Six sizes stretch over bowls, cans, jars and cut fruit. They handle the microwave and the freezer.",
      12, [], A("2.6 to 8 in", None, "food-grade silicone", None, True, 12), 210),
    P("KT-4005", "Vacuum-Seal Coffee & Dry Goods Canister", ST,
      "Twist the lid to pump out air and keep coffee beans or nuts fresh for longer. A date wheel on the lid tracks when you filled it.",
      32, V("KT-4005", "color", [("BLK", "Matte Black"), ("STL", "Brushed Steel")]),
      A("1.2 qt", None, "stainless steel", None, False, 12), 70),
    P("KT-4006", "Glass Spice Jar Set (12 Jars)", ST,
      "Twelve 4 oz square jars with shaker inserts and bamboo lids. Includes 120 printed labels and a fine-tip chalk pen.",
      24, [], A("4 oz each", None, "glass, bamboo lids", None, False, 12), 99),

    # coffee gear
    P("KT-5001", "Conical Burr Grinder", CG,
      "Forty grind settings cover everything from espresso to French press. Steel conical burrs run slowly so the beans stay cool.",
      149, V("KT-5001", "color", [("BLK", "Matte Black"), ("WHT", "White")]),
      A("8 oz hopper", 150, "stainless steel burrs", None, False, 24), 0,
      flags=["out_of_stock"], restock_date="2026-10-12"),
    P("KT-5002", "Pour-Over Dripper Set", CG,
      "A ceramic cone dripper, glass server and 40 paper filters for clean single cups. Brews up to 20 oz at a time.",
      32, V("KT-5002", "color", [("WHT", "White"), ("BLK", "Matte Black")]),
      A("20 oz", None, "ceramic and borosilicate glass", None, True, 12), 83),
    P("KT-5003", "Double-Wall French Press 1L", CG,
      "Insulated stainless walls keep coffee hot for about an hour. A two-stage filter keeps grit out of the cup.",
      38, [], A("1 L", None, "stainless steel", None, True, 12), 76),
    P("KT-5004", "Handheld Milk Frother", CG,
      "Makes foam for a latte or cappuccino in about twenty seconds. Charges over USB-C and stands on its own base.",
      19, [], A(None, 5, "stainless steel whisk", None, False, 12), 134),
    P("KT-5005", "Coffee Scale with Timer", CG,
      "Weighs to 0.1 g with a built-in brew timer for repeatable pour-overs. The silicone mat protects it from heat and spills.",
      45, [], A("2 kg max", None, "ABS with silicone mat", None, False, 12), 57),
    P("KT-5006", "Compact Espresso Machine", CG,
      "A 15-bar pump and a steam wand in a machine under eight inches wide. Heats up in about forty seconds.",
      249, V("KT-5006", "color", [("STL", "Brushed Steel"), ("BLK", "Matte Black")]),
      A("1.4 L tank", 1350, "stainless steel", None, False, 24), 18),
]

BY_SKU = {p["sku"]: p for p in PRODUCTS}

# ------------------------------------------------------------------ orders

CARRIERS = {"UPS": "U", "USPS": "P", "FedEx": "F"}
STATES = ["SC", "GA", "NC", "CA", "OR", "TX", "NY", "IL", "WA", "CO", "MA", "FL", "OH", "MN"]
NAMES = ["Alex", "Jordan", "Casey", "Riley", "Morgan", "Avery", "Quinn", "Harper", "Rowan", "Jules",
         "Theo", "Mina", "Omar", "Elena", "Kofi", "Hana", "Luca", "Nadia", "Pablo", "Greta", "Owen"]


def d(s):
    return date.fromisoformat(s)


def tracking(order_num, carrier):
    # Fake format on purpose: does not match any real carrier's numbering.
    return f"TK{CARRIERS[carrier]}{(order_num * 7919) % 10**9:09d}"


def line(sku, variant=None, qty=1):
    return {"sku": sku, "variant_id": variant, "name": BY_SKU[sku]["name"],
            "qty": qty, "unit_price": BY_SKU[sku]["price"]}


def build_order(num, first_name, items, placed, status, carrier, ship_days=1, transit_days=4, note=None):
    subtotal = sum(i["qty"] * i["unit_price"] for i in items)
    surcharge = sum(i["qty"] * BY_SKU[i["sku"]]["shipping_surcharge_usd"] for i in items)
    shipping = 0 if subtotal >= FREE_SHIPPING_OVER else FLAT_SHIPPING
    shipped = placed + timedelta(days=ship_days)
    eta = shipped + timedelta(days=transit_days)
    has_shipped = status in ("shipped", "delayed", "delivered", "refunded")
    order = {
        "id": f"TK-{num}",
        "customer_first_name": first_name,
        "ship_to_state": random.choice(STATES),
        "items": items,
        "subtotal": subtotal,
        "shipping": shipping,
        "heavy_item_surcharge": surcharge,
        "total": round(subtotal + shipping + surcharge, 2),
        "status": status,
        "carrier": carrier if has_shipped else None,
        "tracking": tracking(num, carrier) if has_shipped else None,
        "placed_at": placed.isoformat(),
        "shipped_at": shipped.isoformat() if has_shipped else None,
        "estimated_delivery": eta.isoformat() if has_shipped else None,
        "delivered_at": eta.isoformat() if status in ("delivered", "refunded") else None,
        "note": note,
    }
    return order


# Orders the support emails point at. Everything else is filler.
SCRIPTED = {
    10204: ("Noor", [line("KT-2005")], d("2026-08-24"), "delivered", "USPS"),
    10207: ("Marcus", [line("KT-1004")], d("2026-09-09"), "delayed", "UPS",
            "Carrier scan gap since 2026-09-12; original estimate missed."),
    10209: ("Walt", [line("KT-1001", "KT-1001-WHT")], d("2026-08-27"), "delivered", "USPS"),
    10211: ("Sam", [line("KT-2004", "KT-2004-BLU")], d("2026-09-02"), "delivered", "FedEx"),
    10214: ("Dana", [line("KT-1001", "KT-1001-RED"), line("KT-5002", "KT-5002-WHT")],
            d("2026-08-24"), "delivered", "UPS"),
    10217: ("Lena", [line("KT-2006")], d("2026-09-07"), "delivered", "UPS"),
    10219: ("Ingrid", [line("KT-2002"), line("KT-3002")], d("2026-09-09"), "delivered", "USPS"),
    10221: ("Priya", [line("KT-3005")], d("2026-09-06"), "delivered", "USPS"),
    10223: ("Beth", [line("KT-1002", "KT-1002-CRM")], d("2026-09-20"), "processing", "UPS"),
    10225: ("Victor", [line("KT-5006", "KT-5006-STL")], d("2026-09-15"), "shipped", "FedEx",
            "Payment processor shows one capture plus one authorization hold that will drop off."),
}

FILLER_STATUS = {10203: "cancelled", 10206: "refunded"}


def filler_order(num):
    placed = d("2026-08-20") + timedelta(days=round((num - 10201) * 31 / 29))
    in_stock = [p for p in PRODUCTS if p["inventory"] > 0]
    items = []
    for p in random.sample(in_stock, random.choice([1, 1, 2, 2, 3])):
        variant = random.choice(p["variants"])["id"] if p["variants"] else None
        items.append(line(p["sku"], variant, random.choice([1, 1, 1, 2])))
    if num in FILLER_STATUS:
        status = FILLER_STATUS[num]
    elif placed >= d("2026-09-19"):
        status = "processing"
    elif placed >= d("2026-09-16"):
        status = "shipped"
    else:
        status = "delivered"
    note = {"cancelled": "Cancelled by customer before shipping.",
            "refunded": "Returned within 30 days; refunded to original payment method."}.get(status)
    return build_order(num, random.choice(NAMES), items, placed, status,
                       random.choice(list(CARRIERS)), note=note)


ORDERS = []
for num in range(10201, 10231):
    if num in SCRIPTED:
        name, items, placed, status, carrier, *rest = SCRIPTED[num]
        ORDERS.append(build_order(num, name, items, placed, status, carrier, note=rest[0] if rest else None))
    else:
        ORDERS.append(filler_order(num))

ORDER = {o["id"]: o for o in ORDERS}

# ------------------------------------------------------------------ emails

LABEL_GUIDE = {
    "intent": {
        "order_status": "Where is my order / delivery timing.",
        "return_request": "Wants to send back something that arrived as ordered and works.",
        "defect_warranty": "Item arrived as ordered but is faulty or has failed.",
        "how_to": "Question about a product: how to use it, what it works with, when it is back in stock.",
        "damaged_in_shipping": "Item or box arrived physically damaged by the carrier.",
        "wrong_item": "Box contents do not match the order (wrong or missing item).",
        "cancel_order": "Wants to cancel or change an order that has not shipped.",
        "other": "None of the above, including billing disputes.",
    },
    "order_id": "The order id as the customer wrote it, normalised to TK-NNNNN. null if none is given. "
                "Never invented. Tracking numbers are not order ids. It may not match a real order "
                "(see label_meta.order_id_valid).",
    "product_sku": "SKU of the one product the email is mainly about, from the catalog. For wrong_item, "
                   "the product that was ordered. null if the email does not identify a product.",
    "sentiment": ["positive", "neutral", "negative"],
    "urgency": {
        "high": "Safety issue, money dispute, or a time window that closes within about a day.",
        "medium": "Customer is blocked or waiting on us, but nothing gets worse today.",
        "low": "No time pressure.",
    },
    "suggested_action": {
        "send_tracking": "", "refund": "Includes starting a return for refund.", "replace": "",
        "answer_question": "", "cancel": "Cancel or edit an unshipped order.",
        "escalate": "Always wins when there is an injury, a safety risk, or a legal or chargeback threat.",
    },
    "product_issue": "Short free text or null. Not labeled, not scored.",
    "primary_intent_rule": "When an email has two intents, label the one that needs an action from us; "
                           "the other goes in label_meta.secondary_intent (not scored).",
}


def email(n, received, first_name, subject, body, *, intent, order_id, sku, sentiment, urgency, action,
          secondary_intent=None, skus=(), order_id_valid=None, actual_order_id=None, label_note=None):
    return {
        "id": f"EM-{n:03d}",
        "received_at": received,
        "from_first_name": first_name,
        "subject": subject,
        "body": body,
        "labels": {
            "intent": intent,
            "order_id": order_id,
            "product_sku": sku,
            "sentiment": sentiment,
            "urgency": urgency,
            "suggested_action": action,
        },
        "label_meta": {
            "secondary_intent": secondary_intent,
            "skus": list(skus),
            "order_id_valid": order_id_valid,
            "actual_order_id": actual_order_id,
            "note": label_note,
        },
    }


lena = ORDER["TK-10217"]

EMAILS = [
    email(1, "2026-09-18T08:12:00-04:00", "Marcus", "wheres my order",
          "hi, i orderd the air fryer like 9 days ago (order 10207) and the tracking hasnt moved since "
          "last week?? it said it would be here by the 14th. can someone tell me whats going on. "
          "need it for my sons bday dinner on the 26th\n\nmarcus",
          intent="order_status", order_id="TK-10207", sku="KT-1004", sentiment="negative", urgency="medium",
          action="send_tracking", skus=["KT-1004"], order_id_valid=True, actual_order_id="TK-10207",
          label_note="Annoyed but civil; I called it negative. Deadline is 8 days out, so medium not high."),

    email(2, "2026-09-16T19:47:00-04:00", "Dana", "YOUR KETTLE BURNED MY HAND",
          "I am FURIOUS. The lid on the red kettle I bought from you (TK10214) FLEW OPEN while I was "
          "pouring and boiling water went all over my hand. I had it under cold water for 20 minutes. "
          "The latch has NEVER clicked shut properly since day one and I assumed that was just how it was. "
          "This thing is DANGEROUS and you are still selling it!!! I want to know what you are going to "
          "do about this. The pour over thing in the same order is fine, not that it matters.\n\nDana",
          intent="defect_warranty", order_id="TK-10214", sku="KT-1001", sentiment="negative", urgency="high",
          action="escalate", skus=["KT-1001"], order_id_valid=True, actual_order_id="TK-10214",
          label_note="Known issue KI-001. Injury means escalate beats replace."),

    email(3, "2026-09-17T10:05:00-04:00", "Walt", "Kettle lid question",
          "Hello,\n\nI bought one of your white electric kettles at the end of August. It works well but "
          "the lid doesn't seem to click closed, it just sort of rests there, and it lifted a bit when I "
          "poured this morning. Is that normal or did I get a dud? I don't have the order number handy, "
          "sorry, it would have been under Walt. Happy to send a photo if that helps.\n\nThanks,\nWalt",
          intent="defect_warranty", order_id=None, sku="KT-1001", sentiment="neutral", urgency="medium",
          action="replace", skus=["KT-1001"], order_id_valid=None, actual_order_id="TK-10209",
          label_note="Same defect as EM-002, polite, no order id, no injury. Medium because the fault is a "
                     "scald risk even though he is calm. Arguable: answer_question."),

    email(4, "2026-09-16T13:30:00-04:00", "Ingrid", "Re: Your Tom's Kitchen order TK-10219 has been delivered",
          "Hi there - box arrived Monday, thank you. The little paring knife is great. But the skillet in "
          "the box is the 8 inch and I definitely ordered the 10 (it says 10\" on the packing slip too!). "
          "Bit annoying as I bought it specifically because the 8 I already have is too small. "
          "Can you send the right one? Do I need to post this one back?\n\nIngrid\n\n"
          "> Your order has been delivered. Track your package: ...",
          intent="wrong_item", order_id="TK-10219", sku="KT-2002", sentiment="negative", urgency="medium",
          action="replace", skus=["KT-2002", "KT-2001"], order_id_valid=True,
          actual_order_id="TK-10219",
          label_note="Order id appears only in the subject line. Mildly negative; arguable: neutral."),

    email(5, "2026-09-19T21:14:00-04:00", "Noor", "couple of questions!",
          "Hiya! First off I LOVE the wok I got from you last month, it's basically the only pan I use "
          "now :) Two q's: 1) we just moved and the new place has an induction hob. will the 10 inch "
          "nonstick skillet work on it? the wok does which is great. 2) the burr grinder says sold out, "
          "any idea when its back? want to get it for my partner's birthday in november. thanks!!\nNoor x",
          intent="how_to", order_id=None, sku="KT-2002", sentiment="positive", urgency="low",
          action="answer_question", skus=["KT-2002", "KT-5001", "KT-2005"], order_id_valid=None,
          actual_order_id=None,
          label_note="Two products asked about; product_sku is the first (the skillet). Arguable. Answers live in products.json: KT-2002 is not induction compatible; KT-5001 restocks 2026-10-12."),

    email(6, "2026-09-20T16:52:00-04:00", "Beth", "change my order pls!!",
          "Hi i JUST placed an order like 10 min ago for the toaster and i clicked cream by accident, "
          "i wanted the black one to match my kettle. order number is TK-10232. can you switch it before "
          "it ships?? if you cant switch it then just cancel it and ill reorder. thanks so much\nBeth",
          intent="cancel_order", order_id="TK-10232", sku="KT-1002", sentiment="neutral", urgency="high",
          action="cancel", skus=["KT-1002"], order_id_valid=False, actual_order_id="TK-10223",
          label_note="She transposed two digits: TK-10232 does not exist, her order is TK-10223. The label is "
                     "what she wrote, because the model only sees the email. High because it must happen before shipping."),

    email(7, "2026-09-17T09:40:00-04:00", "Sam", "dutch oven",
          "Hello, I received the blue dutch oven (order #TK 10211). It's lovely but honestly it is much "
          "heavier than I expected and with my wrists I can't lift it safely when it's full, so I think "
          "I need to send it back. How does that work? Also I noticed I was charged an extra $15 on top "
          "of the price that I don't remember agreeing to, what was that for and do I get it back too?\n\n"
          "Regards\nSam",
          intent="return_request", order_id="TK-10211", sku="KT-2004", sentiment="neutral", urgency="low",
          action="refund", secondary_intent="other", skus=["KT-2004"], order_id_valid=True,
          actual_order_id="TK-10211",
          label_note="Two intents. Return is primary (it needs an action); the $15 is the heavy-item surcharge."),

    email(8, "2026-09-18T12:26:00-04:00", "Lena", "Fwd: Order confirmation",
          "hi - something's missing from my cookware bundle. got the two frying pans but no saucepan, and "
          "there was no second box. pasting my confirmation below\n\n"
          "---------- Forwarded message ---------\n"
          "Thanks for your order, Lena!\n"
          f"Order: {lena['id']}   Placed: {lena['placed_at']}\n"
          "1 x Everyday Cookware Bundle (3-Piece)   $119.00\n"
          f"Shipped via {lena['carrier']}, tracking {lena['tracking']}\n\n"
          "can you send the saucepan? thx\n\nSent from my iPhone",
          intent="wrong_item", order_id="TK-10217", sku="KT-2006", sentiment="neutral", urgency="medium",
          action="replace", skus=["KT-2006", "KT-2003"], order_id_valid=True,
          actual_order_id="TK-10217",
          label_note="Tracking number sits next to the order id as a distractor."),

    email(9, "2026-09-19T07:58:00-04:00", "Victor", "CHARGED TWICE - fix this today",
          "I ordered ONE espresso machine on the 15th (order 10225) and my card shows TWO charges of "
          "$249 from Tom's Kitchen. That is nearly five hundred dollars. I have emailed once already and "
          "heard nothing. If the second charge is not reversed by end of day I am disputing both with my "
          "bank and you can have the machine back.\n\nVictor",
          intent="other", order_id="TK-10225", sku="KT-5006", sentiment="negative", urgency="high",
          action="escalate", skus=["KT-5006"], order_id_valid=True, actual_order_id="TK-10225",
          label_note="Billing has no intent of its own in this schema, so other. Chargeback threat means escalate beats refund. The second charge is really an "
                     "authorization hold (see order note), which the model cannot know."),

    email(10, "2026-09-18T18:03:00-04:00", "Priya", "my order",
          "Hi, I got my package last week and it's not really what I expected to be honest. "
          "What are my options?\nThanks, Priya",
          intent="return_request", order_id=None, sku=None, sentiment="neutral", urgency="low",
          action="answer_question", skus=[], order_id_valid=None, actual_order_id="TK-10221",
          label_note="Deliberately vague: no product, no order id, no stated problem. The most arguable label "
                     "in the set. We have to ask what she bought before anything else, hence answer_question. "
                     "Alternative: intent other."),
]


def write(name, payload):
    path = HERE / name
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {path.relative_to(HERE.parent)}")


write("products.json", PRODUCTS)
write("orders.json", ORDERS)
write("support-emails.json", {"label_guide": LABEL_GUIDE, "emails": EMAILS})
