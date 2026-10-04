# database.py
# ============================================================
# ABHAY PANEL STORE - DATABASE (SQLite)
# ============================================================

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

DB_PATH = Path("store.db")


# ============================================================
# CONNECTION
# ============================================================

def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ============================================================
# INIT DB
# ============================================================

def init_db() -> None:
    conn = _conn()
    cur = conn.cursor()

    # ---------------- users ----------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            balance REAL DEFAULT 0,
            created_at INTEGER
        )
    """)

    # Purane users table me naye columns add karo
    for col, col_type in [
        ("referral_code", "TEXT"),
        ("referred_by", "INTEGER"),
        ("referral_balance", "REAL DEFAULT 0"),
        ("last_spin", "INTEGER DEFAULT 0"),
        ("spin_balance", "REAL DEFAULT 0"),
        ("country", "TEXT"),
        ("total_spent", "REAL DEFAULT 0"),
        ("total_deposited", "REAL DEFAULT 0"),
        ("reseller_expiry", "INTEGER DEFAULT 0"),
    ]:
        try:
            cur.execute(f"ALTER TABLE users ADD COLUMN {col} {col_type}")
        except Exception:
            pass

    # ---------------- products ----------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            supplier_pid TEXT UNIQUE,
            name TEXT,
            display_name TEXT,
            category TEXT,
            description TEXT,
            maintenance INTEGER DEFAULT 0,
            style TEXT DEFAULT 'success'
        )
    """)

    # Products me naye columns
    for col, col_type in [
        ("features", "TEXT"),
        ("demo_link", "VARCHAR(255)"),
        ("image_url", "VARCHAR(255)"),
        ("is_active", "INTEGER DEFAULT 1"),
    ]:
        try:
            cur.execute(f"ALTER TABLE products ADD COLUMN {col} {col_type}")
        except Exception:
            pass

    # ---------------- durations ----------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS durations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            duration TEXT,
            display_duration TEXT,
            supplier_cost REAL,
            display_price REAL,
            reseller_price REAL,
            FOREIGN KEY(product_id) REFERENCES products(id)
        )
    """)

    # ---------------- deposits ----------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS deposits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            order_id TEXT UNIQUE,
            status TEXT,
            created_at INTEGER
        )
    """)

    # ---------------- orders ----------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_ref TEXT UNIQUE,
            user_id INTEGER,
            product_id TEXT,
            product_name TEXT,
            duration TEXT,
            price REAL,
            keys TEXT,
            status TEXT DEFAULT 'COMPLETED',
            created_at INTEGER
        )
    """)

    # ---------------- spin history ----------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS spin_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            created_at INTEGER
        )
    """)

    # ---------------- referral history ----------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS referral_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id INTEGER,
            referee_id INTEGER,
            amount REAL,
            created_at INTEGER
        )
    """)

    # ---------------- support tickets ----------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS support_tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_ref TEXT UNIQUE,
            user_id INTEGER,
            subject TEXT,
            message TEXT,
            status TEXT DEFAULT 'OPEN',
            admin_reply TEXT,
            created_at INTEGER,
            updated_at INTEGER
        )
    """)

    # ---------------- broadcast history ----------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS broadcast_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            total INTEGER,
            delivered INTEGER,
            failed INTEGER,
            blocked INTEGER,
            duration REAL,
            created_at INTEGER
        )
    """)

    # ---------------- bot settings ----------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS bot_settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at INTEGER
        )
    """)

    conn.commit()
    conn.close()


# ============================================================
# USERS
# ============================================================

def get_or_create_user(telegram_id, username=None, first_name=None, last_name=None):
    conn = _conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    row = cur.fetchone()

    if row:
        conn.close()
        return dict(row)

    import random
    import string
    ref_code = "REF" + "".join(random.choices(string.ascii_uppercase + string.digits, k=6))

    cur.execute(
        """INSERT INTO users 
           (telegram_id, username, first_name, last_name, balance, created_at, referral_code) 
           VALUES (?, ?, ?, ?, 0, ?, ?)""",
        (telegram_id, username, first_name, last_name, int(time.time()), ref_code),
    )
    conn.commit()
    user_id = cur.lastrowid
    conn.close()

    return {
        "id": user_id,
        "telegram_id": telegram_id,
        "balance": 0,
        "referral_code": ref_code,
    }


def get_user(telegram_id):
    conn = _conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_referral_code(code):
    conn = _conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE referral_code = ?", (code,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def set_referred_by(user_telegram_id, referrer_telegram_id):
    conn = _conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE users SET referred_by = ? WHERE telegram_id = ? AND (referred_by IS NULL OR referred_by = 0)",
            (referrer_telegram_id, user_telegram_id),
        )
        conn.commit()
        changed = cur.rowcount > 0
    except Exception:
        changed = False
    conn.close()
    return changed


def add_referral_balance(telegram_id, amount):
    conn = _conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET referral_balance = referral_balance + ? WHERE telegram_id = ?",
        (amount, telegram_id),
    )
    conn.commit()
    conn.close()


def add_to_total_spent(telegram_id, amount):
    conn = _conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET total_spent = total_spent + ? WHERE telegram_id = ?",
        (amount, telegram_id),
    )
    conn.commit()
    conn.close()


def get_user_stats(telegram_id):
    conn = _conn()
    cur = conn.cursor()

    cur.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    user = cur.fetchone()

    if not user:
        conn.close()
        return None

    user = dict(user)

    cur.execute("SELECT COUNT(*) as cnt FROM orders WHERE user_id = ?", (user["id"],))
    orders_count = cur.fetchone()["cnt"]

    cur.execute("SELECT COUNT(*) as cnt FROM users WHERE referred_by = ?", (telegram_id,))
    ref_count = cur.fetchone()["cnt"]

    conn.close()

    return {
        "user": user,
        "orders_count": orders_count,
        "referral_count": ref_count,
    }


# ============================================================
# WALLET
# ============================================================

def get_wallet_balance(telegram_id):
    user = get_user(telegram_id)
    if not user:
        return 0.0
    return float(user.get("balance") or 0)


def credit_wallet(user_id, amount, reference=""):
    conn = _conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET balance = balance + ? WHERE telegram_id = ?",
        (amount, user_id),
    )
    conn.commit()
    changed = cur.rowcount
    conn.close()
    return changed > 0


def debit_wallet(user_id, amount, reference=""):
    conn = _conn()
    cur = conn.cursor()
    cur.execute("SELECT balance FROM users WHERE telegram_id = ?", (user_id,))
    row = cur.fetchone()
    if not row or float(row["balance"]) < amount:
        conn.close()
        return False
    cur.execute(
        "UPDATE users SET balance = balance - ? WHERE telegram_id = ?",
        (amount, user_id),
    )
    conn.commit()
    conn.close()
    return True


# ============================================================
# DEPOSITS
# ============================================================

def create_deposit(user_id, amount, order_id, status="pending"):
    conn = _conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO deposits (user_id, amount, order_id, status, created_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, amount, order_id, status, int(time.time())),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def get_deposit_by_order_id(order_id):
    conn = _conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM deposits WHERE order_id = ?", (order_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def update_deposit_status(order_id, status):
    conn = _conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE deposits SET status = ? WHERE order_id = ?",
        (status, order_id),
    )
    conn.commit()
    conn.close()
    return True


# ============================================================
# PRODUCTS
# ============================================================

def get_products(category=None):
    conn = _conn()
    cur = conn.cursor()
    if category:
        cur.execute("SELECT * FROM products WHERE category = ? ORDER BY name", (category,))
    else:
        cur.execute("SELECT * FROM products ORDER BY name")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_product(pid):
    conn = _conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM products WHERE supplier_pid = ?", (str(pid),))
    row = cur.fetchone()
    if not row:
        conn.close()
        return None
    product = dict(row)
    cur.execute(
        "SELECT duration, display_duration, supplier_cost, display_price, reseller_price FROM durations WHERE product_id = ?",
        (product["id"],),
    )
    dur_rows = cur.fetchall()
    conn.close()
    product["durations"] = [
        {
            "duration": r["duration"],
            "display_duration": r["display_duration"] or r["duration"],
            "supplier_cost": r["supplier_cost"],
            "display_price": r["display_price"],
            "reseller_price": r["reseller_price"],
        }
        for r in dur_rows
    ]
    return product


# ============================================================
# ORDERS
# ============================================================

def generate_order_ref() -> str:
    import random
    import string
    rand = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"ORD-{rand}"


def create_order(
    user_id, product_id, duration, price, keys,
    product_name="", order_ref="",
):
    if not order_ref:
        order_ref = generate_order_ref()

    conn = _conn()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO orders 
           (order_ref, user_id, product_id, product_name, duration, price, keys, status, created_at) 
           VALUES (?, ?, ?, ?, ?, ?, ?, 'COMPLETED', ?)""",
        (
            order_ref, user_id, product_id, product_name, duration, price,
            "\n".join(keys) if isinstance(keys, list) else str(keys),
            int(time.time()),
        ),
    )
    conn.commit()
    conn.close()
    return order_ref


def get_user_orders(user_id, limit=10):
    conn = _conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC LIMIT ?",
        (user_id, limit),
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ============================================================
# SPIN
# ============================================================

def can_spin(telegram_id):
    user = get_user(telegram_id)
    if not user:
        return False, 0

    last_spin = int(user.get("last_spin") or 0)
    now = int(time.time())
    diff = now - last_spin
    cooldown = 24 * 60 * 60

    if diff >= cooldown:
        return True, 0
    return False, cooldown - diff


def set_last_spin(telegram_id):
    conn = _conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET last_spin = ? WHERE telegram_id = ?",
        (int(time.time()), telegram_id),
    )
    conn.commit()
    conn.close()


def add_spin_balance(telegram_id, amount):
    conn = _conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET spin_balance = spin_balance + ? WHERE telegram_id = ?",
        (amount, telegram_id),
    )
    conn.commit()
    conn.close()


def log_spin(user_id, amount):
    conn = _conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO spin_history (user_id, amount, created_at) VALUES (?, ?, ?)",
        (user_id, amount, int(time.time())),
    )
    conn.commit()
    conn.close()


# ============================================================
# REFERRAL
# ============================================================

def log_referral(referrer_id, referee_id, amount):
    conn = _conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO referral_history (referrer_id, referee_id, amount, created_at) VALUES (?, ?, ?, ?)",
        (referrer_id, referee_id, amount, int(time.time())),
    )
    conn.commit()
    conn.close()


def get_referral_count(telegram_id):
    conn = _conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) as cnt FROM users WHERE referred_by = ?",
        (telegram_id,),
    )
    cnt = cur.fetchone()["cnt"]
    conn.close()
    return cnt


def get_referral_balance(telegram_id):
    user = get_user(telegram_id)
    if not user:
        return 0.0
    return float(user.get("referral_balance") or 0)
