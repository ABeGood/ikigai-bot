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

    current_datetime = datetime.now()   
    end_of_current_day = current_datetime.replace(hour=config.workday_end.hour-1, minute=59, second=59, microsecond=999)

    if current_datetime.time() < config.workday_start:
        days.append(current_datetime.replace(hour=config.workday_start.hour,
                                            minute=config.workday_start.minute,
                                            second=config.workday_start.second))

    elif current_datetime + timedelta(hours=timeslot_size_h, minutes=config.time_buffer_mins) <= end_of_current_day:
        next_available_timeslot_start = find_closest_slot_start(mins_buffer=config.time_buffer_mins)
        days.append(pd.to_datetime(next_available_timeslot_start))
    

    start_of_the_next_day = current_datetime.replace(hour=config.workday_start.hour, 
                                                    minute=config.workday_start.minute, 
                                                    second=config.workday_start.second, 
                                                    microsecond=config.workday_start.microsecond
                                                    ) + timedelta(days=1)
    
    date_range_with_time = pd.date_range(start_of_the_next_day, end=to_date, freq='D')

    for day in date_range_with_time:
        # Generate time intervals from 06:00 to 23:59 for the full days
        days.append(day)
        
    return days


def find_available_days(new_reservation: Reservation, reservation_table: pd.DataFrame, to_date = None) -> list[datetime]:  # AG: Now returns only days with no reservations
    current_datetime = datetime.now()

    # Some kind of lookforward; TODO: refactor
    if not to_date:
        to_date = (current_datetime.replace(day=1) + timedelta(days=config.days_lookforward)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    days_to_check = generate_days_intervals(to_date, timeslot_size_h=new_reservation.period)

    # Initialize list to store time gaps
    available_days: list[datetime] = []

    # Iterate through each day within the specified range
    for day_start in days_to_check:
        gaps = find_reservation_gaps(reservation_table, selected_date=day_start, reservation_type=new_reservation.type, min_gap_hours=new_reservation.period)

        if len(gaps) > 0:
            available_days.append(day_start)

    return available_days


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


def generate_available_timeslots(reservation_table: pd.DataFrame, new_reservation:Reservation, on_date : datetime) -> dict[str, list[int]]:
    available_timeslots = {}
    
    # Convert stride to timedelta
    # stride = timedelta(minutes=stride_minutes)
    stride = timedelta(minutes=config.time_step)
    
    # Convert reservation period to timedelta
    reservation_period = timedelta(hours=new_reservation.period)

    gaps = find_reservation_gaps(df=reservation_table, 
                                 selected_date=on_date, 
                                 reservation_type=new_reservation.type, 
                                 min_gap_hours=new_reservation.period)
    
    # Iterate through all gaps for all places
    for place, place_gaps in gaps.items():
        for gap in place_gaps:
            current_time = gap['start']
            while current_time + reservation_period <= gap['end']:
                # Format the current time as a string key
                time_key = current_time.strftime('%H:%M')
                
                # Add the place to the list of available places for this timeslot
                if time_key not in available_timeslots:
                    available_timeslots[time_key] = []
                available_timeslots[time_key].append(place)
                
                # Move to the next timeslot
                current_time += stride
    
    # Sort the timeslots
    available_timeslots = dict(sorted(available_timeslots.items()))
    
    return available_timeslots


# def find_overlaps(reservations: pd.DataFrame, time_gap: tuple[datetime, ...]) -> pd.DataFrame:
#     mask =  ((reservations['From'] <= time_gap[0]) & (time_gap[0] < reservations['To'])) | \
#             ((reservations['From'] <= time_gap[1]) & (time_gap[1] < reservations['To']))   | \
#             ((time_gap[0] <= reservations['From']) & (reservations['From'] <= time_gap[1]))   | \
#             ((time_gap[0] < reservations['To']) & (reservations['To'] < time_gap[1]))
    
#     return reservations.loc[mask]


def find_reservation_gaps(df:pd.DataFrame, selected_date:datetime|str, reservation_type:str, min_gap_hours=0):
    # Convert selected_date to datetime if it's a string
    if isinstance(selected_date, str):
        selected_date = datetime.strptime(selected_date, '%Y-%m-%d')
    
    # Filter the dataframe for the selected date
    df_day = df[df['From'].dt.date == selected_date.date()]
    
    # Sort by 'From' time
    df_day = df_day.sort_values('From')
    
    # Initialize dictionary to store gaps for each place
    gaps = {}
    
    # Get unique places (assuming place information is in the 'OrderId')
    places = config.places[reservation_type]
    
    for place in places:
        # Filter reservations for this place
        place_reservations = df_day[df_day['Place'].astype(int) == place]
        
        place_gaps = []

        if place_reservations.empty:
            # If there are no reservations for this place, the whole day is a gap
            start = datetime.combine(selected_date.date(), config.workday_start)
            end = datetime.combine(selected_date.date(), config.workday_end)
            gap = {
                'start': start,
                'end': end,
                'duration': (end - start).total_seconds() / 3600  # in hours
            }
            place_gaps.append(gap)
            gaps[place] = place_gaps
            continue
        
        # Start of the day
        previous_end = datetime.combine(selected_date.date(), config.workday_start)
        
        for _, reservation in place_reservations.iterrows():
            if reservation['From'] > previous_end:
                gap_duration = (reservation['From'] - previous_end).total_seconds() / 3600  # in hours
                if gap_duration > min_gap_hours:
                    gap = {
                        'start': previous_end,
                        'end': reservation['From'],
                        'duration': gap_duration
                    }
                    place_gaps.append(gap)
            
            previous_end = reservation['To']
        
        # Check for gap at the end of the day
        day_end = datetime.combine(selected_date.date(), config.workday_end)
        if previous_end < day_end:
            gap_duration = (day_end - previous_end).total_seconds() / 3600  # in hours
            if gap_duration > min_gap_hours:
                gap = {
                    'start': previous_end,
                    'end': day_end,
                    'duration': gap_duration
                }
                place_gaps.append(gap)
        
        if place_gaps:  # Only add to gaps if there are any gaps longer than min_gap_hours
            gaps[place] = place_gaps
    
    return gaps


def generate_order_id(r: Reservation):
    return f'{r.day.strftime("%Y-%m-%d")}_{r.period}h_{r.time_from.strftime("%H-%M")}_p{r.place}_{r.telegramId}'


# WTF? Why here?
def format_reservation_recap(reservation: Reservation):
    return f'''*Ваша резервация:*
*Дата:* {reservation.day.strftime('%Y-%m-%d')}
*Время:* {reservation.time_from.strftime('%H:%M')} - {reservation.time_to.strftime('%H:%M')}
*Место:* {reservation.place}
*Стоимость*: *666* CZK
'''


def format_prepay(sum: float):
    return f'''Мы принимаем оплату онлайн-банк *Revolut*.
- Кнопка *"Оплатить 🪙"* неренаправит Вас на *страницу оплаты*.
- *Сумма*: *{sum}* CZK
- После оплаты нажмите "Готово ✅".

Нам будет удобно, если в платеже Вы укажите *своё имя*.
Спасибо! ✨
'''


def format_reservation_confirm(reservation: Reservation):
    return f'''🎉 *Ваша резервация подтверждена и ждет оплаты!*
*Дата:* {reservation.day.strftime('%Y-%m-%d')}
*Время:* {reservation.time_from.strftime('%H:%M')} - {reservation.time_to.strftime('%H:%M')}
*Место:* {reservation.place}

До встречи!
'''

def format_reservation_confirm_and_payed(reservation: Reservation):
    return f'''🎉 *Ваша резервация подтверждена и оплачена!*
*Дата:* {reservation.day.strftime('%Y-%m-%d')}
*Время:* {reservation.time_from.strftime('%H:%M')} - {reservation.time_to.strftime('%H:%M')}
*Место:* {reservation.place}

До встречи!
'''

def format_reservation_info(day, time_from, time_to, place):
    return f"""
День: {day.strftime('%Y-%m-%d')}\n\
Время: {time_from.strftime('%H:%M')} - {time_to.strftime('%H:%M')}\n\
Место: {place}
"""