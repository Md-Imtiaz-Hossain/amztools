"""
Module 2: Analyze & Prepare Data - Demo / Simulation Catalog Fixtures
=====================================================================
Purpose:
    Provides realistic, deterministic mock catalog fixtures and brand/category
    mappings used in Demo / Simulation Mode. Allows full offline testing and
    evaluation of the wholesale analysis pipeline without requiring active
    Amazon SP-API credentials.
"""

# Realistic brands used for deterministic simulation of unlisted demo barcodes
DEMO_BRANDS = [
    "La Mer",
    "Bobbi Brown",
    "rom&nd",
    "Helena Rubinstein",
    "FENTY BEAUTY",
    "MAC",
    "Algenist",
    "Anker",
    "Sony",
    "Logitech",
]

# Category and sub-category pairs for simulated demo products
DEMO_CATEGORIES_MAP = [
    ("Arts, Crafts & Sewing", ["Paint Pens & Markers", "Drawing Sets", "Craft Kits", "Scrapbooking"]),
    ("Beauty & Personal Care", ["Facial Care", "Lip Gloss", "Eyeshadow", "Skin Serums"]),
    ("Electronics", ["Headphones & Earbuds", "Bluetooth Speakers", "Cables & Adapters", "Computer Accessories"]),
    ("Cell Phones & Accessories", ["Power Banks", "Phone Cases", "Wireless Chargers", "Screen Protectors"]),
    ("Video Games", ["Console Accessories", "Gaming Mice", "Controllers", "Virtual Reality"]),
    ("Home & Kitchen", ["Kitchen Utensils", "Storage & Organization", "Coffee Makers", "Tableware"]),
]

# Static realistic demo catalog derived from target wholesale data for instant offline testing
KNOWN_DEMO_PRODUCTS = {
    # Electronics demo items
    "019425205698": {
        "asin": "B0BDHWDR12",
        "parent_asin": "",
        "brand": "Apple",
        "title": "Apple AirPods Pro (2nd Generation) Wireless Earbuds with MagSafe Case",
        "pkg_qty": 1,
        "category": "Electronics",
        "sales_rank": 45,
        "est_sales": 18500,
        "cost": 175.00,
        "buybox": 249.00,
        "lowest_fba": 249.00,
        "lowest_fbm": 254.99,
        "total_offers": 18,
        "new_fba_offers": 12,
        "new_fbm_offers": 6,
        "buybox_contention": 4,
        "dims": "1.78 x 2.39 x 0.85",
        "weight": 0.35,
        "manufacturer": "Apple",
        "color": "White",
        "model": "MTJV3AM/A",
        "part_num": "MQD83AM/A",
        "hazmat": "False",
        "brand_restriction": "True",
        "selling_restriction": "approval required",
        "about_this_item": (
            "• UP TO 2X MORE ACTIVE NOISE CANCELLATION: Advanced algorithms cancel unwanted noise.\n"
            "• PERSONALIZED SPATIAL AUDIO: Sound tailored to your unique ear shape for immersive listening.\n"
            "• TOUCH CONTROL: Adjust volume with a swipe, answer calls, and switch listening modes.\n"
            "• EXTENDED BATTERY LIFE: Up to 6 hours listening time with ANC enabled, 30 hours with case.\n"
            "• MAGSAFE CHARGING CASE: Features built-in speaker, lanyard loop, and precision finding."
        ),
        "customer_reviews": "4.7 out of 5 stars (Reviews: 12,480)",
        "image_links": [
            "https://m.media-amazon.com/images/I/61SUj2aKoEL.jpg",
            "https://m.media-amazon.com/images/I/61sRKTA7o-L.jpg",
            "https://m.media-amazon.com/images/I/51b9LU1nSGL.jpg",
            "https://m.media-amazon.com/images/I/61NbxT-L8gL.jpg",
            "https://m.media-amazon.com/images/I/61eDX9kHk1L.jpg",
        ],
    },
    "088727638786": {
        "asin": "B09N3ZNHTY",
        "parent_asin": "",
        "brand": "Samsung",
        "title": 'Samsung Galaxy Tab A8 10.5" 32GB Android Tablet, Dark Gray',
        "pkg_qty": 1,
        "category": "Computers & Accessories",
        "sales_rank": 820,
        "est_sales": 4200,
        "cost": 115.00,
        "buybox": 179.99,
        "lowest_fba": 179.99,
        "lowest_fbm": 182.50,
        "total_offers": 14,
        "new_fba_offers": 8,
        "new_fbm_offers": 6,
        "buybox_contention": 3,
        "dims": "9.72 x 6.37 x 0.27",
        "weight": 1.12,
        "manufacturer": "Samsung",
        "color": "Dark Gray",
        "model": "SM-X200NZAAXAR",
        "part_num": "SM-X200NZAAXAR",
        "hazmat": "True",
        "brand_restriction": "False",
        "selling_restriction": "not eligible",
        "about_this_item": (
            "• A SCREEN EVERYONE WILL LOVE: 10.5-inch LCD screen delivers brilliant clarity.\n"
            "• POWER AND STORAGE FOR ALL: Fast Unisoc Tiger T618 processor with 32GB expandable storage.\n"
            "• LONG-LASTING BATTERY: 7,040 mAh battery keeps you going with fast charging support.\n"
            "• QUAD SPEAKERS: Dolby Atmos surround sound creates a theater-like acoustic experience.\n"
            "• SAMSUNG KIDS ECOSYSTEM: Safe library of educational games, books, and videos."
        ),
        "customer_reviews": "4.5 out of 5 stars (Reviews: 8,350)",
        "image_links": [
            "https://m.media-amazon.com/images/I/61vGykNn-kL.jpg",
            "https://m.media-amazon.com/images/I/61gR7m7m4TL.jpg",
            "https://m.media-amazon.com/images/I/61b1bYq8VBL.jpg",
            "https://m.media-amazon.com/images/I/71u9j6W+vYL.jpg",
            "https://m.media-amazon.com/images/I/61qH5q3l78L.jpg",
        ],
    },
    "073185502444": {
        "asin": "B09HM94VDS",
        "parent_asin": "",
        "brand": "Logitech",
        "title": "Logitech MX Master 3S Wireless Performance Mouse, Quiet Clicks, 8K DPI",
        "pkg_qty": 1,
        "category": "Electronics",
        "sales_rank": 310,
        "est_sales": 7400,
        "cost": 62.00,
        "buybox": 99.99,
        "lowest_fba": 99.99,
        "lowest_fbm": 104.99,
        "total_offers": 22,
        "new_fba_offers": 15,
        "new_fbm_offers": 7,
        "buybox_contention": 6,
        "dims": "4.92 x 3.31 x 2.01",
        "weight": 0.31,
        "manufacturer": "Logitech",
        "color": "Graphite",
        "model": "910-006556",
        "part_num": "910-006556",
        "hazmat": "False",
        "brand_restriction": "False",
        "selling_restriction": "approval required",
        "about_this_item": (
            "• 8K ANY-SURFACE TRACKING: Next-gen 8,000 DPI optical sensor tracks even on glass.\n"
            "• QUIET CLICKS: 90% less click noise while maintaining satisfying tactile feedback.\n"
            "• MAGSPEED SCROLLING: Scroll 1,000 lines in a second with electromagnetic precision.\n"
            "• ERGONOMIC COMFORT: Sculpted silhouette crafted for all-day palm and wrist support.\n"
            "• MULTI-DEVICE FLOW: Seamlessly work across up to 3 computers with Logitech Options+."
        ),
        "customer_reviews": "4.7 out of 5 stars (Reviews: 6,120)",
        "image_links": [
            "https://m.media-amazon.com/images/I/61ni3t1ryQL.jpg",
            "https://m.media-amazon.com/images/I/61O7VfW-KdL.jpg",
            "https://m.media-amazon.com/images/I/61pB5jWJ3tL.jpg",
            "https://m.media-amazon.com/images/I/61Z2Z2u-UUL.jpg",
            "https://m.media-amazon.com/images/I/61t-X3f6sBL.jpg",
        ],
    },
    "084008058862": {
        "asin": "B09VPHVT2Z",
        "parent_asin": "",
        "brand": "Anker",
        "title": "Anker 737 Power Bank (PowerCore 24K), 24,000mAh 3-Port Portable Charger 140W",
        "pkg_qty": 1,
        "category": "Cell Phones & Accessories",
        "sales_rank": 1420,
        "est_sales": 2900,
        "cost": 92.00,
        "buybox": 149.99,
        "lowest_fba": 149.99,
        "lowest_fbm": 152.00,
        "total_offers": 9,
        "new_fba_offers": 5,
        "new_fbm_offers": 4,
        "buybox_contention": 2,
        "dims": "6.13 x 2.15 x 1.95",
        "weight": 1.40,
        "manufacturer": "Anker",
        "color": "Black",
        "model": "A1289",
        "part_num": "A1289011",
        "hazmat": "True",
        "brand_restriction": "False",
        "selling_restriction": "approval required",
        "about_this_item": (
            "• ULTRA-POWERFUL TWO-WAY CHARGING: Delivers up to 140W fast charge and recharges at 140W.\n"
            "• SMART DIGITAL DISPLAY: Easy-to-read screen shows output and input power, plus recharge time.\n"
            "• HUGE 24,000MAH CAPACITY: Juice up an iPhone 13 almost 5 times or a 2021 MacBook Pro.\n"
            "• POWER DELIVERY 3.1: Equipped with the latest PD 3.1 bidirectional fast charging technology.\n"
            "• ACTIVE SHIELD 2.0: Monitors temperature over 3 million times per day for ultimate safety."
        ),
        "customer_reviews": "4.6 out of 5 stars (Reviews: 3,410)",
        "image_links": [
            "https://m.media-amazon.com/images/I/61D8o3qR2DL.jpg",
            "https://m.media-amazon.com/images/I/61L-P3VwSCL.jpg",
            "https://m.media-amazon.com/images/I/61gV4H5b-aL.jpg",
            "https://m.media-amazon.com/images/I/71V2c3p8LWL.jpg",
            "https://m.media-amazon.com/images/I/61k9j1H7MML.jpg",
        ],
    },
    # Real Wholesale Beauty products from Target_Data_and_format.xlsx
    "3605521489654": {
        "asin": "B009QZ5YME",
        "parent_asin": "",
        "brand": "Helena Rubinstein",
        "title": "Helena Rubinstein Prodigy Re-Plasty Age Recovery Skin Regeneration Accelerating Night Care 50ml/1.75oz",
        "pkg_qty": 1,
        "category": "Beauty & Personal Care",
        "sales_rank": 564351,
        "est_sales": 5,
        "cost": 236.00,
        "buybox": None,
        "lowest_fba": None,
        "lowest_fbm": None,
        "total_offers": 0,
        "new_fba_offers": 0,
        "new_fbm_offers": 0,
        "buybox_contention": 0,
        "dims": "3.86 x 3.78 x 3.7",
        "weight": 0.88,
        "manufacturer": "Helena Rubinstein",
        "color": "Red",
        "model": "3605521489654",
        "part_num": "RBN00092",
        "hazmat": "False",
        "brand_restriction": "False",
        "selling_restriction": "approval required",
        "about_this_item": (
            "• POST-PROCEDURE HEALING: Inspired by cosmetic surgery clinic post-intervention care.\n"
            "• PRO-XYLANE 30%: Highly concentrated active ingredient promotes deep epidermic renewal.\n"
            "• BANDAGE TEXTURE: Transforms on contact to create an invisible protective film over skin.\n"
            "• VISIBLE SIGNS OF AGING: Accelerates recovery of wrinkles, skin roughness, and sagging.\n"
            "• LUXURY OVERNIGHT CARE: Awakens the complexion with firm, replenished elasticity."
        ),
        "customer_reviews": "4.5 out of 5 stars (Reviews: 68)",
        "image_links": [
            "https://m.media-amazon.com/images/I/61Q6U+e7NRL.jpg",
            "https://m.media-amazon.com/images/I/51p1Zk-OqEL.jpg",
            "https://m.media-amazon.com/images/I/61k1j2l9YpL.jpg",
            "https://m.media-amazon.com/images/I/71u9y6f7aPL.jpg",
            "https://m.media-amazon.com/images/I/61w6x7e8zCL.jpg",
        ],
    },
    "747930013549": {
        "asin": "B00BH4KLJI",
        "parent_asin": "B0DHY97X8S",
        "brand": "La Mer",
        "title": "La Mer Moisturizing Cream 3.4 Ounce",
        "pkg_qty": 1,
        "category": "Beauty & Personal Care",
        "sales_rank": 359742,
        "est_sales": 5,
        "cost": 260.00,
        "buybox": None,
        "lowest_fba": None,
        "lowest_fbm": 455.39,
        "total_offers": 1,
        "new_fba_offers": 0,
        "new_fbm_offers": 1,
        "buybox_contention": 0,
        "dims": "4.17 x 3.9 x 3.7",
        "weight": 1.15,
        "manufacturer": "La Mer",
        "color": "Cranberry",
        "model": "747930013549",
        "part_num": "U-SC-3229",
        "hazmat": "False",
        "brand_restriction": "False",
        "selling_restriction": "not eligible",
        "about_this_item": (
            "• ICONIC CRÈME DE LA MER: Ultra-rich moisturizing cream that delivers deep soothing moisture.\n"
            "• CELL-RENEWING MIRACLE BROTH: Fermented giant sea kelp infuses skin with vital energy.\n"
            "• RESTORES RADIANCE: Helps eliminate dryness, redness, and irritation for a supple glow.\n"
            "• FIRMS & SMOOTHS: Clinically proven to minimize the appearance of fine lines and pores.\n"
            "• WARM TO ACTIVATE: Warm between fingers until translucent, then press gently into skin."
        ),
        "customer_reviews": "4.6 out of 5 stars (Reviews: 890)",
        "image_links": [
            "https://m.media-amazon.com/images/I/51+u7D7G1rL.jpg",
            "https://m.media-amazon.com/images/I/61y+J2y7LpL.jpg",
            "https://m.media-amazon.com/images/I/51x9Z6g8WPL.jpg",
            "https://m.media-amazon.com/images/I/61t9o1p6yRL.jpg",
            "https://m.media-amazon.com/images/I/51w9e7r6tQL.jpg",
        ],
    },
    "819002011460": {
        "asin": "B00PSAJZX0",
        "parent_asin": "",
        "brand": "Algenist",
        "title": "Algenist GENIUS Ultimate Anti-Aging Eye Cream - Brightening & Firming Eye Cream with Vegan Collagen & Alguronic Acid - Helps Reduce Dark Circles, Puffiness & Fine Lines (0.5 fl oz)",
        "pkg_qty": 1,
        "category": "Beauty & Personal Care",
        "sales_rank": 135706,
        "est_sales": 55,
        "cost": 43.00,
        "buybox": 47.59,
        "lowest_fba": 47.59,
        "lowest_fbm": None,
        "total_offers": 3,
        "new_fba_offers": 3,
        "new_fbm_offers": 0,
        "buybox_contention": 1,
        "dims": "2.36 x 2.24 x 1.97",
        "weight": 0.20,
        "manufacturer": "Algenist",
        "color": "Green",
        "model": "819002011460",
        "part_num": "GENIUS-01",
        "hazmat": "False",
        "brand_restriction": "True",
        "selling_restriction": "approval required",
        "about_this_item": (
            "• PATENETED ALGUORONIC ACID: Naturally sourced from algae to visibly reduce fine lines.\n"
            "• VEGAN COLLAGEN: Plant-derived collagen complex visibly restores firmness and bounce.\n"
            "• COMBATS DARK CIRCLES: Peptides and caffeine invigorate the fragile eye contour area.\n"
            "• DEEP HYDRATION: Nutrient-rich microalgae oil provides intensive barrier replenishment.\n"
            "• OPHTHALMOLOGIST TESTED: Safe for contact lens wearers and sensitive skin."
        ),
        "customer_reviews": "4.4 out of 5 stars (Reviews: 420)",
        "image_links": [
            "https://m.media-amazon.com/images/I/61d7V7y7ZtL.jpg",
            "https://m.media-amazon.com/images/I/61e8R3e4WsL.jpg",
            "https://m.media-amazon.com/images/I/71o9u8i7aZL.jpg",
            "https://m.media-amazon.com/images/I/61q8x9y7wPL.jpg",
            "https://m.media-amazon.com/images/I/61w9t8y7uRL.jpg",
        ],
    },
    "8809625241285": {
        "asin": "B07SL2NXGT",
        "parent_asin": "B0892B1MZX",
        "brand": "rom&nd",
        "title": "rom&nd Better Than Eyes 4-Color Eyeshadow Palette #01 Dry Mango Tulip",
        "pkg_qty": 1,
        "category": "Beauty & Personal Care",
        "sales_rank": 15774,
        "est_sales": 1138,
        "cost": 11.00,
        "buybox": 17.98,
        "lowest_fba": 17.98,
        "lowest_fbm": None,
        "total_offers": 6,
        "new_fba_offers": 6,
        "new_fbm_offers": 0,
        "buybox_contention": 3,
        "dims": "2.72 x 2.56 x 0.67",
        "weight": 0.11,
        "manufacturer": "rom&nd",
        "color": "#01 Dry Mango Tulip",
        "model": "RMD-BTE-01",
        "part_num": "RMD-BTE-01",
        "hazmat": "False",
        "brand_restriction": "False",
        "selling_restriction": "approval required",
        "about_this_item": (
            "• 4-PAN COLOR HARMONY: Carefully calibrated shades designed for seamless blending.\n"
            "• ULTRA-FINE PARTICLES: Silky powder blurs fine lines and glides evenly onto eyelids.\n"
            "• OPAL GLITTER: Translucent glitter pigment adds a romantic shimmering highlight.\n"
            "• LONG-WEARING FORMULA: Sebum-control powder prevents creasing throughout the day.\n"
            "• COMPACT POCKET SIZE: Convenient travel-friendly palette for quick on-the-go touch-ups."
        ),
        "customer_reviews": "4.5 out of 5 stars (Reviews: 1,150)",
        "image_links": [
            "https://m.media-amazon.com/images/I/61k9j2h8gFL.jpg",
            "https://m.media-amazon.com/images/I/61o9i8u7yTL.jpg",
            "https://m.media-amazon.com/images/I/71p9o8i7uSL.jpg",
            "https://m.media-amazon.com/images/I/61u9y8t7rOL.jpg",
            "https://m.media-amazon.com/images/I/61t8y7u6wPL.jpg",
        ],
    },
    "8809625241834": {
        "asin": "B087BHZQQV",
        "parent_asin": "B087BLR4K2",
        "brand": "rom&nd",
        "title": "rom&nd Glasting Water Tint #04 Vintage Ocean (4g)",
        "pkg_qty": 1,
        "category": "Beauty & Personal Care",
        "sales_rank": 7225,
        "est_sales": 2603,
        "cost": 9.00,
        "buybox": 8.97,
        "lowest_fba": 8.97,
        "lowest_fbm": None,
        "total_offers": 8,
        "new_fba_offers": 7,
        "new_fbm_offers": 1,
        "buybox_contention": 4,
        "dims": "4.02 x 0.79 x 0.75",
        "weight": 0.04,
        "manufacturer": "rom&nd",
        "color": "#04 Vintage Ocean",
        "model": "RMD-GWT-04",
        "part_num": "RMD-GWT-04",
        "hazmat": "False",
        "brand_restriction": "False",
        "selling_restriction": "approval required",
        "about_this_item": (
            "• WATER FILM GLOSS: Transparent water-like coating enhances lips with glass shine.\n"
            "• NON-STICKY TEXTURE: Lightweight absorption leaves zero tacky residue.\n"
            "• VIVID LONG-LASTING STAIN: Color pigments adhere firmly to lips under the gloss layer.\n"
            "• MOISTURE LOCK: Infused with botanical oils to keep lips soft and hydrated.\n"
            "• BUILDABLE COVERAGE: Apply one sheer coat or layer for deeper vintage ocean tint."
        ),
        "customer_reviews": "4.4 out of 5 stars (Reviews: 2,340)",
        "image_links": [
            "https://m.media-amazon.com/images/I/61o9p8i7uTL.jpg",
            "https://m.media-amazon.com/images/I/61i8u7y6tRL.jpg",
            "https://m.media-amazon.com/images/I/71u9y8t7rPL.jpg",
            "https://m.media-amazon.com/images/I/61y8t7r6eWL.jpg",
            "https://m.media-amazon.com/images/I/61t8r6e5wQL.jpg",
        ],
    },
    "004549659042": {
        "asin": "B098RKWHHZ",
        "parent_asin": "",
        "brand": "Nintendo",
        "title": "Nintendo Switch – OLED Model w/ White Joy-Con",
        "pkg_qty": 1,
        "category": "Video Games",
        "sales_rank": 85,
        "est_sales": 15400,
        "cost": 230.00,
        "buybox": 349.99,
        "lowest_fba": 349.99,
        "lowest_fbm": 354.00,
        "total_offers": 25,
        "new_fba_offers": 18,
        "new_fbm_offers": 7,
        "buybox_contention": 5,
        "dims": "10.24 x 7.87 x 3.94",
        "weight": 3.25,
        "manufacturer": "Nintendo",
        "color": "White",
        "model": "HEGSKAAAA",
        "part_num": "HEGSKAAAA",
        "hazmat": "True",
        "brand_restriction": "True",
        "selling_restriction": "approval required",
        "about_this_item": (
            "• 7-INCH OLED SCREEN: Vivid colors and crisp contrast bring gaming worlds to life.\n"
            "• WIDE ADJUSTABLE STAND: Angle the system's wide stand for comfortable viewing in Tabletop mode.\n"
            "• WIRED LAN PORT: Use the dock's LAN port when playing in TV mode for stable online play.\n"
            "• 64 GB INTERNAL STORAGE: Save games to your system with 64 GB of internal storage.\n"
            "• ENHANCED AUDIO: Enjoy clear audio from the system's onboard speakers in Handheld mode."
        ),
        "customer_reviews": "4.8 out of 5 stars (Reviews: 24,190)",
        "image_links": [
            "https://m.media-amazon.com/images/I/61-PblYntsL.jpg",
            "https://m.media-amazon.com/images/I/71R2c3p8LWL.jpg",
            "https://m.media-amazon.com/images/I/61j1l9u8aPL.jpg",
            "https://m.media-amazon.com/images/I/71o9u8y7tPL.jpg",
            "https://m.media-amazon.com/images/I/61qH5q3l78L.jpg",
        ],
    },
    "002724291515": {
        "asin": "B0863TXGM3",
        "parent_asin": "",
        "brand": "Sony",
        "title": "Sony WH-1000XM4 Wireless Premium Noise Canceling Overhead Headphones, Black",
        "pkg_qty": 1,
        "category": "Electronics",
        "sales_rank": 110,
        "est_sales": 12800,
        "cost": 210.00,
        "buybox": 348.00,
        "lowest_fba": 348.00,
        "lowest_fbm": 349.95,
        "total_offers": 31,
        "new_fba_offers": 20,
        "new_fbm_offers": 11,
        "buybox_contention": 4,
        "dims": "7.27 x 3.03 x 9.94",
        "weight": 1.60,
        "manufacturer": "Sony",
        "color": "Black",
        "model": "WH1000XM4/B",
        "part_num": "WH1000XM4/B",
        "hazmat": "True",
        "brand_restriction": "True",
        "selling_restriction": "approval required",
        "about_this_item": (
            "• INDUSTRY LEADING NOISE CANCELING: Dual Noise Sensor technology delivers premium isolation.\n"
            "• NEXT-LEVEL MUSIC: Edge-AI co-developed with Sony Music Studios Tokyo for premium audio.\n"
            "• UP TO 30-HOUR BATTERY: Fast charging (10 min charge for 5 hours playback).\n"
            "• TOUCH SENSOR CONTROLS: Pause, play, skip tracks, control volume, activate voice assistant.\n"
            "• SPEAK-TO-CHAT TECHNOLOGY: Automatically reduces volume during conversations."
        ),
        "customer_reviews": "4.7 out of 5 stars (Reviews: 48,200)",
        "image_links": [
            "https://m.media-amazon.com/images/I/71o8Q5XJS5L.jpg",
            "https://m.media-amazon.com/images/I/71k1j2l9YpL.jpg",
            "https://m.media-amazon.com/images/I/71u9j6W+vYL.jpg",
            "https://m.media-amazon.com/images/I/61b1bYq8VBL.jpg",
            "https://m.media-amazon.com/images/I/61qH5q3l78L.jpg",
        ],
    },
    "081001430030": {
        "asin": "B07XJ8C8F5",
        "parent_asin": "",
        "brand": "Amazon",
        "title": "Echo Dot (4th Gen) | Smart speaker with Alexa | Charcoal",
        "pkg_qty": 1,
        "category": "Electronics",
        "sales_rank": 65,
        "est_sales": 22000,
        "cost": 25.00,
        "buybox": 49.99,
        "lowest_fba": 49.99,
        "lowest_fbm": 52.00,
        "total_offers": 16,
        "new_fba_offers": 12,
        "new_fbm_offers": 4,
        "buybox_contention": 2,
        "dims": "3.9 x 3.9 x 3.5",
        "weight": 0.75,
        "manufacturer": "Amazon",
        "color": "Charcoal",
        "model": "B7W644",
        "part_num": "B7W644",
        "hazmat": "False",
        "brand_restriction": "False",
        "selling_restriction": "approval required",
        "about_this_item": (
            "• MEET ECHO DOT: Our most popular smart speaker with Alexa. The sleek, compact design fits anywhere.\n"
            "• CRISP VOCALS & BALANCED BASS: Delivers clear vocals and balanced bass for full sound you can enjoy anywhere.\n"
            "• VOICE CONTROL YOUR ENTERTAINMENT: Stream songs from Amazon Music, Apple Music, Spotify, and more.\n"
            "• READY TO HELP: Ask Alexa to tell a joke, play music, answer questions, and check the weather.\n"
            "• CONTROL YOUR SMART HOME: Use your voice to turn on lights, adjust thermostats, and lock doors."
        ),
        "customer_reviews": "4.7 out of 5 stars (Reviews: 95,400)",
        "image_links": [
            "https://m.media-amazon.com/images/I/714Rq4k05UL.jpg",
            "https://m.media-amazon.com/images/I/71u9y6f7aPL.jpg",
            "https://m.media-amazon.com/images/I/61sRKTA7o-L.jpg",
            "https://m.media-amazon.com/images/I/61NbxT-L8gL.jpg",
            "https://m.media-amazon.com/images/I/61SUj2aKoEL.jpg",
        ],
    },
    "B004N84AHY": {
        "asin": "B004N84AHY",
        "parent_asin": "",
        "brand": "Uni-ball",
        "title": "Uni-posca Paint Marker Pen - Medium Point - Set of 8 (PC-5M 8C)",
        "pkg_qty": 1,
        "category": "Arts, Crafts & Sewing",
        "sales_rank": 24385,
        "sub_category": "Paint Pens & Markers",
        "sub_category_sales_rank": 390,
        "est_sales": 135,
        "cost": 11.20,
        "buybox": 19.98,
        "lowest_fba": 19.98,
        "lowest_fbm": 21.50,
        "total_offers": 8,
        "new_fba_offers": 4,
        "new_fbm_offers": 4,
        "buybox_contention": 3,
        "dims": "5.6 x 3.8 x 1.2",
        "weight": 0.45,
        "manufacturer": "Mitsubishi Pencil Co.",
        "color": "Assorted",
        "model": "PC-5M 8C",
        "part_num": "PC-5M 8C",
        "hazmat": "False",
        "brand_restriction": "False",
        "selling_restriction": "approval required",
        "about_this_item": (
            "• WATER-BASED PIGMENT INK: Vibrant opaque colors produce vivid lines on paper, metal, glass, and wood.\n"
            "• MEDIUM BULLET TIP: 1.8mm - 2.5mm line width provides exceptional control for coloring and outlining.\n"
            "• BLEED-RESISTANT FORMULA: Does not bleed through paper and layers without smudging once dry.\n"
            "• LIGHTFAST & WATERPROOF: Long-lasting permanence for arts, crafts, illustration, and signing.\n"
            "• 8 VIBRANT COLORS: Includes Black, White, Red, Yellow, Blue, Light Blue, Green, and Pink."
        ),
        "customer_reviews": "4.6 out of 5 stars (Reviews: 187)",
        "image_links": [
            "https://m.media-amazon.com/images/I/71N-E4d-EaL.jpg",
            "https://m.media-amazon.com/images/I/81xG-Yx-MGL.jpg",
            "https://m.media-amazon.com/images/I/71DkL-eZgZL.jpg",
            "https://m.media-amazon.com/images/I/71iZ-w0NqAL.jpg",
            "https://m.media-amazon.com/images/I/81P-G9k2zOL.jpg",
        ],
    },
}

__all__ = ["DEMO_BRANDS", "DEMO_CATEGORIES_MAP", "KNOWN_DEMO_PRODUCTS"]
