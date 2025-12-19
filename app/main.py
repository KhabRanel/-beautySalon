from fastapi import FastAPI, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update
import asyncio
from sqlalchemy.exc import OperationalError
from app import models, schemas, database
from datetime import datetime

app = FastAPI(title="Booking Service")

templates = Jinja2Templates(directory="app/templates")


@app.on_event("startup")
async def startup():
    # Пытаемся подключиться к БД в цикле
    retries = 5
    while retries > 0:
        try:
            async with database.engine.begin() as conn:
                # Пробуем создать таблицы (это проверит соединение)
                await conn.run_sync(models.Base.metadata.create_all)
            print("--- Успешное подключение к БД! ---")
            break  # Если успешно, выходим из цикла
        except (OSError, OperationalError) as e:
            retries -= 1
            print(f"--- БД еще не готова, ждем 5 секунд... (Осталось попыток: {retries}) ---")
            print(f"Ошибка: {e}")
            await asyncio.sleep(5)  # Ждем 5 секунд перед повторной попыткой

    if retries == 0:
        print("--- Не удалось подключиться к БД после нескольких попыток ---")

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


@app.delete("/bookings/{booking_id}")
async def delete_booking(booking_id: int, db: AsyncSession = Depends(database.get_db)):
    result = await db.execute(select(models.Booking).where(models.Booking.id == booking_id))
    booking = result.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    await db.delete(booking)
    await db.commit()
    return {"ok": True}


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
    # Получаем заявки для отображения
    result = await db.execute(select(models.Booking).order_by(models.Booking.appointment_time))
    bookings = result.scalars().all()
    return templates.TemplateResponse("index.html", {"request": request, "bookings": bookings})


@app.post("/add", response_class=HTMLResponse)
async def add_booking_form(
        request: Request,
        client_name: str = Form(...),
        service_type: str = Form(...),
        appointment_time: str = Form(...),
        db: AsyncSession = Depends(database.get_db)
):
    # appointment_time приходит строкой из HTML формы, парсим её
    dt_obj = datetime.strptime(appointment_time, "%Y-%m-%d %H:%M")
    new_booking = models.Booking(
        client_name=client_name,
        service_type=service_type,
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
async def reschedule_booking_form(booking_id: int, new_time: str = Form(...),
                                  db: AsyncSession = Depends(database.get_db)):
    dt_obj = datetime.strptime(new_time, "%Y-%m-%d %H:%M")
    await reschedule_booking(booking_id, schemas.BookingUpdateDate(appointment_time=dt_obj), db)
    return RedirectResponse(url="/", status_code=303)