from sqlalchemy.orm import Session
from . import models
from datetime import datetime, date, time

class ReservationRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_reservation(self, reservation_data: dict):
        db_reservation = models.Reservation(**reservation_data)
        self.db.add(db_reservation)
        self.db.commit()
        self.db.refresh(db_reservation)
        return db_reservation

    def get_reservations_by_telegram_id(self, telegram_id: str):
        return self.db.query(models.Reservation)\
                     .filter(models.Reservation.telegram_id == telegram_id)\
                     .all()

    def delete_reservation(self, order_id: str):
        reservation = self.db.query(models.Reservation)\
                           .filter(models.Reservation.order_id == order_id)\
                           .first()
        if reservation:
            self.db.delete(reservation)
            self.db.commit()
            return reservation
        return None