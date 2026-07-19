# Blusukan API — Panduan Lengkap untuk Tim Frontend

> **Base URL:** `https://<domain>/api`
> **API Docs (Swagger):** `https://<domain>/api/docs`
> **Tech Stack FE yang direkomendasikan:** React Native (Expo) + Axios / TanStack Query

---

## Daftar Isi

1. [Konvensi & Aturan Umum](#1-konvensi--aturan-umum)
2. [Autentikasi (Auth Flow)](#2-autentikasi-auth-flow)
3. [Merchant — Onboarding & Profil (Bakul Mode)](#3-merchant--onboarding--profil-bakul-mode)
4. [Catalog — Ingest Menu via Foto (Bakul Mode)](#4-catalog--ingest-menu-via-foto-bakul-mode)
5. [Itinerary — Generate Rute Wisata (Dolan Mode)](#5-itinerary--generate-rute-wisata-dolan-mode)
6. [Events — Kalender Acara (Publik)](#6-events--kalender-acara-publik)
7. [POS & Transaksi (Bakul Mode)](#7-pos--transaksi-bakul-mode)
8. [Gamification — Stamp & Promo (Keduanya)](#8-gamification--stamp--promo-keduanya)
9. [Inventory — Rekomendasi Stok (Bakul Mode)](#9-inventory--rekomendasi-stok-bakul-mode)
10. [Error Handling](#10-error-handling)
11. [Enum & Konstanta Referensi](#11-enum--konstanta-referensi)

---

## 1. Konvensi & Aturan Umum

### Prefix URL
Semua endpoint diawali `/api`. Contoh: `/api/auth/login`, `/api/merchants/me`.

### Autentikasi Header
Setiap request ke endpoint *protected* wajib menyertakan header:
```
Authorization: Bearer <access_token>
```
Simpan `access_token` dan `refresh_token` di `SecureStore` (Expo) setelah login.

### Format Tanggal
Semua field tanggal/waktu menggunakan format **ISO 8601 UTC**: `2026-07-20T12:00:00Z`

### Role User
| Role | Nilai | Keterangan |
|------|-------|------------|
| Wisatawan | `wisatawan` | User default setelah register |
| Pedagang | `pedagang` | Setelah menyelesaikan `POST /merchants/register` |
| Admin | `admin` | Hanya untuk admin internal |

### Petunjuk Penting Token
Setelah `POST /merchants/register`, backend mengembalikan **token baru** dengan `role: "pedagang"`. FE **wajib** mengganti token lama dengan token baru ini agar role merchant aktif di sesi berikutnya.

---

## 2. Autentikasi (Auth Flow)

### Flow Registrasi & Login

```
Register → Login → Simpan { access_token, refresh_token, user } → Gunakan access_token di setiap request
```

Jika `access_token` expired (error `401`), gunakan `refresh_token` untuk mendapatkan token baru via `POST /auth/refresh`.

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
  "refresh_token": "eyJhbGciOiJIUzI1NiJ9...",
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

**Response `200`:** _(Sama dengan response register)_

---

### `POST /api/auth/refresh`
Mendapatkan access_token baru tanpa login ulang.

**Request Body:**
```json
{
  "refresh_token": "<refresh_token>"
}
```

**Response `200`:** _(Sama dengan response login)_

---

### `POST /api/auth/logout`
Invalidasi refresh_token. Hapus semua token dari storage setelah ini.

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
Mengambil data profil user yang sedang login.

**Header:** `Authorization: Bearer <access_token>` ✅

**Response `200`:** _(Sama dengan objek `user` di dalam response login)_

---

### `PATCH /api/auth/me`
Update data profil user (saat ini hanya `full_name`).

**Header:** `Authorization: Bearer <access_token>` ✅

**Request Body:**
```json
{
  "full_name": "Nama Baru"
}
```

**Response `200`:** _(Objek `UserResponse` yang sudah diupdate)_

---

## 3. Merchant — Onboarding & Profil (Bakul Mode)

### Flow Onboarding Bakul

```
User Login (role: wisatawan)
  → POST /merchants/register (kirim data toko)
  → Response membawa token BARU dengan role "pedagang"
  → Simpan token baru, user sekarang adalah Pedagang
```

> [!IMPORTANT]
> `POST /merchants/register` hanya bisa dipanggil SEKALI per user. Jika dipanggil dua kali, server akan mengembalikan error karena sudah ada merchant profile (`has_merchant_profile: true`).

---

### `POST /api/merchants/register`
Mendaftarkan toko baru. Mengubah role user dari `wisatawan` menjadi `pedagang`.

**Header:** `Authorization: Bearer <access_token>` ✅

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

**Field `category` (Enum):**
| Nilai | Keterangan |
|-------|------------|
| `KULINER_PANAS` | Makanan/minuman panas |
| `KULINER_DINGIN` | Minuman dingin, es |
| `KERAJINAN` | Produk kerajinan tangan |
| `LAINNYA` | Selain kategori di atas |

**Response `201`:** _(Token baru + data merchant — struktur sama dengan login response tapi token sudah ter-upgrade ke role `pedagang`)_

---

### `GET /api/merchants/me`
Mengambil profil toko milik user yang sedang login.

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
  "created_at": "2026-07-20T10:00:00Z",
  "updated_at": null,
  "latitude": -7.5660,
  "longitude": 110.8203
}
```

> [!NOTE]
> **Tentang `is_verified`:** Field ini ada di response tapi saat ini **tidak memblokir fitur apapun** di backend. Merchant baru langsung bisa mengakses semua fitur (POS, catalog, dll) meskipun `is_verified: false`. Endpoint admin untuk verifikasi merchant belum diimplementasikan.
>
> **Rekomendasi UX di FE:** Cukup tampilkan badge informatif saja:
> - `is_verified: false` → Badge "Belum Terverifikasi" (kuning/abu)
> - `is_verified: true` → Badge "Terverifikasi ✓" (hijau)
>
> **Jangan** memblokir akses fitur berdasarkan field ini.

---

## 4. Catalog — Ingest Menu via Foto (Bakul Mode)

### Flow Ingest Catalog (2 Langkah)

```
Step 1: POST /merchants/{id}/catalog/ingest  → Upload foto menu
          ↓ Backend kirim ke Gemini Vision API
          ↓ Gemini ekstrak daftar item sebagai "Draft"
          Response: { draft_items: [...] }

Step 2: Tampilkan draft_items ke merchant untuk dikoreksi/dikonfirmasi
          ↓ Merchant edit/tambah/hapus di layar
Step 3: POST /merchants/{id}/catalog/confirm → Kirim hasil final
          Response: Daftar menu yang sudah tersimpan di DB
```

> [!NOTE]
> `{id}` pada URL adalah **merchant_id** milik merchant yang login. Ambil dari `GET /merchants/me`.

---

### `POST /api/merchants/{id}/catalog/ingest`
Upload foto menu. Backend akan menggunakan Gemini Vision untuk membaca & mengekstrak menu menjadi list draft item.

**Header:** `Authorization: Bearer <access_token>` ✅
**Content-Type:** `multipart/form-data`

**Form Data:**
| Field | Tipe | Keterangan |
|-------|------|------------|
| `file` | `File` | File gambar (JPG/PNG), maks 10MB |

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

> [!TIP]
> Simpan `image_url` dari response ini. Anda perlu mengirimkannya kembali di step `confirm` agar gambar terhubung ke catalog item.

---

### `POST /api/merchants/{id}/catalog/confirm`
Menyimpan item catalog yang sudah dikonfirmasi merchant ke database.

**Header:** `Authorization: Bearer <access_token>` ✅
**Content-Type:** `application/json`

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

**Field `source_type`:** `"photo"` jika dari hasil AI, `"manual"` jika ditambah/diedit sendiri oleh merchant.

**Response `201`:** Array dari `CatalogItemResponse`
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

## 5. Itinerary — Generate Rute Wisata (Dolan Mode)

### Flow Generate Itinerary

```
User ketik permintaan natural language: "mau makan soto sama jajan kurang dari 50rb, 2 jam"
  → POST /itineraries (kirim teks + koordinat GPS saat ini)
  → Backend: Gemini parsing teks → SAW scoring merchants → OSRM routing
  → Response: Itinerary lengkap dengan waypoints + GeoJSON rute
  → FE render di peta (gunakan react-native-maps / mapbox-gl)
```

> [!IMPORTANT]
> Endpoint ini **bisa butuh waktu 3-8 detik** karena melibatkan Gemini API + OSRM. Tampilkan loading indicator yang informatif di FE!

---

### `POST /api/itineraries`
Generate itinerary baru berdasarkan input turis.

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
  "raw_query": "mau makan soto dan cari oleh-oleh batik, budget 100rb, 2 jam aja",
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
      [110.8180, -7.5620],
      [110.8250, -7.5700]
    ]
  },
  "estimated_duration_minutes": 95,
  "status": "draft",
  "created_at": "2026-07-20T10:00:00Z"
}
```

**Cara Render di Peta (React Native Maps):**
```javascript
import MapView, { Polyline, Marker } from 'react-native-maps';

// ⚠️ PENTING: GeoJSON pakai [lon, lat], bukan [lat, lon]!
// wp.lat dan wp.lon di waypoints sudah benar dan boleh langsung dipakai.
const routeCoords = itinerary.route_geojson.coordinates.map(([lon, lat]) => ({
  latitude: lat,
  longitude: lon,
}));

<MapView>
  {/* Garis rute jalan kaki mengikuti jalan nyata (dari OSRM) */}
  <Polyline
    coordinates={routeCoords}
    strokeColor="#FF6B35"
    strokeWidth={4}
  />

  {/* Marker untuk setiap toko tujuan */}
  {itinerary.waypoints.map((wp) => (
    <Marker
      key={wp.merchant_id}
      coordinate={{ latitude: wp.lat, longitude: wp.lon }}
      title={`${wp.order}. ${wp.name}`}
      description={wp.category}
    />
  ))}
</MapView>
```

### Penjelasan `route_geojson` (OSRM)

Backend memanggil **OSRM** (profil `foot` / jalan kaki) dengan parameter `geometries=geojson&overview=full`. Kata `overview=full` meminta OSRM mengembalikan **seluruh titik-titik koordinat mengikuti kontur jalan nyata**, bukan garis lurus antar toko.

Hasilnya adalah `LineString` yang bisa berisi **ratusan koordinat** — inilah yang harus di-render sebagai `<Polyline>` di peta.

**Contoh `route_geojson` asli dari OSRM (banyak titik jalan):**
```json
{
  "type": "LineString",
  "coordinates": [
    [110.8203, -7.5660],
    [110.8200, -7.5655],
    [110.8195, -7.5648],
    [110.8187, -7.5635],
    [110.8180, -7.5620],
    "...ratusan titik mengikuti belokan jalan..."
  ]
}
```

> [!WARNING]
> **Jika OSRM mati** (misalnya environment dev tanpa Docker), backend otomatis menggunakan **fallback mock** yang hanya menghubungkan titik-titik dengan **garis lurus** (bukan jalan nyata). Cirinya: `coordinates` hanya berisi tepat sejumlah waypoint, tidak ada titik jalan di antaranya. Pastikan OSRM running di production!

**Perbedaan `route_geojson` vs `waypoints`:**
| Field | Isi | Digunakan untuk |
|-------|-----|-----------------|
| `route_geojson.coordinates` | Ratusan titik jalan dari OSRM `[lon, lat]` | Render `<Polyline>` (garis rute) |
| `waypoints[].lat` / `waypoints[].lon` | Koordinat titik toko tujuan | Render `<Marker>` (pin toko) |
| `waypoints[].order` | Urutan kunjungan (1, 2, 3...) | Label nomor di marker |
| `waypoints[].score` | Skor SAW merchant (0.0–1.0) | Bisa ditampilkan sebagai badge "rating blusukan" |
| `waypoints[].predicted_stock` | Estimasi stok hari ini (bisa null) | Info stok di card merchant |



**Field `status` pada Itinerary:**
| Nilai | Keterangan |
|-------|------------|
| `draft` | Baru dibuat, belum dimulai |
| `active` | Sedang berjalan (setelah PATCH /start) |
| `completed` | Selesai |

---

### `GET /api/itineraries/{itinerary_id}`
Mengambil detail itinerary berdasarkan ID.

**Header:** `Authorization: Bearer <access_token>` ✅

**Response `200`:** _(Sama dengan response generate itinerary)_

---

### `PATCH /api/itineraries/{itinerary_id}/start`
Mengubah status itinerary menjadi `active` (ketika turis menekan tombol "Mulai Perjalanan").

**Header:** `Authorization: Bearer <access_token>` ✅

**Response `200`:**
```json
{
  "message": "Itinerary started",
  "id": "uuid-itinerary"
}
```

---

## 6. Events — Kalender Acara (Publik)

> [!NOTE]
> Endpoint ini **tidak memerlukan autentikasi** (publik). Digunakan untuk menampilkan daftar event di Solo Raya pada halaman eksplorasi.

---

### `GET /api/events`
Mengambil daftar semua event yang sudah diapprove admin.

**Query Params (Opsional):**
| Param | Tipe | Keterangan |
|-------|------|------------|
| `upcoming` | `boolean` | Jika `true`, hanya event yang belum berakhir |

**Contoh:** `GET /api/events?upcoming=true`

**Response `200`:** Array of `EventResponse`
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

**Field `genre` (Enum):**
`cultural` | `sports` | `convention` | `concert` | `festival`

---

### `GET /api/events/{event_id}`
Mengambil detail satu event.

**Response `200`:** _(Sama dengan satu objek di atas)_

---

## 7. POS & Transaksi (Bakul Mode)

### Flow Transaksi (dari sisi Merchant)

```
Turis datang ke warung
  → Turis menunjukkan itinerary ID (misal dari QR Code di app)
  → Merchant hitung total di kasir
  → Pembayaran dilakukan secara fisik (tunai / QRIS mandiri / dll) — DI LUAR SISTEM
  → Merchant konfirmasi pembayaran diterima:
      POST /merchants/{id}/transactions
        - linked_itinerary_id: diisi jika turis punya itinerary
  → Jika itinerary valid → Backend otomatis kasih STAMP ke turis
  → Response: stamp_awarded: true/false
```

---

### `POST /api/merchants/{id}/transactions`
Mencatat transaksi baru. Ini adalah endpoint utama POS.

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
| `nominal_value` | ✅ | Total harga transaksi dalam Rupiah |
| `item_reference` | ❌ | JSON bebas berisi detail item (untuk rekap merchant) |
| `linked_itinerary_id` | ❌ | ID itinerary turis → trigger stamp gamification |
| `client_reference_id` | ❌ | UUID unik dari FE untuk idempotency (cegah double submit) |

> [!TIP]
> **Idempotency:** Selalu generate UUID unik di FE sebelum submit (`uuid.v4()`). Jika request gagal & di-retry, kirim `client_reference_id` yang sama. Backend tidak akan mencatat transaksi duplikat.

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

> `stamp_awarded: true` → Stamp berhasil diberikan ke turis secara otomatis.

---

### `GET /api/merchants/{id}/transactions`
Riwayat transaksi merchant (paginasi).

**Header:** `Authorization: Bearer <access_token>` ✅

**Query Params:**
| Param | Default | Keterangan |
|-------|---------|------------|
| `page` | `1` | Halaman saat ini |
| `limit` | `20` | Jumlah item per halaman |

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

### `GET /api/merchants/{id}/transactions/summary`
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

## 8. Gamification — Stamp & Promo (Keduanya)

### Flow Gamification (Sisi Turis)

```
Turis bertransaksi di merchant via itinerary
  → stamp_awarded: true di response transaksi
  → GET /users/me/stamps  → Lihat total stamp yang dikumpulkan
  → GET /promos/available → Lihat promo yang bisa ditukar
  → POST /promos/{id}/redeem → Tukar stamp → Dapat kode kupon (berlaku 15 menit)
  → Tunjukkan kode ke kasir
  → Kasir konfirmasi via: POST /merchants/{mid}/promo-redemptions/{code}/confirm
```

---

### `GET /api/users/me/stamps`
Melihat semua stamp yang dimiliki wisatawan.

**Header:** `Authorization: Bearer <access_token>` ✅ *(Role: wisatawan)*

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

### `GET /api/promos/available`
Menampilkan promo yang bisa diklaim turis berdasarkan jumlah stamp yang dimiliki.

**Header:** `Authorization: Bearer <access_token>` ✅

**Response `200`:** Array of `PromoAvailableResponse`
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

### `POST /api/promos/{id}/redeem`
Tukar stamp dengan kode kupon promo. Kode berlaku **15 menit**.

**Header:** `Authorization: Bearer <access_token>` ✅
**Body:** _(Tidak ada body, `{id}` adalah promo_id dari URL)_

**Response `201`:**
```json
{
  "redemption_code": "A3F9C2B1",
  "expires_at": "2026-07-20T11:00:00Z"
}
```

> **UX:** Tampilkan `redemption_code` sebagai teks besar atau QR Code. Sertakan countdown timer sampai `expires_at`.

---

### `POST /api/merchants/{id}/promos` *(Merchant)*
Merchant membuat promo baru.

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

**Field `discount_type`:** `"percentage"` atau `"fixed_amount"`

**Response `201`:** Objek promo yang baru dibuat.

---

### `POST /api/merchants/{id}/promo-redemptions/{code}/confirm` *(Merchant)*
Kasir mengkonfirmasi kode kupon dari turis.

**Header:** `Authorization: Bearer <access_token>` ✅ *(Role: pedagang)*
**Body:** _(Tidak ada body, `{code}` adalah kode dari turis, contoh: `A3F9C2B1`)_

**Response `200`:**
```json
{
  "status": "redeemed"
}
```

**Nilai `status` yang mungkin:** `"pending"` | `"redeemed"` | `"expired"`

---

## 9. Inventory — Rekomendasi Stok (Bakul Mode)

### Flow Rekomendasi Stok

```
Merchant set baseline stok harian  →  PATCH /merchants/{id}/baseline-inventory
Setiap hari Celery task berjalan otomatis & menghitung saran stok
Merchant buka app →  GET /merchants/{id}/inventory-recommendations/today
Lihat rekomendasi stok berdasarkan cuaca & event sekitar
```

---

### `PATCH /api/merchants/{merchant_id}/baseline-inventory`
Merchant mengisi stok dasar harian (bahan baku awal).

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
> Kunci (key) bersifat bebas, sesuaikan dengan jenis bahan yang merchant track.

**Response `200`:**
```json
{
  "message": "Baseline inventory berhasil diperbarui."
}
```

---

### `GET /api/merchants/{merchant_id}/inventory-recommendations/today`
Mengambil rekomendasi stok hari ini.

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

## 10. Error Handling

### Format Error Standard
Semua error dikembalikan dalam format:
```json
{
  "detail": "Pesan error dalam Bahasa Indonesia"
}
```

### Error Umum
| HTTP Code | Keterangan | Yang Harus Dilakukan FE |
|-----------|------------|-------------------------|
| `400` | Input tidak valid / Constraint bisnis tidak terpenuhi | Tampilkan `detail` ke user |
| `401` | Token expired / tidak ada | Coba refresh token, jika gagal → redirect ke Login |
| `403` | Tidak punya akses (bukan owner) | Tampilkan error "Tidak diizinkan" |
| `404` | Data tidak ditemukan | Tampilkan halaman / state kosong |
| `409` | Konflik data (misal: stamp sudah diberikan) | Tampilkan pesan konflik |
| `422` | Validasi schema gagal | Periksa field yang dikirim |
| `429` | Rate limit tercapai | Tampilkan "Coba lagi beberapa saat" |
| `500` | Server error | Tampilkan pesan generik "Terjadi kesalahan" |

### Contoh Setup Axios Interceptor (React Native)
```javascript
import axios from 'axios';
import * as SecureStore from 'expo-secure-store';

const api = axios.create({ baseURL: 'https://<domain>/api' });

// Auto-inject token
api.interceptors.request.use(async (config) => {
  const token = await SecureStore.getItemAsync('access_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Auto-refresh token jika 401
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      const refreshToken = await SecureStore.getItemAsync('refresh_token');
      try {
        const { data } = await axios.post('/api/auth/refresh', { refresh_token: refreshToken });
        await SecureStore.setItemAsync('access_token', data.access_token);
        error.config.headers.Authorization = `Bearer ${data.access_token}`;
        return api.request(error.config); // Retry request
      } catch {
        // Refresh gagal → logout
        await SecureStore.deleteItemAsync('access_token');
        await SecureStore.deleteItemAsync('refresh_token');
        // Navigate to login screen
      }
    }
    return Promise.reject(error);
  }
);

export default api;
```

---

## 11. Enum & Konstanta Referensi

### User Role
| Nilai | Keterangan |
|-------|------------|
| `wisatawan` | Turis (default) |
| `pedagang` | Merchant |
| `admin` | Admin |

### Merchant Category
| Nilai | Keterangan |
|-------|------------|
| `KULINER_PANAS` | Makanan/minuman panas |
| `KULINER_DINGIN` | Minuman/makanan dingin |
| `KERAJINAN` | Kerajinan tangan |
| `LAINNYA` | Lainnya |

### Merchant Status
| Nilai | Keterangan |
|-------|------------|
| `pending` | Menunggu verifikasi admin |
| `active` | Aktif |
| `suspended` | Diblokir |

### Itinerary Status
| Nilai | Keterangan |
|-------|------------|
| `draft` | Baru dibuat |
| `active` | Sedang berjalan |
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
| `approved` | Disetujui (tampil publik) |
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
| `expired` | Kode kadaluarsa (>15 menit) |

---

*Dokumen ini dibuat berdasarkan codebase aktual `develop` branch — Blusukan BE (BytesFest 2026)*
*Terakhir diperbarui: 20 Juli 2026*
