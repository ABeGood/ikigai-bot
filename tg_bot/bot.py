import logging
import pandas as pd
import telebot # telebot
from datetime import datetime as dt, timedelta
import json
from time import sleep
import time
import re
from typing import Optional

from telebot import custom_filters, TeleBot
from tg_bot.states import BotStates
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup
from telegram_bot_calendar import DetailedTelegramCalendar, WMonthTelegramCalendar, LSTEP
from telegram.constants import ParseMode

# States storage
from telebot.storage import StateMemoryStorage
from telebot.handler_backends import State
from telebot.types import ReactionTypeEmoji
from tg_bot import messages
from classes.classes import Reservation
import ast

from tg_bot.messages import *
from db.connection import Database
from tg_bot import config
from tg_bot.reminder import ReminderSystem
import math

def get_admin_payment_keyboard(reservation_id: str) -> InlineKeyboardMarkup:
    """Create keyboard for admin payment confirmation"""
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(
        InlineKeyboardButton("✅ Подтвердить", callback_data=f'confirm_payment_{reservation_id}'),
        InlineKeyboardButton("❌ Отклонить", callback_data=f'reject_payment_{reservation_id}')
    )
    return markup


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
    reminder_system : ReminderSystem

    def __init__(self, bot_token:str, reservations_db:Database) -> None:
        self.state_storage = StateMemoryStorage()
        self.reservations_db = reservations_db
        self.bot = telebot.TeleBot(token=bot_token, state_storage=self.state_storage)

        self.reminder_system = ReminderSystem(self)
        self.logger = logging.getLogger(__name__)

        self.bot.add_custom_filter(custom_filters.StateFilter(self.bot))
        self.register_handlers()
        self.register_callback_handlers()
        self.register_admin_payment_handlers()


    def run_bot(self):
        """Start both the bot and reminder system"""
        # Start reminder system
        self.reminder_system.start()
        
        # Start bot polling
        try:
            self.logger.info("Starting bot...")
            self.bot.polling(non_stop=True)
        finally:
            # Ensure reminder system is stopped if bot exits
            self.reminder_system.stop()


    def set_state(self, user_id: int, new_state: State, store_prev_state: bool = True):
        current_state = self.bot.get_state(user_id)
        if store_prev_state:
            if current_state:
                self.bot.add_data(user_id=user_id, prev_state=current_state)

        if current_state == BotStates.state_pay.name:  # AG: mb something better?
            state_data = self.bot.retrieve_data(user_id)
            if state_data and 'pending_payment_reservation' in state_data.data:
                self.bot.add_data(user_id=user_id, pending_payment_reservation=None)

        self.bot.set_state(user_id, new_state)

    def get_previous_state(self, user_id: int) -> Optional[State]:
        state_data = self.bot.retrieve_data(user_id)
        return state_data.data.get('prev_state') if state_data else None

    def notify_admin(self, text:str, reservation:Reservation|None = None):
        if not reservation:
            self.bot.send_message(chat_id=config.admin_chat_id, text=text, parse_mode=ParseMode.MARKDOWN_V2)
        else:
            keyboard = get_admin_payment_keyboard(reservation.order_id)
            self.bot.send_photo(
                chat_id=config.admin_chat_id,
                photo=reservation.payment_confirmation_file_id,
                caption=messages.format_payment_confirm_receive_admin_notification(reservation),
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=keyboard
            )



    def register_admin_payment_handlers(self):
        @self.bot.callback_query_handler(func=lambda call: call.data.startswith(('confirm_payment_', 'reject_payment_')))
        def handle_admin_payment_action(call):
            # Verify it's coming from admin chat
            if call.message.chat.id != config.admin_chat_id:
                return
            
            action = None
            reservation_id = None

            if str(call.data).startswith('confirm_payment_'):
                action = 'confirm'
                reservation_id = re.sub('^confirm_payment_', '', call.data)
            elif str(call.data).startswith('reject_payment_'):
                action = 'reject'
                reservation_id = re.sub('^reject_payment_', '', call.data)
                
            reservation = self.reservations_db.get_reservation_by_order_id(reservation_id)
            
            if not reservation:
                self.bot.answer_callback_query(call.id, text="Reservation not found")
                return
                
            if action == 'confirm':
                # Update reservation status
                reservation = self.reservations_db.update_reservation(reservation_id, {'payed': True})
                
                # Notify admin
                self.bot.edit_message_caption(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    caption=f"{messages.format_reservation_created_and_payed(reservation=reservation)}\n✅ Payment confirmed",
                    parse_mode=ParseMode.MARKDOWN_V2
                )
                
                # Notify user
                self.bot.send_message(
                    chat_id=reservation.telegram_id,
                    text=messages.format_reservation_created_and_payed(reservation),
                    parse_mode=ParseMode.MARKDOWN
                )
                
            elif action == 'reject':
                reservation = self.reservations_db.update_reservation(reservation_id, {'payment_confirmation_link': None, 'payment_confirmation_file_id': None})
                # Keep reservation unpaid
                # Notify admin
                self.bot.edit_message_caption(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    caption=f"{messages.format_reservation_created_and_payed(reservation=reservation)}\n❌ Payment rejected",
                    parse_mode=ParseMode.MARKDOWN_V2
                )
                
                # Notify user about rejection
                self.bot.send_message(
                    chat_id=reservation.telegram_id,
                    text=(
                        "❌ Ваше подтверждение оплаты было отклонено\\.\n\n"
                        "Пожалуйста, убедитесь, что сумма и получатель платежа верны, "
                        "и отправьте новое подтверждение\\."
                    ),  # AG: TODO reservation info
                    parse_mode=ParseMode.MARKDOWN
                )

    
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
            # AG TODO: Set to start state
            photo = message.photo[-1]
            file_id = photo.file_id
            file_info = self.bot.get_file(file_id)
            file_path = file_info.file_path
            
            # Construct the direct download link (valid for 1 hour)
            file_url = f"https://api.telegram.org/file/bot{self.bot.token}/{file_path}"

            state_data = self.bot.retrieve_data(message.from_user.id)
            reservation_to_pay = state_data.data.get('pending_payment_reservation', None) if state_data.data else None
    
            if reservation_to_pay:
                payed_reservation = self.reservations_db.update_payment_confirmation(reservation_to_pay, file_url, file_id)
                self.bot.reply_to(message, text=messages.format_payment_confirm_receive(payed_reservation))
                
                # Add keyboard to admin notification
                keyboard = get_admin_payment_keyboard(payed_reservation.order_id)
                self.bot.send_photo(
                    chat_id=config.admin_chat_id,
                    photo=file_id,
                    caption=messages.format_payment_confirm_receive_admin_notification(payed_reservation),
                    parse_mode=ParseMode.MARKDOWN_V2,
                    reply_markup=keyboard
                )
                return

            last_reservation = self.reservations_db.get_last_reservation_by_telegram_id(str(message.from_user.id))

            if last_reservation and not last_reservation.payment_confirmation_link and not last_reservation.payed:
                payed_reservation = self.reservations_db.update_payment_confirmation(str(last_reservation.order_id), file_url, file_id)
                self.bot.reply_to(message, text=messages.format_payment_confirm_receive(payed_reservation))
                
                # Add keyboard to admin notification
                keyboard = get_admin_payment_keyboard(payed_reservation.order_id)
                self.bot.send_photo(
                    chat_id=config.admin_chat_id,
                    photo=file_id,
                    caption=messages.format_payment_confirm_receive_admin_notification(payed_reservation),
                    parse_mode=ParseMode.MARKDOWN_V2,
                    reply_markup=keyboard
                )

            else:
                unpaid_reservations = self.reservations_db.get_unpaid_reservations_by_telegram_id(str(message.from_user.id))
                
                if len(unpaid_reservations) == 0:
                    self.bot.reply_to(message, text=messages.format_no_pending_payments())
                
                elif len(unpaid_reservations) == 1:
                    reservation = unpaid_reservations[0]
                    self.reservations_db.update_payment_confirmation(str(reservation.order_id), file_url, file_id)
                    self.bot.reply_to(message, messages.format_payment_confirm_receive(reservation))
                    
                    # Add keyboard to admin notification
                    keyboard = get_admin_payment_keyboard(reservation.order_id)
                    self.bot.send_photo(
                        chat_id=config.admin_chat_id,
                        photo=file_id,
                        caption=messages.format_payment_confirm_receive_admin_notification(reservation),
                        parse_mode=ParseMode.MARKDOWN_V2,
                        reply_markup=keyboard
                    )
                
                else:
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
            state=BotStates.state_pay
        )(self.callback_in_pay)

        self.bot.callback_query_handler(
            func=lambda call: True, 
            state=BotStates.state_reservation_menu_recap
        )(self.callback_in_reservation_menu_recap)

        # self.bot.callback_query_handler(
        #     func=lambda call: True, 
        #     state=BotStates.state_payment_confirm
        # )(self.callback_in_payment_confirm)

    def start(self, message):
        # chat_id = message.chat.id
        self.set_state(user_id=message.from_user.id, new_state=BotStates.state_main_menu)
        self.show_main_menu(self.bot, message)

    def admin(self, message):
        chat_id = message.chat.id
        self.bot.send_message(chat_id=chat_id, text='Hello')
    

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
                    
                    button_text = f'{messages.get_status_string(r)} {day_str}  c {time_from_str} до {time_to_str}'
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

            # self.bot.edit_message_text(
            #     chat_id=callback.message.chat.id,
            #     message_id=callback.message.message_id,
            #     text=reservation_message_text,
            #     reply_markup=markup
            # )
            try:
                # Check if the message has a photo
                if hasattr(callback.message, 'photo') and callback.message.photo:
                    # If it's a photo message, delete it and send new text message
                    self.bot.delete_message(
                        chat_id=callback.message.chat.id,
                        message_id=callback.message.message_id
                    )
                    self.bot.send_message(
                        chat_id=callback.message.chat.id,
                        text=reservation_message_text,
                        reply_markup=markup
                    )
                else:
                    # If it's a text message, edit it
                    self.bot.edit_message_text(
                        chat_id=callback.message.chat.id,
                        message_id=callback.message.message_id,
                        text=reservation_message_text,
                        reply_markup=markup
                    )
            except Exception as e:
                # If any error occurs, delete the old message and send a new one
                logging.error(f"Error updating message: {e}")
                try:
                    self.bot.delete_message(
                        chat_id=callback.message.chat.id,
                        message_id=callback.message.message_id
                    )
                    self.bot.send_message(
                        chat_id=callback.message.chat.id,
                        text=reservation_message_text,
                        reply_markup=markup
                    )
                except Exception as e2:
                    logging.error(f"Error in fallback message handling: {e2}")

    def callback_in_my_reservations(self, call):
        if call.data == 'cb_back':
            self.set_state(call.from_user.id, BotStates.state_main_menu)
            self.show_main_menu(self.bot, call.message)
        else:
            self.set_state(call.from_user.id, BotStates.state_my_reservation)
            self.show_my_reservation(self.bot, call)


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
            self.set_state(call.from_user.id, BotStates.state_reservation_menu_type)
            self.show_reservation_type(self.bot, call)
        elif call.data == 'cb_my_reservations':
            self.set_state(call.from_user.id, BotStates.state_my_reservation_list)
            self.show_my_reservations(call)
        elif call.data == "cb_info":
            self.set_state(call.from_user.id, BotStates.state_info)
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
            self.set_state(call.from_user.id, BotStates.state_main_menu)
            self.show_main_menu(self.bot, call.message)


    def show_my_reservation(self, bot:TeleBot, callback):
        chatId = callback.message.chat.id
        messageId = callback.message.message_id
        reservation_id = callback.data
        reservation = self.reservations_db.get_reservation_by_order_id(order_id=reservation_id)
        if not reservation:
            bot.edit_message_text(chat_id=chatId, message_id=messageId, text=RESERVATION_NOT_FOUND_MESSAGE)
            return

        markup = InlineKeyboardMarkup()
        markup.row_width = 1

        if not reservation.payment_confirmation_link:
            markup.add(InlineKeyboardButton(PAY_NOW_BUTTON, callback_data=f'pay_{reservation_id}'),
                       InlineKeyboardButton(CANCEL_RESERVATION_BUTTON, callback_data=f'delete_{reservation_id}'),
                       InlineKeyboardButton(BACK_BUTTON, callback_data='cb_back'),
                       )
            reservation_info = format_reservation_info(reservation)
            bot.edit_message_text(chat_id=chatId, message_id=messageId, text=reservation_info, reply_markup=markup)
        else:
            markup.add(InlineKeyboardButton(CHANGE_PAYCHECK_BUTTON, callback_data=f'change-pay_{reservation_id}'),
                       InlineKeyboardButton(BACK_BUTTON, callback_data='cb_back'),
                       )
            bot.delete_message(chat_id=chatId, message_id=messageId)
            reservation_info = format_reservation_info(reservation)

            try:
                bot.send_photo(
                    chat_id=chatId,
                    photo=reservation.payment_confirmation_file_id,
                    caption=reservation_info,
                    reply_markup=markup
                )
            except Exception as e:  # AG TODO: Notify admin
                # If there's an error sending the photo (e.g., expired link),
                # fall back to text-only message
                logging.error(f"Error sending payment confirmation photo: {e}")
                bot.send_message(
                    chat_id=chatId,
                    text=f"{reservation_info}\n\n⚠️ Payment confirmation image unavailable",
                    reply_markup=markup
                )



    def callback_in_my_reservation(self, call):
        if call.data == 'cb_back':
            self.set_state(call.from_user.id, BotStates.state_my_reservation_list)
            self.show_my_reservations(call)
        elif call.data.startswith('pay_') or call.data.startswith('change-pay_'):
            order_id = '_'.join(call.data.split('_')[1:])
            self.set_state(call.from_user.id, BotStates.state_pay)
            reservation_to_pay = self.reservations_db.get_reservation_by_order_id(order_id)
            self.show_pay(self.bot, callback=call, reservation=reservation_to_pay)

        elif call.data.startswith('delete_'):
            order_id = '_'.join(call.data.split('_')[1:])
            deleted_reservation = self.reservations_db.delete_reservation(order_id)
            ## AG: TODO logics here
            self.set_state(call.from_user.id, BotStates.state_my_reservation_list)
            self.show_my_reservations(call)

            admin_notification = messages.format_reservation_deleted_admin_notification(deleted_reservation)
            self.notify_admin(text=admin_notification)


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
            self.set_state(call.from_user.id, BotStates.state_main_menu)
            self.show_main_menu(self.bot, call.message)
        else:
            spec = call.data[0]
            new_reservation.type = spec
            self.set_state(call.from_user.id, BotStates.state_reservation_menu_hours)
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
            self.set_state(call.from_user.id, BotStates.state_reservation_menu_type)
            self.show_reservation_type(self.bot, call)
        elif call.data == 'talk_to_admin':
            # bot.send_message(call.message.chat.id, 'Please contact the administrator for this request.')
            self.set_state(call.from_user.id, BotStates.state_admin_chat)
            self.show_admin_chat(self.bot, call)
        else:
            hours = int(call.data)
            new_reservation.period = hours
            new_reservation.sum = config.prices[new_reservation.type] * new_reservation.period  # AG TODO: Move to Reservation class
            self.set_state(call.from_user.id, BotStates.state_reservation_menu_date)
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
            self.set_state(call.from_user.id, BotStates.state_main_menu)
            self.show_main_menu(self.bot, call.message)
        
        # Catch and resend message here:


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
            self.set_state(call.from_user.id, BotStates.state_reservation_menu_hours)
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
                self.set_state(user_id=call.from_user.id, new_state=BotStates.state_reservation_menu_time)
                day = pd.to_datetime(result)
                new_reservation.day = day
                self.show_time(self.bot, call, new_reservation)
            elif new_reservation.period % 12 == 0:
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
                
                self.set_state(call.from_user.id, BotStates.state_reservation_menu_place)
                self.show_place(self.bot, call, new_reservation=new_reservation)


    def show_time(self, bot: TeleBot, callback, new_reservation: Reservation, going_back=False):
        if callback.data != 'cb_back':
            # Get last 3 elements and join them with '-'
            date = dt.strptime('-'.join(callback.data.split('_')[-3:]), '%Y-%m-%d').date()
        else:
            date = new_reservation.time_from.date()
        
        # Create time slot buttons
        buttons = []
        
        now = dt.now(config.LOCAL_TIMEZONE)
        workday_start = config.workday_start
        workday_end = config.workday_end
        
        if date == now.date():
            # Add buffer minutes to current time
            buffer_time = now + timedelta(minutes=config.time_buffer_mins)
            
            # If we're before workday start, use workday start
            if buffer_time.time() < workday_start:
                time_start_search = dt.combine(date, time(workday_start.hour, 0))
                # Make timezone-aware
                time_start_search = config.LOCAL_TIMEZONE.localize(time_start_search)
            else:
                # Calculate minutes since start of day
                minutes_since_midnight = buffer_time.hour * 60 + buffer_time.minute
                # Round up to next stride interval
                next_slot_minutes = math.ceil(minutes_since_midnight / config.stride_mins) * config.stride_mins
                # Convert back to datetime and make timezone-aware
                naive_time = dt.combine(date, time(0, 0)) + timedelta(minutes=next_slot_minutes)
                time_start_search = config.LOCAL_TIMEZONE.localize(naive_time)
                
                # If calculated time is before workday start, use workday start
                if time_start_search.time() < workday_start:
                    time_start_search = config.LOCAL_TIMEZONE.localize(dt.combine(date, time(workday_start.hour, 0)))
        else:
            # If not today, start from beginning of workday
            naive_time = dt.combine(date, time(workday_start.hour, 0))
            time_start_search = config.LOCAL_TIMEZONE.localize(naive_time)

        # Calculate end of workday considering reservation period
        # workday_end = dt.combine(date, config.workday_end) - timedelta(hours=new_reservation.period)
        
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
            new_reservation.day = ''
            self.set_state(call.from_user.id, BotStates.state_reservation_menu_date)
            self.show_date(self.bot, call, new_reservation)
        else:
            callback_data = call.data.split('_p')
            time = pd.to_datetime(callback_data[0])
            available_places = ast.literal_eval(callback_data[1])

            new_reservation.available_places = available_places
            new_reservation.time_from = dt.combine(new_reservation.day.date(), time.time())
            new_reservation.time_to = new_reservation.time_from + timedelta(hours=new_reservation.period)

            self.set_state(call.from_user.id, BotStates.state_reservation_menu_place)
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
            self.set_state(call.from_user.id, BotStates.state_reservation_menu_time)
            self.show_time(self.bot, call, new_reservation, going_back=True)
        else:
            place = int(call.data.split('_')[1])
            new_reservation.place = place

            self.set_state(call.from_user.id, BotStates.state_reservation_menu_recap)
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
            self.set_state(call.from_user.id, BotStates.state_reservation_menu_place)
            self.show_place(self.bot, call, new_reservation)
        elif call.data == 'pay_now':
            new_reservation.payed = False
            new_reservation.order_id = self.reservations_db.generate_order_id(new_reservation)
            new_reservation.payment_confirmation_link = None
            save_result_ok = self.reservations_db.create_reservation(new_reservation)
            if save_result_ok:
                self.set_state(call.from_user.id, BotStates.state_pay)
                self.show_pay(self.bot, call, new_reservation)
                self.notify_admin(text=messages.format_reservation_created_admin_notification(new_reservation))
            else:
                ...
                # AG TODO: Error message + admin notification
        elif call.data == 'pay_later':
            new_reservation.payed = False
            new_reservation.order_id = self.reservations_db.generate_order_id(new_reservation)
            new_reservation.payment_confirmation_link = None
            save_result_ok = self.reservations_db.create_reservation(new_reservation)
            if save_result_ok:
                self.bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.id)
                self.set_state(call.from_user.id, BotStates.state_start)
                self.bot.send_message(call.message.chat.id, messages.format_reservation_created(new_reservation), parse_mode=ParseMode.MARKDOWN)
                self.notify_admin(text=messages.format_reservation_created_admin_notification(new_reservation))
            else:
                ...
                # AG TODO: Error message + admin notification
        else:
            print('Unknown callback')


    # Here set the reservation to link the confirmation with
    def show_pay(self, bot:TeleBot, callback, reservation: Reservation):
        markup = InlineKeyboardMarkup()
        markup.row_width = 1

        prev_state = self.get_previous_state(callback.from_user.id)
        if prev_state == BotStates.state_reservation_menu_recap.name:
            markup.add(InlineKeyboardButton(PAY_LINK_BUTTON, url=PAY_URL),)
            recap_string = format_pay_from_recap(reservation.sum)
        elif prev_state == BotStates.state_my_reservation.name:
            self.bot.add_data(user_id=callback.from_user.id, pending_payment_reservation=reservation.order_id)
            if not reservation.payment_confirmation_link:
                markup.add(InlineKeyboardButton(PAY_LINK_BUTTON, url=PAY_URL),)
                recap_string = format_pay_from_my_reservations(reservation.sum)
            else:
                recap_string = format_change_paycheck()

            markup.add(InlineKeyboardButton(BACK_BUTTON, callback_data='cb_back'),)

        chatId = callback.message.chat.id
        messageId = callback.message.message_id
        bot.delete_message(chat_id=chatId, message_id=messageId)
        bot.send_message(callback.message.chat.id, text=recap_string, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)

    def callback_in_pay(self, call):
        global new_reservation
        if call.data == 'cb_back':
            prev_state = self.get_previous_state(call.from_user.id)
            if prev_state == BotStates.state_reservation_menu_recap.name:
                self.set_state(call.from_user.id, BotStates.state_reservation_menu_recap)
                self.show_recap(self.bot, call, new_reservation)
            elif prev_state == BotStates.state_my_reservation.name:
                self.set_state(call.from_user.id, BotStates.state_my_reservation_list)
                self.show_my_reservations(call)
        else:
            print('Unknown callback')
