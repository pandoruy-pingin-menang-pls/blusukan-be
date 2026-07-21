import asyncio

from sqlalchemy import text

from app.db.session import engine


async def main():
    async with engine.begin() as conn:
        await conn.execute(text("INSERT INTO storage.buckets (id, name, public) VALUES ('merchant-menus', 'merchant-menus', true) ON CONFLICT DO NOTHING;"))
        print("Bucket created!")

asyncio.run(main())
