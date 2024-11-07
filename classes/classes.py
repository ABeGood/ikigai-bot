from datetime import datetime


class Reservation():
    order_id : str
    telegram_id : str
    name : str
    type : str
    place : int
    period : int
    day : datetime
    time_from : datetime
    time_to : datetime
    payed : str
    available_places : list[int]

    def __init__(self, telegramId:str, name:str) -> None:
        self.telegram_id = telegramId
        self.name = name
        self.order_id = None

    def to_dict(self) -> dict:
        return {
            'order_id': self.order_id,
            'telegram_id': self.telegram_id,
            'name': self.name,
            'type': self.type,
            'place': self.place,
            'period': self.period,
            'day': self.day.date() if self.day else None,
            'time_from': self.time_from.time() if self.time_from else None,
            'time_to': self.time_to.time() if self.time_to else None,
            'payed': self.payed
        }


    
