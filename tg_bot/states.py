from telebot.handler_backends import State, StatesGroup
from typing import Optional

class BotStates(StatesGroup):
    previous_state = State()

    state_start = State()
    state_main_menu = State()

    # New Reservation
    state_reservation_menu_type = State()
    state_reservation_menu_hours = State()
    state_admin_chat = State()

    state_reservation_menu_date = State()
    state_reservation_menu_time = State()
    state_reservation_menu_place = State()
    state_reservation_menu_recap = State()
    state_pay = State()
    # state_payment_confirm = State()

    # My Reservations
    state_my_reservation_list = State()
    state_my_reservation = State()

    state_info = State()


def change_state(bot, user_id: int, new_state: State, store_previous: bool = True) -> None:
    """
    Handles state transitions with previous state tracking.
    
    Args:
        bot: TeleBot instance
        user_id: User's telegram ID
        new_state: State to transition to
        store_previous: Whether to store current state as previous
    """
    if store_previous:
        current_state = bot.get_state(user_id)
        if current_state:
            bot.set_state(user_id, BotStates.previous_state, current_state)
    try:
        bot.set_state(user_id, new_state)
    except Exception as e:
        print(e)


def get_previous_state(bot, user_id: int) -> Optional[State]:
    """
    Retrieves the previous state for a user.
    
    Args:
        bot: TeleBot instance
        user_id: User's telegram ID
    
    Returns:
        Previous state or None if not found
    """
    return bot.get_state(user_id, BotStates.previous_state)