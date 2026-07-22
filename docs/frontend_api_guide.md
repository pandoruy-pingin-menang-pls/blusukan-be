# Blusukan API — Panduan Lengkap untuk Tim Frontend

> **Base URL:** `https://blusukan-be.up.railway.app/api`  
> **Swagger UI:** `https://blusukan-be.up.railway.app/api/docs`  
> **Local Dev:** `http://127.0.0.1:8000/api` (jalankan `uvicorn app.main:app --reload`)

---

## Daftar Isi

1. [Konvensi & Aturan Umum](#1-konvensi--aturan-umum)
2. [User Roles & Akun Bawaan](#2-user-roles--akun-bawaan)
3. [Auth Flow — Semua Role](#3-auth-flow--semua-role)
4. [Dolan Mode — Flow Wisatawan](#4-dolan-mode--flow-wisatawan)
5. [Bakul Mode — Flow Pedagang](#5-bakul-mode--flow-pedagang)
6. [Admin — Event Management (HITL)](#6-admin--event-management-hitl)
7. [Events — Publik (Tanpa Auth)](#7-events--publik-tanpa-auth)
8. [Error Handling](#8-error-handling)
9. [Enum & Konstanta Referensi](#9-enum--konstanta-referensi)

---

## 1. Konvensi & Aturan Umum

### Prefix URL
Semua endpoint diawali `/api`. Contoh: `/api/auth/login`, `/api/merchants/me`.

### Autentikasi Header
Endpoint *protected* wajib menyertakan header:
```
Authorization: Bearer <access_token>
```
Simpan `access_token` dan `refresh_token` di `SecureStore` (Expo) setelah login.

### Format Tanggal
Semua field tanggal/waktu menggunakan **ISO 8601 UTC**: `2026-07-20T12:00:00Z`

### Format Error Standard
```json
{ "detail": "Pesan error dalam Bahasa Indonesia" }
```

---

## 2. User Roles & Akun Bawaan

| Role | Nilai di Token | Cara Mendapatkan |
|------|----------------|-----------------|
| Wisatawan (Turis) | `wisatawan` | Default setelah `POST /auth/register` |
| Pedagang (Merchant) | `pedagang` | Setelah `POST /merchants/register` — token **baru** diberikan |
| Admin | `admin` | Akun pre-seeded |

### Akun Admin (Pre-seeded)

| Field | Nilai |
|-------|-------|
| **Email** | `admin@blusukan.com` |
| **Password** | `adminblusukan123` |

Login dengan akun ini via `POST /api/auth/login` untuk mendapatkan token admin.

---

## 3. Auth Flow — Semua Role

### Flow Umum

```
Register → Login → { access_token, refresh_token } → Gunakan access_token di setiap request
         ↓ token expired (401)
         Refresh → { access_token baru, refresh_token baru }
```

> **Token Rotation:** Setiap `POST /auth/refresh` me-revoke token lama dan mengeluarkan pasangan token baru. Jangan simpan token lama setelah refresh.

---

### `POST /api/auth/register`
Membuat akun baru. Role default: `wisatawan`.

**Request Body:**
```json
{
  "email": "user@email.com",
  "full_name": "Siti Aminah",
  "password": "minimal8karakter"
}
```

**Response `201`:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "uuid:hexstring...",
  "token_type": "bearer",
  "user": {
    "id": "uuid-string",
    "email": "user@email.com",
    "full_name": "Siti Aminah",
    "role": "wisatawan",
    "has_merchant_profile": false,
    "created_at": "2026-07-20T10:00:00Z",
    "updated_at": null
  }
}
```

---

### `POST /api/auth/login`
Login dengan email & password.

**Request Body:**
```json
{
  "email": "user@email.com",
  "password": "password123"
}
```

**Response `200`:** _(Struktur identik dengan response register)_

---

### `POST /api/auth/refresh`
Rotasi token. Refresh token lama langsung di-revoke.

**Request Body:**
```json
{
  "refresh_token": "<refresh_token_saat_ini>"
}
```

**Response `200`:** _(Struktur identik — berisi token baru)_

---

### `POST /api/auth/logout`
Invalidasi refresh_token. Hapus semua token dari storage lokal setelah ini.

**Header:** `Authorization: Bearer <access_token>` ✅

**Request Body:**
```json
{
  "refresh_token": "<refresh_token>"
}
```

**Response `204`:** _(Tidak ada body)_

---

### `GET /api/auth/me`
Mengambil profil user yang sedang login.

**Header:** `Authorization: Bearer <access_token>` ✅

**Response `200`:**
```json
{
  "id": "uuid-string",
  "email": "user@email.com",
  "full_name": "Siti Aminah",
  "role": "wisatawan",
  "has_merchant_profile": false,
  "created_at": "2026-07-20T10:00:00Z",
  "updated_at": null
}
```

---

### `PATCH /api/auth/me`
Update profil user (saat ini: `full_name` saja).

**Header:** `Authorization: Bearer <access_token>` ✅

**Request Body:**
```json
{
  "full_name": "Nama Baru"
}
```

**Response `200`:** _(Objek `UserResponse` yang sudah diupdate)_

---

## 4. Dolan Mode — Flow Wisatawan

User dengan role `wisatawan` bisa generate itinerary, melihat event publik, mengumpulkan stamp, dan menukar promo.

### 4.1 Generate Itinerary

```
Turis input: "mau makan soto, budget 50rb, 2 jam"
  → POST /api/itineraries  (teks + koordinat GPS)
  → Backend: Gemini parsing → SAW scoring merchants → OSRM routing
  → Response: itinerary + waypoints + GeoJSON rute
  → FE render di peta (react-native-maps / mapbox-gl)
```

> ⏳ Endpoint ini membutuhkan **3–8 detik** karena melibatkan Gemini API + OSRM. Tampilkan loading indicator yang informatif.

---

#### `POST /api/itineraries`
Generate itinerary baru.

**Header:** `Authorization: Bearer <access_token>` ✅

**Request Body:**
```json
{
  "raw_query": "mau makan soto dan cari oleh-oleh batik, budget 100rb, 2 jam aja",
  "current_lat": -7.5660,
  "current_lon": 110.8203
}
```

**Response `201`:**
```json
{
  "id": "uuid-itinerary",
  "user_id": "uuid-user",
  "raw_query": "mau makan soto dan cari oleh-oleh batik...",
  "parsed_constraints": {
    "time_limit_minutes": 120,
    "budget_idr": 100000,
    "search_radius_meter": 3000,
    "interest_categories": "soto, batik",
    "avoid_crowds": false
  },
  "waypoints": [
    {
      "merchant_id": "uuid-merchant-1",
      "name": "Warung Soto Pak Darmo",
      "lat": -7.5620,
      "lon": 110.8180,
      "score": 0.87,
      "order": 1,
      "category": "KULINER_PANAS",
      "predicted_stock": 45
    },
    {
      "merchant_id": "uuid-merchant-2",
      "name": "Batik Amanah",
      "lat": -7.5700,
      "lon": 110.8250,
      "score": 0.74,
      "order": 2,
      "category": "KERAJINAN",
      "predicted_stock": null
    }
  ],
  "route_geojson": {
    "type": "LineString",
    "coordinates": [
      [110.8203, -7.5660],
      [110.8200, -7.5655],
      "...ratusan titik mengikuti belokan jalan (dari OSRM)..."
    ]
  },
  "estimated_duration_minutes": 95,
  "status": "draft",
  "created_at": "2026-07-20T10:00:00Z"
}
```

**Field Penting:**

| Field | Isi | Digunakan untuk |
|-------|-----|----------------|
| `route_geojson.coordinates` | Ratusan titik `[lon, lat]` dari OSRM | Render `<Polyline>` (garis rute) |
| `waypoints[].lat / .lon` | Koordinat toko tujuan | Render `<Marker>` (pin toko) |
| `waypoints[].order` | Urutan kunjungan (1, 2, 3...) | Label nomor di marker |
| `waypoints[].score` | Skor SAW merchant (0.0–1.0) | Badge "rating blusukan" |
| `waypoints[].predicted_stock` | Estimasi stok (bisa `null`) | Info stok di card merchant |

**Cara Render di Peta (React Native Maps):**
```javascript
// ⚠️ GeoJSON pakai [lon, lat] — balik urutannya untuk react-native-maps!
const routeCoords = itinerary.route_geojson.coordinates.map(([lon, lat]) => ({
  latitude: lat,
  longitude: lon,
}));
```

> [!WARNING]
> **Jika OSRM tidak berjalan** (local dev tanpa Docker), backend otomatis menggunakan **fallback mock** dengan garis lurus antar waypoint. `coordinates` hanya berisi sejumlah waypoint. Jalankan Docker untuk routing nyata.

---

#### `GET /api/itineraries/{itinerary_id}`
Mengambil detail itinerary.

**Header:** `Authorization: Bearer <access_token>` ✅

**Response `200`:** _(Sama dengan response generate)_

---

#### `PATCH /api/itineraries/{itinerary_id}/start`
Ubah status itinerary menjadi `active` (user klik "Mulai Perjalanan").

**Header:** `Authorization: Bearer <access_token>` ✅

**Response `200`:**
```json
{
  "message": "Itinerary started",
  "id": "uuid-itinerary"
}
```

---

### 4.2 Stamps & Promo Redemption (Dolan Side)

Stamp didapat **otomatis** saat merchant mencatat transaksi dengan `linked_itinerary_id` milik turis.

#### `GET /api/users/me/stamps`
Lihat semua stamp yang dimiliki.

**Header:** `Authorization: Bearer <access_token>` ✅

**Response `200`:**
```json
{
  "total_stamps": 5,
  "stamps": [
    {
      "id": "uuid-stamp",
      "merchant_name": "Warung Bu Sari",
      "awarded_at": "2026-07-20T10:30:00Z"
    }
  ]
}
```

---

#### `GET /api/promos/available`
Daftar promo yang bisa ditukar (stamp cukup).

**Header:** `Authorization: Bearer <access_token>` ✅

**Response `200`:**
```json
[
  {
    "promo_id": "uuid-promo",
    "merchant_name": "Batik Amanah",
    "title": "Diskon 20% untuk pembelian batik",
    "discount_type": "percentage",
    "discount_value": 20.0,
    "stamp_required_count": 3,
    "user_stamp_count": 5
  }
]
```

---

#### `POST /api/promos/{id}/redeem`
Tukar stamp dengan kode kupon. **Kode berlaku 15 menit.**

**Header:** `Authorization: Bearer <access_token>` ✅  
**Body:** _(Tidak ada body — `{id}` adalah `promo_id`)_

**Response `201`:**
```json
{
  "redemption_code": "A3F9C2B1",
  "expires_at": "2026-07-20T11:00:00Z"
}
```

> **UX:** Tampilkan `redemption_code` sebagai teks besar atau QR Code. Tambahkan countdown timer hingga `expires_at`.

---

## 5. Bakul Mode — Flow Pedagang

### 5.1 Merchant Onboarding

```
User Login (role: wisatawan)
  → POST /merchants/register
  → Response: token BARU dengan role "pedagang" + data merchant
  → Simpan token baru → user sekarang adalah Pedagang
```

> [!IMPORTANT]
> `POST /merchants/register` hanya bisa dipanggil **sekali** per user. Jika dipanggil dua kali, server mengembalikan error karena `has_merchant_profile: true`.
>
> Setelah register merchant, **wajib ganti token lama** dengan token baru dari response ini agar role `pedagang` aktif.

---

#### `POST /api/merchants/register`
Daftarkan toko baru. Role user otomatis di-upgrade ke `pedagang`.

**Header:** `Authorization: Bearer <access_token>` ✅ *(Role: wisatawan)*

**Request Body:**
```json
{
  "name": "Warung Bu Sari",
  "description": "Warung makanan tradisional Solo, spesialis nasi liwet.",
  "category": "KULINER_PANAS",
  "address": "Jl. Slamet Riyadi No. 10, Surakarta",
  "latitude": -7.5660,
  "longitude": 110.8203
}
```

**Response `201`:**
```json
{
  "access_token": "eyJ...(token baru dengan role pedagang)...",
  "refresh_token": "...",
  "token_type": "bearer",
  "user": { ... },
  "merchant": {
    "id": "uuid-merchant",
    "name": "Warung Bu Sari",
    "category": "KULINER_PANAS",
    "is_verified": false,
    "is_active": true,
    ...
  }
}
```

---

#### `GET /api/merchants/me`
Lihat profil toko milik user yang sedang login.

**Header:** `Authorization: Bearer <access_token>` ✅ *(Role: pedagang)*

**Response `200`:**
```json
{
  "id": "uuid-merchant",
  "owner_id": "uuid-user",
  "name": "Warung Bu Sari",
  "description": "Warung makanan tradisional Solo",
  "category": "KULINER_PANAS",
  "address": "Jl. Slamet Riyadi No. 10",
  "is_verified": false,
  "is_active": true,
  "latitude": -7.5660,
  "longitude": 110.8203,
  "created_at": "2026-07-20T10:00:00Z",
  "updated_at": null
}
```

> [!NOTE]
> `is_verified` saat ini **tidak memblokir fitur apapun** — merchant langsung bisa akses semua fitur (POS, catalog, dll) meskipun `is_verified: false`. Tampilkan badge informatif saja: ✅ Terverifikasi / ⏳ Menunggu Verifikasi.

---

### 5.2 Catalog Ingestion via AI

```
Step 1: POST /merchants/{id}/catalog/ingest  → Upload foto menu
          ↓ Gemini Vision mengekstrak item sebagai "Draft"
          Response: { draft_items: [...], image_url: "..." }

Step 2: FE tampilkan draft_items ke merchant untuk dikoreksi

Step 3: POST /merchants/{id}/catalog/confirm → Kirim hasil final
          Response: Array CatalogItemResponse (tersimpan di DB)
```

> [!TIP]
> `{id}` pada URL adalah **merchant_id**. Ambil dari `GET /merchants/me`.

---

#### `POST /api/merchants/{id}/catalog/ingest`
Upload foto menu; Gemini Vision mengekstrak item.

**Header:** `Authorization: Bearer <access_token>` ✅  
**Content-Type:** `multipart/form-data`

**Form Data:**
| Field | Tipe | Keterangan |
|-------|------|------------|
| `file` | `File` | JPG/PNG, maks 10MB |

**Response `200`:**
```json
{
  "message": "Berhasil mengekstrak 3 item dari foto.",
  "image_url": "https://supabase.../menu-image.jpg",
  "draft_items": [
    { "item_name": "Nasi Liwet", "price": 15000, "category": "culinary" },
    { "item_name": "Es Teh Manis", "price": 5000, "category": "culinary" },
    { "item_name": "Tempe Goreng", "price": 3000, "category": "culinary" }
  ]
}
```

> Simpan `image_url` — wajib dikirim kembali di step `confirm`.

---

#### `POST /api/merchants/{id}/catalog/confirm`
Simpan item yang sudah dikonfirmasi ke database + generate pgvector embeddings.

**Header:** `Authorization: Bearer <access_token>` ✅

**Request Body:**
```json
{
  "image_url": "https://supabase.../menu-image.jpg",
  "items": [
    {
      "item_name": "Nasi Liwet",
      "price": 15000,
      "category": "culinary",
      "source_type": "photo"
    },
    {
      "item_name": "Es Jeruk (Tambahan Manual)",
      "price": 6000,
      "category": "culinary",
      "source_type": "manual"
    }
  ]
}
```

| `source_type` | Keterangan |
|---------------|------------|
| `"photo"` | Item dari hasil AI |
| `"manual"` | Ditambah/diedit manual oleh merchant |

**Response `201`:** Array `CatalogItemResponse`
```json
[
  {
    "id": "uuid-item",
    "merchant_id": "uuid-merchant",
    "item_name": "Nasi Liwet",
    "price": "15000",
    "category": "culinary",
    "description_raw": null,
    "image_url": "https://supabase.../menu-image.jpg",
    "source_type": "photo",
    "confidence": "high",
    "created_at": "2026-07-20T10:00:00Z"
  }
]
```

---

#### `GET /api/merchants/{id}/catalog`
Publik: Melihat daftar menu/katalog merchant.

**Autentikasi:** Tidak diperlukan (publik).

**Response `200`:** _(Array CatalogItemResponse)_

---

### 5.3 POS & Transaksi

```
Turis datang → Merchant hitung total → Pembayaran fisik (tunai/QRIS mandiri)
  → POST /merchants/{id}/transactions
      - linked_itinerary_id: ID itinerary turis (jika ada)
  → Jika itinerary valid → Stamp otomatis diberikan ke turis
  → Response: { stamp_awarded: true/false }
```

---

#### `POST /api/merchants/{id}/transactions`
Catat transaksi baru (endpoint utama POS).

**Header:** `Authorization: Bearer <access_token>` ✅ *(Role: pedagang, harus owner merchant ini)*

**Request Body:**
```json
{
  "nominal_value": 25000,
  "item_reference": {
    "items": [
      { "name": "Nasi Liwet", "qty": 1, "price": 15000 },
      { "name": "Es Teh", "qty": 2, "price": 5000 }
    ]
  },
  "linked_itinerary_id": "uuid-itinerary-turis",
  "client_reference_id": "unique-client-side-id-123"
}
```

| Field | Wajib | Keterangan |
|-------|-------|------------|
| `nominal_value` | ✅ | Total harga (Rupiah) |
| `item_reference` | ❌ | JSON bebas untuk rekap merchant |
| `linked_itinerary_id` | ❌ | ID itinerary turis → trigger stamp gamification |
| `client_reference_id` | ❌ | UUID dari FE untuk idempotency (cegah double-submit) |

> [!TIP]
> **Idempotency:** Generate UUID di FE sebelum submit. Jika request gagal & di-retry, kirim `client_reference_id` yang sama — backend tidak akan mencatat duplikat.

**Response `201`:**
```json
{
  "id": "uuid-transaction",
  "merchant_id": "uuid-merchant",
  "tourist_user_id": "uuid-user-turis",
  "nominal_value": 25000.0,
  "item_reference": { "items": [...] },
  "linked_itinerary_id": "uuid-itinerary",
  "client_reference_id": "unique-client-side-id-123",
  "is_suspicious": false,
  "logged_at": "2026-07-20T10:30:00Z",
  "stamp_awarded": true
}
```

---

#### `GET /api/merchants/{id}/transactions`
Riwayat transaksi merchant (paginasi).

**Header:** `Authorization: Bearer <access_token>` ✅

**Query Params:**
| Param | Default | Keterangan |
|-------|---------|------------|
| `page` | `1` | Halaman saat ini |
| `limit` | `20` | Item per halaman |

**Response `200`:**
```json
{
  "items": [ ...array TransactionResponse... ],
  "total": 150,
  "page": 1,
  "limit": 20
}
```

---

#### `GET /api/merchants/{id}/transactions/summary`
Ringkasan omzet hari ini.

**Header:** `Authorization: Bearer <access_token>` ✅

**Response `200`:**
```json
{
  "total_omzet": 1250000.0,
  "total_transaksi": 47
}
```

---

### 5.4 Gamification — Promo (Bakul Side)

#### `POST /api/merchants/{id}/promos`
Buat promo baru yang membutuhkan stamp.

**Header:** `Authorization: Bearer <access_token>` ✅ *(Role: pedagang)*

**Request Body:**
```json
{
  "title": "Gratis Es Teh untuk 3 Stamp",
  "discount_type": "fixed_amount",
  "discount_value": 5000,
  "stamp_required_count": 3,
  "valid_until": "2026-12-31T23:59:59Z"
}
```

**Response `201`:** Objek promo yang baru dibuat.

---

#### `POST /api/merchants/{id}/promo-redemptions/{code}/confirm`
Kasir konfirmasi kode kupon dari turis.

**Header:** `Authorization: Bearer <access_token>` ✅ *(Role: pedagang)*  
**Body:** _(Tidak ada body — `{code}` adalah kode 8 karakter dari turis, misal: `A3F9C2B1`)_

**Response `200`:**
```json
{
  "status": "redeemed"
}
```

| `status` | Keterangan |
|----------|------------|
| `pending` | Kode belum dipakai |
| `redeemed` | Sudah dikonfirmasi merchant |
| `expired` | Kode kedaluwarsa (>15 menit) |

---

### 5.5 Inventory — Predictive Stock

```
Merchant set baseline stok
  → PATCH /merchants/{id}/baseline-inventory
Celery task berjalan otomatis setiap hari → hitung saran stok
Merchant buka app
  → GET /merchants/{id}/inventory-recommendations/today
```

---

#### `PATCH /api/merchants/{merchant_id}/baseline-inventory`
Set stok dasar harian.

**Header:** `Authorization: Bearer <access_token>` ✅

**Request Body:**
```json
{
  "baseline_inventory": {
    "nasi": 50,
    "ayam": 30,
    "minuman": 100
  }
}
```

> Key bersifat bebas — sesuaikan dengan bahan yang ingin di-track merchant.

**Response `200`:**
```json
{
  "message": "Baseline inventory berhasil diperbarui."
}
```

---

#### `GET /api/merchants/{merchant_id}/inventory-recommendations/today`
Ambil rekomendasi stok hari ini (berdasarkan event sekitar & cuaca).

**Header:** `Authorization: Bearer <access_token>` ✅

**Response `200`:**
```json
{
  "id": "uuid-rec",
  "merchant_id": "uuid-merchant",
  "generated_for_date": "2026-07-20",
  "weather_condition": "hujan",
  "nearby_events": [
    {
      "name": "Solo Batik Carnival",
      "estimated_attendee_count": 5000,
      "genre": "festival"
    }
  ],
  "recommended_stock": {
    "nasi": 70,
    "ayam": 45,
    "minuman": 80
  },
  "ai_suggestion_text": "Cuaca hujan diperkirakan mengurangi pembeli sebesar 20%. Namun ada festival besar di dekat lokasi Anda. Disarankan menyiapkan stok minuman panas lebih banyak."
}
```

---

### 5.6 Credit Score (Bakul)

#### `GET /api/merchants/{id}/credit-score`
Ambil skor kredit merchant beserta riwayatnya.

**Header:** `Authorization: Bearer <access_token>` ✅ *(Role: pedagang, harus owner merchant ini)*

**Response `200`:** Objek `CreditScoreResponse` berisi skor saat ini dan riwayat log.

---

## 6. Admin — Event Management (HITL)

> [!IMPORTANT]
> Semua endpoint `/api/admin/*` membutuhkan `role: admin`.  
> Login dengan: `admin@blusukan.com` / `adminblusukan123`

---

### `POST /api/admin/events`
Buat event baru secara manual. Status otomatis `approved` saat dibuat admin.

**Header:** `Authorization: Bearer <access_token>` ✅ *(Role: admin)*

**Request Body:**
```json
{
  "name": "Solo Batik Carnival 2026",
  "genre": "festival",
  "venue_name": "Jl. Slamet Riyadi, Surakarta",
  "estimated_attendee_count": 5000,
  "start_datetime": "2026-08-01T16:00:00Z",
  "end_datetime": "2026-08-01T22:00:00Z"
}
```

> `latitude` dan `longitude` venue bersifat opsional namun disarankan diisi untuk akurasi rekomendasi inventory.

**Response `201`:**
```json
{
  "event_id": "uuid-event",
  "status": "approved"
}
```

---

### `GET /api/admin/events`
Daftar semua event (bisa difilter status).

**Header:** `Authorization: Bearer <access_token>` ✅ *(Role: admin)*

**Query Params:**
| Param | Keterangan |
|-------|------------|
| `status` | `pending_review` \| `approved` \| `rejected` |

**Response `200`:** Array of `EventResponse`

---

### `PATCH /api/admin/events/{event_id}/review`
Approve atau reject event yang pending.

**Header:** `Authorization: Bearer <access_token>` ✅ *(Role: admin)*

**Request Body:**
```json
{
  "action": "approve",
  "name": "(opsional) Edit nama event",
  "genre": "(opsional) Ubah genre",
  "estimated_attendee_count": 6000
}
```

| `action` | Keterangan |
|----------|------------|
| `approve` | Event jadi publik (`status: approved`) |
| `reject` | Event ditolak (`status: rejected`) |

**Response `200`:** `EventResponse` yang sudah diupdate.

---

### `POST /api/admin/inventory-recommendations/recalculate`
Trigger manual Celery untuk recalculate semua merchant recommendations sekarang.

**Header:** `Authorization: Bearer <access_token>` ✅

**Response `202`:**
```json
{
  "message": "Tugas perhitungan stok telah dikirim ke Celery.",
  "job_id": "async-celery"
}
```

---

## 7. Events — Publik (Tanpa Auth)

> Endpoint ini **tidak memerlukan autentikasi**. Digunakan untuk halaman eksplorasi event di Solo Raya.

---

### `GET /api/events`
Daftar event yang sudah `approved`.

**Query Params:**
| Param | Tipe | Keterangan |
|-------|------|------------|
| `upcoming` | `boolean` | Jika `true`, hanya event yang belum berakhir |

**Contoh:** `GET /api/events?upcoming=true`

**Response `200`:**
```json
[
  {
    "id": "uuid-event",
    "name": "Solo Batik Carnival 2026",
    "genre": "festival",
    "venue_name": "Jl. Slamet Riyadi",
    "estimated_attendee_count": 5000,
    "start_datetime": "2026-08-01T16:00:00Z",
    "end_datetime": "2026-08-01T22:00:00Z",
    "status": "approved",
    "reviewed_by_admin_id": "uuid-admin",
    "created_at": "2026-07-15T08:00:00Z",
    "is_expired": false
  }
]
```

---

### `GET /api/events/{event_id}`
Detail satu event approved.

**Response `200`:** _(Satu objek EventResponse, `is_expired: true` jika sudah lewat)_

---

## 8. Error Handling

### Tabel Error Umum
| HTTP Code | Keterangan | Tindakan FE |
|-----------|------------|-------------|
| `400` | Input tidak valid / constraint bisnis | Tampilkan `detail` ke user |
| `401` | Token expired / tidak ada / token reuse | Refresh token; jika gagal → redirect Login |
| `403` | Role tidak cukup / bukan owner merchant | Tampilkan "Tidak diizinkan" |
| `404` | Data tidak ditemukan | Tampilkan state kosong |
| `409` | Konflik (misal: stamp sudah diberikan) | Tampilkan pesan konflik |
| `422` | Validasi schema gagal (field salah tipe/format) | Periksa field yang dikirim |
| `429` | Rate limit / limit ingest foto tercapai | Tampilkan "Coba lagi nanti" |
| `500` | Server error | Tampilkan pesan generik |

### Contoh Setup Axios Interceptor (React Native / Expo)
```javascript
import axios from 'axios';
import * as SecureStore from 'expo-secure-store';

const api = axios.create({ baseURL: 'https://blusukan-be.up.railway.app/api' });

// Auto-inject token ke setiap request
api.interceptors.request.use(async (config) => {
  const token = await SecureStore.getItemAsync('access_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Auto-refresh jika 401
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401 && !error.config._retried) {
      error.config._retried = true;
      const refreshToken = await SecureStore.getItemAsync('refresh_token');
      try {
        const { data } = await axios.post('/api/auth/refresh', {
          refresh_token: refreshToken,
        });
        // Simpan token baru (rotation — token lama sudah tidak valid)
        await SecureStore.setItemAsync('access_token', data.access_token);
        await SecureStore.setItemAsync('refresh_token', data.refresh_token);
        error.config.headers.Authorization = `Bearer ${data.access_token}`;
        return api.request(error.config);
      } catch {
        await SecureStore.deleteItemAsync('access_token');
        await SecureStore.deleteItemAsync('refresh_token');
        // Navigate ke login screen
      }
    }
    return Promise.reject(error);
  }
);

export default api;
```

---

## 9. Enum & Konstanta Referensi

### User Role
| Nilai | Keterangan |
|-------|------------|
| `wisatawan` | Turis (default setelah register) |
| `pedagang` | Merchant (setelah register merchant) |
| `admin` | Admin internal |

### Merchant Category
| Nilai | Keterangan |
|-------|------------|
| `KULINER_PANAS` | Makanan/minuman panas |
| `KULINER_DINGIN` | Minuman/makanan dingin |
| `KERAJINAN` | Kerajinan tangan |
| `LAINNYA` | Selain kategori di atas |

### Merchant Status (DB)
| Nilai | Keterangan |
|-------|------------|
| `pending` | Menunggu verifikasi admin |
| `active` | Aktif (saat ini tidak memblokir fitur) |
| `suspended` | Diblokir |

### Itinerary Status
| Nilai | Keterangan |
|-------|------------|
| `draft` | Baru dibuat, belum dimulai |
| `active` | Sedang berjalan (setelah `PATCH /start`) |
| `completed` | Selesai |

### Event Genre
| Nilai |
|-------|
| `cultural` |
| `sports` |
| `convention` |
| `concert` |
| `festival` |

### Event Status
| Nilai | Keterangan |
|-------|------------|
| `pending_review` | Menunggu review admin |
| `approved` | Disetujui — tampil di publik |
| `rejected` | Ditolak |

### Discount Type (Promo)
| Nilai | Keterangan |
|-------|------------|
| `percentage` | Diskon persentase (misal: 20%) |
| `fixed_amount` | Diskon nominal tetap (misal: Rp5.000) |

### Redemption Status
| Nilai | Keterangan |
|-------|------------|
| `pending` | Kode belum dipakai |
| `redeemed` | Sudah dikonfirmasi merchant |
| `expired` | Kode kedaluwarsa (>15 menit) |

### Source Type (Catalog Item)
| Nilai | Keterangan |
|-------|------------|
| `photo` | Dari hasil AI (Gemini Vision) |
| `manual` | Ditambah/diedit sendiri oleh merchant |

---

> *Dokumen ini diperbarui berdasarkan codebase aktual branch `main` — Blusukan BE (BytesFest 2026)*  
> *Terakhir diperbarui: 22 Juli 2026*
