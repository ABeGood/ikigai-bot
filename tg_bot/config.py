from typing import Dict, Tuple
import datetime
import pytz
from datetime import timedelta

reminder_thresholds = [
    timedelta(minutes=10),
    timedelta(minutes=7),
    timedelta(minutes=5),
    timedelta(minutes=3),
]

def calculate_check_interval(thresholds: list[timedelta]) -> int:
    """
    Calculate optimal check interval based on threshold gaps.
    Returns interval in minutes.
    """
    if len(thresholds) < 2:
        return 1  # AG: Bad!!!
    
    # Find smallest gap between thresholds
    gaps = []
    for i in range(len(thresholds) - 1):
        gap = (thresholds[i] - thresholds[i + 1]).total_seconds() / 60
        gaps.append(gap)
    
    # Use 1/3 of smallest gap, rounded down, minimum 1 minute
    return max(1, int(min(gaps) / 3))

def calculate_threshold_window(thresholds: list[timedelta]) -> timedelta:
    """
    Calculate optimal threshold window based on gaps.
    Window should be small enough to not overlap between thresholds.
    """
    if len(thresholds) < 2:
        return timedelta(seconds=30)
    
    # Find smallest gap between thresholds
    min_gap = float('inf')
    for i in range(len(thresholds) - 1):
        gap = (thresholds[i] - thresholds[i + 1]).total_seconds()
        min_gap = min(min_gap, gap)
    
    # Use 1/4 of smallest gap for window size (both sides combined)
    window_seconds = int(min_gap / 4)
    
    # Ensure window is at least 10 seconds and at most 30 seconds
    return timedelta(seconds=max(10, min(30, window_seconds)))

stride_mins = 30
time_step = 30  # min
time_buffer_mins = 25

closest_slot_start_min_buffer = 0

days_lookforward = 180

workday_start = datetime.time(9, 0) 
workday_end = datetime.time(21, 0)

places : Dict[str, Tuple[int, ...]] = {'b': (1, 2, 3), 'h': (1, 2)}
prices = {'h': 250, 'b': 250}

period_buttons = {
    'hour_1': (1, '🕐 1 час'),
    # 'hour_2': (2, '🕐 2 часа'),
    'hour_3': (3, '🕐 3 часа'),
    'day_1': (1*12, '1 день'),
    # 'day_7': (7*12, '7 дней'),
    'other': ('talk_to_admin', 'Другое/Связаться с администратором'),
}

admin_chat_id = -1002217216611
# LOCAL_TIMEZONE = 'Europe/Prague'
LOCAL_TIMEZONE = pytz.timezone('Europe/Prague')