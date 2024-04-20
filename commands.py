# from telegram import Update
# from telegram.ext import ContextTypes
# from telegram import Update, ReplyKeyboardMarkup


# async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

#     await context.bot.send_message(
#         chat_id=update.effective_chat.id,
#         text='Welcome to Ikigai bot...',
#         parse_mode='HTML'
#     )

#     reply_keyboard = [['Новая резервация'], ['О нас'], ['...']]
#     await update.message.reply_text(
#         "!@#!@%#$^",
#         reply_markup=ReplyKeyboardMarkup(
#             reply_keyboard, one_time_keyboard=True, input_field_placeholder="Do you take it?"
#         ),
#     )


# async def info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     await context.bot.send_message(
#         chat_id=update.effective_chat.id,
#         text='Information about the Ikigai coworking will be displayed here.',
#         parse_mode='HTML'
#     )