from telebot.handler_backends import State, StatesGroup

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from telegram_bot_calendar import DetailedTelegramCalendar, WMonthTelegramCalendar, LSTEP
from util import db, utils
import pandas as pd
from datetime import datetime as dt
from config import places
from classes.classes import Reservation

# from classes.classes import MyCalendar

import json

reservations_table = db.ReservationTable()

class BotStates(StatesGroup):
        state_start = State()  # Do I need this?

        state_main_menu = State()

        # New Reservation
        state_reservation_menu_type = State()
        state_reservation_menu_hours = State()
        state_reservation_menu_date = State()
        state_reservation_menu_time = State()
        state_reservation_menu_place = State()
        state_reservation_menu_recap = State()

        # My Reservations
        state_my_reservation_list = State()
        state_my_reservation = State()

        state_info = State()


def show_main_menu(bot, message):
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add  (
                    InlineKeyboardButton('🆕 Новая резервация', callback_data='cb_new_reservation'),
                    InlineKeyboardButton('🆕 Мои резервации', callback_data='cb_my_reservations'),
                    InlineKeyboardButton('⏺️ О нас', callback_data='cb_info')
                )

    bot.send_message(message.chat.id, 'Welcome to Ikigai bot! 🎉', reply_markup=markup)



def show_reservation_type(bot, callback):
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add  ( 
                    InlineKeyboardButton('Hairstyle', callback_data='hairstyle'),
                    InlineKeyboardButton('Brows', callback_data='brows'),
                    InlineKeyboardButton('🔙 Назад', callback_data='cb_back'),
                )

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


def format_calendar(calendar, new_reservation: Reservation):
    global reservations_table
    json_calendar = json.loads(calendar)
    calendar = InlineKeyboardMarkup(InlineKeyboardMarkup.de_json(json_calendar).keyboard)
    calendar.add(InlineKeyboardButton('🔙 Назад', callback_data='cb_back'),)

    reservations_filtered_by_places = reservations_table.table[reservations_table.table['Type'].isin(places[new_reservation.type])]

    available_days = utils.find_available_days(new_reservation, reservation_table=reservations_filtered_by_places)

    date_format = '%Y_%m_%d'

    for week in calendar.keyboard:
        for day in week:
            if day.callback_data.startswith('cbcal_0_s_d_'):
                parts = day.callback_data.split('_')
                date_str = '_'.join(parts[-3:])
                date_str = dt.strptime(date_str, date_format).date().strftime(date_format)
                
                if date_str not in [date_obj.strftime(date_format) for date_obj in available_days]:
                    day.text = '✖️'
                    day.callback_data = 'cb_no_timeslots'
                

    return calendar

def show_date(bot, callback, new_reservation):
    global reservations_table
    reservations_table.read_table_to_df()
    calendar, step = WMonthTelegramCalendar().build()
    calendar = format_calendar(calendar, new_reservation)
    bot.send_message(callback.message.chat.id, 'Выберете подходящий для вас день:', reply_markup=calendar)


def show_time(bot, callback, new_reservation: Reservation):
    global timeslots
    markup = InlineKeyboardMarkup()

    if callback.data != 'cb_back':
        date = callback.data
        parts = callback.data.split('_')
        date_str = '_'.join(parts[-3:])
        date_str = date_str.replace('_', '-')
        date = dt.strptime(date_str, '%Y-%m-%d')
        date_str = date.strftime('%Y-%m-%d')
    elif callback.data == 'cb_back':
        date = new_reservation.time_from
        date_str = date.strftime('%Y-%m-%d')

    timeslots = utils.find_timeslots(new_reservation, reservations_table.table, date)

    for timeslot, places in timeslots.items():
        markup.add(InlineKeyboardButton(timeslot, callback_data=f'{timeslot}_p{places}'))

    markup.add(InlineKeyboardButton('🔙 Назад', callback_data='cb_back'),)
    bot.send_message(callback.message.chat.id, 'Выбетере подходящее для вас время', reply_markup=markup)


def show_place(bot, callback, new_reservation: Reservation):
    markup = InlineKeyboardMarkup()
    markup.row_width = 4
    for place in new_reservation.available_places:
        markup.add(InlineKeyboardButton(f'Место {place}', callback_data=f'place_{place}'),)

    markup.add(InlineKeyboardButton('🔙 Назад', callback_data='cb_back'),)

    bot.send_photo(callback.message.chat.id, caption='Выберете рабочее место.', photo=open('img/seats/empty.png', 'rb'), reply_markup=markup)


def show_recap(bot, callback, new_reservation: Reservation):
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    markup.add  (   
                    InlineKeyboardButton('Оплатить 🪙', callback_data='pay_now'),
                    InlineKeyboardButton('Оплатить позже ⌛', callback_data='pay_later'),
                    InlineKeyboardButton('🔙 Назад', callback_data='cb_back'),
                )
    
    img_path = f'img/seats/place-{new_reservation.place}.png'

    recap_string = f"""
    Ваша резервация:
    {new_reservation.day.strftime('%d.%m.%Y')}
    {new_reservation.time_from.strftime('%H:%M')} - {new_reservation.time_to.strftime('%H:%M')} ({new_reservation.period} часа)
    И так далее ..."""

    bot.send_photo(callback.message.chat.id, caption=recap_string, photo=open(img_path, 'rb'), reply_markup=markup)


def show_info(bot, callback):
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    markup.add(InlineKeyboardButton('🔙 Назад', callback_data='cb_back'),)
    bot.send_message(callback.message.chat.id, 'Информация о нас.\nКонтакты.\nСсылки.', reply_markup=markup)


def show_my_reservations(bot, callback):
    reservations_table.read_table_to_df()
    reservations_df = reservations_table.table
    my_reservations_df = reservations_df[reservations_df['TelegramId'] == str(callback.from_user.id)]
    # TODO: if payed, mark somehow
    markup = InlineKeyboardMarkup()
    markup.row_width = 1

    for index, r in my_reservations_df.iterrows():
        markup.add(InlineKeyboardButton(f'{r["Day"].strftime("%Y-%m-%d").replace("-", ".")}  {r["From"].strftime("%H:%M")} - {r["To"].strftime("%H:%M")}', callback_data=r["OrderId"]),)

    markup.add(InlineKeyboardButton('🔙 Назад', callback_data='cb_back'),)

    bot.send_message(callback.message.chat.id, 'Ваши резервации:', reply_markup=markup)
