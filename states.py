from aiogram.fsm.state import State, StatesGroup

class Registration(StatesGroup):
    nickname = State()
    citizenship = State()
    bank_account = State()

class CreateVacancy(StatesGroup):
    description = State()
    priority = State()
    category = State()
    salary = State()

class EditProfile(StatesGroup):
    new_bank = State()

class JobAction(StatesGroup):
    waiting_for_coords = State()