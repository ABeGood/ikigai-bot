# https://github.com/AMRedichkina/EngBuddyBot/blob/main/bot/dialog.py
# https://github.com/python-telegram-bot/python-telegram-bot/blob/master/examples/conversationbot.py

# State filter: https://github.com/eternnoir/pyTelegramBotAPI/blob/master/examples/custom_states.py#L103

import logging
import os
from dotenv import load_dotenv
import pandas as pd
import telebot # telebot
import datetime as dt

from telebot import custom_filters
from states.states import BotStates
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup
from telegram_bot_calendar import DetailedTelegramCalendar, WMonthTelegramCalendar, LSTEP
from telegram.constants import ParseMode

import states.states as states

# States storage
from telebot.storage import StateMemoryStorage
from telebot.handler_backends import State, StatesGroup
from util import db, utils
from classes.classes import Reservation
import ast

from config import *
from keys import token
from texts import *

load_dotenv()


logging.basicConfig(
    level=logging.DEBUG, 
    filename='bot.log', 
    filemode='w', 
    format='%(asctime)s - %(levelname)s - %(message)s'
)


if __name__ == '__main__':
    state_storage = StateMemoryStorage() # you can init here another storage
    new_reservation : Reservation
    
    bot_token : str | None = os.environ.get('BOT_TOKEN')
    bot = telebot.TeleBot(token=token, state_storage=state_storage)

    @bot.message_handler(commands=['start'])
    def start(message):
        bot.set_state(user_id=message.from_user.id, state=BotStates.state_main_menu)
        states.show_main_menu(bot, message)
    

    @bot.callback_query_handler(func=lambda call: True, state=BotStates.state_main_menu)
    def callback_query(call):
        global new_reservation
        if call.data == "cb_new_reservation":
            new_reservation = Reservation(telegramId=call.from_user.id, name=call.from_user.full_name)
            bot.set_state(call.from_user.id, BotStates.state_reservation_menu_type)
            states.show_reservation_type(bot, call)
        elif call.data == 'cb_my_reservations':
            bot.set_state(call.from_user.id, BotStates.state_my_reservation_list)
            states.show_my_reservations(bot, call)
        elif call.data == "cb_info":
            bot.set_state(call.from_user.id, BotStates.state_info)
            states.show_info(bot, call)


    @bot.callback_query_handler(func=lambda call: True, state=BotStates.state_info)
    def callback_query(call):
        if call.data == 'cb_back':
            bot.set_state(call.from_user.id, BotStates.state_main_menu)
            states.show_main_menu(bot, call.message)

    
    @bot.callback_query_handler(func=lambda call: True, state=BotStates.state_my_reservation_list)
    def callback_query(call):
        if call.data == 'cb_back':
            bot.set_state(call.from_user.id, BotStates.state_main_menu)
            states.show_main_menu(bot, call.message)
        else:
            bot.set_state(call.from_user.id, BotStates.state_my_reservation)
            states.show_my_reservation(bot, call, reservations_table=states.reservations_table)


    @bot.callback_query_handler(func=lambda call: True, state=BotStates.state_my_reservation)
    def callback_query(call):
        if call.data == 'cb_back':
            bot.set_state(call.from_user.id, BotStates.state_my_reservation_list)
            states.show_my_reservations(bot, call)
        elif call.data.startswith('delete_'):
            order_id = '_'.join(call.data.split('_')[1:])
            states.reservations_table.delete_reservation(order_id)
            bot.set_state(call.from_user.id, BotStates.state_my_reservation_list)
            states.show_my_reservations(bot, call)

                
    @bot.callback_query_handler(func=lambda call: True, state=BotStates.state_reservation_menu_type)
    def callback_query(call):
        global new_reservation
        if call.data == 'cb_back':
            bot.set_state(call.from_user.id, BotStates.state_main_menu)
            states.show_main_menu(bot, call.message)
        else:
            spec = call.data[0]
            new_reservation.type = spec
            bot.set_state(call.from_user.id, BotStates.state_reservation_menu_hours)
            states.show_hours(bot, call)


    @bot.callback_query_handler(func=lambda call: True, state=BotStates.state_reservation_menu_hours)
    def callback_query(call):
        global new_reservation
        if call.data == 'cb_back':
            bot.set_state(call.from_user.id, BotStates.state_reservation_menu_type)
            states.show_reservation_type(bot, call)
        else:
            hours = int(call.data)
            new_reservation.period = hours
            bot.set_state(call.from_user.id, BotStates.state_reservation_menu_date)
            states.show_date(bot, call, new_reservation)


    @bot.callback_query_handler(func=DetailedTelegramCalendar.func(), state=BotStates.state_reservation_menu_date)
    def callback_query(call):
        global new_reservation
        result, key, step = DetailedTelegramCalendar().process(call.data)
        if not result and key:
            key = states.format_calendar(key, new_reservation=new_reservation)
            bot.edit_message_text(f"Select {LSTEP[step]}",
                                call.message.chat.id,
                                call.message.message_id,
                                reply_markup=key)
        elif result:
            bot.set_state(user_id=call.from_user.id, state=BotStates.state_reservation_menu_time)
            day = pd.to_datetime(result)
            new_reservation.day = day
            states.show_time(bot, call, new_reservation)


    @bot.callback_query_handler(func=lambda call: True, state=BotStates.state_reservation_menu_date)
    def callback_query(call):
        if call.data == 'cb_back':
            bot.set_state(call.from_user.id, BotStates.state_reservation_menu_hours)
            states.show_hours(bot, call)

        
    @bot.callback_query_handler(func=lambda call: True, state=BotStates.state_reservation_menu_time)
    def callback_query(call):
        global new_reservation
        if call.data == 'cb_back':
            new_reservation.day = ''  # TODO
            bot.set_state(call.from_user.id, BotStates.state_reservation_menu_date)
            states.show_date(bot, call, new_reservation)
        else:
            callback_data = call.data.split('_p')
            time = pd.to_datetime(callback_data[0])
            available_places = ast.literal_eval(callback_data[1])
            new_reservation.available_places = available_places
            new_reservation.time_from = dt.datetime.combine(new_reservation.day.date(), time.time())
            new_reservation.time_to = new_reservation.time_from + dt.timedelta(hours=new_reservation.period)

            bot.set_state(call.from_user.id, BotStates.state_reservation_menu_place)
            states.show_place(bot, call, new_reservation=new_reservation)


    @bot.callback_query_handler(func=lambda call: True, state=BotStates.state_reservation_menu_place)
    def callback_query(call):
        global new_reservation
        if call.data == 'cb_back':
            bot.set_state(call.from_user.id, BotStates.state_reservation_menu_time)
            states.show_time(bot, call, new_reservation, going_back=True)
        else:
            place = int(call.data.split('_')[1])
            new_reservation.place = place

            bot.set_state(call.from_user.id, BotStates.state_reservation_menu_recap)
            states.show_recap(bot, call, new_reservation=new_reservation)

    @bot.callback_query_handler(func=lambda call: True, state=BotStates.state_reservation_menu_recap)
    def callback_query(call):
        global new_reservation
        if call.data == 'cb_back':
            bot.set_state(call.from_user.id, BotStates.state_reservation_menu_place)
            states.show_place(bot, call, new_reservation)
        else:
            new_reservation.orderid = utils.generate_order_id(new_reservation)

            # AG: payment here
            save_result_ok = states.reservations_table.save_reservation_to_table(new_reservation=new_reservation)
            if save_result_ok:
                bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.id)
                bot.set_state(call.from_user.id, BotStates.state_start)
                bot.send_message(call.message.chat.id, utils.format_reservation_confirm(new_reservation), parse_mode=ParseMode.MARKDOWN)


    # @bot.callback_query_handler(func=lambda call: True, state=BotStates.state_reservation_done)
    # def callback_query(call): 
    #     bot.set_state(call.from_user.id, BotStates.state_start)
    #     states.show_start(bot, call)


    bot.add_custom_filter(custom_filters.StateFilter(bot))
    bot.infinity_polling(skip_pending=True)