from classes.classes import Reservation
import datetime
from datetime import date, time
import pytz


# Message texts
WELCOME_MESSAGE = 'Welcome to Ikigai bot! 🎉'
SELECT_WORKPLACE_MESSAGE = 'Какое рабочее место Вам нужно?'
SELECT_TIME_MESSAGE = 'How much time do you need?'
SELECT_DATE_MESSAGE = 'Выберете подходящий для вас день:'
SELECT_TIME_SLOT_MESSAGE = 'Выбетере подходящее для вас время'
SELECT_SEAT_MESSAGE = 'Выберете рабочее место.'


INFO_MESSAGE = '''*Beauty Coworking ikigai* - это рабочее пространство для профессионалов индустрии красоты. 

- Мы предоставляем удобные и функциональные рабочие места для визажистов, бровистов и стилистов, которые ценят комфорт и качество в своей работе.

- Мы создали Beauty Coworking с целью поддерживать начинающих предпринимателей в их деловом росте.

- Наша миссия - предоставить доступное и функциональное пространство для работы и развития вашего бизнеса в области красоты.

*Присоединяйтесь к Beauty Coworking ikigai* и обеспечьте себе идеальное рабочее окружение для достижения профессиональных целей в индустрии красоты.
'''


MY_RESERVATIONS_MESSAGE = 'Ваши резервации:'
MY_RESERVATIONS_MESSAGE_NO_RESERVATIONS = 'У Вас пока нет ни одной активной резервации.'
RESERVATION_NOT_FOUND_MESSAGE = "Резервация не найдена..."

ADMIN_CHAT_MESSAGE = 'Оставьте свое сообщение здесь и мы перешлем его администратору.'

# Button texts
NEW_RESERVATION_BUTTON = '🆕 Новая резервация'
MY_RESERVATIONS_BUTTON = '🆕 Мои резервации'
ABOUT_US_BUTTON = '⏺️ О нас'
BACK_BUTTON = '🔙 Назад'
PAY_NOW_BUTTON = 'Оплатить 🪙'
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


# WTF? Why here?
def format_reservation_recap(reservation: Reservation):
    return f'''*Ваша резервация:*
*Дата:* {reservation.day.strftime('%d.%m.%Y')}
*Время:* {reservation.time_from.strftime('%H:%M')} - {reservation.time_to.strftime('%H:%M')}
*Место:* {reservation.place}
*Стоимость*: *666* CZK
'''


def format_prepay(sum: float):
    return f'''Мы принимаем оплату онлайн-банк *Revolut*.
- Кнопка *"Оплатить 🪙"* неренаправит Вас на *страницу оплаты*.
- *Сумма*: *{sum}* CZK
- После оплаты нажмите "Готово ✅".

Нам будет удобно, если в платеже Вы укажите *своё имя*.
Спасибо! ✨
'''


def format_reservation_confirm(reservation: Reservation):
    return f'''🎉 *Ваша резервация подтверждена и ждет оплаты!*
*Дата:* {reservation.day.strftime('%d.%m.%Y')}
*Время:* {reservation.time_from.strftime('%H:%M')} - {reservation.time_to.strftime('%H:%M')}
*Место:* {reservation.place}

До встречи!
'''

def format_reservation_confirm_and_payed(reservation: Reservation):
    return f'''🎉 *Ваша резервация подтверждена и оплачена!*
*Дата:* {reservation.day.strftime('%d.%m.%Y')}
*Время:* {reservation.time_from.strftime('%H:%M')} - {reservation.time_to.strftime('%H:%M')}
*Место:* {reservation.place}

До встречи!
'''

def format_reservation_info(day, time_from, time_to, place):
    return f"""
День: {day.strftime('%d.%m.%Y')}\n\
Время: {time_from.strftime('%H:%M')} - {time_to.strftime('%H:%M')}\n\
Место: {place}
"""

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
        dt_combined = datetime.combine(day, dt)
        if dt_combined.tzinfo is None:
            dt_combined = pytz.timezone('UTC').localize(dt_combined)
        return dt_combined.astimezone(pytz.UTC)
    return dt