import logging
from dotenv import load_dotenv
import pandas as pd
import telebot # telebot
import datetime as dt
import json
import time

from telebot import custom_filters, TeleBot
from tg_bot.states import BotStates
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup
from telegram_bot_calendar import DetailedTelegramCalendar, WMonthTelegramCalendar, LSTEP
from telegram.constants import ParseMode

import tg_bot.states as states

# States storage
from telebot.storage import StateMemoryStorage
from telebot.types import ReactionTypeEmoji
from tg_bot import messages
from classes.classes import Reservation
import ast

from tg_bot.config import *
from tg_bot.messages import *
from db.connection import Database
from tg_bot import config

load_dotenv()


logging.basicConfig(
    level=logging.DEBUG, 
    filename='bot.log', 
    filemode='w', 
    format='%(asctime)s - %(levelname)s - %(message)s'
)

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


class TelegramBot:
    state_storage : StateMemoryStorage
    reservations_db : Database
    bot : telebot.TeleBot

    def __init__(self, bot_token:str, reservations_db:Database) -> None:
        self.state_storage = StateMemoryStorage()
        self.bot = telebot.TeleBot(token=bot_token, state_storage=self.state_storage)
        self.reservations_db = reservations_db

        self.bot.add_custom_filter(custom_filters.StateFilter(self.bot))
        # Register handlers in __init__
        self.register_handlers()
        self.register_callback_handlers()


    def notify_admin(self, text:str):
        notification_text = f"""
    {text}        

    """
        self.bot.send_message(chat_id=admin_chat_id, text=notification_text, parse_mode=ParseMode.MARKDOWN)

    
    def register_handlers(self):
        """Register all message handlers"""
        self.bot.message_handler(commands=['start'])(self.start)
        self.bot.message_handler(commands=['admin'])(self.admin)
        # Add other handlers here

    def register_callback_handlers(self):
        """Register all callback query handlers"""
        # Main menu callbacks
        self.bot.callback_query_handler(
            func=lambda call: True, 
            state=BotStates.state_main_menu
        )(self.callback_in_main_menu)

        # Info state callbacks
        self.bot.callback_query_handler(
            func=lambda call: True, 
            state=BotStates.state_info
        )(self.callback_in_info)

        # Info state callbacks
        self.bot.callback_query_handler(
            func=lambda call: True, 
            state=BotStates.state_my_reservation_list
        )(self.callback_in_my_reservation_list)

        # Info state callbacks
        self.bot.callback_query_handler(
            func=lambda call: True, 
            state=BotStates.state_my_reservation
        )(self.callback_in_my_reservation)

        # Info state callbacks
        self.bot.callback_query_handler(
            func=lambda call: True, 
            state=BotStates.state_reservation_menu_type
        )(self.callback_in_reservation_menu_type)

        self.bot.callback_query_handler(
            func=lambda call: True, 
            state=BotStates.state_reservation_menu_hours
        )(self.callback_in_state_reservation_menu_hours)

        self.bot.callback_query_handler(
            func=lambda call: True, 
            state=BotStates.state_admin_chat
        )(self.callback_in_admin_chat)

        
        

    def start(self, message):
        chat_id = message.chat.id
        self.bot.set_state(user_id=message.from_user.id, state=BotStates.state_main_menu)
        show_main_menu(self.bot, message)


    def admin(self, message):
        chat_id = message.chat.id
        self.bot.send_message(chat_id = chat_id, text='Hello')
    

    def callback_in_main_menu(self, call):
        global new_reservation
        if call.data == "cb_new_reservation":
            new_reservation = Reservation(telegramId=call.from_user.id, name=f'{call.from_user.full_name} ({call.from_user.username})')
            self.bot.set_state(call.from_user.id, BotStates.state_reservation_menu_type)
            show_reservation_type(self.bot, call)
        elif call.data == 'cb_my_reservations':
            self.bot.set_state(call.from_user.id, BotStates.state_my_reservation_list)
            show_my_reservations(self.bot, call)
        elif call.data == "cb_info":
            self.bot.set_state(call.from_user.id, BotStates.state_info)
            show_info(self.bot, call)


    def callback_in_info(self, call):
        if call.data == 'cb_back':
            self.bot.set_state(call.from_user.id, BotStates.state_main_menu)
            show_main_menu(self.bot, call.message)

    
    def callback_in_my_reservation_list(self, call):
        if call.data == 'cb_back':
            self.bot.set_state(call.from_user.id, BotStates.state_main_menu)
            show_main_menu(self.bot, call.message)
        else:
            self.bot.set_state(call.from_user.id, BotStates.state_my_reservation)
            reservation_table = self.reservations_db.to_dataframe()
            show_my_reservation(self.bot, call, reservations_table=reservation_table)


    def callback_in_my_reservation(self, call):
        if call.data == 'cb_back':
            self.bot.set_state(call.from_user.id, BotStates.state_my_reservation_list)
            show_my_reservations(self.bot, call)
        elif call.data.startswith('delete_'):
            order_id = '_'.join(call.data.split('_')[1:])
            deleted_reservation = self.reservations_db.delete_reservation(order_id)
            self.bot.set_state(call.from_user.id, BotStates.state_my_reservation_list)
            show_my_reservations(self.bot, call)

            self.notify_admin(f"✴️ Reservation was deleted:\n{deleted_reservation['From']}\n {deleted_reservation['OrderId']} \n{deleted_reservation['CreationTime']}")

                
    def callback_in_reservation_menu_type(self, call):
        global new_reservation
        if call.data == 'cb_back':
            self.bot.set_state(call.from_user.id, BotStates.state_main_menu)
            show_main_menu(self.bot, call.message)
        else:
            spec = call.data[0]
            new_reservation.type = spec
            self.bot.set_state(call.from_user.id, BotStates.state_reservation_menu_hours)
            show_hours(self.bot, call)


    def callback_in_state_reservation_menu_hours(self, call):
        global new_reservation
        if call.data == 'cb_back':
            self.bot.set_state(call.from_user.id, BotStates.state_reservation_menu_type)
            show_reservation_type(self.bot, call)
        elif call.data == 'talk_to_admin':
            # bot.send_message(call.message.chat.id, 'Please contact the administrator for this request.')
            self.bot.set_state(call.from_user.id, BotStates.state_admin_chat)
            show_admin_chat(self.bot, call)
        else:
            hours = int(call.data)
            new_reservation.period = hours
            self.bot.set_state(call.from_user.id, BotStates.state_reservation_menu_date)
            self.show_date(self.bot, call, new_reservation)


    def callback_in_admin_chat(self, call):
        if call.data == 'cb_back':
            self.bot.set_state(call.from_user.id, BotStates.state_main_menu)
            show_main_menu(self.bot, call.message)
        
        # Catch and resend message here:
    # # async def handle_message(update: Update, context: CallbackContext):
    # #     user_status = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
    # #     status_message = f"User status {update.effective_user.mention_html()} in this chat: {user_status.status}"
    # #     await context.bot.send_message(chat_id=update.effective_chat.id,
    # #                                 text=status_message,
    # #                                 parse_mode='HTML')

    def format_calendar(self, calendar, new_reservation: Reservation):
        json_calendar = json.loads(calendar)
        calendar = InlineKeyboardMarkup(InlineKeyboardMarkup.de_json(json_calendar).keyboard)
        calendar.add(InlineKeyboardButton(BACK_BUTTON, callback_data='cb_back'),)

        # Filter the reservations_table by 'Type' first
        reservation_df = self.reservations_db.to_dataframe()
        filtered_by_type = reservation_df[reservation_df['type'] == new_reservation.type]

        available_days = messages.find_available_days(new_reservation, reservation_table=filtered_by_type)

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

    def callback__in_reservation_menu_date(self, call):
        global new_reservation
        result, key, step = DetailedTelegramCalendar().process(call.data)
        if not result and key:
            key = format_calendar(key, new_reservation=new_reservation)
            self.bot.edit_message_text(f"Select {LSTEP[step]}",
                                call.message.chat.id,
                                call.message.message_id,
                                reply_markup=key)
        elif result:
            if new_reservation.period <= 12:
                self.bot.set_state(user_id=call.from_user.id, state=BotStates.state_reservation_menu_time)
                day = pd.to_datetime(result)
                new_reservation.day = day
                show_time(self.bot, call, new_reservation)
            elif new_reservation.period % 12 == 0:
                self.bot.set_state(user_id=call.from_user.id, state=BotStates.state_reservation_menu_place)
                day = pd.to_datetime(result)
                new_reservation.day = day

                # timeslots = self.reservations_db.find_timeslots_for_days(new_reservation, states.reservations_table.table, new_reservation.day)

                # available_places = []

                # buttons = []
                # for timeslot, places in timeslots.items():
                #     buttons.append(InlineKeyboardButton(timeslot, callback_data=f'{timeslot}_p{places}'))
                #     available_places.append(places)

                # new_reservation.available_places = available_places[0]
                # new_reservation.time_from = dt.datetime.combine(new_reservation.day.date(), workday_start)
                # new_reservation.time_to = new_reservation.time_from + dt.timedelta(hours=new_reservation.period)

                # bot.set_state(call.from_user.id, BotStates.state_reservation_menu_place)
                # states.show_place(bot, call, new_reservation=new_reservation)


    # @bot.callback_query_handler(func=lambda call: True, state=BotStates.state_reservation_menu_date)
    # def callback_query(call):
    #     if call.data == 'cb_back':
    #         bot.set_state(call.from_user.id, BotStates.state_reservation_menu_hours)
    #         states.show_hours(bot, call)

        
    # @bot.callback_query_handler(func=lambda call: True, state=BotStates.state_reservation_menu_time)
    # def callback_query(call):
    #     global new_reservation
    #     if call.data == 'cb_back':
    #         new_reservation.day = ''  # TODO
    #         bot.set_state(call.from_user.id, BotStates.state_reservation_menu_date)
    #         states.show_date(bot, call, new_reservation)
    #     else:
    #         callback_data = call.data.split('_p')
    #         time = pd.to_datetime(callback_data[0])
    #         available_places = ast.literal_eval(callback_data[1])

    #         new_reservation.available_places = available_places
    #         new_reservation.time_from = dt.datetime.combine(new_reservation.day.date(), time.time())
    #         new_reservation.time_to = new_reservation.time_from + dt.timedelta(hours=new_reservation.period)

    #         bot.set_state(call.from_user.id, BotStates.state_reservation_menu_place)
    #         states.show_place(bot, call, new_reservation=new_reservation)


    # @bot.callback_query_handler(func=lambda call: True, state=BotStates.state_reservation_menu_place)
    # def callback_query(call):
    #     global new_reservation
    #     if call.data == 'cb_back':
    #         bot.set_state(call.from_user.id, BotStates.state_reservation_menu_time)
    #         states.show_time(bot, call, new_reservation, going_back=True)
    #     else:
    #         place = int(call.data.split('_')[1])
    #         new_reservation.place = place

    #         bot.set_state(call.from_user.id, BotStates.state_reservation_menu_recap)
    #         states.show_recap(bot, call, new_reservation=new_reservation)


    # @bot.callback_query_handler(func=lambda call: True, state=BotStates.state_reservation_menu_recap)
    # def callback_query(call):
    #     global new_reservation
    #     if call.data == 'cb_back':
    #         bot.set_state(call.from_user.id, BotStates.state_reservation_menu_place)
    #         states.show_place(bot, call, new_reservation)
    #     elif call.data == 'pay_now':
    #         bot.set_state(call.from_user.id, BotStates.state_prepay)
    #         states.show_prepay(bot, call, new_reservation)
    #     elif call.data == 'pay_later':
    #         new_reservation.payed = 'No'
    #         new_reservation.order_id = messages.generate_order_id(new_reservation)
    #         save_result_ok = states.reservation_repo.create_reservation(reservation_data=new_reservation)
    #         if save_result_ok:
    #             bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.id)
    #             bot.set_state(call.from_user.id, BotStates.state_start)
    #             bot.send_message(call.message.chat.id, messages.format_reservation_confirm(new_reservation), parse_mode=ParseMode.MARKDOWN)

    #             notify_admin('❇️ New reservation:\n'+messages.format_reservation_confirm(new_reservation))
    #     else:
    #         print('Unknown callback')


    # @bot.callback_query_handler(func=lambda call: True, state=BotStates.state_prepay)
    # def callback_query(call): 
    #     global new_reservation
    #     if call.data == 'cb_back':
    #         bot.set_state(call.from_user.id, BotStates.state_reservation_menu_recap)
    #         states.show_recap(bot, call, new_reservation)
    #     elif call.data == 'pay_done':
    #         bot.set_state(call.from_user.id, BotStates.state_start)
    #         new_reservation.payed = 'Pending'
    #         new_reservation.order_id = messages.generate_order_id(new_reservation)
    #         save_result_ok = states.reservation_repo.create_reservation(reservation_data=new_reservation)
    #         if save_result_ok:
    #             bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.id)
    #             bot.set_state(call.from_user.id, BotStates.state_start)
    #             bot.send_message(call.message.chat.id, messages.format_reservation_confirm_and_payed(new_reservation), parse_mode=ParseMode.MARKDOWN)

    #             notify_admin('❇️ New reservation:\n'+messages.format_reservation_confirm_and_payed(new_reservation))
    #     else:
    #         print('Unknown callback')


    # @bot.message_handler(func = lambda msg: msg.text is not None and '/' not in msg.text, state=BotStates.state_admin_chat)
    # def handle_message(msg):

    #     if msg.text == "Hi":
    #         bot.send_message(msg.chat.id,"Hello!")
    #     else:
    #         # bot.delete_message(chat_id=msg.chat.id, message_id=msg.message_id)
    #         # bot.send_message(msg.chat.id, "Got you.")
    #         bot.forward_message(chat_id=admin_chat_id, from_chat_id=msg.chat.id, message_id=msg.message_id)
    #         bot.set_state(msg.from_user.id, BotStates.state_admin_chat)

    #         time.sleep(2.5)

    #         bot.set_message_reaction(msg.chat.id, msg.message_id, [ReactionTypeEmoji('👍')], is_big=True)
    #         markup = InlineKeyboardMarkup()
    #         markup.row_width = 1
    #         markup.add(InlineKeyboardButton(BACK_BUTTON, callback_data='cb_back'),)

    #         time.sleep(0.5)
    #         bot.send_message(msg.chat.id, "Что-нибудь еще?", reply_markup=markup)


    def show_date(self, bot:TeleBot, callback, new_reservation:Reservation):
        # global reservations_table
        # reservations_table_df = reservation_repo.
        calendar, step = WMonthTelegramCalendar().build()
        calendar = self.format_calendar(calendar, new_reservation)

        chatId = callback.message.chat.id
        messageId = callback.message.message_id
        bot.edit_message_text(chat_id=chatId, message_id=messageId, text=SELECT_DATE_MESSAGE, reply_markup=calendar)