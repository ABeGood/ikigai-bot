from admin.app import app
from tg_bot.bot import TelegramBot
from db.connection import Database
from keys import keys

if __name__ == '__main__':

    reservations_db = Database()
    tg_bot = TelegramBot(bot_token=keys.token, reservations_db=reservations_db)
    tg_bot.bot.infinity_polling(skip_pending=True)

    # app.run(debug=True, port=5000)

