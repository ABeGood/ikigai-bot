from sqlalchemy import Column, Integer, String, DateTime, Time, Date
from sqlalchemy.sql import func
from db.connection import Base
from datetime import datetime, time

class Reservation(Base):
    __tablename__ = "reservations"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    order_id = Column(String, unique=True, index=True)
    telegram_id = Column(String)
    name = Column(String)
    type = Column(String)
    place = Column(Integer)
    day = Column(Date, nullable=False)
    time_from = Column(Time, nullable=False)  # TIME type
    time_to = Column(Time, nullable=False)    # TIME type
    period = Column(Integer)
    payed = Column(String)