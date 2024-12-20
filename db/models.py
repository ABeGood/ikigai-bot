from sqlalchemy import Column, Integer, Float, Boolean, String, DateTime, Date
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base

class Reservation(declarative_base()):
    __tablename__ = "reservations"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    order_id = Column(String, unique=True, index=True)
    telegram_id = Column(String)
    name = Column(String)
    type = Column(String)
    place = Column(Integer)
    period = Column(Float)
    day = Column(Date)
    time_from = Column(DateTime(timezone=True))  # Changed from Time to DateTime with timezone
    time_to = Column(DateTime(timezone=True))    # Changed from Time to DateTime with timezone
    sum = Column(Float)
    payed = Column(Boolean)
    payment_confirmation_link = Column(String)
    payment_confirmation_file_id = Column(String)