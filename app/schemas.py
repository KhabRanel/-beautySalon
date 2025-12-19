from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class BookingBase(BaseModel):
    client_name: str = Field(..., min_length=2, title="Имя клиента")
    service_type: str = Field(..., title="Тип услуги")
    description: Optional[str] = None
    appointment_time: datetime

class BookingCreate(BookingBase):
    pass

class BookingUpdateDate(BaseModel):
    appointment_time: datetime

class BookingResponse(BookingBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True