import logging
from dotenv import load_dotenv
import pandas as pd
import telebot # telebot
from datetime import datetime as dt, timedelta
import json
from time import sleep
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

from tg_bot.messages import *
from db.connection import Database
from tg_bot import config
import math

load_dotenv()


logging.basicConfig(
    level=logging.DEBUG, 
    filename='bot.log', 
    filemode='w', 
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class TelegramBot:
    state_storage : StateMemoryStorage
    reservations_db : Database
    bot : telebot.TeleBot

    def __init__(self, bot_token:str, reservations_db:Database) -> None:
        self.state_storage = StateMemoryStorage()
        self.bot = telebot.TeleBot(token=bot_token, state_storage=self.state_storage)
        self.reservations_db = reservations_db

        self.bot.add_custom_filter(custom_filters.StateFilter(self.bot))
        self.register_handlers()
        self.register_callback_handlers()


    def notify_admin(self, text:str):
        self.bot.send_message(chat_id=config.admin_chat_id, text=text, parse_mode=ParseMode.MARKDOWN_V2)

    
    def register_handlers(self):
        """Register all message handlers"""
        self.bot.message_handler(commands=['start'])(self.start)
        self.bot.message_handler(commands=['admin'])(self.admin)

        # Add new message handler for admin chat
        @self.bot.message_handler(
            func=lambda msg: msg.text is not None and '/' not in msg.text,
            state=BotStates.state_admin_chat
        )
        def handle_message(msg):
            if msg.text == "Hi":
                self.bot.send_message(msg.chat.id, "Hello!")
            else:
                self.bot.forward_message(
                    chat_id=config.admin_chat_id,
                    from_chat_id=msg.chat.id,
                    message_id=msg.message_id
                )

                sleep(1.5)

                self.bot.set_message_reaction(
                    msg.chat.id,
                    msg.message_id,
                    [ReactionTypeEmoji('👍')],
                    is_big=True
                )
                
                markup = InlineKeyboardMarkup()
                markup.row_width = 1
                markup.add(InlineKeyboardButton(BACK_BUTTON, callback_data='cb_back'))

                sleep(1.0)
                self.bot.send_message(
                    msg.chat.id,
                    "Что-нибудь еще?",
                    reply_markup=markup
                )

        @self.bot.message_handler(
            content_types=['photo'],
        )
        def handle_payment_photo(message):
            photo = message.photo[-1]
            file_id = photo.file_id
            file_info = self.bot.get_file(file_id)
            file_path = file_info.file_path
            
            # Construct the direct download link (valid for 1 hour)
            file_url = f"https://api.telegram.org/file/bot{self.bot.token}/{file_path}"

            last_reservation = self.reservations_db.get_last_reservation_by_telegram_id(str(message.from_user.id))

            if last_reservation and not last_reservation.payment_confiramtion_link and not last_reservation.payed:
                # Case 1: Last reservation exists and needs payment confirmation

                # Add payment confirmation to the last reservation
                self.reservations_db.update_payment_confirmation(last_reservation.order_id, file_url)
                
                # Notify user
                self.bot.reply_to(message, text=messages.format_payment_confirm_receive(last_reservation))

                # Notify admin
                admin_notification = messages.format_payment_confirm_receive_admin_notofication(last_reservation)
                self.notify_admin(admin_notification)

            else:
                # Get all unpaid reservations without confirmation
                unpaid_reservations = self.reservations_db.get_unpaid_reservations_by_telegram_id(str(message.from_user.id))
                
                if len(unpaid_reservations) == 0:
                    # No reservations need payment confirmation
                    self.bot.reply_to(message, text=messages.format_no_pending_payments())
                
                elif len(unpaid_reservations) == 1:
                    # Only one reservation needs confirmation
                    reservation = unpaid_reservations[0]
                    self.reservations_db.update_payment_confirmation(reservation.order_id, file_url)
                    
                    self.bot.reply_to(message, messages.format_payment_confirm_receive(reservation))
                    
                    admin_notification = messages.format_payment_confirm_receive_admin_notofication(reservation)
                    self.notify_admin(admin_notification)
                
                else:
                    # Multiple reservations need confirmation
                    self.bot.reply_to(message, text=messages.format_multiple_pending_payments())

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
        )(self.callback_in_my_reservations)

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
        )(self.callback_in_reservation_menu_hours)

        self.bot.callback_query_handler(
            func=lambda call: True, 
            state=BotStates.state_admin_chat
        )(self.callback_in_admin_chat)

        self.bot.callback_query_handler(
            func=lambda call: True, 
            state=BotStates.state_reservation_menu_date
        )(self.callback_in_reservation_menu_date)

        self.bot.callback_query_handler(
            func=lambda call: True, 
            state=BotStates.state_reservation_menu_time
        )(self.callback_in_reservation_menu_time)

        self.bot.callback_query_handler(
            func=lambda call: True, 
            state=BotStates.state_reservation_menu_place
        )(self.callback_in_reservation_menu_place)

        self.bot.callback_query_handler(
            func=lambda call: True, 
            state=BotStates.state_prepay
        )(self.callback_in_prepay)

        self.bot.callback_query_handler(
            func=lambda call: True, 
            state=BotStates.state_reservation_menu_recap
        )(self.callback_in_reservation_menu_recap)

        self.bot.callback_query_handler(
            func=lambda call: True, 
            state=BotStates.state_payment_confirm
        )(self.callback_in_payment_confirm)

    def start(self, message):
        chat_id = message.chat.id
        self.bot.set_state(user_id=message.from_user.id, state=BotStates.state_main_menu)
        self.show_main_menu(self.bot, message)

    def admin(self, message):
        chat_id = message.chat.id
        self.bot.send_message(chat_id = chat_id, text='Hello')
    

    def show_my_reservations(self, callback):
        """
        Display user's upcoming reservations with interactive buttons
        
        Args:
            bot: TeleBot instance
            callback: Callback query containing user information
        """
        with self.reservations_db.get_db() as session:
            # Get upcoming reservations for user
            my_reservations = self.reservations_db.get_upcoming_reservations_by_telegram_id(str(callback.from_user.id))
            
            markup = InlineKeyboardMarkup()
            markup.row_width = 1

            if my_reservations:
                reservation_message_text = MY_RESERVATIONS_MESSAGE
                for r in my_reservations:
                    # Format datetime for button display
                    day_str = r.day.strftime("%d.%m.%Y")
                    time_from_str = r.time_from.strftime("%H:%M")
                    time_to_str = r.time_to.strftime("%H:%M")
                    
                    button_text = f'{"✅" if r.payed else "💳"} {day_str}  c {time_from_str} до {time_to_str}'
                    markup.add(InlineKeyboardButton(
                        text=button_text,
                        callback_data=r.order_id
                    ))
            else:
                reservation_message_text = MY_RESERVATIONS_MESSAGE_NO_RESERVATIONS

            markup.add(InlineKeyboardButton(
                text=BACK_BUTTON,
                callback_data='cb_back'
            ))

            self.bot.edit_message_text(
                chat_id=callback.message.chat.id,
                message_id=callback.message.message_id,
                text=reservation_message_text,
                reply_markup=markup
            )

    def callback_in_my_reservations(self, call):
        if call.data == 'cb_back':
            self.bot.set_state(call.from_user.id, BotStates.state_main_menu)
            self.show_main_menu(self.bot, call.message)
        else:
            self.bot.set_state(call.from_user.id, BotStates.state_my_reservation)
            reservation_table = self.reservations_db.to_dataframe()
            self.show_my_reservation(self.bot, call, reservations_table=reservation_table)


    def show_main_menu(self, bot:TeleBot, message):
        markup = InlineKeyboardMarkup()
        markup.row_width = 2
        markup.add(
            InlineKeyboardButton(NEW_RESERVATION_BUTTON, callback_data='cb_new_reservation'),
            InlineKeyboardButton(MY_RESERVATIONS_BUTTON, callback_data='cb_my_reservations'),
            InlineKeyboardButton(ABOUT_US_BUTTON, callback_data='cb_info')
        )
        bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
        bot.send_message(message.chat.id, WELCOME_MESSAGE, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)

    def callback_in_main_menu(self, call):
        global new_reservation
        if call.data == "cb_new_reservation":
            new_reservation = Reservation(telegramId=call.from_user.id, name=f'{call.from_user.full_name} ({call.from_user.username})')
            self.bot.set_state(call.from_user.id, BotStates.state_reservation_menu_type)
            self.show_reservation_type(self.bot, call)
        elif call.data == 'cb_my_reservations':
            self.bot.set_state(call.from_user.id, BotStates.state_my_reservation_list)
            self.show_my_reservations(call)
        elif call.data == "cb_info":
            self.bot.set_state(call.from_user.id, BotStates.state_info)
            self.show_info(self.bot, call)


    def show_info(self, bot:TeleBot, callback):
        markup = InlineKeyboardMarkup()
        markup.row_width = 1
        markup.add(InlineKeyboardButton(BACK_BUTTON, callback_data='cb_back'),)

        chatId = callback.message.chat.id
        messageId = callback.message.message_id
        bot.edit_message_text(chat_id=chatId, message_id=messageId, text=INFO_MESSAGE, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)

    def callback_in_info(self, call):
        if call.data == 'cb_back':
            self.bot.set_state(call.from_user.id, BotStates.state_main_menu)
            self.show_main_menu(self.bot, call.message)


    def show_my_reservation(self, bot:TeleBot, callback, reservations_table: pd.DataFrame):
        chatId = callback.message.chat.id
        messageId = callback.message.message_id
        reservation_id = callback.data
        reservation_df = reservations_table.loc[reservations_table['order_id'] == reservation_id]
        if reservation_df.empty:
            bot.edit_message_text(chat_id=chatId, message_id=messageId, text=RESERVATION_NOT_FOUND_MESSAGE)
            return
        
        reservation = Reservation.from_dataframe_row(reservation_df)

        markup = InlineKeyboardMarkup()
        markup.row_width = 1
        if reservation.payed == False:
            markup.add(InlineKeyboardButton(PAY_NOW_BUTTON, callback_data='pay_now'),)

        markup.add(
            InlineKeyboardButton(CANCEL_RESERVATION_BUTTON, callback_data=f'delete_{reservation_id}'),
            InlineKeyboardButton(BACK_BUTTON, callback_data='cb_back'),
        )
        
        reservation_info = format_reservation_info(reservation)
        bot.edit_message_text(chat_id=chatId, message_id=messageId, text=reservation_info, reply_markup=markup)

            


    def callback_in_my_reservation(self, call):
        if call.data == 'cb_back':
            self.bot.set_state(call.from_user.id, BotStates.state_my_reservation_list)
            self.show_my_reservations(call)
        elif call.data.startswith('delete_'):
            order_id = '_'.join(call.data.split('_')[1:])
            deleted_reservation = self.reservations_db.delete_reservation(order_id)
            ## AG: TODO logics here
            self.bot.set_state(call.from_user.id, BotStates.state_my_reservation_list)
            self.show_my_reservations(call)

            self.notify_admin(f"✴️ Reservation was deleted:\n{deleted_reservation['From']}\n {deleted_reservation['OrderId']} \n{deleted_reservation['CreationTime']}")


    def show_reservation_type(self, bot:TeleBot, callback):
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

    def callback_in_reservation_menu_type(self, call):
        global new_reservation
        if call.data == 'cb_back':
            self.bot.set_state(call.from_user.id, BotStates.state_main_menu)
            self.show_main_menu(self.bot, call.message)
        else:
            spec = call.data[0]
            new_reservation.type = spec
            self.bot.set_state(call.from_user.id, BotStates.state_reservation_menu_hours)
            self.show_hours(self.bot, call)


    def show_hours(self, bot:TeleBot, callback):
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

    def callback_in_reservation_menu_hours(self, call):
        global new_reservation
        if call.data == 'cb_back':
            self.bot.set_state(call.from_user.id, BotStates.state_reservation_menu_type)
            self.show_reservation_type(self.bot, call)
        elif call.data == 'talk_to_admin':
            # bot.send_message(call.message.chat.id, 'Please contact the administrator for this request.')
            self.bot.set_state(call.from_user.id, BotStates.state_admin_chat)
            self.show_admin_chat(self.bot, call)
        else:
            hours = int(call.data)
            new_reservation.period = hours
            new_reservation.sum = config.prices[new_reservation.type] * new_reservation.period  # AG TODO: Move to Reservation class
            self.bot.set_state(call.from_user.id, BotStates.state_reservation_menu_date)
            self.show_date(self.bot, call, new_reservation)


    def show_admin_chat(self, bot:TeleBot, callback):
        markup = InlineKeyboardMarkup()
        markup.row_width = 1
        markup.add(
            InlineKeyboardButton(BACK_BUTTON, callback_data='cb_back'),
        )

        chatId = callback.message.chat.id
        messageId = callback.message.message_id
        bot.edit_message_text(chat_id=chatId, message_id=messageId, text=ADMIN_CHAT_MESSAGE, reply_markup=markup)

    def callback_in_admin_chat(self, call):
        if call.data == 'cb_back':
            self.bot.set_state(call.from_user.id, BotStates.state_main_menu)
            self.show_main_menu(self.bot, call.message)
        
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

        available_days = self.reservations_db.find_available_days(new_reservation)

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


    def show_date(self, bot:TeleBot, callback, new_reservation:Reservation):
        calendar, step = WMonthTelegramCalendar().build()
        calendar = self.format_calendar(calendar, new_reservation)

        chatId = callback.message.chat.id
        messageId = callback.message.message_id
        bot.edit_message_text(chat_id=chatId, message_id=messageId, text=SELECT_DATE_MESSAGE, reply_markup=calendar)

    def callback_in_reservation_menu_date(self, call):
        if call.data == 'cb_back':
            self.bot.set_state(call.from_user.id, BotStates.state_reservation_menu_hours)
            self.show_hours(self.bot, call)
            return
        
        result, key, step = DetailedTelegramCalendar().process(call.data)
        if not result and key:
            key = self.format_calendar(key, new_reservation=new_reservation)
            self.bot.edit_message_text(f"Select {LSTEP[step]}",
                                call.message.chat.id,
                                call.message.message_id,
                                reply_markup=key)
        elif result:
            if new_reservation.period < 12:
                self.bot.set_state(user_id=call.from_user.id, state=BotStates.state_reservation_menu_time)
                day = pd.to_datetime(result)
                new_reservation.day = day
                self.show_time(self.bot, call, new_reservation)
            elif new_reservation.period % 12 == 0:
                self.bot.set_state(user_id=call.from_user.id, state=BotStates.state_reservation_menu_place)
                day = pd.to_datetime(result)
                new_reservation.day = day
                new_reservation.time_from = dt.combine(new_reservation.day.date(), config.workday_start)
                new_reservation.time_to = new_reservation.time_from + timedelta(hours=new_reservation.period)

                timeslots = self.reservations_db.get_available_timeslots(new_reservation)
                available_places = []

                buttons = []
                for timeslot, places in timeslots.items():
                    buttons.append(InlineKeyboardButton(timeslot, callback_data=f'{timeslot}_p{places}'))
                    available_places.append(places)

                new_reservation.available_places = available_places[0]
                

                self.bot.set_state(call.from_user.id, BotStates.state_reservation_menu_place)
                self.show_place(self.bot, call, new_reservation=new_reservation)


    def show_time(self, bot: TeleBot, callback, new_reservation: Reservation, going_back=False):
        if callback.data != 'cb_back':
            # Get last 3 elements and join them with '-'
            date = dt.strptime('-'.join(callback.data.split('_')[-3:]), '%Y-%m-%d').date()
        else:
            date = new_reservation.time_from.date()
        
        # Create time slot buttons
        buttons = []
        
        now = dt.now(pytz.UTC)
        workday_start = config.workday_start
        workday_end = config.workday_end
        
        if date == now.date():
            # Add buffer minutes to current time
            buffer_time = now + timedelta(minutes=config.time_buffer_mins)
            
            # If we're before workday start, use workday start
            if buffer_time.time() < workday_start:
                time_start_search = dt.combine(date, time(workday_start.hour, 0))
                # Make timezone-aware
                time_start_search = pytz.UTC.localize(time_start_search)
            else:
                # Calculate minutes since start of day
                minutes_since_midnight = buffer_time.hour * 60 + buffer_time.minute
                # Round up to next stride interval
                next_slot_minutes = math.ceil(minutes_since_midnight / config.stride_mins) * config.stride_mins
                # Convert back to datetime and make timezone-aware
                naive_time = dt.combine(date, time(0, 0)) + timedelta(minutes=next_slot_minutes)
                time_start_search = pytz.UTC.localize(naive_time)
                
                # If calculated time is before workday start, use workday start
                if time_start_search.time() < workday_start:
                    time_start_search = pytz.UTC.localize(dt.combine(date, time(workday_start.hour, 0)))
        else:
            # If not today, start from beginning of workday
            naive_time = dt.combine(date, time(workday_start.hour, 0))
            time_start_search = pytz.UTC.localize(naive_time)

        # Calculate end of workday considering reservation period
        workday_end = dt.combine(date, config.workday_end) - timedelta(hours=new_reservation.period)
        
        timeslots = self.reservations_db.get_available_timeslots(new_reservation)
        available_places = []

        buttons = []
        for timeslot, places in timeslots.items():
            buttons.append(InlineKeyboardButton(timeslot, callback_data=f'{timeslot}_p{places}'))
            available_places.append(places)

        # new_reservation.available_places = available_places

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

    def callback_in_reservation_menu_time(self, call):
        global new_reservation
        if call.data == 'cb_back':
            new_reservation.day = ''  # TODO
            self.bot.set_state(call.from_user.id, BotStates.state_reservation_menu_date)
            self.show_date(self.bot, call, new_reservation)
        else:
            callback_data = call.data.split('_p')
            time = pd.to_datetime(callback_data[0])
            available_places = ast.literal_eval(callback_data[1])

            new_reservation.available_places = available_places
            new_reservation.time_from = dt.combine(new_reservation.day.date(), time.time())
            new_reservation.time_to = new_reservation.time_from + timedelta(hours=new_reservation.period)

            self.bot.set_state(call.from_user.id, BotStates.state_reservation_menu_place)
            self.show_place(self.bot, call, new_reservation=new_reservation)


    def show_place(self, bot:TeleBot, callback, new_reservation: Reservation):
        markup = InlineKeyboardMarkup()
        markup.row_width = 4
        for place in new_reservation.available_places:
            markup.add(InlineKeyboardButton(f'Место {place}', callback_data=f'place_{place}'),)

        markup.add(InlineKeyboardButton(BACK_BUTTON, callback_data='cb_back'),)

        chatId = callback.message.chat.id
        messageId = callback.message.message_id
        bot.delete_message(chat_id=chatId, message_id=messageId)
        bot.send_photo(chat_id=chatId, caption=SELECT_SEAT_MESSAGE, photo=open('img/seats/places_all.jpg', 'rb'), reply_markup=markup)

    def callback_in_reservation_menu_place(self, call):
        global new_reservation
        if call.data == 'cb_back':
            self.bot.set_state(call.from_user.id, BotStates.state_reservation_menu_time)
            self.show_time(self.bot, call, new_reservation, going_back=True)
        else:
            place = int(call.data.split('_')[1])
            new_reservation.place = place

            self.bot.set_state(call.from_user.id, BotStates.state_reservation_menu_recap)
            self.show_recap(self.bot, call, new_reservation=new_reservation)


    def show_recap(self, bot:TeleBot, callback, new_reservation: Reservation):
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

    def callback_in_reservation_menu_recap(self, call):
        global new_reservation
        if call.data == 'cb_back':
            self.bot.set_state(call.from_user.id, BotStates.state_reservation_menu_place)
            self.show_place(self.bot, call, new_reservation)
        elif call.data == 'pay_now':
            self.bot.set_state(call.from_user.id, BotStates.state_prepay)
            self.show_prepay(self.bot, call, new_reservation)
        elif call.data == 'pay_later':
            new_reservation.payed = False
            new_reservation.order_id = self.reservations_db.generate_order_id(new_reservation)
            new_reservation.payment_confiramtion_link = ''
            save_result_ok = self.reservations_db.create_reservation(new_reservation)
            if save_result_ok:
                self.bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.id)
                self.bot.set_state(call.from_user.id, BotStates.state_start)
                self.bot.send_message(call.message.chat.id, messages.format_reservation_created(new_reservation), parse_mode=ParseMode.MARKDOWN)

                self.notify_admin(messages.format_reservation_created_admin_notification(new_reservation))
        else:
            print('Unknown callback')


    def show_prepay(self, bot:TeleBot, callback, new_reservation: Reservation):
        markup = InlineKeyboardMarkup()
        markup.row_width = 1
        markup.add(
            InlineKeyboardButton(PAY_NOW_BUTTON, callback_data='pay_now', url=PAY_URL),
            InlineKeyboardButton(PAY_DONE_BUTTON, callback_data='pay_done'),
            InlineKeyboardButton(BACK_BUTTON, callback_data='cb_back'),
        )

        recap_string = format_prepay(new_reservation.sum)

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

    def callback_in_prepay(self, call): 
        global new_reservation
        if call.data == 'cb_back':
            self.bot.set_state(call.from_user.id, BotStates.state_reservation_menu_recap)
            self.show_recap(self.bot, call, new_reservation)
        elif call.data == 'pay_done':
            new_reservation.payed = False
            new_reservation.order_id = self.reservations_db.generate_order_id(new_reservation)
            new_reservation.payment_confiramtion_link = ''
            save_result_ok = self.reservations_db.create_reservation(new_reservation)
            if save_result_ok:
                self.bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.id)
                self.bot.set_state(call.from_user.id, BotStates.state_start)

                self.bot.send_message(call.message.chat.id, messages.format_payment_confirm_request(new_reservation), parse_mode=ParseMode.MARKDOWN)
                self.notify_admin(messages.format_reservation_created_admin_notification(new_reservation))
        else:
            print('Unknown callback')


    def show_payment_confirm(self, bot:TeleBot, callback, new_reservation: Reservation):
        markup = InlineKeyboardMarkup()
        markup.row_width = 1
        markup.add(
            InlineKeyboardButton(BACK_BUTTON, callback_data='cb_back'),
        )

        chatId = callback.message.chat.id
        messageId = callback.message.message_id
        bot.delete_message(chat_id=chatId, message_id=messageId)

        bot.send_message(callback.message.chat.id, text=messages.PATMENT_CONFIRM_REQUEST , reply_markup=markup, parse_mode=ParseMode.MARKDOWN)

    def callback_in_payment_confirm(self, call):
        ...
