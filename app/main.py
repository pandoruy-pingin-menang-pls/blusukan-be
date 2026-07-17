from fastapi import FastAPI

app = FastAPI(title="Blusukan API", version="1.0.0")

@app.get("/")
async def root():
    return {"message": "Sugeng rawuh ingkang Blusukan API!"}

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "Blusukan API"}