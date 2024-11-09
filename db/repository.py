from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, Column, Integer, String, DateTime, Date
from . import models
from datetime import datetime, date, time, timedelta
from zoneinfo import ZoneInfo
import pandas as pd
from typing import List, Dict, Optional
from classes.classes import Reservation
import config
from util.utils import localize_from_db, prepare_for_db

class ReservationRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_reservation(self, reservation_data: Reservation):
        """Create a new reservation with proper timezone handling"""
        reservation_dict = reservation_data.to_dict()
        
        # Convert time objects to timezone-aware datetime objects
        reservation_dict['time_from'] = reservation_dict['time_from']
        reservation_dict['time_to'] = reservation_dict['time_to']
        
        db_reservation = models.Reservation(**reservation_dict)
        self.db.add(db_reservation)
        self.db.commit()
        self.db.refresh(db_reservation)
        return db_reservation


    def update_reservation(self, order_id: str, data: dict) -> bool:
        reservation = self.db.query(models.Reservation)\
                        .filter(models.Reservation.order_id == order_id)\
                        .first()
        if reservation:
            for key, value in data.items():
                setattr(reservation, key, value)
            self.db.commit()
            return True
        return False

    def get_reservations_by_telegram_id(self, telegram_id: str):
        return self.db.query(models.Reservation)\
                    .filter(models.Reservation.telegram_id == telegram_id)\
                    .all()

    def get_upcoming_reservations_by_telegram_id(self, telegram_id: str):
        current_datetime = datetime.now()
        current_datetime = prepare_for_db(current_datetime)
        current_date = current_datetime.date()  # This calls the date() method
        
        return self.db.query(models.Reservation)\
                     .filter(
                         and_(
                             models.Reservation.telegram_id == telegram_id,
                             or_(
                                 models.Reservation.day > current_date,
                                 and_(
                                     models.Reservation.day == current_date,
                                     models.Reservation.time_from > current_datetime
                                 )
                             )
                         )
                     )\
                     .order_by(models.Reservation.day, models.Reservation.time_from)\
                     .all()

    # Alternative version if time_from is stored as timestamp with timezone
    def get_upcoming_reservations_by_telegram_id_v2(self, telegram_id: str):
        current_datetime = datetime.now()
        current_datetime = prepare_for_db(current_datetime)
        
        return self.db.query(models.Reservation)\
                     .filter(
                         and_(
                             models.Reservation.telegram_id == telegram_id,
                             or_(
                                 models.Reservation.time_from > current_datetime
                             )
                         )
                     )\
                     .order_by(models.Reservation.time_from)\
                     .all()

    def delete_reservation(self, order_id: str) -> Optional[models.Reservation]:
        reservation = self.db.query(models.Reservation)\
                           .filter(models.Reservation.order_id == order_id)\
                           .first()
        if reservation:
            deleted_reservation = {
                'From': reservation.time_from,
                'OrderId': reservation.order_id,
                'CreationTime': reservation.created_at
            }

            self.db.delete(reservation)
            self.db.commit()
            deleted_reservation['From'] = localize_from_db(deleted_reservation['From'])
            return deleted_reservation
        return None

    def get_reservations_by_type_and_date_range(self, reservation_type: str, start_date: date, end_date: date):
        return self.db.query(models.Reservation)\
                     .filter(
                         and_(
                             models.Reservation.type == reservation_type,
                             models.Reservation.day >= start_date,
                             models.Reservation.day <= end_date
                         )
                     )\
                     .order_by(models.Reservation.day, models.Reservation.time_from)\
                     .all()

    def get_reservations_for_date(self, target_date: date):
        return self.db.query(models.Reservation)\
                     .filter(models.Reservation.day == target_date)\
                     .order_by(models.Reservation.time_from)\
                     .all()

    def get_available_places_for_timeslot(self, place_type: str, day: date, time_from: time, time_to: time) -> List[int]:
        """
        Find available places for a given timeslot
        """
        # Convert times to timezone-aware datetimes for comparison
        datetime_from = prepare_for_db(datetime.combine(day, time_from))
        datetime_to = prepare_for_db(datetime.combine(day, time_to))
        
        occupied_places = self.db.query(models.Reservation.place)\
                               .filter(
                                   and_(
                                       models.Reservation.day == day,
                                       models.Reservation.time_from < datetime_to,
                                       models.Reservation.time_to > datetime_from
                                   )
                               )\
                               .all()
        
        occupied_places = [place[0] for place in occupied_places]
        all_places = config.places[place_type]
        return [place for place in all_places if place not in occupied_places]

    def to_dataframe(self) -> pd.DataFrame:
        """Convert all reservations to a pandas DataFrame with localized times"""
        reservations = self.db.query(models.Reservation).all()
        
        if not reservations:
            return pd.DataFrame(columns=[
                'id', 'created_at', 'order_id', 'telegram_id', 'name',
                'type', 'place', 'day', 'time_from', 'time_to', 'period', 'payed'
            ])
            
        data = []
        for r in reservations:
            data.append({
                'id': r.id,
                'created_at': localize_from_db(r.created_at),
                'order_id': r.order_id,
                'telegram_id': r.telegram_id,
                'name': r.name,
                'type': r.type,
                'place': r.place,
                'day': r.day,  # Date doesn't need timezone conversion
                'time_from': localize_from_db(r.time_from),
                'time_to': localize_from_db(r.time_to),
                'period': r.period,
                'payed': r.payed
            })
            
        return pd.DataFrame(data)