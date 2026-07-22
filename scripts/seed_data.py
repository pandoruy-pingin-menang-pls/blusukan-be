"""
Blusukan Seed — Accounts Only
==============================
Hanya membuat akun user untuk keperluan testing phase-by-phase.
Data merchant, catalog, events, dll dibuat melalui API di tiap phase.

Akun yang di-seed:
  Admin    : admin@blusukan.com      / adminblusukan123
  Pedagang : warung@blusukan.com     / pedagang123   (mulai sebagai wisatawan)
             batik@blusukan.com      / pedagang123   (mulai sebagai wisatawan)
             jamu@blusukan.com       / pedagang123   (mulai sebagai wisatawan)
  Wisatawan: turis@blusukan.com      / wisatawan123
             turis2@blusukan.com     / wisatawan123

Catatan: akun warung/batik/jamu mulai dengan role WISATAWAN.
Role akan di-upgrade ke PEDAGANG saat Phase 2 (POST /merchants/register).

Jalankan dari root project:
  venv\\Scripts\\python.exe -m scripts.seed_data
"""

import asyncio
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.db.session import async_session_maker, engine
from app.modules.auth.models import User, UserRole


def _p(msg: str) -> None:
    print(msg)


SEED_ACCOUNTS = [
    # (email, password, full_name, role)
    ("admin@blusukan.com",  "adminblusukan123", "Admin Blusukan", UserRole.ADMIN),
    ("warung@blusukan.com", "pedagang123",      "Pak Darmo",      UserRole.WISATAWAN),
    ("batik@blusukan.com",  "pedagang123",      "Bu Amanah",      UserRole.WISATAWAN),
    ("jamu@blusukan.com",   "pedagang123",      "Mbah Gendhis",   UserRole.WISATAWAN),
    ("turis@blusukan.com",  "wisatawan123",     "Dimas Pramudya", UserRole.WISATAWAN),
    ("turis2@blusukan.com", "wisatawan123",     "Rara Sekar",     UserRole.WISATAWAN),
]


async def seed(db: AsyncSession) -> None:
    _p("\n[SEED] Membuat akun testing Blusukan...\n")

    created = 0
    skipped = 0

    for email, password, full_name, role in SEED_ACCOUNTS:
        existing = await db.execute(
            text("SELECT id FROM users WHERE email = :e"), {"e": email}
        )
        if existing.fetchone():
            _p(f"   SKIP : {email} (sudah ada)")
            skipped += 1
        else:
            db.add(User(
                id=uuid.uuid4(),
                email=email,
                hashed_password=get_password_hash(password),
                full_name=full_name,
                role=role,
                has_merchant_profile=False,
            ))
            _p(f"   OK   : {email} ({role.value})")
            created += 1

    await db.flush()
    await db.commit()

    _p("\n" + "=" * 60)
    _p("[DONE] Akun berhasil dibuat!")
    _p("")
    _p(f"  {created} akun baru | {skipped} sudah ada")
    _p("")
    _p("Akun yang tersedia:")
    _p("  admin@blusukan.com      / adminblusukan123  [admin]")
    _p("  warung@blusukan.com     / pedagang123       [wisatawan -> naik ke pedagang di Phase 2]")
    _p("  batik@blusukan.com      / pedagang123       [wisatawan -> naik ke pedagang di Phase 2]")
    _p("  jamu@blusukan.com       / pedagang123       [wisatawan -> naik ke pedagang di Phase 2]")
    _p("  turis@blusukan.com      / wisatawan123      [wisatawan]")
    _p("  turis2@blusukan.com     / wisatawan123      [wisatawan]")
    _p("")
    _p("Lanjutkan dengan testing per Phase di README.")
    _p("=" * 60)


async def main():
    async with async_session_maker() as db:
        try:
            await seed(db)
        except Exception as e:
            await db.rollback()
            _p(f"[ERROR] Seed gagal: {e}")
            import traceback
            traceback.print_exc()
            raise
        finally:
            await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
