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
    payment_confiramtion_link : str
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
        self.payment_confiramtion_link = None

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
            'payment_confiramtion_link': self.payment_confiramtion_link,
        }


    
