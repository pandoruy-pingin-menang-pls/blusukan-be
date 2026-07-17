# Blusukan Backend API

Sugeng Rawuh! This is the backend service for Blusukan, an event-driven dual-sided ecosystem connecting tourists (Dolan Mode) with hidden-gem MSMEs in Solo Raya (Bakul Mode). The system features predictive stocking and weighted routing.

Built for **BytesFest 2026: Decent Work and Economic Growth** by Team Pandoruy Pingin Menang Pls, Faculty of Computer Science, Universitas Indonesia.

## Tech Stack

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-async-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Supabase-336791?style=for-the-badge&logo=postgresql&logoColor=white)
![PostGIS](https://img.shields.io/badge/PostGIS-Spatial-2C7A3D?style=for-the-badge&logo=postgresql&logoColor=white)
![pgvector](https://img.shields.io/badge/pgvector-Semantic%20Search-4B32C3?style=for-the-badge&logo=postgresql&logoColor=white)
![Gemini API](https://img.shields.io/badge/Gemini%20API-AI%20Engine-8E75B2?style=for-the-badge&logo=googlegemini&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-Orchestration-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white)
![OSRM](https://img.shields.io/badge/OSRM-Routing%20Engine-6B4226?style=for-the-badge&logo=openstreetmap&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-Cache%20%26%20Queue-DC382D?style=for-the-badge&logo=redis&logoColor=white)
![Celery](https://img.shields.io/badge/Celery-Task%20Queue-37814A?style=for-the-badge&logo=celery&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Containerized-2496ED?style=for-the-badge&logo=docker&logoColor=white)

## About the Project

Blusukan addresses three main problems faced by informal MSMEs in Solo Raya during major events like festivals, concerts, and sports events:

1. **Mainstream Avenue Trap:** Tourists are directed only to main streets, leaving merchants in alleys invisible.
2. **Operational Blindness:** Merchants do not know how much stock to prepare for sudden events.
3. **High Friction Discovery:** Tourists find it difficult to discover authentic places beyond mainstream recommendations.

The solution is a single application with two modes:

* **Dolan Mode** (for tourists): Users input natural language constraints such as time, budget, and interests. The system then generates an itinerary directing them to hidden-gem merchants using weighted routing.
* **Bakul Mode** (for merchants): Merchants can onboard easily using photos or voice notes. They receive daily predictive stock recommendations based on events and weather, and can record transactions with zero platform fees via direct QRIS payments.

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

# 4. Copy environment variables
cp .env.example .env
# Fill in the values with your credentials

# 5. Run the server
uvicorn app.main:app --reload
```

After the server is running, check:
* Health check: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)
* Swagger API Docs: [http://127.0.0.1:8000/api/docs](http://127.0.0.1:8000/api/docs)

## Project Structure (Summary)

```text
app/
├── main.py            # FastAPI entrypoint
├── core/              # Config, security, and logging
├── db/                # Database connections and migrations
├── modules/           # Business logic per feature (auth, merchants, routing, etc.)
├── integrations/      # External clients (Gemini, OSRM, Supabase Storage)
└── workers/           # Background jobs (Celery)
```

## Software Architecture (Modular Monolith)

1. **Controllers (Routers):** Handle incoming HTTP requests and responses.
2. **Services (Business Logic):** Core logic and external API orchestration.
3. **Repositories (Data Access):** Database operations and query abstraction.
4. **Workers:** Background task processing via Celery.

**Request Flow Example (Itinerary):**
Client Request -> Router -> Service (calls Gemini, PostGIS, OSRM) -> Formatted Response.

## Key Design Principles

1. **Geospatial-First:** Uses PostGIS to natively handle map distances and intersections.
2. **Async by Default:** Offloads heavy AI and routing calculations to Celery workers.
3. **Zero-Friction Abstraction:** Uses Gemini to process unstructured photos and voice notes into structured data.
4. **Weighted Routing:** Modifies OSRM edge weights to prioritize hidden alleys over mainstream roads.