"""FSM state for purchases that need customer-supplied information."""

from aiogram.fsm.state import State, StatesGroup


class PurchaseStates(StatesGroup):
    customer_email = State()
    confirmation = State()
