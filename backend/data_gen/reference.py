"""Ma'lumotnomalar: hududlar, sohalar, xavf tasnifi.

geo_key — geoBoundaries UZB ADM1 qatlamidagi ISO 3166-2 kodi (shapeISO).

Sintetik tanlanma rasmiy AGREGAT statistikaga moslashtirilgan (manbalar CALIBRATION da).
Subyektlar, STIR va ko'rsatkichlar baribir sun'iy: real korxona ma'lumoti ishlatilmaydi.
"""

import math

# --- Rasmiy agregatlar (Milliy statistika qo'mitasi) ----------------------------------------

# Faoliyat ko'rsatayotgan korxonalar soni, 2026-yil 1-aprel holatiga (jami 577,2 ming).
REGION_ENTERPRISES = {
    "TK": 109_781, "TO": 54_542, "SA": 53_457, "FA": 49_303, "QA": 44_221, "AN": 35_524, "BU": 35_098,
    "NG": 33_796, "XO": 32_512, "SU": 32_030, "QR": 29_471, "JI": 26_741, "NW": 24_208, "SI": 16_522,
}

# Yalpi hududiy mahsulot 2025-yil, mlrd so'm. Jizzax bo'yicha ochiq manbada qiymat topilmadi.
REGION_GRP_BLN = {
    "QR": 54_076.9, "AN": 107_717.6, "BU": 86_608.1, "JI": None, "QA": 98_783.4, "NW": 167_964.6,
    "NG": 85_400.0, "SA": 121_489.5, "SU": 66_186.5, "SI": 35_794.4, "TO": 180_177.4, "FA": 111_305.3,
    "XO": 62_987.5, "TK": 367_222.3,
}

# Iqtisodiy faoliyat turlari bo'yicha korxonalar soni, 2026-yil 1-avgust holatiga (jami 601,3 ming).
# "Boshqa tarmoqlar" (125 940) rasmiy manbada ajratilmagan: Xizmatlar va Boshqa o'rtasida teng bo'lindi.
SECTOR_ENTERPRISES = {
    "SAV": 164_481, "QXJ": 131_925, "SAN": 63_861, "OVQ": 33_966, "QUR": 33_163, "TRL": 18_894,
    "SOG": 15_341, "ITA": 13_705, "XIZ": 62_970, "BOS": 62_970,
}

# 2025-yil hajmlari, mlrd so'm: sanoat mahsuloti, qurilish ishlari, chakana savdo aylanmasi,
# qishloq, o'rmon va baliq xo'jaligi mahsuloti, bozor xizmatlari.
VOLUME_2025_BLN = {"industry": 1_101_100.0, "construction": 313_900.0, "retail": 482_400.0,
                   "agriculture": 538_900.0, "services": 1_050_300.0}
SECTOR_VOLUME = {"SAN": "industry", "QUR": "construction", "SAV": "retail", "QXJ": "agriculture",
                 "OVQ": "services", "TRL": "services", "SOG": "services", "ITA": "services",
                 "XIZ": "services", "BOS": "services"}


def sector_mean_monthly_mln(sector_id: str) -> float:
    """Bitta korxonaga to'g'ri keladigan o'rtacha oylik aylanma, mln so'm: yillik hajm / korxonalar soni / 12.

    Bozor xizmatlari hajmi xizmat ko'rsatuvchi barcha sohalar o'rtasida korxonalar soniga teng taqsimlanadi
    (sohalar kesimidagi xizmatlar hajmi ochiq manbada topilmadi).
    """
    vol = SECTOR_VOLUME[sector_id]
    count = sum(c for s, c in SECTOR_ENTERPRISES.items() if SECTOR_VOLUME[s] == vol)
    return VOLUME_2025_BLN[vol] * 1000 / count / 12


def region_level(region_id: str) -> float:
    """Hududiy daraja: korxona boshiga YaHM mamlakat o'rtachasiga nisbati, ildiz bilan yumshatilgan.

    Ildiz Navoiy kabi yirik tog'-kon korxonalari bor hududlarda barcha kichik subyektlar
    aylanmasini sun'iy oshirib yubormaslik uchun olinadi. Ma'lumoti yo'q hudud: 1,0.
    """
    known = {r: g for r, g in REGION_GRP_BLN.items() if g is not None}
    national = sum(known.values()) / sum(REGION_ENTERPRISES[r] for r in known)
    grp = REGION_GRP_BLN.get(region_id)
    if grp is None:
        return 1.0
    return math.sqrt((grp / REGION_ENTERPRISES[region_id]) / national)


_REGION_TOTAL = sum(REGION_ENTERPRISES.values())
_SECTOR_TOTAL = sum(SECTOR_ENTERPRISES.values())

# (id, to'liq nom, qisqa nom, ISO kodi, subyektlar ulushi — rasmiy korxonalar soni bo'yicha)
REGIONS: list[tuple[str, str, str, str, float]] = [
    (rid, name, short, iso, REGION_ENTERPRISES[rid] / _REGION_TOTAL)
    for rid, name, short, iso in [
        ("QR", "Qoraqalpog‘iston Respublikasi", "Qoraqalpog‘iston", "UZ-QR"),
        ("AN", "Andijon viloyati", "Andijon", "UZ-AN"),
        ("BU", "Buxoro viloyati", "Buxoro", "UZ-BU"),
        ("JI", "Jizzax viloyati", "Jizzax", "UZ-JI"),
        ("QA", "Qashqadaryo viloyati", "Qashqadaryo", "UZ-QA"),
        ("NW", "Navoiy viloyati", "Navoiy", "UZ-NW"),
        ("NG", "Namangan viloyati", "Namangan", "UZ-NG"),
        ("SA", "Samarqand viloyati", "Samarqand", "UZ-SA"),
        ("SU", "Surxondaryo viloyati", "Surxondaryo", "UZ-SU"),
        ("SI", "Sirdaryo viloyati", "Sirdaryo", "UZ-SI"),
        ("TO", "Toshkent viloyati", "Toshkent vil.", "UZ-TO"),
        ("FA", "Farg‘ona viloyati", "Farg‘ona", "UZ-FA"),
        ("XO", "Xorazm viloyati", "Xorazm", "UZ-XO"),
        ("TK", "Toshkent shahri", "Toshkent sh.", "UZ-TK"),
    ]
]

# (id, nom, ikon, ulush, o'rtacha oylik aylanma mln so'm (rasmiy hajm / soni), mavsumiylik amplitudasi,
#  eng yuqori oy (1–12), o'rtacha chek ming so'm). Mavsumiylik va chek — sintetik parametrlar.
SECTORS: list[tuple[str, str, str, float, float, float, int, float]] = [
    (sid, name, icon, SECTOR_ENTERPRISES[sid] / _SECTOR_TOTAL, sector_mean_monthly_mln(sid), amp, peak, check)
    for sid, name, icon, amp, peak, check in [
        ("SAV", "Savdo", "shopping-cart", 0.18, 12, 180.0),
        ("QXJ", "Qishloq xo‘jaligi", "wheat", 0.45, 10, 900.0),
        ("SAN", "Sanoat", "factory", 0.10, 11, 3200.0),
        ("XIZ", "Xizmatlar", "briefcase", 0.08, 3, 220.0),
        ("BOS", "Boshqa", "layers", 0.10, 6, 300.0),
        ("OVQ", "Yashash va ovqatlanish", "utensils", 0.22, 7, 85.0),
        ("QUR", "Qurilish", "hard-hat", 0.30, 7, 2400.0),
        ("TRL", "Transport va saqlash", "truck", 0.12, 11, 650.0),
        ("SOG", "Sog‘liqni saqlash", "stethoscope", 0.07, 1, 260.0),
        ("ITA", "Axborot va aloqa", "cpu", 0.06, 12, 540.0),
    ]
]

# Kichik korxona va mikrofirmalar ulushi rasmiy: 84,9% (2025-yil 1-avgust). O'rta va yirik o'rtasidagi
# bo'linish (12% / 3%) va hajm koeffitsientlari — taxmin.
SIZE_GROUPS = [("small", 0.85, 1.0), ("medium", 0.12, 8.0), ("large", 0.03, 60.0)]
TURNOVER_SIGMA = 0.9  # subyektlar orasidagi tarqoqlik (lognormal)


def size_mean_factor() -> float:
    """Tanlanma o'rtachasi = mediana × shu koeffitsient (hajm aralashmasi × lognormal o'rtachasi)."""
    return sum(share * mult for _, share, mult in SIZE_GROUPS) * math.exp(TURNOVER_SIGMA ** 2 / 2)


CALIBRATION = {
    "note": "Sintetik tanlanma rasmiy agregat statistikaga moslashtirilgan. Subyektlar va ularning ko‘rsatkichlari sun’iy.",
    "sources": [
        {"what": "Hududlar bo‘yicha faoliyat ko‘rsatayotgan korxonalar soni", "as_of": "2026-04-01",
         "publisher": "Milliy statistika qo‘mitasi (yuz.uz orqali)",
         "url": "https://yuz.uz/ru/news/tashkent-lidiruet-po-kolichestvu-deystvuyuix-predpriyatiy-v-uzbekistane---statistika-po-regionam"},
        {"what": "Iqtisodiy faoliyat turlari bo‘yicha korxonalar soni", "as_of": "2026-08-01",
         "publisher": "Milliy statistika qo‘mitasi (yuz.uz orqali)",
         "url": "https://yuz.uz/ru/news/v-kakix-sferax-osuestvlyaet-deyatelnost-naibolshee-kolichestvo-predpriyatiy-v-uzbekistane"},
        {"what": "2025-yil: YaIM 1 849,7 trln, sanoat 1 101,1 trln, qishloq xo‘jaligi 538,9 trln, qurilish 313,9 trln, chakana savdo 482,4 trln, bozor xizmatlari 1 050,3 trln so‘m",
         "as_of": "2025", "publisher": "Milliy statistika qo‘mitasi (gazeta.uz orqali)",
         "url": "https://www.gazeta.uz/ru/2026/01/23/gdp-uzbekistan-2025/"},
        {"what": "Hududlar bo‘yicha yalpi hududiy mahsulot 2025", "as_of": "2025",
         "publisher": "Milliy statistika qo‘mitasi (kun.uz, spot.uz orqali)",
         "url": "https://kun.uz/news/2026/03/13/statistika-iqtisodiyoti-eng-tez-osgan-hududlar-royxati"},
        {"what": "Kichik korxona va mikrofirmalar ulushi 84,9%", "as_of": "2025-08-01",
         "publisher": "Milliy statistika qo‘mitasi", "url": "https://stat.uz"},
    ],
    "assumptions": [
        "“Boshqa tarmoqlar” (125 940) Xizmatlar va Boshqa sohalari o‘rtasida teng bo‘lingan.",
        "Bozor xizmatlari hajmi xizmat sohalari o‘rtasida korxonalar soniga teng taqsimlangan.",
        "Qishloq xo‘jaligi hajmida dehqon xo‘jaliklari hissasi ajratilmagan: o‘rtacha aylanma yuqoriroq chiqadi.",
        "O‘rta va yirik korxonalar ulushi (12% / 3%) va hajm koeffitsientlari taxmin.",
        "Jizzax viloyati bo‘yicha YaHM topilmagan: hududiy koeffitsient 1,0.",
        "Mavsumiylik, o‘rtacha chek va soliq yuklamasi indeksi sintetik parametrlar.",
    ],
}

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
