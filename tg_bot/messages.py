from classes.classes import Reservation
import datetime
from datetime import date, time
import pytz
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton


# Message texts
WELCOME_MESSAGE = 'Добро пожалоть в Ikigai бот! 🎉'
SELECT_WORKPLACE_MESSAGE = 'Какое рабочее место Вам нужно?'
SELECT_TIME_MESSAGE = 'Сколько времени вам нужно?'
SELECT_DATE_MESSAGE = 'Выберете подходящий для вас день.'
SELECT_TIME_SLOT_MESSAGE = 'Выбетере подходящее для вас время.'
SELECT_SEAT_MESSAGE = 'Выберете рабочее место.'


INFO_MESSAGE = '''*Beauty Coworking Ikigai* - это рабочее пространство для профессионалов индустрии красоты.\n\n
- Мы предоставляем удобные и функциональные рабочие места для визажистов, бровистов и стилистов, которые ценят комфорт и качество в своей работе.\n
- Мы создали Beauty Coworking с целью поддерживать начинающих предпринимателей в их деловом росте.\n
- Наша миссия - предоставить доступное и функциональное пространство для работы и развития вашего бизнеса в области красоты.\n
*Присоединяйтесь к Beauty Coworking ikigai* и обеспечьте себе идеальное рабочее окружение для достижения профессиональных целей в индустрии красоты.
'''

MY_RESERVATIONS_MESSAGE = 'Ваши резервации:'
MY_RESERVATIONS_MESSAGE_NO_RESERVATIONS = 'У Вас пока нет ни одной активной резервации.'
RESERVATION_NOT_FOUND_MESSAGE = "Резервация не найдена..."

ADMIN_CHAT_MESSAGE = 'Оставьте свое сообщение здесь и мы перешлем его администратору.'
PATMENT_CONFIRM_REQUEST = 'Пожалуйста, пришлите нам подтверждение об оплате. Это может быть скриншот с суммой и адресом перевода.'

# Button texts
NEW_RESERVATION_BUTTON = '🆕 Новая резервация'
MY_RESERVATIONS_BUTTON = '🆕 Мои резервации'
ABOUT_US_BUTTON = '⏺️ О нас'
BACK_BUTTON = '🔙 Назад'
PAY_NOW_BUTTON = 'Оплатить 🪙'
CHANGE_PAYCHECK_BUTTON = 'Изменить чек 🪙'
PAY_LINK_BUTTON = 'Ссылка для оплаты 🪙'
PAY_DONE_BUTTON = 'Готово ✅'
PAY_URL = 'http://revolut.me/yuliyagb1b'
PAY_LATER_BUTTON = 'Оплатить позже ⌛'
CANCEL_RESERVATION_BUTTON = 'Отменить резервацию'

# Time slot buttons
ONE_HOUR_BUTTON = '🕐 1 час'
TWO_HOURS_BUTTON = '🕐 2 часа'
THREE_HOURS_BUTTON = '🕐 3 часа'
SIX_HOURS_BUTTON = '🕐 6 часов (полдня)'
OTHER_HOURS_BUTTON = 'Other...'

# Workplace types
HAIRSTYLE_BUTTON = 'Hairstyle'
BROWS_BUTTON = 'Brows'


def escape_markdown(text: str) -> str:
    """Escape Markdown special characters"""
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    
    escaped_text = text
    for char in special_chars:
        escaped_text = escaped_text.replace(char, f'\{char}')
    return escaped_text


# WTF? Why here?
def format_reservation_recap(reservation: Reservation):
    return f'''📆 *Ваша резервация*:

Дата     : *{reservation.day.strftime('%d.%m.%Y')}*
Время  : *{reservation.time_from.strftime('%H:%M')}* - *{reservation.time_to.strftime('%H:%M')}*
Место  : *{reservation.place}*
Сумма : *{reservation.sum}* CZK
'''


def format_pay_from_recap(sum: float):
    return f'''Мы принимаем оплату через онлайн-банк *Revolut*.

*Сумма*: *{sum}* CZK

После оплаты, пожалуйста, *пришлите нам подтверждение*. Это может быть скриншот с суммой и адресом перевода.

Спасибо! ✨
'''


def format_pay_from_my_reservations(sum: float):
    return f'''Мы принимаем оплату через онлайн-банк *Revolut*.

*Сумма*: *{sum}* CZK

После оплаты, пожалуйста, *пришлите нам подтверждение*. Это может быть скриншот с суммой и адресом перевода.

Спасибо! ✨
'''

def format_change_paycheck():
    return f'''Если вы хотите заменить чек для этой резервации просто пришлите ешо сюда!\n
Спасибо! ✨
'''


def format_reservation_created(reservation: Reservation):
    return f'''🎉 *Ваша резервация подтверждена и ждет оплаты!*

*Дата  :* {reservation.day.strftime('%d.%m.%Y')}
*Время :* {reservation.time_from.strftime('%H:%M')} - {reservation.time_to.strftime('%H:%M')}
*Место :* {reservation.place}

До встречи!
'''

# def format_reservation_created_admin_notification(reservation: Reservation):
#     return f'''
# ❇️ New reservation:
# Client: {reservation.name} ({reservation.telegram_id})
# Day: {reservation.day.strftime('%d.%m.%Y')}
# Time: {reservation.time_from.strftime('%H:%M')} - {reservation.time_to.strftime('%H:%M')} ({reservation.period} hours)
# {'⚠️ not payed' if not reservation.payed else '✅ payed'}
# '''

def format_reservation_created_admin_notification(reservation: Reservation):
    user_link = f'[{reservation.name}](tg://user?id={reservation.telegram_id})'
    
    return f'''
❇️ *New reservation*

Client :  {user_link}
Day     :  {reservation.day.strftime('%d.%m.%Y')}
Time   :  {reservation.time_from.strftime('%H:%M')} - {reservation.time_to.strftime('%H:%M')} ({reservation.period} hours)
Sum    :  {reservation.sum} CZK

'''

def format_reservation_deleted_admin_notification(reservation: Reservation):
    user_link = f'[{reservation.name}](tg://user?id={reservation.telegram_id})'
    
    # int(reservation.period)  <- Kostyl
    return f'''
❌ *Reservation deleted*

Client  : {user_link}
Day     : {reservation.day.strftime('%d.%m.%Y')}
Time    : {reservation.time_from.strftime('%H:%M')} - {reservation.time_to.strftime('%H:%M')} ({int(reservation.period)} hours)
Sum     : {reservation.sum} CZK
Order ID: `{reservation.order_id}`
{'✅ Was not payed' if not reservation.payment_confirmation_file_id else '⚠️ Was payed'}

'''

def format_reservation_created_and_payed(reservation: Reservation):
    return f'''✅ *Ваша резервация оплачена и подтверждена!*

*Дата  :* {reservation.day.strftime('%d.%m.%Y')}
*Время :* {reservation.time_from.strftime('%H:%M')} - {reservation.time_to.strftime('%H:%M')}
*Место :* {reservation.place}

До встречи! ✨
'''


def format_reservation_confirmed_by_admin(reservation: Reservation, action:str):
    if action == 'confirm':
        return f'''✅ *Ваша резервация оплачена и подтверждена!*

*Дата  :* {reservation.day.strftime('%d.%m.%Y')}
*Время :* {reservation.time_from.strftime('%H:%M')} - {reservation.time_to.strftime('%H:%M')}
*Место :* {reservation.place}

До встречи! ✨
'''
    elif action == 'reject':
        return f'''🔔 Ваше подтверждение оплаты было отклонено.

Пожалуйста, убедитесь, что сумма и получатель платежа верны, и отправьте новое подтверждение.

*Дата   :* {reservation.day.strftime('%d.%m.%Y')}
*Время :* {reservation.time_from.strftime('%H:%M')} - {reservation.time_to.strftime('%H:%M')}
*Место :* {reservation.place}
*Сумма :* {reservation.sum} CZK

Спасибо! ✨
'''


def format_user_reminder(reservation: Reservation):
    return f"""🔔 *Напоминание об оплате*

*Дата:* {reservation.day.strftime('%d.%m.%Y')}
*Время:* {reservation.time_from.strftime('%H:%M')} - {reservation.time_to.strftime('%H:%M')}
*Место:* {reservation.place}
*Сумма:* {str(reservation.sum)} CZK"""


def format_reservation_deleted(reservation: Reservation):

    return f"""🔔 *Ваша резервация была отменена*
Причина: отсутствие оплаты.

*Резервация:*
*Дата:* {reservation.day.strftime('%d.%m.%Y')}
*Время:* {reservation.time_from.strftime('%H:%M')} - {reservation.time_to.strftime('%H:%M')}
*Место:* {reservation.place}
*Сумма:* {str(reservation.sum)} CZK
"""


def format_payment_confirm_receive(reservation: Reservation):   # TODO
    return f'''⌛ Спасибо! 

Мы проверим платеж и подтвердим вашу резервацию ({reservation.order_id}).
'''

def format_payment_confirm_receive_admin_notification(reservation: Reservation):   # TODO: 1. Add payment photo, 2. Confirm from tg
    user_link = f'[{reservation.name}](tg://user?id={reservation.telegram_id})'

    return f'''
💳 Payment confirmation received:

*Client*: {user_link}
*Date*: {reservation.day.strftime('%d.%m.%Y')}
*Time*: {reservation.time_from.strftime('%H:%M')} - {reservation.time_to.strftime('%H:%M')} ({reservation.period}) hours)
*Place*: {reservation.place}
*Sum*: {reservation.sum} CZK
'''

def format_payment_admin_action(reservation: Reservation):   # TODO: 1. Add payment photo, 2. Confirm from tg
    user_link = f'[{reservation.name}](tg://user?id={reservation.telegram_id})'

    return f'''
*Client*: {user_link}
*Date*: {reservation.day.strftime('%d.%m.%Y')}
*Time*: {reservation.time_from.strftime('%H:%M')} - {reservation.time_to.strftime('%H:%M')} ({reservation.period} hours)
*Place*: {reservation.place}
*Sum*: {reservation.sum} CZK
'''

def format_wait_to_confirm_admin_notification(reservation: Reservation) -> str | None:
    """Format notification message for admin about unconfirmed payments"""
    if not reservation:
        return None
    
    user_link = f'[{reservation.name}](tg://user?id={reservation.telegram_id})'
        
    return f'''🔔 Payments awaiting confirmation:

*Client*: {user_link}
*Date*: {reservation.day.strftime('%d.%m.%Y')}
*Time*: {reservation.time_from.strftime('%H:%M')} - {reservation.time_to.strftime('%H:%M')} ({reservation.period} hours)
*Place*: {reservation.place}
*Sum*: {reservation.sum} CZK
'''

def format_no_pending_payments():
    return f'''❓ У вас нет бронирований, ожидающих подтверждения оплаты.\n
Если вы хотите отправить новое подтверждение оплаты для какого-то из ваших бронирований, это можно сделать в меню *"Мои резервации"*.
'''

def format_multiple_pending_payments():
    return f'''❓ У вас несколько бронирований, ожидающих подтверждения оплаты.\n
Пожалуйста, выберете к какому бронированию относится этот платеж в меню *"Мои резервации"*
'''

def get_status_string(reservation: Reservation):
    # Set status emoji based on payment 
    if reservation.payed:
        return "✅ Оплачено"
    else:
        if reservation.payment_confirmation_link and reservation.payment_confirmation_file_id:
            status = "⌛ Ожидает подтверждения оплаты администратором"
        elif not reservation.payment_confirmation_link and reservation.payment_confirmation_file_id:
            status = "❌ Оплата отклонена"
        elif not reservation.payment_confirmation_link:
            status = "💳 Ожидает оплаты"
        
    return status

def format_reservation_info(reservation: Reservation):
    return f"""
{get_status_string(reservation)}

*День*: {reservation.day.strftime('%d.%m.%Y')}
*Время*: {reservation.time_from.strftime('%H:%M')} - {reservation.time_to.strftime('%H:%M')}
*Место*: {reservation.place}
*Сумма*: {reservation.sum}
"""

def get_admin_payment_keyboard(reservation_id: str) -> InlineKeyboardMarkup:
    """Create keyboard for admin payment confirmation"""
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(
        InlineKeyboardButton("✅ Подтвердить", callback_data=f'confirm_payment_{reservation_id}'),
        InlineKeyboardButton("❌ Отклонить", callback_data=f'reject_payment_{reservation_id}')
    )
    return markup


def get_user_reminder_keyboard(reservation_id: str) -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(
        "Перейти к резервации",
        callback_data=f"view_reservation_{reservation_id}"
    ))
    return markup


def localize_from_db(dt):
    """Convert UTC datetime from DB to local timezone"""
    if dt is None:
        return None
    
    if isinstance(dt, datetime):
        # Convert UTC datetime to local timezone
        if dt.tzinfo is None:
            dt = pytz.UTC.localize(dt)
        return dt.astimezone(pytz.timezone('UTC'))
    elif isinstance(dt, date):
        # Only date, no timezone conversion needed
        return dt
    return dt

def prepare_for_db(dt, day=None):
    """Convert local time/datetime to UTC datetime for DB storage"""
    if dt is None:
        return None
        
    if isinstance(dt, datetime):
        # If datetime has no timezone, assume it's in local timezone
        if dt.tzinfo is None:
            dt = pytz.timezone('UTC').localize(dt)
        # Convert to UTC for storage
        return dt.astimezone(pytz.UTC)
    elif isinstance(dt, time):
        # Convert time to datetime using the provided day or current day
        if day is None:
            day = date.today()
        dt_combined = datetime.datetime.combine(day, dt)
        if dt_combined.tzinfo is None:
            dt_combined = pytz.timezone('UTC').localize(dt_combined)
        return dt_combined.astimezone(pytz.UTC)
    return dt