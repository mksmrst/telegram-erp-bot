# 📦 Telegram ERP-бот для учета товаров и продаж

Асинхронный Telegram-бот, помогающий продавать товары, вести финансовый учет и составлять отчетность для малого бизнеса.

---

## ✨ Функционал

### 👤 Для пользователей
* Просмотр каталога товаров.
* Оформление заказов и покупка товаров в режиме реального времени.

### 👑 Для администратора
* Добавление новых товаров в базу.
* Просмотр финансовой отчетности, чистой прибыли и оценка маржинальности продаж.
* **Списание партий по модели FIFO:** бот отслеживает конкретные партии товаров, которые поступили в разное время и по разным закупочным ценам, и ведет корректную отчетность в соответствии с закупками в разные промежутки времени.
  <img src="https://github.com/mksmrst/telegram-erp-bot/blob/main/photo_catalog.jpg" width="320" />
  <img src="https://github.com/mksmrst/telegram-erp-bot/blob/main/photo_fin.jpg" width="320" />
</p>
<h3 align="center">🎬 Демонстрация ключевых функций</h3>

<table align="center">
  <tr>
    <td align="center"><b>📝 Создание товара</b><br>
        <img src="https://github.com/mksmrst/telegram-erp-bot/blob/main/gif_start-ezgif.com-optimize.gif" width="200"/></td>
  </tr>
</table>
---

## 🛠 Технологический стек

* **Language:** Python 3
* **Framework:** aiogram 3
* **Database:** SQLite (`aiosqlite`)
* **Hosting:** Render

---

## 🗄 Структура базы данных

* `products` — каталог всех товаров и их актуальные остатки на складе.
* `orders` — история заказов клиентов.
* `supplies` — партии закупленных товаров с учетом себестоимости.
* `users` — сведения о зарегистрированных пользователях бота.

---

## 🚀 Локальный запуск проекта

1. **Клонировать репозиторий:**
   ```bash
   git clone [https://github.com/mksmrst/telegram-erp-bot.git](https://github.com/mksmrst/telegram-erp-bot.git)
   cd telegram-erp-bot
   
2. Установить зависимости:
    ```bash
    pip install -r requirements.txt

3. Создать файл .env в корне проекта с токеном бота:
    ``` bash
    BOT_TOKEN=ваш_токен_от_BotFather
   
4. Запустить бота:
    ```bash
    python main.py
