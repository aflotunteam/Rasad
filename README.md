# RASAD

> **NAMOYISH MA’LUMOTLARI — SINTETIK.** Loyihadagi barcha subyektlar, ko‘rsatkichlar va natijalar sun’iy yaratilgan. Ular rasmiy statistika emas, real korxona, STIR yoki fuqaro ma’lumotlari ishlatilmagan.

RASAD — ko‘p manbali iqtisodiy ma’lumotlarni yagona muhitda qayta ishlab, subyekt, hudud va tarmoq kesimida g‘ayrioddiy holatlar hamda xavf signallarini aniqlaydigan, ularni ustuvorlashtiradigan, sabablarini izohlaydigan va ekspert qarorini qo‘llab-quvvatlaydigan intellektual tahlil platformasi.

RASAD aybni aniqlamaydi va yakuniy huquqiy qaror chiqarmaydi. U quyidagi savolga javob beradi: *«Qaysi holat qo‘shimcha ekspert tahlilini birinchi navbatda talab qiladi va nima sababdan?»*

## Tez ishga tushirish (Windows)

Kerak bo‘ladi: Python 3.12+ va Node.js 20+.

```powershell
.\scripts\dev.ps1 -Install -Seed
```

Skript Python va npm paketlarini o‘rnatadi, bazani sintetik ma’lumot bilan to‘ldiradi hamda ikkala serverni ishga tushiradi:

- Veb-ilova: http://localhost:5173
- API hujjatlari (OpenAPI): http://127.0.0.1:8000/docs

Keyingi safar `.\scripts\dev.ps1` buyrug‘ining o‘zi yetarli. `-Seed` bazani boshlang‘ich holatga qaytaradi: demo oldidan shuni ishga tushiring.

**Doimiy rejim.** `.\scripts\install-autostart.ps1` Windows’da "RASAD Server" vazifasini ro‘yxatdan o‘tkazadi. U tizimga kirganda `scripts\serve.ps1` nazoratchisini ishga tushiradi. Nazoratchi API (8000) va veb (5173) jarayonlarini kuzatadi. Jarayon to‘xtasa yoki `/health` 3 marta ketma-ket javob bermasa, uni qayta ishga tushiradi. Loglar `logs\` papkasiga yoziladi. O‘chirish uchun: `.\scripts\install-autostart.ps1 -Remove`.

<details>
<summary>Qo‘lda ishga tushirish</summary>

```bash
cd backend
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt
.venv/Scripts/python -m scripts.seed          # alembic upgrade + sintetik ma'lumot + Risk Engine
.venv/Scripts/python -m uvicorn app.main:app --port 8000

cd ../frontend
npm install
npm run dev                                    # /api so'rovlari 8000-portga proksi qilinadi
```
</details>

## Namoyish hisoblari

| Rol | Login | Parol | Imkoniyatlar |
|---|---|---|---|
| Administrator | `admin` | `Admin123!` | Barcha bo‘limlar, xavf chegaralari, modellar, foydalanuvchilar |
| Tahlilchi | `tahlilchi` | `Tahlil123!` | Faqat Namangan viloyati; ekspert qarori, import |
| Tahlilchi | `tahlilchi2` | `Tahlil123!` | Faqat Toshkent shahri |
| Rahbar | `rahbar` | `Rahbar123!` | Boshqaruv ko‘rsatkichlari va hisobotlar; STIR maskalangan |
| Auditor | `auditor` | `Audit123!` | Audit jurnali; sozlamalarni faqat ko‘rish |

Parollar faqat lokal namoyish uchun. Login sahifasidagi ro‘yxatdan hisobni bosib tanlash mumkin.

## Golden demo oqimi

`admin` bilan kiring:

1. **Bosh sahifa** → O‘zbekiston xaritasida **Namangan viloyati**ni bosing (butun sahifa filtrlanadi).
2. **Yuqori ustuvorlikdagi holatlar** ro‘yxatidan **SUB-000125** ni oching.
3. Xavf bahosi **≈ 82/100**, ishonch darajasi va ma’lumot sifati alohida ko‘rsatiladi.
4. **NEGA?** → 3 ta asosiy sabab: aylanma o‘zgarishi (−65,8%), xavfli aloqadorlik, soliq yuklamasi.
5. **Vaqt bo‘yicha og‘ish** → **Aloqadorliklar** («Xavfli yo‘lga fokus») → **SI izohi**.
6. **Ekspert qarori** (izoh majburiy) → qaror tarixi va audit jurnalida ko‘rinadi.
7. **Hisobot** → PDF, XLSX yoki CSV.

## Arxitektura

```
frontend/   Vue 3 + TypeScript + Vite + Pinia + Vue Router + ECharts + MapLibre GL
backend/
  app/      FastAPI (/api/v1), SQLAlchemy 2, Alembic, JWT, RBAC/ABAC, audit, hisobotlar
  ml/       Risk Engine: belgilar → qoidalar + Isolation Forest + vaqt + graf → kalibrlash → sabablar
  data_gen/ Deterministik sintetik generator (5000 subyekt, 14 hudud, 11 soha, 24 oy)
  scripts/  seed.py, make_samples.py
  tests/    pytest (42 ta test)
data/samples/  Import ustasi uchun namuna fayllar (qasddan qo‘yilgan xatolar bilan)
docs/source/   Texnik topshiriq, UI spetsifikatsiyasi, GUI namunasi
```

**Tahlil zanjiri:** ma’lumot sifati → subyektni moslashtirish → tahliliy belgilar → modellar → kalibrlash → xavf bahosi → ishonch darajasi → sabablar → ekspert qarori.

- Har bir omilning ta’siri yakuniy bahoga proporsional taqsimlanadi. «NEGA?» oynasidagi ballar yig‘indisi xavf bahosiga teng.
- Ishonch darajasi ma’lumot sifati, tarix uzunligi, manbalar soni va modellar kelishuvidan hisoblanadi. Ma’lumot sifati 60 dan past bo‘lsa, ishonch «Past» dan oshmaydi.
- SI izohi Claude Sonnet 5 bilan yoziladi va raqamlar tekshiruvidan o‘tadi; kalit bo‘lmasa, shablon izohi ishlatiladi.
- API javoblari yagona formatda: `{"success", "data", "error"}`. Xato kodlari: `AUTH_*`, `DATA_*`, `MODEL_001`, `RISK_001`, `IMPORT_001`, `REPORT_001`, `SYSTEM_001`.

## Sintetik ma’lumot va rasmiy statistika

Subyektlar, STIR va ko‘rsatkichlar sun’iy, lekin tanlanma tuzilmasi rasmiy agregat statistikaga moslashtirilgan (`backend/data_gen/reference.py`):

| Parametr | Manba |
|---|---|
| Hududlar bo‘yicha subyektlar ulushi | Faoliyat ko‘rsatayotgan korxonalar soni, 2026-yil 1-aprel (577,2 ming) |
| Sohalar bo‘yicha ulush | Iqtisodiy faoliyat turlari bo‘yicha korxonalar soni, 2026-yil 1-avgust (601,3 ming) |
| Sohalar bo‘yicha o‘rtacha oylik aylanma | 2025-yil hajmi / korxonalar soni / 12 (sanoat 1 101,1; qurilish 313,9; chakana savdo 482,4; qishloq xo‘jaligi 538,9; bozor xizmatlari 1 050,3 trln so‘m) |
| Hududiy daraja | 2025-yil YaHM / korxonalar soni (ildiz bilan yumshatilgan) |
| Kichik va mikro korxonalar ulushi | 84,9% |

Har bir soha aylanmasi post-stratifikatsiya bilan rasmiy o‘rtachaga keltiriladi (±2%). Manbalar havolalari, taxminlar va tanlanma/rasmiy taqqoslash jadvali: **Ma’lumot manbalari → Sintetik ma’lumot kalibrlashi**.

## Sun’iy intellekt izohi (Claude Sonnet 5)

SI izohi hisoblangan natijalarni o‘zbek tilidagi matnga aylantiradi. Model bahoni yaratmaydi.

1. Loyiha ildizidagi `.env` faylida kalitni kiriting: `ANTHROPIC_API_KEY=sk-ant-...` (fayl gitga tushmaydi).
2. Backend serverini qayta ishga tushiring.
3. **Sozlamalar → Sun’iy intellekt xizmati → Ulanishni tekshirish** (token sarflamaydi).

Himoya qatlamlari (`backend/app/ai/`):

- Modelga faqat strukturali natija yuboriladi; javob JSON sxema bo‘yicha olinadi.
- Javobdagi har bir son hisoblangan qiymatlar bilan solishtiriladi; o‘ylab topilgan son, ayb bildiruvchi so‘z yoki kirill yozuvi topilsa, matn rad etiladi.
- Kalit yo‘q bo‘lsa, API xatosi, vaqt tugashi yoki rad etishda shablon izohi ko‘rsatiladi: platforma to‘xtamaydi.
- Har bir izoh `ai_explanations` jadvalida keshlanadi (bir xil natija uchun qayta to‘lov yo‘q), token sarfi va audit yozuvi saqlanadi.

Sozlamalar: `AI_MODEL` (sukut bo‘yicha `claude-sonnet-5`), `AI_EFFORT` (`low`), `AI_TIMEOUT_SECONDS` (30), `AI_ENABLED`.

## Qabul mezonlari (TZ §42)

| # | Mezon | Holat |
|---|---|---|
| AC-01 | Foydalanuvchi tizimga kira oladi | ✔ JWT, 5 ta demo hisob |
| AC-02 | Kamida 5 000 ta sinov subyekti | ✔ 5 000, rasmiy tuzilmaga moslashtirilgan |
| AC-03 | 14 hudud xaritada chiqadi | ✔ geoBoundaries ADM1 |
| AC-04 | Hududni bosganda filtr ishlaydi | ✔ |
| AC-05 | Subyekt kartasi ≤ 2 s da ochiladi | ✔ lokalda ≈ 0,15 s |
| AC-06 | Model real hisob bajaradi | ✔ baholar seed vaqtida hisoblanadi |
| AC-07 | Kamida 1 anomaliya algoritmi | ✔ Isolation Forest |
| AC-08 | Xavf sababi kamida 3 omil bilan | ✔ |
| AC-09 | Ekspert qarori DB ga saqlanadi | ✔ |
| AC-10 | Hisobot eksport qilinadi | ✔ PDF / XLSX / CSV |
| AC-11 | Harakat audit jurnaliga tushadi | ✔ |
| AC-12 | Demo boshidan oxirigacha xatosiz | ✔ avtomatik brauzer sinovida tekshirilgan |

## Testlar

```bash
cd backend && .venv/Scripts/python -m pytest -q          # 42 ta test: engine, API, RBAC, audit, import, hisobotlar
cd frontend && npm test && npm run typecheck && npm run build   # 12 ta unit test + tiplar + build
```

## MVP cheklovlari (ochiq aytilgan)

- **Ma’lumotlar sintetik.** Sifat ko‘rsatkichlari (AUC va boshqalar) sun’iy joylangan anomaliyalarga nisbatan o‘lchangan va real samaradorlikni anglatmaydi.
- **Xavf chegaralari (40/70) shartli.** Ular ilmiy kalibrlanmagan va Sozlamalar → Xavf chegaralari bo‘limida o‘zgartiriladi.
- **Baza: SQLite.** Sxema PostgreSQL/PostGIS ga ko‘chirishga tayyor, `DATABASE_URL` orqali almashtiriladi.
- **Fon vazifalar: FastAPI BackgroundTasks.** Production uchun Celery + Redis tavsiya etiladi.
- **Import RAW qatlamiga yuklanadi.** Tahlilga qo‘shish qayta hisoblash vazifasi orqali amalga oshiriladi.
- **Kesh, Prometheus/Grafana, markazlashgan loglash, rezervlash** Pilot va Production bosqichlariga qoldirilgan (TZ §24–27).

## Litsenziyalar va manbalar

- Kod: [GPL-3.0](LICENSE)
- Xarita chegaralari: [geoBoundaries](https://www.geoboundaries.org) gbOpen UZB ADM1 — © OpenStreetMap hissadorlari, ODbL 1.0
- PDF shrifti: DejaVu Sans (erkin litsenziya)
- [Texnik topshiriq](docs/source/RASAD_TZ_toldirilgan.txt) · [UI/UX spetsifikatsiyasi](docs/source/rasad%20promt.txt)
