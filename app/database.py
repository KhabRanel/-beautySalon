from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import declarative_base
import os

# Получаем URL БД из переменных окружения (для Docker)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://user:password@localhost:5433/booking_db"
)

print(f"--- DEBUG: ACTUAL CONNECTION URL: {DATABASE_URL} ---")

engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

# Зависимость для получения сессии БД
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session