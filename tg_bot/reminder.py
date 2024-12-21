import logging
from datetime import datetime, timedelta
import threading
from typing import Optional
from tg_bot import config, messages
from db.connection import Database
import pytz


# def calculate_check_interval(thresholds: list[timedelta]) -> int:
#     """
#     Calculate optimal check interval based on threshold gaps.
#     Returns interval in minutes.
#     """
#     if len(thresholds) < 2:
#         return 1  # AG: Bad!!!
    
#     # Find smallest gap between thresholds
#     gaps = []
#     for i in range(len(thresholds) - 1):
#         gap = (thresholds[i] - thresholds[i + 1]).total_seconds() / 60
#         gaps.append(gap)
    
#     # Use 1/3 of smallest gap, rounded down, minimum 1 minute
#     return max(1, int(min(gaps) / 3))


# def calculate_threshold_window(thresholds: list[timedelta]) -> timedelta:
#     """
#     Calculate optimal threshold window based on gaps.
#     Window should be small enough to not overlap between thresholds.
#     """
#     if len(thresholds) < 2:
#         return timedelta(seconds=30)
    
#     # Find smallest gap between thresholds
#     min_gap = float('inf')
#     for i in range(len(thresholds) - 1):
#         gap = (thresholds[i] - thresholds[i + 1]).total_seconds()
#         min_gap = min(min_gap, gap)
    
#     # Use 1/4 of smallest gap for window size (both sides combined)
#     window_seconds = int(min_gap / 4)
    
#     # Ensure window is at least 10 seconds and at most 30 seconds
#     return timedelta(seconds=max(10, min(30, window_seconds)))


def calculate_check_params(thresholds_from_creation: list[timedelta], 
                         thresholds_from_start: list[timedelta]) -> tuple[int, timedelta]:
    """
    Calculate optimal check interval and window considering both threshold types.
    Returns (check_interval_minutes, window).
    """
    # Calculate minimum gap for each list separately
    def get_min_gap(thresholds: list[timedelta]) -> float:
        if len(thresholds) < 2:
            return float('inf')
        gaps = []
        sorted_thresholds = sorted(thresholds, reverse=True)
        for i in range(len(sorted_thresholds) - 1):
            gap = (sorted_thresholds[i] - sorted_thresholds[i + 1]).total_seconds() / 60
            gaps.append(gap)
        return min(gaps) if gaps else float('inf')

    # Get minimum gap from both lists
    min_gap_creation = get_min_gap(thresholds_from_creation)
    min_gap_start = get_min_gap(thresholds_from_start)
    
    # Use the smaller of the two minimum gaps
    absolute_min_gap = min(min_gap_creation, min_gap_start)
    
    # Check interval should be small enough to not miss any threshold
    check_interval = max(1, int(absolute_min_gap / 3))
    
    # Window should be small enough to not overlap between closest thresholds
    window_seconds = int((absolute_min_gap * 60) / 4)  # Convert minutes to seconds
    threshold_window = timedelta(seconds=max(10, min(30, window_seconds)))
    
    return check_interval, threshold_window


class ReminderSystem:
    """Handles payment reminders and reservation cleanup"""
    
    def __init__(self, telegram_bot):
        """
        Initialize reminder system with the existing bot instance
        
        Args:
            telegram_bot: The main TelegramBot instance
        """
        self.logger = logging.getLogger(__name__)
        self.db : Database = telegram_bot.reservations_db
        self.bot = telegram_bot
        
        # Get thresholds from config
        self.reminder_thresholds_from_creation = config.reminder_thresholds_from_creation
        self.reminder_thresholds_from_start = config.reminder_thresholds_from_start

        # self.check_interval, self.threshold_window = calculate_check_params(
        #     self.reminder_thresholds_from_creation,
        #     self.reminder_thresholds_from_start
        # )

        self.check_interval, self.threshold_window = 10, timedelta(minutes=6)

        self.last_admin_notification = None
        self._stop_event = threading.Event()
        self._reminder_thread: Optional[threading.Thread] = None

        # Log the calculated values
        self.logger.info(f"Reminder system initialized with:")
        self.logger.info(f"- Check interval: {self.check_interval} minutes")
        self.logger.info(f"- Threshold window: {self.threshold_window.total_seconds()} seconds")

    # TODO
    def get_user_reminder_from_creation_message(self, reservation, reminder_level):
        """Generate reminder message based on level"""
        base_message = messages.format_user_reminder(reservation=reservation)

        urgency_messages = [
            "⚠️Пожалуйста, не забудьте оплатить вашу резервацию.",
            "‼️ Прошло 6 часов. Пожалуйста, оплатите резервацию для сохранения места.",
            "🚨 Важно: если оплата не поступит в течение следующих часов, резервация будет отменена.",
        ]

        # Create markup with button to view reservation
        markup = messages.get_user_reminder_keyboard(reservation.order_id)
        message = base_message + '\n\n' + urgency_messages[reminder_level]
        return message, markup

    def get_user_reminder_from_start_message(self, reservation, warning_level):
        """Generate warning message based on time remaining until start"""
        base_message = messages.format_reservation_recap(reservation)
        
        urgency_messages = [
            "⚠️ До начала вашей резервации осталось 2 часа. \nПожалуйста, оплатите бронирование сейчас.",
            "🚨 Важно \n\nДо начала вашей резервации осталось 30 минут! \n\nРезервация будет отменена через 10 минут, если оплата не поступит."
        ]
        
        markup = messages.get_user_reminder_keyboard(reservation.order_id)
        message = urgency_messages[warning_level] + '\n\n' + base_message
        return message, markup

    def should_send_user_reminder(self, time_passed: timedelta, threshold: timedelta) -> bool:
        """
        Check if we should send a reminder for this threshold.
        Returns True if time_passed is within threshold_window of the threshold.
        """
        window_start = threshold - self.threshold_window
        window_end = threshold + self.threshold_window
        return window_start <= time_passed <= window_end


    def send_user_reminder(self, reservation, reminder_level) -> bool:
        """Send payment reminder to user"""
        try:
            message, markup = self.get_user_reminder_from_creation_message(reservation, reminder_level)
            self.bot.bot.send_message(
                chat_id=reservation.telegram_id,
                text=message,
                parse_mode='MARKDOWN',
                reply_markup=markup
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to send reminder for reservation {reservation.order_id}: {e}")
            return False


    def check_time_to_start(self, reservation, current_time):
        """Check time remaining until reservation start and handle notifications"""
        if reservation.payed:
            return False
            
        time_to_start = reservation.time_from.replace(tzinfo=config.LOCAL_TIMEZONE) - current_time
        
        # Check deletion threshold first (10 mins before start)
        if time_to_start <= self.reminder_thresholds_from_start[0]:
            self.delete_unpaid_reservation(reservation)
            # TODO: notify admin
            return True
        
        # Check warning thresholds
        for i, threshold in enumerate(self.reminder_thresholds_from_start[1:]):
            if self.should_send_user_reminder(time_to_start, threshold):
                message, markup = self.get_user_reminder_from_start_message(reservation, i)
                self.bot.bot.send_message(
                    chat_id=reservation.telegram_id,
                    text=message,
                    parse_mode='MARKDOWN',
                    reply_markup=markup
                )
                return True
                
        return False


    def delete_unpaid_reservation(self, reservation) -> bool:
        """Delete unpaid reservation and notify user"""
        try:
            if self.db.delete_reservation(reservation.order_id):
                text=messages.format_reservation_deleted(reservation=reservation)
                self.bot.bot.send_message(
                    chat_id=reservation.telegram_id,
                    text=text,
                    parse_mode='MARKDOWN'
                )
                return True
            else:
                self.logger.error(f"Failed to delete reservation {reservation.order_id}: DB returned None.")
                return False
        except Exception as e:
            self.logger.error(f"Exception while reservation deletion {reservation.order_id}: {e}")
            return False


    def check_reservations(self):
        """Check unpaid reservations and send reminders"""
        try:
            current_time = datetime.now(config.LOCAL_TIMEZONE)
            unpaid_reservations = self.db.get_upcoming_unpaid_reservations()

            for reservation in unpaid_reservations:
                if self._stop_event.is_set():
                    break

                # First check time-to-start conditions
                if self.check_time_to_start(reservation, current_time):
                    continue  # Skip regular reminder checks if we handled a time-to-start condition

                time_since_creation = current_time - reservation.created_at

                # Handle reservation deletion if past final threshold
                if time_since_creation > self.reminder_thresholds_from_creation[0]:
                    self.delete_unpaid_reservation(reservation)
                    # TODO: notify admin
                    continue
                    
                # Send appropriate reminder based on time elapsed
                for i, threshold in enumerate(self.reminder_thresholds_from_creation[1:][::-1]):
                    if self.should_send_user_reminder(time_since_creation, threshold):
                        self.send_user_reminder(reservation, i)
                        break

        except Exception as e:
            self.logger.error(f"Error in check_user_paiments(): {e}")


    def check_admin_unconfirmed_payments(self):
        """Check for paid but unconfirmed reservations and notify admin"""
        current_time = datetime.now(config.LOCAL_TIMEZONE)
        
        # Get reservations with unconfirmed payments
        unconfirmed = self.db.get_paid_unconfirmed_reservations()
        if not unconfirmed:
            return
        
        # Only notify admin if it's been more than 30 minutes since last notification
        if (self.last_admin_notification is None or 
            current_time - self.last_admin_notification > config.admin_reminder_cooldown):
            try:
                for reservation in unconfirmed:
                    self.bot.notify_admin(text='', reservation=reservation
                    )
                self.last_admin_notification = current_time
            except Exception as e:
                self.logger.error(f"Failed to send admin notification: {e}")


    def reminder_loop(self):
        """Main reminder loop that runs in a separate thread"""
        self.logger.info("Starting reminder system...")
        while not self._stop_event.is_set():
            self.check_reservations()
            self.check_admin_unconfirmed_payments()
            # Sleep for the check interval, but check stop_event periodically
            self._stop_event.wait(timeout=self.check_interval * 60)


    def start(self):
        """Start the reminder system in a separate thread"""
        if self._reminder_thread is None or not self._reminder_thread.is_alive():
            self._stop_event.clear()
            self._reminder_thread = threading.Thread(target=self.reminder_loop)
            self._reminder_thread.daemon = True  # Thread will stop when main program exits
            self._reminder_thread.start()
            self.logger.info("Reminder system started")


    def stop(self):
        """Stop the reminder system"""
        if self._reminder_thread and self._reminder_thread.is_alive():
            self._stop_event.set()
            self._reminder_thread.join()
            self.logger.info("Reminder system stopped")
