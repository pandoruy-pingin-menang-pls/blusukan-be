from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass

# Import semua model di sini agar Alembic bisa menemukannya
