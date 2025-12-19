from fastapi import FastAPI, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update, func
import asyncio
from sqlalchemy.exc import OperationalError
from app import models, schemas, database
from datetime import datetime
from contextlib import asynccontextmanager


templates = Jinja2Templates(directory="app/templates")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Логика при старте
    async with database.engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
    yield
    # Логика при выключении (если нужна)


app = FastAPI(title="Beauty Salon", lifespan=lifespan)


# --- API Endpoints ---

@app.post("/bookings/", response_model=schemas.BookingResponse)
async def create_booking(booking: schemas.BookingCreate, db: AsyncSession = Depends(database.get_db)):
    db_booking = models.Booking(**booking.dict())
    db.add(db_booking)
    await db.commit()
    await db.refresh(db_booking)
    return db_booking


@app.get("/bookings/", response_model=list[schemas.BookingResponse])
async def read_bookings(db: AsyncSession = Depends(database.get_db)):
    result = await db.execute(select(models.Booking).order_by(models.Booking.appointment_time))
    return result.scalars().all()


@app.post("/delete/{booking_id}")  # Должен быть POST, так как форма в HTML отправляет POST
async def delete_booking(
        booking_id: int,
        db: AsyncSession = Depends(database.get_db)
):
    # Находим запись
    result = await db.execute(select(models.Booking).where(models.Booking.id == booking_id))
    booking = result.scalar_one_or_none()

    if booking:
        await db.delete(booking)
        await db.commit()

    # Вместо возврата сообщения или объекта, делаем редирект на главную
    return RedirectResponse(url="/", status_code=303)


@app.put("/bookings/{booking_id}/reschedule")
async def reschedule_booking(booking_id: int, new_data: schemas.BookingUpdateDate,
                             db: AsyncSession = Depends(database.get_db)):
    stmt = update(models.Booking).where(models.Booking.id == booking_id).values(
        appointment_time=new_data.appointment_time)
    result = await db.execute(stmt)
    await db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Booking not found")
    return {"status": "updated"}


# --- Frontend Endpoints (Работа с формами) ---

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, db: AsyncSession = Depends(database.get_db)):
    now = datetime.now()

    service_durations = {
        "Маникюр": 90,
        "Педикюр": 120,
        "Стрижка": 60,
        "Окрашивание": 180,
        "Массаж": 60,
        "Брови": 30
    }

    # Получаем все записи
    result = await db.execute(select(models.Booking).order_by(models.Booking.appointment_time))
    bookings = result.scalars().all()

    for b in bookings:
        b.duration = service_durations.get(b.service_type, 60)

    # 1. Статистика за всё время (прошедшие записи)
    past_bookings = [b for b in bookings if b.appointment_time < now]
    total_past_revenue = sum(b.price for b in past_bookings)
    total_clients = len(past_bookings)

    # 2. Популярная услуга
    services = [b.service_type for b in past_bookings]
    popular_service = max(set(services), key=services.count) if services else "—"

    # 3. Статистика на сегодня (оставляем как было)
    today_bookings = [b for b in bookings if b.appointment_time.date() == now.date()]
    today_revenue = sum(b.price for b in today_bookings)

    return templates.TemplateResponse("index.html", {
        "request": request,
        "bookings": bookings,
        "now": now,
        "range": range,
        "today_count": len(today_bookings),
        "total_revenue": today_revenue,
        "history": {
            "revenue": total_past_revenue,
            "clients": total_clients,
            "popular": popular_service
        }
    })


@app.post("/add")
async def add_booking_form(
    request: Request,
    client_name: str = Form(...),
    service_type: str = Form(...),
    price: int = Form(0),
    appointment_time: str = Form(None), # Меняем на None, чтобы обработать вручную
    db: AsyncSession = Depends(database.get_db)
):
    # Если дата пустая или пришла ошибка - просто редиректим назад
    if not appointment_time or appointment_time.strip() == "":
        return RedirectResponse(url="/", status_code=303)

    try:
        # Пробуем распарсить дату
        dt_obj = datetime.strptime(appointment_time, "%Y-%m-%d %H:%M")
    except ValueError:
        # Если формат неверный - тоже редиректим
        return RedirectResponse(url="/", status_code=303)
    new_booking = models.Booking(
        client_name=client_name,
        service_type=service_type,
        price=price,
        appointment_time=dt_obj
    )
    db.add(new_booking)
    await db.commit()
    return RedirectResponse(url="/", status_code=303)


@app.get("/delete/{booking_id}")
async def delete_booking_form(booking_id: int, db: AsyncSession = Depends(database.get_db)):
    await delete_booking(booking_id, db)
    return RedirectResponse(url="/", status_code=303)


@app.post("/reschedule/{booking_id}")
async def reschedule_booking_form(
        booking_id: int,
        new_time: str = Form(None),  # Ставим None, чтобы не падать сразу
        db: AsyncSession = Depends(database.get_db)
):
    # 1. Проверка на пустое поле
    if not new_time or new_time.strip() == "":
        return RedirectResponse(url="/", status_code=303)

    try:
        # 2. Проверка формата (убираем T, если используем Flatpickr с пробелом)
        dt_obj = datetime.strptime(new_time, "%Y-%m-%d %H:%M")
    except ValueError:
        # Если дата некорректная, просто возвращаем на главную
        return RedirectResponse(url="/", status_code=303)

    # 3. Дальше идет ваша логика обновления в БД
    result = await db.execute(select(models.Booking).where(models.Booking.id == booking_id))
    booking = result.scalar_one_or_none()

    if booking:
        booking.appointment_time = dt_obj
        await db.commit()

    return RedirectResponse(url="/", status_code=303)