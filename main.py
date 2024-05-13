# https://github.com/AMRedichkina/EngBuddyBot/blob/main/bot/dialog.py
# https://github.com/python-telegram-bot/python-telegram-bot/blob/master/examples/conversationbot.py

# State filter: https://github.com/eternnoir/pyTelegramBotAPI/blob/master/examples/custom_states.py#L103

import logging
import config
import pandas as pd
import telebot # telebot
import datetime as dt

from telebot import custom_filters
from states.states import BotStates
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup
from telegram_bot_calendar import DetailedTelegramCalendar, WMonthTelegramCalendar, LSTEP

import states.states as states

# States storage
from telebot.storage import StateMemoryStorage
from telebot.handler_backends import State, StatesGroup
from util import db
from classes.classes import Reservation


logging.basicConfig(
    level=logging.DEBUG, 
    filename='bot.log', 
    filemode='w', 
    format='%(asctime)s - %(levelname)s - %(message)s'
)


if __name__ == '__main__':
    state_storage = StateMemoryStorage() # you can init here another storage
    new_reservation = None
    

    bot = telebot.TeleBot(config.token,
        state_storage=state_storage)

    @bot.message_handler(commands=['start'])
    def start(message):
        bot.set_state(user_id=message.from_user.id, state=BotStates.state_main_menu)
        states.show_main_menu(bot, message)
            

    @bot.callback_query_handler(func=lambda call: True, state=BotStates.state_main_menu)
    def callback_query(call):
        global new_reservation

        if call.data == "cb_new_reservation":
            states.reservations_table = states.reservations_table.read_table_to_df()
            # TODO: dropna()
            new_reservation = Reservation(orderId=None, telegramId=call.from_user.id, name=call.from_user.full_name)
            bot.set_state(call.from_user.id, BotStates.state_reservation_menu_type)
            states.show_reservation_type(bot, call)
        elif call.data == 'cb_start_my_reservations':
            # my reservations
            pass
        elif call.data == "cb_info":
            bot.set_state(call.from_user.id, BotStates.info)

                
    @bot.callback_query_handler(func=lambda call: True, state=BotStates.state_reservation_menu_type)
    def callback_query(call):
        if call.data == 'cb_back':
            bot.set_state(call.from_user.id, BotStates.state_main_menu)
            states.show_main_menu(bot, call.message)
        else:
            spec = call.data
            new_reservation.type = spec
            bot.set_state(call.from_user.id, BotStates.state_reservation_menu_hours)
            states.show_hours(bot, call)


    @bot.callback_query_handler(func=lambda call: True, state=BotStates.state_reservation_menu_hours)
    def callback_query(call):
        if call.data == 'cb_back':
            bot.set_state(call.from_user.id, BotStates.state_reservation_menu_type)
            states.show_reservation_type(bot, call)
        else:
            hours = call.data
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
        if call.data == 'cb_back':
            bot.set_state(call.from_user.id, BotStates.state_reservation_menu_date)
            states.show_date(bot, call, new_reservation)
        else:
            time = call.data
            new_reservation.time_from = pd.to_datetime(time)
            save_result_ok = states.reservations_table.save_reservation_to_table(new_reservation=new_reservation)
            if save_result_ok:
                bot.set_state(call.from_user.id, BotStates.state_reservation_done)
                states.show_reservation_done(bot, call)


    @bot.callback_query_handler(func=lambda call: True, state=BotStates.state_reservation_done)
    def callback_query(call):
        bot.set_state(call.from_user.id, BotStates.state_start)
        states.show_start(bot, call)


    bot.add_custom_filter(custom_filters.StateFilter(bot))
    bot.infinity_polling(skip_pending=True)