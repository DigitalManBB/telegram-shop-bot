import logging
import asyncio

from telegram.ext import ApplicationBuilder

from config import BOT_TOKEN
from db import get_item, get_pending_purchases, init_db, update_purchase_status
from handlers import setup_handlers
from payment import get_payment_status


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def process_pending_payments(context) -> None:
    """
    Периодически проверяет pending-платежи.
    При успешной оплате отправляет пользователю уведомление в бот.
    """
    try:
        pending_purchases = get_pending_purchases()

        for purchase in pending_purchases:
            payment_status = await asyncio.to_thread(get_payment_status, purchase["payment_id"])
            if payment_status != "succeeded":
                continue

            # Сначала фиксируем статус в БД, чтобы избежать дублей.
            update_purchase_status(purchase["id"], "succeeded")

            item = get_item(purchase["item_id"])
            item_name = item["name"] if item else f"#{purchase['item_id']}"

            await context.bot.send_message(
                chat_id=purchase["user_id"],
                text=(
                    "Платёж успешно получен.\n"
                    f"Товар: {item_name}\n\n"
                    "Оплата обрабатывается, товар придёт автоматически."
                ),
            )
    except Exception as error:
        logger.exception("Ошибка фоновой проверки платежей: %s", error)


def main() -> None:
    """Точка входа: инициализация БД и запуск Telegram-бота."""
    init_db()

    application = ApplicationBuilder().token(BOT_TOKEN).build()
    setup_handlers(application)
    application.job_queue.run_repeating(process_pending_payments, interval=20, first=10)

    logger.info("Бот запущен")
    application.run_polling()


if __name__ == "__main__":
    main()

