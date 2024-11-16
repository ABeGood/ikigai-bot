from typing import Dict, Tuple
import datetime

stride_mins = 30
time_step = 30  # min
time_buffer_mins = 25

closest_slot_start_min_buffer = 0

days_lookforward = 180

workday_start = datetime.time(9, 0) 
workday_end = datetime.time(21, 0)

places : Dict[str, Tuple[int, ...]] = {'b': (1, 2, 3), 'h': (1, 2)}

period_buttons = {
    'hour_1': (1, '🕐 1 час'),
    # 'hour_2': (2, '🕐 2 часа'),
    'hour_3': (3, '🕐 3 часа'),
    'day_1': (1*12, '1 день'),
    # 'day_7': (7*12, '7 дней'),
    'other': ('talk_to_admin', 'Другое/Связаться с администратором'),
}

admin_chat_id = -1002217216611
LOCAL_TIMEZONE = 'Europe/Prague'