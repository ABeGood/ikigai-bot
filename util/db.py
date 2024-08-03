import pandas as pd
import google_sheets_api as gs
from datetime import datetime
from classes.classes import Reservation
from upload import createEvent, uploadEvent

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
                'Payed': [False]
            }
        )

        self.table = pd.concat([self.table, new_reservation_df])
        self.table.dropna(inplace=True)  # Remove empty rows

        # Here add to calendar; !!! Move from here
        calendar_event = createEvent(start=new_reservation.time_from, 
                                     end=new_reservation.time_to, 
                                     subject=new_reservation.name, 
                                     place=new_reservation.place, 
                                     colour='green')
        
        uploadEvent(calendar_event)

        try:
            gs.save_df_to_table(self.table)
            return True
        except Exception as e:
            print(e.with_traceback)
            return False
        
    def delete_reservation(self, reservation_id: str):
        self.table = self.table[self.table['OrderId'] != reservation_id]
        self.table.dropna(inplace=True)  # Remove empty rows
        try:
            gs.save_df_to_table(self.table)
            return True
        except Exception as e:
            print(e.with_traceback)
            return False
        

