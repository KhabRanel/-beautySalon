import pytest
from httpx import AsyncClient
from app.main import app
from app.database import Base, engine, get_db
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Используем in-memory SQLite для тестов (или отдельную тестовую БД Postgres)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True, scope="module")
async def prepare_database():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_create_booking():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/bookings/", json={
            "client_name": "Тестовый Клиент",
            "service_type": "Маникюр",
            "appointment_time": "2023-12-31T12:00:00"
        })
    assert response.status_code == 200
    assert response.json()["client_name"] == "Тестовый Клиент"


@pytest.mark.asyncio
async def test_read_bookings():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/bookings/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) > 0


@pytest.mark.asyncio
async def test_delete_booking():
    # Сначала создадим
    async with AsyncClient(app=app, base_url="http://test") as ac:
        create = await ac.post("/bookings/", json={
            "client_name": "Delete Me",
            "service_type": "Test",
            "appointment_time": "2023-12-31T15:00:00"
        })
        booking_id = create.json()["id"]

        # Удаляем
        response = await ac.delete(f"/bookings/{booking_id}")
        assert response.status_code == 200

        # Проверяем что удалено
        check = await ac.get("/bookings/")
        ids = [b["id"] for b in check.json()]
        assert booking_id not in ids