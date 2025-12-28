import os
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL")

@contextmanager
def get_conn():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

# =============================
# INIT DB
# =============================

def init_db():
    with get_conn() as c:
        cur = c.cursor()

        # USERS
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            phone TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            balance BIGINT DEFAULT 0,
            created_at TIMESTAMP NOT NULL
        )
        """)

        # PACKAGES
        cur.execute("""
        CREATE TABLE IF NOT EXISTS packages (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            price BIGINT NOT NULL,
            active BOOLEAN DEFAULT TRUE
        )
        """)

        # ORDERS (AUTO / ALFA)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            package_id INTEGER REFERENCES packages(id),
            user_number TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP NOT NULL
        )
        """)

        # SEED PACKAGES
        cur.execute("SELECT COUNT(*) FROM packages")
        if cur.fetchone()["count"] == 0:
            cur.executemany(
                "INSERT INTO packages(name, price, active) VALUES (%s,%s,TRUE)",
                [
                    ("11 GB", 870000),
                    ("22 GB", 1200000),
                    ("33 GB", 1450000),
                    ("44 GB", 1860000),
                    ("55 GB", 2280000),
                ],
            )

        # =============================
        # STOCK TABLES (PHONE BASED)
        # =============================

        cur.execute("""
        CREATE TABLE IF NOT EXISTS stock_products (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP NOT NULL
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS stock_orders (
            id SERIAL PRIMARY KEY,
            phone TEXT NOT NULL,
            product_id INTEGER REFERENCES stock_products(id),
            months INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP NOT NULL
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS stock_accounts (
            id SERIAL PRIMARY KEY,
            stock_order_id INTEGER UNIQUE REFERENCES stock_orders(id),
            account_email TEXT NOT NULL,
            account_password TEXT NOT NULL,
            profile_name TEXT,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            created_at TIMESTAMP NOT NULL
        )
        """)

        # SEED STOCK PRODUCTS
        cur.execute("SELECT COUNT(*) FROM stock_products")
        if cur.fetchone()["count"] == 0:
            cur.executemany(
                "INSERT INTO stock_products(name, active, created_at) VALUES (%s, TRUE, %s)",
                [
                    ("Netflix Stock", datetime.utcnow()),
                    ("Shahid Stock", datetime.utcnow()),
                    ("OSN+ Stock", datetime.utcnow()),
                    ("TOD Mobile & TV Stock", datetime.utcnow()),
                    ("Anghami Stock", datetime.utcnow()),
                ],
            )

# =============================
# USERS
# =============================

def create_user(phone, password_hash):
    with get_conn() as c:
        c.cursor().execute(
            "INSERT INTO users(phone,password_hash,balance,created_at) VALUES (%s,%s,0,%s)",
            (phone, password_hash, datetime.utcnow()),
        )

def get_user_by_phone(phone):
    with get_conn() as c:
        cur = c.cursor()
        cur.execute("SELECT * FROM users WHERE phone=%s", (phone,))
        return cur.fetchone()

def add_balance(phone, amt):
    with get_conn() as c:
        c.cursor().execute(
            "UPDATE users SET balance = balance + %s WHERE phone=%s",
            (amt, phone),
        )

def deduct_balance(phone, amt):
    with get_conn() as c:
        c.cursor().execute(
            "UPDATE users SET balance = balance - %s WHERE phone=%s",
            (amt, phone),
        )

# =============================
# PACKAGES / ORDERS (AUTO)
# =============================

def list_packages(active_only=True):
    with get_conn() as c:
        cur = c.cursor()
        if active_only:
            cur.execute("SELECT * FROM packages WHERE active=TRUE ORDER BY price")
        else:
            cur.execute("SELECT * FROM packages ORDER BY price")
        return cur.fetchall()

def create_order(user_id, package_id, user_number):
    with get_conn() as c:
        cur = c.cursor()
        cur.execute(
            """INSERT INTO orders(user_id,package_id,user_number,status,created_at)
               VALUES (%s,%s,%s,'pending',%s) RETURNING id""",
            (user_id, package_id, user_number, datetime.utcnow()),
        )
        return cur.fetchone()["id"]

# =============================
# STOCK (MANUAL)
# =============================

def list_stock_products(active_only=True):
    with get_conn() as c:
        cur = c.cursor()
        if active_only:
            cur.execute("SELECT * FROM stock_products WHERE active=TRUE ORDER BY id")
        else:
            cur.execute("SELECT * FROM stock_products ORDER BY id")
        return cur.fetchall()

def create_stock_order(phone, product_id, months):
    with get_conn() as c:
        cur = c.cursor()
        cur.execute(
            """INSERT INTO stock_orders(phone, product_id, months, status, created_at)
               VALUES (%s,%s,%s,'pending',%s)
               RETURNING id""",
            (phone, product_id, months, datetime.utcnow()),
        )
        return cur.fetchone()["id"]

def list_user_stock_orders(phone, limit=50):
    with get_conn() as c:
        cur = c.cursor()
        cur.execute(
            """SELECT so.id, so.status, so.months, so.created_at,
                      sp.name AS product_name
               FROM stock_orders so
               JOIN stock_products sp ON sp.id = so.product_id
               WHERE so.phone = %s
               ORDER BY so.id DESC
               LIMIT %s""",
            (phone, limit),
        )
        return cur.fetchall()

def list_user_stock_accounts(phone, limit=50):
    with get_conn() as c:
        cur = c.cursor()
        cur.execute(
            """SELECT sa.id, sp.name AS product_name,
                      sa.account_email, sa.account_password, sa.profile_name,
                      sa.start_date, sa.end_date
               FROM stock_accounts sa
               JOIN stock_orders so ON so.id = sa.stock_order_id
               JOIN stock_products sp ON sp.id = so.product_id
               WHERE so.phone = %s
               ORDER BY sa.id DESC
               LIMIT %s""",
            (phone, limit),
        )
        return cur.fetchall()

def list_pending_stock_orders(limit=100):
    with get_conn() as c:
        cur = c.cursor()
        cur.execute(
            """SELECT so.id, so.months, so.status, so.created_at,
                      so.phone,
                      sp.name AS product_name
               FROM stock_orders so
               JOIN stock_products sp ON sp.id = so.product_id
               WHERE so.status = 'pending'
               ORDER BY so.id DESC
               LIMIT %s""",
            (limit,),
        )
        return cur.fetchall()

def fulfill_stock_order(
    soid,
    account_email,
    account_password,
    profile_name,
    start_date,
    end_date,
):
    with get_conn() as c:
        cur = c.cursor()
        cur.execute(
            """INSERT INTO stock_accounts(
                   stock_order_id, account_email, account_password, profile_name,
                   start_date, end_date, created_at
               ) VALUES (%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (stock_order_id)
               DO UPDATE SET
                   account_email=EXCLUDED.account_email,
                   account_password=EXCLUDED.account_password,
                   profile_name=EXCLUDED.profile_name,
                   start_date=EXCLUDED.start_date,
                   end_date=EXCLUDED.end_date
            """,
            (
                soid,
                account_email,
                account_password,
                profile_name,
                start_date,
                end_date,
                datetime.utcnow(),
            ),
        )
        cur.execute(
            "UPDATE stock_orders SET status='active' WHERE id=%s",
            (soid,),
        )
def get_stock_order(soid: int):
    with get_conn() as c:
        cur = c.cursor()
        cur.execute(
            """SELECT so.id, so.phone, so.months, so.created_at,
                      sp.name AS product_name
               FROM stock_orders so
               JOIN stock_products sp ON sp.id = so.product_id
               WHERE so.id = %s""",
            (soid,),
        )
        return cur.fetchone()
