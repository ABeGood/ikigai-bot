import asyncio
import logging
from datetime import datetime, timedelta
import pytz
import os
from dotenv import load_dotenv
import threading
from typing import Optional
from telebot.types import Message
from telegram.constants import ParseMode
from tg_bot import config
from db.connection import Database


class ReminderSystem:
    """Handles payment reminders and reservation cleanup"""
    
    def __init__(self, telegram_bot):
        """
        Initialize reminder system with the existing bot instance
        
        Args:
            telegram_bot: The main TelegramBot instance
        """
        self.telegram_bot = telegram_bot
        self.db : Database = telegram_bot.reservations_db
        self.logger = logging.getLogger(__name__)
        self.bot = telegram_bot
        
        # Get thresholds from config
        self.reminder_thresholds = config.reminder_thresholds
        # Calculate check interval and threshold window
        # self.check_interval = config.calculate_check_interval(self.reminder_thresholds)
        self.check_interval = 7
        self.threshold_window = config.calculate_threshold_window(self.reminder_thresholds)
        self.last_admin_notification = None

        # Log the calculated values
        self.logger.info(f"Reminder system initialized with:")
        self.logger.info(f"- Check interval: {self.check_interval} minutes")
        self.logger.info(f"- Threshold window: {self.threshold_window.total_seconds()} seconds")

        self._stop_event = threading.Event()
        self._reminder_thread: Optional[threading.Thread] = None

    def get_reminder_message(self, reservation, reminder_level) -> str:
        """Generate reminder message based on level"""
        base_message = (
            "⚠️ *Напоминание об оплате*\n\n"
            f"*Дата:* {reservation.day.strftime('%d.%m.%Y')}\n"
            f"*Время:* {reservation.time_from.strftime('%H:%M')} - {reservation.time_to.strftime('%H:%M')}\n"
            f"*Место:* {reservation.place}\n"
            f"*Сумма:* {reservation.sum} CZK\n\n"
        )

        urgency_messages = [
            "🚨 Важно: если оплата не поступит в течение следующих часов, резервация будет отменена.",
            "‼️ Прошло 6 часов. Пожалуйста, оплатите резервацию для сохранения места.",
            "⚠️Пожалуйста, не забудьте оплатить вашу резервацию.",
        ]

        return base_message + urgency_messages[reminder_level]

    
    def should_send_reminder(self, time_passed: timedelta, threshold: timedelta) -> bool:
        """
        Check if we should send a reminder for this threshold.
        Returns True if time_passed is within threshold_window of the threshold.
        """
        window_start = threshold - self.threshold_window
        window_end = threshold + self.threshold_window
        return window_start <= time_passed <= window_end

    def send_reminder(self, reservation, reminder_level) -> bool:
        """Send payment reminder to user"""
        try:
            message = self.get_reminder_message(reservation, reminder_level)
            self.bot.notify_admin(text=message)
            return True
        except Exception as e:
            self.logger.error(f"Failed to send reminder for reservation {reservation.order_id}: {e}")
            return False

    def delete_unpaid_reservation(self, reservation) -> bool:
        """Delete unpaid reservation and notify user"""
        try:
            self.db.delete_reservation(reservation.order_id)
            text=(
                "❌ *Ваша резервация была отменена*\n\n"
                f"Дата: {reservation.day.strftime('%d.%m.%Y')}\n"
                f"Время: {reservation.time_from.strftime('%H:%M')} - {reservation.time_to.strftime('%H:%M')}\n"
                f"Место: {reservation.place}\n\n"
                "Причина: отсутствие оплаты в течение 24 часов."
            )
            self.bot.notify_admin(text=text)
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete reservation {reservation.order_id}: {e}")
            return False

    def check_user_paiments(self):
        """Check unpaid reservations and send reminders"""
        try:
            current_time = datetime.now(config.LOCAL_TIMEZONE)
            unpaid_reservations = self.db.get_upcoming_reservations_without_payment()

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
                    if self.should_send_reminder(time_since_creation, threshold):
                        self.send_reminder(reservation, i)
                        break

        except Exception as e:
            self.logger.error(f"Error in reminder process: {e}")

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