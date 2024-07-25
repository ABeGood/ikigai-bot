from typing import Dict, Tuple
import datetime

stride_mins = 30
time_step = 30  # min
time_buffer_mins = 25

closest_slot_start_min_buffer = 0

days_lookforward = 180

workday_start = datetime.time(9, 0) 
workday_end = datetime.time(21, 0)

places : Dict[str, Tuple[int, ...]] = {'b': (1, 2), 'h': (3, 4, 5, 6)}