import asyncio
import re

from sqlalchemy import func, select

from app.db.session import async_session_maker
from app.integrations.gemini_client import gemini_client
from app.modules.catalog.models import MerchantCatalogItem


async def test():
    query = "makanan"
    categories = [c.strip() for c in re.split(r',|\bdan\b|\batau\b|\b&\b', query.lower()) if c.strip()]
    print("CATEGORIES:", categories)

    query_embeddings = []
    for cat in categories:
        emb = await gemini_client.embed_text(cat)
        query_embeddings.append(emb)

    async with async_session_maker() as db:
        distances = []
        for emb in query_embeddings:
            distances.append(MerchantCatalogItem.embedding.cosine_distance(emb))

        least_distance = distances[0] if len(distances) == 1 else func.least(*distances)

        vector_stmt = (
            select(
                MerchantCatalogItem.merchant_id,
                MerchantCatalogItem.item_name,
                least_distance.label("least_dist")
            )
            .where(MerchantCatalogItem.embedding.is_not(None))
        )
        res = await db.execute(vector_stmt)
        for row in res.all():
            print(f"Item: {row.item_name}, Min Dist: {row.least_dist}, Similarity: {max(1.0 - row.least_dist, 0.0)}")

asyncio.run(test())
