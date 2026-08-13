# handlers/admin.py
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from db.database import (
    delete_product, update_product_stock,
    add_product, get_product_by_id, register_sale, add_supply_record
)
from states.product import SupplyProductForm, AddProductForm, EditProduct
from handlers.common import back_to_catalog, get_main_reply_keyboard

router = Router()

ADMIN_IDS = [999583318]


@router.callback_query(F.data.startswith("prod_"))
async def process_product_click(callback: types.CallbackQuery):
    product_id = callback.data.split("_")[1]
    user_id = callback.from_user.id

    builder = InlineKeyboardBuilder()

    if user_id in ADMIN_IDS:
        builder.button(text="💰 Продать 1 шт.", callback_data=f"sell_one_{product_id}")
        builder.button(text="🔍 Посмотреть карточку товара", callback_data=f"show_card_{product_id}")
        builder.button(text="➕ Добавить поставку", callback_data=f"add_supply_{product_id}")
        builder.button(text="✏️ Изменить точное кол-во", callback_data=f"edit_stock_{product_id}")
        builder.button(text="🗑 Удалить товар", callback_data=f"delete_prod_{product_id}")
        builder.button(text="◀️ Назад в каталог", callback_data="back_to_catalog")
        builder.adjust(1, 2, 2, 1)

        text = f"⚙️ <b>Панель управления товаром #{product_id}</b>"
    else:
        builder.button(text="🛒 Купить", callback_data=f"buy_prod_{product_id}")
        builder.button(text="◀️ Назад в каталог", callback_data="back_to_catalog")
        builder.adjust(1)

        text = f"📦 <b>Информация о товаре #{product_id}</b>"

    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("show_card_"))
async def show_product_card(callback: types.CallbackQuery):
    product_id = int(callback.data.split("_")[2])
    product = await get_product_by_id(product_id)

    if not product:
        await callback.answer("❌ Товар не найден!", show_alert=True)
        return

    p_id, title, price, cost_price, stock = product

    profit = price - cost_price
    margin = (profit / price * 100) if price > 0 else 0

    formatted_price = f"{price:,.0f}".replace(",", " ")
    formatted_cost = f"{cost_price:,.0f}".replace(",", " ")
    formatted_profit = f"{profit:,.0f}".replace(",", " ")

    user_id = callback.from_user.id

    if user_id in ADMIN_IDS:
        text = (
            f"📦 <b>Карточка товара (Админ-режим)</b>\n\n"
            f"📌 <b>Название:</b> {title}\n"
            f"💵 <b>Цена продажи:</b> {formatted_price} руб.\n"
            f"📉 <b>Закупочная цена:</b> {formatted_cost} руб.\n"
            f"📈 <b>Прибыль с шт.:</b> {formatted_profit} руб. ({margin:.1f}%)\n"
            f"📊 <b>Остаток на складе:</b> {stock} шт.\n"
        )
    else:
        text = (
            f"📌 <b>{title}</b>\n\n"
            f"💵 <b>Цена:</b> {formatted_price} руб.\n"
            f"📦 <b>В наличии:</b> {stock} шт.\n"
        )

    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Назад к управлению", callback_data=f"prod_{product_id}")

    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("sell_one_"))
async def sell_one_thing(callback: types.CallbackQuery):
    product_id = int(callback.data.split('_')[2])
    product = await register_sale(product_id)

    if product is None:
        await callback.answer(text="К сожалению данный товар закончился(", show_alert=True)
    else:
        title, price, profit, new_stock = product
        formatted_profit = f"{profit:,.0f}".replace(",", " ")
        await callback.answer(text=f"Название товара: {title}\nПрибыль: {formatted_profit}\nОстаток на складе: {new_stock}", show_alert=True)


@router.callback_query(F.data.startswith("delete_prod_"))
async def confirm_delete_product(callback: types.CallbackQuery):
    product_id = callback.data.split("_")[2]

    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Да, удалить", callback_data=f"confirm_delete_{product_id}")
    builder.button(text="◀️ Отмена", callback_data=f"prod_{product_id}")
    builder.adjust(2)

    await callback.message.edit_text(
        f"⚠️ <b>Вы уверены, что хотите удалить товар #{product_id}?</b>\n"
        f"Это действие нельзя будет отменить.",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_delete_"))
async def process_delete_product(callback: types.CallbackQuery):
    product_id = int(callback.data.split("_")[2])

    await delete_product(product_id)
    await callback.answer("Товар успешно удален!", show_alert=True)
    await back_to_catalog(callback)


@router.callback_query(F.data.startswith("edit_stock_"))
async def start_edit_stock(callback: types.CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split("_")[2])
    await state.update_data(editing_product_id=product_id)
    await state.set_state(EditProduct.waiting_for_stock)

    cancel_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Отмена", callback_data="cancel_edit_stock")]
        ]
    )

    await callback.message.edit_text(
        f"✏️ <b>Изменение остатка для товара #{product_id}</b>\n\n"
        f"Введите новое количество товара на складе (числом):", reply_markup=cancel_kb, parse_mode="HTML"
    )

    await callback.answer()


@router.callback_query(F.data == "cancel_edit_stock", EditProduct.waiting_for_stock)
async def cancel_command(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    current_id = data["editing_product_id"]
    await state.clear()
    await callback.answer("❌ Изменение остатка отменено", show_alert=True)
    product = await get_product_by_id(current_id)

    p_id, title, price, cost_price, stock = product

    profit = price - cost_price
    margin = (profit / price * 100) if price > 0 else 0

    formatted_price = f"{price:,.0f}".replace(",", " ")
    formatted_stock = f"{stock:,.0f}".replace(",", " ")
    formatted_cost_price = f"{cost_price:,.0f}".replace(",", " ")
    formatted_profit = f"{profit:,.0f}".replace(",", " ")

    text = (
        f"❌ <b>Изменение остатка отменено.</b>\n\n"
        f"📦 <b>Карточка товара (Админ-режим)</b>\n\n"
        f"📌 <b>Название:</b> {title}\n"
        f"💵 <b>Цена продажи:</b> {formatted_price} руб.\n"
        f"📉 <b>Закупочная цена:</b> {formatted_cost_price} руб.\n"
        f"📈 <b>Прибыль с шт.:</b> {formatted_profit} руб. ({margin:.1f}%)\n"
        f"📊 <b>Остаток на складе:</b> {formatted_stock} шт.\n"
    )
    builder = InlineKeyboardBuilder()
    builder.button(text="Назад", callback_data=f"prod_{p_id}")

    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")


@router.message(EditProduct.waiting_for_stock)
async def process_new_stock(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Пожалуйста, введите корректное целое число!")
        return

    new_stock = int(message.text)
    user_data = await state.get_data()
    product_id = user_data["editing_product_id"]

    await update_product_stock(product_id, new_stock)
    await state.clear()

    await message.answer(
        f"✅ Остаток товара #{product_id} успешно изменен на <b>{new_stock} шт.</b>!\n\n"
        f"Используйте /menu для просмотра обновленного каталога.",
        parse_mode="HTML"
    )


@router.message(Command("cancel"))
@router.message(F.text.casefold() == "отмена")
async def cancel_handler(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("В текущем состоянии нечего отменить!")
        return
    else:
        await state.clear()
        is_admin = message.from_user.id in ADMIN_IDS
        await message.answer("Действие отменено.", reply_markup=get_main_reply_keyboard(is_admin))


@router.message(Command("add_product"))
@router.message(F.text == "➕ Добавить товар")
async def cmd_add_product(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ У вас нет прав для добавления товаров!")
        return

    await state.set_state(AddProductForm.title)
    await message.answer("📝 <b>Добавление нового товара</b>\n\nВведите название товара:", parse_mode="HTML")


@router.message(AddProductForm.title)
async def process_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(AddProductForm.price)
    await message.answer("💰 Введите цену продажи товара (в рублях):")


@router.message(AddProductForm.price)
async def process_price(message: types.Message, state: FSMContext):
    try:
        cleaned_text = message.text.replace(" ", "").replace(",", ".")
        price = float(cleaned_text)
        if price <= 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Введите корректное число! Пример: 1500 или 1 500")
        return

    await state.update_data(price=price)
    await state.set_state(AddProductForm.cost_price)
    await message.answer("📉 Введите закупочную цену товара (себестоимость в рублях):")


@router.message(AddProductForm.cost_price)
async def process_cost_price(message: types.Message, state: FSMContext):
    try:
        cleaned_text = message.text.replace(" ", "").replace(",", ".")
        cost_price = float(cleaned_text)
        if cost_price < 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Введите корректное число! Пример: 800 или 0")
        return

    await state.update_data(cost_price=cost_price)
    await state.set_state(AddProductForm.stock)
    await message.answer("📦 Введите количество товара на складе (в шт.):")


@router.message(AddProductForm.stock)
async def process_stock(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Количество должно быть целым положительным числом!")
        return

    stock = int(message.text)
    user_data = await state.get_data()

    title = user_data["title"]
    price = user_data["price"]
    cost_price = user_data["cost_price"]

    await add_product(title, price, cost_price, stock)
    await state.clear()

    formatted_price = f"{price:,.0f}".replace(",", " ")
    formatted_cost = f"{cost_price:,.0f}".replace(",", " ")
    formatted_stock = f"{stock:,.0f}".replace(",", " ")

    await message.answer(
        f"✅ <b>Товар успешно добавлен!</b>\n\n"
        f"📌 <b>Название:</b> {title}\n"
        f"💵 <b>Продажа:</b> {formatted_price} руб.\n"
        f"📉 <b>Закупка:</b> {formatted_cost} руб.\n"
        f"📊 <b>Остаток:</b> {formatted_stock} шт.\n\n"
        f"Используйте /menu для просмотра каталога.",
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("buy_prod_"))
async def process_buy_product(callback: types.CallbackQuery):
    product_id = int(callback.data.split("_")[2])

    product = await get_product_by_id(product_id)
    if not product:
        await callback.answer("Товар не найден!", show_alert=True)
        return

    p_id, title, price, cost_price, stock = product

    if stock <= 0:
        await callback.answer("❌ К сожалению, товар закончился на складе!", show_alert=True)
        return

    new_stock = stock - 1
    await update_product_stock(product_id, new_stock)

    await callback.answer(f"🎉 Вы успешно купили {title}!", show_alert=True)
    await back_to_catalog(callback)


@router.callback_query(F.data.startswith("add_supply_"))
async def start_add_supply(callback: types.CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split("_")[2])

    await state.update_data(supply_product_id=product_id)
    await state.set_state(SupplyProductForm.waiting_for_quantity)

    await callback.message.edit_text(
        f"📦 <b>Приёмка поставки для товара #{product_id}</b>\n\n"
        f"Сколько штук пришло в новой поставке? (введите число):",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(SupplyProductForm.waiting_for_quantity)
async def process_supply_quantity(message: types.Message, state: FSMContext):
    if not message.text.isdigit() or int(message.text) <= 0:
        await message.answer("❌ Введите корректное положительное число штук!")
        return

    added_quantity = int(message.text)
    await state.update_data(quantity=added_quantity)
    await state.set_state(SupplyProductForm.waiting_for_cost_price)

    await message.answer(
        f"✅ Успешно! К товару добавлено <b>+{added_quantity} шт.</b>\n\n"
        f"Введите закупочную цену товара",
        parse_mode="HTML"
    )


@router.message(SupplyProductForm.waiting_for_cost_price)
async def process_cost_price_supply(message: types.Message, state: FSMContext):
    try:
        cleaned_text = message.text.replace(" ", "").replace(",", ".")
        added_price = float(cleaned_text)
        if added_price <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите корректную закупочную цену (положительное число)!")
        return

    user_data = await state.get_data()
    supply_product_id = user_data["supply_product_id"]
    quantity = user_data["quantity"]
    await add_supply_record(supply_product_id, quantity, added_price)
    await state.clear()

    formatted_price = f"{added_price:,.0f}".replace(",", " ")
    await message.answer(
        f"Данные успешно обновлены!\nК товару №{supply_product_id} добавлено {quantity}\n"
        f"Также была установлена новая закупочная цена: {formatted_price}"
    )