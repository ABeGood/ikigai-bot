import pandas as pd
import google_sheets_api as gs
from datetime import datetime, timedelta, date
from util.utils import find_overlap

class ReservationTable():

    table = None
    time_from = '06:00'
    time_to = '24:00'

    def __init__(self) -> None:
        self.table = self.read_table_to_df()

    def read_table_to_df(self):
        self.table = gs.read_table_to_df()

        if self.table.empty:
            self.table = pd.DataFrame(columns=['OrderId', 'TelegramId', 'Name', 'Type', 'Day', 'From','To','Payed'])

        # self.table['From'] = pd.to_datetime(self.table['From'])
        self.table['From'] = pd.to_datetime(self.table['From'])
        self.table['To'] = pd.to_datetime(self.table['To'])
        self.table['Day'] = pd.to_datetime(self.table['Day'])
        return self


    def save_reservation_to_table(self, new_reservation):

        time_from = datetime.combine(new_reservation.day.date(), new_reservation.time_from.time())
        time_to = time_from + pd.Timedelta(hours=int(new_reservation.period))

        new_reservation_df = pd.DataFrame(
                {
                    'OrderId': [new_reservation.orderid],
                    'TelegramId': [new_reservation.telegramId],
                    'Name': [new_reservation.name],
                    'Type': [new_reservation.type],
                    'Day': [new_reservation.day],
                    'From': [time_from],
                    'To': [time_to],
                    'Payed': [False]
                }
            )
        
        self.table = pd.concat([self.table, new_reservation_df])
        try:
            gs.save_df_to_table(self.table)
            return True
        except Exception as e:
            print(e.with_traceback)
            return False
        


    def get_days(self, to_date: datetime, timeslot_size_h):
        days = []
        mins_buffer = 10
        current_datetime = datetime.now()
        
        end_of_current_day = current_datetime.replace(hour=23, minute=59, second=59, microsecond=999999)

        if current_datetime + timedelta(hours=timeslot_size_h, minutes=mins_buffer) <= end_of_current_day:
            if (current_datetime + timedelta(minutes=mins_buffer)).minute < 30:
                next_available_timeslot_start = (current_datetime.replace(minute=30, second=0, microsecond=000000))
            else:
                next_available_timeslot_start = (current_datetime.replace(hour=current_datetime.hour+1, minute=0, second=0, microsecond=000000))

            end_of_current_day = current_datetime.replace(hour=23, minute=59, second=59, microsecond=999999)
            days.append([next_available_timeslot_start, end_of_current_day])


        start_of_the_next_day = current_datetime.replace(hour=6, minute=0, second=0, microsecond=0) + timedelta(days=1)
        date_range_with_time = pd.date_range(start_of_the_next_day, end=to_date, freq='D')

        for day in date_range_with_time:
            # Generate time intervals from 06:00 to 23:59 for the full days
            days.append([day, day.replace(hour=23, minute=59, second=59)])
            
        return days


    def find_time_gaps(self, n_of_hours: int):  # AG: Now returns only days with no reservations

        n_of_hours = int(n_of_hours)
        current_datetime = datetime.now()
        to_date = (current_datetime.replace(day=1) + timedelta(days=32)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Convert 'From' and 'To' columns to datetime objects
        reservations_table = self.table.copy()
        reservations_table['From'] = pd.to_datetime(reservations_table['From'])
        reservations_table['To'] = pd.to_datetime(reservations_table['To'])

        # Parse time_start and time_end strings to datetime objects
        time_start = pd.to_datetime('2000-01-01 ' + '06:00:00')
        time_end = pd.to_datetime('2000-01-01 ' + '00:00:00')


        # Initialize list to store time gaps
        timeslots = {}
        time_step = 30 # min

        # Iterate through each day within the specified range
        for day in self.get_days(to_date, timeslot_size_h=n_of_hours):
            # Convert day to string format
            day_start = day[0]
            day_end = day[1]
            print(f'Day: {day_start} - {day_end}')

            day_str = day_start.strftime('%Y-%m-%d')

            # Filter reservations for the current day
            reservations_on_day = reservations_table[reservations_table['Day'] == day_str]
            reservations_on_day.sort_values(by='From', inplace=True)
            print(f'Reservations at this day: {len(reservations_on_day)}')

            gap_start_time = day_start
            gap_end_time = gap_start_time + timedelta(hours=n_of_hours)

            if len(reservations_on_day) == 0:
                while gap_end_time <= day_end:
                    timeslots.setdefault(day_str,[]).append(gap_start_time)
                    gap_start_time = (gap_start_time + timedelta(minutes=time_step))  # .replace(second=0, microsecond=0)
                    gap_end_time = gap_start_time + timedelta(hours=n_of_hours)
            elif len(reservations_on_day) >= 1:
                for _, reservation in reservations_on_day.iterrows():
                    next_reservation_start = reservation['From']
                    next_reservation_end = reservation['To']
                    # new_reservation = [gap_start_time, gap_end_time]

                    while gap_end_time <= next_reservation_start:
                        timeslots.setdefault(day_str,[]).append(gap_start_time)
                        gap_start_time = (gap_start_time + timedelta(minutes=time_step))  # .replace(second=0, microsecond=0)
                        gap_end_time = gap_start_time + timedelta(hours=n_of_hours)

                    gap_start_time = next_reservation_end
                    gap_end_time = gap_start_time + timedelta(hours=n_of_hours)

                    # if not find_overlap(new_reservation, existing_reservation):
                    #     timeslots[day_str].append((gap_start_time, gap_end_time))
                    #     gap_start_time = gap_start_time + timedelta(minutes=time_step).replace(second=0, microsecond=0)
                    #     gap_end_time = gap_start_time + timedelta(hours=n_of_hours)
                    # else:
                    #     gap_start_time = gap_start_time + timedelta(minutes=time_step).replace(second=0, microsecond=0)
                    #     gap_end_time = gap_start_time + timedelta(hours=n_of_hours)
                else:
                    while gap_end_time <= day_end:
                        timeslots.setdefault(day_str,[]).append(gap_start_time)
                        gap_start_time = (gap_start_time + timedelta(minutes=time_step))  # .replace(second=0, microsecond=0)
                        gap_end_time = gap_start_time + timedelta(hours=n_of_hours)


            # for _, reservation in reservations_on_day.iterrows():
            #         # If there is a gap between the previous reservation and the current one
            #         if reservation['From'] > gap_start_time:
            #             n_of_free_hours = reservation['From'] - gap_start_time
                        
            #             # if int(n_of_free_hours.hours()) >= int(n_of_hours):
            #             while int(n_of_free_hours.hours()) >= int(n_of_hours):
            #                 time_gaps.append(gap_start_time)
            #                 gap_start_time = gap_start_time + timedelta(minutes=time_step).replace(second=0, microsecond=0)
            #             else:
            #                 gap_start_time = reservation['To']
            #         # Update gap_start_time to the end of the current reservation

        return timeslots

