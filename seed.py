"""
seed.py — Bulk insert Flowerworld products into the database.
Run once with: python seed.py
"""

from app import app, db, Product

PRODUCTS = [
    # ---------- WREATHS ----------
    ("Autumn Eucalyptus Wreath",    68.00, "w-1.png"),
    ("Golden Wheat Wreath",         58.00, "w-2.png"),
    ("Dried Lavender Wreath",       72.00, "w-3.png"),
    ("Wild Grass Wreath",           54.00, "w-4.png"),
    ("Rustic Berry Wreath",         76.00, "w-5.png"),
    ("Olive Branch Wreath",         82.00, "w-6.png"),
    ("Rosemary Wreath",             62.00, "w-7.png"),
    ("Dried Rose Wreath",           88.00, "w-8.png"),
    ("Pine and Cedar Wreath",       74.00, "w-9.png"),
    ("Cotton Boll Wreath",          66.00, "w-10.png"),
    ("Dried Hydrangea Wreath",      94.00, "w-11.png"),
    ("Wheat and Rye Wreath",        56.00, "w-12.png"),
    ("Herb Garden Wreath",          64.00, "w-13.png"),
    ("Dried Orange Wreath",         70.00, "w-14.png"),
    ("Pampas Grass Wreath",         78.00, "w-15.png"),
    ("Bittersweet Wreath",          80.00, "w-16.png"),
    ("Seeded Eucalyptus Wreath",    68.00, "w-17.png"),
    ("Dried Thistle Wreath",        72.00, "w-18.png"),
    ("Honeycomb Wreath",            60.00, "w-19.png"),
    ("Wildflower Meadow Wreath",    84.00, "w-20.png"),
    ("Dried Magnolia Wreath",       96.00, "w-21.png"),
    ("Bay Leaf Wreath",             58.00, "w-22.png"),
    ("Dried Fern Wreath",           64.00, "w-23.png"),
    ("Autumn Leaf Wreath",          70.00, "w-24.png"),

    # ---------- DRIED BUNCHES ----------
    ("Dried Eucalyptus Bunch",      24.00, "b-1.png"),
    ("Dried Lavender Bundle",       18.00, "b-2.png"),
    ("Pampas Grass Stems",          32.00, "b-3.png"),
    ("Dried Wheat Bunch",           16.00, "b-4.png"),
    ("Dried Ruscus Bunch",          22.00,"b-5.png"),
    ("Dried Rose Stems",            38.00, "b-6.png"),
    ("Lagurus Grass Bundle",        20.00, "b-7.png"),
    ("Dried Hydrangea Bunch",       42.00, "b-8.png"),


    # ---------- FOR THE HOME ----------
    ("Dried Flower Wall Hanging",       88.00, "h-1.png"),
    ("Botanical Ceramic Vase",          64.00, "h-2.png"),
    ("Dried Flower Frame",              72.00, "h-3.png"),
    ("Hanging Herb Bundle",             34.00, "h-4.png"),
    ("Dried Wreath Hanger",             28.00, "h-5.png"),
    ("Dried Flower Shadow Box",         78.00, "h-6.png"),
    ("Botanical Candle",                42.00, "h-7.png"),
    ("Dried Flower Garland",            56.00, "h-8.png"),
    ("Woven Grass Basket",              58.00, "h-9.png"),

    # ---------- SEASONAL ----------
    ("Autumn Harvest Arrangement",      86.00, "s-1.png"),
    ("Thanksgiving Centerpiece",        112.00, "s-2.png"),
    ("Halloween Dried Bundle",          42.00, "s-3.png"),
    ("Fall Equinox Wreath",             76.00, "s-4.png"),
    ("Winter Solstice Bundle",          58.00, "s-5.png"),
    ("Spring Awakening Bunch",          48.00, "s-6.png"),
    ("Summer Meadow Arrangement",       72.00, "s-7.png"),
    ("Autumn Leaf Garland",             64.00, "s-8.png"),
    ("Winter Evergreen Bundle",         52.00, "s-9.png"),
]


def seed():
    with app.app_context():
        # Delete existing products (so re-running doesn't duplicate)
        Product.query.delete()
        db.session.commit()
        print("Cleared old products.")

        # Insert new
        for name, price, image in PRODUCTS:
            if image.startswith("w-"):
                category = "wreaths"
            elif image.startswith("b-"):
                category = "bunches"
            elif image.startswith("h-"):
                category = "home"
            else:
                category = "seasonal"

            # Full image path including subfolder
            image_path = f"{category}/{image}"

            p = Product(
                name=name,
                price=price,
                image=image_path,
                category=category,
                stock=10,
                description=f"{name} — hand-arranged in our studio using seasonal dried botanicals.",
            )
            db.session.add(p)

        db.session.commit()
        print(f"Inserted {len(PRODUCTS)} products.")


if __name__ == "__main__":
    seed()