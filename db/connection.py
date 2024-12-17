from typing import Generator, Optional, List
from contextlib import contextmanager
import os
from datetime import datetime, date, time, timedelta
import pytz
from urllib.parse import urlparse
import pandas as pd
from sqlalchemy import create_engine, event, and_, or_
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError, OperationalError
import logging
from functools import lru_cache
from tenacity import retry, stop_after_attempt, wait_exponential

from db import models
from tg_bot.config import places, workday_start, workday_end, days_lookforward, LOCAL_TIMEZONE

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseConfig:
    def __init__(self):
        self.database_url = self._get_database_url()
        self.pool_settings = {
            'pool_size': int(os.getenv("DB_POOL_SIZE", "10")),
            'max_overflow': int(os.getenv("DB_MAX_OVERFLOW", "20")),
            'pool_timeout': int(os.getenv("DB_POOL_TIMEOUT", "30")),
            'pool_recycle': int(os.getenv("DB_POOL_RECYCLE", "1800")),
            'pool_pre_ping': True
        }
        self.workday_settings = {
            'workday_start': int(os.getenv("WORKDAY_START", "9")),
            'workday_end': int(os.getenv("WORKDAY_END", "21")),
            'time_buffer': int(os.getenv("TIME_BUFFER", "30")),
            'lookforward_days': int(os.getenv("LOOKFORWARD_DAYS", "30"))
        }
        
    def _get_database_url(self) -> str:
        url = os.getenv("DATABASE_URL")
        if not url:
            url = self._construct_db_url()
        
        if url and "postgres.railway.internal" in url:
            url = os.getenv("EXTERNAL_DATABASE_URL", url)
            
        if url and url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
            
        if not url:
            raise DatabaseConfigError("No database URL configured")
            
        return url
    
    @staticmethod
    def _construct_db_url() -> Optional[str]:
        required_params = ["PGHOST", "PGPORT", "PGDATABASE", "PGUSER", "PGPASSWORD"]
        params = {param: os.getenv(param) for param in required_params}
        
        if all(params.values()):
            return f"postgresql://{params['PGUSER']}:{params['PGPASSWORD']}@{params['PGHOST']}:{params['PGPORT']}/{params['PGDATABASE']}"
        return None

class Database:
    def __init__(self):
        self.config = DatabaseConfig()
        self.engine = self._create_engine()
        self.SessionLocal = self._create_session_factory()
        self._setup_engine_events()

    def _create_engine(self) -> Engine:
        return create_engine(
            self.config.database_url,
            poolclass=QueuePool,
            **self.config.pool_settings
        )

    def _create_session_factory(self) -> sessionmaker:
        return sessionmaker(
            bind=self.engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False
        )

    def _setup_engine_events(self):
        @event.listens_for(self.engine, "connect")
        def connect(dbapi_connection, connection_record):
            logger.info("Database connection established")
            
        @event.listens_for(self.engine, "checkout")
        def checkout(dbapi_connection, connection_record, connection_proxy):
            logger.debug("Connection checked out from pool")

    def find_available_days(self, new_reservation: 'Reservation') -> List[datetime]:
        """Find available days for a new reservation"""
        try:
            with self.get_db() as session:
                return self._find_available_days(session, new_reservation)
        except Exception as e:
            logger.error(f"Error finding available days: {str(e)}")
            return []

    def get_last_reservation_by_telegram_id(self, telegram_id: str):
        """Get the most recent reservation for a user"""
        with self.get_db() as session:
            reservation = session.query(models.Reservation)\
                .filter(models.Reservation.telegram_id == telegram_id)\
                .order_by(models.Reservation.created_at.desc())\
                .first()
            return reservation if reservation else None
        
    def get_reservation_by_order_id(self, order_id: str) -> Optional[models.Reservation]:
        """Get a reservation by its order ID"""
        try:
            with self.get_db() as session:
                return session.query(models.Reservation)\
                    .filter(models.Reservation.order_id == order_id)\
                    .first()
        except Exception as e:
            logger.error(f"Error getting reservation by order ID: {str(e)}")
            return None
        
    def get_upcoming_reservations_by_telegram_id(self, telegram_id: str) -> List[models.Reservation]:
        """
        Get all upcoming reservations for a specific telegram user id.
        
        Args:
            telegram_id: User's telegram id
            
        Returns:
            List of upcoming Reservation model instances
        """
        try:
            with self.get_db() as session:
                # Get current datetime in UTC
                current_datetime = datetime.now(LOCAL_TIMEZONE)
                current_date = current_datetime.date()
                
                # Query upcoming reservations
                upcoming_reservations = session.query(models.Reservation).filter(
                    and_(
                        models.Reservation.telegram_id == telegram_id,
                        or_(
                            # Future dates
                            models.Reservation.day > current_date,
                            # Today but future time
                            and_(
                                models.Reservation.day == current_date,
                                models.Reservation.time_from > current_datetime
                            )
                        )
                    )
                ).order_by(
                    models.Reservation.day,
                    models.Reservation.time_from
                ).all()
                
                return upcoming_reservations
                
        except Exception as e:
            logger.error(f"Error getting upcoming reservations: {str(e)}")
            return []


    def get_unpaid_reservations_by_telegram_id(self, telegram_id: str):
        """Get all future unpaid reservations without payment confirmation for a user"""
        current_datetime = datetime.now(LOCAL_TIMEZONE)
        current_date = current_datetime.date()
        
        with self.get_db() as session:
            reservations = session.query(models.Reservation)\
                .filter(
                    models.Reservation.telegram_id == telegram_id,
                    (models.Reservation.payment_confirmation_link == None) | 
                    (models.Reservation.payment_confirmation_link == ''),
                    or_(
                        # Future dates
                        models.Reservation.day > current_date,
                        # Today but future time
                        and_(
                            models.Reservation.day == current_date,
                            models.Reservation.time_from > current_datetime
                        )
                    )
                )\
                .order_by(models.Reservation.created_at.desc())\
                .all()
            return reservations if reservations else []
    
    def get_paid_unconfirmed_reservations(self):
        """
        Get all future reservations that have payment confirmation but are not marked as paid.
        
        Returns:
            list: List of Reservation objects that are:
                - Have payment confirmation link
                - Not marked as paid (payed == False)
                - Haven't started yet (future reservations)
        """
        current_datetime = datetime.now(LOCAL_TIMEZONE)
        current_date = current_datetime.date()
        
        with self.get_db() as session:
            reservations = session.query(models.Reservation)\
                .filter(
                    models.Reservation.payed == False,
                    models.Reservation.payment_confirmation_link.isnot(None),
                    models.Reservation.payment_confirmation_link != '',
                    or_(
                        # Future dates
                        models.Reservation.day > current_date,
                        # Today but future time
                        and_(
                            models.Reservation.day == current_date,
                            models.Reservation.time_from > current_datetime
                        )
                    )
                )\
                .order_by(models.Reservation.created_at.desc())\
                .all()
            return reservations if reservations else []
    
    def get_reservations_for_date(self, target_date: date) -> List[models.Reservation]:
        """
        Get all reservations for a specific date.
        
        Args:
            target_date: Date object to query reservations for
            
        Returns:
            List of Reservation model instances for the specified date
        """
        try:
            with self.get_db() as session:
                # Query reservations for the target date
                reservations = session.query(models.Reservation).filter(
                    models.Reservation.day == target_date
                ).order_by(
                    models.Reservation.time_from
                ).all()
                
                return reservations
                
        except SQLAlchemyError as e:
            logger.error(f"Database error getting reservations for date {target_date}: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Error getting reservations for date {target_date}: {str(e)}")
            return []

    def get_available_timeslots(self, new_reservation: 'Reservation') -> dict[str, list[int]]:
        """
        Get all available timeslots for the day specified in the new reservation.
        
        Args:
            new_reservation: Reservation object with type, period and day
            
        Returns:
            Dictionary with time slots as keys (format "HH:MM") and lists of available places as values
        """
        # Here I use UTC to keep it compatible with DB.  <-- TODO
        try:
            if not new_reservation.day:
                logger.error("No day specified in reservation")
                return {}

            with self.get_db() as session:
                # Get existing reservations for the day
                existing_reservations = session.query(models.Reservation).filter(
                    and_(
                        # models.Reservation.type == new_reservation.type,
                        models.Reservation.day == new_reservation.day.date()
                    )
                ).all()
                
                # Convert to DataFrame for easier processing
                if existing_reservations:
                    reservations_df = pd.DataFrame([{
                        'time_from': r.time_from,
                        'time_to': r.time_to,
                        'place': r.place
                    } for r in existing_reservations])
                else:
                    reservations_df = pd.DataFrame(columns=['time_from', 'time_to', 'place'])

                # Get configuration
                workday_start = self.config.workday_settings['workday_start']
                workday_end = self.config.workday_settings['workday_end']
                all_places = places.get(new_reservation.type)
                
                if not all_places:
                    return {}

                # Initialize result dictionary
                available_slots = {}
                
                # Calculate time slots
                slot_duration = timedelta(minutes=30)  # 30-minute intervals
                reservation_duration = timedelta(hours=new_reservation.period)
                
                # Set time boundaries
                day_start = new_reservation.day.replace(
                    hour=workday_start,
                    minute=0,
                    second=0,
                    microsecond=0
                )
                day_end = new_reservation.day.replace(
                    hour=workday_end,
                    minute=0,
                    second=0,
                    microsecond=0
                )
                
                # Current time for today's checks
                now = datetime.now(LOCAL_TIMEZONE)
                
                # Iterate through time slots
                current_time : pd.Timestamp = day_start
                while current_time + reservation_duration <= day_end:
                    # Skip past times for today
                    if new_reservation.day.date() == now.date() and pytz.utc.localize(current_time.to_pydatetime()) <= now:
                        current_time += slot_duration
                        continue
                    
                    available_places = []
                    slot_end_time = current_time + reservation_duration
                    
                    # Check each place
                    for place in all_places:
                        is_available = True
                        # Check for overlapping reservations
                        for _, reservation in reservations_df.iterrows():
                            if (pytz.utc.localize(current_time) < reservation['time_to'] and 
                                pytz.utc.localize(slot_end_time) > reservation['time_from'] and 
                                place == reservation['place']):
                                is_available = False
                                break
                        
                        if is_available:
                            available_places.append(place)
                    
                    # Add to results if there are available places
                    if available_places:
                        time_key = current_time.strftime('%H:%M')
                        available_slots[time_key] = available_places

                    current_time += slot_duration
                
                return available_slots
        except Exception as e:
            logger.error(f"Error getting available timeslots: {str(e)}")
            return {}


    def get_upcoming_unpaid_reservations(self) -> List[models.Reservation]:
        """
        Get all upcoming reservations that don't have a payment confirmation link.
        Only returns reservations that have not yet occurred and need payment confirmation.
        
        Returns:
            List[models.Reservation]: List of upcoming Reservation model instances without payment confirmation
        """
        try:
            with self.get_db() as session:
                # Get current datetime in UTC
                current_datetime = datetime.now(LOCAL_TIMEZONE)
                current_date = current_datetime.date()
                
                # Query unpaid reservations that are either:
                # 1. In the future
                # 2. Today but haven't started yet
                upcoming_unpaid = session.query(models.Reservation).filter(
                    and_(
                         or_(
                            models.Reservation.payment_confirmation_link.is_(None),
                            models.Reservation.payment_confirmation_link == ''
                        ),
                        or_(
                            # Future dates
                            models.Reservation.day > current_date,
                            # Today but future time
                            and_(
                                models.Reservation.day == current_date,
                                models.Reservation.time_from > current_datetime
                            )
                        )
                    )
                ).order_by(
                    models.Reservation.created_at.desc()
                ).all()

                return upcoming_unpaid
        except SQLAlchemyError as e:
            logger.error(f"Database error getting reservations without payment: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Error getting reservations without payment: {str(e)}")
            return []


    # def get_available_places_for_timeslot(self, new_reservation: 'Reservation', time_from: time, time_to: time) -> List[int] | None:
    #     """
    #     Find available places for a given timeslot.
        
    #     Args:
    #         new_reservation: Reservation object with day and type
    #         time_from: Time object for start of slot
    #         time_to: Time object for end of slot
            
    #     Returns:
    #         List of available place numbers or None if error
    #     """
    #     try:
    #         if not all([new_reservation.day, new_reservation.type]):
    #             logger.error("Missing required reservation details")
    #             return None

    #         with self.get_db() as session:
    #             # Convert time objects to timezone-aware timestamps for comparison
    #             naive_datetime_from = datetime.combine(new_reservation.day.date(), time_from)
    #             naive_datetime_to = datetime.combine(new_reservation.day.date(), time_to)
                
    #             # Make datetimes timezone-aware
    #             tz = pytz.UTC
    #             datetime_from = tz.localize(naive_datetime_from)
    #             datetime_to = tz.localize(naive_datetime_to)

    #             # Validate time is within working hours
    #             if (time_from < workday_start or 
    #                 time_to > workday_end or
    #                 time_from >= time_to):
    #                 logger.error("Requested time is outside working hours or invalid")
    #                 return None

    #             # Validate not in past
    #             now = datetime.now(pytz.UTC)
    #             if datetime_from <= now:
    #                 logger.error("Requested time is in the past")
    #                 return None

    #             # Get existing reservations for the timeframe
    #             overlapping_reservations = session.query(models.Reservation).filter(
    #                 and_(
    #                     # models.Reservation.type == new_reservation.type,
    #                     models.Reservation.day == new_reservation.day.date(),
    #                     models.Reservation.time_from < datetime_to,
    #                     models.Reservation.time_to > datetime_from
    #                 )
    #             ).all()

    #             # Get all occupied places
    #             occupied_places = {r.place for r in overlapping_reservations}

    #             # Get all possible places for this type from config
    #             all_places = places.get(new_reservation.type)

    #             if not all_places:
    #                 logger.error(f"No places configured for type {new_reservation.type}")
    #                 return None

    #             # Calculate available places
    #             available_places = [
    #                 place for place in all_places 
    #                 if place not in occupied_places
    #             ]

    #             return sorted(available_places)

    #     except Exception as e:
    #         logger.error(f"Error getting available places: {str(e)}")
    #         return None
        
    def generate_order_id(self, r: 'Reservation'):
        return f'{r.day.strftime("%Y-%m-%d")}_{r.period}h_{r.time_from.strftime("%H-%M")}_p{r.place}_{r.telegram_id}'

    def create_reservation(self, reservation: 'Reservation') -> Optional[models.Reservation]:
        """
        Create a new reservation in the database
        
        Args:
            reservation: Reservation object with all required fields
            
        Returns:
            Created Reservation model object or None if creation failed
        """
        try:
            with self.get_db() as session:
                # Convert reservation to dict
                reservation_data = reservation.to_dict()
                
                # Create new reservation model instance
                db_reservation = models.Reservation(
                    order_id=reservation_data['order_id'],
                    telegram_id=reservation_data['telegram_id'],
                    name=reservation_data['name'],
                    type=reservation_data['type'],
                    place=reservation_data['place'],
                    day=reservation_data['day'],
                    time_from=reservation_data['time_from'],
                    time_to=reservation_data['time_to'],
                    period=float(reservation_data['period']),  # Ensure period is float
                    sum=reservation_data['sum'],
                    payed=reservation_data.get('payed', False),
                    payment_confirmation_link=reservation_data.get('payment_confirmation_link')
                )
                
                # Validate time slots are available
                if not self._validate_reservation_slot(session, db_reservation):
                    logger.error(f"Reservation slot not available for order {db_reservation.order_id}")
                    return None

                # Add and commit
                session.add(db_reservation)
                session.commit()
                session.refresh(db_reservation)
                
                return db_reservation
                
        except SQLAlchemyError as e:
            logger.error(f"Database error creating reservation: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error creating reservation: {str(e)}")
            return None

    def delete_reservation(self, order_id: str) -> Optional[dict]:
        """
        Delete a reservation by its order_id.
        
        Args:
            order_id: Unique identifier of the reservation
            
        Returns:
            Dictionary with deleted reservation details or None if deletion failed
        """
        try:
            with self.get_db() as session:
                # Find the reservation
                reservation = session.query(models.Reservation).filter(
                    models.Reservation.order_id == order_id
                ).first()
                
                if not reservation:
                    logger.error(f"Reservation not found for order_id: {order_id}")
                    return None
                
                # Delete the reservation
                session.delete(reservation)
                session.commit()
                
                return reservation
                
        except SQLAlchemyError as e:
            logger.error(f"Database error deleting reservation {order_id}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error deleting reservation {order_id}: {str(e)}")
            return None
        
    def update_reservation(self, order_id: str, update_data: dict) -> bool:
        """
        Update a reservation with new data.
        
        Args:
            order_id: Unique identifier of the reservation
            update_data: Dictionary containing fields to update
            
        Returns:
            Boolean indicating success or failure of update
        """
        try:
            with self.get_db() as session:
                # Find the reservation
                reservation = session.query(models.Reservation).filter(
                    models.Reservation.order_id == order_id
                ).first()
                
                if not reservation:
                    logger.error(f"Reservation not found for order_id: {order_id}")
                    return False
                
                # List of allowed fields to update
                allowed_fields = {
                    # 'name', 'type', 'place', 'day',
                    'time_from', 'time_to', 'period', 'payed',
                    'payment_confirmation_link',
                    'payment_confirmation_file_id'
                }
                
                # Update only allowed fields
                for key, value in update_data.items():
                    if key in allowed_fields:
                        # Handle datetime fields
                        if key in ['time_from', 'time_to']:
                            if value:
                                # Ensure timezone awareness
                                value = datetime.fromisoformat(value) if isinstance(value, str) else value
                        elif key == 'day':
                            if value:
                                # Convert string date to date object if needed
                                value = (
                                    datetime.strptime(value, '%Y-%m-%d').date()
                                    if isinstance(value, str)
                                    else value
                                )
                        
                        setattr(reservation, key, value)
                
                # Validate updated reservation
                if not self._validate_reservation_update(session, reservation):
                    session.rollback()
                    return False
                
                session.commit()
                return reservation
                
        except SQLAlchemyError as e:
            logger.error(f"Database error updating reservation {order_id}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error updating reservation {order_id}: {str(e)}")
            return False

    def update_payment_confirmation(self, reservation_id: str, payment_confirmation_link: str, payment_confirmation_file_id: str) -> models.Reservation|None:
        """Update payment confirmation link for a reservation"""
        with self.get_db() as session:
            reservation = session.query(models.Reservation)\
                .filter(models.Reservation.order_id == reservation_id)\
                .first()
            if reservation:
                reservation.payment_confirmation_link = payment_confirmation_link
                reservation.payment_confirmation_file_id = payment_confirmation_file_id
                session.commit()
                return reservation
            return None

    def _validate_reservation_update(self, session: Session, reservation: models.Reservation) -> bool:
        """
        Validate that the updated reservation doesn't conflict with existing ones.
        
        Args:
            session: Database session
            reservation: Updated reservation to validate
            
        Returns:
            Boolean indicating if update is valid
        """
        try:
            # Check for overlapping reservations
            overlapping = session.query(models.Reservation).filter(
                and_(
                    models.Reservation.type == reservation.type,
                    models.Reservation.place == reservation.place,
                    models.Reservation.day == reservation.day,
                    models.Reservation.id != reservation.id,  # Exclude current reservation
                    or_(
                        and_(
                            models.Reservation.time_from < reservation.time_to,
                            models.Reservation.time_to > reservation.time_from
                        )
                    )
                )
            ).first()
            
            if overlapping:
                logger.error(f"Update would create booking conflict for order_id: {reservation.order_id}")
                return False
            
            # Validate times
            if (reservation.time_from >= reservation.time_to or(reservation.time_to - reservation.time_from).total_seconds() / 3600 != reservation.period):
                logger.error(f"Invalid time range for order_id: {reservation.order_id}")
                return False
            
            # Validate working hours
            workday_start = self.config.workday_settings['workday_start']
            workday_end = self.config.workday_settings['workday_end']
            
            if (
                reservation.time_from.hour < workday_start or
                reservation.time_to.hour > workday_end
            ):
                logger.error(f"Reservation outside working hours for order_id: {reservation.order_id}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating reservation update: {str(e)}")
            return False
        
    def _validate_reservation_slot(self, session: Session, reservation: models.Reservation) -> bool:
        """
        Validate that the requested time slot is available
        
        Args:
            session: Database session
            reservation: Reservation model to validate
            
        Returns:
            bool indicating if slot is available
        """
        # Check for overlapping reservations
        overlapping = session.query(models.Reservation).filter(
            and_(
                models.Reservation.type == reservation.type,
                models.Reservation.place == reservation.place,
                models.Reservation.day == reservation.day,
                or_(
                    and_(
                        models.Reservation.time_from < reservation.time_to,
                        models.Reservation.time_to > reservation.time_from
                    )
                )
            )
        ).first()
        
        return overlapping is None

    def _find_available_days(self, session: Session, new_reservation: 'Reservation') -> List[datetime]:
        now = datetime.now(LOCAL_TIMEZONE)
        end_date = now + timedelta(days=days_lookforward)
        
        # Get existing reservations
        existing_reservations = self._get_existing_reservations(
            session,
            new_reservation.type,
            now,
            end_date
        )
        
        # Generate possible days
        days_to_check = self._generate_days_range(now, end_date)
        
        available_days = []
        for day in days_to_check:
            if self._has_available_slots(day, new_reservation, existing_reservations):
                available_days.append(day)
                
        return available_days

    def _get_existing_reservations(
        self,
        session: Session,
        reservation_type: str,
        start_date: datetime,
        end_date: datetime
    ) -> pd.DataFrame:
        query = (
            session.query(models.Reservation)
            .filter(
                and_(
                    models.Reservation.type == reservation_type,
                    models.Reservation.day >= start_date.date(),
                    models.Reservation.day <= end_date.date()
                )
            )
            .order_by(models.Reservation.day, models.Reservation.time_from)
        )
        
        reservations = query.all()
        
        if not reservations:
            return pd.DataFrame(columns=['day', 'time_from', 'time_to', 'place'])
            
        data = [{
            'day': r.day,
            'time_from': r.time_from,
            'time_to': r.time_to,
            'place': r.place
        } for r in reservations]
            
        return pd.DataFrame(data)

    def _generate_days_range(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[datetime]:
        days = []
        current_day = start_date
        workday_start = self.config.workday_settings['workday_start']
        workday_end = self.config.workday_settings['workday_end']
        
        while current_day <= end_date:
            if current_day == start_date and current_day.hour >= workday_end:
                current_day += timedelta(days=1)
                current_day = current_day.replace(
                    hour=workday_start,
                    minute=0,
                    second=0,
                    microsecond=0
                )
                continue
                
            day_start = current_day.replace(
                hour=workday_start,
                minute=0,
                second=0,
                microsecond=0
            )
            days.append(day_start)
            
            current_day += timedelta(days=1)
            
        return days

    def _has_available_slots(
        self,
        day: datetime,
        new_reservation: 'Reservation',
        existing_reservations: pd.DataFrame
    ) -> bool:
        day_reservations = existing_reservations[
            existing_reservations['day'] == day.date()
        ]
        
        all_places = places.get(new_reservation.type)
        if not all_places:
            return False
            
        duration = timedelta(hours=new_reservation.period)
        workday_start = self.config.workday_settings['workday_start']
        workday_end = self.config.workday_settings['workday_end']
        
        current_time = day.replace(hour=workday_start, minute=0)
        end_time = day.replace(hour=workday_end, minute=0)
        
        while current_time + duration <= end_time:
            if current_time <= datetime.now(LOCAL_TIMEZONE):
                current_time += timedelta(minutes=30)
                continue
                
            for place in all_places:
                if self._is_slot_available(
                    current_time,
                    current_time + duration,
                    place,
                    day_reservations
                ):
                    return True
                    
            current_time += timedelta(minutes=30)
            
        return False

    def _is_slot_available(
        self,
        start_time: datetime,
        end_time: datetime,
        place: int,
        day_reservations: pd.DataFrame
    ) -> bool:
        place_reservations = day_reservations[
            day_reservations['place'] == place
        ]
        
        for _, reservation in place_reservations.iterrows():
            if (start_time < reservation['time_to'] and 
                end_time > reservation['time_from']):
                return False
                
        return True

    # [Previous methods remain unchanged...]
    @contextmanager
    def get_db(self) -> Generator[Session, None, None]:
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error: {str(e)}")
            raise DatabaseError(f"Database operation failed: {str(e)}")
        except Exception as e:
            session.rollback()
            logger.error(f"Unexpected error: {str(e)}")
            raise
        finally:
            session.close()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True
    )
    def execute_with_retry(self, session: Session, operation):
        try:
            return operation(session)
        except OperationalError as e:
            logger.warning(f"Database operation failed, retrying: {str(e)}")
            session.rollback()
            raise

    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert all reservations to a pandas DataFrame with localized times"""
        try:
            with self.get_db() as session:
                reservations = session.query(models.Reservation).all()
                
                if not reservations:
                    return pd.DataFrame(columns=[
                        'id', 'created_at', 'order_id', 'telegram_id', 'name',
                        'type', 'place', 'day', 'time_from', 'time_to', 'period',
                        'sum', 'payed', 'payment_confirmation_link'
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
                        'sum': r.sum,
                        'payed': r.payed,
                        'payment_confirmation_link': r.payment_confirmation_link
                    })
                
                return pd.DataFrame(data)
            
        except Exception as e:
            logger.error(f"Error converting to dataframe: {str(e)}")
            return pd.DataFrame(columns=[
                'id', 'created_at', 'order_id', 'telegram_id', 'name',
                'type', 'place', 'day', 'time_from', 'time_to', 'period',
                'sum', 'payed', 'payment_confirmation_link'
            ])

class DatabaseError(Exception):
    pass

class DatabaseConfigError(DatabaseError):
    pass

class DatabaseConnectionError(DatabaseError):
    pass

class DatabaseOperationError(DatabaseError):
    pass