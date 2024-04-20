import logging

from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.ext import ConversationHandler
from telegram_bot_calendar import DetailedTelegramCalendar, LSTEP, WMonthTelegramCalendar


logging.basicConfig(filename='basic.log',encoding='utf-8', 
                    level=logging.DEBUG, 
                    filemode = 'w', 
                    format='%(process)d-%(levelname)s-%(message)s') 

logger = logging.getLogger(__name__)

logger.debug('start')


MAIN_MENU, \
RESERVATION_MENU, \
INFO, \
RESERVATION_MENU_TYPE, \
RESERVATION_MENU_N_OF_HOURS, \
RESERVATION_MENU_DAY, \
RESERVATION_MENU_TIME, \
RESERVATION_DONE \
= range(8)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Sends the initial greeting to the user and sets up the game.

    :param update: An object that contains all the incoming update data.
    :param context: A context object containing information for the callback function.
    :return: The next state for the conversation.
    """

    reply_keyboard = reply_keyboard = [['🆕 Новая резервация'], 
                                       ['⏺️ О нас']]

    await update.message.reply_text(
        text='Welcome to Ikigai bot! 🎉',
        parse_mode='HTML',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, 
            one_time_keyboard=True
        ),
    )
    return MAIN_MENU


async def reservation_menu_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handles the first question of the game.

    :param update: An object that contains all the incoming update data.
    :param context: A context object containing information for the callback function.
    :return: The next state for the conversation.
    """
    reply_keyboard = [['Hairstyle', 'Brow master']]
    await update.message.reply_text(
        "Выберете вашу специальность",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True
        ),
    )
    return RESERVATION_MENU

async def reservation_menu_n_of_hours(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handles the first question of the game.

    :param update: An object that contains all the incoming update data.
    :param context: A context object containing information for the callback function.
    :return: The next state for the conversation.
    """

    reply_keyboard = [[InlineKeyboardButton('🕐 1 час', callback_data='1_hour')], 
                      ['🕐 2 часа'], 
                      ['🕐 3 часа'], 
                      ['🕐 6 часов (полдня)']]
    await update.message.reply_text(
        "Выберете период на который вы хотите забронировать рабочее место.",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True
        ),
    )
    return RESERVATION_MENU_N_OF_HOURS


async def reservation_menu_day(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handles the first question of the game.

    :param update: An object that contains all the incoming update data.
    :param context: A context object containing information for the callback function.
    :return: The next state for the conversation.
    """
    calendar, step = DetailedTelegramCalendar().build()

    await update.message.reply_text(
            "Выберете день, в который вы хотите забронировать рабочее место.",
            reply_markup=calendar
        )
    
    return RESERVATION_MENU_DAY


async def reservation_menu_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handles the first question of the game.

    :param update: An object that contains all the incoming update data.
    :param context: A context object containing information for the callback function.
    :return: The next state for the conversation.
    """
    reply_keyboard = [['🕐ысиви'], 
                      ['смртпа'], 
                      ['смпрта'], 
                      ['смптр']]
    await update.message.reply_text(
        "Выберете TIME вы хотите забронировать рабочее место.",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True
        ),
    )
    return RESERVATION_MENU_TIME


async def reservation_menu_recap(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handles the first question of the game.

    :param update: An object that contains all the incoming update data.
    :param context: A context object containing information for the callback function.
    :return: The next state for the conversation.
    """
    await update.message.reply_text(
        "DONE ✅",
    )
    return RESERVATION_DONE


async def info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handles the first question of the game.

    :param update: An object that contains all the incoming update data.
    :param context: A context object containing information for the callback function.
    :return: The next state for the conversation.
    """
    reply_keyboard = [['BACK']]
    await update.message.reply_text(
        "Some info",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True
        ),
    )
    return INFO


async def calendarCallback(update, context):


    result, key, step = DetailedTelegramCalendar().process(update.callback_query)
    if not result and key:
        update.edit_message_text(f"Select {LSTEP[step]}",
                              update.message.chat.id,
                              update.message.message_id,
                              reply_markup=key)
    elif result:
        update.edit_message_text(f"You selected {result}",
                              update.message.chat.id,
                              update.message.message_id)
        

    # query = update.callback_query
    # print('query.data:', query)
    # await query.answer(f'selected: {query.data}')

    # reply_keyboard = [['🕐ысиви'], 
    #                   ['смртпа'], 
    #                   ['смпрта'], 
    #                   ['смптр']]
    # await update.effective_message.reply_text(  # update.message == None
    #     "Выберете TIME вы хотите забронировать рабочее место.",
    #     reply_markup=ReplyKeyboardMarkup(
    #         reply_keyboard, one_time_keyboard=True
    #     ),
    # )


    # return RESERVATION_MENU_TIME




async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Ends the conversation when the user sends /cancel.

    :param update: An object that contains all the incoming update data.
    :param context: A context object containing information for the callback function.
    :return: The next state for the conversation, which is ConversationHandler.END in this case.
    """
    user = update.message.from_user
    await update.message.reply_text(
        "Досвидания.", reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END