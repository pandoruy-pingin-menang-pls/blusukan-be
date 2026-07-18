import asyncio

from sqlalchemy import text

from app.db.session import engine


async def test_connection():
    try:
        # Mencoba membuka koneksi dan menjalankan query sederhana (SELECT 1)
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            print("[BERHASIL] Aplikasi sudah terhubung ke database Supabase.")
            print(f"Hasil Test Query (SELECT 1) = {result.scalar()}")
    except Exception as e:
        import sys
        print("[GAGAL KONEK] Berikut pesan errornya:")
        print(e)
        sys.exit(1)
    finally:
        # Menutup engine secara aman
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test_connection())
