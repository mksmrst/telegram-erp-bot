# handlers/common.py
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from db.database import get_all_products, get_financial_report

router = Router()

ADMIN_IDS = [999583318]

# Вспомогательная функция для генерации реплай-кнопок
def get_main_reply_keyboard(is_admin: bool = False) -> types.ReplyKeyboardMarkup:
    keyboard = [
        [types.KeyboardButton(text="📦 Каталог товаров"), types.KeyboardButton(text="❓ Справка")]
    ]
    if is_admin:
        keyboard.append([types.KeyboardButton(text="➕ Добавить товар"), types.KeyboardButton(text="📊 Финансовый отчет")])

    return types.ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


@router.message(Command("start"))
async def cmd_start(message: types.Message):
    is_admin = message.from_user.id in ADMIN_IDS
    reply_kb = get_main_reply_keyboard(is_admin)

    await message.answer(
        "👋 Нажмите <b>«📦 Каталог товаров»</b> для просмотра списка.",
        reply_markup=reply_kb,
        parse_mode="HTML"
    )


@router.message(Command("menu"))
@router.message(F.text == "📦 Каталог товаров")
async def cmd_menu(message: types.Message):
    products = await get_all_products()

    if not products:
        await message.answer("К сожалению, в данный момент каталог пуст(")
        return

    text = "📦 <b>Каталог товаров:</b>\n\nВыберите товар из списка ниже:"
    builder = InlineKeyboardBuilder()

    for product in products:
        p_id, title, price, stock = product
        formatted_price = f"{price:,.0f}".replace(",", " ")
        formatted_stock = f"{stock:,.0f}".replace(",", " ")
        builder.button(
            text=f"{title} | {formatted_price} руб. ({formatted_stock} шт.)",
            callback_data=f"prod_{p_id}"
        )

    builder.adjust(1)
    await message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")


@router.message(F.text == "❓ Справка")
@router.message(Command("help"))
async def cmd_help(message: types.Message):
    help_text = (
        "❓ <b>Инструкция по работе с ERP-системой:</b>\n\n"
        "• <b>📦 Каталог товаров:</b> Показывает актуальный список товаров и остатки на складе.\n"
        "• <b>🛒 Покупка:</b> Выберите товар в каталоге и нажмите «Купить».\n"
    )
    if message.from_user.id in ADMIN_IDS:
        help_text += (
            "\n👑 <b>Функции Администратора:</b>\n"
            "• <b>📊 Финансовый отчет:</b> Сводка по стоимости склада и марже.\n"
            "• <b>🔍 Карточка товара:</b> Просмотр закупки и профита с каждой штуки.\n"
            "• <b>➕ Добавить товар:</b> Пошаговый ввод данных через FSM.\n"
        )
    await message.answer(help_text, parse_mode="HTML")


@router.message(F.text == "📊 Финансовый отчет")
@router.message(Command("report"))
async def cmd_report(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ У вас нет доступа к финансовым отчетам.")
        return

    report = await get_financial_report()

    retail_fmt = f"{report['total_retail']:,.0f}".replace(",", " ")
    cost_fmt = f"{report['total_cost']:,.0f}".replace(",", " ")
    profit_fmt = f"{report['potential_profit']:,.0f}".replace(",", " ")
    stocks_having = f"{report['total_units']:,.0f}".replace(",", " ")

    text = (
        "📈 <b>Финансовая аналитика склада:</b>\n\n"
        f"📦 <b>Товаров в наличии:</b> {stocks_having} шт.\n"
        f"💵 <b>Заморожено в закупке:</b> {cost_fmt} руб.\n"
        f"💰 <b>Оценка в рознице:</b> {retail_fmt} руб.\n"
        f"🔥 <b>Потенциальная маржа:</b> {profit_fmt} руб.\n"
    )

    await message.answer(text, parse_mode="HTML")


@router.callback_query(F.data == "back_to_catalog")
async def back_to_catalog(callback: types.CallbackQuery):
    products = await get_all_products()
    builder = InlineKeyboardBuilder()

    for product in products:
        p_id, title, price, stock = product
        formatted_price = f"{price:,.0f}".replace(",", " ")
        builder.button(
            text=f"{title} | {formatted_price} руб. ({stock} шт.)",
            callback_data=f"prod_{p_id}"
        )

    builder.adjust(1)
    await callback.message.edit_text(
        "📦 <b>Каталог товаров ERP:</b>\n\nВыберите товар из списка ниже:",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()