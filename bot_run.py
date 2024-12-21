from tg_bot.bot import TelegramBot
from db.connection import Database
from dotenv import load_dotenv
import os

if __name__ == '__main__':
    load_dotenv()
    reservations_db = Database()
    tg_bot = TelegramBot(bot_token=os.environ.get('BOT_TOKEN'), reservations_db=reservations_db)
    tg_bot.run_bot()