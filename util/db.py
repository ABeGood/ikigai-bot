from database.connection import get_db
from database.repository import ReservationRepository
from datetime import datetime

class ReservationTable:
    def __init__(self):
        self.db = next(get_db())
        self.repository = ReservationRepository(self.db)

    def save_reservation_to_table(self, new_reservation):
        reservation_data = {
            'order_id': new_reservation.orderid,
            'telegram_id': new_reservation.telegramId,
            'name': new_reservation.name,
            'type': new_reservation.type,
            'place': new_reservation.place,
            'day': new_reservation.day,
            'time_from': new_reservation.time_from.time(),
            'time_to': new_reservation.time_to.time(),
            'period': new_reservation.period,
            'payed': new_reservation.payed
        }
        
        try:
            self.repository.create_reservation(reservation_data)
            return True
        except Exception as e:
            print(e)
            return False

    def delete_reservation(self, order_id: str):
        return self.repository.delete_reservation(order_id)