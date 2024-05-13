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


def format_calendar(calendar, new_reservation):
    # json_calendar = json.loads(calendar)['inline_keyboard']
    json_calendar = json.loads(calendar)
    calendar = InlineKeyboardMarkup(InlineKeyboardMarkup.de_json(json_calendar).keyboard)
    # markup = InlineKeyboardMarkup(json_calendar['inline_keyboard'])
    calendar.add(InlineKeyboardButton('🔙 Назад', callback_data='cb_back'),)
    # available_days = reservations_table.find_available_timeslots(new_reservation)
    available_days = reservations_table.find_time_gaps(n_of_hours=new_reservation.period)

    date_format = '%Y_%m_%d'
    available_dates = list(available_days.keys())

    for week in calendar.keyboard:
        for day in week:
            if day.callback_data.startswith('cbcal_0_s_d_'):
                parts = day.callback_data.split('_')
                date_str = '_'.join(parts[-3:])
           
                day_date = dt.strptime(date_str, date_format).date().strftime(format = '%Y-%m-%d')
                if day_date not in available_dates:
                    day.text = '✖️'
                    day.callback_data = 'cb_no_timeslots'
                # else:
                #     day.callback_data = json.dumps([timeslot.strftime('%H-%M') for timeslot in available_days[day_date]])

    return calendar

def show_date(bot, callback, new_reservation):
    calendar, step = WMonthTelegramCalendar().build()
    calendar = format_calendar(calendar, new_reservation)
    bot.send_message(callback.message.chat.id, 'Выберете подходящий для вас день:', reply_markup=calendar)


def show_time(bot, callback, new_reservation):
    markup = InlineKeyboardMarkup()
    date = callback.data

    parts = callback.data.split('_')
    date_str = '_'.join(parts[-3:])
    date_str = date_str.replace('_', '-')
    date = dt.strptime(date_str, '%Y-%m-%d')
    date_str = dt.strftime(date, format='%Y-%m-%d')
    
    # date = date.strftime('%Y-%m-%d')
    timeslots = reservations_table.find_time_gaps(n_of_hours=new_reservation.period)[date_str]

    for timeslot in timeslots:
        markup.add(InlineKeyboardButton(dt.strftime(timeslot, '%H:%M'), callback_data=dt.strftime(timeslot, '%H:%M')))

    markup.add(InlineKeyboardButton('🔙 Назад', callback_data='cb_back'),)
    bot.send_message(callback.message.chat.id, 'Выбетере подходящее для вас время', reply_markup=markup)


def show_reservation_done(bot, callback):
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    bot.send_message(callback.message.chat.id, '🎉 Ваша резервация подтверждена! \nДо встречи.')
