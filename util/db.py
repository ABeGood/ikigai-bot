import pandas as pd
import google_sheets_api as gs
from datetime import datetime
from classes.classes import Reservation
from util.calendar import createEvent, uploadEvent, get_service, clear_calendar, sync_calendar_with_reservations
import threading

CALENDAR_ID = '54ef8d9bf21e3ca24bfdb00d77684478afca8c301b3c23543eed688205002d5f@group.calendar.google.com'

class ReservationTable:

    table : pd.DataFrame

    def __init__(self):
        self.read_table_to_df()

    def read_table_to_df(self):
        updated_table = gs.read_table_to_df()

        if updated_table.empty:
            updated_table = pd.DataFrame(columns=['CreationTime', 'OrderId', 'TelegramId', 'Name', 'Type', 'Place', 'Day', 'From', 'To', 'Period', 'Payed'])

        updated_table['CreationTime'] = pd.to_datetime(updated_table['CreationTime'])
        updated_table['From'] = pd.to_datetime(updated_table['From'])
        updated_table['To'] = pd.to_datetime(updated_table['To'])
        updated_table['Day'] = pd.to_datetime(updated_table['Day'])

        self.table = updated_table


    def sync_calendar(self):
        service = get_service()
        clear_calendar(service, CALENDAR_ID)
        sync_calendar_with_reservations(service, CALENDAR_ID, self.table.to_dict('records'))


    def save_reservation_to_table(self, new_reservation: Reservation):
        new_reservation_df = pd.DataFrame(
            {
                'CreationTime': [datetime.now()],
                'OrderId': [new_reservation.orderid],
                'TelegramId': [new_reservation.telegramId],
                'Name': [new_reservation.name],
                'Type': [new_reservation.type],
                'Place': [new_reservation.place],
                'Day': [new_reservation.day],
                'From': [new_reservation.time_from],
                'To': [new_reservation.time_to],
                'Period': [new_reservation.period],
                'Payed': [new_reservation.payed],
            }
        )

        self.table = pd.concat([self.table, new_reservation_df])
        self.table.dropna(inplace=True)  # Remove empty rows

        try:
            gs.save_df_to_table(self.table)
            threading.Thread(target=self.sync_calendar, daemon=True).start()
            return True
        except Exception as e:
            print(e.with_traceback)
            return False
        
        
    def delete_reservation(self, reservation_id: str):
        deleted_reservation = self.table[self.table['OrderId'] == reservation_id]
        self.table = self.table[self.table['OrderId'] != reservation_id]
        self.table.dropna(inplace=True)  # Remove empty rows

        try:
            gs.save_df_to_table(self.table)
            threading.Thread(target=self.sync_calendar, daemon=True).start()
            return deleted_reservation
        except Exception as e:
            print(e.with_traceback)
            return None
        
    
    def force_sync_calendar(self):
        self.read_table_to_df()  # Refresh the table data
        self.sync_calendar()  # Sync the calendar with the latest data
        

