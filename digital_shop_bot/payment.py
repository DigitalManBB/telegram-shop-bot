import uuid
from decimal import Decimal

from yookassa import Configuration, Payment

import config



Configuration.account_id = config.YOOKASSA_SHOP_ID
Configuration.secret_key = config.YOOKASSA_SECRET_KEY


def create_payment(amount: int, description: str, user_id: int, item_id: int) -> tuple[str, str]:
    """
    Создаёт платёж в YooKassa.
    Возвращает (payment_url, payment_id).
    """
    amount_value = str(Decimal(amount).quantize(Decimal("0.01")))

    payment = Payment.create(
        {
            "amount": {
                "value": amount_value,
                "currency": "RUB",
            },
            "confirmation": {
                "type": "redirect",
                # Пока оставляем заглушку
                "return_url": "https://example.com/",
            },
            "capture": True,
            "description": description,
            "metadata": {
                "user_id": str(user_id),
                "item_id": str(item_id),
            },
        },
        str(uuid.uuid4()),
    )

    return payment.confirmation.confirmation_url, payment.id


def get_payment_status(payment_id: str) -> str:
    """Возвращает текущий статус платежа в YooKassa."""
    payment = Payment.find_one(payment_id)
    return str(payment.status)

