# https://github.com/AMRedichkina/EngBuddyBot/blob/main/bot/dialog.py
# https://github.com/python-telegram-bot/python-telegram-bot/blob/master/examples/conversationbot.py

# State filter: https://github.com/eternnoir/pyTelegramBotAPI/blob/master/examples/custom_states.py#L103

import logging
import os
from dotenv import load_dotenv
import pandas as pd
import telebot # telebot
import datetime as dt
import asyncio
import time

from telebot import custom_filters
from states.states import BotStates
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup
from telegram_bot_calendar import DetailedTelegramCalendar, WMonthTelegramCalendar, LSTEP
from telegram.constants import ParseMode

import states.states as states

# States storage
from telebot.storage import StateMemoryStorage
from telebot.handler_backends import State, StatesGroup
from telebot.types import ReactionTypeEmoji
from util import utils
from classes.classes import Reservation
import ast

from config import *
# from keys import token
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
    
    bot_token : str = os.environ.get('BOT_TOKEN')
    bot = telebot.TeleBot(token=bot_token, state_storage=state_storage)

    def notify_admin(text:str):
        notification_text = f"""
    {text}        

    """
        bot.send_message(chat_id=admin_chat_id, text=notification_text, parse_mode=ParseMode.MARKDOWN)

    @bot.message_handler(commands=['start'])
    def start(message):
        chat_id = message.chat.id
        bot.set_state(user_id=message.from_user.id, state=BotStates.state_main_menu)
        states.show_main_menu(bot, message)
    

    @bot.callback_query_handler(func=lambda call: True, state=BotStates.state_main_menu)
    def callback_query(call):
        global new_reservation
        if call.data == "cb_new_reservation":
            new_reservation = Reservation(telegramId=call.from_user.id, name=call.from_user.full_name)  # TODO: full_name
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
            reservation_table = states.reservation_repo.to_dataframe()
            states.show_my_reservation(bot, call, reservations_table=reservation_table)


    @bot.callback_query_handler(func=lambda call: True, state=BotStates.state_my_reservation)
    def callback_query(call):
        if call.data == 'cb_back':
            bot.set_state(call.from_user.id, BotStates.state_my_reservation_list)
            states.show_my_reservations(bot, call)
        elif call.data.startswith('delete_'):
            order_id = '_'.join(call.data.split('_')[1:])
            deleted_reservation = states.reservations_table.delete_reservation(order_id)
            bot.set_state(call.from_user.id, BotStates.state_my_reservation_list)
            states.show_my_reservations(bot, call)

            notify_admin(f"✴️ Reservation was deleted:\n{deleted_reservation.iloc[0]['From']}\n {deleted_reservation.iloc[0]['OrderId']} \n{deleted_reservation.iloc[0]['CreationTime']}")

                
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
        elif call.data == 'talk_to_admin':
            # bot.send_message(call.message.chat.id, 'Please contact the administrator for this request.')
            bot.set_state(call.from_user.id, BotStates.state_admin_chat)
            states.show_admin_chat(bot, call)
        else:
            hours = int(call.data)
            new_reservation.period = hours
            bot.set_state(call.from_user.id, BotStates.state_reservation_menu_date)
            states.show_date(bot, call, new_reservation)


    @bot.callback_query_handler(func=lambda call: True, state=BotStates.state_admin_chat)
    def callback_query(call):
        if call.data == 'cb_back':
            bot.set_state(call.from_user.id, BotStates.state_main_menu)
            states.show_main_menu(bot, call.message)
        
        # Catch and resend message here:
        

    # async def handle_message(update: Update, context: CallbackContext):
    #     user_status = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
    #     status_message = f"User status {update.effective_user.mention_html()} in this chat: {user_status.status}"
    #     await context.bot.send_message(chat_id=update.effective_chat.id,
    #                                 text=status_message,
    #                                 parse_mode='HTML')


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
            if new_reservation.period <= 12:
                bot.set_state(user_id=call.from_user.id, state=BotStates.state_reservation_menu_time)
                day = pd.to_datetime(result)
                new_reservation.day = day
                states.show_time(bot, call, new_reservation)
            elif new_reservation.period % 12 == 0:
                bot.set_state(user_id=call.from_user.id, state=BotStates.state_reservation_menu_place)
                day = pd.to_datetime(result)
                new_reservation.day = day

                timeslots = utils.find_timeslots_for_days(new_reservation, states.reservations_table.table, new_reservation.day)

                available_places = []

                buttons = []
                for timeslot, places in timeslots.items():
                    buttons.append(InlineKeyboardButton(timeslot, callback_data=f'{timeslot}_p{places}'))
                    available_places.append(places)

                new_reservation.available_places = available_places[0]
                new_reservation.time_from = dt.datetime.combine(new_reservation.day.date(), workday_start)
                new_reservation.time_to = new_reservation.time_from + dt.timedelta(hours=new_reservation.period)

                bot.set_state(call.from_user.id, BotStates.state_reservation_menu_place)
                states.show_place(bot, call, new_reservation=new_reservation)


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
        elif call.data == 'pay_now':
            bot.set_state(call.from_user.id, BotStates.state_prepay)
            states.show_prepay(bot, call, new_reservation)
        elif call.data == 'pay_later':
            new_reservation.payed = 'No'
            new_reservation.order_id = utils.generate_order_id(new_reservation)
            save_result_ok = states.reservation_repo.create_reservation(reservation_data=new_reservation)
            if save_result_ok:
                bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.id)
                bot.set_state(call.from_user.id, BotStates.state_start)
                bot.send_message(call.message.chat.id, utils.format_reservation_confirm(new_reservation), parse_mode=ParseMode.MARKDOWN)

                notify_admin('❇️ New reservation:\n'+utils.format_reservation_confirm(new_reservation))
        else:
            print('Unknown callback')


    @bot.callback_query_handler(func=lambda call: True, state=BotStates.state_prepay)
    def callback_query(call): 
        global new_reservation
        if call.data == 'cb_back':
            bot.set_state(call.from_user.id, BotStates.state_reservation_menu_recap)
            states.show_recap(bot, call, new_reservation)
        elif call.data == 'pay_done':
            bot.set_state(call.from_user.id, BotStates.state_start)
            new_reservation.payed = 'Pending'
            new_reservation.order_id = utils.generate_order_id(new_reservation)
            save_result_ok = states.reservation_repo.create_reservation(reservation_data=new_reservation)
            if save_result_ok:
                bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.id)
                bot.set_state(call.from_user.id, BotStates.state_start)
                bot.send_message(call.message.chat.id, utils.format_reservation_confirm_and_payed(new_reservation), parse_mode=ParseMode.MARKDOWN)

                notify_admin('❇️ New reservation:\n'+utils.format_reservation_confirm_and_payed(new_reservation))
        else:
            print('Unknown callback')



    @bot.message_handler(func = lambda msg: msg.text is not None and '/' not in msg.text, state=BotStates.state_admin_chat)
    def handle_message(msg):
        if msg.text == "Hi":
            bot.send_message(msg.chat.id,"Hello!")
        else:
            # bot.delete_message(chat_id=msg.chat.id, message_id=msg.message_id)
            # bot.send_message(msg.chat.id, "Got you.")
            bot.forward_message(chat_id=admin_chat_id, from_chat_id=msg.chat.id, message_id=msg.message_id)
            bot.set_state(msg.from_user.id, BotStates.state_admin_chat)

            time.sleep(2.5)

            bot.set_message_reaction(msg.chat.id, msg.message_id, [ReactionTypeEmoji('👍')], is_big=True)
            markup = InlineKeyboardMarkup()
            markup.row_width = 1
            markup.add(InlineKeyboardButton(BACK_BUTTON, callback_data='cb_back'),)

            time.sleep(0.5)
            bot.send_message(msg.chat.id, "Что-нибудь еще?", reply_markup=markup)
            

    bot.add_custom_filter(custom_filters.StateFilter(bot))
    bot.infinity_polling(skip_pending=True)