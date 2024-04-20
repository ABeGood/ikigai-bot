# https://github.com/AMRedichkina/EngBuddyBot/blob/main/bot/dialog.py
# https://github.com/python-telegram-bot/python-telegram-bot/blob/master/examples/conversationbot.py

import config
from telegram.ext import ApplicationBuilder, CommandHandler
from telegram.ext import filters, MessageHandler
from telegram.ext import ConversationHandler, CallbackQueryHandler

# from commands import start, info
from dialog import *


if __name__ == '__main__':
    app = ApplicationBuilder().token(config.token).build()

    # start_handler = CommandHandler('start', start)
    # info_handler = CommandHandler('info', info)


    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MAIN_MENU: [
                MessageHandler(filters.Regex("^(🆕 Новая резервация)$"), reservation_menu_type),
                MessageHandler(filters.Regex("^(⏺️ О нас)$"), info)
                ],

            RESERVATION_MENU: [
                MessageHandler(filters.Regex("^(Hairstyle|Brow master)$"), reservation_menu_n_of_hours)
                ],

            RESERVATION_MENU_N_OF_HOURS: [
                MessageHandler(filters.Regex("^(🕐 1 час|🕐 2 часа|🕐 3 часа|🕐 6 часов (полдня))$"), reservation_menu_day)
                ],

            RESERVATION_MENU_DAY: [
                # MessageHandler(filters=None, callback=reservation_menu_time)
                CallbackQueryHandler(callback=calendarCallback)
            ],

            RESERVATION_MENU_TIME: [
                MessageHandler(filters=None, callback=reservation_menu_recap)
            ],

            RESERVATION_DONE: [
                MessageHandler(filters=None, callback=start)
            ],

            INFO: [MessageHandler(filters=None, callback=start)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # conv_handler = ConversationHandler(
    #     entry_points=[CommandHandler('reservation_type', greeting)],
    #     states={
    #         GREETING: [MessageHandler(filters.Regex("^(Новая резервация|О нас|...)$"), reservation_period)],
    #         RESERVATION_PERIOD: [MessageHandler(filters.Regex("^(3 часа|1 день|1 неделя|Другое)$"), None)],
    #     },
    #     fallbacks=[CommandHandler("cancel", cancel)]
    # )


    # app.add_handler(start_handler)
    # app.add_handler(info_handler)
    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(calendarCallback))



    app.run_polling()