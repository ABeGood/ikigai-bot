from typing import Dict, Tuple
import datetime
import pytz
from datetime import timedelta


admin_chat_id = -1002217216611
LOCAL_TIMEZONE = pytz.timezone('Europe/Prague')

reminder_thresholds_from_creation = [
    timedelta(minutes=60*24),
    timedelta(minutes=60*20),
    timedelta(minutes=60*6),
    timedelta(minutes=60*1),
]

reminder_thresholds_from_start = [
    timedelta(minutes=10),   # Delete threshold - delete reservation 5 mins before start
    timedelta(minutes=60*2),  # First warning 120 mins before start
    timedelta(minutes=20)   # Second warning 20 mins before start
]

admin_reminder_cooldown = timedelta(minutes=30)

stride_mins = 30
time_step = 30  # min
time_buffer_mins = 15

days_lookforward = 180

workday_start = datetime.time(9, 0) 
workday_end = datetime.time(21, 0)

places : Dict[str, Tuple[int, ...]] = {'h': (1, 2), 'b': (3,)}

prices_hair = { 1: 150.0,
                3: 360.0,
                12: 600.0}

prices_brows = {1: 130.0,
                3: 300.0,
                12: 500.0}

prices = {'h':prices_hair, 'b':prices_brows}

period_buttons = {
    'hour_1': (1, '🕐 1 час'),
    # 'hour_2': (2, '🕐 2 часа'),
    'hour_3': (3, '🕐 3 часа'),
    'day_1': (1*12, '1 день'),
    # 'day_7': (7*12, '7 дней'),
    'other': ('talk_to_admin', 'Другое/Связаться с администратором'),
}
