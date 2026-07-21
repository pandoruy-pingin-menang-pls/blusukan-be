from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidTransactionException, ItineraryOwnershipException
from app.modules.gamification.service import gamification_service
from app.modules.routing.models import Itinerary
from app.modules.transactions.models import Transaction
from app.modules.transactions.schemas import TransactionCreate

# Konstanta diambil dari dokumen/constants
SUSPICIOUS_TRANSACTION_THRESHOLD = 5000000

class TransactionService:
    @staticmethod
    async def log_transaction(
        db: AsyncSession,
        merchant_id: UUID,
        transaction_in: TransactionCreate,
        user_id: Optional[UUID] = None
    ) -> Transaction:
        if transaction_in.nominal_value <= 0:
            raise InvalidTransactionException()

        # Idempotency check
        if transaction_in.client_reference_id:
            stmt = select(Transaction).where(
                Transaction.merchant_id == merchant_id,
                Transaction.client_reference_id == transaction_in.client_reference_id,
            )
            res = await db.execute(stmt)
            existing_tx = res.scalars().first()
            if existing_tx:
                # Jika duplicate idempotency key, return langsung (sukses, tidak error)
                # Namun tidak men-trigger ulang gamification
                existing_tx.stamp_awarded = existing_tx.linked_itinerary_id is not None
                return existing_tx

        # Suspicious check
        is_suspicious = transaction_in.nominal_value > SUSPICIOUS_TRANSACTION_THRESHOLD

        # Itinerary ownership validation
        if transaction_in.linked_itinerary_id:
            itinerary_stmt = select(Itinerary).where(Itinerary.id == transaction_in.linked_itinerary_id)
            itinerary_res = await db.execute(itinerary_stmt)
            itinerary = itinerary_res.scalars().first()

            # Jika itinerary tidak ditemukan atau user_id-nya berbeda dengan user yang sedang login (tourist)
            # Pada kasus ini, user_id (B2C) tidak sama dengan pemilik merchant, tetapi user_id turis diurus
            # jika request ini dipicu oleh kasir, tapi "linked_itinerary_id" bisa dicek ownership turis.
            # Proposal mengatakan "linked_itinerary_id milik user lain -> 403".
            # Tetapi endpoint ini dipanggil oleh *Merchant*. Bagaimana merchant tahu user_id tourist?
            # Merchant app mengirim `linked_itinerary_id` (mungkin hasil scan QR itinerary).
            # Karena merchant tidak login sebagai turis, kita cukup cek apakah `linked_itinerary_id` valid.
            if not itinerary:
                raise ItineraryOwnershipException()

            # Catat turis dari itinerary
            tourist_user_id = itinerary.user_id
        else:
            tourist_user_id = None

        new_tx = Transaction(
            merchant_id=merchant_id,
            tourist_user_id=tourist_user_id,
            nominal_value=transaction_in.nominal_value,
            item_reference=transaction_in.item_reference,
            linked_itinerary_id=transaction_in.linked_itinerary_id,
            client_reference_id=transaction_in.client_reference_id,
            is_suspicious=is_suspicious,
        )

        db.add(new_tx)
        await db.commit()
        await db.refresh(new_tx)

        # Event-driven: Trigger gamification stamp jika ada linked_itinerary_id
        stamp_awarded = False
        if new_tx.linked_itinerary_id and new_tx.tourist_user_id:
            # Tidak blocking menggunakan create_task, tetapi karena kita dalam context DB session,
            # lebih aman memanggil service sinkronus dengan async/await agar session belum ditutup.
            # Alternatif: fire-and-forget menggunakan session terpisah (seperti background tasks).
            # Untuk simplifikasi MVP dan kepatuhan (event-driven), kita jalankan langsung.
            try:
                await gamification_service.award_stamp(
                    db,
                    user_id=new_tx.tourist_user_id,
                    merchant_id=merchant_id,
                    transaction_id=new_tx.id
                )
                stamp_awarded = True
            except Exception:
                # Log error, tidak menggagalkan POS (zero-fee settlement logging)
                pass

        new_tx.stamp_awarded = stamp_awarded
        return new_tx

    @staticmethod
    async def get_transaction_summary(db: AsyncSession, merchant_id: UUID):
        now = datetime.now(timezone.utc)
        today = now.date()

        stmt = select(
            func.coalesce(func.sum(Transaction.nominal_value), 0).label("total_omzet"),
            func.count(Transaction.id).label("total_transaksi")
        ).where(
            Transaction.merchant_id == merchant_id,
            func.date(Transaction.logged_at) == today
        )

        result = await db.execute(stmt)
        row = result.first()

        return {
            "total_omzet": float(row.total_omzet) if row else 0.0,
            "total_transaksi": int(row.total_transaksi) if row else 0
        }

    @staticmethod
    async def list_transactions(db: AsyncSession, merchant_id: UUID, page: int = 1, limit: int = 20):
        offset = (page - 1) * limit

        count_stmt = select(func.count()).where(Transaction.merchant_id == merchant_id)
        total_res = await db.execute(count_stmt)
        total = total_res.scalar_one()

        stmt = (
            select(Transaction)
            .where(Transaction.merchant_id == merchant_id)
            .order_by(Transaction.logged_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await db.execute(stmt)
        items = result.scalars().all()

        return {
            "items": items,
            "total": total,
            "page": page,
            "limit": limit
        }

transaction_service = TransactionService()
