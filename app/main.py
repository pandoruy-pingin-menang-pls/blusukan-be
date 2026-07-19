from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.modules.auth.router import router as auth_router
from app.modules.catalog.router import router as catalog_router
from app.modules.events.router import router as event_router
from app.modules.gamification.router import (
    merchant_promo_router,
    user_gamification_router,
)
from app.modules.inventory.router import admin_router as inventory_admin_router
from app.modules.inventory.router import router as inventory_router
from app.modules.merchant.router import router as merchant_router
from app.modules.routing.router import router as routing_router
from app.modules.transactions.router import router as transactions_router

description = """
Blusukan API (BytesFest 2026)

Supporting a dual-mode ecosystem:
* **Dolan Mode (B2C)**: Tourist itineraries & hidden gems.
* **Bakul Mode (B2B)**: Predictive stocking for MSMEs & QRIS settlement.
"""

app = FastAPI(
    title="Blusukan API",
    description=description,
    version="1.0.0",
    contact={
        "name": "Blusukan Team",
    },
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Izinkan Frontend (FE) untuk menembak API ini tanpa diblokir oleh CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Ganti dengan domain FE Anda saat production (misal: ["https://blusukan.com"])
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_router = APIRouter(prefix="/api")
api_router.include_router(auth_router)
api_router.include_router(merchant_router)
api_router.include_router(catalog_router)
api_router.include_router(event_router)
api_router.include_router(routing_router)
api_router.include_router(inventory_router)
api_router.include_router(inventory_admin_router)
api_router.include_router(transactions_router)
api_router.include_router(merchant_promo_router)
api_router.include_router(user_gamification_router)

@api_router.get("/", tags=["Root"])
async def root():
    return {"message": "Sugeng rawuh ingkang Blusukan API!"}

@api_router.get("/health", tags=["System"])
async def health():
    return {"status": "healthy", "service": "Blusukan API"}

app.include_router(api_router)
