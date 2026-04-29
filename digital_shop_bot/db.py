import sqlite3
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "shop.db"


def _connect() -> sqlite3.Connection:
    """Создаёт подключение к SQLite с row_factory в виде словаря."""
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    """Создаёт таблицы items и purchases при первом запуске."""
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                price INTEGER NOT NULL,
                content TEXT NOT NULL,
                content_type TEXT NOT NULL DEFAULT 'text',
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS purchases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                item_id INTEGER NOT NULL,
                payment_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            """
        )


def add_item(name: str, description: str, price: int, content: str) -> int:
    """Добавляет товар и возвращает его ID."""
    with _connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO items (name, description, price, content, content_type)
            VALUES (?, ?, ?, ?, 'text');
            """,
            (name, description, price, content),
        )
        return int(cursor.lastrowid)


def get_all_items() -> list[dict[str, Any]]:
    """Возвращает все товары из каталога."""
    with _connect() as conn:
        cursor = conn.execute(
            """
            SELECT id, name, description, price, content, content_type, created_at
            FROM items
            ORDER BY id ASC;
            """
        )
        return [dict(row) for row in cursor.fetchall()]


def get_item(item_id: int) -> dict[str, Any] | None:
    """Возвращает один товар по ID."""
    with _connect() as conn:
        cursor = conn.execute(
            """
            SELECT id, name, description, price, content, content_type, created_at
            FROM items
            WHERE id = ?;
            """,
            (item_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def delete_item(item_id: int) -> None:
    """Удаляет товар по ID."""
    with _connect() as conn:
        conn.execute("DELETE FROM items WHERE id = ?;", (item_id,))


def add_purchase(user_id: int, item_id: int, payment_id: str, status: str = "pending") -> int:
    """Создаёт запись о покупке и возвращает её ID."""
    with _connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO purchases (user_id, item_id, payment_id, status)
            VALUES (?, ?, ?, ?);
            """,
            (user_id, item_id, payment_id, status),
        )
        return int(cursor.lastrowid)


def get_pending_purchases(limit: int = 50) -> list[dict[str, Any]]:
    """Возвращает покупки со статусом pending."""
    with _connect() as conn:
        cursor = conn.execute(
            """
            SELECT id, user_id, item_id, payment_id, status, created_at
            FROM purchases
            WHERE status = 'pending'
            ORDER BY id ASC
            LIMIT ?;
            """,
            (limit,),
        )
        return [dict(row) for row in cursor.fetchall()]


def update_purchase_status(purchase_id: int, status: str) -> None:
    """Обновляет статус покупки."""
    with _connect() as conn:
        conn.execute(
            """
            UPDATE purchases
            SET status = ?
            WHERE id = ?;
            """,
            (status, purchase_id),
        )

