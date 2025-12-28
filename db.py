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


def init_db():
    with get_conn() as c:
        cur = c.cursor()

        # Users
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                phone TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                balance BIGINT DEFAULT 0,
                created_at TIMESTAMP NOT NULL
            )
            """
        )

        # Alfa uShare packages
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS packages (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                price BIGINT NOT NULL,
                active BOOLEAN DEFAULT TRUE
            )
            """
        )

        # Orders (general)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                package_id INTEGER REFERENCES packages(id),
                user_number TEXT,
                status TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL
            )
            """
        )

        # Extend orders for premium subscriptions + delivery (safe on existing DB)
        cur.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS order_type TEXT DEFAULT 'ushare'")
        cur.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS product_name TEXT")
        cur.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS duration TEXT")
        cur.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS price_usd NUMERIC")
        cur.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS delivery_phone TEXT")
        cur.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS delivery_email TEXT")
        cur.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS delivery_password TEXT")
        cur.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS delivery_notes TEXT")

        # Premium products / variants / plans (for Netflix/Shahid/others)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS products (
                id SERIAL PRIMARY KEY,
                slug TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                active BOOLEAN DEFAULT TRUE
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS product_variants (
                id SERIAL PRIMARY KEY,
                product_id INTEGER REFERENCES products(id),
                name TEXT NOT NULL,
                active BOOLEAN DEFAULT TRUE
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS product_plans (
                id SERIAL PRIMARY KEY,
                variant_id INTEGER REFERENCES product_variants(id),
                duration TEXT NOT NULL,
                price_usd NUMERIC NOT NULL,
                active BOOLEAN DEFAULT TRUE
            )
            """
        )

        # Seed default packages
        cur.execute("SELECT COUNT(*) AS count FROM packages")
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

        # Seed default products (Netflix/Shahid)
        cur.execute("SELECT COUNT(*) AS count FROM products")
        if cur.fetchone()["count"] == 0:
            cur.executemany(
                "INSERT INTO products(slug, title, active) VALUES (%s,%s,TRUE)",
                [("netflix", "Netflix", True), ("shahid", "Shahid VIP", True)],
            )

        # Seed variants and plans if empty
        cur.execute("SELECT COUNT(*) AS count FROM product_variants")
        if cur.fetchone()["count"] == 0:
            # Netflix
            cur.execute("SELECT id, slug, title FROM products")
            prows = {r["slug"]: r for r in cur.fetchall()}
            netflix_id = prows["netflix"]["id"]
            shahid_id = prows["shahid"]["id"]

            cur.execute(
                "INSERT INTO product_variants(product_id,name,active) VALUES (%s,%s,TRUE) RETURNING id",
                (netflix_id, "Netflix 1 user"),
            )
            nv1 = cur.fetchone()["id"]
            cur.execute(
                "INSERT INTO product_variants(product_id,name,active) VALUES (%s,%s,TRUE) RETURNING id",
                (netflix_id, "Netflix Full Account"),
            )
            nv2 = cur.fetchone()["id"]

            # Shahid
            cur.execute(
                "INSERT INTO product_variants(product_id,name,active) VALUES (%s,%s,TRUE) RETURNING id",
                (shahid_id, "Shahid 1 User VIP"),
            )
            sv1 = cur.fetchone()["id"]
            cur.execute(
                "INSERT INTO product_variants(product_id,name,active) VALUES (%s,%s,TRUE) RETURNING id",
                (shahid_id, "Shahid VIP Full Account"),
            )
            sv2 = cur.fetchone()["id"]

            # Plans
            cur.executemany(
                "INSERT INTO product_plans(variant_id,duration,price_usd,active) VALUES (%s,%s,%s,TRUE)",
                [
                    (nv1, "1 Month", 3.6),
                    (nv1, "3 Months", 6.9),
                    (nv1, "6 Months", 12.5),
                    (nv1, "1 Year", 21.0),
                    (nv2, "1 Month", 8.9),
                    (nv2, "1 Year", 90.0),
                    (sv1, "1 Month", 2.5),
                    (sv1, "3 Months", 4.5),
                    (sv1, "1 Year", 10.0),
                    (sv2, "1 Month", 5.0),
                    (sv2, "3 Months", 10.0),
                    (sv2, "1 Year", 35.0),
                ],
            )


def fmt_lbp(amount: int) -> str:
    return f"{amount:,}"


# --------------------
# Users
# --------------------
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


def get_user_by_id(uid):
    with get_conn() as c:
        cur = c.cursor()
        cur.execute("SELECT * FROM users WHERE id=%s", (uid,))
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


# --------------------
# uShare packages
# --------------------
def list_packages(active_only=True):
    with get_conn() as c:
        cur = c.cursor()
        if active_only:
            cur.execute("SELECT * FROM packages WHERE active = TRUE ORDER BY price")
        else:
            cur.execute("SELECT * FROM packages ORDER BY price")
        return cur.fetchall()


def get_package(pid):
    with get_conn() as c:
        cur = c.cursor()
        cur.execute("SELECT * FROM packages WHERE id=%s", (pid,))
        return cur.fetchone()


def create_ushare_order(user_id, package_id, user_number):
    with get_conn() as c:
        cur = c.cursor()
        cur.execute(
            """INSERT INTO orders(user_id,package_id,user_number,status,created_at,order_type)
               VALUES (%s,%s,%s,'pending',%s,'ushare') RETURNING id""",
            (user_id, package_id, user_number, datetime.utcnow()),
        )
        return cur.fetchone()["id"]


# --------------------
# Premium (Netflix/Shahid/others)
# --------------------
def list_variants_with_plans(product_slug: str):
    with get_conn() as c:
        cur = c.cursor()
        cur.execute(
            """SELECT pv.id, pv.name, p.slug AS product_slug, p.title AS product_title
               FROM product_variants pv
               JOIN products p ON p.id = pv.product_id
               WHERE p.slug=%s AND pv.active=TRUE AND p.active=TRUE
               ORDER BY pv.id""",
            (product_slug,),
        )
        variants = cur.fetchall()

        # attach plans
        for v in variants:
            cur.execute(
                """SELECT id, duration, price_usd
                   FROM product_plans
                   WHERE variant_id=%s AND active=TRUE
                   ORDER BY id""",
                (v["id"],),
            )
            v["plans"] = cur.fetchall()
        return variants


def get_variant(variant_id: int):
    with get_conn() as c:
        cur = c.cursor()
        cur.execute(
            """SELECT pv.*, p.slug AS product_slug, p.title AS product_title
               FROM product_variants pv
               JOIN products p ON p.id = pv.product_id
               WHERE pv.id=%s""",
            (variant_id,),
        )
        return cur.fetchone()


def get_plan(plan_id: int):
    with get_conn() as c:
        cur = c.cursor()
        cur.execute("SELECT * FROM product_plans WHERE id=%s", (plan_id,))
        return cur.fetchone()


def create_premium_order(user_id: int, product_name: str, duration: str, price_usd: float):
    with get_conn() as c:
        cur = c.cursor()
        cur.execute(
            """INSERT INTO orders(user_id,status,created_at,order_type,product_name,duration,price_usd)
               VALUES (%s,'pending',%s,'premium',%s,%s,%s) RETURNING id""",
            (user_id, datetime.utcnow(), product_name, duration, price_usd),
        )
        return cur.fetchone()["id"]


def deliver_order(oid: int, phone=None, email=None, password=None, notes=None):
    with get_conn() as c:
        cur = c.cursor()
        cur.execute(
            """UPDATE orders
               SET delivery_phone=%s, delivery_email=%s, delivery_password=%s, delivery_notes=%s
               WHERE id=%s""",
            (phone, email, password, notes, oid),
        )


# --------------------
# Orders
# --------------------
def list_user_orders(user_id, limit=50):
    with get_conn() as c:
        cur = c.cursor()
        cur.execute(
            """SELECT o.id, o.status, o.created_at, o.order_type, o.user_number,
                      o.product_name, o.duration, o.price_usd,
                      o.delivery_phone, o.delivery_email, o.delivery_password, o.delivery_notes,
                      p.name AS package_name
               FROM orders o
               LEFT JOIN packages p ON p.id = o.package_id
               WHERE o.user_id=%s
               ORDER BY o.id DESC
               LIMIT %s""",
            (user_id, limit),
        )
        rows = cur.fetchall()
        # stringify datetime for templates
        for r in rows:
            if isinstance(r.get("created_at"), datetime):
                r["created_at"] = r["created_at"].strftime("%Y-%m-%d %H:%M")
        return rows


def get_order(oid: int):
    with get_conn() as c:
        cur = c.cursor()
        cur.execute(
            """SELECT o.*, u.phone,
                      p.name AS package_name, p.price AS package_price
               FROM orders o
               JOIN users u ON u.id = o.user_id
               LEFT JOIN packages p ON p.id = o.package_id
               WHERE o.id=%s""",
            (oid,),
        )
        return cur.fetchone()


def update_order_status(oid: int, status: str):
    with get_conn() as c:
        cur = c.cursor()
        cur.execute("UPDATE orders SET status=%s WHERE id=%s", (status, oid))
