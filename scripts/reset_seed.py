"""
Blusukan Reset Seed Script
==========================
Menghapus semua data yang diinsert oleh seed_data.py.
Data dihapus berdasarkan email akun seed.

Jalankan dari root project:
  venv\\Scripts\\python.exe -m scripts.reset_seed
"""

import asyncio

from sqlalchemy import text

from app.db.session import async_session_maker, engine

SEED_EMAILS = [
    "admin@blusukan.com",
    "warung@blusukan.com",
    "batik@blusukan.com",
    "jamu@blusukan.com",
    "turis@blusukan.com",
    "turis2@blusukan.com",
]


async def reset():
    async with async_session_maker() as db:
        print("\n[RESET] Menghapus seed data Blusukan...\n")

        # Ambil user_id dari akun seed
        placeholders = ", ".join(f"'{e}'" for e in SEED_EMAILS)
        result = await db.execute(
            text(f"SELECT id, email FROM users WHERE email IN ({placeholders})")
        )
        rows = result.fetchall()
        user_ids  = [str(row[0]) for row in rows]
        found_emails = [row[1] for row in rows]

        if not user_ids:
            print("[SKIP] Tidak ada akun seed yang ditemukan. Database sudah bersih.")
            return

        print(f"   Ditemukan {len(user_ids)} akun seed: {found_emails}")
        print("   Memulai penghapusan...\n")

        # Ambil merchant_id milik user seed
        uid_literal = ", ".join(f"'{u}'" for u in user_ids)
        result = await db.execute(
            text(f"SELECT id FROM merchants WHERE owner_id IN ({uid_literal})")
        )
        merchant_ids = [str(row[0]) for row in result.fetchall()]

        def _fmt(ids):
            return ", ".join(f"'{i}'" for i in ids)

        steps = []

        if merchant_ids:
            mid = _fmt(merchant_ids)
            steps += [
                ("promo_redemptions (via promos)",
                 f"DELETE FROM promo_redemptions WHERE promo_id IN (SELECT id FROM promos WHERE merchant_id IN ({mid}))"),
                ("promos",
                 f"DELETE FROM promos WHERE merchant_id IN ({mid})"),
                ("stamps (via merchant)",
                 f"DELETE FROM stamps WHERE merchant_id IN ({mid})"),
                ("transactions",
                 f"DELETE FROM transactions WHERE merchant_id IN ({mid})"),
                ("merchant_catalog_items",
                 f"DELETE FROM merchant_catalog_items WHERE merchant_id IN ({mid})"),
                ("inventory_recommendations",
                 f"DELETE FROM inventory_recommendations WHERE merchant_id IN ({mid})"),
                ("credit_score_logs",
                 f"DELETE FROM credit_score_logs WHERE merchant_id IN ({mid})"),
                ("merchants",
                 f"DELETE FROM merchants WHERE id IN ({mid})"),
            ]

        if user_ids:
            uid = _fmt(user_ids)
            steps += [
                ("itineraries",
                 f"DELETE FROM itineraries WHERE user_id IN ({uid})"),
                ("refresh_tokens",
                 f"DELETE FROM refresh_tokens WHERE user_id IN ({uid})"),
                ("promo_redemptions (via user)",
                 f"DELETE FROM promo_redemptions WHERE user_id IN ({uid})"),
                ("stamps (via user)",
                 f"DELETE FROM stamps WHERE user_id IN ({uid})"),
                ("events (by seed admin)",
                 f"DELETE FROM events WHERE reviewed_by_admin_id IN ({uid})"),
                ("users",
                 f"DELETE FROM users WHERE id IN ({uid})"),
            ]

        for label, query in steps:
            result = await db.execute(text(query))
            print(f"   OK  {label}: {result.rowcount} baris dihapus")

        await db.commit()
        print("\n[DONE] Reset selesai. Jalankan seed_data.py untuk re-seed.\n")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(reset())
