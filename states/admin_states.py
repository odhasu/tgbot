"""FSM state groups for multi-step admin input flows."""

from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class AddCategoryStates(StatesGroup):
    name = State()


class AddProductStates(StatesGroup):
    name = State()
    description = State()
    price = State()
    stock = State()
    delivery_type = State()
    photo = State()


class EditProductStates(StatesGroup):
    value = State()


class SearchUserStates(StatesGroup):
    query = State()


class BalanceStates(StatesGroup):
    amount = State()


class BroadcastStates(StatesGroup):
    message = State()
    confirm = State()
