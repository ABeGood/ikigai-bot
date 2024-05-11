from telebot.handler_backends import State, StatesGroup

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from telegram_bot_calendar import DetailedTelegramCalendar, WMonthTelegramCalendar, LSTEP
from util import db
import pandas as pd
from datetime import datetime as dt

# from classes.classes import MyCalendar

import json

reservations_table = db.ReservationTable()


class BotStates(StatesGroup):
        state_start = State()
        state_main_menu = State()
        state_reservation_menu_type = State()
        state_reservation_menu_hours = State()
        state_reservation_menu_date = State()
        state_reservation_menu_time = State()
        state_reservation_done = State()
        state_info = State()


def show_main_menu(bot, message):
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(InlineKeyboardButton('🆕 Новая резервация', callback_data='cb_new_reservation'),
               InlineKeyboardButton('🆕 Мои резервации', callback_data='cb_my_reservations'),
               InlineKeyboardButton('⏺️ О нас', callback_data='cb_info')
               )

    bot.send_message(message.chat.id, 'Welcome to Ikigai bot! 🎉', reply_markup=markup)



def show_reservation_type(bot, callback):
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(InlineKeyboardButton('Hairstyle', callback_data='hairstyle'),
                            InlineKeyboardButton('Brows', callback_data='brows'),
                            InlineKeyboardButton('🔙 Назад', callback_data='cb_back'),)

    bot.send_message(callback.message.chat.id, 'Какое рабочее место Вам нужно?', reply_markup=markup)


def show_hours(bot, callback):
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    markup.add  (   
                    InlineKeyboardButton('🕐 1 час', callback_data='1'),
                    InlineKeyboardButton('🕐 2 часа', callback_data='2'),
                    InlineKeyboardButton('🕐 3 часа', callback_data='3'),
                    InlineKeyboardButton('🕐 6 часов (полдня)', callback_data='6'),
                    InlineKeyboardButton('Other...', callback_data='cb_hours_other'),
                    InlineKeyboardButton('🔙 Назад', callback_data='cb_back'),
                )

    bot.send_message(callback.message.chat.id, 'How much time do you need?', reply_markup=markup)


def show_date(bot, callback, new_reservation):
    calendar, step = WMonthTelegramCalendar().build()
    # json_calendar = json.loads(calendar)['inline_keyboard']
    json_calendar = json.loads(calendar)
    calendar = InlineKeyboardMarkup(InlineKeyboardMarkup.de_json(json_calendar).keyboard)
    # markup = InlineKeyboardMarkup(json_calendar['inline_keyboard'])
    calendar.add(InlineKeyboardButton('🔙 Назад', callback_data='cb_back'),)
    # available_days = reservations_table.find_available_timeslots(new_reservation)
    available_days = reservations_table.find_time_gaps(n_of_hours=new_reservation.period)

    available_days_starts = []

    for available_day in available_days:
        available_days_starts.append(available_day[0].date())

    for week in calendar.keyboard:
        for day in week:
            parts = day.callback_data.split('_')

            # Extract the date part (last 3 elements)
            date_str = '_'.join(parts[-3:])

            # Define the date format
            date_format = '%Y_%m_%d'

            # Parse the date string to a datetime object
            try:
                day_datetime = dt.strptime(date_str, date_format)
                day_datetime = pd.to_datetime(day_datetime, format=date_format)

                if day_datetime.date() not in available_days_starts:
                    day.text = '✖️'
                    day.callback_data = 'cb_no_timeslots'
            except:
                continue

    bot.send_message(callback.message.chat.id, 'Выберете подходящий для вас день:', reply_markup=calendar)


def show_time(bot, callback):
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add( InlineKeyboardButton('10:00', callback_data='10:00'),
                InlineKeyboardButton('10:30', callback_data='10:30'),
                InlineKeyboardButton('14:30', callback_data='14:30'))

    bot.send_message(callback.message.chat.id, 'Выбетере подходящее для вас время', reply_markup=markup)


def show_reservation_done(bot, callback):
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    bot.send_message(callback.message.chat.id, '🎉 Ваша резервация подтверждена! \nДо встречи.')
