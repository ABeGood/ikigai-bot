from telebot.handler_backends import State, StatesGroup
from telebot import TeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from telegram_bot_calendar import DetailedTelegramCalendar, WMonthTelegramCalendar, LSTEP
from util import utils
import pandas as pd
from datetime import datetime as dt, time, timedelta
from texts import *
from classes.classes import Reservation
from util.utils import format_reservation_recap, format_reservation_info, format_prepay
from telegram.constants import ParseMode
from db.connection import get_db
from db.repository import ReservationRepository
import json
import config
import math


# Initialize repository with database session
db = next(get_db())
reservation_repo = ReservationRepository(db)

class BotStates(StatesGroup):
    state_start = State()
    state_main_menu = State()

    # New Reservation
    state_reservation_menu_type = State()
    state_reservation_menu_hours = State()
    state_admin_chat = State()

    state_reservation_menu_date = State()
    state_reservation_menu_time = State()
    state_reservation_menu_place = State()
    state_reservation_menu_recap = State()
    state_prepay = State()

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
        InlineKeyboardButton(config.period_buttons.get('hour_1')[1], callback_data=str(config.period_buttons.get('hour_1')[0])),
        InlineKeyboardButton(config.period_buttons.get('hour_3')[1], callback_data=str(config.period_buttons.get('hour_3')[0])),
        InlineKeyboardButton(config.period_buttons.get('day_1')[1], callback_data=str(config.period_buttons.get('day_1')[0])),
        # InlineKeyboardButton(config.period_buttons.get('day_7')[1], callback_data=str(config.period_buttons.get('day_7')[0])),
        InlineKeyboardButton(config.period_buttons.get('other')[1], callback_data=str(config.period_buttons.get('other')[0])),
        InlineKeyboardButton(BACK_BUTTON, callback_data='cb_back'),
    )

    chatId = callback.message.chat.id
    messageId = callback.message.message_id
    bot.edit_message_text(chat_id=chatId, message_id=messageId, text=SELECT_TIME_MESSAGE, reply_markup=markup)

def format_calendar(calendar, new_reservation: Reservation):
    json_calendar = json.loads(calendar)
    calendar = InlineKeyboardMarkup(InlineKeyboardMarkup.de_json(json_calendar).keyboard)
    calendar.add(InlineKeyboardButton(BACK_BUTTON, callback_data='cb_back'),)

    # Filter the reservations_table by 'Type' first
    reservation_df = reservation_repo.to_dataframe()
    filtered_by_type = reservation_df[reservation_df['type'] == new_reservation.type]

    available_days = utils.find_available_days(new_reservation, reservation_table=filtered_by_type)

    # available_days = utils.find_reservation_gaps()


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

def show_date(bot:TeleBot, callback, new_reservation:Reservation):
    # global reservations_table
    # reservations_table_df = reservation_repo.
    calendar, step = WMonthTelegramCalendar().build()
    calendar = format_calendar(calendar, new_reservation)

    chatId = callback.message.chat.id
    messageId = callback.message.message_id
    bot.edit_message_text(chat_id=chatId, message_id=messageId, text=SELECT_DATE_MESSAGE, reply_markup=calendar)

def show_time(bot: TeleBot, callback, new_reservation: Reservation, going_back=False):
    if callback.data != 'cb_back':
        # Get last 3 elements and join them with '-'
        date = dt.strptime('-'.join(callback.data.split('_')[-3:]), '%Y-%m-%d').date()
    else:
        date = new_reservation.time_from.date()
    
    # Create time slot buttons
    buttons = []
    
    now = dt.now()
    
    # Calculate time_start_search only if date is today
    if date == now.date():
        # Add buffer minutes to current time
        buffer_time = now + timedelta(minutes=config.time_buffer_mins)
        # Calculate minutes since start of day
        minutes_since_midnight = buffer_time.hour * 60 + buffer_time.minute
        # Round up to next stride interval
        next_slot_minutes = math.ceil(minutes_since_midnight / config.stride_mins) * config.stride_mins
        # Convert back to datetime
        time_start_search = dt.combine(date, time(0, 0)) + timedelta(minutes=next_slot_minutes)
    else:
        # If not today, start from beginning of workday
        time_start_search = dt.combine(date, config.workday_start)

    # Calculate end of workday considering reservation period
    workday_end = dt.combine(date, config.workday_end) - timedelta(hours=new_reservation.period)
    
    # Generate time slots
    current_slot = time_start_search
    while current_slot <= workday_end:  # WTF?
        time_from = current_slot.time()
        time_to = (current_slot + timedelta(hours=new_reservation.period)).time()
        
        places = reservation_repo.get_available_places_for_timeslot(
            place_type=new_reservation.type,
            day=date,
            time_from=time_from,
            time_to=time_to
        )
        
        if places:
            time_str = current_slot.strftime("%H:%M")
            buttons.append(InlineKeyboardButton(
                text=time_str,
                callback_data=f'{time_str}_p{places}'
            ))
        
        # Move to next slot
        current_slot += timedelta(minutes=config.stride_mins)

    rows = [buttons[i:i + 4] for i in range(0, len(buttons), 4)]
    markup = InlineKeyboardMarkup(rows)
    markup.add(InlineKeyboardButton(BACK_BUTTON, callback_data='cb_back'))

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


def show_prepay(bot:TeleBot, callback, new_reservation: Reservation):
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    markup.add(
        InlineKeyboardButton(PAY_NOW_BUTTON, callback_data='pay_now', url=PAY_URL),
        InlineKeyboardButton(PAY_DONE_BUTTON, callback_data='pay_done'),
        InlineKeyboardButton(BACK_BUTTON, callback_data='cb_back'),
    )

    recap_string = format_prepay(555)

    chatId = callback.message.chat.id
    messageId = callback.message.message_id
    bot.delete_message(chat_id=chatId, message_id=messageId)

    # if len(recap_string) > 4095:
    #     for x in range(0, len(recap_string), 4095):
    #         # bot.reply_to(message, text=recap_string[x:x+4095])
    #         bot.send_message(callback.message.chat.id, text=recap_string[x:x+4095], reply_markup=markup, parse_mode=ParseMode.MARKDOWN)
    # else:
    #     # bot.reply_to(message, text=recap_string)
    #     bot.send_message(callback.message.chat.id, text=recap_string, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)

    bot.send_message(callback.message.chat.id, text=recap_string, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)
    


def show_info(bot:TeleBot, callback):
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    markup.add(InlineKeyboardButton(BACK_BUTTON, callback_data='cb_back'),)

    chatId = callback.message.chat.id
    messageId = callback.message.message_id
    bot.edit_message_text(chat_id=chatId, message_id=messageId, text=INFO_MESSAGE, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)

def show_my_reservations(bot: TeleBot, callback):
    # Get upcoming reservations using repository
    my_reservations = reservation_repo.get_upcoming_reservations_by_telegram_id(str(callback.from_user.id))
    
    markup = InlineKeyboardMarkup()
    markup.row_width = 1

    if my_reservations:
        reservation_message_text = MY_RESERVATIONS_MESSAGE
        for r in my_reservations:
            button_text = f'{r.day.strftime("%d.%m.%Y")}  c {r.time_from.strftime("%H:%M")} до {r.time_to.strftime("%H:%M")}'
            markup.add(InlineKeyboardButton(button_text, callback_data=r.order_id))
    else:
        reservation_message_text = MY_RESERVATIONS_MESSAGE_NO_RESERVATIONS

    markup.add(InlineKeyboardButton(BACK_BUTTON, callback_data='cb_back'))

    bot.edit_message_text(
        chat_id=callback.message.chat.id,
        message_id=callback.message.message_id,
        text=reservation_message_text,
        reply_markup=markup
    )

def show_my_reservation(bot:TeleBot, callback, reservations_table: pd.DataFrame):
    reservation_id = callback.data
    reservation = reservations_table.loc[reservations_table['order_id'] == reservation_id]

    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    if reservation['payed'].values[0] == 'False':
        markup.add(InlineKeyboardButton(PAY_NOW_BUTTON, callback_data='pay_now'),)

    markup.add(
        InlineKeyboardButton(CANCEL_RESERVATION_BUTTON, callback_data=f'delete_{reservation_id}'),
        InlineKeyboardButton(BACK_BUTTON, callback_data='cb_back'),
    )
    
    chatId = callback.message.chat.id
    messageId = callback.message.message_id

    if not reservation.empty:
        # DataFrame already contains localized times from repository
        reservation_info = format_reservation_info(
            reservation['day'].iloc[0],
            reservation['time_from'].iloc[0],
            reservation['time_to'].iloc[0],
            reservation['place'].values[0]
        )
        bot.edit_message_text(chat_id=chatId, message_id=messageId, text=reservation_info, reply_markup=markup)
    else:
        bot.edit_message_text(chat_id=chatId, message_id=messageId, text=RESERVATION_NOT_FOUND_MESSAGE)


def show_admin_chat(bot:TeleBot, callback):
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    markup.add(
        InlineKeyboardButton(BACK_BUTTON, callback_data='cb_back'),
    )

    chatId = callback.message.chat.id
    messageId = callback.message.message_id
    bot.edit_message_text(chat_id=chatId, message_id=messageId, text=ADMIN_CHAT_MESSAGE, reply_markup=markup)