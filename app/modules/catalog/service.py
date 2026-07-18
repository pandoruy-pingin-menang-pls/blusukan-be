from datetime import date
from typing import List

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import IngestLimitReachedException
from app.integrations.gemini_client import gemini_client
from app.integrations.supabase_storage import supabase_storage
from app.modules.catalog.models import MerchantCatalogItem
from app.modules.catalog.schemas import (
    CatalogConfirmRequest,
    CatalogIngestResponse,
    DraftItem,
)
from app.modules.merchant.models import Merchant

MAX_DAILY_INGEST = 5

class CatalogService:
    @staticmethod
    async def ingest_menu(db: AsyncSession, merchant: Merchant, file: UploadFile) -> CatalogIngestResponse:
        today = date.today()

        # Reset limit counter if it's a new day
        if merchant.ingest_count_reset_at is None or merchant.ingest_count_reset_at < today:
            merchant.daily_ingest_count = 0
            merchant.ingest_count_reset_at = today

        # Check limit
        if merchant.daily_ingest_count >= MAX_DAILY_INGEST:
            raise IngestLimitReachedException()

        merchant.daily_ingest_count += 1
        await db.commit()

        # Read file bytes
        file_bytes = await file.read()
        mime_type = file.content_type or "image/jpeg"

        # 1. Upload to Supabase Storage
        image_url = await supabase_storage.upload_menu_image(file_bytes, mime_type, str(merchant.id))

        # 2. Extract Data using Gemini
        raw_items = await gemini_client.extract_menu_from_image(file_bytes, mime_type)

        draft_items = []
        for item in raw_items:
            # Defensive check
            if "item_name" in item:
                draft = DraftItem(
                    item_name=item["item_name"],
                    price=item.get("price"),
                    category=item.get("category", "culinary")
                )
                draft_items.append(draft)

        return CatalogIngestResponse(
            message="Data berhasil diekstrak. Silakan periksa dan konfirmasi.",
            image_url=image_url,
            draft_items=draft_items
        )

    @staticmethod
    async def confirm_catalog(db: AsyncSession, merchant: Merchant, request: CatalogConfirmRequest) -> List[MerchantCatalogItem]:
        inserted_items = []

        for item_data in request.items:
            # Generate embedding
            # In a real heavy system, this might be background processed,
            # but for MVP and Gemini's speed, synchronous is acceptable.
            embedding = await gemini_client.embed_text(f"{item_data.item_name} - {item_data.category}")

            # Confidence logic: low if price is missing
            confidence = "low" if item_data.price is None else "high"

            new_item = MerchantCatalogItem(
                merchant_id=merchant.id,
                item_name=item_data.item_name,
                price=item_data.price,
                category=item_data.category,
                source_type=item_data.source_type,
                confidence=confidence,
                embedding=embedding,
                image_url=request.image_url
            )
            db.add(new_item)
            inserted_items.append(new_item)

        # Update merchant status to active if they have at least 1 item
        if inserted_items and merchant.status == "pending":
            merchant.status = "active"

        await db.commit()

        # Refresh all inserted items to get DB-generated IDs
        for item in inserted_items:
            await db.refresh(item)

        return inserted_items

catalog_service = CatalogService()
