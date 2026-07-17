from fastapi import FastAPI, APIRouter

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

api_router = APIRouter(prefix="/api")

@api_router.get("/", tags=["Root"])
async def root():
    return {"message": "Sugeng rawuh ingkang Blusukan API!"}

@api_router.get("/health", tags=["System"])
async def health():
    return {"status": "healthy", "service": "Blusukan API"}

app.include_router(api_router)