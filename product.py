# product.py
# ============================================================
# ABHAY PANEL STORE - PRODUCT CATALOG
# User Price + Reseller Price set directly in code
# ============================================================

from __future__ import annotations

import sqlite3
from pathlib import Path


DB_PATH = Path("store.db")


# ============================================================
# PRODUCTS
# ============================================================
# 
# Har product me:
#   "cost"            → Supplier cost (website se)
#   "display_price"   → USER PRICE (normal user ko dikhega)
#   "reseller_price"  → RESELLER PRICE (reseller ko dikhega)
# 
# ============================================================

PRODUCTS = [
    # --------------------------------------------------------
    # PID 54 - PATO TEAM FF ALL ANDROID
    # --------------------------------------------------------
    {
        "pid": 54,
        "name": "PATO TEAM FF ALL ANDROID",
        "display_name": "PATO TEAM ALL",
        "category": "NON ROOT",
        "style": "success",
        "maintenance": 0,
        "durations": [
            #  duration        display           user_price    reseller_price
            {"duration": "3d",  "display_duration": "3 DAYS",  "cost": 67,  "display_price": 99,  "reseller_price": 79},
            {"duration": "7d",  "display_duration": "7 DAYS",  "cost": 100, "display_price": 149, "reseller_price": 119},
            {"duration": "15d", "display_duration": "15 DAYS", "cost": 167, "display_price": 249, "reseller_price": 199},
            {"duration": "30d", "display_duration": "30 DAYS", "cost": 267, "display_price": 349, "reseller_price": 299},
        ],
    },

    # --------------------------------------------------------
    # PID 155 - XYZ CHEATS APKMOD FF NONROOT
    # --------------------------------------------------------
    {
        "pid": 155,
        "name": "XYZ CHEATS APKMOD FF NONROOT",
        "display_name": "XYZ APKMOD NONROOT",
        "category": "NON ROOT",
        "style": "danger",
        "maintenance": 0,
        "durations": [
            {"duration": "1h",  "display_duration": "1 HOUR",   "cost": 7, "display_price": 20, "reseller_price": 15},
            {"duration": "2h",  "display_duration": "2 HOURS",  "cost": 16, "display_price": 30, "reseller_price": 25},
            {"duration": "4h",  "display_duration": "4 HOURS",  "cost": 25, "display_price": 40, "reseller_price": 35},
            {"duration": "6h",  "display_duration": "6 HOURS",  "cost": 42, "display_price": 70, "reseller_price": 55},
            {"duration": "12h", "display_duration": "12 HOURS", "cost": 65, "display_price": 119, "reseller_price": 99},
            {"duration": "24h", "display_duration": "24 HOURS", "cost": 126, "display_price": 169, "reseller_price": 129},
            {"duration": "3d",  "display_duration": "3 DAYS",   "cost": 186, "display_price": 259, "reseller_price": 219},
            {"duration": "7d",  "display_duration": "7 DAYS",   "cost": 273, "display_price": 299, "reseller_price": 259},
        ],
    },

    # --------------------------------------------------------
    # PID 151 - ABCD PANEL FF NONROOT
    # --------------------------------------------------------
    {
        "pid": 151,
        "name": "ABCD PANEL FF NONROOT",
        "display_name": "ABCD PANEL NONROOT",
        "category": "NON ROOT",
        "style": "primary",
        "maintenance": 0,
        "durations": [
            {"duration": "12h", "display_duration": "12 HOURS", "cost": 5,  "display_price": 29,  "reseller_price": 19},
            {"duration": "1d",  "display_duration": "1 DAY",    "cost": 14, "display_price": 39,  "reseller_price": 29},
            {"duration": "3d",  "display_duration": "3 DAYS",   "cost": 27, "display_price": 59,  "reseller_price": 45},
            {"duration": "7d",  "display_duration": "7 DAYS",   "cost": 50, "display_price": 99,  "reseller_price": 75},
        ],
    },

    # --------------------------------------------------------
    # PID 159 - ZRAX PANEL NONROOT FF
    # --------------------------------------------------------
    {
        "pid": 159,
        "name": "ZRAX PANEL NONROOT FF",
        "display_name": "ZRAX PANEL ALL",
        "category": "NON ROOT",
        "style": "success",
        "maintenance": 0,
        "durations": [
            {"duration": "1d", "display_duration": "1 DAY",  "cost": 9,  "display_price": 39, "reseller_price": 29},
            {"duration": "3d", "display_duration": "3 DAYS", "cost": 23, "display_price": 59, "reseller_price": 45},
            {"duration": "7d", "display_duration": "7 DAYS", "cost": 47, "display_price": 99, "reseller_price": 75},
        ],
    },

    # --------------------------------------------------------
    # PID 136 - BALA MODS-V6 FF NONROOT
    # --------------------------------------------------------
    {
        "pid": 136,
        "name": "BALA MODS-V6 FF NONROOT",
        "display_name": "BALA MODS V6 NONROOT",
        "category": "NON ROOT",
        "style": "danger",
        "maintenance": 0,
        "durations": [
            {"duration": "1h",  "display_duration": "1 HOUR",   "cost": 5,   "display_price": 29,  "reseller_price": 19},
            {"duration": "3h",  "display_duration": "3 HOURS",  "cost": 17,  "display_price": 39,  "reseller_price": 29},
            {"duration": "6h",  "display_duration": "6 HOURS",  "cost": 34,  "display_price": 59,  "reseller_price": 45},
            {"duration": "12h", "display_duration": "12 HOURS", "cost": 67,  "display_price": 99,  "reseller_price": 75},
            {"duration": "1d",  "display_duration": "1 DAY",    "cost": 143, "display_price": 199, "reseller_price": 169},
        ],
    },

    # --------------------------------------------------------
    # PID 62 - DRIPCLIENT FF NONROOT APKMOD
    # --------------------------------------------------------
    {
        "pid": 62,
        "name": "DRIPCLIENT FF NONROOT APKMOD",
        "display_name": "DRIP APKMOD NONROOT",
        "category": "NON ROOT",
        "style": "success",
        "maintenance": 0,
        "durations": [
            {"duration": "1d",  "display_duration": "1 DAY",   "cost": 12,  "display_price": 39,  "reseller_price": 29},
            {"duration": "3d",  "display_duration": "3 DAYS",  "cost": 25,  "display_price": 49,  "reseller_price": 39},
            {"duration": "7d",  "display_duration": "7 DAYS",  "cost": 65,  "display_price": 99,  "reseller_price": 75},
            {"duration": "15d", "display_duration": "15 DAYS", "cost": 128, "display_price": 179, "reseller_price": 149},
            {"duration": "30d", "display_duration": "30 DAYS", "cost": 165, "display_price": 229, "reseller_price": 189},
        ],
    },

    # --------------------------------------------------------
    # PID 150 - DRIPCLIENT WIRE FF NONROOT
    # --------------------------------------------------------
    {
        "pid": 150,
        "name": "DRIPCLIENT WIRE FF NONROOT",
        "display_name": "DRIP WIRE NONROOT",
        "category": "NON ROOT",
        "style": "primary",
        "maintenance": 0,
        "durations": [
            {"duration": "6h",  "display_duration": "6 HOURS",  "cost": 11,  "display_price": 35,  "reseller_price": 29},
            {"duration": "12h", "display_duration": "12 HOURS", "cost": 26,  "display_price": 60,  "reseller_price": 39},
            {"duration": "1d",  "display_duration": "1 DAY",    "cost": 39,  "display_price": 80,  "reseller_price": 55},
            {"duration": "7d",  "display_duration": "7 DAYS",   "cost": 127, "display_price": 160, "reseller_price": 149},
        ],
    },

    # --------------------------------------------------------
    # PID 63 - DRIPCLIENT FF ROOT ANDROID
    # --------------------------------------------------------
    {
        "pid": 63,
        "name": "DRIPCLIENT FF ROOT ANDROID",
        "display_name": "DRIP CLIENT ROOT",
        "category": "ROOT",
        "style": "danger",
        "maintenance": 0,
        "durations": [
            {"duration": "1d",  "display_duration": "1 DAY",   "cost": 12,  "display_price": 45,  "reseller_price": 39},
            {"duration": "7d",  "display_duration": "7 DAYS",  "cost": 65,  "display_price": 130, "reseller_price": 119},
            {"duration": "30d", "display_duration": "30 DAYS", "cost": 150, "display_price": 250, "reseller_price": 199},
        ],
    },

    # --------------------------------------------------------
    # PID 48 - PRIME HOOK FF NONROOT ANDROID
    # --------------------------------------------------------
    {
        "pid": 48,
        "name": "PRIME HOOK FF NONROOT ANDROID",
        "display_name": "PRIME HOOK ALL",
        "category": "NON ROOT",
        "style": "success",
        "maintenance": 0,
        "durations": [
            {"duration": "1d",  "display_duration": "1 DAY",   "cost": 16,  "display_price": 35,  "reseller_price": 28},
            {"duration": "3d",  "display_duration": "3 DAYS",  "cost": 37,  "display_price": 69,  "reseller_price": 58},
            {"duration": "7d",  "display_duration": "7 DAYS",  "cost": 75,  "display_price": 220, "reseller_price": 150},
            {"duration": "10d", "display_duration": "10 DAYS", "cost": 112, "display_price": 310, "reseller_price": 139},
        ],
    },

    # --------------------------------------------------------
    # PID 127 - SILENT CHEAT FF NONROOT APKMOD (Maintenance)
    # --------------------------------------------------------
    {
        "pid": 127,
        "name": "SILENT CHEAT FF NONROOT APKMOD",
        "display_name": "SILENT CHEAT APKMOD",
        "category": "NON ROOT",
        "style": "danger",
        "maintenance": 1,
        "durations": [
            {"duration": "1d",  "display_duration": "1 DAY",   "cost": 20,  "display_price": 49,  "reseller_price": 39},
            {"duration": "3d",  "display_duration": "3 DAYS",  "cost": 49,  "display_price": 89,  "reseller_price": 69},
            {"duration": "7d",  "display_duration": "7 DAYS",  "cost": 83,  "display_price": 149, "reseller_price": 119},
            {"duration": "14d", "display_duration": "14 DAYS", "cost": 149, "display_price": 229, "reseller_price": 189},
            {"duration": "28d", "display_duration": "28 DAYS", "cost": 232, "display_price": 349, "reseller_price": 289},
        ],
    },

    # --------------------------------------------------------
    # PID 128 - SILENT CHEAT FF ROOT ANDROID
    # --------------------------------------------------------
    {
        "pid": 128,
        "name": "SILENT CHEAT FF ROOT ANDROID",
        "display_name": "SILENT CHEAT ROOT",
        "category": "ROOT",
        "style": "danger",
        "maintenance": 0,
        "durations": [
            {"duration": "1d safe",    "display_duration": "1 DAY SAFE",    "cost": 23,  "display_price": 59,  "reseller_price": 49},
            {"duration": "3d safe",    "display_duration": "3 DAYS SAFE",   "cost": 49,  "display_price": 99,  "reseller_price": 79},
            {"duration": "7d safe",    "display_duration": "7 DAYS SAFE",   "cost": 83,  "display_price": 149, "reseller_price": 119},
            {"duration": "14d safe",   "display_duration": "14 DAYS SAFE",  "cost": 149, "display_price": 229, "reseller_price": 189},
            {"duration": "28d safe",   "display_duration": "28 DAYS SAFE",  "cost": 233, "display_price": 349, "reseller_price": 289},
            {"duration": "1d brutal",  "display_duration": "1 DAY BRUTAL",  "cost": 23,  "display_price": 59,  "reseller_price": 49},
            {"duration": "3d brutal",  "display_duration": "3 DAYS BRUTAL", "cost": 49,  "display_price": 99,  "reseller_price": 79},
            {"duration": "7d brutal",  "display_duration": "7 DAYS BRUTAL", "cost": 83,  "display_price": 149, "reseller_price": 119},
            {"duration": "14d brutal", "display_duration": "14 DAYS BRUTAL","cost": 149, "display_price": 229, "reseller_price": 189},
            {"duration": "28d brutal", "display_duration": "28 DAYS BRUTAL","cost": 233, "display_price": 349, "reseller_price": 289},
        ],
    },

    # --------------------------------------------------------
    # PID 149 - XRAG FF ALL
    # --------------------------------------------------------
    {
        "pid": 149,
        "name": "XRAG FF ALL",
        "display_name": "XRAG FF ALL",
        "category": "NON ROOT",
        "style": "success",
        "maintenance": 0,
        "durations": [
            {"duration": "1h",  "display_duration": "1 HOUR",   "cost": 5,   "display_price": 18,  "reseller_price": 15},
            {"duration": "3h",  "display_duration": "3 HOURS",  "cost": 11,  "display_price": 35,  "reseller_price": 29},
            {"duration": "6h",  "display_duration": "6 HOURS",  "cost": 20,  "display_price": 55,  "reseller_price": 39},
            {"duration": "12h", "display_duration": "12 HOURS", "cost": 25,  "display_price": 75,  "reseller_price": 45},
            {"duration": "24h", "display_duration": "1 DAYS", "cost": 39,  "display_price": 100,  "reseller_price": 65},
            {"duration": "3d",  "display_duration": "3 DAYS",   "cost": 83,  "display_price": 150, "reseller_price": 119},
            {"duration": "7d",  "display_duration": "7 DAYS",   "cost": 133, "display_price": 200, "reseller_price": 169},
        ],
    },

    # --------------------------------------------------------
    # PID 144 - NINE X FF NONROOT
    # --------------------------------------------------------
    {
        "pid": 144,
        "name": "NINE X FF NONROOT",
        "display_name": "NINE X NONROOT",
        "category": "NON ROOT",
        "style": "primary",
        "maintenance": 0,
        "durations": [
            {"duration": "10d", "display_duration": "10 DAYS", "cost": 233, "display_price": 349, "reseller_price": 289},
        ],
    },
]


# ============================================================
# DB HELPERS
# ============================================================

def table_columns(conn, table):
    return [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]


def find_table(conn, candidates):
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    existing = {r[0] for r in rows}
    for t in candidates:
        if t in existing:
            return t
    return None


# ============================================================
# SEED — DB me products add karta hai
# ============================================================

def seed() -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")

    product_table = find_table(conn, ["products", "supplier_products"])
    duration_table = find_table(
        conn, ["supplier_product_durations", "product_durations", "durations"],
    )

    if not product_table:
        raise RuntimeError("No products table found.")

    product_columns = table_columns(conn, product_table)
    duration_columns = table_columns(conn, duration_table) if duration_table else []

    # Auto-add columns
    for col, col_type in [
        ("display_name", "TEXT"),
        ("style", "TEXT DEFAULT 'success'"),
    ]:
        if col not in product_columns:
            try:
                conn.execute(f"ALTER TABLE {product_table} ADD COLUMN {col} {col_type}")
                product_columns.append(col)
            except Exception:
                pass

    if duration_table:
        for col, col_type in [
            ("display_duration", "TEXT"),
            ("display_price", "REAL"),
            ("reseller_price", "REAL"),
        ]:
            if col not in duration_columns:
                try:
                    conn.execute(f"ALTER TABLE {duration_table} ADD COLUMN {col} {col_type}")
                    duration_columns.append(col)
                except Exception:
                    pass

    for product in PRODUCTS:
        pid = product["pid"]

        pid_column = None
        for c in ("supplier_pid", "product_id", "pid"):
            if c in product_columns:
                pid_column = c
                break
        if not pid_column:
            raise RuntimeError("No PID column")

        row = conn.execute(
            f"SELECT id FROM {product_table} WHERE {pid_column} = ? LIMIT 1", (pid,)
        ).fetchone()

        if row:
            product_id = row[0]
            updates = []
            values = []
            for field in ("name", "display_name", "category", "description", "style"):
                if field in product_columns:
                    updates.append(f"{field} = ?")
                    values.append(product.get(field, product.get("name")))
            for field in ("maintenance", "is_maintenance"):
                if field in product_columns:
                    updates.append(f"{field} = ?")
                    values.append(product["maintenance"])
            if updates:
                values.append(product_id)
                conn.execute(f"UPDATE {product_table} SET {', '.join(updates)} WHERE id = ?", values)
        else:
            fields = []
            values = []
            ph = []
            for field in ("name", "display_name", "category", "description", "style"):
                if field in product_columns:
                    fields.append(field)
                    values.append(product.get(field, product.get("name")))
                    ph.append("?")
            for field in ("maintenance", "is_maintenance"):
                if field in product_columns:
                    fields.append(field)
                    values.append(product["maintenance"])
                    ph.append("?")
            fields.append(pid_column)
            values.append(pid)
            ph.append("?")
            conn.execute(
                f"INSERT INTO {product_table} ({', '.join(fields)}) VALUES ({', '.join(ph)})",
                values,
            )
            product_id = conn.execute(
                f"SELECT id FROM {product_table} WHERE {pid_column} = ? LIMIT 1", (pid,)
            ).fetchone()[0]

        if not duration_table:
            continue

        for dur in product["durations"]:
            duration = dur["duration"]
            display_duration = dur.get("display_duration", duration)
            supplier_cost = dur.get("cost")
            display_price = dur.get("display_price")
            reseller_price = dur.get("reseller_price")

            dfield = None
            for c in ("duration", "duration_name", "name"):
                if c in duration_columns:
                    dfield = c
                    break
            if not dfield:
                continue

            fk = None
            for c in ("product_id", "supplier_product_id"):
                if c in duration_columns:
                    fk = c
                    break
            if not fk:
                continue

            existing = conn.execute(
                f"SELECT id FROM {duration_table} WHERE {fk} = ? AND {dfield} = ? LIMIT 1",
                (product_id, duration),
            ).fetchone()

            if existing:
                updates = []
                values = []
                for field, val in (
                    ("display_duration", display_duration),
                    ("supplier_cost", supplier_cost),
                    ("cost", supplier_cost),
                    ("display_price", display_price),
                    ("reseller_price", reseller_price),
                ):
                    if field in duration_columns:
                        updates.append(f"{field} = ?")
                        values.append(val)
                if updates:
                    values.append(existing[0])
                    conn.execute(f"UPDATE {duration_table} SET {', '.join(updates)} WHERE id = ?", values)
            else:
                fields = [fk, dfield]
                values = [product_id, duration]
                ph = ["?", "?"]
                for field, val in (
                    ("display_duration", display_duration),
                    ("supplier_cost", supplier_cost),
                    ("cost", supplier_cost),
                    ("display_price", display_price),
                    ("reseller_price", reseller_price),
                ):
                    if field in duration_columns:
                        fields.append(field)
                        values.append(val)
                        ph.append("?")
                conn.execute(
                    f"INSERT INTO {duration_table} ({', '.join(fields)}) VALUES ({', '.join(ph)})",
                    values,
                )

    conn.commit()
    conn.close()


if __name__ == "__main__":
    seed()
