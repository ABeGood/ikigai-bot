from sqlalchemy import Column, Integer, String, DateTime, Time, Date
from sqlalchemy.sql import func
from .connection import Base

class Reservation(Base):
    __tablename__ = "reservations"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    order_id = Column(String, unique=True, index=True)
    telegram_id = Column(String)
    name = Column(String)
    type = Column(String)
    place = Column(Integer)
    day = Column(Date)
    time_from = Column(Time)
    time_to = Column(Time)
    period = Column(Integer)
    payed = Column(String)