from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from uuid import UUID

from app.core.security import JWTBearer
from app.db.session import get_db
from app.core.exceptions import ItineraryNotFoundException
from app.modules.auth.models import User
from app.modules.routing.models import Itinerary
from app.modules.routing.schemas import GenerateItineraryRequest, ItineraryResponse
from app.modules.routing.service import routing_service

router = APIRouter(prefix="/itineraries", tags=["Itineraries"])

@router.post("", response_model=ItineraryResponse, status_code=status.HTTP_201_CREATED)
async def generate_itinerary(
    request: GenerateItineraryRequest,
    current_user: User = Depends(JWTBearer()),
    db: AsyncSession = Depends(get_db)
):
    """
    Men-generate itinerary (Dolan Mode) berdasarkan input natural language dari turis.
    Menggunakan AI untuk parsing kebutuhan dan OSRM untuk routing.
    """
    try:
        itinerary = await routing_service.generate_itinerary(
            db=db,
            user_id=current_user.id,
            raw_query=request.raw_query,
            current_lat=request.current_lat,
            current_lon=request.current_lon
        )
        return itinerary
    except Exception as e:
        # Pengecualian turunan HTTPException (seperti RoutingNoMerchantsException) 
        # akan otomatis di-handle FastAPI dan dikembalikan ke client tanpa masuk ke blok ini 
        # jika tidak kita tangkap. Jadi kita tangkap error umum saja.
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

@router.get("/{itinerary_id}", response_model=ItineraryResponse)
async def get_itinerary(
    itinerary_id: UUID,
    current_user: User = Depends(JWTBearer()),
    db: AsyncSession = Depends(get_db)
):
    """
    Mendapatkan detail itinerary berdasarkan ID.
    """
    result = await db.execute(
        select(Itinerary).where(Itinerary.id == itinerary_id, Itinerary.user_id == current_user.id)
    )
    itinerary = result.scalars().first()
    
    if not itinerary:
        raise ItineraryNotFoundException()
        
    return itinerary

@router.patch("/{itinerary_id}/start")
async def start_itinerary(
    itinerary_id: UUID,
    current_user: User = Depends(JWTBearer()),
    db: AsyncSession = Depends(get_db)
):
    """
    Mengubah status itinerary dari draft/active menjadi in_progress/started.
    (Untuk tracking status saat turis mulai jalan).
    """
    result = await db.execute(
        select(Itinerary).where(Itinerary.id == itinerary_id, Itinerary.user_id == current_user.id)
    )
    itinerary = result.scalars().first()
    
    if not itinerary:
        raise ItineraryNotFoundException()
        
    itinerary.status = "active"
    await db.commit()
    
    return {"message": "Itinerary started", "id": str(itinerary_id)}
