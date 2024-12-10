from admin.app import app
from tg_bot.bot import TelegramBot
# from requests.exceptions import ConnectionError, ReadTimeout
from db.connection import Database
from dotenv import load_dotenv
import os

if __name__ == '__main__':

    load_dotenv()

    # app.run(debug=True, port=5000)

    reservations_db = Database()
    tg_bot = TelegramBot(bot_token=os.environ.get('BOT_TOKEN'), reservations_db=reservations_db)

    tg_bot.run_bot()

    # AG TODO: pending_payment_reservation must be deleted from bot's state data on polling timeout

