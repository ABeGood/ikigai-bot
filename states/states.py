from telebot.handler_backends import State, StatesGroup
from telebot import TeleBot, types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from telegram_bot_calendar import DetailedTelegramCalendar, WMonthTelegramCalendar, LSTEP
from util import db, utils
import pandas as pd
from datetime import datetime as dt
from texts import *  # Import all texts for the screens
from classes.classes import Reservation
from util.utils import format_reservation_recap, format_reservation_info
from telegram.constants import ParseMode

import json
import config

reservations_table = db.ReservationTable()

class BotStates(StatesGroup):
    state_start = State()
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

def show_main_menu(bot:TeleBot, message):
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(
        InlineKeyboardButton(NEW_RESERVATION_BUTTON, callback_data='cb_new_reservation'),
        InlineKeyboardButton(MY_RESERVATIONS_BUTTON, callback_data='cb_my_reservations'),
        InlineKeyboardButton(ABOUT_US_BUTTON, callback_data='cb_info')
    )
    bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    bot.send_message(message.chat.id, WELCOME_MESSAGE, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)

def show_reservation_type(bot:TeleBot, callback):
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(
        InlineKeyboardButton(HAIRSTYLE_BUTTON, callback_data='hairstyle'),
        InlineKeyboardButton(BROWS_BUTTON, callback_data='brows'),
        InlineKeyboardButton(BACK_BUTTON, callback_data='cb_back'),
    )

    chatId = callback.message.chat.id
    messageId = callback.message.message_id
    bot.edit_message_text(chat_id=chatId, message_id=messageId, text=SELECT_WORKPLACE_MESSAGE, reply_markup=markup)

def show_hours(bot:TeleBot, callback):
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    markup.add(
        InlineKeyboardButton(ONE_HOUR_BUTTON, callback_data='1'),
        InlineKeyboardButton(TWO_HOURS_BUTTON, callback_data='2'),
        InlineKeyboardButton(THREE_HOURS_BUTTON, callback_data='3'),
        InlineKeyboardButton(SIX_HOURS_BUTTON, callback_data='6'),
        InlineKeyboardButton(OTHER_HOURS_BUTTON, callback_data='cb_hours_other'),
        InlineKeyboardButton(BACK_BUTTON, callback_data='cb_back'),
    )

    chatId = callback.message.chat.id
    messageId = callback.message.message_id
    bot.edit_message_text(chat_id=chatId, message_id=messageId, text=SELECT_TIME_MESSAGE, reply_markup=markup)

def format_calendar(calendar, new_reservation: Reservation):
    global reservations_table
    json_calendar = json.loads(calendar)
    calendar = InlineKeyboardMarkup(InlineKeyboardMarkup.de_json(json_calendar).keyboard)
    calendar.add(InlineKeyboardButton(BACK_BUTTON, callback_data='cb_back'),)

    # Filter the reservations_table by 'Type' first
    filtered_by_type = reservations_table.table[reservations_table.table['Type'] == new_reservation.type]

    available_days = utils.find_available_days(new_reservation, reservation_table=filtered_by_type)

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

def show_date(bot:TeleBot, callback, new_reservation):
    global reservations_table
    reservations_table.read_table_to_df()
    calendar, step = WMonthTelegramCalendar().build()
    calendar = format_calendar(calendar, new_reservation)

    chatId = callback.message.chat.id
    messageId = callback.message.message_id
    bot.edit_message_text(chat_id=chatId, message_id=messageId, text=SELECT_DATE_MESSAGE, reply_markup=calendar)

def show_time(bot:TeleBot, callback, new_reservation: Reservation, going_back=False):
    global timeslots

    if callback.data != 'cb_back':  # Fix this if
        date = callback.data
        parts = callback.data.split('_')
        date_str = '_'.join(parts[-3:])
        date_str = date_str.replace('_', '-')
        date = dt.strptime(date_str, '%Y-%m-%d')
    elif callback.data == 'cb_back':
        date = new_reservation.time_from

    timeslots = utils.find_timeslots(new_reservation, reservations_table.table, date)

    buttons = []
    for timeslot, places in timeslots.items():
        buttons.append(InlineKeyboardButton(timeslot, callback_data=f'{timeslot}_p{places}'))

    rows = [buttons[i:i + 4] for i in range(0, len(buttons), 4)]
    # Create the markup
    markup = InlineKeyboardMarkup(rows)

    markup.add(InlineKeyboardButton(BACK_BUTTON, callback_data='cb_back'),)

    if going_back:
        chatId = callback.message.chat.id
        messageId = callback.message.message_id
        bot.delete_message(chat_id=chatId, message_id=messageId)
        bot.send_message(callback.message.chat.id, text=SELECT_TIME_SLOT_MESSAGE, reply_markup=markup)
    else:
        chatId = callback.message.chat.id
        messageId = callback.message.message_id
        bot.edit_message_text(chat_id=chatId, message_id=messageId, text=SELECT_TIME_SLOT_MESSAGE, reply_markup=markup)

def show_place(bot:TeleBot, callback, new_reservation: Reservation):
    markup = InlineKeyboardMarkup()
    markup.row_width = 4
    for place in new_reservation.available_places:
        markup.add(InlineKeyboardButton(f'Место {place}', callback_data=f'place_{place}'),)

    markup.add(InlineKeyboardButton(BACK_BUTTON, callback_data='cb_back'),)

    chatId = callback.message.chat.id
    messageId = callback.message.message_id
    bot.delete_message(chat_id=chatId, message_id=messageId)
    bot.send_photo(chat_id=chatId, caption=SELECT_SEAT_MESSAGE, photo=open('img/seats/places_all.jpg', 'rb'), reply_markup=markup)

def show_recap(bot:TeleBot, callback, new_reservation: Reservation):
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    markup.add(
        InlineKeyboardButton(PAY_NOW_BUTTON, callback_data='pay_now'),
        InlineKeyboardButton(PAY_LATER_BUTTON, callback_data='pay_later'),
        InlineKeyboardButton(BACK_BUTTON, callback_data='cb_back'),
    )
    
    img_path = f'img/seats/places_{new_reservation.place}.jpg'

    recap_string = format_reservation_recap(new_reservation)

    chatId = callback.message.chat.id
    messageId = callback.message.message_id
    bot.delete_message(chat_id=chatId, message_id=messageId)
    bot.send_photo(callback.message.chat.id, caption=recap_string, photo=open(img_path, 'rb'), reply_markup=markup, parse_mode=ParseMode.MARKDOWN)

def show_info(bot:TeleBot, callback):
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    markup.add(InlineKeyboardButton(BACK_BUTTON, callback_data='cb_back'),)

    chatId = callback.message.chat.id
    messageId = callback.message.message_id
    bot.edit_message_text(chat_id=chatId, message_id=messageId, text=INFO_MESSAGE, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)

def show_my_reservations(bot, callback):
    reservations_table.read_table_to_df()
    reservations_df = reservations_table.table
    current_time = dt.now().strftime('%H:%M')
    my_reservations_df = reservations_df[(reservations_df['TelegramId'] == str(callback.from_user.id)) & (reservations_df['From'] > current_time)]
    markup = InlineKeyboardMarkup()
    markup.row_width = 1

    for index, r in my_reservations_df.iterrows():
        markup.add(InlineKeyboardButton(f'{r["Day"].strftime("%Y-%m-%d").replace("-", ".")}  {r["From"].strftime("%H:%M")} - {r["To"].strftime("%H:%M")}', callback_data=r["OrderId"]),)

    markup.add(InlineKeyboardButton(BACK_BUTTON, callback_data='cb_back'),)

    chatId = callback.message.chat.id
    messageId = callback.message.message_id
    bot.edit_message_text(chat_id=chatId, message_id=messageId, text=MY_RESERVATIONS_MESSAGE, reply_markup=markup)

def show_my_reservation(bot:TeleBot, callback, reservations_table: db.ReservationTable):
    reservation_id = callback.data
    reservation = reservations_table.table.loc[reservations_table.table['OrderId'] == reservation_id]

    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    if reservation['Payed'].values[0] == 'False':
        markup.add(InlineKeyboardButton(PAY_NOW_BUTTON, callback_data='pay_now'),)

    markup.add(
        InlineKeyboardButton(CANCEL_RESERVATION_BUTTON, callback_data=f'delete_{reservation_id}'),
        InlineKeyboardButton(BACK_BUTTON, callback_data='cb_back'),
    )
    
    chatId = callback.message.chat.id
    messageId = callback.message.message_id

    if not reservation.empty:
        reservation_info = format_reservation_info(
            reservation['Day'].astype('datetime64[ns]').values[0].astype('datetime64[D]').tolist(),
            reservation['From'].astype('datetime64[ns]').values[0].astype('datetime64[m]').tolist(),
            reservation['To'].astype('datetime64[ns]').values[0].astype('datetime64[m]').tolist(),
            reservation['Place'].values[0]
        )
        bot.edit_message_text(chat_id=chatId, message_id=messageId, text=reservation_info, reply_markup=markup)
    else:
        bot.edit_message_text(chat_id=chatId, message_id=messageId, text=RESERVATION_NOT_FOUND_MESSAGE)