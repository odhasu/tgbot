"""FSM state groups for multi-step admin input flows."""

from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class AddCategoryStates(StatesGroup):
    name = State()
    description = State()
    sort_order = State()


class EditCategoryStates(StatesGroup):
    value = State()


class EditSettingsStates(StatesGroup):
    value = State()


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
