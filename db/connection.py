import os
from contextlib import contextmanager
from typing import Generator
from urllib.parse import urlparse, parse_qs
import pandas as pd

from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError, DBAPIError
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
import datetime
from datetime import date, time
import pytz
from tg_bot import config

from classes.classes import Reservation
from db import models

class DatabaseConfig:
    def __init__(self):
        load_dotenv()
        
        # Get database URL with fallback
        self.database_url = self._get_database_url()
        
        # Configure connection pool
        self.pool_size = int(os.getenv("DB_POOL_SIZE", "5"))
        self.max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "10"))
        self.pool_timeout = int(os.getenv("DB_POOL_TIMEOUT", "30"))
        self.pool_recycle = int(os.getenv("DB_POOL_RECYCLE", "1800"))  # 30 minutes
        
    def _get_database_url(self) -> str:
        """Get and format database URL with fallbacks"""
        # Try getting URL directly
        url = os.getenv("DATABASE_URL")
        
        # Fall back to constructing from components if needed
        if not url:
            url = self._construct_db_url()
            
        # Handle Railway's internal/external URL conversion
        if url and "postgres.railway.internal" in url:
            url = os.getenv("EXTERNAL_DATABASE_URL", url)
            
        # Fix protocol for SQLAlchemy
        if url and url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
            
        if not url:
            raise ValueError("No database URL configured")
            
        return url
    
    def _construct_db_url(self) -> str:
        """Construct database URL from individual components"""
        host = os.getenv("PGHOST")
        port = os.getenv("PGPORT")
        database = os.getenv("PGDATABASE")
        user = os.getenv("PGUSER")
        password = os.getenv("PGPASSWORD")
        
        if all([host, port, database, user, password]):
            return f"postgresql://{user}:{password}@{host}:{port}/{database}"
        return None

class Database:
    def __init__(self):
        self.config = DatabaseConfig()
        self.engine = self._create_engine()
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
        self.Base = declarative_base()
        
        # Set up engine event listeners
        self._setup_engine_events()
        
    def _create_engine(self) -> Engine:
        """Create SQLAlchemy engine with proper configuration"""
        return create_engine(
            self.config.database_url,
            pool_size=self.config.pool_size,
            max_overflow=self.config.max_overflow,
            pool_timeout=self.config.pool_timeout,
            pool_recycle=self.config.pool_recycle,
            pool_pre_ping=True  # Enable connection health checks
        )
    
    def _setup_engine_events(self):
        @event.listens_for(self.engine, "connect")
        def connect(dbapi_connection, connection_record):
            print("Database connection established")

        # @event.listens_for(self.engine, "disconnect")
        # def disconnect(dbapi_connection, connection_record):
        #     print("Database connection closed")

    @contextmanager
    def get_db(self) -> Generator[Session, None, None]:
        """Provide a transactional scope around a series of operations"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except SQLAlchemyError as e:
            session.rollback()
            raise DatabaseError(f"Database error occurred: {str(e)}")
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()


    def create_reservation(self, reservation_data: Reservation):
        """Create a new reservation with proper timezone handling"""
        reservation_dict = reservation_data.to_dict()
        
        # Convert time objects to timezone-aware datetime objects
        reservation_dict['time_from'] = reservation_dict['time_from']
        reservation_dict['time_to'] = reservation_dict['time_to']
        
        db_reservation = models.Reservation(**reservation_dict)

        with self.get_db() as db:
            db.add(db_reservation)
            try:
                db.commit()
                db.refresh(db_reservation)
                return db_reservation
            except:
                db.rollback()
                return None


    def update_reservation(self, order_id: str, data: dict) -> bool:
        with self.get_db() as db:
            reservation = db.query(models.Reservation)\
                            .filter(models.Reservation.order_id == order_id)\
                            .first()
            if reservation:
                for key, value in data.items():
                    setattr(reservation, key, value)
                try:
                    db.commit()
                    return True
                except:
                    db.rollback()
            return False


    def get_reservations_by_telegram_id(self, telegram_id: str):
        with self.get_db() as db:
            return db.query(models.Reservation)\
                        .filter(models.Reservation.telegram_id == telegram_id)\
                        .all()


    # def get_upcoming_reservations_by_telegram_id(self, telegram_id: str):
    #     current_datetime = datetime.now()
    #     current_datetime = prepare_for_db(current_datetime)
    #     current_date = current_datetime.date()  # This calls the date() method
        
    #     return self.db.query(models.Reservation)\
    #                  .filter(
    #                      and_(
    #                          models.Reservation.telegram_id == telegram_id,
    #                          or_(
    #                              models.Reservation.day > current_date,
    #                              and_(
    #                                  models.Reservation.day == current_date,
    #                                  models.Reservation.time_from > current_datetime
    #                              )
    #                          )
    #                      )
    #                  )\
    #                  .order_by(models.Reservation.day, models.Reservation.time_from)\
    #                  .all()


    # # Alternative version if time_from is stored as timestamp with timezone
    # def get_upcoming_reservations_by_telegram_id_v2(self, telegram_id: str):
    #     current_datetime = datetime.now()
    #     current_datetime = prepare_for_db(current_datetime)
        
    #     return self.db.query(models.Reservation)\
    #                  .filter(
    #                      and_(
    #                          models.Reservation.telegram_id == telegram_id,
    #                          or_(
    #                              models.Reservation.time_from > current_datetime
    #                          )
    #                      )
    #                  )\
    #                  .order_by(models.Reservation.time_from)\
    #                  .all()


    # def delete_reservation(self, order_id: str) -> Optional[models.Reservation]:
    #     reservation = self.db.query(models.Reservation)\
    #                        .filter(models.Reservation.order_id == order_id)\
    #                        .first()
    #     if reservation:
    #         deleted_reservation = {
    #             'From': reservation.time_from,
    #             'OrderId': reservation.order_id,
    #             'CreationTime': reservation.created_at
    #         }

    #         self.db.delete(reservation)
    #         try:
    #             self.db.commit()
    #             deleted_reservation['From'] = localize_from_db(deleted_reservation['From'])
    #             return deleted_reservation
    #         except:
    #             self.db.rollback()
    #     return None


    # def get_reservations_by_type_and_date_range(self, reservation_type: str, start_date: date, end_date: date):
    #     return self.db.query(models.Reservation)\
    #                  .filter(
    #                      and_(
    #                          models.Reservation.type == reservation_type,
    #                          models.Reservation.day >= start_date,
    #                          models.Reservation.day <= end_date
    #                      )
    #                  )\
    #                  .order_by(models.Reservation.day, models.Reservation.time_from)\
    #                  .all()


    # def get_reservations_for_date(self, target_date: date):
    #     return self.db.query(models.Reservation)\
    #                  .filter(models.Reservation.day == target_date)\
    #                  .order_by(models.Reservation.time_from)\
    #                  .all()


    # def get_available_places_for_timeslot(self, place_type: str, day: date, time_from: time, time_to: time) -> List[int]:
    #     """
    #     Find available places for a given timeslot
    #     """
    #     # Convert times to timezone-aware datetimes for comparison
    #     datetime_from = prepare_for_db(datetime.combine(day, time_from))
    #     datetime_to = prepare_for_db(datetime.combine(day, time_to))
        
    #     occupied_places = self.db.query(models.Reservation.place)\
    #                            .filter(
    #                                and_(
    #                                    models.Reservation.day == day,
    #                                    models.Reservation.time_from < datetime_to,
    #                                    models.Reservation.time_to > datetime_from
    #                                )
    #                            )\
    #                            .all()
        
    #     occupied_places = [place[0] for place in occupied_places]
    #     all_places = config.places[place_type]
    #     return [place for place in all_places if place not in occupied_places]


    def to_dataframe(self) -> pd.DataFrame:
        """Convert all reservations to a pandas DataFrame with localized times"""
        with self.get_db() as db:
            reservations = db.query(models.Reservation).all()
        
            if not reservations:
                return pd.DataFrame(columns=[
                    'id', 'created_at', 'order_id', 'telegram_id', 'name',
                    'type', 'place', 'day', 'time_from', 'time_to', 'period', 'payed'
                ])
                
            data = []
            for r in reservations:
                data.append({
                    'id': r.id,
                    'created_at': self.localize_from_db(r.created_at),
                    'order_id': r.order_id,
                    'telegram_id': r.telegram_id,
                    'name': r.name,
                    'type': r.type,
                    'place': r.place,
                    'day': r.day,  # Date doesn't need timezone conversion
                    'time_from': self.localize_from_db(r.time_from),
                    'time_to': self.localize_from_db(r.time_to),
                    'period': r.period,
                    'payed': r.payed
                })
            
            return pd.DataFrame(data)
    

    # def find_closest_slot_start(mins_buffer):
    #     current_datetime = datetime.now()
    #     if 0 <= current_datetime.minute <= 30-mins_buffer:  # xx:00 - xx:20
    #         next_available_timeslot_start = (current_datetime.replace(minute=30, second=0, microsecond=000000))  # give xx:30
    #     elif 30-mins_buffer <= current_datetime.minute <= 60-mins_buffer:  # xx:20 - xx:50
    #         next_available_timeslot_start = (current_datetime.replace(hour=current_datetime.hour+1, minute=0, second=0, microsecond=000000))  # give xx+1:00
    #     elif 60-mins_buffer <= current_datetime.minute < 60:  # xx:50 - xx:59
    #         next_available_timeslot_start = (current_datetime.replace(hour=current_datetime.hour+1, minute=30, second=0, microsecond=000000))  # give xx+1:30
    #     return next_available_timeslot_start


    # def generate_days_intervals(to_date: datetime, timeslot_size_h: int) -> list[datetime]:
    #     days: list[datetime] = []

    #     current_datetime = datetime.now()   
    #     end_of_current_day = current_datetime.replace(hour=config.workday_end.hour-1, minute=59, second=59, microsecond=999)

    #     if current_datetime.time() < config.workday_start:
    #         days.append(current_datetime.replace(hour=config.workday_start.hour,
    #                                             minute=config.workday_start.minute,
    #                                             second=config.workday_start.second))

    #     elif current_datetime + timedelta(hours=timeslot_size_h, minutes=config.time_buffer_mins) <= end_of_current_day:
    #         next_available_timeslot_start = find_closest_slot_start(mins_buffer=config.time_buffer_mins)
    #         days.append(pd.to_datetime(next_available_timeslot_start))
        

    #     start_of_the_next_day = current_datetime.replace(hour=config.workday_start.hour, 
    #                                                     minute=config.workday_start.minute, 
    #                                                     second=config.workday_start.second, 
    #                                                     microsecond=config.workday_start.microsecond
    #                                                     ) + timedelta(days=1)
        
    #     date_range_with_time = pd.date_range(start_of_the_next_day, end=to_date, freq='D')

    #     for day in date_range_with_time:
    #         # Generate time intervals from 06:00 to 23:59 for the full days
    #         days.append(day)
            
    #     return days


    # def find_available_days(new_reservation: Reservation, reservation_table: pd.DataFrame, to_date = None) -> list[datetime]:  # AG: Now returns only days with no reservations
    #     current_datetime = datetime.now()

    #     # Some kind of lookforward; TODO: refactor
    #     if not to_date:
    #         to_date = (current_datetime.replace(day=1) + timedelta(days=config.days_lookforward)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    #     days_to_check = generate_days_intervals(to_date, timeslot_size_h=new_reservation.period)

    #     # Initialize list to store time gaps
    #     available_days: list[datetime] = []

    #     # Iterate through each day within the specified range
    #     for day_start in days_to_check:
    #         gaps = find_reservation_gaps(reservation_table, selected_date=day_start, reservation_type=new_reservation.type, min_gap_hours=new_reservation.period)

    #         if len(gaps) > 0:
    #             available_days.append(day_start)

    #     return available_days


    # def find_timeslots(new_reservation: Reservation, reservation_table: pd.DataFrame, on_date : datetime) -> dict[str, list[int]]:  # AG: Now returns only days with no reservations
    #     timeslots: dict[str, list[int]] = {}
    #     day_start : datetime
    #     day_end = on_date.replace(hour=config.workday_end.hour, 
    #                               minute=config.workday_end.minute, 
    #                               second=config.workday_end.second, 
    #                               microsecond=config.workday_end.microsecond)
        
    #     # day_str = day_start.strftime('%Y-%m-%d')
    #     current_datetime = datetime.now()  

    #     if on_date.date() == current_datetime.now().date():
    #         day_start = find_closest_slot_start(mins_buffer=config.time_buffer_mins)
    #     else:
    #         day_start = on_date.replace(hour=config.workday_start.hour, 
    #                                     minute=config.workday_start.minute, 
    #                                     second=config.workday_start.second, 
    #                                     microsecond=config.workday_start.microsecond
    #                                     )

    #     # Filter reservations for the current day
    #     reservations_on_day = reservation_table[reservation_table['Day'] == day_start.strftime('%Y-%m-%d')]
    #     reservations_on_day = reservations_on_day[reservations_on_day['Place'].isin(config.places[new_reservation.type])]
    #     reservations_on_day.sort_values(by='From', inplace=True)
    #     print(f'Reservations on {day_start.strftime("%Y-%m-%d")}: {len(reservations_on_day)}')

    #     gap_start_time = day_start
    #     gap_end_time = gap_start_time + timedelta(hours=new_reservation.period)

    #     if len(reservations_on_day) == 0:
    #         while gap_end_time <= day_end:
    #             timeslots[gap_start_time.strftime('%H:%M')] = list(config.places[new_reservation.type])
    #             gap_start_time = (gap_start_time + timedelta(minutes=config.time_step))
    #             gap_end_time = gap_start_time + timedelta(hours=new_reservation.period)
    #     elif len(reservations_on_day) >= 1:
    #         while gap_end_time <= day_end:
    #             reservations_overlap = find_overlaps(reservations_on_day, (gap_start_time, gap_end_time))
    #             if len(reservations_overlap) > 0:
    #                 booked_places = reservations_overlap['Place'].astype(int).to_list()
    #                 free_places = list(sorted(set(config.places[new_reservation.type]) - set(booked_places)))
    #                 if len(free_places) > 0:
    #                     timeslots[gap_start_time.strftime('%H:%M')] = free_places
    #             else:
    #                 timeslots[gap_start_time.strftime('%H:%M')] = list(config.places[new_reservation.type])
                
    #             gap_start_time = (gap_start_time + timedelta(minutes=config.time_step))
    #             gap_end_time = gap_start_time + timedelta(hours=new_reservation.period)

    #     return timeslots


#     def generate_available_timeslots(reservation_table: pd.DataFrame, new_reservation:Reservation, on_date : datetime) -> dict[str, list[int]]:
#         available_timeslots = {}
        
#         # Convert stride to timedelta
#         # stride = timedelta(minutes=stride_minutes)
#         stride = timedelta(minutes=config.time_step)
        
#         # Convert reservation period to timedelta
#         reservation_period = timedelta(hours=new_reservation.period)

#         gaps = find_reservation_gaps(df=reservation_table, 
#                                     selected_date=on_date, 
#                                     reservation_type=new_reservation.type, 
#                                     min_gap_hours=new_reservation.period)
        
#         # Iterate through all gaps for all places
#         for place, place_gaps in gaps.items():
#             for gap in place_gaps:
#                 current_time = gap['start']
#                 while current_time + reservation_period <= gap['end']:
#                     # Format the current time as a string key
#                     time_key = current_time.strftime('%H:%M')
                    
#                     # Add the place to the list of available places for this timeslot
#                     if time_key not in available_timeslots:
#                         available_timeslots[time_key] = []
#                     available_timeslots[time_key].append(place)
                    
#                     # Move to the next timeslot
#                     current_time += stride
        
#         # Sort the timeslots
#         available_timeslots = dict(sorted(available_timeslots.items()))
        
#         return available_timeslots


#     def find_reservation_gaps(df:pd.DataFrame, selected_date:datetime|str, reservation_type:str, min_gap_hours=0):
#         """
#         Find gaps between reservations for each place on a selected date.
#         Handles empty DataFrames and returns all places as fully available.
        
#         Args:
#             df (pd.DataFrame): Reservations DataFrame
#             selected_date (datetime|str): Date to check for gaps
#             reservation_type (str): Type of reservation (e.g., 'hairstyle', 'brows')
#             min_gap_hours (float): Minimum gap duration to consider (in hours)
        
#         Returns:
#             dict: Dictionary of gaps for each place
#         """
#         # Convert selected_date to datetime if it's a string
#         if isinstance(selected_date, str):
#             selected_date = datetime.strptime(selected_date, '%Y-%m-%d')
        
#         # Initialize dictionary to store gaps for each place
#         gaps = {}
        
#         # Get places for the reservation type
#         places = config.places[reservation_type]
        
#         # If DataFrame is empty or has no reservations for the day,
#         # return full day availability for all places
#         if df.empty:
#             for place in places:
#                 start = datetime.combine(selected_date.date(), config.workday_start)
#                 end = datetime.combine(selected_date.date(), config.workday_end)
#                 gap = {
#                     'start': start,
#                     'end': end,
#                     'duration': (end - start).total_seconds() / 3600  # in hours
#                 }
#                 gaps[place] = [gap]
#             return gaps
        
#         try:        
#             # Ensure datetime columns are properly formatted
#             if not pd.api.types.is_datetime64_any_dtype(df['time_from']):
#                 df['time_from'] = pd.to_datetime(df['time_from']).dt.time
                
#             if not pd.api.types.is_datetime64_any_dtype(df['time_to']):
#                 df['time_to'] = pd.to_datetime(df['time_to']).dt.time
                
#             # Filter for selected date
#             df_day = df[df['time_from'].dt.date == selected_date.date()]
            
#             # Sort by start time
#             df_day = df_day.sort_values('time_from')
            
#             for place in places:
#                 # Filter reservations for this place
#                 place_reservations = df_day[df_day['place'].astype(int) == place]
                
#                 place_gaps = []

#                 if place_reservations.empty:
#                     # If there are no reservations for this place, the whole day is a gap
#                     start = datetime.combine(selected_date.date(), config.workday_start)
#                     end = datetime.combine(selected_date.date(), config.workday_end)
#                     gap = {
#                         'start': start,
#                         'end': end,
#                         'duration': (end - start).total_seconds() / 3600  # in hours
#                     }
#                     place_gaps.append(gap)
#                     gaps[place] = place_gaps
#                     continue
                
#                 # Start of the day
#                 previous_end = datetime.combine(selected_date.date(), config.workday_start)
                
#                 for _, reservation in place_reservations.iterrows():
#                     if reservation['time_from'] > previous_end:
#                         gap_duration = (reservation['time_from'] - previous_end).total_seconds() / 3600
#                         if gap_duration >= min_gap_hours:
#                             gap = {
#                                 'start': previous_end,
#                                 'end': reservation['time_from'],
#                                 'duration': gap_duration
#                             }
#                             place_gaps.append(gap)
                    
#                     previous_end = reservation['time_to']
                
#                 # Check for gap at the end of the day
#                 day_end = datetime.combine(selected_date.date(), config.workday_end)
#                 if previous_end < day_end:
#                     gap_duration = (day_end - previous_end).total_seconds() / 3600
#                     if gap_duration >= min_gap_hours:
#                         gap = {
#                             'start': previous_end,
#                             'end': day_end,
#                             'duration': gap_duration
#                         }
#                         place_gaps.append(gap)
                
#                 if place_gaps:  # Only add to gaps if there are any gaps longer than min_gap_hours
#                     gaps[place] = place_gaps
                
#         except Exception as e:
#             print(f"Error processing reservations: {str(e)}")
#             # In case of any error, return full day availability for all places
#             for place in places:
#                 start = datetime.combine(selected_date.date(), config.workday_start)
#                 end = datetime.combine(selected_date.date(), config.workday_end)
#                 gap = {
#                     'start': start,
#                     'end': end,
#                     'duration': (end - start).total_seconds() / 3600  # in hours
#                 }
#                 gaps[place] = [gap]
        
#         return gaps


#     def generate_order_id(r: Reservation):
#         return f'{r.day.strftime("%Y-%m-%d")}_{r.period}h_{r.time_from.strftime("%H-%M")}_p{r.place}_{r.telegram_id}'


    def localize_from_db(self, dt:datetime.datetime):
        """Convert UTC datetime from DB to local timezone"""
        if dt is None:
            return None
        
        if isinstance(dt, datetime.datetime):
            # Convert UTC datetime to local timezone
            if dt.tzinfo is None:
                dt = pytz.UTC.localize(dt)
            return dt.astimezone(pytz.timezone(config.LOCAL_TIMEZONE))
        elif isinstance(dt, date):
            # Only date, no timezone conversion needed
            return dt
        return dt

#     def prepare_for_db(dt, day=None):
#         """Convert local time/datetime to UTC datetime for DB storage"""
#         if dt is None:
#             return None
            
#         if isinstance(dt, datetime):
#             # If datetime has no timezone, assume it's in local timezone
#             if dt.tzinfo is None:
#                 dt = pytz.timezone('UTC').localize(dt)
#             # Convert to UTC for storage
#             return dt.astimezone(pytz.UTC)
#         elif isinstance(dt, time):
#             # Convert time to datetime using the provided day or current day
#             if day is None:
#                 day = date.today()
#             dt_combined = datetime.combine(day, dt)
#             if dt_combined.tzinfo is None:
#                 dt_combined = pytz.timezone('UTC').localize(dt_combined)
#             return dt_combined.astimezone(pytz.UTC)
#         return dt

class DatabaseError(Exception):
    """Custom exception for database-related errors"""
    pass
