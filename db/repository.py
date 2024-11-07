from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, Column, Integer, String, DateTime, Date
from . import models
from datetime import datetime, date, time, timedelta
from zoneinfo import ZoneInfo
import pandas as pd
from typing import List, Dict, Optional
from classes.classes import Reservation
import config

class ReservationRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_reservation(self, reservation_data: Reservation):
        # First convert any datetime objects to time
        if isinstance(reservation_data.time_from, datetime):
            time_from = reservation_data.time_from.time()
        else:
            time_from = reservation_data.time_from
            
        if isinstance(reservation_data.time_to, datetime):
            time_to = reservation_data.time_to.time()
        else:
            time_to = reservation_data.time_to

        # Now combine the day with times to create timezone-aware datetimes
        timezone = ZoneInfo("Europe/Prague")  # Or your desired timezone
        
        datetime_from = datetime.combine(
            reservation_data.day,
            time_from
        ).replace(tzinfo=timezone)
        
        datetime_to = datetime.combine(
            reservation_data.day,
            time_to
        ).replace(tzinfo=timezone)

        db_reservation = models.Reservation(
            order_id=reservation_data.order_id,
            telegram_id=reservation_data.telegram_id,
            name=reservation_data.name,
            type=reservation_data.type,
            place=reservation_data.place,
            day=reservation_data.day,
            time_from=datetime_from,  # Now using timezone-aware datetime
            time_to=datetime_to,      # Now using timezone-aware datetime
            period=reservation_data.period,
            payed=reservation_data.payed
        )
        
        self.db.add(db_reservation)
        self.db.commit()
        self.db.refresh(db_reservation)
        return db_reservation

    def get_reservations_by_telegram_id(self, telegram_id: str):
        return self.db.query(models.Reservation)\
                     .filter(models.Reservation.telegram_id == telegram_id)\
                     .all()

    def get_upcoming_reservations_by_telegram_id(self, telegram_id: str):
        current_time = datetime.now()
        current_date = current_time.date()  # This calls the date() method
        current_time_only = current_time.time()  # This gets just the time

        # Create timezone-aware datetime for comparison
        timezone = ZoneInfo("Europe/Prague")  # Or your desired timezone
        current_datetime = datetime.now().replace(tzinfo=timezone)
        
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
        # Create timezone-aware datetime for comparison
        timezone = ZoneInfo("Europe/Prague")  # Or your desired timezone
        current_datetime = datetime.now().replace(tzinfo=timezone)
        
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
        timezone = ZoneInfo("Europe/Prague")
        datetime_from = datetime.combine(day, time_from).replace(tzinfo=timezone)
        datetime_to = datetime.combine(day, time_to).replace(tzinfo=timezone)
        
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
        """Convert all reservations to a pandas DataFrame"""
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
                'created_at': r.created_at,
                'order_id': r.order_id,
                'telegram_id': r.telegram_id,
                'name': r.name,
                'type': r.type,
                'place': r.place,
                'day': r.day,
                'time_from': r.time_from,
                'time_to': r.time_to,
                'period': r.period,
                'payed': r.payed
            })
            
        df = pd.DataFrame(data)
        return df