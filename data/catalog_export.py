"""Write data/catalog-export.csv: the full Tom's Kitchen catalog as a merchandising export. Synthetic only.

Run from the repo root:  python3 data/catalog_export.py
One row per variant (color or size), the way a merchandising system exports it, so product-level
fields repeat on each variant row. The first 30 products are data/products.json, unchanged. The rest
are generated from the product families below. Deterministic (fixed random seed). Session 02 puts this whole file in the prompt.
"""
import csv
import json
import random
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).parent
random.seed(2002)

COLUMNS = [
    "variant_id", "sku", "name", "color", "upc", "variant_stock", "category", "collection", "list_price",
    "sale_price", "final_sale",
    "capacity", "dimensions_in", "weight_lb", "material", "induction_compatible", "dishwasher_safe",
    "oven_safe_to_f", "warranty_months", "voltage", "heavy_item_surcharge_usd", "ships_separately",
    "restock_date", "country_of_origin", "bundle_skus", "description", "care",
]

SA, CW, KP, ST, CG = "small appliances", "cookware", "knives & prep", "storage", "coffee gear"

CARE = {
    "nonstick": "Wood, silicone or nylon utensils only. Low to medium heat. Hand washing extends coating life.",
    "induction nonstick": "Wood, silicone or nylon utensils only. Low to medium heat. Steel base plate works on induction.",
    "tri-ply": "Preheat before adding oil. Vinegar removes rainbow tints. Dishwasher safe.",
    "enameled": "Hand wash. Low to medium heat. No cold water on a hot pot.",
    "carbon": "Hand wash, dry on the hob, wipe with oil. Never soak or use the dishwasher.",
    "cast iron": "Hand wash, dry straight away, keep lightly oiled. Never soak or use the dishwasher.",
    "bakeware": "Hand wash recommended. No metal utensils on coated surfaces.",
    "ceramic": "Dishwasher and microwave safe. Avoid sudden temperature changes.",
    "appliance": "Unplug before cleaning. Wipe the base with a damp cloth; never immerse it. 120 V only.",
    "knife": "Hand wash and dry. Cut on wood or plastic. Hone regularly.",
    "wood": "Hand wash, dry on edge, oil monthly. Never soak.",
    "tool": "Dishwasher safe on the top rack.",
    "tool hand": "Hand wash and dry.",
    "glass": "Let glass reach room temperature before the oven. Lids are not oven safe.",
    "plastic": "Top-rack dishwasher safe. Not for the microwave.",
    "silicone": "Dishwasher, microwave and freezer safe.",
    "steel": "Hand wash. Dry to avoid water spots.",
    "coffee": "Rinse after each use. Descale monthly in hard-water areas.",
}

COLORS = {
    "enamel": [("BLU", "Harbor Blue"), ("RED", "Cherry Red"), ("GRN", "Olive"), ("WHT", "Chalk White"), ("BLK", "Graphite")],
    "appliance": [("BLK", "Matte Black"), ("WHT", "White"), ("SST", "Brushed Steel"), ("RED", "Tomato Red"), ("CRM", "Cream"), ("GRN", "Sage Green")],
    "nonstick": [("GRY", "Charcoal"), ("BLU", "Navy"), ("SND", "Sand")],
    "wood": [("WAL", "Walnut"), ("MAP", "Maple"), ("ACA", "Acacia")],
    "silicone": [("GRY", "Slate Grey"), ("GRN", "Sage Green"), ("TER", "Terracotta"), ("BLU", "Harbor Blue")],
}


def fam(category, collection, base, sizes, material, price, care, *, induction=None, dishwasher=None,
        oven=None, warranty=12, volts=None, origin="China", colors=None, desc="", weight=1.0, dims="",
        heavy=None, separately=False):
    """One product family; sizes is a list of (size label, price delta, weight delta)."""
    return dict(category=category, collection=collection, base=base, sizes=sizes, material=material,
                price=price, care=care, induction=induction, dishwasher=dishwasher, oven=oven,
                warranty=warranty, volts=volts, origin=origin, colors=colors, desc=desc, weight=weight,
                dims=dims, heavy=heavy or {}, separately=separately)


FAMILIES = [
    # ---------------------------------------------------------------- cookware
    fam(CW, "Everyday", "Everyday Nonstick Skillet", [('12"', 0, 0)], "hard-anodised aluminium, PFOA-free nonstick",
        54, "nonstick", induction=False, dishwasher=True, oven=400, warranty=24, colors=COLORS["nonstick"],
        desc="The family-size member of the Everyday range, with room for a full pan of fried rice or four burgers.",
        weight=2.9, dims="21.5 x 12.2 x 2.2"),
    fam(CW, "Everyday", "Induction-Ready Nonstick Skillet", [('8"', 0, 0), ('10"', 12, 0.6), ('12"', 22, 1.2)],
        "aluminium with steel induction plate, PFOA-free nonstick", 42, "induction nonstick", induction=True,
        dishwasher=True, oven=400, warranty=24, colors=COLORS["nonstick"],
        desc="Everyday nonstick with a bonded steel plate in the base, so it works on induction hobs as well as gas and electric.",
        weight=1.9, dims="varies by size"),
    fam(CW, "Everyday", "Everyday Nonstick Saucepan", [("1.5 Qt", 0, 0), ("2.5 Qt", 8, 0.5)],
        "hard-anodised aluminium, PFOA-free nonstick", 39, "nonstick", induction=False, dishwasher=True,
        oven=400, warranty=24, desc="For porridge, sauces and anything that likes to stick. Glass lid with a steam vent.",
        weight=2.0, dims="7.5 x 15 x 4"),
    fam(CW, "Pro Clad", "Tri-Ply Stainless Skillet", [('8"', 0, 0), ('10"', 15, 0.8), ('12"', 30, 1.5)],
        "tri-ply stainless steel, aluminium core", 55, "tri-ply", induction=True, dishwasher=True, oven=500,
        warranty=120, origin="Portugal", desc="Sears evenly edge to edge and goes from hob to oven. Flared rim for drip-free pouring.",
        weight=2.2, dims="varies by size"),
    fam(CW, "Pro Clad", "Tri-Ply Stainless Saucepan", [("1.5 Qt", -14, -0.8), ("2 Qt", -8, -0.4), ("4 Qt", 12, 0.9)],
        "tri-ply stainless steel, aluminium core", 59, "tri-ply", induction=True, dishwasher=True, oven=500,
        warranty=120, origin="Portugal", desc="The same tri-ply build as our 3 Qt saucepan, with a snug stainless lid.",
        weight=3.0, dims="varies by size"),
    fam(CW, "Pro Clad", "Tri-Ply Stainless Saucier 3 Qt", [("", 0, 0)], "tri-ply stainless steel, aluminium core",
        89, "tri-ply", induction=True, dishwasher=True, oven=500, warranty=120, origin="Portugal",
        desc="Rounded sides let a whisk reach every corner, for risotto, custard and pan sauces.", weight=3.4,
        dims="16.5 x 9 x 4.2"),
    fam(CW, "Pro Clad", "Tri-Ply Stainless Saute Pan", [("3.5 Qt", 0, 0), ("5 Qt", 25, 1.3)],
        "tri-ply stainless steel, aluminium core", 99, "tri-ply", induction=True, dishwasher=True, oven=500,
        warranty=120, origin="Portugal", desc="Straight sides and a helper handle for braising, shallow frying and one-pan dinners.",
        weight=4.6, dims="varies by size"),
    fam(CW, "Pro Clad", "Tri-Ply Stainless Stockpot", [("8 Qt", 0, 0), ("12 Qt", 40, 3.1)],
        "tri-ply stainless steel, aluminium core", 119, "tri-ply", induction=True, dishwasher=True, oven=500,
        warranty=120, origin="Portugal", desc="Tall enough for stock, pasta for a crowd or a batch of chili.",
        weight=7.1, dims="varies by size", heavy={"12 Qt": 10}),
    fam(CW, "Pro Clad", "Stainless Steel Pasta Insert", [("for 8 Qt", 0, 0)], "18/10 stainless steel", 39, "tri-ply",
        induction=None, dishwasher=True, oven=500, warranty=24, desc="Perforated insert that lifts pasta out of the 8 Qt stockpot in one go.",
        weight=1.3, dims="10.5 x 10.5 x 7"),
    fam(CW, "Heirloom", "Enameled Cast Iron Dutch Oven", [("3.5 Qt", -80, -7.2), ("5.5 Qt", -40, -3.4), ("9 Qt", 60, 4.8)],
        "enameled cast iron", 189, "enameled", induction=True, dishwasher=False, oven=500, warranty=120,
        origin="France", colors=COLORS["enamel"], desc="Heavy lid with self-basting spikes. Holds heat for slow braises and bread.",
        weight=15.2, dims="varies by size", heavy={"9 Qt": 20}),
    fam(CW, "Heirloom", "Enameled Cast Iron Braiser 3.5 Qt", [("", 0, 0)], "enameled cast iron", 159, "enameled",
        induction=True, dishwasher=False, oven=500, warranty=120, origin="France", colors=COLORS["enamel"],
        desc="Wide and shallow, for browning then braising in the same pan.", weight=11.0, dims="15.4 x 12.5 x 4.7"),
    fam(CW, "Heirloom", "Enameled Cast Iron Oval Casserole 6.75 Qt", [("", 0, 0)], "enameled cast iron", 229,
        "enameled", induction=True, dishwasher=False, oven=500, warranty=120, origin="France",
        colors=COLORS["enamel"], desc="An oval shape that fits a whole chicken or a pork shoulder.", weight=14.3,
        dims="15.8 x 10.4 x 6.4", heavy={"": 15}),
    fam(CW, "Heirloom", "Pre-Seasoned Cast Iron Skillet", [('10"', 0, 0), ('12"', 12, 1.6)], "cast iron", 39,
        "cast iron", induction=True, dishwasher=False, oven=650, warranty=120, origin="USA",
        desc="Seasoned with vegetable oil and ready to cook. Two pour spouts and a helper handle.", weight=5.4,
        dims="varies by size"),
    fam(CW, "Heirloom", "Cast Iron Grill Pan 10.5\"", [("", 0, 0)], "cast iron", 45, "cast iron", induction=True,
        dishwasher=False, oven=650, warranty=120, origin="USA", desc="Raised ribs for grill marks indoors.", weight=6.1,
        dims="17.5 x 10.7 x 2"),
    fam(CW, "Heirloom", "Reversible Cast Iron Griddle", [("", 0, 0)], "cast iron", 59, "cast iron", induction=True,
        dishwasher=False, oven=650, warranty=120, origin="USA",
        desc="Flat on one side for pancakes, ridged on the other. Spans two burners.", weight=8.9, dims="20 x 10.4 x 0.8"),
    fam(CW, "Workshop", "Carbon Steel Skillet", [('10"', 0, 0), ('12"', 15, 0.9)], "carbon steel", 55, "carbon",
        induction=True, dishwasher=False, oven=600, warranty=24, origin="France",
        desc="Light like stainless, nonstick like cast iron once seasoned.", weight=3.3, dims="varies by size"),
    fam(CW, "Workshop", "Carbon Steel Crepe Pan 10\"", [("", 0, 0)], "carbon steel", 42, "carbon", induction=True,
        dishwasher=False, oven=600, warranty=24, origin="France", desc="Low sides for flipping crepes and tortillas.",
        weight=2.4, dims="17.7 x 10.2 x 0.9"),
    fam(CW, "Bakehouse", "Aluminized Steel Sheet Pan", [("Quarter", -8, -0.5), ("Half", 0, 0)], "aluminized steel",
        24, "bakeware", induction=None, dishwasher=False, oven=500, warranty=24, origin="USA",
        desc="Rolled edges that don't warp in a hot oven.", weight=1.6, dims="varies by size"),
    fam(CW, "Bakehouse", "Nonstick Loaf Pan 9 x 5", [("", 0, 0)], "aluminized steel, PFOA-free nonstick", 19,
        "bakeware", dishwasher=False, oven=450, warranty=24, origin="USA", desc="Releases banana bread cleanly.",
        weight=0.9, dims="10.5 x 5.8 x 2.8"),
    fam(CW, "Bakehouse", "Nonstick Muffin Tin 12-Cup", [("", 0, 0)], "aluminized steel, PFOA-free nonstick", 24,
        "bakeware", dishwasher=False, oven=450, warranty=24, origin="USA", desc="Twelve standard cups with wide handles.",
        weight=1.5, dims="15.8 x 10.8 x 1.2"),
    fam(CW, "Bakehouse", "Round Cake Pans 9\" (Set of 2)", [("", 0, 0)], "anodised aluminium", 29, "bakeware",
        dishwasher=False, oven=500, warranty=24, origin="USA", desc="Straight sides for level layers.", weight=1.4,
        dims="9.5 x 9.5 x 2"),
    fam(CW, "Bakehouse", "Stoneware Baking Dish 9 x 13", [("", 0, 0)], "glazed stoneware", 49, "ceramic",
        dishwasher=True, oven=500, warranty=12, origin="Portugal", colors=COLORS["enamel"][:3],
        desc="Oven to table for lasagne and crumbles.", weight=6.2, dims="15.5 x 9.8 x 3"),
    fam(CW, "Bakehouse", "Stoneware Pie Dish 9.5\"", [("", 0, 0)], "glazed stoneware", 34, "ceramic",
        dishwasher=True, oven=500, warranty=12, origin="Portugal", desc="Fluted rim for a neat crust.", weight=2.9,
        dims="11 x 11 x 2"),
    fam(CW, "Pro Clad", "Stainless Roasting Pan with Rack", [("", 0, 0)], "tri-ply stainless steel", 149, "tri-ply",
        induction=True, dishwasher=True, oven=500, warranty=120, origin="Portugal",
        desc="Holds a 20 lb turkey. Works on the hob for making gravy.", weight=7.9, dims="19 x 14 x 3.5",
        separately=True),
    fam(CW, "Everyday", "Nonstick Wok 12\"", [("", 0, 0)], "hard-anodised aluminium, PFOA-free nonstick", 59,
        "nonstick", induction=False, dishwasher=True, oven=400, warranty=24, colors=COLORS["nonstick"],
        desc="Flat-bottomed nonstick wok for stir-fries on electric and gas hobs. Not for induction.", weight=3.1,
        dims="20.5 x 12.4 x 3.8"),
    fam(CW, "Heirloom", "Pre-Seasoned Cast Iron Dutch Oven 5 Qt", [("", 0, 0)], "cast iron", 79, "cast iron",
        induction=True, dishwasher=False, oven=650, warranty=120, origin="USA",
        desc="Bare cast iron with a lid that doubles as a skillet.", weight=14.8, dims="12.4 x 10.5 x 6", heavy={"": 15}),
    fam(CW, "Heirloom", "Cast Iron Pizza Pan 14\"", [("", 0, 0)], "cast iron", 49, "cast iron", induction=True,
        dishwasher=False, oven=650, warranty=120, origin="USA", desc="Crisps the base like a pizza stone but won't crack.",
        weight=8.0, dims="16 x 14 x 0.8"),
    fam(CW, "Pro Clad", "Stainless Steamer Insert", [("for 3 Qt", 0, 0), ("for 4 Qt", 4, 0.1)], "18/10 stainless steel",
        29, "tri-ply", dishwasher=True, oven=500, warranty=24, origin="Portugal",
        desc="Fits the Pro Clad saucepans of the same size. Lid not included.", weight=0.9, dims="varies by size"),
    fam(CW, "Pro Clad", "Splatter Screen 13\"", [("", 0, 0)], "stainless steel mesh", 19, "tool", dishwasher=True,
        warranty=12, desc="Fine mesh lets steam out and keeps oil in. Fits pans up to 13 in.", weight=0.5, dims="21 x 13 x 1"),
    fam(CW, "Bakehouse", "Ceramic Pizza Stone 15\"", [("", 0, 0)], "cordierite", 44, "tool hand", dishwasher=False,
        oven=900, warranty=12, desc="Preheat in the oven for 45 minutes. Never wash with soap.", weight=9.2,
        dims="15 x 15 x 0.6", separately=True),
    fam(CW, "Bakehouse", "Wire Cooling Racks (Set of 2)", [("", 0, 0)], "stainless steel", 24, "tool", dishwasher=True,
        oven=575, warranty=12, desc="Grid racks that fit inside a half sheet pan.", weight=2.0, dims="16.5 x 11.5 x 0.8"),
    # ---------------------------------------------------------------- small appliances
    fam(SA, "Countertop", "Wide-Slot 4-Slice Toaster", [("", 0, 0)], "stainless steel", 79, "appliance", warranty=12,
        volts="120 V", colors=COLORS["appliance"][:2] + [COLORS["appliance"][4]],
        desc="Two independent pairs of extra-wide slots, each with its own browning dial.", weight=5.5,
        dims="11.8 x 11.4 x 7.6"),
    fam(SA, "Countertop", "Toaster Oven Air Fry 0.6 cu ft", [("", 0, 0)], "stainless steel", 169, "appliance",
        warranty=24, volts="120 V", desc="Toasts six slices, bakes a 12\" pizza and air fries.", weight=17.6,
        dims="18.5 x 15.7 x 11.2", separately=True),
    fam(SA, "Countertop", "Air Fryer 6 Qt with Window", [("", 0, 0)], "steel with nonstick basket", 159, "appliance",
        warranty=12, volts="120 V", dishwasher=True, desc="A bigger basket with a viewing window, for family-size batches.",
        weight=11.5, dims="15.2 x 12.4 x 13"),
    fam(SA, "Countertop", "Stand Mixer 5 Qt", [("", 0, 0)], "die-cast zinc body, stainless bowl", 349, "appliance",
        warranty=24, volts="120 V", colors=COLORS["appliance"], desc="Tilt head, 10 speeds, dough hook, flat beater and whisk.",
        weight=22.5, dims="14.1 x 8.7 x 13.9", heavy={"": 10}, separately=True),
    fam(SA, "Countertop", "Food Processor", [("8-Cup", 0, 0), ("11-Cup", 40, 2.5)], "BPA-free bowl, stainless blades",
        119, "appliance", warranty=24, volts="120 V", dishwasher=True,
        desc="Slicing and shredding discs plus an S-blade. Bowl and blades are dishwasher safe.", weight=9.0,
        dims="varies by size"),
    fam(SA, "Countertop", "Immersion Blender with Whisk", [("", 0, 0)], "stainless shaft", 59, "appliance",
        warranty=12, volts="120 V", desc="Purees soup in the pot. Detachable shaft is dishwasher safe.", weight=2.1,
        dims="15 x 2.6 x 2.6"),
    fam(SA, "Countertop", "Countertop Blender 1.5L 1200W", [("", 0, 0)], "Tritan jar, stainless blades", 149,
        "appliance", colors=COLORS["appliance"][:3], warranty=24, volts="120 V", dishwasher=True, desc="Crushes ice and blends frozen fruit smooth.",
        weight=9.8, dims="8.5 x 7.8 x 17.5"),
    fam(SA, "Countertop", "Slow Cooker 6 Qt", [("", 0, 0)], "stoneware insert, steel housing", 69, "appliance",
        colors=COLORS["appliance"][:3], warranty=12, volts="120 V", desc="Programmable, with keep-warm and a locking lid for travel.", weight=12.1,
        dims="16.5 x 11.2 x 10.8"),
    fam(SA, "Countertop", "Electric Pressure Multicooker 6 Qt", [("", 0, 0)], "stainless inner pot", 119, "appliance",
        warranty=12, volts="120 V", desc="Pressure cooks, slow cooks, steams and makes yogurt.", weight=11.8,
        dims="13.4 x 12.2 x 12.5"),
    fam(SA, "Countertop", "Belgian Waffle Maker", [("", 0, 0)], "nonstick plates", 59, "appliance", colors=COLORS["appliance"][:3], warranty=12,
        volts="120 V", desc="Deep pockets and a beep when it's done.", weight=4.6, dims="12 x 9.5 x 4"),
    fam(SA, "Countertop", "Electric Griddle 20\"", [("", 0, 0)], "cast aluminium, nonstick", 64, "appliance",
        warranty=12, volts="120 V", desc="Cooks eight pancakes at once. Removable drip tray.", weight=7.3,
        dims="21.5 x 11.8 x 3"),
    fam(SA, "Countertop", "Sous Vide Precision Cooker", [("", 0, 0)], "stainless steel, polycarbonate", 129,
        "appliance", warranty=24, volts="120 V", desc="Clips to any pot and holds water to within 0.2F.", weight=2.4,
        dims="13.5 x 2.9 x 2.9", origin="Vietnam"),
    fam(SA, "Countertop", "Ice Cream Maker 1.5 Qt", [("", 0, 0)], "aluminium freezer bowl", 79, "appliance",
        warranty=12, volts="120 V", desc="Freeze the bowl overnight, then churn in 25 minutes.", weight=6.6,
        dims="9.2 x 8.3 x 11.2"),
    fam(SA, "Countertop", "Slow Juicer", [("", 0, 0)], "Tritan and stainless", 199, "appliance", warranty=24,
        volts="120 V", desc="Presses at 60 rpm for more juice and less foam.", weight=10.4, dims="9.5 x 7 x 17"),
    fam(SA, "Countertop", "Rice Cooker 10-Cup", [("", 0, 0)], "aluminium inner pot, nonstick", 129, "appliance",
        warranty=12, volts="120 V", desc="The big sister of our 6-cup cooker, with a GABA brown rice setting.",
        weight=9.1, dims="14 x 10.8 x 9.5"),
    fam(SA, "Countertop", "Egg Cooker", [("", 0, 0)], "BPA-free plastic, stainless tray", 25, "appliance",
        warranty=12, volts="120 V", desc="Cooks up to seven eggs soft, medium or hard.", weight=1.4, dims="7.6 x 6.7 x 6.2"),
    # ---------------------------------------------------------------- knives & prep
    fam(KP, "Forged", "Santoku Knife 7\"", [("", 0, 0)], "high-carbon stainless steel", 79, "knife", dishwasher=False,
        warranty=120, origin="Germany", desc="Granton edge keeps slices from sticking to the blade.", weight=0.5,
        dims="12 x 1.8 x 0.8"),
    fam(KP, "Forged", "Utility Knife 6\"", [("", 0, 0)], "high-carbon stainless steel", 49, "knife", dishwasher=False,
        warranty=120, origin="Germany", desc="Between a chef's knife and a paring knife, for sandwiches and shallots.",
        weight=0.3, dims="10.5 x 1.2 x 0.7"),
    fam(KP, "Forged", "Boning Knife 6\"", [("", 0, 0)], "high-carbon stainless steel", 59, "knife", dishwasher=False,
        warranty=120, origin="Germany", desc="Flexible blade for trimming and breaking down chicken.", weight=0.3,
        dims="11 x 1 x 0.7"),
    fam(KP, "Forged", "Nakiri Knife 6.5\"", [("", 0, 0)], "VG-10 stainless steel", 119, "knife", dishwasher=False,
        warranty=120, origin="Japan", desc="Flat edge for push-cutting vegetables.", weight=0.4, dims="11.5 x 2 x 0.7"),
    fam(KP, "Forged", "Chinese Cleaver 7\"", [("", 0, 0)], "high-carbon stainless steel", 69, "knife",
        dishwasher=False, warranty=120, origin="Germany", desc="A vegetable cleaver for slicing and scooping, not for bone.",
        weight=0.7, dims="12 x 3.3 x 0.8"),
    fam(KP, "Forged", "Steak Knives (Set of 4)", [("", 0, 0)], "high-carbon stainless steel", 79, "knife",
        dishwasher=False, warranty=120, origin="Germany", desc="Fine serrations that don't tear meat.", weight=1.1,
        dims="9.5 x 1 x 0.6"),
    fam(KP, "Forged", "Knife Block Set (7-Piece)", [("", 0, 0)], "high-carbon stainless steel, acacia block", 299,
        "knife", dishwasher=False, warranty=120, origin="Germany",
        desc="Chef's, bread, santoku, utility and paring knives, honing steel and shears in an acacia block.",
        weight=6.4, dims="14 x 5.5 x 9.8", separately=True),
    fam(KP, "Forged", "Honing Steel 10\"", [("", 0, 0)], "chromium-plated steel", 29, "knife", dishwasher=False,
        warranty=120, origin="Germany", desc="Straightens the edge between sharpenings.", weight=0.6, dims="15 x 1.3 x 1"),
    fam(KP, "Prep", "Take-Apart Kitchen Shears", [("", 0, 0)], "stainless steel", 24, "tool", dishwasher=True,
        warranty=24, desc="Blades separate for cleaning. Notched for bones and nuts.", weight=0.3, dims="8.5 x 3.3 x 0.6"),
    fam(KP, "Prep", "Magnetic Knife Strip", [('16"', 0, 0), ('24"', 10, 0.5)], "walnut and neodymium magnets", 39,
        "wood", dishwasher=False, warranty=12, colors=COLORS["wood"][:2], desc="Mounts with two screws; holds up to 8 knives.",
        weight=1.0, dims="varies by size"),
    fam(KP, "Prep", "End-Grain Maple Cutting Board", [("Medium", 0, 0), ("Large", 40, 4.0)], "hard maple", 89, "wood",
        dishwasher=False, warranty=12, origin="USA", desc="End grain closes up after each cut and is kind to edges.",
        weight=7.5, dims="varies by size"),
    fam(KP, "Prep", "Plastic Cutting Boards (Set of 3)", [("", 0, 0)], "polypropylene", 29, "plastic",
        dishwasher=True, warranty=12, desc="Color-coded for meat, fish and vegetables. Non-slip corners.", weight=2.6,
        dims="15 x 11 x 0.4"),
    fam(KP, "Prep", "Box Grater", [("", 0, 0)], "stainless steel", 24, "tool", dishwasher=True, warranty=12,
        desc="Four sides: coarse, fine, slicing and zesting.", weight=0.8, dims="4.5 x 3.5 x 9.5"),
    fam(KP, "Prep", "Rasp Zester", [("", 0, 0)], "stainless steel", 16, "tool", dishwasher=True, warranty=12,
        desc="For citrus zest, hard cheese, ginger and nutmeg.", weight=0.2, dims="12.5 x 1.3 x 1"),
    fam(KP, "Prep", "Y-Peeler (Set of 2)", [("", 0, 0)], "stainless steel blade, ABS handle", 12, "tool",
        dishwasher=True, warranty=12, desc="One straight blade, one serrated for tomatoes and peaches.", weight=0.2,
        dims="6 x 2.6 x 0.6"),
    fam(KP, "Prep", "Salad Spinner 5 Qt", [("", 0, 0)], "BPA-free plastic", 34, "plastic", dishwasher=True,
        warranty=12, desc="One-hand pump and a brake. The bowl doubles as a serving bowl.", weight=2.2, dims="10.5 x 10.5 x 6.5"),
    fam(KP, "Prep", "Stainless Mixing Bowls (Set of 5)", [("", 0, 0)], "stainless steel", 45, "tool",
        dishwasher=True, warranty=12, desc="Nesting bowls from 1 to 8 qt with non-slip bases and lids.", weight=4.1,
        dims="12.5 x 12.5 x 5"),
    fam(KP, "Prep", "Measuring Cups and Spoons Set", [("", 0, 0)], "stainless steel", 29, "tool", dishwasher=True,
        warranty=12, desc="Engraved markings that won't wear off. Includes odd sizes like 2/3 cup.", weight=1.0,
        dims="6 x 4 x 3"),
    fam(KP, "Prep", "Silicone Spatula Set (3-Piece)", [("", 0, 0)], "silicone over steel core", 22, "silicone",
        dishwasher=True, warranty=12, colors=COLORS["silicone"], desc="Heat safe to 600F; safe on nonstick.", weight=0.5,
        dims="11 x 2.5 x 0.8"),
    fam(KP, "Prep", "Olivewood Spoon Set (3-Piece)", [("", 0, 0)], "olive wood", 32, "wood", dishwasher=False,
        warranty=12, origin="Italy", desc="Hand-finished spoons, each with its own grain.", weight=0.6, dims="12 x 2.5 x 1"),
    fam(KP, "Prep", "Locking Tongs (Set of 2)", [("", 0, 0)], "stainless steel with silicone tips", 18, "tool",
        dishwasher=True, warranty=12, desc="9\" and 12\" tongs that lock closed for storage.", weight=0.6,
        dims="12 x 1.8 x 1.5"),
    fam(KP, "Prep", "Instant-Read Thermometer", [("", 0, 0)], "ABS body, stainless probe", 29, "tool hand",
        dishwasher=False, warranty=12, desc="Reads in 2 seconds. Takes one AAA battery (included).", weight=0.2,
        dims="6.3 x 1.4 x 0.7"),
    fam(KP, "Prep", "Digital Kitchen Scale", [("", 0, 0)], "tempered glass platform", 25, "tool hand",
        dishwasher=False, warranty=12, desc="Weighs to 11 lb in 1 g steps, with tare.", weight=1.1, dims="8.5 x 6.5 x 0.8"),
    fam(KP, "Prep", "Garlic Press", [("", 0, 0)], "stainless steel", 19, "tool", dishwasher=True, warranty=24,
        desc="Presses unpeeled cloves; the basket swings out to clean.", weight=0.5, dims="7.3 x 2 x 1.3"),
    fam(KP, "Prep", "Stainless Colander 5 Qt", [("", 0, 0)], "stainless steel", 29, "tool", dishwasher=True,
        warranty=12, desc="Micro-perforated so rice and quinoa don't slip through.", weight=1.3, dims="13.5 x 11 x 5"),
    fam(KP, "Prep", "French Rolling Pin 20\"", [("", 0, 0)], "maple", 22, "wood", dishwasher=False, warranty=12,
        origin="USA", desc="Tapered ends for rolling pastry into rounds.", weight=0.9, dims="20 x 1.8 x 1.8"),
    fam(KP, "Prep", "Bench Scraper", [("", 0, 0)], "stainless steel, beech handle", 14, "tool hand", dishwasher=False,
        warranty=12, desc="Marked in inches for cutting dough; also scoops chopped vegetables.", weight=0.4, dims="6 x 4.5 x 1"),
    fam(KP, "Prep", "Balloon Whisks (Set of 3)", [("", 0, 0)], "stainless steel", 19, "tool", dishwasher=True,
        warranty=12, desc="8, 10 and 12 inch whisks with sealed handles.", weight=0.6, dims="12 x 2.8 x 2.8"),
    fam(KP, "Prep", "Knife Edge Guards (Set of 4)", [("", 0, 0)], "felt-lined ABS", 16, "tool hand", dishwasher=False,
        warranty=12, desc="Protect edges in a drawer. Fit blades from 3.5 to 9 in.", weight=0.3, dims="various"),
    fam(KP, "Forged", "Engraved Chef's Knife 8\"", [("", 0, 0)], "high-carbon stainless steel", 104, "knife",
        dishwasher=False, warranty=120, origin="Germany",
        desc="Our 8 in chef's knife with up to 20 characters engraved on the blade. Engraved items are final sale.",
        weight=0.5, dims="13 x 2 x 0.8"),
    # ---------------------------------------------------------------- storage
    fam(ST, "Keep", "Glass Food Storage Set (18-Piece)", [("", 0, 0)], "borosilicate glass, BPA-free lids", 64,
        "glass", dishwasher=True, oven=450, warranty=12, desc="Nine containers from 1 to 8 cups with snap-lock lids.",
        weight=9.4, dims="12 x 9 x 7.5"),
    fam(ST, "Keep", "Glass Meal Prep Containers (Set of 5)", [("", 0, 0)], "borosilicate glass, BPA-free lids", 34,
        "glass", dishwasher=True, oven=450, warranty=12, desc="Two-compartment containers for lunches.", weight=5.2,
        dims="8.5 x 6.3 x 2.6"),
    fam(ST, "Keep", "Airtight Pantry Canisters", [("Set of 5", 20, 1.0), ("Tall 3.2 Qt", -18, -0.8)], "BPA-free plastic",
        38, "plastic", dishwasher=True, warranty=12, desc="One-press lids that seal airtight. Stack and match our Set of 3.",
        weight=2.4, dims="varies by size"),
    fam(ST, "Keep", "Produce Keepers (Set of 3)", [("", 0, 0)], "BPA-free plastic", 29, "plastic", dishwasher=True,
        warranty=12, desc="Adjustable vents and a raised tray keep berries and greens fresh longer.", weight=2.0,
        dims="10 x 7 x 4.5"),
    fam(ST, "Keep", "Stainless Bento Lunch Box", [("", 0, 0)], "stainless steel, silicone seal", 32, "steel",
        dishwasher=True, warranty=12, desc="Three compartments and a leak-proof lid.", weight=0.9, dims="8 x 5.5 x 2.4"),
    fam(ST, "Keep", "Beeswax Food Wraps (Set of 4)", [("", 0, 0)], "organic cotton, beeswax", 16, "tool hand",
        dishwasher=False, warranty=12, origin="USA", desc="Wrap cheese, bread and half a lemon. Rinse in cool water.",
        weight=0.2, dims="various"),
    fam(ST, "Keep", "Bamboo Bread Box", [("", 0, 0)], "bamboo, acrylic window", 49, "wood", dishwasher=False,
        warranty=12, desc="Roll-top lid. The lid doubles as a cutting board.", weight=4.4, dims="15.5 x 9.8 x 7.4"),
    fam(ST, "Keep", "Expandable Spice Rack", [("", 0, 0)], "bamboo", 29, "wood", dishwasher=False, warranty=12,
        desc="Three tiers that extend from 13 to 22 inches, sized for our spice jars.", weight=1.8, dims="13 x 10 x 3.8"),
    fam(ST, "Keep", "Bamboo Drawer Organizer", [("", 0, 0)], "bamboo", 34, "wood", dishwasher=False, warranty=12,
        desc="Expands from 13 to 21 inches with seven compartments.", weight=2.9, dims="17 x 13.4 x 2.2"),
    fam(ST, "Keep", "Turntable Organizer 10\"", [("", 0, 0)], "BPA-free plastic", 16, "plastic", dishwasher=True,
        warranty=12, desc="Lazy Susan for the fridge or a corner cabinet.", weight=0.8, dims="10 x 10 x 1.6"),
    fam(ST, "Keep", "Glass Oil Sprayer", [("", 0, 0)], "glass, stainless pump", 18, "glass", dishwasher=True,
        warranty=12, desc="A fine mist from a pump, with no propellant.", weight=0.4, dims="2 x 2 x 7.5"),
    fam(ST, "Keep", "Silicone Freezer Trays (Set of 2)", [("", 0, 0)], "food-grade silicone", 24, "silicone",
        dishwasher=True, warranty=12, colors=COLORS["silicone"][:2], desc="Freeze soup and stock in 1-cup portions.",
        weight=1.1, dims="11.5 x 7.5 x 2.3"),
    fam(ST, "Keep", "Vacuum-Seal Canister Large 2.4 Qt", [("", 0, 0)], "stainless steel", 44, "steel",
        dishwasher=False, warranty=12, desc="The larger size of our vacuum canister, for flour and beans.", weight=1.4,
        dims="5.5 x 5.5 x 9.2"),
    # ---------------------------------------------------------------- coffee gear
    fam(CG, "Brew", "Electric Gooseneck Kettle 0.9L", [("", 0, 0)], "stainless steel", 89, "appliance",
        warranty=24, volts="120 V", colors=COLORS["appliance"][:3],
        desc="Set the temperature to the degree and hold it for 60 minutes.", weight=2.6, dims="11.5 x 6.3 x 7.9"),
    fam(CG, "Brew", "12-Cup Drip Coffee Maker", [("", 0, 0)], "stainless steel, glass carafe", 99, "appliance",
        colors=COLORS["appliance"][:3], warranty=24, volts="120 V", desc="Brews at 200F with a bloom cycle. Programmable.", weight=7.3, dims="13.9 x 8.3 x 14.8"),
    fam(CG, "Brew", "Cold Brew Maker 1.5 Qt", [("", 0, 0)], "borosilicate glass, stainless filter", 34, "coffee",
        dishwasher=True, warranty=12, desc="Steep overnight in the fridge. Makes a week of concentrate.", weight=2.0,
        dims="5 x 5 x 11"),
    fam(CG, "Brew", "Stainless Stovetop Espresso Maker", [("3-Cup", 0, 0), ("6-Cup", 10, 0.4)], "18/10 stainless steel",
        44, "coffee", induction=True, dishwasher=False, warranty=24, origin="Italy",
        desc="Italian-made moka pot in stainless steel, so it works on induction.", weight=1.4, dims="varies by size"),
    fam(CG, "Brew", "Aluminium Moka Pot", [("3-Cup", 0, 0), ("6-Cup", 8, 0.3)], "cast aluminium", 29, "coffee",
        induction=False, dishwasher=False, warranty=12, origin="Italy",
        desc="The classic octagonal moka pot. Not for induction.", weight=1.0, dims="varies by size"),
    fam(CG, "Espresso", "Espresso Tamper 58mm", [("", 0, 0)], "stainless steel, walnut handle", 29, "tool hand",
        dishwasher=False, warranty=12, desc="Fits our Compact Espresso Machine basket.", weight=1.0, dims="58 mm base"),
    fam(CG, "Espresso", "Espresso Knock Box", [("", 0, 0)], "ABS, silicone bar", 24, "tool", dishwasher=True,
        warranty=12, desc="Knock out spent pucks without scratching the portafilter.", weight=1.2, dims="5.9 x 4.7 x 4.3"),
    fam(CG, "Espresso", "Milk Frothing Pitcher 12 oz", [("", 0, 0)], "stainless steel", 19, "tool", dishwasher=True,
        warranty=12, desc="Sharp spout for latte art.", weight=0.4, dims="3.5 x 3 x 4"),
    fam(CG, "Espresso", "Espresso Cups with Saucers (Set of 4)", [("", 0, 0)], "porcelain", 29, "ceramic",
        dishwasher=True, warranty=12, origin="Portugal", desc="3 oz cups with thick walls that hold heat.", weight=2.1,
        dims="3 oz each"),
    fam(CG, "Brew", "Hand Burr Grinder", [("", 0, 0)], "stainless steel burrs, aluminium body", 69, "coffee",
        dishwasher=False, warranty=24, desc="Grinds 20 g in about 40 seconds; 30 click settings.", weight=1.3,
        dims="7.5 x 2 x 2"),
    fam(CG, "Brew", "Insulated Travel Mug 16 oz", [("", 0, 0)], "double-wall stainless steel", 29, "coffee",
        dishwasher=True, warranty=12, colors=COLORS["silicone"], desc="Leak-proof lid. Hot for 6 hours.", weight=0.8,
        dims="3.5 x 3.5 x 7.3"),
    fam(CG, "Brew", "Stoneware Mugs (Set of 4)", [("", 0, 0)], "glazed stoneware", 39, "ceramic", dishwasher=True,
        warranty=12, origin="Portugal", colors=COLORS["enamel"][:3], desc="14 oz mugs with a reactive glaze; each one differs a little.",
        weight=4.4, dims="14 oz each"),
    fam(CG, "Brew", "Paper Filters for Pour-Over (100 Pack)", [("", 0, 0)], "unbleached paper", 9, "tool hand",
        dishwasher=None, warranty=0, desc="Sized for our Pour-Over Dripper.", weight=0.3, dims="size 02"),
    fam(CG, "Brew", "Glass Tea Infuser Teapot 1L", [("", 0, 0)], "borosilicate glass, stainless infuser", 34,
        "glass", dishwasher=True, warranty=12, desc="Removable infuser for loose-leaf tea.", weight=1.3, dims="7.5 x 5.5 x 6"),
    fam(CG, "Brew", "Matcha Set (Bowl, Whisk, Scoop)", [("", 0, 0)], "ceramic, bamboo", 42, "ceramic",
        dishwasher=False, warranty=12, origin="Japan", desc="Handmade bowl, 100-prong bamboo whisk and scoop.", weight=1.5,
        dims="5 x 5 x 3"),
    fam(CG, "Espresso", "Descaling Solution (2 Pack)", [("", 0, 0)], "citric acid solution", 14, "tool hand",
        dishwasher=None, warranty=0, origin="USA", desc="Two treatments for kettles and espresso machines.", weight=1.1,
        dims="8 oz bottles"),
]

PREFIX = {SA: 1, CW: 2, KP: 3, ST: 4, CG: 5}


def yn(v):
    return "" if v is None else ("yes" if v else "no")


def base_rows():
    """The 30 products from products.json, in export shape."""
    rows = []
    for p in json.loads((HERE / "products.json").read_text()):
        a = p["attributes"]
        mat = (a["material"] or "").lower()
        rows.append({
            "sku": p["sku"], "name": p["name"], "category": p["category"], "collection": "Original",
            "list_price": f"{p['price']:.2f}", "sale_price": "", "final_sale": "no",
            "variants": [(v["id"], v.get("color") or v.get("size") or "") for v in p["variants"]],
            "capacity": a["capacity"] or "", "dimensions_in": "",
            "weight_lb": f"{p['weight_kg'] * 2.2046:.1f}" if p.get("weight_kg") else "",
            "material": a["material"] or "", "induction_compatible": yn(a["induction_compatible"]),
            "dishwasher_safe": yn(a["dishwasher_safe"]), "oven_safe_to_f": "",
            "warranty_months": a["warranty_months"], "voltage": "120 V" if a["wattage"] and a["wattage"] > 5 else "",
            "heavy_item_surcharge_usd": f"{p['shipping_surcharge_usd']:.2f}" if p["shipping_surcharge_usd"] else "",
            "ships_separately": "no", "stock": p["inventory"], "restock_date": p.get("restock_date", ""),
            "country_of_origin": "", "bundle_skus": " ".join(p["bundle_skus"]),
            "description": p["description"] + "".join(f" Known issue {k['id']}: {k['summary']}" for k in p["known_issues"]),
            "care": CARE["appliance"] if p["category"] == SA else "",
        })
    return rows


def generated_rows(start):
    rows, counters = [], dict(start)
    for f in FAMILIES:
        for size, dprice, dweight in f["sizes"]:
            n = PREFIX[f["category"]]
            counters[n] += 1
            sku = f"KT-{n}{counters[n]:03d}"
            name = f"{f['base']} {size}".strip()
            price = f["price"] + dprice
            weight = max(0.1, f["weight"] + dweight)
            colors = f["colors"] or []
            if colors:
                colors = random.sample(colors, k=random.randint(max(2, len(colors) - 1), len(colors)))
            roll = random.random()
            final_sale = roll < 0.07
            on_sale = final_sale or roll < 0.22
            sale = round(price * random.choice([0.7, 0.75, 0.8, 0.85, 0.9])) - 0.01 if on_sale else None
            stock = 0 if random.random() < 0.08 else random.randint(4, 260)
            restock = (date(2026, 9, 23) + timedelta(days=random.randint(10, 75))).isoformat() if stock == 0 else ""
            heavy = f["heavy"].get(size, 0)
            rows.append({
                "sku": sku, "name": name, "category": f["category"], "collection": f["collection"],
                "list_price": f"{price:.2f}", "sale_price": f"{sale:.2f}" if sale else "",
                "final_sale": "yes" if final_sale else "no",
                "variants": [(f"{sku}-{code}", label) for code, label in colors],
                "capacity": size, "dimensions_in": f["dims"], "weight_lb": f"{weight:.1f}",
                "material": f["material"], "induction_compatible": yn(f["induction"]),
                "dishwasher_safe": yn(f["dishwasher"]), "oven_safe_to_f": f["oven"] or "",
                "warranty_months": f["warranty"], "voltage": f["volts"] or "",
                "heavy_item_surcharge_usd": f"{heavy:.2f}" if heavy else "",
                "ships_separately": "yes" if f["separately"] or heavy else "no",
                "stock": stock, "restock_date": restock, "country_of_origin": f["origin"], "bundle_skus": "",
                "description": f["desc"] + (" Clearance: final sale." if final_sale else ""),
                "care": CARE[f["care"]],
            })
    return rows


def upc(variant_id):
    """Deterministic fake 12-digit UPC with a valid check digit (prefix 0 81234 is not a real company)."""
    body = f"081234{abs(hash_str(variant_id)) % 10**5:05d}"
    odd = sum(int(d) for d in body[0::2]) * 3 + sum(int(d) for d in body[1::2])
    return body + str((10 - odd % 10) % 10)


def hash_str(s):
    h = 0
    for ch in s:
        h = (h * 131 + ord(ch)) % 2**31
    return h


def by_variant(products):
    """Expand to one row per variant. Stock is split across variants; the restock date stays product-level."""
    out = []
    for p in products:
        variants = p.pop("variants") or [(p["sku"], "")]
        stock = p.pop("stock")
        shares = [random.random() + 0.2 for _ in variants]
        split = [int(stock * s / sum(shares)) for s in shares]
        split[0] += stock - sum(split)
        for (vid, color), qty in zip(variants, split):
            out.append({"variant_id": vid, **p, "color": color, "upc": upc(vid), "variant_stock": qty})
    return out


base = base_rows()
start = {n: max(int(r["sku"][4:]) for r in base if r["sku"][3] == str(n)) % 1000 for n in PREFIX.values()}
products = base + generated_rows(start)
rows = by_variant(products)
path = HERE / "catalog-export.csv"
with path.open("w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=COLUMNS)
    w.writeheader()
    w.writerows(rows)
print(f"wrote {path.relative_to(HERE.parent)}: {len(products)} products, {len(rows)} variant rows")
