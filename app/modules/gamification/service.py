import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import (
    DuplicateStampException,
    InsufficientStampsException,
    MerchantOwnershipException,
    PromoExpiredException,
    PromoNotFoundException,
    RedemptionAlreadyUsedException,
    RedemptionCodeExpiredException,
    RedemptionNotFoundException,
)
from app.modules.auth.models import User
from app.modules.gamification.models import (
    Promo,
    PromoRedemption,
    RedemptionStatus,
    Stamp,
)
from app.modules.gamification.schemas import PromoCreate


class GamificationService:
    @staticmethod
    async def award_stamp(
        db: AsyncSession, user_id: UUID, merchant_id: UUID, transaction_id: UUID
    ):
        """
        Diberikan secara internal saat transaksi valid.
        Idempotent: Jika stamp untuk transaction_id ini sudah ada, akan menangkap IntegrityError.
        """
        stamp = Stamp(
            user_id=user_id,
            merchant_id=merchant_id,
            transaction_id=transaction_id,
        )
        db.add(stamp)
        try:
            await db.commit()
            return stamp
        except IntegrityError as err:
            await db.rollback()
            raise DuplicateStampException() from err

    @staticmethod
    async def get_user_stamps(db: AsyncSession, user_id: UUID):
        stmt = (
            select(Stamp)
            .options(selectinload(Stamp.merchant))
            .where(Stamp.user_id == user_id)
            .order_by(Stamp.awarded_at.desc())
        )
        result = await db.execute(stmt)
        stamps = result.scalars().all()
        return stamps

    @staticmethod
    async def get_total_stamps(db: AsyncSession, user_id: UUID) -> int:
        stmt = select(func.count()).select_from(Stamp).where(Stamp.user_id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one()

    @staticmethod
    async def create_promo(
        db: AsyncSession, merchant_id: UUID, promo_in: PromoCreate
    ):
        promo = Promo(
            merchant_id=merchant_id,
            title=promo_in.title,
            discount_type=promo_in.discount_type,
            discount_value=promo_in.discount_value,
            stamp_required_count=promo_in.stamp_required_count,
            valid_until=promo_in.valid_until,
            is_active=True,
        )
        db.add(promo)
        await db.commit()
        await db.refresh(promo)
        return promo

    @staticmethod
    async def list_available_promos(db: AsyncSession, user_id: UUID):
        # Hitung jumlah stamp user terlebih dahulu
        user_stamp_count = await GamificationService.get_total_stamps(db, user_id)

        # Cari semua promo yang aktif dan tidak expired
        now = datetime.now(timezone.utc)
        stmt = (
            select(Promo)
            .options(selectinload(Promo.merchant))
            .where(
                Promo.is_active.is_(True),
                Promo.valid_until > now,
                Promo.stamp_required_count <= user_stamp_count,
            )
        )
        result = await db.execute(stmt)
        promos = result.scalars().all()
        return promos, user_stamp_count

    @staticmethod
    async def redeem_promo(db: AsyncSession, user_id: UUID, promo_id: UUID):
        now = datetime.now(timezone.utc)

        # 1. Row-level lock pada user untuk menghindari race condition
        # (PostgreSQL tidak mengizinkan FOR UPDATE pada fungsi agregat)
        user_stmt = select(1).select_from(User).where(User.id == user_id).with_for_update()
        await db.execute(user_stmt)

        user_stamp_count = await GamificationService.get_total_stamps(db, user_id)

        # 2. Ambil data promo
        promo_stmt = select(Promo).where(Promo.id == promo_id)
        result = await db.execute(promo_stmt)
        promo = result.scalars().first()

        if not promo:
            raise PromoNotFoundException()
        if not promo.is_active or promo.valid_until <= now:
            raise PromoExpiredException()
        if user_stamp_count < promo.stamp_required_count:
            raise InsufficientStampsException()

        # 3. Buat kode redeem dan simpan
        redemption_code = secrets.token_hex(4).upper()
        # Menggunakan konstanta manual jika tidak import constants
        expires_at = now + timedelta(minutes=15)

        redemption = PromoRedemption(
            promo_id=promo_id,
            user_id=user_id,
            redemption_code=redemption_code,
            expires_at=expires_at,
            status=RedemptionStatus.PENDING,
        )

        # Simulasi pemotongan stamp bisa dilakukan dengan menandai stamp yang terpakai
        # Namun di desain saat ini hanya menggunakan count sebagai limit threshold,
        # asumsinya sistem menghitung total stamp yang telah dipakai dan mengurangi available,
        # Untuk kepatuhan thd dokumen: "Hitung total stamp aktif user... jika memenuhi, buat kode"
        # Karena kita butuh mengurangi saldo, kita bisa menyimpan relasi atau
        # mengurangi logic. Tapi desain "PromoRedemption" menyimpan `user_id`, jadi total stamp =
        # Total(Stamp) - Sum(PromoRedemption.stamp_required).
        # Agar count di langkah 1 tetap valid, kita query ulang:
        used_stamps_stmt = (
            select(func.coalesce(func.sum(Promo.stamp_required_count), 0))
            .select_from(PromoRedemption)
            .join(Promo, PromoRedemption.promo_id == Promo.id)
            .where(PromoRedemption.user_id == user_id)
        )
        used_result = await db.execute(used_stamps_stmt)
        used_stamps = used_result.scalar_one() or 0

        available_stamps = user_stamp_count - used_stamps
        if available_stamps < promo.stamp_required_count:
            raise InsufficientStampsException()

        db.add(redemption)
        await db.commit()
        await db.refresh(redemption)

        return redemption

    @staticmethod
    async def confirm_redemption(
        db: AsyncSession, merchant_id: UUID, redemption_code: str
    ):
        now = datetime.now(timezone.utc)

        stmt = (
            select(PromoRedemption)
            .options(selectinload(PromoRedemption.promo))
            .where(PromoRedemption.redemption_code == redemption_code)
        )
        result = await db.execute(stmt)
        redemption = result.scalars().first()

        if not redemption:
            raise RedemptionNotFoundException()

        # Validasi bahwa merchant adalah pemilik promo ini
        if redemption.promo.merchant_id != merchant_id:
            raise MerchantOwnershipException()

        if redemption.status == RedemptionStatus.REDEEMED:
            raise RedemptionAlreadyUsedException()

        if redemption.expires_at <= now or redemption.status == RedemptionStatus.EXPIRED:
            redemption.status = RedemptionStatus.EXPIRED
            await db.commit()
            raise RedemptionCodeExpiredException()

        redemption.status = RedemptionStatus.REDEEMED
        redemption.redeemed_at = now
        await db.commit()
        return redemption

gamification_service = GamificationService()
