from datetime import datetime, timedelta
import pandas as pd



def find_available_days(self, n_of_hours: int):
        current_datetime = datetime.now()
        to_date = (current_datetime.replace(day=1) + timedelta(days=32)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        def get_days(to_date: datetime):
            days = []
            end_of_current_day = current_datetime.replace(hour=23, minute=59, second=59, microsecond=999999)
            start_of_the_next_day = current_datetime.replace(hour=6, minute=0, second=0, microsecond=0) + timedelta(days=1)
            days.append([current_datetime, end_of_current_day])
            date_range_with_time = pd.date_range(start_of_the_next_day, end=to_date, freq='D')

            for day in date_range_with_time:
                # Generate time intervals from 06:00 to 23:59 for the current day
                days.append([day, day.replace(hour=23, minute=59, second=59)])
                
            return days

        # Convert 'From' and 'To' columns to datetime objects
        reservations_table = self.table.copy()
        reservations_table['From'] = pd.to_datetime(reservations_table['From'])
        reservations_table['To'] = pd.to_datetime(reservations_table['To'])

        # Parse time_start and time_end strings to datetime objects
        time_start = pd.to_datetime('2000-01-01 ' + '06:00:00')
        time_end = pd.to_datetime('2000-01-01 ' + '00:00:00')


        # Initialize list to store time gaps
        time_gaps = []
        time_step = 30 # min

        # Iterate through each day within the specified range
        for day in get_days(to_date):
            # Convert day to string format
            day_start = day[0]
            day_end = day[1]
            print(f'Day: {day_start} - {day_end}')

            day_str = day_start.strftime('%Y-%m-%d')

            # Filter reservations for the current day
            reservations_on_day = reservations_table[reservations_table['Day'] == day_str]
            print(f'Reservations at this day: {len(reservations_on_day)}')

            if len(reservations_on_day) == 0:
                return pd.date_range(day_start, end=day_end, freq=f'{time_step}m')
            else:
                # Sort reservations by start time
                reservations_on_day.sort_values(by='From', inplace=True)

                # Initialize gap start time to the beginning of the day
                gap_start_time = day_start

                # while gap_start_time < day_end:
                    

                # Iterate through reservations to find gaps
                for _, reservation in reservations_on_day.iterrows():
                    # If there is a gap between the previous reservation and the current one
                    if reservation['From'] > gap_start_time:
                        n_of_free_hours = reservation['From'] - gap_start_time
                        
                        # if int(n_of_free_hours.hours()) >= int(n_of_hours):
                        while int(n_of_free_hours.hours()) >= int(n_of_hours):
                            time_gaps.append(gap_start_time)
                            gap_start_time = gap_start_time + timedelta(minutes=time_step).replace(second=0, microsecond=0)
                        else:
                            gap_start_time = reservation['To']
                    # Update gap_start_time to the end of the current reservation


            return time_gaps





def find_time_gaps(self, n_of_hours: int):

        current_datetime = datetime.now()
        to_date = (current_datetime.replace(day=1) + timedelta(days=32)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        def get_days(to_date: datetime):
            days = []
            end_of_current_day = current_datetime.replace(hour=23, minute=59, second=59, microsecond=999999)
            start_of_the_next_day = current_datetime.replace(hour=6, minute=0, second=0, microsecond=0) + timedelta(days=1)
            days.append([current_datetime, end_of_current_day])
            date_range_with_time = pd.date_range(start_of_the_next_day, end=to_date, freq='D')

            for day in date_range_with_time:
                # Generate time intervals from 06:00 to 23:59 for the current day
                days.append([day, day.replace(hour=23, minute=59, second=59)])
                
            return days

        # Convert 'From' and 'To' columns to datetime objects
        reservations_table = self.table.copy()
        reservations_table['From'] = pd.to_datetime(reservations_table['From'])
        reservations_table['To'] = pd.to_datetime(reservations_table['To'])

        # Parse time_start and time_end strings to datetime objects
        time_start = pd.to_datetime('2000-01-01 ' + '06:00:00')
        time_end = pd.to_datetime('2000-01-01 ' + '00:00:00')


        # Initialize list to store time gaps
        time_gaps = []
        time_step = 30 # min

        # Iterate through each day within the specified range
        for day in get_days(to_date):
            # Convert day to string format
            day_start = day[0]
            day_end = day[1]
            print(f'Day: {day_start} - {day_end}')

            day_str = day_start.strftime('%Y-%m-%d')

            # Filter reservations for the current day
            reservations_on_day = reservations_table[reservations_table['Day'] == day_str]
            print(f'Reservations at this day: {len(reservations_on_day)}')

            if len(reservations_on_day) == 0:
                return pd.date_range(day_start, end=day_end, freq=f'{time_step}m')
            else:
                 return []
                # Sort reservations by start time
                # reservations_on_day.sort_values(by='From', inplace=True)

                # # Initialize gap start time to the beginning of the day
                # gap_start_time = day_start

                # # while gap_start_time < day_end:
                    

                # # Iterate through reservations to find gaps
                # for _, reservation in reservations_on_day.iterrows():
                #     # If there is a gap between the previous reservation and the current one
                #     if reservation['From'] > gap_start_time:
                #         n_of_free_hours = reservation['From'] - gap_start_time
                        
                #         # if int(n_of_free_hours.hours()) >= int(n_of_hours):
                #         while int(n_of_free_hours.hours()) >= int(n_of_hours):
                #             time_gaps.append(gap_start_time)
                #             gap_start_time = gap_start_time + timedelta(minutes=time_step).replace(second=0, microsecond=0)
                #         else:
                #             gap_start_time = reservation['To']
                #     # Update gap_start_time to the end of the current reservation
            # return time_gaps

def find_overlap(new_reservation, existing_reservation):
    r1 = pd.date_range(new_reservation[0], end=new_reservation[1])
    r2 = pd.date_range(existing_reservation[0], end=existing_reservation[1])
    # r2 = Range(start=datetime(2012, 3, 20), end=datetime(2012, 9, 15))
    
    latest_start = max(r1.start, r2.start)
    earliest_end = min(r1.end, r2.end)
    delta = (earliest_end - latest_start).minutes
    overlap = max(0, delta)
    return overlap