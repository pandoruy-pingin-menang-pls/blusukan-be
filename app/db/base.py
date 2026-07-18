from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass

# Import semua model di sini agar Alembic bisa menemukannya
from app.modules.auth.models import User, RefreshToken
from app.modules.merchant.models import Merchant
from app.modules.catalog.models import MerchantCatalogItem

