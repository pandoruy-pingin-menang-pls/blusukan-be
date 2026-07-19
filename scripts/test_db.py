import asyncio

from sqlalchemy import text

from app.db.session import async_session_maker


async def test():
    async with async_session_maker() as db:
        res = await db.execute(text("SELECT * FROM merchant_catalog_items WHERE merchant_id = 'acc073e7-79a8-408e-b8e4-b67be600be42'"))
        for row in res.all():
            print(row)

asyncio.run(test())
