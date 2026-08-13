from sqlite3 import Row
from typing import Iterable
import aiosqlite

DB_NAME = "erp_database.db"


async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                price REAL NOT NULL,
                stock INTEGER NOT NULL
            )
        """)

        await db.execute(""" 
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'new',
                total_amount REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        async with db.execute("SELECT MAX(version) FROM schema_migrations") as cursor:
            row = await cursor.fetchone()
            current_version = row[0] if row[0] is not None else 0

        if current_version < 1:
            await db.execute("ALTER TABLE products ADD COLUMN cost_price REAL DEFAULT 0.0")
            await db.execute("INSERT INTO schema_migrations (version) VALUES (1)")
            print("🚀 Применена миграция базы №1: добавлена закупочная цена")

        if current_version < 2:
            await db.execute("""
                             CREATE TABLE IF NOT EXISTS supplies 
                             (id INTEGER PRIMARY KEY AUTOINCREMENT,
                              product_id INTEGER,
                              quantity INTEGER,
                              cost_price REAL NOT NULL,
                              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                              FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE)
                                 """)
            await db.execute("INSERT INTO schema_migrations (version) VALUES (2)")
            print("🚀 Применена миграция базы №2: добавлена новая таблица с поставками")

        await db.commit()
        print("Database initialized")


async def get_all_products() -> Iterable[Row]:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT id, title, price, stock FROM products WHERE stock > 0"
        ) as cursor:
            return await cursor.fetchall()


async def get_product_by_id(product_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT id, title, price, cost_price, stock FROM products WHERE id = ?",
            (product_id,)
        ) as cursor:
            return await cursor.fetchone()  # Возвращаем 1 кортеж с данными товара


async def delete_product(product_id: int):
    async with aiosqlite.connect(DB_NAME) as connect:
        await connect.execute("DELETE FROM products WHERE id = ?", (product_id,))
        await connect.commit()


async def update_product_stock(product_id: int, new_stock: int):
    async with aiosqlite.connect(DB_NAME) as connect:
        async with connect.execute(
            "SELECT stock, cost_price FROM products WHERE id = ?",
            (product_id,)
        ) as cursor:
            row = await cursor.fetchone()
            stock = row[0] if row is not None else 0
            diff = new_stock - stock
            cost_price = row[1] if row is not None else 0
            if diff > 0:
                await connect.execute(
                    "INSERT INTO supplies (product_id, quantity, cost_price) VALUES (?, ?, ?)",
                    (product_id, diff, cost_price)
                )
            else:
                async with connect.execute(
                    "SELECT id, quantity FROM supplies WHERE product_id = ? AND quantity > 0 ORDER BY created_at ASC",
                    (product_id,)
                ) as cursor:
                    supplies = await cursor.fetchall()
                    to_remove = abs(diff)
                    for supply_id, qty in supplies:
                        if to_remove <= 0:
                            break
                        else:
                            deduct = min(to_remove, qty)
                            await connect.execute(
                                "UPDATE supplies SET quantity = quantity - ? WHERE id = ?", (deduct, supply_id)
                            )
                            to_remove -= deduct
        await connect.execute(
            "UPDATE products SET stock = ? WHERE id = ?",
            (new_stock, product_id)
        )

        await connect.commit()


async def add_product(title: str, price: float, cost_price: float, stock: int):
    async with aiosqlite.connect(DB_NAME) as connect:
        async with connect.execute(
            "INSERT INTO products (title, price, cost_price, stock) VALUES (?, ?, ?, ?)",
            (title, price, cost_price, stock)
        ) as cursor:
            product_id = cursor.lastrowid
            if stock > 0:
                await connect.execute(
                    "INSERT INTO supplies (product_id, quantity, cost_price) VALUES (?, ?, ?)",
                    (product_id, stock, cost_price)
                )
            await connect.commit()


async def add_supply_record(product_id: int, quantity: int, cost_price: float):
    async with aiosqlite.connect(DB_NAME) as connect:
        await connect.execute(
            "INSERT INTO supplies (product_id, quantity, cost_price) VALUES (?, ?, ?)",
            (product_id, quantity, cost_price)
        )
        await connect.execute(
            "UPDATE products SET stock = stock + ? WHERE id = ?",
            (quantity, product_id)
        )
        await connect.commit()


async def get_financial_report():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT price, cost_price, stock FROM products") as cursor:
            products = await cursor.fetchall()

            total_retail_value = 0.0
            total_cost_value = 0.0
            total_units = 0

            for price, cost_price, stock in products:
                total_retail_value += price * stock
                total_cost_value += cost_price * stock
                total_units += stock

            potential_profit = total_retail_value - total_cost_value

            return {
                "total_units": total_units,
                "total_retail": total_retail_value,
                "total_cost": total_cost_value,
                "potential_profit": potential_profit
            }
        
async def register_sale(product_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        # 1. Достаем данные о самом товаре
        async with db.execute(
            "SELECT title, price, stock FROM products WHERE id = ?",
            (product_id,)
        ) as cursor:
            product = await cursor.fetchone()
            if not product or product[2] <= 0:
                return None  # Товара нет или склад пуст

            title, price, stock = product

        # 2. Находим самую старую активную партию (FIFO)
        async with db.execute(
            "SELECT id, cost_price FROM supplies WHERE product_id = ? AND quantity > 0 ORDER BY created_at ASC LIMIT 1",
            (product_id,)
        ) as cursor:
            supply = await cursor.fetchone()
            if not supply:
                return None  # Поставок с остатком нет

            supply_id, cost_price = supply

        # 3. Списываем 1 шт. из конкретной партии (по supply_id)
        await db.execute(
            "UPDATE supplies SET quantity = quantity - 1 WHERE id = ?",
            (supply_id,)
        )

        # 4. Уменьшаем общий остаток товара на складе
        new_stock = stock - 1
        await db.execute(
            "UPDATE products SET stock = ? WHERE id = ?",
            (new_stock, product_id)
        )

        # 5. Сохраняем все изменения в базе одним транзакционным коммитом
        await db.commit()

        # 6. Считаем прибыль = (Розничная цена - Закупка конкретно ЭТОЙ партии)
        profit = price - cost_price

        return title, price, profit, new_stock

import os

# Проверяем, есть ли переменная Turso в окружении
TURSO_URL = os.getenv("TURSO_DATABASE_URL")
TURSO_TOKEN = os.getenv("TURSO_AUTH_TOKEN")

if TURSO_URL and TURSO_TOKEN:
    # Этот импорт сработает только на сервере Render (Linux)
    import libsql_experimental as sqlite
else:
    # На твоем ПК в Windows будет работать стандартный aiosqlite
    import aiosqlite as sqlite