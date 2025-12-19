from sqlalchemy import Column, Integer, String, DateTime, Text
from app.database import Base
from datetime import datetime

class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    client_name = Column(String, nullable=False)
    service_type = Column(String, nullable=False) # Например: "Маникюр"
    description = Column(Text, nullable=True)
    # Используем DateTime для хранения даты и времени
    appointment_time = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.now)