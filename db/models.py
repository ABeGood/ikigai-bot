from sqlalchemy import Column, Integer, String, DateTime, Date
from sqlalchemy.sql import func
from db.connection import Base

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
    time_from = Column(DateTime(timezone=True))  # Changed from Time to DateTime with timezone
    time_to = Column(DateTime(timezone=True))    # Changed from Time to DateTime with timezone
    period = Column(Integer)
    payed = Column(String)