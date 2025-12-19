from sqlalchemy import Column, Integer, String, DateTime, Text
from app.database import Base
from datetime import datetime

class Booking(Base):
    __tablename__ = "bookings"
    id = Column(Integer, primary_key=True, index=True)
    client_name = Column(String, nullable=False)
    service_type = Column(String, nullable=False)
    price = Column(Integer, default=0) # Добавили поле цены
    appointment_time = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.now)