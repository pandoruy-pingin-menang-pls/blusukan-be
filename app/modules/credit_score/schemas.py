from typing import List, Optional

from pydantic import BaseModel, Field


class CreditScoreHistoryItem(BaseModel):
    period: str = Field(
        ..., description="Format: YYYY-MM", json_schema_extra={"example": "2026-06"}
    )
    score: int = Field(
        ..., description="Nilai skor dari 0-1000", json_schema_extra={"example": 850}
    )


class CreditScoreResponse(BaseModel):
    current_score: Optional[int] = Field(
        None, description="Skor saat ini. Kosong jika data tidak mencukupi."
    )
    data_status: str = Field(..., description="'sufficient' atau 'insufficient_data'")
    history: List[CreditScoreHistoryItem] = Field(
        default_factory=list, description="Riwayat skor tiap periode"
    )
