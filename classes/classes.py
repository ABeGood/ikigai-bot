from datetime import datetime


class Reservation():
    order_id : str
    telegram_id : str
    name : str
    type : str
    place : int
    period : float
    day : datetime
    time_from : datetime
    time_to : datetime
    sum : float
    payed : bool
    payment_confirmation_link : str | None
    payment_confirmation_file_id : str
    available_places : list[int]

    def __init__(self, telegramId:str, name:str) -> None:
        self.order_id = None
        self.telegram_id = telegramId
        self.name = name
        self.type = None
        self.place = None
        self.period = None
        self.day = None
        self.time_from = None
        self.time_to = None
        self.sum = None
        self.payed = None
        self.payment_confirmation_link = None
        self.payment_confirmation_file_id = None

    def to_dict(self) -> dict:
        return {
            'order_id': self.order_id,
            'telegram_id': self.telegram_id,
            'name': self.name,
            'type': self.type,
            'place': self.place,
            'period': self.period,
            'day': self.day.date() if self.day else None,
            'time_from': self.time_from,
            'time_to': self.time_to,
            'sum': self.sum,
            'payed': self.payed,
            'payment_confirmation_link': self.payment_confirmation_link,
            'payment_confirmation_file_id' : self.payment_confirmation_file_id
        }
    
    @classmethod
    def from_dataframe_row(cls, row):
        # Create instance with required parameters
        reservation = cls(telegramId=row['telegram_id'], name=row['name'])
        
        # Set all other attributes from the row
        reservation.order_id = row['order_id']
        reservation.type = row['type']
        reservation.place = row['place']
        reservation.period = row['period']
        reservation.day = row['day']
        reservation.time_from = row['time_from']
        reservation.time_to = row['time_to']
        reservation.sum = row['sum']
        reservation.payed = row['payed']
        reservation.payment_confirmation_link = row['payment_confirmation_link']
        reservation.payment_confirmation_file_id = row['payment_confirmation_file_id']
        
        return reservation
