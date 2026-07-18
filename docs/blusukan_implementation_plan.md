# BLUSUKAN BACKEND — IMPLEMENTATION PLAN
**Versi:** 4.0 (Final)
**Tim:** 4 orang
**Convention Branch:** `feat/<modul>-<deskripsi>` (dari `develop`, merge kembali ke `develop`)

---

## ATURAN PENGERJAAN

- Sebelum merge ke `develop`, CI wajib *pass* (Unit Test dan Ruff linter lulus).
- Wajib me-raise exception menggunakan *class exception* kustom (dari `app/core/exceptions.py`), bukan `HTTPException` standar. Pesan error yang ditampilkan ke *Frontend* harus berbahasa Indonesia.
- Wajib membuat *Unit Test* di tiap selesai pengerjaan per *branch*.

1. **1 branch = 1 orang.** Anggota tim bebas mengklaim branch mana saja, asalkan dependensinya sudah terpenuhi.
2. **Cek dependensi sebelum mulai.** Jika branch yang menjadi prasyarat belum merge ke `develop`, tunggu dulu.
3. Ada **1 peran khusus: Maintainer**, yang bertanggung jawab atas `app/main.py`. Maintainer bebas dipegang siapa saja, tapi harus konsisten 1 orang selama project berlangsung. Tugasnya:
   - Mengerjakan `feat/core-infrastructure` dan `feat/auth-otp-jwt` (dua branch blocker utama).
   - **Menjadi satu-satunya orang yang menambahkan baris `app.include_router(...)` ke `app/main.py`** — dilakukan setiap kali ada branch baru yang merge ke `develop`, untuk menghindari conflict.
   - Review PR setiap branch sebelum merge ke `develop`.
   - Deploy ke staging.

---

## DAFTAR BRANCH & DEPENDENSI

> **Cara membaca kolom Dependensi:** Branch yang tertulis di kolom itu wajib sudah merge ke `develop` sebelum kamu boleh mulai branch ini.

| # | Branch | Dependensi (harus merge dulu) | Diklaim oleh |
|---|--------|-------------------------------|--------------|
| 1 | `feat/core-infrastructure` | ❌ Tidak ada | *(Maintainer)* |
| 2 | `feat/auth-email-jwt` | `feat/core-infrastructure` | *(Maintainer)* |
| 3 | `feat/merchant-onboarding-ingestion` | `feat/auth-email-jwt` | |
| 4 | `feat/events-admin-hitl` | `feat/auth-email-jwt` | |
| 5 | `feat/inventory-predictive-stock` | `feat/merchant-onboarding-ingestion` + `feat/events-admin-hitl` | |
| 6 | `feat/routing-itinerary-generation` | `feat/auth-email-jwt` + `feat/merchant-onboarding-ingestion` | |
| 7 | `feat/pos-gamification` | `feat/merchant-onboarding-ingestion` + `feat/routing-itinerary-generation` | |
| 8 | `feat/credit-score-support` | `feat/pos-gamification` | |

---

## DEPENDENCY MAP (Visual)

```
feat/core-infrastructure
    │
    │  [SEMUA ORANG TUNGGU INI]
    ▼
feat/auth-otp-jwt
    │
    ├──────────────────────────────────────┐
    ▼                                      ▼
feat/merchant-onboarding-ingestion    feat/events-admin-hitl
    │                                      │
    ├────────────────────┐                 │
    │                    │                 ▼
    │                    │  feat/inventory-predictive-stock
    │                    │  [tunggu: feat/merchant-onboarding-ingestion
    │                    │           + feat/events-admin-hitl]
    │                    │
    ▼                    ▼
feat/routing-itinerary-generation    feat/pos-gamification
[tunggu: feat/auth-otp-jwt           [tunggu: feat/merchant-onboarding-ingestion
 + feat/merchant-onboarding-ingestion         + feat/routing-itinerary-generation]
]                                             │
                                              ▼
                                    feat/credit-score-support
                                    [tunggu: feat/pos-gamification]
```

**Urutan merge ke `develop` yang aman:**
```
1. feat/core-infrastructure
2. feat/auth-otp-jwt
3. feat/merchant-onboarding-ingestion  ─┐ bisa paralel
4. feat/events-admin-hitl              ─┘
5. feat/routing-itinerary-generation   ─┐ bisa paralel setelah no.3 selesai
5. feat/inventory-predictive-stock     ─┘ (inventory butuh no.3 + no.4)
6. feat/pos-gamification                  setelah no.3 + no.5 (routing) selesai
7. feat/credit-score-support              setelah no.6 selesai
```

---

## ✅ PHASE 0 — Foundation (SUDAH SELESAI, di `main`)

| Status | Item |
|--------|------|
| ✅ | Struktur folder modular monolith |
| ✅ | `Dockerfile` + `docker-compose.yml` |
| ✅ | `.env.example` (Supabase + Upstash format) |
| ✅ | `app/main.py` (FastAPI + APIRouter prefix `/api` + Swagger `/api/docs`) |
| ✅ | `.github/workflows/ci.yml` |
| ✅ | `README.md` |

---

## 🔧 BRANCH 1: `feat/core-infrastructure`
**Dikerjakan oleh:** Maintainer
**Estimasi:** 3–4 jam
**Dependensi Branch:** ❌ Tidak ada — ini yang pertama dikerjakan
**File yang disentuh (EKSKLUSIF):**
- `app/core/config.py`
- `app/core/exceptions.py`
- `app/core/logging.py`
- `app/core/security.py` ← hanya helper (hash, verify) — JWT/OTP logic di Branch auth
- `app/db/base.py`
- `app/db/session.py`
- `alembic.ini`
- `app/db/migrations/env.py`
- `scripts/init_postgis.sql`

### Isi `app/core/config.py`
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_ENV: str = "development"
    DATABASE_URL: str
    SUPABASE_URL: str
    SUPABASE_SERVICE_ROLE_KEY: str
    SUPABASE_ANON_KEY: str
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    GEMINI_API_KEY: str
    GEMINI_MODEL_TEXT: str = "gemini-2.5-flash"
    GEMINI_MODEL_VISION: str = "gemini-2.5-flash"
    GEMINI_EMBEDDING_MODEL: str = "text-embedding-004"
    REDIS_URL: str
    CELERY_BROKER_URL: str
    WEATHER_API_KEY: str
    OSRM_BASE_URL: str = "http://localhost:5000"
    SUPABASE_STORAGE_BUCKET_MENU: str = "merchant-menus"
    SUPABASE_STORAGE_BUCKET_VOICE: str = "merchant-voicenotes"
    MAX_UPLOAD_SIZE_BYTES: int = 10 * 1024 * 1024

    class Config:
        env_file = ".env"

settings = Settings()
```

### Isi `app/core/exceptions.py`
Custom exception classes. Global handler didaftarkan di `app/main.py` setelah branch ini merge.

| Exception Class | HTTP Code | Error Code String |
|----------------|-----------|-------------------|
| `OTPExpiredException` | 400 | `OTP_EXPIRED` |
| `OTPRateLimitException` | 429 | `OTP_RATE_LIMIT` |
| `InvalidLocationException` | 400 | `INVALID_LOCATION` |
| `InsufficientBudgetException` | 400 | `INSUFFICIENT_BUDGET` |
| `PromoExpiredException` | 400 | `PROMO_EXPIRED` |
| `MerchantOwnershipException` | 403 | `FORBIDDEN_NOT_OWNER` |
| `DuplicateStampException` | 409 | `STAMP_ALREADY_AWARDED` |
| `TokenReuseDetectedException` | 401 | `TOKEN_REUSE_DETECTED` |
| `IngestLimitReachedException` | 429 | `INGEST_LIMIT_REACHED` |

### Isi `app/db/session.py`
```python
# AsyncEngine → AsyncSessionMaker
# Expose: get_db() dependency (async generator untuk FastAPI Depends)
```

### Isi `scripts/init_postgis.sql`
```sql
-- Jalankan SEKALI di Supabase SQL Editor sebelum Alembic migration
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
```

### Checklist Merge ke `develop`
- [ ] `from app.core.config import settings` tidak error
- [ ] `get_db()` menghasilkan `AsyncSession` valid
- [ ] `alembic upgrade head` jalan tanpa error
- [ ] Seluruh tim bisa `git pull develop` dan langsung mulai ngoding branch masing-masing

---

## 🔐 BRANCH 2: `feat/auth-email-jwt`
**Dikerjakan oleh:** Dev Lead
**Estimasi:** 3–4 jam
**Dependensi Branch:** `feat/core-infrastructure` harus sudah merge ke `develop`
**File yang disentuh (EKSKLUSIF):**
- `app/modules/auth/models.py`
- `app/modules/auth/schemas.py`
- `app/modules/auth/service.py`
- `app/modules/auth/router.py`
- `app/modules/auth/__init__.py`
- `app/modules/auth/dependencies.py` ← `get_current_user`, `require_admin`
- `app/db/migrations/versions/[hashed]_create_users_refresh_tokens.py`
- `tests/unit/test_auth_service.py`

### Skema Database

**Tabel `users`:**
| Kolom | Tipe | Keterangan |
|-------|------|------------|
| id | UUID PK | `gen_random_uuid()` |
| email | VARCHAR(255) UNIQUE NOT NULL | |
| hashed_password | VARCHAR NOT NULL | Simpan bcrypt hash dari password |
| full_name | VARCHAR(150) NULLABLE | |
| role | ENUM('wisatawan','pedagang','admin') | Role default UI, bukan hard access control |
| has_merchant_profile | BOOLEAN DEFAULT false | Flag akses Bakul Mode |
| created_at | TIMESTAMPTZ DEFAULT now() | |
| updated_at | TIMESTAMPTZ | |

**Tabel `refresh_tokens`:**
| Kolom | Tipe | Keterangan |
|-------|------|------------|
| id | UUID PK | |
| user_id | UUID FK → users.id | |
| token_hash | VARCHAR NOT NULL | Simpan bcrypt hash, JANGAN raw token |
| expires_at | TIMESTAMPTZ | |
| revoked_at | TIMESTAMPTZ NULLABLE | |
| created_at | TIMESTAMPTZ | |

### Business Logic Auth

**Flow Register:**
1. Validasi format Email dan panjang password (min. 8 karakter) di Pydantic schema.
2. Cek apakah email sudah terdaftar. Jika ya → `400 EMAIL_ALREADY_EXISTS`.
3. Hash password menggunakan bcrypt.
4. Insert user baru ke database.
5. Generate `access_token` (JWT, 60 menit) + `refresh_token` (random 64-char hex, simpan bcrypt hash ke DB).
6. Return access_token + refresh_token + user object.

**Flow Login:**
1. Cari user berdasarkan email. Jika tidak ada → `401 INVALID_CREDENTIALS`.
2. Verifikasi bcrypt hash password. Jika tidak cocok → `401 INVALID_CREDENTIALS`.
3. Generate `access_token` (JWT, 60 menit) + `refresh_token` (random 64-char hex, simpan bcrypt hash ke DB).
4. Return access_token + refresh_token + user object.

**JWT Payload:**
```json
{"sub": "user_uuid", "role": "wisatawan", "has_merchant_profile": false, "exp": 1234567890}
```

**Flow Refresh Token:**
1. Hash token yang diterima → query `refresh_tokens` table.
2. Jika tidak ditemukan / expired → `401`.
3. Jika ditemukan tapi `revoked_at` tidak NULL → **token reuse detected** → revoke SEMUA token user + log security event → `401 TOKEN_REUSE_DETECTED`.
4. Revoke token lama → issue token baru (rotasi) → return.

### Dependency yang Wajib Diekspor (dipakai semua branch lain)

```python
# app/modules/auth/dependencies.py

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User:
    # Decode JWT → query user dari DB → raise 401 jika invalid

async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    # Cek current_user.role == 'admin' → raise 403 jika bukan
```

> **Catatan untuk semua Developer:** Import `get_current_user` dan `require_admin` dari path ini untuk endpoint yang butuh auth.

### API Endpoints

| Method | Route | Body | Response | Auth |
|--------|-------|------|----------|------|
| POST | `/api/auth/register` | `{email, password, full_name?}` | `201 {access_token, refresh_token, user}` | ❌ |
| POST | `/api/auth/login` | `{email, password}` | `200 {access_token, refresh_token, user}` | ❌ |
| POST | `/api/auth/refresh` | `{refresh_token}` | `200 {access_token, refresh_token}` | ❌ |
| GET | `/api/auth/me` | — | `200 {id, email, full_name, has_merchant_profile, role}` | ✅ Bearer |
| PATCH | `/api/auth/me` | `{full_name?}` | `200 {user}` | ✅ Bearer |
| POST | `/api/auth/logout` | `{refresh_token}` | `204` | ✅ Bearer |

### Edge Cases Wajib Ditangani
- Email sudah terdaftar saat register → `400`
- Password salah saat login → `401 INVALID_CREDENTIALS` (pesan harus sama baik saat email salah/password salah demi keamanan)
- Refresh token revoked tapi dipakai lagi → invalidasi semua sesi user
- Akses endpoint privat tanpa token → `401` bukan `403`

### Checklist Merge ke `develop`
- [ ] Register berhasil (password tersimpan sebagai hash)
- [ ] Login berhasil → JWT + refresh token direturn
- [ ] Validasi error `INVALID_CREDENTIALS` berfungsi
- [ ] Refresh token rotation berfungsi
- [ ] Dependency `get_current_user` bisa diimport modul lain
- [ ] Unit test `tests/unit/test_auth_service.py` coverage ≥ 90%

---

## 🏪 BRANCH 3: `feat/merchant-onboarding-ingestion`
**Dikerjakan oleh:** Developer 1
**Estimasi:** 6–8 jam
**Dependensi Branch:** `feat/auth-otp-jwt` harus sudah merge ke `develop`
**File yang disentuh (EKSKLUSIF):**
- `app/modules/merchants/models.py`
- `app/modules/merchants/schemas.py`
- `app/modules/merchants/service.py`
- `app/modules/merchants/router.py`
- `app/modules/merchants/__init__.py`
- `app/modules/merchants/dependencies.py` ← `require_merchant_ownership`
- `app/modules/ingestion/service.py`
- `app/modules/ingestion/schemas.py`
- `app/modules/ingestion/__init__.py`
- `app/integrations/gemini_client.py`
- `app/integrations/supabase_storage.py`
- `app/db/migrations/versions/[hashed]_create_merchants_catalog.py`
- `tests/unit/test_ingestion_service.py`

### Deskripsi Fitur
> Merchant mikro bisa onboarding hanya dengan memfoto menu atau merekam suara. Gemini Vision/STT mengekstrak data produk secara otomatis. Merchant mengkonfirmasi hasilnya (HITL kecil sisi user), lalu data tersimpan sebagai katalog digital dengan embedding pgvector untuk digunakan oleh Routing Engine.

### Skema Database

**Tabel `merchant_profiles`:**
| Kolom | Tipe | Keterangan |
|-------|------|------------|
| id | UUID PK | |
| user_id | UUID FK → users.id | |
| business_name | VARCHAR(150) NOT NULL | |
| category | VARCHAR(50) | `culinary`, `hot_culinary`, `cold_beverage`, `cold_beverage_dessert`, `craft`, `batik`, `outdoor_retail` |
| description | TEXT | |
| location | GEOGRAPHY(Point, 4326) | PostGIS — index GIST wajib |
| address_text | TEXT | |
| is_redemption_partner | BOOLEAN DEFAULT false | Priority visibility di Routing |
| baseline_rating | NUMERIC(2,1) DEFAULT 4.0 | Cold-start default |
| review_count | INTEGER DEFAULT 0 | Untuk HiddenGemIndex |
| baseline_inventory | JSONB | `{"category_key": qty_per_day}` — dipakai Branch inventory |
| qris_image_url | TEXT NULLABLE | |
| status | ENUM('pending','active','suspended') | |
| daily_ingest_count | INTEGER DEFAULT 0 | Anti-abuse Gemini quota |
| ingest_count_reset_at | DATE | Reset tiap hari |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

```sql
CREATE INDEX idx_merchant_location ON merchant_profiles USING GIST(location);
```

**Tabel `merchant_catalog_items`:**
| Kolom | Tipe | Keterangan |
|-------|------|------------|
| id | UUID PK | |
| merchant_id | UUID FK | |
| item_name | VARCHAR(150) | |
| price | NUMERIC(10,2) NULLABLE | NULL jika tidak bisa diekstrak |
| category | VARCHAR(50) | |
| description_raw | TEXT | |
| embedding | VECTOR(768) | pgvector |
| image_url | TEXT NULLABLE | |
| source_type | ENUM('photo','voice','manual') | |
| confidence | ENUM('high','low') | 'low' jika price NULL |
| created_at | TIMESTAMPTZ | |

```sql
CREATE INDEX idx_catalog_embedding ON merchant_catalog_items USING ivfflat (embedding vector_cosine_ops);
```

### Business Logic

**Cara Kerja Onboarding (Step-by-Step):**
1. `POST /api/merchants` → buat `merchant_profiles` status `pending` → set `user.has_merchant_profile = true`.
2. `POST /api/merchants/{id}/catalog/ingest` (multipart):
   - Reject file > 10MB **sebelum** dikirim ke Gemini (hemat quota).
   - Upload raw file ke Supabase Storage (private bucket).
   - Jika foto → `gemini_client.extract_text_from_image()`.
   - Jika audio → `gemini_client.speech_to_text()`.
   - `gemini_client.structure_menu_text(raw_text)` → JSON schema ketat `[{item_name, price?, category}]`.
   - **Parsing defensif:** strip markdown fence, try JSON parse, jika gagal → `422`.
   - Jika `draft_items` kosong (foto blur/audio noise) → return `200 {draft_items: [], message: "..."}` bukan 500.
   - Return `draft_items` ke FE untuk konfirmasi merchant.
3. `POST /api/merchants/{id}/catalog/confirm` → merchant submit hasil edit → generate embedding per item → commit ke DB → `status = 'active'` jika ≥ 1 item.

**Aturan Bisnis:**
- Harga NULL → `confidence: "low"`, merchant wajib isi manual (jangan auto-fill 0)
- Max 20x ingest/hari per merchant → counter `daily_ingest_count`
- GPS di luar bounding box Solo Raya (lat: -7.8 s.d. -7.4, lng: 110.5 s.d. 110.9) → `400 INVALID_LOCATION`
- Merchant hanya bisa akses merchant miliknya sendiri (`require_merchant_ownership`)

### `app/integrations/gemini_client.py` (dibuat di branch ini, dipakai branch lain)
```python
class GeminiClient:
    # Semua method wajib: retry max 3x, exponential backoff, timeout 30 detik
    def extract_text_from_image(self, file_bytes: bytes) -> str: ...
    def speech_to_text(self, file_bytes: bytes) -> str: ...
    def structure_menu_text(self, raw_text: str) -> list[dict]: ...
    def embed_text(self, text: str) -> list[float]: ...  # 768-dim
    def parse_constraints(self, raw_query: str) -> dict: ...  # dipakai feat/routing
    def generate_stock_advice(self, context: dict) -> str: ...  # dipakai feat/inventory
```

### Dependency yang Diekspor (dipakai Branch pos-gamification dan routing)
```python
# app/modules/merchants/dependencies.py
async def require_merchant_ownership(merchant_id: UUID, current_user: User = Depends(get_current_user), db=Depends(get_db)) -> MerchantProfile:
    # Query merchant → cek merchant.user_id == current_user.id
    # Jika bukan owner → raise 403 (BUKAN 404, cegah info leakage)
```

### API Endpoints

| Method | Route | Body | Response | Auth |
|--------|-------|------|----------|------|
| POST | `/api/merchants` | `{business_name, category, description, latitude, longitude, address_text}` | `201 {merchant_id, status:"pending"}` | ✅ Bearer |
| GET | `/api/merchants/{id}` | — | `200 {merchant + catalog_items}` | ✅ Bearer |
| PATCH | `/api/merchants/{id}` | field opsional | `200 {merchant}` | ✅ Owner |
| POST | `/api/merchants/{id}/catalog/ingest` | multipart: `file`, `source_type` | `200 {draft_items:[{item_name, price, category, confidence}]}` | ✅ Owner |
| POST | `/api/merchants/{id}/catalog/confirm` | `{items:[{item_name, price, category}]}` | `201 {saved_count}` | ✅ Owner |
| PATCH | `/api/merchants/{id}/redemption-partner` | `{is_redemption_partner: bool}` | `200 {merchant_id, is_redemption_partner}` | ✅ Owner |
| GET | `/api/merchants` | `?lat&lng&radius` | `200 [merchants]` | ❌ Public |

### Edge Cases Wajib Ditangani
- LLM JSON tidak valid → strip fence, try parse, fallback `422`
- Harga NULL → `confidence: "low"`, jangan auto-fill 0
- Foto blur → `draft_items: []` bukan error 500
- File > 10MB → reject di middleware sebelum sampai Gemini
- Ingest > 20x/hari → `429 INGEST_LIMIT_REACHED`
- GPS tidak valid → `400 INVALID_LOCATION`
- Akses merchant milik orang lain → `403`

### Checklist Merge ke `develop`
- [ ] Onboarding via foto menu berhasil
- [ ] Draft items dikembalikan ke FE untuk konfirmasi
- [ ] `catalog/confirm` simpan item + embedding ke DB
- [ ] `merchant.status = 'active'` setelah confirm
- [ ] Rate limit 20x ingest/hari berfungsi
- [ ] `require_merchant_ownership` bisa diimport branch lain
- [ ] `gemini_client.py` bisa diimport branch lain
- [ ] Unit test parsing JSON malformed pass

---

## 📅 BRANCH 4: `feat/events-admin-hitl`
**Dikerjakan oleh:** Developer 2
**Estimasi:** 4–5 jam
**Dependensi Branch:** `feat/auth-otp-jwt` harus sudah merge ke `develop` (butuh `require_admin`)
**File yang disentuh (EKSKLUSIF):**
- `app/modules/events/models.py`
- `app/modules/events/schemas.py`
- `app/modules/events/service.py`
- `app/modules/events/router.py`
- `app/modules/events/__init__.py`
- `app/modules/admin/router.py`
- `app/modules/admin/__init__.py`
- `app/db/migrations/versions/[hashed]_create_events.py`
- `tests/unit/test_events_service.py`

### Deskripsi Fitur
> Admin memasukkan data event (konser, festival, olahraga) secara manual via dashboard admin. Tidak ada scraper otomatis. Setiap event wajib di-review admin sebelum `status='approved'`. Event yang approved digunakan sebagai input kalkulasi Predictive Stocking.

### Skema Database

**Tabel `events`:**
| Kolom | Tipe | Keterangan |
|-------|------|------------|
| id | UUID PK | |
| name | VARCHAR(200) NOT NULL | |
| genre | VARCHAR(50) | `cultural`, `sports`, `convention`, `concert`, `festival` |
| location | GEOGRAPHY(Point, 4326) | |
| venue_name | VARCHAR(150) | |
| estimated_attendee_count | INTEGER NOT NULL | Wajib diisi admin |
| start_datetime | TIMESTAMPTZ NOT NULL | |
| end_datetime | TIMESTAMPTZ NOT NULL | |
| status | ENUM('pending_review','approved','rejected') | Tidak ada auto-approve |
| reviewed_by_admin_id | UUID FK NULLABLE → users.id | |
| created_at | TIMESTAMPTZ | |

### Business Logic

**Cara Kerja:**
1. Admin input event manual → `status = 'pending_review'`.
2. Admin review daftar pending dari dashboard.
3. Admin approve/reject/edit field → jika `approved`, event masuk perhitungan Branch inventory pada run berikutnya.

**Aturan Bisnis:**
- `end_datetime` harus setelah `start_datetime` → validasi Pydantic
- `estimated_attendee_count` tidak boleh NULL saat create
- Event dengan `end_datetime < now()` dan status `pending_review` → auto-expire (di-handle oleh Celery job di Branch inventory)
- Hanya admin yang bisa create/approve/reject
- Public endpoint hanya return `status='approved'` yang belum lewat

### API Endpoints

| Method | Route | Body | Response | Auth |
|--------|-------|------|----------|------|
| POST | `/api/admin/events` | `{name, genre, latitude, longitude, venue_name, estimated_attendee_count, start_datetime, end_datetime}` | `201 {event_id, status:"pending_review"}` | ✅ Admin |
| GET | `/api/admin/events` | `?status=pending_review` | `200 [events]` | ✅ Admin |
| PATCH | `/api/admin/events/{id}/review` | `{action:"approve"\|"reject", edited_fields?}` | `200 {event}` | ✅ Admin |
| GET | `/api/events` | `?upcoming=true` | `200 [events]` (hanya approved & belum lewat) | ❌ Public |
| GET | `/api/events/{id}` | — | `200 {event}` | ❌ Public |

### Edge Cases Wajib Ditangani
- `end_datetime` sebelum `start_datetime` → `400 INVALID_DATE_RANGE`
- Non-admin akses `/api/admin/*` → `403`
- Event sudah lewat tapi belum di-review → return status `expired` di response

### Checklist Merge ke `develop`
- [ ] Admin bisa create event manual
- [ ] Admin bisa approve/reject event
- [ ] Public hanya lihat event approved & belum lewat
- [ ] Non-admin dapat `403` di semua `/api/admin/events/*`

---

## 📦 BRANCH 5: `feat/inventory-predictive-stock`
**Dikerjakan oleh:** Developer 2
**Estimasi:** 6–7 jam
**Dependensi Branch:**
- `feat/events-admin-hitl` harus sudah merge ke `develop` (butuh event model)
- `feat/merchant-onboarding-ingestion` harus sudah merge ke `develop` (butuh merchant data)
**File yang disentuh (EKSKLUSIF):**
- `app/modules/inventory/models.py`
- `app/modules/inventory/schemas.py`
- `app/modules/inventory/service.py`
- `app/modules/inventory/router.py`
- `app/modules/inventory/__init__.py`
- `app/modules/inventory/calculator.py` ← formula deterministik
- `app/workers/celery_app.py`
- `app/workers/tasks_stock_recalc.py`
- `app/integrations/weather_client.py`
- `app/db/migrations/versions/[hashed]_create_inventory_recommendations.py`
- `tests/unit/test_inventory_calculator.py` ← coverage ≥ 90%

### Deskripsi Fitur
> Setiap hari jam 03.00 WIB, Celery job menghitung rekomendasi stok untuk semua merchant aktif menggunakan formula deterministik (bukan LLM). Gemini hanya mengubah angka final menjadi kalimat saran (NLG layer saja). Merchant melihat rekomendasi di dashboard pagi.

### Skema Database

**Tabel `inventory_recommendations`:**
| Kolom | Tipe | Keterangan |
|-------|------|------------|
| id | UUID PK | |
| merchant_id | UUID FK | |
| event_id | UUID FK NULLABLE | Event yang paling berpengaruh |
| s_baseline | NUMERIC NOT NULL | |
| m_event | NUMERIC DEFAULT 0 | |
| m_weather | NUMERIC DEFAULT 0 | |
| s_predicted | NUMERIC NOT NULL | Sudah di-clamp ≥ 0 |
| weather_condition | VARCHAR(50) | |
| message_text | TEXT | Output NLG Gemini |
| generated_for_date | DATE NOT NULL | |
| generated_at | TIMESTAMPTZ | |

```sql
UNIQUE(merchant_id, generated_for_date)  -- cegah duplicate job run
```

### Business Logic: Formula Deterministik (di `calculator.py`)

```python
# ================================================================
# ENGINEERING DECISION LOG
# M_event: implementasikan angka dari RUMUS (0.10), bukan dari
# narasi ("+15%"). Inkonsistensi ini dicatat sebagai technical debt.
# Multi-event: ambil M_event MAKSIMUM, bukan dijumlahkan.
# ================================================================

def calculate_m_event(attendee_count: int | None, distance_m: float) -> float:
    """Lookup table M_event berdasarkan jumlah attendee dan jarak."""
    if attendee_count is None:
        return 0
    if attendee_count > 5000 and distance_m < 1000:
        return 0.30
    elif 1000 <= attendee_count <= 5000 and distance_m < 1000:
        return 0.10  # Rumus, bukan narasi "+15%"
    elif attendee_count > 5000 and 1000 <= distance_m <= 3000:
        return 0.10
    return 0

def calculate_m_weather(weather_condition: str, merchant_category: str) -> float:
    """Lookup table M_weather berdasarkan cuaca dan kategori merchant."""
    table = {
        ("heavy_rain", "hot_culinary"): 0.15,
        ("heavy_rain", "cold_beverage_dessert"): -0.20,
        ("heavy_rain", "outdoor_retail"): -0.30,
        ("sunny", "cold_beverage"): 0.25,
        ("hot", "cold_beverage"): 0.25,
    }
    return table.get((weather_condition, merchant_category), 0)

def calculate_s_predicted(s_baseline: float, m_event: float, m_weather: float) -> float:
    """Hitung S_predicted dan clamp ke >= 0 (cegah nilai negatif)."""
    return max(s_baseline * (1 + m_event + m_weather), 0)
```

**Default S_baseline per kategori (jika merchant belum set):**
```python
BASELINE_DEFAULTS = {
    "culinary": 50,
    "hot_culinary": 50,
    "cold_beverage": 80,
    "cold_beverage_dessert": 60,
    "craft": 20,
    "batik": 15,
    "outdoor_retail": 30,
}
```

**Cara Kerja Celery Job (`tasks_stock_recalc.py`):**
1. Trigger: Celery beat setiap hari 03.00 WIB.
2. Ambil semua merchant `status='active'`.
3. Per merchant (batching `asyncio.Semaphore(10)` — batas concurrency Gemini):
   - Ambil `S_baseline` dari `baseline_inventory`. Jika kosong → pakai `BASELINE_DEFAULTS`.
   - Query event terdekat: `status='approved'`, dalam H-3 s.d. H+1, `ST_Distance(merchant.location, event.location) <= 3000m`.
   - Jika multi-event → ambil `M_event` **maksimum**.
   - Fetch cuaca dari Weather API (cache Redis per kecamatan 1 jam).
   - Hitung `M_weather`.
   - Hitung `S_predicted`, clamp ke ≥ 0.
   - Generate kalimat saran via Gemini NLG (ubah angka jadi teks, BUKAN kalkulasi ulang).
   - Upsert ke `inventory_recommendations` (handle `UNIQUE` constraint).

### API Endpoints

| Method | Route | Body | Response | Auth |
|--------|-------|------|----------|------|
| GET | `/api/merchants/{id}/inventory-recommendations/today` | — | `200 {s_baseline, m_event, m_weather, s_predicted, message_text, event_context, generated_for_date}` | ✅ Owner |
| GET | `/api/merchants/{id}/inventory-recommendations/history` | `?limit=7` | `200 [{date, s_predicted, message_text}]` | ✅ Owner |
| PATCH | `/api/merchants/{id}/baseline-inventory` | `{category_key: qty}` | `200 {baseline_inventory}` | ✅ Owner |
| POST | `/api/admin/inventory-recommendations/recalculate` | `{merchant_id?}` | `202 {job_id}` | ✅ Admin |

### Unit Test Matrix Wajib

| Skenario | S_baseline | M_event | M_weather | Expected S_predicted |
|----------|------------|---------|-----------|----------------------|
| Attendee 6000, jarak 500m, no weather effect | 50 | 0.30 | 0 | 65 |
| Attendee 3000, jarak 500m, no weather effect | 50 | 0.10 | 0 | 55 |
| No event, heavy_rain + outdoor_retail | 50 | 0 | -0.30 | 35 |
| No event, hot weather + cold_beverage | 80 | 0 | 0.25 | 100 |
| Event (M=0.30) + heavy_rain outdoor_retail (-0.30) | 50 | 0.30 | -0.30 | 50 |
| Multiple event (M=0.30 & M=0.10) → ambil max | 50 | 0.30 | 0 | 65 |
| Weather API down → fallback M_weather=0 | 50 | 0.10 | 0 | 55 |
| Extreme minus combo → clamp ke 0 | 10 | 0 | -1.5 | 0 (bukan negatif) |
| `attendee_count = NULL` → M_event=0 | 50 | 0 | 0 | 50 |

### Edge Cases Wajib Ditangani
- `baseline_inventory` kosong → pakai `BASELINE_DEFAULTS`, JANGAN 0
- Weather API down → `M_weather = 0`, job tetap jalan
- Tidak ada event dalam radius → `M_event = 0`, tampilkan kalimat "tidak ada event besar"
- `attendee_count = NULL` → `M_event = 0`
- Duplicate job run hari yang sama → upsert dengan `UNIQUE` constraint
- Ratusan merchant → `asyncio.Semaphore(10)` batas concurrency

### Checklist Merge ke `develop`
- [ ] Formula `calculate_m_event` sesuai tabel, termasuk multi-event max
- [ ] Formula `calculate_m_weather` sesuai tabel
- [ ] `S_predicted` tidak pernah negatif (clamp berfungsi)
- [ ] Weather API down → fallback 0, job tidak gagal
- [ ] Celery beat job terdaftar (`tasks_stock_recalc`)
- [ ] Semua skenario unit test matrix pass

---

## 🗺️ BRANCH 6: `feat/routing-itinerary-generation`
**Dikerjakan oleh:** Developer 3
**Estimasi:** 8–10 jam
**Dependensi Branch:**
- `feat/auth-otp-jwt` harus sudah merge ke `develop`
- `feat/merchant-onboarding-ingestion` harus sudah merge ke `develop` (butuh merchant data + embedding + `gemini_client.parse_constraints()`)
**File yang disentuh (EKSKLUSIF):**
- `app/modules/routing/models.py`
- `app/modules/routing/schemas.py`
- `app/modules/routing/service.py`
- `app/modules/routing/router.py`
- `app/modules/routing/__init__.py`
- `app/modules/routing/scoring.py` ← SAW formula
- `app/modules/routing/weight_presets.py` ← tabel bobot preset
- `app/integrations/osrm_client.py`
- `app/db/migrations/versions/[hashed]_create_itineraries.py`
- `tests/unit/test_routing_scoring.py` ← coverage ≥ 90%

### Deskripsi Fitur
> Wisatawan input kebutuhan bahasa alami. Gemini parsing constraint, sistem scoring SAW per merchant kandidat (PostGIS + pgvector + hidden gem index + rating), generate itinerary terurut, OSRM hitung rute jalan kaki. Ini fitur inti demo Dolan Mode.

### Formula SAW (Simple Additive Weighting)
1. **Normalisasi Matriks (Benefit/Cost):**
   - Benefit: $r_{ij} = \frac{x_{ij}}{\max_i x_{ij}}$
   - Cost: $r_{ij} = \frac{\min_i x_{ij}}{x_{ij}}$
2. **Perhitungan Skor Akhir:**
   - $V_i = \sum_{j=1}^n w_j r_{ij}$

### Skema Database

**Tabel `itineraries`:**
| Kolom | Tipe | Keterangan |
|-------|------|------------|
| id | UUID PK | |
| user_id | UUID FK | |
| raw_query | TEXT NOT NULL | Input asli bahasa alami |
| parsed_constraints | JSONB | `{time_limit_minutes, budget_idr, search_radius_meter, interest_categories, avoid_crowds}` |
| waypoints | JSONB | `[{merchant_id, name, score, score_breakdown, order}]` |
| route_geojson | JSONB | Output OSRM |
| estimated_duration_minutes | INTEGER | |
| status | ENUM('draft','active','completed') | |
| created_at | TIMESTAMPTZ | |

### Business Logic: SAW Scoring (`scoring.py`)

```python
# ================================================================
# ENGINEERING DECISION LOG — wajib ada sebagai code comment
# ================================================================
# 1. Term Distance: implementasi w3 × Distance_normalized (Opsi A)
#    BUKAN 1/Distance seperti literal proposal. Alasan: jika
#    1/Distance_normalized dipakai literal, merchant paling jauh
#    (Distance_norm → 0) menghasilkan score → ∞ (berlawanan tujuan).
#    Opsi A konsisten dengan definisi variabel Distance yang sudah
#    dinormalisasi di proposal.
# 2. Bobot w1-w4: rule-based lookup table (weight_presets.py)
#    untuk MVP — deterministik & mudah diuji.
# 3. HiddenGemIndex = 1 - min(review_count / MAX_THRESHOLD, 1)
#    MAX_THRESHOLD default 100 (bootstrap), idealnya P90 dari DB.
# 4. Multi-event M_event: ambil MAKSIMUM (keputusan desain).
# ================================================================

def calculate_hidden_gem_index(review_count: int, max_threshold: int = 100) -> float:
    return 1 - min(review_count / max_threshold, 1)

def calculate_distance_norm(distance_m: float, max_radius_m: float) -> float:
    return max(1 - (distance_m / max_radius_m), 0)  # clamp ke [0,1]

def calculate_rating_norm(rating: float) -> float:
    return rating / 5.0

def calculate_saw_score(
    hidden_gem_index: float,
    category_match: float,
    distance_norm: float,
    rating_norm: float,
    weights: dict,
    is_redemption_partner: bool
) -> float:
    score = (
        weights["w1"] * hidden_gem_index +
        weights["w2"] * category_match +
        weights["w3"] * distance_norm +
        weights["w4"] * rating_norm
    )
    if is_redemption_partner:
        score *= 1.15
    return score
```

**`weight_presets.py` — Tabel Bobot:**
```python
WEIGHT_PRESETS = {
    "default":           {"w1": 0.25, "w2": 0.25, "w3": 0.25, "w4": 0.25},
    "avoid_crowds":      {"w1": 0.40, "w2": 0.20, "w3": 0.20, "w4": 0.20},
    "rush":              {"w1": 0.15, "w2": 0.20, "w3": 0.45, "w4": 0.20},
    "specific_category": {"w1": 0.15, "w2": 0.50, "w3": 0.20, "w4": 0.15},
}

def get_weights(parsed_constraints: dict) -> dict:
    """Pilih preset, normalisasi wajib agar sum == 1.0."""
    weights = WEIGHT_PRESETS["default"].copy()
    if parsed_constraints.get("avoid_crowds"):
        weights = WEIGHT_PRESETS["avoid_crowds"].copy()
    if parsed_constraints.get("time_limit_minutes", 999) < 120:
        # Rata-ratakan dengan rush jika kombinasi, lalu normalisasi
        ...
    # SELALU normalisasi setelah assignment
    total = sum(weights.values())
    return {k: v / total for k, v in weights.items()}
```

**Cara Kerja Itinerary Generation (Step-by-Step):**
1. `POST /api/itineraries` terima `{raw_query, start_location:{lat,lng}}`.
2. `gemini_client.parse_constraints(raw_query)` → `{time_limit_minutes, budget_idr, search_radius_meter, interest_categories, avoid_crowds}`.
3. Apply default fallback jika field kosong: `time_limit=300`, `radius=2000`, `budget=999999999`.
4. Clamp bounds: `radius` ∈ [500, 5000], `budget` ≥ 10000.
5. **Hitung Jumlah Toko (Heuristik Waktu):**
   - < 60 mnt → 1 toko
   - 60-120 mnt → 2 toko
   - 120-180 mnt → 3 toko
   - > 180 mnt → 4 toko
6. **Alokasi Budget per Toko:**
   - `budget_per_toko = budget_idr / jumlah_toko` (Misal total budget Rp 200rb untuk 4 toko, maka max Rp 50rb/toko).
7. Embed `interest_categories` (misal 768 dimensi) ke `user_intent_vector`.
8. Eksekusi query PostGIS + pgvector (dengan filter RADIUS dan ALOKASI BUDGET):
   ```sql
   SELECT m.*, ST_Distance(m.location, :user_loc) AS distance_m,
          COALESCE(MAX(1 - (c.embedding <=> :user_intent_vector)), 0.0) AS max_category_match
   FROM merchants m
   LEFT JOIN merchant_catalog_items c ON c.merchant_id = m.id
   -- FILTER 1: Radius jarak jalan kaki dari turis
   WHERE ST_DWithin(m.location, :user_loc, :radius)
   -- FILTER 2: Budget per toko
   AND c.price <= :budget_per_toko
   GROUP BY m.id
   ```
9. Hitung SAW score per kandidat di Python dengan memanggil `calculate_saw_score()` menggunakan hasil query di atas.
10. Sort Score DESC, potong (LIMIT) sejumlah `jumlah_toko` dari poin 5.
11. Panggil OSRM 1x saja → dapatkan rute.
12. Simpan ke `itineraries`, return ke FE.

### Aturan Pasti (Edge Cases) Parsing & Filter:
Untuk menghindari ambiguitas saat implementasi, berikut adalah kontrak baku untuk menangani kemungkinan skenario turis:

1. **Turis tidak menyebutkan waktu:**
   - Parameter `time_limit_minutes` dari Gemini akan kosong (Null).
   - *Fallback:* Sistem berasumsi turis sedang santai/bebas. Di-set ke **300 menit (5 jam)**, sehingga turis akan langsung mendapat **4 toko** (jumlah maksimal).
2. **Turis tidak menyebutkan budget:**
   - Parameter `budget_idr` dari Gemini akan kosong.
   - *Fallback:* Sistem berasumsi budget turis *unlimited* (tak terbatas). Di-set ke **Rp 999.999.999**. Artinya, harga menu mana pun (mau murah atau *fine-dining*) akan masuk kualifikasi pencarian.
3. **Logika Filter Budget (Hard Filter):**
   - Filter `c.price <= :budget` diterapkan sebelum kecocokan AI dicari.
   - Artinya, menu restoran yang mahal akan "ditutup/disembunyikan". AI hanya akan mencocokkan niat turis dengan menu-menu yang harganya pas di kantong.
   - Jika *seluruh* menu di sebuah toko harganya melampaui budget, toko tersebut **gugur** dan tidak akan masuk ke dalam perankingan.
4. **Turis tidak menyebutkan minat spesifik (hanya "saya mau jalan-jalan"):**
   - `interest_categories` dari Gemini diatur ke nilai generik: *"tempat menarik, kuliner populer, oleh-oleh"*.
   - Semua toko akan memiliki kesempatan yang sama saat dicocokkan dengan *vektor generik* tersebut.
5. **Turis meminta jumlah toko irasional (misal "10 toko dalam 1 jam"):**
   - Jumlah toko secara ketat mematuhi heuristik waktu kita (< 60m=1, 60-120m=2, dst).
   - Angka "10 toko" diabaikan sepenuhnya oleh sistem.

### API Endpoints

| Method | Route | Body | Response | Auth |
|--------|-------|------|----------|------|
| POST | `/api/itineraries` | `{raw_query, start_location:{lat,lng}}` | `201 {itinerary_id, parsed_constraints, waypoints:[{merchant_id, name, score, score_breakdown, order}], route_geojson, estimated_duration_minutes}` | ✅ Bearer |
| GET | `/api/itineraries/{id}` | — | `200 {...}` | ✅ Owner |
| GET | `/api/itineraries/me` | `?status=active` | `200 [itineraries]` | ✅ Bearer |
| PATCH | `/api/itineraries/{id}/start` | — | `200 {status:"active"}` | ✅ Owner |
| POST | `/api/itineraries/{id}/checkin` | `{merchant_id, current_location:{lat,lng}}` | `200 {checked_in: bool, is_near_merchant: bool, distance_m: float}` | ✅ Owner |

### Unit Test WAJIB (`test_routing_scoring.py`)
```python
def test_weights_always_sum_to_one():
    for constraint in [{"avoid_crowds": True}, {"time_limit_minutes": 60}, {}]:
        weights = get_weights(constraint)
        assert abs(sum(weights.values()) - 1.0) < 1e-6

def test_hidden_gem_index_zero_reviews():
    assert calculate_hidden_gem_index(0, 100) == 1.0

def test_hidden_gem_index_max_reviews():
    assert calculate_hidden_gem_index(100, 100) == 0.0

def test_redemption_partner_multiplier():
    score_base = calculate_saw_score(0.5, 0.5, 0.5, 0.5, WEIGHT_PRESETS["default"], False)
    score_partner = calculate_saw_score(0.5, 0.5, 0.5, 0.5, WEIGHT_PRESETS["default"], True)
    assert abs(score_partner / score_base - 1.15) < 1e-6

def test_distance_norm_clamp_outside_radius():
    assert calculate_distance_norm(3000, 2000) == 0  # di luar radius → clamp 0
```

### Edge Cases Wajib Ditangani
- Tidak ada kandidat dalam radius → auto-expand 1.5× → jika tetap kosong → `200 {waypoints: [], message: "..."}`
- Merchant tanpa embedding → `category_match = 0.0`
- Semua Score sama → secondary sort `distance ASC`
- Budget < harga terendah → `200 {waypoints: [], message: "Budget tidak cukup"}`
- `parsed_constraints` nilai ekstrem/negatif → clamp bounds
- OSRM segmen tidak valid → exclude waypoint, regenerate

### Checklist Merge ke `develop`
- [ ] `w1+w2+w3+w4 == 1.0` pada semua kombinasi constraint (test pass)
- [ ] `HiddenGemIndex` benar (0 review = 1.0, max review = 0.0)
- [ ] Redemption partner multiplier 1.15× diterapkan
- [ ] Iterative trimming OSRM berfungsi jika melebihi time_limit
- [ ] Auto-expand radius berfungsi
- [ ] Engineering Decision Log ada sebagai code comment di `scoring.py`
- [ ] Unit test semua skenario pass

---

## 💰 BRANCH 7: `feat/pos-gamification`
**Dikerjakan oleh:** Developer 1
**Estimasi:** 5–6 jam
**Dependensi Branch:**
- `feat/auth-otp-jwt` harus sudah merge ke `develop`
- `feat/merchant-onboarding-ingestion` harus sudah merge ke `develop` (butuh merchant model + `require_merchant_ownership`)
- `feat/routing-itinerary-generation` harus sudah merge ke `develop` (butuh `itinerary_id` reference untuk trigger stamp)
**File yang disentuh (EKSKLUSIF):**
- `app/modules/transactions/models.py`
- `app/modules/transactions/schemas.py`
- `app/modules/transactions/service.py`
- `app/modules/transactions/router.py`
- `app/modules/transactions/__init__.py`
- `app/modules/gamification/models.py`
- `app/modules/gamification/schemas.py`
- `app/modules/gamification/service.py`
- `app/modules/gamification/router.py`
- `app/modules/gamification/__init__.py`
- `app/db/migrations/versions/[hashed]_create_transactions_stamps_promos.py`
- `tests/unit/test_gamification_service.py`
- `tests/integration/test_pos_gamification.py`

### Deskripsi Fitur
> Merchant mencatat transaksi (nominal + item opsional). Jika transaksi terhubung ke itinerary wisatawan aktif, stamp otomatis diberikan. Wisatawan bisa redeem promo ketika terkumpul cukup stamp.

### Formula POS Gamification
1. **Perhitungan XP/Poin:**
   - Base XP = $\lfloor \frac{\text{Total Transaksi}}{1000} \rfloor$
   - Bonus Streak = $(1 + (\text{Streak Hari} \times 0.1))$
2. **Kenaikan Level:**
   - Required XP = $1000 \times (\text{Level} \times 1.5)$

### Skema Database

**Tabel `transactions`:**
| Kolom | Tipe | Keterangan |
|-------|------|------------|
| id | UUID PK | |
| merchant_id | UUID FK | |
| tourist_user_id | UUID FK NULLABLE | Nullable: merchant bisa log walk-in |
| nominal_value | NUMERIC(12,2) NOT NULL | |
| item_reference | JSONB NULLABLE | |
| linked_itinerary_id | UUID FK NULLABLE | |
| client_reference_id | VARCHAR(64) NULLABLE | Idempotency key dari FE |
| is_suspicious | BOOLEAN DEFAULT false | Anti-fraud flag |
| logged_at | TIMESTAMPTZ DEFAULT now() | |

```sql
UNIQUE(merchant_id, client_reference_id)
```

**Tabel `stamps`:**
| Kolom | Tipe | Keterangan |
|-------|------|------------|
| id | UUID PK | |
| user_id | UUID FK | |
| merchant_id | UUID FK | |
| transaction_id | UUID FK UNIQUE | 1 transaksi = max 1 stamp |
| awarded_at | TIMESTAMPTZ | |

**Tabel `promos`:**
| Kolom | Tipe | Keterangan |
|-------|------|------------|
| id | UUID PK | |
| merchant_id | UUID FK | |
| title | VARCHAR(150) NOT NULL | Contoh: "Diskon 20K" |
| discount_type | ENUM('percentage','fixed_amount') | |
| discount_value | NUMERIC(10,2) NOT NULL | |
| stamp_required_count | INTEGER NOT NULL | Jumlah stamp untuk redeem |
| is_active | BOOLEAN DEFAULT true | |
| valid_until | TIMESTAMPTZ NOT NULL | |
| created_at | TIMESTAMPTZ | |

**Tabel `promo_redemptions`:**
| Kolom | Tipe | Keterangan |
|-------|------|------------|
| id | UUID PK | |
| promo_id | UUID FK | |
| user_id | UUID FK | |
| redemption_code | VARCHAR(8) UNIQUE NOT NULL | Kode yang ditunjukkan ke kasir |
| status | ENUM('pending','redeemed','expired') | |
| expires_at | TIMESTAMPTZ NOT NULL | TTL kode (misal 15 menit) |
| redeemed_at | TIMESTAMPTZ NULLABLE | Waktu merchant confirm |
| created_at | TIMESTAMPTZ | |

### Business Logic

**Alur POS & Log Transaksi (Tanpa Payment Gateway Asli):**
1. *Client* (Merchant App) menghitung `total_price` secara lokal. Pembayaran dilakukan *offline* (tunai/scan QRIS statis).
2. *Client* me-request `POST /api/merchants/{id}/transactions` dengan payload `{nominal_value: total_price, ...}`.
3. Server memvalidasi `nominal_value > 0`. Jika `nominal_value > 5000000`, set flag `is_suspicious = True`.
4. Server mengecek idempotensi menggunakan `client_reference_id` untuk mencegah duplikasi (retry safe).
5. Server mengeksekusi `db.add(Transaction(...))` lalu `await db.commit()`.
6. Jika payload mengandung `linked_itinerary_id` (tidak null): Server memvalidasi kepemilikan itinerary, lalu men-trigger `gamification_service.award_stamp(user_id, merchant_id, transaction_id)` via `asyncio.create_task()` atau *background task*.

**Gamification Award Stamp (idempotent):**
1. Cek `UNIQUE(transaction_id)` di tabel `stamps` (tangani IntegrityError).
2. Eksekusi `db.add(Stamp(...))`.
3. (Opsional) Trigger notifikasi WebSocket / push jika threshold poin terpenuhi.

**Alur Pembuatan & Penggunaan Promo (Redemption):**
1. Merchant men-trigger `POST /api/merchants/{id}/promos` dengan payload konfigurasi. Server mengeksekusi `db.add(Promo(...))`.
2. Tourist me-request klaim via `POST /api/promos/{id}/redeem`.
3. Server memberlakukan *Row-Level Lock* (`SELECT ... FOR UPDATE`) pada record `stamps` user untuk mencegah *race condition*.
4. Jika `total_stamp >= stamp_required_count`, server men-generate `redemption_code` (menggunakan `secrets.token_hex(4).upper()`) dan set `expires_at = func.now() + timedelta(minutes=15)`.
5. Server menyimpan entri ke `promo_redemptions` dengan status `pending`.
6. Merchant memvalidasi kupon via `POST /api/merchants/{id}/promo-redemptions/{code}/confirm`.
7. Server mengecek `expires_at > now()` dan status == `pending`.
8. Jika valid, update status menjadi `redeemed`, tandai *stamp* sebagai terpakai, dan return `200 OK`. *Client* POS secara lokal akan memotong tagihan sesuai nilai diskon dari DB.

### API Endpoints

| Method | Route | Body | Response | Auth |
|--------|-------|------|----------|------|
| POST | `/api/merchants/{id}/promos` | `{title, discount_type, discount_value, stamp_required_count, valid_until}` | `201 {promo_id}` | ✅ Owner |
| POST | `/api/merchants/{id}/transactions` | `{nominal_value, item_reference?, linked_itinerary_id?, client_reference_id?}` | `201 {transaction_id, stamp_awarded: bool}` | ✅ Owner |
| GET | `/api/merchants/{id}/transactions` | `?page&limit` | `200 {items, pagination}` | ✅ Owner |
| GET | `/api/merchants/{id}/transactions/summary` | `?date=today` | `200 {total_omzet, total_transaksi}` | ✅ Owner |
| GET | `/api/merchants/{id}/qris` | — | `200 {qris_image_url}` | ✅ Owner |
| GET | `/api/users/me/stamps` | — | `200 {total_stamps, stamps:[{merchant_name, awarded_at}]}` | ✅ Bearer |
| GET | `/api/promos/available` | — | `200 [{promo_id, merchant_name, title, discount, stamp_required, user_stamp_count}]` | ✅ Bearer |
| POST | `/api/promos/{id}/redeem` | — | `201 {redemption_code, expires_at}` | ✅ Bearer |
| POST | `/api/merchants/{id}/promo-redemptions/{code}/confirm` | — | `200 {status:"redeemed"}` | ✅ Owner |

### Edge Cases Wajib Ditangani
- `nominal_value <= 0` → `400`
- `client_reference_id` duplikat → return response transaksi awal (idempotency, bukan error)
- `linked_itinerary_id` milik user lain → `403`, jangan trigger stamp
- Double-trigger stamp via retry → `UNIQUE(transaction_id)` cegah
- Race condition redeem promo bersamaan → `SELECT ... FOR UPDATE`
- Promo expired → `400 PROMO_EXPIRED`
- `redemption_code` dipakai 2x → `409`

### Checklist Merge ke `develop`
- [ ] Transaksi log berfungsi + `stamp_awarded: true` jika ada itinerary
- [ ] Idempotency `client_reference_id` berfungsi (retry tidak double-insert)
- [ ] Stamp tidak double-award
- [ ] Race condition redeem (concurrent test `asyncio.gather`) → hanya 1 sukses
- [ ] `redemption_code` unik dan bisa diconfirm merchant

---

## 📊 BRANCH 8: `feat/credit-score-support`
**Dikerjakan oleh:** Developer 3
**Estimasi:** 3–4 jam
**Dependensi Branch:** `feat/pos-gamification` harus sudah merge ke `develop` (butuh transaction data)
**File yang disentuh (EKSKLUSIF):**
- `app/modules/credit_score/models.py`
- `app/modules/credit_score/schemas.py`
- `app/modules/credit_score/service.py`
- `app/modules/credit_score/router.py`
- `app/modules/credit_score/__init__.py`
- `app/db/migrations/versions/[hashed]_create_credit_score_logs.py`

### API Endpoints

| Method | Route | Body | Response | Auth |
|--------|-------|------|----------|------|
| GET | `/api/merchants/{id}/credit-score` | — | `200 {current_score, data_status, history:[{period, score}]}` | ✅ Owner |


### Formula Credit Score
1. **Komponen Skor:**
   - 40%: Konsistensi Transaksi (Frekuensi)
   - 30%: Volume Transaksi (Total Nominal)
   - 20%: Masa Aktif Merchant
   - 10%: Rating / Review Pelanggan
2. **Skor Akhir:** $S = \sum (C_i \times W_i)$ dengan skala 0 - 1000.

**Aturan:**
- Merchant < 1 bulan data → `data_status: "insufficient_data"`, jangan tampilkan angka 0
- Transaksi `is_suspicious=true` dikecualikan dari perhitungan skor

---

## 📁 FILE OWNERSHIP MAP (Referensi Anti-Conflict)

| File / Folder | Branch |
|---------------|--------|
| `app/core/*` | `feat/core-infrastructure` (Dev Lead) |
| `app/db/base.py`, `app/db/session.py` | `feat/core-infrastructure` (Dev Lead) |
| `app/modules/auth/*` | `feat/auth-otp-jwt` (Dev Lead) |
| `app/modules/merchants/*` | `feat/merchant-onboarding-ingestion` (Dev 1) |
| `app/modules/ingestion/*` | `feat/merchant-onboarding-ingestion` (Dev 1) |
| `app/integrations/gemini_client.py` | `feat/merchant-onboarding-ingestion` (Dev 1) |
| `app/integrations/supabase_storage.py` | `feat/merchant-onboarding-ingestion` (Dev 1) |
| `app/modules/events/*` | `feat/events-admin-hitl` (Dev 2) |
| `app/modules/admin/*` | `feat/events-admin-hitl` (Dev 2) |
| `app/modules/inventory/*` | `feat/inventory-predictive-stock` (Dev 2) |
| `app/workers/*` | `feat/inventory-predictive-stock` (Dev 2) |
| `app/integrations/weather_client.py` | `feat/inventory-predictive-stock` (Dev 2) |
| `app/modules/routing/*` | `feat/routing-itinerary-generation` (Dev 3) |
| `app/integrations/osrm_client.py` | `feat/routing-itinerary-generation` (Dev 3) |
| `app/modules/transactions/*` | `feat/pos-gamification` (Dev 1) |
| `app/modules/gamification/*` | `feat/pos-gamification` (Dev 1) |
| `app/modules/credit_score/*` | `feat/credit-score-support` (Dev 3) |
| **`app/main.py`** | **⚠️ SHARED — Dev Lead saja yang tambahkan `include_router` setelah tiap PR merge** |
| `scripts/seed_dummy_data.py` | Dev Lead — dikerjakan terakhir |

---

## 🏁 CHECKLIST FINAL SEBELUM DEMO

- [ ] Semua endpoint Phase 3 pass test happy-path + minimal 2 edge case
- [ ] Seed data realistis: 5 event, 15 merchant, 30+ catalog item, 10 user
- [ ] Load test `/api/itineraries` → response < 3 detik
- [ ] `w1+w2+w3+w4 == 1.0` terbukti di semua skenario (unit test pass)
- [ ] `S_predicted` tidak pernah negatif (semua test case pass)
- [ ] Akses resource milik user lain → `403` bukan `200`
- [ ] Engineering Decision Log ada di `scoring.py` dan `calculator.py`
- [ ] Swagger `/api/docs` semua endpoint terkelompok berdasarkan tags
- [ ] Error codes terdokumentasi di `docs/error_codes.md`
