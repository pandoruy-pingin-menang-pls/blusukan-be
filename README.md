# Blusukan Backend API

Sugeng Rawuh! This is the backend service for **Blusukan**, an event-driven dual-sided ecosystem connecting tourists (*Dolan Mode*) with hidden-gem MSMEs in Solo Raya (*Bakul Mode*). The system features predictive stocking, weighted routing, AI-powered catalog ingestion, and a stamp-based gamification engine.

Built for **BytesFest 2026: Decent Work and Economic Growth** by Team Pandoruy Pingin Menang Pls, Faculty of Computer Science, Universitas Indonesia.

---

## Tech Stack

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-async-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Supabase-336791?style=for-the-badge&logo=postgresql&logoColor=white)
![PostGIS](https://img.shields.io/badge/PostGIS-Spatial-2C7A3D?style=for-the-badge&logo=postgresql&logoColor=white)
![pgvector](https://img.shields.io/badge/pgvector-Semantic%20Search-4B32C3?style=for-the-badge&logo=postgresql&logoColor=white)
![Gemini API](https://img.shields.io/badge/Gemini%20API-AI%20Engine-8E75B2?style=for-the-badge&logo=googlegemini&logoColor=white)
![OSRM](https://img.shields.io/badge/OSRM-Routing%20Engine-6B4226?style=for-the-badge&logo=openstreetmap&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-Cache%20%26%20Queue-DC382D?style=for-the-badge&logo=redis&logoColor=white)
![Celery](https://img.shields.io/badge/Celery-Task%20Queue-37814A?style=for-the-badge&logo=celery&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Containerized-2496ED?style=for-the-badge&logo=docker&logoColor=white)

---

## About the Project

Blusukan addresses three core problems faced by informal MSMEs in Solo Raya during major events like festivals, concerts, and sports events:

1. **Mainstream Avenue Trap:** Tourists are directed only to main streets, leaving merchants in alleys invisible.
2. **Operational Blindness:** Merchants do not know how much stock to prepare for sudden events.
3. **High Friction Discovery:** Tourists find it difficult to discover authentic places beyond mainstream recommendations.

The solution is a single application with two user modes and an admin layer:

| Mode | User | Description |
|------|------|-------------|
| **Dolan Mode** | Wisatawan (Tourist) | Input natural language constraints → get a weighted itinerary to hidden-gem merchants |
| **Bakul Mode** | Pedagang (Merchant) | Onboard via photo → receive predictive stock recs → record QRIS transactions |
| **Admin** | Admin | Manage events via HITL review, seed data, trigger recalculations |

---

## Deployment

| Resource | URL |
|----------|-----|
| **Base API URL** | https://blusukan-be.up.railway.app/api |
| **Swagger UI** | https://blusukan-be.up.railway.app/api/docs |
| **ReDoc** | https://blusukan-be.up.railway.app/api/redoc |

---

## Project Structure

```text
app/
├── main.py                # FastAPI entrypoint, router registration
├── core/                  # Config, security (JWT/bcrypt), logging, exceptions
├── db/                    # Async engine, session factory, Alembic migrations
├── integrations/          # External clients: Gemini Vision, OSRM, Supabase Storage, Weather
├── modules/
│   ├── admin/             # Admin-only endpoints (event HITL review)
│   ├── auth/              # Register, login, refresh, logout, /me
│   ├── catalog/           # AI menu ingestion (ingest + confirm)
│   ├── credit_score/      # Merchant credit scoring
│   ├── events/            # Public event calendar
│   ├── gamification/      # Stamps, promos, redemptions
│   ├── inventory/         # Baseline stock + predictive recommendations
│   ├── merchant/          # Merchant onboarding + profile
│   ├── routing/           # Itinerary generation (Gemini + OSRM)
│   └── transactions/      # POS transaction logging
└── workers/               # Celery tasks (daily stock recalculation)
```

---

## Software Architecture (Modular Monolith)

| Layer | Responsibility |
|-------|----------------|
| **Routers** | Handle HTTP requests, validate input schemas, return responses |
| **Services** | Business logic, external API calls (Gemini, OSRM, Weather) |
| **Models** | SQLAlchemy ORM with PostGIS geometry types |
| **Workers** | Celery background tasks (scheduled stock recalculation) |

**Request Flow (Itinerary):**
```
Client → Router → Service (Gemini parse → PostGIS SAW scoring → OSRM route) → Itinerary DB → Response
```

---

## Key Design Principles

1. **Geospatial-First:** PostGIS natively handles merchant proximity, radii, and route geometry.
2. **Async by Default:** Heavy AI and routing work is async; Celery offloads scheduled batch processing.
3. **Zero-Friction Abstraction:** Gemini Vision converts unstructured photos/notes into structured catalog data.
4. **Weighted Routing:** OSRM edge weights are modified to de-prioritize mainstream roads and surface hidden alleys.
5. **Token Security:** Refresh tokens use rotation + reuse detection; compromised sessions are fully invalidated.
6. **Idempotency:** POS transactions accept a `client_reference_id` to prevent double-recording on retries.

---

## Running Locally

```bash
# 1. Clone the repo
git clone <repo-url>
cd blusukan-be

# 2. Create a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy and fill environment variables
cp .env.example .env

# 5. Run the server
uvicorn app.main:app --reload
```

After the server is running:
- Health check: http://127.0.0.1:8000/api/health
- Swagger UI: http://127.0.0.1:8000/api/docs

---

## Testing the API via Swagger - Phase Guide

Open Swagger UI at `/api/docs`. Click the **Authorize** button and paste `Bearer <access_token>` after logging in.

---

### Seed Testing Accounts

Run the seed script to create empty accounts:

```bash
venv\Scripts\python.exe -m scripts.seed_data
```

> **Note:** The seed data is already populated in the Railway deployment. If you are testing the live API, you can skip this step and use the accounts below.

> Merchant accounts (`warung`, `batik`, `jamu`) are created with the `wisatawan` role initially - the role will be upgraded to `pedagang` after Phase 2.

| Role | Email | Password | Notes |
|------|-------|----------|-------|
| **Admin** | `admin@blusukan.com` | `adminblusukan123` | Access to all `/admin/*` endpoints |
| **Merchant Candidate 1** | `warung@blusukan.com` | `pedagang123` | Will own Warung Soto |
| **Merchant Candidate 2** | `batik@blusukan.com` | `pedagang123` | Will own Batik Amanah |
| **Merchant Candidate 3** | `jamu@blusukan.com` | `pedagang123` | Will own Jamu Gendhis |
| **Tourist 1** | `turis@blusukan.com` | `wisatawan123` | For testing Dolan Mode |
| **Tourist 2** | `turis2@blusukan.com` | `wisatawan123` | Backup tourist account |

---

### Phase 1 - Login

**Account:** Any account can be used. Start with `turis@blusukan.com` for the tourist flow.

| Step | Method | Endpoint | Body / Notes |
|------|--------|----------|--------------|
| 1 | `POST` | `/api/auth/login` | `{ "email": "turis@blusukan.com", "password": "wisatawan123" }` |
| 2 | - | *(Authorize Swagger)* | Copy `access_token` → click **Authorize** → `Bearer <token>` |
| 3 | `GET` | `/api/auth/me` | Verify: `role` should be `wisatawan`, `has_merchant_profile: false` |

> **Token expired?** Send `POST /api/auth/refresh` with `{ "refresh_token": "..." }` to rotate tokens without re-logging in.

---

### Phase 2 - Merchant Onboarding (Bakul Mode)

**Account:** `warung@blusukan.com` / `pedagang123`

Log in first, then register the store. The role will be **automatically upgraded** from `wisatawan` → `pedagang`.

| Step | Method | Endpoint | Body / Notes |
|------|--------|----------|--------------|
| 1 | `POST` | `/api/auth/login` | `{ "email": "warung@blusukan.com", "password": "pedagang123" }` |
| 2 | `POST` | `/api/merchants/register` | See body below |
| 3 | - | *(Swap token)* | The response contains a **new token** with `role: pedagang`. Re-authorize in Swagger. |
| 4 | `GET` | `/api/merchants/me` | Note down the merchant `id` - used in all subsequent steps |

**Body for step 2:**
```json
{
  "name": "Warung Soto Pak Darmo",
  "description": "Soto ayam kampung khas Solo, tersembunyi di gang Pasar Kliwon.",
  "category": "KULINER_PANAS",
  "address": "Gang Beton No. 7, Pasar Kliwon, Surakarta",
  "latitude": -7.5622,
  "longitude": 110.8181
}
```

> Repeat Phase 2 with `batik@blusukan.com` (category: `KERAJINAN`) and `jamu@blusukan.com` (category: `KULINER_DINGIN`) to have 3 active merchants.

**Merchant Categories:** `KULINER_PANAS` | `KULINER_DINGIN` | `KERAJINAN` | `LAINNYA`

---

### Phase 3 - Catalog Ingestion via AI (Bakul Mode)

**Account:** `warung@blusukan.com` (must be `pedagang`, must have a `merchant_id`)

| Step | Method | Endpoint | Body / Notes |
|------|--------|----------|--------------|
| 1 | `POST` | `/api/merchants/{merchant_id}/catalog/ingest` | `multipart/form-data`, field `file` (JPG/PNG menu photo, ≤ 10MB). Gemini Vision will extract items. |
| 2 | - | *(View `draft_items`)* | Save `image_url` from response - mandatory to send in step 3. |
| 3 | `POST` | `/api/merchants/{merchant_id}/catalog/confirm` | See body below |
| 4 | `GET` | `/api/merchants/{merchant_id}/catalog` | Verify items are saved (public, no auth needed). |

**Body for step 3** (adjust based on `draft_items` from step 1):
```json
{
  "image_url": "<image_url from ingest response>",
  "items": [
    { "item_name": "Soto Ayam Kampung", "price": 15000, "category": "culinary", "source_type": "photo" },
    { "item_name": "Es Teh Manis",      "price": 4000,  "category": "beverage", "source_type": "manual" }
  ]
}
```

> No photo file available? Use any image (e.g., a restaurant menu photo from the internet). Gemini will still extract any readable text.

---

### Phase 4 - Events & Admin HITL (Admin)

**Account:** `admin@blusukan.com` / `adminblusukan123`

| Step | Method | Endpoint | Body / Notes |
|------|--------|----------|--------------|
| 1 | `POST` | `/api/auth/login` | `{ "email": "admin@blusukan.com", "password": "adminblusukan123" }` → Authorize |
| 2 | `POST` | `/api/admin/events` | Create a new event - see body below |
| 3 | `GET` | `/api/admin/events?status=pending_review` | Check for events waiting for review |
| 4 | `PATCH` | `/api/admin/events/{event_id}/review` | `{ "action": "approve" }` |
| 5 | `GET` | `/api/events?upcoming=true` | Verify event appears in the public endpoint |

**Body for step 2:**
```json
{
  "name": "Solo Batik Carnival 2026",
  "genre": "festival",
  "venue_name": "Jl. Slamet Riyadi, Surakarta",
  "latitude": -7.5560,
  "longitude": 110.8220,
  "estimated_attendee_count": 8000,
  "start_datetime": "2026-08-01T16:00:00Z",
  "end_datetime": "2026-08-01T22:00:00Z"
}
```

> Events created directly by the admin will automatically have an `approved` status. To test the review flow, create an event via another API endpoint, then review it via steps 3-4.

**Event Genres:** `cultural` | `sports` | `convention` | `concert` | `festival`

---

### Phase 5 - Inventory & Predictive Stock (Bakul Mode)

**Account:** `warung@blusukan.com` (must be `pedagang`)

| Step | Method | Endpoint | Body / Notes |
|------|--------|----------|--------------|
| 1 | `PATCH` | `/api/merchants/{merchant_id}/baseline-inventory` | Set daily base stock - see body below |
| 2 | `GET` | `/api/merchants/{merchant_id}/inventory-recommendations/today` | Stock recommendations for today (requires active event & running Celery) |
| 3 | `POST` | `/api/admin/inventory-recommendations/recalculate` | *(Use admin account)* Trigger Celery to recalculate immediately |

**Body for step 1:**
```json
{
  "baseline_inventory": {
    "nasi": 50,
    "ayam": 30,
    "minuman": 80
  }
}
```

> Keys are arbitrary, adjust them according to the materials you want to track. Recommendations are calculated automatically every day by Celery based on upcoming events & weather.

---

### Phase 6 - Generate Itinerary / Dolan Mode (Tourist)

**Account:** `turis@blusukan.com` / `wisatawan123`

| Step | Method | Endpoint | Body / Notes |
|------|--------|----------|--------------|
| 1 | `POST` | `/api/auth/login` | `{ "email": "turis@blusukan.com", "password": "wisatawan123" }` → Authorize |
| 2 | `POST` | `/api/itineraries` | See body below - takes 3–8 seconds |
| 3 | `GET` | `/api/itineraries/{itinerary_id}` | Fetch the details of the newly generated itinerary |
| 4 | `PATCH` | `/api/itineraries/{itinerary_id}/start` | Change status → `active` (simulating "starting the journey") |

**Body for step 2:**
```json
{
  "raw_query": "mau makan soto dan cari oleh-oleh batik, budget 100rb, 2 jam aja",
  "current_lat": -7.5660,
  "current_lon": 110.8203
}
```

> Requires at least 1 active merchant in the DB (Phase 2 completed) for the itinerary to be generated. If OSRM is not running, routing will fall back to a straight line.

---

### Phase 7 - POS & Transactions (Bakul Mode)

**Account:** `warung@blusukan.com` (must be `pedagang`)

| Step | Method | Endpoint | Body / Notes |
|------|--------|----------|--------------|
| 1 | `POST` | `/api/merchants/{merchant_id}/transactions` | Log a transaction + link to a tourist itinerary to trigger a stamp |
| 2 | `GET` | `/api/merchants/{merchant_id}/transactions` | Transaction history (params: `page`, `limit`) |
| 3 | `GET` | `/api/merchants/{merchant_id}/transactions/summary` | Today's revenue & transaction count |

**Body for step 1** (replace `linked_itinerary_id` with ID from Phase 6):
```json
{
  "nominal_value": 19000,
  "item_reference": {
    "items": [
      { "name": "Soto Ayam Kampung", "qty": 1, "price": 15000 },
      { "name": "Es Teh Manis",      "qty": 1, "price": 4000  }
    ]
  },
  "linked_itinerary_id": "<itinerary_id from Phase 6>",
  "client_reference_id": "test-tx-001"
}
```

> If `linked_itinerary_id` is valid, the response will include `"stamp_awarded": true` - a stamp is automatically given to the tourist.

---

### Phase 8 - Gamification: Stamps & Promos

#### Merchant creates a promo - `warung@blusukan.com`

| Step | Method | Endpoint | Body / Notes |
|------|--------|----------|--------------|
| 1 | `POST` | `/api/merchants/{merchant_id}/promos` | Create a promo that requires a stamp |

**Body:**
```json
{
  "title": "Free Iced Tea for 3 Stamps",
  "discount_type": "fixed_amount",
  "discount_value": 4000,
  "stamp_required_count": 1,
  "valid_until": "2026-12-31T23:59:59Z"
}
```

> Set `stamp_required_count: 1` to immediately test it after 1 transaction in Phase 7.

#### Tourist claims a stamp & redeems - `turis@blusukan.com`

| Step | Method | Endpoint | Body / Notes |
|------|--------|----------|--------------|
| 1 | `GET` | `/api/users/me/stamps` | Check accumulated stamps (from Phase 7) |
| 2 | `GET` | `/api/promos/available` | List promos available to claim - copy `promo_id` |
| 3 | `POST` | `/api/promos/{promo_id}/redeem` | Exchange stamp → get `redemption_code` (TTL 15 mins) |

#### Cashier confirms - `warung@blusukan.com`

| Step | Method | Endpoint | Body / Notes |
|------|--------|----------|--------------|
| 1 | `POST` | `/api/merchants/{merchant_id}/promo-redemptions/{code}/confirm` | `{code}` = 8-character code from tourist, e.g., `A3F9C2B1` |