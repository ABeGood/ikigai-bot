from telebot.handler_backends import State, StatesGroup

class BotStates(StatesGroup):
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
    state_prepay = State()

    # My Reservations
    state_my_reservation_list = State()
    state_my_reservation = State()

    state_info = State()