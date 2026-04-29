import asyncio
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

import config
from db import add_item, add_purchase, delete_item, get_all_items, get_item
from payment import create_payment


logger = logging.getLogger(__name__)


NAME, DESCRIPTION, PRICE, CONTENT = range(4)


def setup_handlers(application: Application) -> None:
    """Регистрирует все обработчики бота."""
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("shop", shop_handler))
    application.add_handler(CommandHandler("admin", admin_handler))
    application.add_handler(CommandHandler("items", items_handler))

    add_conversation = ConversationHandler(
        entry_points=[CommandHandler("add", add_start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_name)],
            DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_description)],
            PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_price)],
            CONTENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_content)],
        },
        fallbacks=[CommandHandler("cancel", add_cancel)],
    )
    application.add_handler(add_conversation)

    application.add_handler(CallbackQueryHandler(buy_callback, pattern=r"^buy_\d+$"))
    application.add_handler(CallbackQueryHandler(delete_callback, pattern=r"^delete_\d+$"))


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /start: приветствие и краткая справка."""
    del context
    text = (
        "Привет! Это магазин цифровых товаров.\n\n"
        "Доступные команды:\n"
        "/shop — показать каталог\n"
        "/admin — админ-панель\n"
        "/items — список товаров (для админа)\n"
        "/add — добавить товар (для админа)"
    )
    await update.message.reply_text(text)


async def shop_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /shop: показывает каталог товаров с кнопками Купить."""
    del context
    items = get_all_items()
    if not items:
        await update.message.reply_text("Пока нет доступных товаров.")
        return

    for item in items:
        text = (
            f"*{item['name']}*\n"
            f"{item['description']}\n"
            f"Цена: {item['price']} ₽"
        )
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("Купить", callback_data=f"buy_{item['id']}")]]
        )
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")


async def buy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик покупки: создаёт платёж и отправляет ссылку."""
    query = update.callback_query
    await query.answer()

    item_id = int(query.data.split("_")[1])
    item = get_item(item_id)
    if not item:
        await query.message.reply_text("Товар не найден или уже удалён.")
        return

    user_id = query.from_user.id
    description = f"Покупка товара: {item['name']}"

    try:
        
        payment_url, payment_id = await asyncio.to_thread(
            create_payment, item["price"], description, user_id, item_id
        )
        add_purchase(user_id=user_id, item_id=item_id, payment_id=payment_id)
    except Exception as error:
        logger.exception("Ошибка создания платежа: %s", error)
        await query.message.reply_text("Не удалось создать платёж. Попробуйте позже.")
        return

    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Оплатить", url=payment_url)]]
    )
    await query.message.reply_text(
        (
            f"Вы выбрали: {item['name']}\n"
            f"К оплате: {item['price']} ₽\n\n"
            "После оплаты товар будет выдан автоматически.\n"
            "Сейчас заглушка: Оплата обрабатывается, товар придёт автоматически."
        ),
        reply_markup=keyboard,
    )


async def admin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /admin: проверка доступа и показ админ-команд."""
    del context
    user_id = update.effective_user.id
    if not config.is_admin(user_id):
        await update.message.reply_text("У вас нет доступа к админ-панели.")
        return

    await update.message.reply_text(
        "Админ-панель:\n"
        "/add — добавить товар\n"
        "/items — список товаров\n"
        "/cancel — отменить текущий сценарий добавления"
    )


async def add_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Старт сценария добавления товара."""
    user_id = update.effective_user.id
    if not config.is_admin(user_id):
        await update.message.reply_text("У вас нет прав для добавления товаров.")
        return ConversationHandler.END

    context.user_data.clear()
    await update.message.reply_text("Введите название товара:")
    return NAME


async def add_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Шаг NAME: сохраняем название."""
    context.user_data["name"] = update.message.text.strip()
    await update.message.reply_text("Введите описание товара:")
    return DESCRIPTION


async def add_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Шаг DESCRIPTION: сохраняем описание."""
    context.user_data["description"] = update.message.text.strip()
    await update.message.reply_text("Введите цену (целое число в рублях):")
    return PRICE


async def add_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Шаг PRICE: валидируем и сохраняем цену."""
    raw_price = update.message.text.strip()
    if not raw_price.isdigit():
        await update.message.reply_text("Цена должна быть числом. Введите ещё раз:")
        return PRICE

    price = int(raw_price)
    if price <= 0:
        await update.message.reply_text("Цена должна быть больше нуля. Введите ещё раз:")
        return PRICE

    context.user_data["price"] = price
    await update.message.reply_text("Введите текст товара (контент, который получит покупатель):")
    return CONTENT


async def add_content(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Шаг CONTENT: сохраняем товар в БД."""
    content = update.message.text.strip()
    context.user_data["content"] = content

    item_id = add_item(
        name=context.user_data["name"],
        description=context.user_data["description"],
        price=context.user_data["price"],
        content=context.user_data["content"],
    )
    context.user_data.clear()

    await update.message.reply_text(f"Товар успешно добавлен. ID: {item_id}")
    return ConversationHandler.END


async def add_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена сценария добавления."""
    context.user_data.clear()
    await update.message.reply_text("Добавление товара отменено.")
    return ConversationHandler.END


async def items_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /items: список товаров с кнопками удаления."""
    del context
    user_id = update.effective_user.id
    if not config.is_admin(user_id):
        await update.message.reply_text("Команда доступна только администраторам.")
        return

    items = get_all_items()
    if not items:
        await update.message.reply_text("Список товаров пуст.")
        return

    lines = ["Список товаров:"]
    for index, item in enumerate(items, start=1):
        lines.append(f"{index}. {item['name']} — {item['price']} ₽")

    keyboard = [
        [InlineKeyboardButton(f"Удалить: {item['name']}", callback_data=f"delete_{item['id']}")]
        for item in items
    ]
    await update.message.reply_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def delete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Удаление товара по callback delete_{id} (только для админа)."""
    del context
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    if not config.is_admin(user_id):
        await query.message.reply_text("Удаление доступно только администраторам.")
        return

    item_id = int(query.data.split("_")[1])
    item = get_item(item_id)
    if not item:
        await query.message.reply_text("Товар уже удалён.")
        return

    delete_item(item_id)
    await query.message.reply_text(f"Товар «{item['name']}» удалён.")

