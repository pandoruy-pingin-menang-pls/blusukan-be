# BACKEND IMPLEMENTATION PLAN
## Proyek: Blusukan — Event-Driven Dual-Sided Ecosystem (Solo Raya)

**Disusun sebagai:** Task Document / Technical Blueprint
**Role:** Senior Backend Engineer & Tech Lead
**Sumber acuan:** Proposal Hackathon "Blusukan" (BytesFest 2026 — Decent Work and Economic Growth)

---

## 0. Ringkasan Proyek (Context Recap)

Blusukan adalah aplikasi dual-mode:
- **Dolan Mode (B2C)** — wisatawan input constraint bahasa natural (waktu, budget, lokasi, minat) → sistem menghasilkan itinerary yang mengarahkan ke merchant "hidden gem" via weighted routing.
- **Bakul Mode (B2B)** — merchant mikro onboarding tanpa friksi (foto/voice note), menerima rekomendasi stok prediktif berbasis event & cuaca, melakukan settlement zero-fee via QRIS, dan mengumpulkan data untuk alternative credit scoring.
- Kedua mode terhubung lewat **Gamification Engine** (stamp & redemption) dan **Event Calendar** yang di-maintain lewat pipeline Human-in-the-Loop (HITL).

**Tech Stack (mengikuti proposal, Bab 2.3):**

| Layer | Teknologi |
|---|---|
| Backend Framework | Python 3.11+, **FastAPI** (async) |
| Database | **PostgreSQL** (via Supabase) + **PostGIS** (spatial) + **pgvector** (semantic search) |
| AI/LLM Layer | **Gemini API** (vision, speech-to-text, embedding, NLG), orkestrasi via **LangChain** |
| Routing Engine | **OSRM** (self-hosted, open source) |
| Auth & Storage | Supabase Auth (phone OTP) + Supabase Storage (foto menu, foto produk) |
| Task Queue / Scheduler | Celery + Redis (hanya untuk kalkulasi stok prediktif terjadwal) atau APScheduler jika skala MVP |
| Caching | Redis |
| Containerization | Docker + Docker Compose |
| CI/CD | GitHub Actions |
| API Docs | OpenAPI/Swagger (native FastAPI) |

> **Catatan Tech Lead:** Jika tim tidak mau maintain OSRM sendiri saat hackathon, siapkan fallback ke Mapbox Directions API/Google Directions API di layer `RoutingProvider` (interface abstraction) — tapi default implementation tetap OSRM sesuai proposal.

---

## PHASE 1 — Repository & Environment Setup

### 1.1 Struktur Direktori (Modular Monolith, disiapkan untuk mudah di-split jadi microservice nanti)

```
blusukan-backend/
├── app/
│   ├── main.py                     # FastAPI entrypoint
│   ├── core/
│   │   ├── config.py                # Pydantic Settings (.env loader)
│   │   ├── security.py              # JWT, password/OTP hashing, auth deps
│   │   ├── logging.py
│   │   └── exceptions.py            # Custom exception classes + handlers
│   ├── db/
│   │   ├── session.py                # SQLAlchemy/asyncpg session
│   │   ├── base.py
│   │   └── migrations/               # Alembic migration scripts
│   ├── modules/
│   │   ├── auth/
│   │   │   ├── router.py
│   │   │   ├── schemas.py
│   │   │   ├── service.py
│   │   │   └── models.py
│   │   ├── merchants/                # Bakul Mode: profile, catalog
│   │   ├── ingestion/                # Multimodal ingestion pipeline (Gemini)
│   │   ├── inventory/                # Predictive Stocking Model
│   │   ├── transactions/             # Ultra-Simple POS & Zero-Fee Settlement
│   │   ├── events/                   # Event calendar + HITL admin approval
│   │   ├── routing/                  # Weighted Routing Engine (SAW + OSRM)
│   │   ├── gamification/             # Stamp & Promo Redemption
│   │   ├── credit_score/             # Alternative Credit Scoring
│   │   └── admin/                    # Admin dashboard endpoints
│   ├── integrations/
│   │   ├── gemini_client.py
│   │   ├── osrm_client.py
│   │   ├── supabase_storage.py
│   │   └── qris_utils.py             # QRIS payload parsing/validation (bukan payment gateway)
│   ├── workers/
│   │   ├── celery_app.py
│   │   └── tasks_stock_recalc.py     # recalculate S_predicted terjadwal
│   └── tests/
│       ├── unit/
│       └── integration/
├── scripts/
│   ├── seed_dummy_data.py
│   └── init_postgis.sql
├── docker-compose.yml
├── Dockerfile
├── alembic.ini
├── requirements.txt / pyproject.toml
├── .env.example
└── README.md
```

**Aturan Routing API:**
- Seluruh *endpoint* backend **wajib** diawali dengan prefix `/api/` (misal: `/api/health`, `/api/auth/login`).
- Konvensi ini di-handle secara global melalui `APIRouter(prefix="/api")` di file `app/main.py`.

### 1.2 Branching Strategy

Gunakan **Trunk-based hybrid dengan Git Flow ringan** (cocok untuk tim hackathon 4 orang, tapi tetap disiplin):

| Branch | Fungsi | Rule |
|---|---|---|
| `main` | Production-ready, hanya menerima merge dari `develop` via PR + tag release | Protected, no direct push |
| `develop` | Integrasi seluruh fitur, base untuk staging/demo | Protected, wajib PR + minimal 1 review |
| `feature/<module>-<deskripsi>` | Contoh: `feature/auth-otp-login`, `feature/inventory-predictive-stock` | Branch dari `develop`, merge kembali ke `develop` |
| `fix/<deskripsi>` | Bugfix non-urgent | Branch dari `develop` |
| `hotfix/<deskripsi>` | Bugfix urgent di production | Branch dari `main`, merge ke `main` **dan** `develop` |
| `chore/<deskripsi>` | Setup tooling, CI, dependency bump | Branch dari `develop` |

**Alur rilis:**
```
feature/xxx → PR → develop → (staging demo test) → PR → main → tag v1.0.0
```
Commit convention: **Conventional Commits** (`feat:`, `fix:`, `refactor:`, `test:`, `chore:`, `docs:`).

### 1.3 Environment Variables (`.env.example`)

```env
# App
APP_ENV=development
APP_SECRET_KEY=
APP_DEBUG=true

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/blusukan
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_ANON_KEY=

# Auth
JWT_SECRET_KEY=
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30
OTP_PROVIDER_API_KEY=          # e.g. Twilio/Vonage/Fonnte

# AI
GEMINI_API_KEY=
GEMINI_MODEL_TEXT=gemini-2.5-flash
GEMINI_MODEL_VISION=gemini-2.5-flash
GEMINI_EMBEDDING_MODEL=text-embedding-004

# Routing
OSRM_BASE_URL=http://localhost:5000

# Weather
WEATHER_API_KEY=               # e.g. OpenWeatherMap/BMKG

# Redis / Celery
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1

# Storage
SUPABASE_STORAGE_BUCKET_MENU=merchant-menus
SUPABASE_STORAGE_BUCKET_VOICE=merchant-voicenotes
```

### 1.4 Dependency Inti (`requirements.txt`)

```
fastapi
uvicorn[standard]
pydantic-settings
sqlalchemy[asyncio]
asyncpg
alembic
geoalchemy2                # PostGIS ORM integration
pgvector
python-jose[cryptography]  # JWT
passlib[bcrypt]
langchain
langchain-google-genai
google-generativeai
httpx                      # OSRM / weather API client (async)
celery
redis
supabase                   # supabase-py client
pytest
pytest-asyncio
httpx[testing]
factory-boy                # test data factory
python-multipart           # file upload
```

### 1.5 Checklist Phase 1

- [ ] Init repo, buat `main` & `develop`
- [ ] Setup `.gitignore` (exclude `.env`, `__pycache__`, `*.pyc`)
- [ ] Setup Docker Compose: `api`, `postgres+postgis`, `redis`, `osrm`
- [ ] Install & konfigurasi Alembic
- [ ] Setup pre-commit hooks (`black`, `isort`, `flake8`/`ruff`)
- [ ] Setup GitHub Actions: lint + test on PR ke `develop`/`main`
- [ ] `README.md` berisi cara run lokal (docker-compose up)

---

## PHASE 2 — Database & Core Configurations

### 2.1 Entity Relationship Overview

```
users 1---1 merchant_profiles
users 1---N transactions (sebagai tourist)
merchant_profiles 1---N merchant_catalog_items
merchant_profiles 1---N transactions
merchant_profiles 1---N inventory_recommendations
merchant_profiles 1---N promos
events 1---N inventory_recommendations
users 1---N stamps
stamps N---1 promo_redemptions (via promo)
```

### 2.2 Skema Tabel Detail

#### `users`
| Kolom | Tipe | Keterangan |
|---|---|---|
| id | UUID PK | default `gen_random_uuid()` |
| phone_number | VARCHAR(20) UNIQUE NOT NULL | format E.164 |
| full_name | VARCHAR(150) | |
| role | ENUM('wisatawan','pedagang','admin') | user bisa switch role tapi role dasar disimpan; lihat catatan 2.2.1 |
| password_hash | VARCHAR NULLABLE | opsional jika pakai OTP-only |
| is_phone_verified | BOOLEAN DEFAULT false | |
| created_at | TIMESTAMPTZ DEFAULT now() | |
| updated_at | TIMESTAMPTZ | |

> **Catatan 2.2.1 (penting, sesuai Bab 2.1 proposal):** "Satu login bisa toggle antara Bakul Mode & Dolan Mode." Jadi `role` di tabel `users` sebaiknya BUKAN pembatas akses keras, melainkan **role default UI**. Buat kolom terpisah `has_merchant_profile BOOLEAN` yang menentukan apakah user boleh mengakses Bakul Mode. Semua orang defaultnya bisa akses Dolan Mode.

#### `merchant_profiles`
| Kolom | Tipe | Keterangan |
|---|---|---|
| id | UUID PK | |
| user_id | UUID FK → users.id | |
| business_name | VARCHAR(150) | |
| category | VARCHAR(50) | enum-like: `culinary`, `craft`, `batik`, `beverage`, dst |
| description | TEXT | |
| location | GEOGRAPHY(Point, 4326) | PostGIS, wajib index GIST |
| address_text | TEXT | |
| is_redemption_partner | BOOLEAN DEFAULT false | opt-in flag (Bab 2.4.1) |
| baseline_rating | NUMERIC(2,1) DEFAULT 4.0 | cold-start default (Bab 2.4.1) |
| review_count | INTEGER DEFAULT 0 | dipakai hitung `HiddenGemIndex` |
| baseline_inventory | JSONB | `{item_id: qty_per_day}` (Bab 2.4.2) |
| status | ENUM('pending','active','suspended') | |
| created_at, updated_at | TIMESTAMPTZ | |

Index wajib: `CREATE INDEX idx_merchant_location ON merchant_profiles USING GIST(location);`

#### `merchant_catalog_items`
| Kolom | Tipe | Keterangan |
|---|---|---|
| id | UUID PK | |
| merchant_id | UUID FK | |
| item_name | VARCHAR(150) | |
| price | NUMERIC(10,2) | |
| category | VARCHAR(50) | untuk `CategoryMatch` |
| description_raw | TEXT | hasil ekstraksi Gemini |
| embedding | VECTOR(768) | pgvector, sesuai dimensi model embedding Gemini |
| image_url | TEXT NULLABLE | |
| source_type | ENUM('photo','voice','manual') | |
| created_at | TIMESTAMPTZ | |

Index: `CREATE INDEX idx_catalog_embedding ON merchant_catalog_items USING ivfflat (embedding vector_cosine_ops);`

#### `events`
| Kolom | Tipe | Keterangan |
|---|---|---|
| id | UUID PK | |
| name | VARCHAR(200) | |
| genre | VARCHAR(50) | `cultural`, `sports`, `convention`, dst |
| location | GEOGRAPHY(Point,4326) | |
| venue_name | VARCHAR(150) | |
| estimated_attendee_count | INTEGER | |
| start_datetime | TIMESTAMPTZ | |
| end_datetime | TIMESTAMPTZ | |
| status | ENUM('scraped','pending_review','approved','rejected') | HITL pipeline (Bab 2.5.1) |
| source_url | TEXT | |
| reviewed_by_admin_id | UUID FK NULLABLE | |
| created_at | TIMESTAMPTZ | |

#### `transactions`
| Kolom | Tipe | Keterangan |
|---|---|---|
| id | UUID PK | |
| merchant_id | UUID FK | |
| tourist_user_id | UUID FK NULLABLE | nullable karena merchant bisa log walk-in tanpa app |
| nominal_value | NUMERIC(12,2) | |
| item_reference | JSONB NULLABLE | opsional daftar item |
| linked_itinerary_id | UUID FK NULLABLE | untuk trigger stamp |
| logged_at | TIMESTAMPTZ DEFAULT now() | |

#### `inventory_recommendations`
| Kolom | Tipe | Keterangan |
|---|---|---|
| id | UUID PK | |
| merchant_id | UUID FK | |
| event_id | UUID FK NULLABLE | |
| s_baseline | NUMERIC | |
| m_event | NUMERIC | |
| m_weather | NUMERIC | |
| s_predicted | NUMERIC | |
| weather_condition | VARCHAR(50) | |
| message_text | TEXT | output NLG Gemini |
| generated_for_date | DATE | |
| generated_at | TIMESTAMPTZ | |

#### `itineraries`
| Kolom | Tipe | Keterangan |
|---|---|---|
| id | UUID PK | |
| user_id | UUID FK | |
| raw_query | TEXT | input natural language asli |
| parsed_constraints | JSONB | `{time_limit, budget, radius, interests, start_location}` |
| waypoints | JSONB | ordered list of merchant_id + score breakdown |
| route_geojson | JSONB | hasil OSRM |
| status | ENUM('draft','active','completed') | |
| created_at | TIMESTAMPTZ | |

#### `stamps`
| Kolom | Tipe | Keterangan |
|---|---|---|
| id | UUID PK | |
| user_id | UUID FK | |
| merchant_id | UUID FK | |
| transaction_id | UUID FK UNIQUE | 1 transaksi = max 1 stamp (cegah duplikasi) |
| awarded_at | TIMESTAMPTZ | |

#### `promos`
| Kolom | Tipe | Keterangan |
|---|---|---|
| id | UUID PK | |
| merchant_id | UUID FK | |
| title | VARCHAR(150) | |
| stamp_required_count | INTEGER | |
| discount_type | ENUM('percentage','nominal') | |
| discount_value | NUMERIC | |
| is_active | BOOLEAN | |
| valid_until | DATE NULLABLE | |

#### `promo_redemptions`
| Kolom | Tipe | Keterangan |
|---|---|---|
| id | UUID PK | |
| user_id | UUID FK | |
| promo_id | UUID FK | |
| redeemed_at | TIMESTAMPTZ | |
| redemption_code | VARCHAR(10) UNIQUE | ditampilkan ke merchant sebagai bukti |
| status | ENUM('unredeemed','redeemed','expired') | |

### 2.3 Konfigurasi Koneksi & ORM

- Gunakan **SQLAlchemy 2.0 async** + `GeoAlchemy2` untuk tipe geography.
- Alembic autogenerate migration per modul (jangan satu migration raksasa).
- Aktifkan extension wajib di migration awal:
  ```sql
  CREATE EXTENSION IF NOT EXISTS postgis;
  CREATE EXTENSION IF NOT EXISTS vector;
  CREATE EXTENSION IF NOT EXISTS pgcrypto; -- gen_random_uuid()
  ```
- Koneksi ke Supabase: gunakan **connection pooling mode (pgbouncer, port 6543)** untuk API layer, dan **direct connection (port 5432)** untuk Alembic migration.

### 2.4 Integrasi Pihak Ketiga — Setup Awal

| Integrasi | Fungsi | Catatan Implementasi |
|---|---|---|
| Gemini API | Vision (OCR menu), Speech-to-Text, Embedding, NLG | Wrap semua call di `integrations/gemini_client.py` dengan retry + timeout, JANGAN panggil Gemini langsung dari router |
| OSRM | Path computation | Self-host via Docker image `osrm/osrm-backend`, preprocess peta OSM area Solo Raya (`osrm-extract` + `osrm-contract`) |
| Weather API | Input untuk `M_weather` | Cache hasil per kecamatan selama 1 jam (Redis) untuk hemat quota |
| Supabase Storage | Simpan foto menu/produk & voice note | Signed URL, expiry 1 jam untuk akses privat |
| OTP Provider | Verifikasi nomor HP | Rate limit 3x/menit per nomor |

### 2.5 Checklist Phase 2

- [ ] Semua tabel di atas dibuat via Alembic migration bertahap per modul
- [ ] Seed script dummy: 5 events, 15 merchant, 30 catalog item, 10 user
- [ ] Test koneksi PostGIS (`ST_DWithin` query) berjalan
- [ ] Test koneksi pgvector (`<=>` cosine distance query) berjalan
- [ ] `gemini_client.py`, `osrm_client.py` bisa dipanggil dari script standalone dan mengembalikan response valid

---

## PHASE 3 — Staged Feature Implementation (Core Focus)

> Prinsip pengerjaan tiap stage: **service layer murni logika (testable, tanpa dependency FastAPI Request)**, router hanya validasi input/output. Semua kalkulasi angka (SAW score, stok prediktif) **HARUS deterministic di backend**, LLM hanya untuk NLG/ekstraksi (sesuai prinsip proposal Bab 2.4.2: "LLM as Presentation Layer, bukan calculator").

### STAGE 3.1 — Authentication & User/Role Management

**Tujuan:** Login berbasis OTP, dual-role toggle tanpa perlu akun terpisah.

**Step-by-step logic:**
1. `POST /auth/otp/request` → generate OTP 6 digit, simpan hash OTP + expiry (5 menit) di Redis dengan key `otp:{phone_number}`, kirim via provider.
2. `POST /auth/otp/verify` → cocokkan OTP, jika valid:
   - Jika `phone_number` belum ada di `users` → create user baru (`role default = wisatawan`, `has_merchant_profile = false`).
   - Jika sudah ada → fetch user.
   - Generate `access_token` (JWT, 60 menit) + `refresh_token` (30 hari, disimpan hashed di tabel `refresh_tokens`).
3. `POST /auth/refresh` → validasi refresh token, rotasi (revoke lama, issue baru) — cegah replay attack.
4. `GET /auth/me` → return profile user + flag `has_merchant_profile` (dipakai FE untuk render toggle Dolan/Bakul).
5. `POST /auth/logout` → revoke refresh token aktif.

**API Table:**

| Method | Route | Request | Response |
|---|---|---|---|
| POST | `/api/v1/auth/otp/request` | `{phone_number}` | `202 {message: "OTP sent", retry_after: 60}` |
| POST | `/api/v1/auth/otp/verify` | `{phone_number, otp_code}` | `200 {access_token, refresh_token, user: {...}}` |
| POST | `/api/v1/auth/refresh` | `{refresh_token}` | `200 {access_token, refresh_token}` |
| GET | `/api/v1/auth/me` | header `Authorization: Bearer` | `200 {id, full_name, phone_number, has_merchant_profile}` |
| POST | `/api/v1/auth/logout` | `{refresh_token}` | `204` |

**Edge cases wajib diantisipasi:**
- OTP request spam → rate limit per nomor (max 3x/10 menit), return `429`.
- OTP expired tapi user submit → return `400 OTP_EXPIRED`, jangan generic error.
- Nomor HP format tidak valid (bukan E.164) → validasi regex di schema Pydantic sebelum masuk service.
- Race condition: dua request verify OTP bersamaan dengan kode benar → gunakan Redis `DEL` atomic setelah verifikasi sukses agar OTP hanya bisa dipakai sekali (single-use).
- Refresh token yang sudah direvoke tapi dipakai lagi → detect sebagai potensi token theft, revoke SEMUA token user tersebut (session invalidation total) dan log security event.
- User ganti nomor HP tanpa logout dulu di device lain → pastikan JWT tetap valid sampai expiry (accept as known limitation), dokumentasikan.

---

### STAGE 3.2 — Bakul Mode: Merchant Onboarding & Multimodal Ingestion Pipeline

**Tujuan:** Frictionless onboarding via foto menu / voice note (Bab 2.4.3).

**Step-by-step logic:**
1. `POST /merchants` → buat `merchant_profiles` dasar (nama, kategori, lokasi GPS dari device) dengan `status='pending'`. Set `has_merchant_profile=true` pada user.
2. `POST /merchants/{id}/catalog/ingest` (multipart) → terima file foto ATAU audio:
   - Upload raw file ke Supabase Storage, simpan `source_type`.
   - **Jika foto:** panggil `gemini_client.extract_text_from_image()` (Vision) → raw text.
   - **Jika audio:** panggil `gemini_client.speech_to_text()` → raw text.
   - Panggil `gemini_client.structure_menu_text(raw_text)` dengan **strict JSON schema prompt** → hasil list `{item_name, price, category}`.
   - **Validasi hasil LLM secara defensif** sebelum insert ke DB (lihat edge case di bawah).
   - Untuk tiap item valid: generate embedding via `gemini_client.embed_text()`, insert ke `merchant_catalog_items`.
   - Return daftar item yang berhasil di-parse ke FE untuk **konfirmasi manual oleh merchant** (HITL kecil di sisi user) sebelum final save — ini krusial untuk minim bug data.
3. `POST /merchants/{id}/catalog/confirm` → merchant confirm/edit hasil ekstraksi → commit final ke DB, ubah `merchant_profiles.status='active'` jika minimal 1 item tersimpan.
4. `PATCH /merchants/{id}/redemption-partner` → toggle `is_redemption_partner`.

**API Table:**

| Method | Route | Request | Response |
|---|---|---|---|
| POST | `/api/v1/merchants` | `{business_name, category, description, latitude, longitude, address_text}` | `201 {merchant_id, status:"pending"}` |
| POST | `/api/v1/merchants/{id}/catalog/ingest` | multipart: `file`, `source_type` | `200 {draft_items: [{item_name, price, category, confidence}]}` |
| POST | `/api/v1/merchants/{id}/catalog/confirm` | `{items: [{item_name, price, category}]}` | `201 {saved_count}` |
| PATCH | `/api/v1/merchants/{id}/redemption-partner` | `{is_redemption_partner: bool}` | `200 {merchant_id, is_redemption_partner}` |
| GET | `/api/v1/merchants/{id}` | - | `200 {merchant profile + catalog list}` |

**Edge cases wajib diantisipasi:**
- **LLM mengembalikan JSON tidak valid / ada teks tambahan di luar JSON** → wrap parsing dengan try/except, strip markdown fences (```json), jika parsing gagal → return `422` dengan pesan "silakan coba ulang / input manual", JANGAN biarkan raw LLM output masuk ke DB.
- **LLM hasil harga NULL atau bukan angka** (tulisan tangan buram) → set default `null`, tandai `confidence: "low"`, wajib user isi manual di step konfirmasi — jangan auto-save harga 0.
- **Foto blur / audio noise berat** → jika `draft_items` kosong, return `200 {draft_items: [], message: "Tidak dapat membaca dokumen, silakan foto ulang atau isi manual"}`, bukan error 500.
- **Duplikasi item** (merchant upload menu yang sama 2x) → saat confirm, cek `item_name` mirip (fuzzy match/trigram) di merchant yang sama, warn FE tapi tetap izinkan (jangan block, karena bisa jadi varian menu).
- **GPS lokasi tidak valid** (0,0 atau di luar bounding box Solo Raya) → validasi di schema, tolak dengan `400 INVALID_LOCATION`.
- **File upload > limit size** (misal 10MB) → reject di level FastAPI middleware sebelum sampai ke Gemini (hemat cost & waktu).
- **Rate/cost control:** batasi jumlah ingest call per merchant per hari (misal 20x) untuk cegah abuse quota Gemini.

---

### STAGE 3.3 — Bakul Mode: Predictive Stocking Model

**Tujuan:** Implementasi formula deterministik Bab 2.4.2 — **ini bagian paling sensitif terhadap bug karena berupa business rule matematis**, harus diuji dengan test case eksplisit per skenario.

**Step-by-step logic (WAJIB diimplementasikan persis sesuai proposal, bukan didekati LLM):**

1. **Trigger:** Celery beat job harian (misal jam 05:00 WIB) `tasks_stock_recalc.py` untuk semua merchant `status='active'`. Juga bisa dipanggil manual via endpoint (misal setelah event baru di-approve).
2. Untuk tiap merchant:
   a. Ambil `S_baseline` dari `merchant_profiles.baseline_inventory` (per kategori item; jika belum diisi merchant, gunakan default per `category` merchant, misal HIK = 50 porsi/hari).
   b. Query event terdekat: `events` dengan `status='approved'` dan `start_datetime` dalam rentang H-3 s.d. H+1, filter jarak via PostGIS `ST_Distance(merchant.location, event.location) <= 3000` (meter).
   c. **Hitung `M_event`** berdasarkan lookup table:
      ```
      IF attendee > 5000 AND distance < 1000m: M_event = 0.30
      ELIF 1000 <= attendee <= 5000 AND distance < 1000m: M_event = 0.10   # catatan: proposal menulis "+15%" di teks tapi nilai 0.10 di rumus — implementasikan 0.10 sesuai rumus, FLAG untuk tim produk agar konsisten
      ELIF attendee > 5000 AND 1000m <= distance <= 3000m: M_event = 0.10
      ELSE: M_event = 0
      ```
      > **CATATAN BUG POTENSIAL DARI PROPOSAL:** Ada inkonsistensi angka antara narasi ("+15% surge") dan variabel (`M_event = 0.10`) untuk kasus attendee 1.000–5.000. **Sebagai engineer, implementasikan nilai numerik pada rumus (0.10) sebagai source of truth**, dan catat sebagai technical debt/butuh konfirmasi PM sebelum go-live.
      - Jika ada **lebih dari satu event yang match**, ambil `M_event` **maksimum** (bukan dijumlahkan) — untuk mencegah surge > 100% yang tidak realistis. (Keputusan desain, dokumentasikan di code comment.)
   d. **Hitung `M_weather`** berdasarkan forecast cuaca H+1 dari Weather API + kategori merchant:
      ```
      IF heavy_rain AND category == 'hot_culinary': M_weather = 0.15
      ELIF heavy_rain AND category == 'cold_beverage_dessert': M_weather = -0.20
      ELIF heavy_rain AND category == 'outdoor_retail': M_weather = -0.30
      ELIF (sunny OR hot) AND category == 'cold_beverage': M_weather = 0.25
      ELSE: M_weather = 0
      ```
   e. Hitung `S_predicted = S_baseline * (1 + M_event + M_weather)`.
   f. **Clamp hasil**: `S_predicted = max(S_predicted, 0)` — cegah nilai negatif jika kombinasi minus ekstrem.
   g. Simpan row baru di `inventory_recommendations`.
   h. Panggil `gemini_client.generate_stock_advice(context)` **hanya untuk mengubah angka final menjadi kalimat** (NLG layer), contoh prompt ketat: *"Berdasarkan data berikut: baseline X, event Y (jarak Z), cuaca W → tulis 1 kalimat saran stok dalam Bahasa Indonesia casual, sertakan persentase kenaikan/penurunan yang SUDAH dihitung, jangan menghitung ulang."*
3. `GET /merchants/{id}/inventory-recommendations/today` → merchant lihat rekomendasi hari ini.

**API Table:**

| Method | Route | Request | Response |
|---|---|---|---|
| GET | `/api/v1/merchants/{id}/inventory-recommendations/today` | - | `200 {s_baseline, m_event, m_weather, s_predicted, message_text, event_context}` |
| GET | `/api/v1/merchants/{id}/inventory-recommendations/history` | query `?limit=7` | `200 [{date, s_predicted, message_text}]` |
| PATCH | `/api/v1/merchants/{id}/baseline-inventory` | `{category: value}` | `200 {baseline_inventory}` |
| POST | `/api/v1/admin/inventory-recommendations/recalculate` | `{merchant_id?}` (admin/manual trigger) | `202 {job_id}` |

**Edge cases wajib diantisipasi:**
- Merchant belum set `baseline_inventory` sama sekali → gunakan default per kategori (bukan 0), agar `S_predicted` tidak selalu 0.
- Weather API down/timeout → fallback `M_weather = 0`, tetap generate rekomendasi (jangan gagalkan seluruh job karena 1 API eksternal down), log warning.
- Tidak ada event dalam radius 3km → `M_event = 0`, tetap tampilkan pesan "Tidak ada event besar, stok seperti biasa" (bukan error/kosong).
- Event dengan `estimated_attendee_count = NULL` (data scraping tidak lengkap) → treat sebagai tidak memenuhi threshold manapun (`M_event` kontribusi 0 dari event itu), jangan crash.
- Duplicate job run (Celery retry) di hari yang sama → gunakan `UNIQUE(merchant_id, generated_for_date)` constraint + upsert, cegah data ganda.
- Job berjalan untuk ratusan merchant sekaligus → batching + async gather dengan concurrency limit (misal `asyncio.Semaphore(10)`) supaya tidak membanjiri Gemini API rate limit.

---

### STAGE 3.4 — Bakul Mode: Ultra-Simple POS & Zero-Fee Settlement

**Tujuan:** Log transaksi tanpa platform pernah pegang uang (Bab 2.4.4).

**Step-by-step logic:**
1. `GET /merchants/{id}/qris` → return QRIS statis milik merchant (disimpan sebagai image URL saat onboarding, opsional field terpisah `qris_image_url`).
2. `POST /merchants/{id}/transactions` (dipanggil merchant setelah menerima pembayaran manual) → payload `{nominal_value, item_reference?, linked_itinerary_id?}`.
   - Insert ke `transactions`.
   - **Jika `linked_itinerary_id` ada** (artinya transaksi berasal dari tourist yang sedang ikuti itinerary Blusukan) → trigger Gamification Engine (Stage 3.7) secara async (event-driven, jangan blocking response POS).
   - Update agregat harian merchant (untuk dashboard: omzet hari ini, jumlah transaksi) — bisa via materialized view atau counter cache di Redis yang di-flush ke DB tiap jam.
3. `GET /merchants/{id}/transactions/summary` → omzet hari ini, jumlah transaksi (untuk dashboard "Selamat Pagi, Bu Marni").

**API Table:**

| Method | Route | Request | Response |
|---|---|---|---|
| GET | `/api/v1/merchants/{id}/qris` | - | `200 {qris_image_url}` |
| POST | `/api/v1/merchants/{id}/transactions` | `{nominal_value, item_reference?, linked_itinerary_id?}` | `201 {transaction_id, stamp_awarded: bool}` |
| GET | `/api/v1/merchants/{id}/transactions/summary` | query `?date=today` | `200 {total_omzet, total_transaksi}` |
| GET | `/api/v1/merchants/{id}/transactions` | query `?page&limit` | `200 {items:[...], pagination}` |

**Edge cases wajib diantisipasi:**
- `nominal_value` negatif atau 0 → validasi schema, `400`.
- `nominal_value` tidak wajar (misal 999.000.000) — tambahkan soft-warning/flag `is_suspicious` untuk anti-fraud credit scoring, tapi tetap izinkan simpan (jangan block operasional).
- Endpoint ini **tidak boleh butuh koneksi internet stabil terus-menerus** secara UX — di sisi FE idealnya ada offline queue, tapi di backend cukup pastikan endpoint idempotent: sertakan `client_reference_id` opsional dari FE agar retry tidak menghasilkan transaksi ganda (`UNIQUE(merchant_id, client_reference_id)`).
- `linked_itinerary_id` tidak valid/milik user lain → validasi kepemilikan sebelum trigger stamp, jangan percaya begitu saja.
- Merchant yang bukan `is_redemption_partner` tapi transaksi punya `linked_itinerary_id` → tetap catat transaksi & tetap beri stamp (stamp untuk SEMUA hidden gem yang terdaftar, bukan hanya redemption partner — redemption partner hanya untuk **priority visibility**, bukan syarat stamp). Pastikan logic ini eksplisit dites.

---

### STAGE 3.5 — Event Calendar & HITL Admin Pipeline

**Tujuan:** Bab 2.5.1 — scraping otomatis + review manual sebelum event live.

**Step-by-step logic:**
1. Celery periodic task `tasks_scraper.py` (misal tiap 6 jam) → scrape sumber (portal berita lokal/community page yang di-whitelist).
2. Panggil `gemini_client.extract_event_structured(raw_html_text)` dengan strict JSON schema → `{name, coordinates, genre, estimated_attendee_count, start_datetime}`.
3. Insert ke `events` dengan `status='pending_review'`. **Jangan pernah auto-approve dari hasil scraping+LLM.**
4. Admin dashboard: `GET /admin/events?status=pending_review` → list untuk direview.
5. `PATCH /admin/events/{id}/review` → admin approve/reject/edit field sebelum approve.
6. Setelah `status='approved'`, event otomatis masuk perhitungan Stage 3.3 & 3.6 pada run berikutnya.

**API Table:**

| Method | Route | Request | Response |
|---|---|---|---|
| GET | `/api/v1/admin/events` | query `?status=pending_review` | `200 [events]` |
| PATCH | `/api/v1/admin/events/{id}/review` | `{action: "approve"\|"reject", edited_fields?}` | `200 {event}` |
| POST | `/api/v1/admin/events` | manual create (fallback jika scraper gagal) | `201 {event}` |
| GET | `/api/v1/events` | query `?status=approved&upcoming=true` (public) | `200 [events]` |

**Edge cases wajib diantisipasi:**
- Scraper gagal total (source down) → fallback source kedua (sesuai Tabel Risk di proposal Bab 3.1.3), catat log kegagalan, JANGAN biarkan silent fail tanpa alert.
- Event duplikat dari 2 sumber berbeda → dedup check berdasarkan `name` (fuzzy) + `start_datetime` + jarak lokasi < 200m sebelum insert.
- `estimated_attendee_count` hasil scraping tidak masuk akal (misal 99999999) → flag untuk review manual dengan warning, jangan auto-approve meskipun ada tombol "quick approve".
- Event yang sudah lewat (`end_datetime < now()`) tapi masih `status='pending_review'` → auto-expire via scheduled job, exclude dari kalkulasi.

---

### STAGE 3.6 — Dolan Mode: Weighted Routing / Itinerary Generation

**Tujuan:** Implementasi formula SAW (Bab 2.4.1) — bagian paling kompleks, wajib logika presisi.

**Step-by-step logic:**
1. `POST /itineraries` menerima `raw_query` (natural language) + `start_location {lat, lng}`.
2. **Parsing constraint:** panggil `gemini_client.parse_constraints(raw_query)` dengan strict JSON schema output:
   ```json
   {"time_limit_minutes": int, "budget_idr": int, "search_radius_meter": int, "interest_categories": [string], "avoid_crowds": bool}
   ```
   - Sertakan default value di service layer jika field tidak berhasil di-extract (misal `time_limit_minutes` default 240, `search_radius_meter` default 2000) — **jangan biarkan constraint kosong menyebabkan query kandidat kosong**.
3. **Candidate generation (PostGIS):**
   ```sql
   SELECT * FROM merchant_profiles
   WHERE status='active'
   AND ST_DWithin(location, ST_MakePoint(:lng,:lat)::geography, :radius)
   ```
4. **Scoring per kandidat (SAW formula, dihitung di Python, BUKAN di SQL agar mudah diuji unit):**
   ```
   HiddenGemIndex = 1 - min(review_count / MAX_REVIEW_THRESHOLD, 1)   # MAX_REVIEW_THRESHOLD misal 100
   CategoryMatch = cosine_similarity(query_embedding, merchant_catalog_embedding_avg)  # via pgvector <=> operator
   DistanceNorm = 1 - (distance_meter / max_radius_meter)   # clamp ke [0,1]
   RatingNorm = merchant.baseline_rating / 5.0

   # Bobot dinamis berdasar parsed constraint:
   IF avoid_crowds == True: w1 = 0.4 else w1 = 0.2
   IF time_limit_minutes < 120: w3 = 0.4 else w3 = 0.2
   # w1+w2+w3+w4 harus selalu = 1.0 → normalisasi ulang setelah assignment manual

   Score = w1*HiddenGemIndex + w2*CategoryMatch + w3*DistanceNorm + w4*RatingNorm
   IF merchant.is_redemption_partner: Score *= 1.15
   ```
   > **Wajib unit test:** pastikan `w1+w2+w3+w4 == 1.0` (dengan toleransi floating point 1e-6) di setiap kombinasi constraint sebelum dipakai kalkulasi — ini sumber bug paling umum di formula weighted scoring.
5. **Filtering:** buang kandidat yang melebihi sisa budget (asumsikan average spend per merchant dari data historis/kategori) atau di luar radius waktu tempuh (`distance / walking_speed_4.5kmh > time_limit_minutes`).
6. Sort by `Score` DESC, ambil top-N (misal 3-5 waypoint sesuai `time_limit_minutes`).
7. Kirim ordered waypoints ke `osrm_client.get_route(waypoints)` → dapatkan `route_geojson`, `total_distance`, `estimated_duration`.
8. **Validasi hasil OSRM terhadap `time_limit_minutes` user** — jika `estimated_duration` melebihi limit, **drop waypoint terakhir dan re-request OSRM** (iterative trimming), bukan tampilkan rute yang melanggar constraint user.
9. Simpan ke `itineraries`, return ke FE.
10. `PATCH /itineraries/{id}/start` → set `status='active'`, mulai geofence tracking sisi FE (backend hanya expose endpoint check-in).

**API Table:**

| Method | Route | Request | Response |
|---|---|---|---|
| POST | `/api/v1/itineraries` | `{raw_query, start_location:{lat,lng}}` | `201 {itinerary_id, parsed_constraints, waypoints:[{merchant_id, name, score, order}], route_geojson, estimated_duration}` |
| GET | `/api/v1/itineraries/{id}` | - | `200 {...}` |
| PATCH | `/api/v1/itineraries/{id}/start` | - | `200 {status:"active"}` |
| POST | `/api/v1/itineraries/{id}/checkin` | `{merchant_id, current_location}` | `200 {checked_in: bool, is_near_merchant: bool}` |

**Edge cases wajib diantisipasi:**
- Tidak ada kandidat merchant dalam radius (daerah sepi) → auto-expand radius 1.5x sekali (dengan notifikasi ke user "radius diperluas"), jika tetap kosong return `200 {waypoints: [], message: "Belum ada merchant terdaftar di area ini"}`, bukan error 404/500.
- `CategoryMatch` untuk merchant tanpa item catalog (embedding kosong) → default `CategoryMatch = 0` (bukan crash null pointer), merchant tetap eligible lewat kriteria lain.
- Semua kandidat punya `Score` sama (tie) → tambahkan secondary sort key `distance ASC` untuk determinism (hasil harus reproducible untuk query yang identik).
- User budget sangat kecil (< harga rata-rata 1 item manapun) → return response eksplisit "budget tidak cukup untuk membuat itinerary" alih-alih list kosong tanpa penjelasan.
- `parsed_constraints` dari Gemini mengandung nilai di luar rentang wajar (misal `time_limit_minutes: -30` atau `budget_idr: 999999999`) → clamp dengan `MIN`/`MAX` sane bounds sebelum dipakai query.
- OSRM tidak menemukan rute jalan kaki valid antar 2 titik (terhalang sungai dll) → catch exception dari OSRM client, exclude waypoint bermasalah, regenerate rute tanpa titik tersebut, jangan biarkan seluruh request gagal karena 1 segmen.

---

### ⚠️ 3.6.1 — Formula Ambiguities & Engineering Decisions (WAJIB DIBACA SEBELUM CODING STAGE 3.6)

Bagian ini mendokumentasikan **selisih antara rumus literal di proposal vs implementasi yang secara matematis benar**, beserta rekomendasi solusi. Tim wajib memilih salah satu opsi di bawah dan mencatat keputusan final di code comment + laporan (untuk transparansi ke juri/dosen pembimbing).

#### Ambiguitas #1 — Term `Distance` di rumus SAW (PALING KRITIS)

**Masalah:** Proposal menulis rumus utama:
```
Score = w1(HiddenGemIndex) + w2(CategoryMatch) + w3(1/Distance) + w4(Rating)
```
tapi kemudian mendefinisikan variabel `Distance` sebagai **sudah dinormalisasi ke arah "kedekatan"**:
```
Distance_normalized = 1 − (raw_distance / MaxRadius)   → 1.0 = sangat dekat, 0 = di tepi radius
```
Jika `1/Distance_normalized` benar-benar dipakai literal, merchant yang **paling jauh** (Distance_normalized → 0) akan menghasilkan `1/x → ∞`, sehingga justru mendapat skor tertinggi — **berlawanan dengan tujuan desain** (mengutamakan kedekatan).

| Opsi | Deskripsi | Rekomendasi |
|---|---|---|
| **A — Ganti jadi additive langsung (yang saya pakai di plan)** | `w3 × Distance_normalized` (tanpa `1/x`) | ✅ **Direkomendasikan.** Paling konsisten dengan definisi variabel `Distance_normalized` yang sudah ada, secara matematis stabil, mudah dijelaskan ke juri sebagai "koreksi minor notasi rumus, bukan perubahan intent". |
| **B — Pakai `1/Distance` tapi dengan raw distance (bukan yang sudah dinormalisasi)** | `w3 × (1/(raw_distance_meter + epsilon))`, lalu normalisasi hasilnya ke [0,1] terhadap seluruh kandidat (min-max scaling) | Bisa dipakai jika tim ingin tetap literal ke notasi asli `1/Distance`, tapi butuh langkah normalisasi tambahan (`epsilon` untuk cegah div-by-zero saat distance=0) — lebih kompleks tanpa benefit tambahan dibanding Opsi A. |
| **C — Tanya ulang ke penulis proposal / dosen pembimbing** | Klarifikasi intent asli sebelum submit final | Lakukan ini **paralel** dengan opsi A — kalian tetap bisa mulai coding pakai Opsi A sambil menunggu konfirmasi, karena Opsi A tidak mengubah hasil fungsional yang diinginkan (dekat = prioritas). |

**Solusi konkret yang saya sarankan:** Implementasikan **Opsi A**, lalu di laporan/dokumentasi teknis tulis catatan kaki singkat: *"Formula 1/Distance pada dokumen proposal direalisasikan sebagai Distance_normalized (1 − distance/MaxRadius) untuk menjaga korelasi positif antara kedekatan dan skor, konsisten dengan definisi variabel Distance yang telah dinormalisasi."* Ini membuat keputusan terlihat sengaja dan terukur, bukan kelalaian.

#### Ambiguitas #2 — Cara menghitung bobot `w1, w2, w3, w4`

**Masalah:** Proposal hanya menjelaskan **kualitatif** ("request hidden alleys memaksimalkan w1", "request buru-buru memaksimalkan w3", total selalu 1.0) tanpa rumus/tabel angka pasti.

**Solusi yang disarankan — pilih salah satu, urut dari paling simpel ke paling robust:**

1. **Rule-based lookup table (disarankan untuk MVP/hackathon)** — definisikan tabel bobot preset berdasarkan kombinasi intent yang di-extract Gemini, contoh:

   | Intent terdeteksi | w1 (HiddenGem) | w2 (Category) | w3 (Distance) | w4 (Rating) |
   |---|---|---|---|---|
   | Default (tidak ada preferensi eksplisit) | 0.25 | 0.25 | 0.25 | 0.25 |
   | `avoid_crowds = true` | 0.40 | 0.20 | 0.20 | 0.20 |
   | `time_limit_minutes < 120` (buru-buru) | 0.15 | 0.20 | 0.45 | 0.20 |
   | `interest_categories` sangat spesifik (mis. "batik saja") | 0.15 | 0.50 | 0.20 | 0.15 |
   | Kombinasi 2 intent sekaligus | rata-ratakan lalu **wajib renormalisasi** agar total = 1.0 | | | |

   Implementasi: simpan tabel ini sebagai **konstanta terpisah** (`app/modules/routing/weight_presets.py`), bukan hardcode di service — memudahkan tuning tanpa redeploy logic inti. Setelah assignment, **selalu jalankan** `weights = {k: v/sum(weights.values()) for k,v in weights.items()}` untuk jaga invariant total=1.0 meski preset di-edit sembarangan.

2. **LLM-assisted weighting (lebih adaptif, sedikit lebih berisiko)** — minta Gemini langsung mengembalikan `{w1,w2,w3,w4}` sebagai bagian dari JSON constraint parsing di Stage 3.6 langkah 2, dengan prompt yang menjelaskan makna tiap bobot. **Wajib** tetap clamp & renormalisasi di backend (jangan percaya LLM menjaga total=1.0 dengan presisi), dan tetapkan `min_weight` (mis. 0.1) per komponen supaya tidak ada kriteria yang hilang total (`w=0`) akibat output ekstrem dari LLM.

3. **Hybrid (disarankan untuk versi pasca-hackathon/produksi)** — mulai dari lookup table (opsi 1) sebagai default aman, tapi izinkan LLM melakukan *fine-adjustment* kecil (±0.1) dari preset berdasarkan nuansa bahasa yang lebih halus di query user. Ini mengurangi risiko LLM non-determinism sambil tetap adaptif.

**Rekomendasi saya:** mulai dari **Opsi 1 (rule-based)** untuk kebutuhan demo hackathon — deterministik, mudah di-unit-test, tidak bergantung kualitas output LLM. Upgrade ke Opsi 3 setelah MVP tervalidasi.

#### Ambiguitas #3 — Formula `HiddenGemIndex`

**Masalah:** Proposal hanya menyatakan *"derived inversely from review count, 1.0 = zero footprint"* tanpa rumus matematis eksplisit.

**Solusi yang disarankan:**

```
HiddenGemIndex = 1 − min(review_count / MAX_REVIEW_THRESHOLD, 1)
```
di mana `MAX_REVIEW_THRESHOLD` adalah konstanta yang merepresentasikan "jumlah review yang sudah dianggap mainstream" (bukan angka sembarangan). Cara menentukannya:

- **Jangan hardcode angka tebakan** (mis. asal pilih 100). Sebagai gantinya, hitung dari **distribusi data riil**: ambil **persentil ke-90 (P90)** dari `review_count` seluruh merchant aktif di database saat job maintenance berjalan (mis. mingguan), lalu gunakan nilai itu sebagai `MAX_REVIEW_THRESHOLD` dinamis. Ini membuat definisi "hidden gem" **relatif terhadap kondisi pasar Solo Raya saat ini**, bukan angka statis yang bisa jadi tidak relevan setelah user growth.
- Simpan `MAX_REVIEW_THRESHOLD` di tabel config (`system_settings`) yang di-refresh oleh scheduled job, bukan di-hardcode di kode — supaya tidak perlu redeploy tiap kali ingin tuning.
- Tambahkan lower bound: merchant dengan `review_count = 0` (baru onboarding) otomatis dapat `HiddenGemIndex = 1.0` (paling diprioritaskan sebagai hidden gem) — ini **selaras dengan tujuan bisnis proposal** (mendorong visibilitas merchant baru).

#### Ambiguitas #4 — Inkonsistensi `M_event` tier 2 (sudah disinggung sebelumnya, dirangkum ulang di sini)

**Masalah:** Narasi menyebut "+15% surge" untuk event 1.000–5.000 attendee & jarak <1km, tapi rumus menuliskan `M_event = 0.10` (yaitu +10%).

**Solusi yang disarankan:**
1. Implementasikan nilai **0.10 dari rumus** sebagai source of truth (rumus lebih eksplisit & lebih mudah diverifikasi daripada narasi).
2. Simpan **semua threshold `M_event`/`M_weather` sebagai data di tabel `system_settings`/config table**, bukan hardcoded angka di kode — sehingga jika tim akhirnya sepakat memakai 0.15, cukup update 1 baris data, tanpa redeploy.
3. Cantumkan catatan di laporan akhir proyek: *"Nilai M_event 0.10 dipilih berdasarkan rumus matematis pada dokumen, dengan asumsi narasi '+15%' adalah salah ketik."*

---

### 📋 Ringkasan Aksi (Checklist Sebelum Mulai Coding Stage 3.6)

- [ ] Tim sepakat pakai **Opsi A** untuk term Distance (rekomendasi utama)
- [ ] Tim pilih metode bobot w1-w4: **rule-based lookup table** untuk MVP (rekomendasi utama)
- [ ] `MAX_REVIEW_THRESHOLD` dibuat dinamis (P90) dan disimpan di config table, bukan hardcode
- [ ] `M_event`/`M_weather` thresholds dipindah ke config table agar mudah di-tuning
- [ ] Semua keputusan di atas ditulis sebagai code comment di `app/modules/routing/scoring.py` dan disalin ke laporan akhir proyek sebagai "Engineering Decision Log" — ini justru bisa jadi nilai tambah di mata juri karena menunjukkan rigor engineering, bukan sekadar copy-paste rumus proposal mentah-mentah

---

### STAGE 3.7 — Gamification Engine (Stamp & Promo Redemption)

**Tujuan:** Bab 2.4.5 & 2.5.4 — event-driven stamp minting dari transaksi.

**Step-by-step logic:**
1. **Trigger:** dipanggil secara internal (bukan expose ke publik) setelah `POST /merchants/{id}/transactions` sukses **dan** `linked_itinerary_id` valid milik tourist yang login.
2. Service `gamification_service.award_stamp(transaction)`:
   - Cek constraint `UNIQUE(transaction_id)` di tabel `stamps` — cegah double award jika event terpanggil dua kali (idempotency).
   - Insert row `stamps`.
   - Hitung total stamp aktif user → cek apakah memenuhi `stamp_required_count` promo manapun yang berlaku → jika ya, buat notifikasi "promo unlocked" (lihat integrasi notifikasi di bawah).
3. `GET /users/me/stamps` → list stamp + progress ke promo berikutnya.
4. `GET /promos/available` → list promo yang statusnya `is_active=true` dan `stamp_required_count <= user_total_stamp`.
5. `POST /promos/{id}/redeem` → generate `redemption_code` unik (short, mudah dibacakan ke merchant), `status='unredeemed'`, response ditampilkan sebagai layar konfirmasi ke tourist (FE tunjukkan ke merchant secara manual, sesuai Bab 2.4.5: "manually present the redeemed promo screen").
6. (Opsional MVP+1) `POST /merchants/{id}/promo-redemptions/{code}/confirm` → merchant scan/input kode untuk konfirmasi redeem selesai, `status='redeemed'`.

**API Table:**

| Method | Route | Request | Response |
|---|---|---|---|
| GET | `/api/v1/users/me/stamps` | - | `200 {total_stamps, stamps:[{merchant_name, awarded_at}]}` |
| GET | `/api/v1/promos/available` | - | `200 [{promo_id, merchant_name, title, discount, stamp_required}]` |
| POST | `/api/v1/promos/{id}/redeem` | - | `201 {redemption_code, expires_at}` |
| POST | `/api/v1/merchants/{id}/promo-redemptions/{code}/confirm` | - | `200 {status:"redeemed"}` |

**Edge cases wajib diantisipasi:**
- Transaksi yang di-log lebih dari sekali karena retry network FE → sudah dicegah via `client_reference_id` idempotency di Stage 3.4, pastikan `award_stamp` juga tidak double-trigger.
- User redeem promo tapi stamp count sebenarnya belum cukup (race condition jika 2 request redeem bersamaan pakai budget stamp yang sama) → gunakan **row lock (`SELECT ... FOR UPDATE`)** saat menghitung stamp available vs promo requirement dalam 1 transaction DB.
- Promo sudah `valid_until` terlewati saat user coba redeem → validasi di service, `400 PROMO_EXPIRED`.
- Redemption code dipakai 2x oleh merchant berbeda (kalau kode bocor) → `status` check sebelum confirm, sekali `redeemed` tidak bisa dipakai lagi, return `409`.
- Merchant yang bukan pemilik promo mencoba confirm kode → validasi ownership `merchant_id` di query.

---

### STAGE 3.8 — Alternative Credit Score (Financial Inclusion Data Layer)

**Tujuan:** Bab 3.1.2 — bangun data historis transaksi jadi skor kredit sederhana (read-model, bukan real lending).

**Step-by-step logic:**
1. Scheduled job bulanan: agregasi `transactions` per merchant → hitung `total_transaction_count`, `total_nominal`, `consistency_score` (misal: standar deviasi omzet harian dibanding rata-rata, makin stabil makin tinggi skor).
2. Simpan snapshot ke `credit_score_logs`.
3. `GET /merchants/{id}/credit-score` → merchant lihat skor & histori (untuk keperluan lampiran ke partner lembaga keuangan, sesuai Bab 3.2.5).

**API Table:**

| Method | Route | Request | Response |
|---|---|---|---|
| GET | `/api/v1/merchants/{id}/credit-score` | - | `200 {current_score, history:[{period, score}]}` |

**Edge cases wajib diantisipasi:**
- Merchant baru < 1 bulan data → skor ditandai `insufficient_data` bukan angka 0 (0 bisa disalahartikan sebagai "buruk").
- Transaksi `is_suspicious=true` (dari Stage 3.4) dikecualikan dari perhitungan skor agar tidak dimanipulasi merchant untuk menaikkan skor palsu.

---

### STAGE 3.9 — Admin & Notification Support Endpoints

- `GET /admin/dashboard/metrics` — total merchant aktif, total transaksi, total itinerary dibuat (untuk demo/monitoring).
- Push notification: gunakan Supabase Realtime/Firebase Cloud Messaging (di luar scope backend inti, tapi sediakan **event hook**: setiap `inventory_recommendations` baru & `stamp` baru terbentuk, publish message ke Redis pub/sub channel `notifications:{user_id}` yang dikonsumsi worker notifikasi terpisah).

### 3.10 Ringkasan Urutan Prioritas Pengerjaan (untuk tim 4 orang)

| Prioritas | Stage | Alasan |
|---|---|---|
| P0 | 3.1 Auth | Blocker semua fitur lain |
| P0 | 3.2 Merchant Onboarding | Data merchant wajib ada sebelum Dolan Mode bisa jalan |
| P0 | 3.6 Weighted Routing | Fitur inti demo Dolan Mode |
| P1 | 3.4 POS & Settlement | Blocker untuk gamification |
| P1 | 3.3 Predictive Stocking | Fitur inti demo Bakul Mode |
| P1 | 3.5 Event HITL | Data input untuk 3.3 & 3.6, bisa mulai dengan seed manual dulu |
| P2 | 3.7 Gamification | Depend on 3.4 |
| P3 | 3.8 Credit Score | Nice-to-have untuk demo impact |
| P3 | 3.9 Admin/Notif | Support tooling |

---

## PHASE 4 — Security, Testing, & Documentation

### 4.1 Security Baseline

- [ ] **CORS**: whitelist origin FE (React Native dev + production domain) di FastAPI `CORSMiddleware`, jangan gunakan `*` di production.
- [ ] **Auth/Authorization**: dependency `get_current_user` wajib di semua endpoint privat; tambahkan dependency `require_merchant_ownership(merchant_id)` untuk endpoint Bakul Mode agar user tidak bisa akses/edit merchant orang lain (cek `merchant.user_id == current_user.id`).
- [ ] **Admin-only routes**: dependency `require_admin_role` khusus `/admin/*`.
- [ ] **Rate limiting**: gunakan `slowapi`/Redis-based limiter untuk endpoint OTP, ingest (Gemini cost), dan itinerary generation.
- [ ] **Input validation**: seluruh request body via Pydantic schema dengan `strict` type & explicit bounds (lat/lng range, nominal > 0, dll) — cegah SQL/NoSQL injection secara struktural (ORM parametrized query, tidak pernah raw string interpolation).
- [ ] **Secrets management**: `.env` tidak pernah commit, gunakan GitHub Actions secrets / Supabase Vault untuk production.
- [ ] **PII & Location Privacy** (sesuai Bab 3.1.3 proposal): raw device coordinates HANYA dipakai untuk query proximity real-time, **tidak disimpan permanen** di tabel user — hanya simpan hasil agregat/anonymized untuk analytics B2G. Buat kolom `expires_at`/scheduled cleanup job untuk data lokasi mentah jika terpaksa disimpan sementara di cache.
- [ ] **CSRF**: karena API stateless berbasis Bearer token (bukan cookie session), risiko CSRF rendah — pastikan TIDAK menggunakan cookie-based auth tanpa CSRF token tambahan jika suatu saat beralih ke cookie.
- [ ] **File upload security**: validasi MIME type actual (bukan hanya ekstensi), scan ukuran, simpan di bucket privat dengan signed URL, bukan public bucket.

### 4.2 Testing Plan

**Prioritas testing mengikuti kompleksitas business logic (bukan sekadar coverage %):**

| Modul | Jenis Test | Fokus |
|---|---|---|
| Predictive Stocking (3.3) | Unit test | Semua kombinasi `M_event` x `M_weather` (termasuk edge: tidak ada event, cuaca API down, multiple event overlap) — buat test matrix eksplisit |
| Weighted Routing (3.6) | Unit test | `w1+w2+w3+w4==1.0` di semua skenario constraint; scoring dengan mocked candidate data; redemption partner multiplier 1.15x diterapkan benar |
| Weighted Routing (3.6) | Integration test | End-to-end dari raw_query → parsed constraint (mock Gemini) → candidate query (test DB dgn PostGIS) → OSRM (mock/stub) → response terurut benar |
| Auth OTP (3.1) | Unit + Integration | Single-use OTP, expiry, rate limit, token refresh rotation |
| Multimodal Ingestion (3.2) | Unit test | Parsing defensif terhadap LLM output malformed (mock berbagai response Gemini: JSON valid, JSON dengan fence, JSON invalid, empty) |
| POS & Stamp (3.4, 3.7) | Integration test | Idempotency `client_reference_id`; race condition redeem promo (concurrent request test dengan `asyncio.gather`) |
| Semua endpoint privat | Security test | Akses ke resource milik user lain harus `403`, bukan `404` yang bocor info atau `200` yang bocor data |

- [ ] Setup `pytest` dengan fixture: test DB terpisah (schema `test_blusukan`), auto-rollback per test.
- [ ] Mock semua external call (Gemini, OSRM, Weather API) di unit test — hanya integration test tertentu yang boleh hit sandbox/staging API sungguhan.
- [ ] Minimal coverage target: **90% untuk `modules/inventory`, `modules/routing`, `modules/gamification`** (business logic core), 70% untuk modul lain.
- [ ] CI wajib jalankan test suite di setiap PR ke `develop`/`main`, block merge jika gagal.

### 4.3 API Documentation

- [ ] Manfaatkan Swagger/OpenAPI otomatis dari FastAPI (`/docs`, `/redoc`) — pastikan semua schema Pydantic punya `Field(description=...)` yang jelas agar dokumentasi auto-generate informatif.
- [ ] Tambahkan `response_model` eksplisit di setiap route (jangan `response_model=dict`) agar contoh response di Swagger akurat.
- [ ] Tag routes per modul (`tags=["Auth"]`, `tags=["Bakul - Inventory"]`, dst) agar Swagger UI terorganisir sesuai Stage di atas.
- [ ] Buat file `docs/error_codes.md` berisi daftar custom error code (`OTP_EXPIRED`, `INVALID_LOCATION`, `PROMO_EXPIRED`, dll) beserta HTTP status dan penjelasan — dipakai FE untuk mapping pesan error ke Bahasa Indonesia yang ramah pengguna.
- [ ] Export Postman collection dari OpenAPI spec untuk kebutuhan QA manual saat demo.

### 4.4 Checklist Akhir Sebelum Demo/Rilis

- [ ] Seluruh endpoint di Phase 3 sudah punya test minimal happy-path + 2 edge case
- [ ] Environment staging berjalan via `docker-compose up` tanpa error
- [ ] Data seed realistis untuk demo (event Grebeg Sudiro contoh, 10+ merchant di sekitar Pasar Gede/Laweyan)
- [ ] Load test ringan endpoint `/itineraries` (target: response < 3 detik termasuk panggilan Gemini + OSRM)
- [ ] Review manual formula Bab 2.4.1 & 2.4.2 bersama tim (terutama catatan inkonsistensi `M_event` 0.10 vs "15%" di atas) sebelum dianggap final

---

**Selesai.** Dokumen ini adalah living document — update tiap Stage selesai dengan checklist tercentang dan link ke PR terkait.
