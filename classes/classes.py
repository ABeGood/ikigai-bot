from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import pandas as pd
from util import db


class Reservation():
    orderid = None
    telegramId = None
    name = None
    type = None
    period = None
    day = None
    time_from = None
    time_to = None

    def __init__(self, orderId, telegramId, name) -> None:
        self.orderid = orderId
        self.telegramId = telegramId
        self.name = name

    
