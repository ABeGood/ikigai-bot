from datetime import datetime, timedelta
from classes.classes import Reservation
import pandas as pd
import config


def find_closest_slot_start(mins_buffer):
    current_datetime = datetime.now()
    if 0 <= current_datetime.minute <= 30-mins_buffer:  # xx:00 - xx:20
        next_available_timeslot_start = (current_datetime.replace(minute=30, second=0, microsecond=000000))  # give xx:30
    elif 30-mins_buffer <= current_datetime.minute <= 60-mins_buffer:  # xx:20 - xx:50
        next_available_timeslot_start = (current_datetime.replace(hour=current_datetime.hour+1, minute=0, second=0, microsecond=000000))  # give xx+1:00
    elif 60-mins_buffer <= current_datetime.minute < 60:  # xx:50 - xx:59
        next_available_timeslot_start = (current_datetime.replace(hour=current_datetime.hour+1, minute=30, second=0, microsecond=000000))  # give xx+1:30
    return next_available_timeslot_start


def generate_days_intervals(to_date: datetime, timeslot_size_h: int) -> list[datetime]:
    days: list[datetime] = []
    mins_buffer = 10

    current_datetime = datetime.now()   
    end_of_current_day = current_datetime.replace(hour=23, minute=59, second=59, microsecond=999999)

    if current_datetime < current_datetime.replace(hour=6, minute=0, second=0, microsecond=0):
        days.append(current_datetime.replace(hour=6, minute=0, second=0, microsecond=0))

    elif current_datetime + timedelta(hours=timeslot_size_h, minutes=mins_buffer) <= end_of_current_day:
        next_available_timeslot_start = find_closest_slot_start(mins_buffer=mins_buffer)
        days.append(pd.to_datetime(next_available_timeslot_start))


    start_of_the_next_day = current_datetime.replace(hour=6, minute=0, second=0, microsecond=0) + timedelta(days=1)
    date_range_with_time = pd.date_range(start_of_the_next_day, end=to_date, freq='D')

    for day in date_range_with_time:
        # Generate time intervals from 06:00 to 23:59 for the full days
        days.append(day)
        
    return days


def find_available_days(new_reservation: Reservation, reservation_table: pd.DataFrame, to_date = None) -> list[datetime]:  # AG: Now returns only days with no reservations
    current_datetime = datetime.now()
    if to_date is None:
        to_date = (current_datetime.replace(day=1) + timedelta(days=150)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    days_to_check = generate_days_intervals(to_date, timeslot_size_h=new_reservation.period)


    # Initialize list to store time gaps
    available_days: list[datetime] = []

    # Iterate through each day within the specified range
    for day_start in days_to_check:
        # Convert day to string format
        day_end = day_start.replace(hour=23, minute=59, second=59) - timedelta(hours=new_reservation.period)
        print(f'Day: {day_start}')

        day_str = day_start.strftime('%Y-%m-%d')

        # Filter reservations for the current day
        reservations_on_day = reservation_table[reservation_table['Day'] == day_str]
        print(f'Reservations on {day_str}: {len(reservations_on_day)}')
        if len(reservations_on_day) == 0:
            available_days.append(day_start)
        else:
            possible_timeslots = pd.DataFrame()
            possible_timeslots['From'] = pd.Series(pd.date_range(day_start, day_end, freq=f'{new_reservation.period}h'))
            possible_timeslots['To'] = possible_timeslots['From'] + pd.Timedelta(hours=new_reservation.period)

            available_timeslots = (
                pd.merge_asof(possible_timeslots, reservations_on_day.add_suffix('_existing'), left_on='From', right_on='From_existing')
                .loc[lambda d: ~((d['From_existing'].ge(d['From_existing']) & d['From_existing'].lt(d['To']))
                                |(d['To_existing'].le(d['To']) & d['To_existing'].gt(d['From']))
                                ),
                        ['From', 'To']]
                )
            
            if not available_timeslots.empty:
                available_days.append(day_start)

    return available_days


def find_timeslots(new_reservation: Reservation, reservation_table: pd.DataFrame, on_date : datetime) -> dict[str, list[int]]:  # AG: Now returns only days with no reservations
    timeslots: dict[str, list[int]] = {}
    time_step = 30 # min
    time_buffer_mins = 25
    day_start : datetime
    day_end = on_date.replace(hour=23, minute=59, second=59, microsecond=999999)
    current_datetime = datetime.now()  

    if on_date.date() == current_datetime.now().date():
        day_start = find_closest_slot_start(mins_buffer=time_buffer_mins)
    else:
        day_start = on_date.replace(hour=6, minute=0, second=0, microsecond=0)


    day_str = day_start.strftime('%Y-%m-%d')

    # Filter reservations for the current day
    reservations_on_day = reservation_table[reservation_table['Day'] == day_str]
    reservations_on_day = reservations_on_day[reservations_on_day['Type'] == new_reservation.type]
    reservations_on_day.sort_values(by='From', inplace=True)
    print(f'Reservations on {day_str}: {len(reservations_on_day)}')

    gap_start_time = day_start
    gap_end_time = gap_start_time + timedelta(hours=new_reservation.period)

    if len(reservations_on_day) == 0:
        while gap_end_time <= day_end:
            timeslots[gap_start_time.strftime('%H:%M')] = list(config.places[new_reservation.type])
            gap_start_time = (gap_start_time + timedelta(minutes=time_step))
            gap_end_time = gap_start_time + timedelta(hours=new_reservation.period)
    elif len(reservations_on_day) >= 1:
        while gap_end_time <= day_end:
            reservations_overlap = find_overlaps(reservations_on_day, (gap_start_time, gap_end_time))
            if len(reservations_overlap) > 0:
                booked_places = reservations_overlap['Place'].astype(int).to_list()
                free_places = list(sorted(set(config.places[new_reservation.type]) - set(booked_places)))
                if len(free_places) > 0:
                    timeslots[gap_start_time.strftime('%H:%M')] = free_places
            else:
                timeslots[gap_start_time.strftime('%H:%M')] = list(config.places[new_reservation.type])
            
            gap_start_time = (gap_start_time + timedelta(minutes=time_step))
            gap_end_time = gap_start_time + timedelta(hours=new_reservation.period)

    return timeslots


def find_overlaps(reservations: pd.DataFrame, time_gap: tuple[datetime, ...]) -> pd.DataFrame:
    mask =  ((reservations['From'] <= time_gap[0]) & (time_gap[0] <= reservations['To'])) | \
            ((reservations['From'] <= time_gap[1]) & (time_gap[1] <= reservations['To']))   | \
            ((time_gap[0] <= reservations['From']) & (reservations['From'] <= time_gap[1]))   | \
            ((time_gap[0] <= reservations['To']) & (reservations['To'] <= time_gap[1]))
    
    return reservations.loc[mask]

def generate_order_id(r: Reservation):
    return f'{r.day.strftime("%Y-%m-%d")}_{r.period}h_{r.time_from.strftime("%H-%M")}_p{r.place}_{r.telegramId}'