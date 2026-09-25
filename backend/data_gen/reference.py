"""Ma'lumotnomalar: hududlar, sohalar, xavf tasnifi.

geo_key — geoBoundaries UZB ADM1 qatlamidagi ISO 3166-2 kodi (shapeISO).
"""

# (id, to'liq nom, qisqa nom, ISO kodi, subyektlar ulushi — sintetik taqsimot)
REGIONS: list[tuple[str, str, str, str, float]] = [
    ("QR", "Qoraqalpog‘iston Respublikasi", "Qoraqalpog‘iston", "UZ-QR", 0.055),
    ("AN", "Andijon viloyati", "Andijon", "UZ-AN", 0.085),
    ("BU", "Buxoro viloyati", "Buxoro", "UZ-BU", 0.060),
    ("JI", "Jizzax viloyati", "Jizzax", "UZ-JI", 0.040),
    ("QA", "Qashqadaryo viloyati", "Qashqadaryo", "UZ-QA", 0.085),
    ("NW", "Navoiy viloyati", "Navoiy", "UZ-NW", 0.035),
    ("NG", "Namangan viloyati", "Namangan", "UZ-NG", 0.080),
    ("SA", "Samarqand viloyati", "Samarqand", "UZ-SA", 0.100),
    ("SU", "Surxondaryo viloyati", "Surxondaryo", "UZ-SU", 0.070),
    ("SI", "Sirdaryo viloyati", "Sirdaryo", "UZ-SI", 0.030),
    ("TO", "Toshkent viloyati", "Toshkent vil.", "UZ-TO", 0.080),
    ("FA", "Farg‘ona viloyati", "Farg‘ona", "UZ-FA", 0.095),
    ("XO", "Xorazm viloyati", "Xorazm", "UZ-XO", 0.050),
    ("TK", "Toshkent shahri", "Toshkent sh.", "UZ-TK", 0.135),
]

# (id, nom, ikon, ulush, bazaviy oylik aylanma mln so'm, mavsumiylik amplitudasi,
#  eng yuqori oy (1–12), o'rtacha chek ming so'm)
SECTORS: list[tuple[str, str, str, float, float, float, int, float]] = [
    ("SAV", "Savdo", "shopping-cart", 0.22, 260.0, 0.18, 12, 180.0),
    ("XIZ", "Xizmatlar", "briefcase", 0.14, 140.0, 0.08, 3, 220.0),
    ("QUR", "Qurilish", "hard-hat", 0.10, 420.0, 0.30, 7, 2400.0),
    ("QXJ", "Qishloq xo‘jaligi", "wheat", 0.10, 190.0, 0.45, 10, 900.0),
    ("TRL", "Transport va logistika", "truck", 0.08, 230.0, 0.12, 11, 650.0),
    ("SAN", "Sanoat", "factory", 0.08, 520.0, 0.10, 11, 3200.0),
    ("OVQ", "Umumiy ovqatlanish", "utensils", 0.08, 95.0, 0.22, 7, 85.0),
    ("ITA", "IT va aloqa", "cpu", 0.06, 160.0, 0.06, 12, 540.0),
    ("TAL", "Ta’lim", "graduation-cap", 0.05, 70.0, 0.35, 9, 350.0),
    ("SOG", "Sog‘liqni saqlash", "stethoscope", 0.05, 110.0, 0.07, 1, 260.0),
    ("BOS", "Boshqa", "layers", 0.04, 90.0, 0.10, 6, 300.0),
]

SIZE_GROUPS = [("small", 0.70, 1.0), ("medium", 0.25, 5.5), ("large", 0.05, 32.0)]

RISK_TYPES: list[tuple[str, str, str, str]] = [
    ("R01", "Faoliyat dinamikasi", "trending-down", "Subyektning iqtisodiy ko‘rsatkichlarida keskin o‘zgarish."),
    ("R02", "Sohaviy og‘ish", "git-compare", "Subyekt o‘z sohasidagi o‘xshash subyektlardan keskin farq qiladi."),
    ("R03", "Hududiy og‘ish", "map-pin", "Subyekt hududiy iqtisodiy qonuniyatlarga nisbatan g‘ayrioddiy holatda."),
    ("R04", "Operatsion noodatiylik", "activity", "Operatsiyalar soni, hajmi yoki davriyligida g‘ayrioddiylik."),
    ("R05", "Aloqadorlik xavfi", "share-2", "Xavfi yuqori subyektlar bilan g‘ayrioddiy bog‘liqlik."),
    ("R06", "Ma’lumotlar ziddiyati", "file-warning", "Turli manbalardagi ma’lumotlar o‘zaro mos kelmaydi."),
    ("R07", "Davriy xavf", "calendar-clock", "Vaqt qatorlarida mavsumiy qonuniyatdan sezilarli og‘ish."),
    ("R08", "Kompleks xavf", "layers", "Bir nechta xavf signalining bir vaqtda kuzatilishi."),
]

RELATION_TYPES = {
    "supplier": "Yetkazib beruvchi",
    "buyer": "Xaridor",
    "founder": "Umumiy muassis",
    "director": "Umumiy rahbar",
    "address": "Umumiy manzil",
}

DATA_SOURCES = [
    # code, name, type, status, description, last_error
    ("synthetic_demo_transactions_v1", "Tranzaksiyalar oqimi (sintetik)", "api", "active",
     "Oylik aylanma, operatsiyalar soni va o‘rtacha chek.", None),
    ("synthetic_demo_registry_v1", "Subyektlar reyestri (sintetik)", "db", "active",
     "Ro‘yxatdan o‘tish ma’lumotlari va reyestrdagi aylanma.", None),
    ("synthetic_demo_tax_v1", "Soliq ko‘rsatkichlari (sintetik)", "file", "delayed",
     "Soliq yuklamasi indeksi. Oxirgi yuklash rejadan kechikkan.", None),
    ("synthetic_demo_relations_v1", "Aloqadorliklar reyestri (sintetik)", "api", "active",
     "Muassislar, rahbarlar, manzillar va shartnoma aloqalari.", None),
    ("synthetic_demo_customs_v1", "Tashqi savdo ma’lumotlari (sintetik)", "api", "error",
     "Eksport va import operatsiyalari.", "Manba javob bermadi: ulanish vaqti tugadi (namoyish holati)."),
]

DEMO_USERS = [
    # username, password, full name, role, region
    ("admin", "Admin123!", "Namoyish administratori", "admin", None),
    ("tahlilchi", "Tahlil123!", "Tahlilchi (Namangan)", "analyst", "NG"),
    ("tahlilchi2", "Tahlil123!", "Tahlilchi (Toshkent sh.)", "analyst", "TK"),
    ("rahbar", "Rahbar123!", "Bo‘lim rahbari", "manager", None),
    ("auditor", "Audit123!", "Ichki auditor", "auditor", None),
]

GOLDEN_SUBJECT = "SUB-000125"
