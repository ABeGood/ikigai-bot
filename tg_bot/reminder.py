import logging
from datetime import datetime, timedelta
import threading
from typing import Optional
from tg_bot import config, messages
from db.connection import Database


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
        self.reminder_thresholds = config.reminder_thresholds
        # Calculate check interval and threshold window
        self.check_interval = calculate_check_interval(self.reminder_thresholds) # TODO
        self.threshold_window = calculate_threshold_window(self.reminder_thresholds)
        self.last_admin_notification = None

        # Log the calculated values
        self.logger.info(f"Reminder system initialized with:")
        self.logger.info(f"- Check interval: {self.check_interval} minutes")
        self.logger.info(f"- Threshold window: {self.threshold_window.total_seconds()} seconds")

        self._stop_event = threading.Event()
        self._reminder_thread: Optional[threading.Thread] = None

    def get_user_reminder_message(self, reservation, reminder_level):
        """Generate reminder message based on level"""
        base_message = messages.format_user_reminder(reservation=reservation)

        urgency_messages = [
            "⚠️Пожалуйста, не забудьте оплатить вашу резервацию\\.",
            "‼️ Прошло 6 часов\\. Пожалуйста, оплатите резервацию для сохранения места\\.",
            "🚨 Важно: если оплата не поступит в течение следующих часов, резервация будет отменена\\.",
        ]

        # Create markup with button to view reservation
        markup = messages.get_user_reminder_keyboard(reservation.order_id)
        return base_message + urgency_messages[reminder_level], markup


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
            message, markup = self.get_user_reminder_message(reservation, reminder_level)
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


    def check_user_paiments(self):
        """Check unpaid reservations and send reminders"""
        try:
            current_time = datetime.now(config.LOCAL_TIMEZONE)
            unpaid_reservations = self.db.get_upcoming_unpaid_reservations()

            for reservation in unpaid_reservations:
                if self._stop_event.is_set():
                    break
                
                time_since_creation = current_time - reservation.created_at

                # Handle reservation deletion if past final threshold
                if time_since_creation > self.reminder_thresholds[0]:
                    self.delete_unpaid_reservation(reservation)
                    continue
                    
                # Send appropriate reminder based on time elapsed
                for i, threshold in enumerate(self.reminder_thresholds[1:][::-1]):
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
        
        for reservation in unconfirmed:
            try:
                self.bot.notify_admin(text = '', reservation=reservation)
                self.last_admin_notification = current_time
            except Exception as e:
                self.logger.error(f"Failed to send admin notification: {e}")


    def reminder_loop(self):
        """Main reminder loop that runs in a separate thread"""
        self.logger.info("Starting reminder system...")
        while not self._stop_event.is_set():
            self.check_user_paiments()
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
