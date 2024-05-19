from datetime import datetime


class Reservation():
    orderid : str
    telegramId : str
    name : str
    type : str
    place : int
    period : int
    day : datetime
    time_from : datetime
    time_to : datetime
    available_places : list[int]

    def __init__(self, telegramId:str, name:str) -> None:
        self.telegramId = telegramId
        self.name = name


    
