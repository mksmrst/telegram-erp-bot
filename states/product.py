from aiogram.fsm.state import StatesGroup, State

class EditProduct(StatesGroup):
    waiting_for_stock = State()

class AddProductForm(StatesGroup):
    title = State()
    price = State()
    cost_price = State()
    stock = State()

class SupplyProductForm(StatesGroup):
    waiting_for_quantity = State()
    waiting_for_cost_price = State()